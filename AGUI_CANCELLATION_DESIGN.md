# AG-UI Task Cancellation Design

## Overview

Implement user-initiated cancellation for long-running Agentic Tasks following AG-UI protocol patterns. Users can stop LLM streaming and tool execution mid-flight.

## AG-UI Protocol for Cancellation

### Standard AG-UI Events

AG-UI protocol includes these cancellation-related events:

1. **`task.cancel.request`** (Client → Server)
   - User clicks cancel button
   - Includes `elementId` and `reason`

2. **`task.cancelled`** (Server → Client)
   - Task was successfully cancelled
   - Includes `elementId`, `reason`, and partial results

3. **`task.cancel.failed`** (Server → Client)
   - Cancellation failed (task already completed/can't be stopped)
   - Includes `elementId` and `error` message

### Cancellation States

```
┌──────────────┐
│  RUNNING     │  ← Task executing normally
└──────┬───────┘
       │ (user clicks cancel)
       ↓
┌──────────────┐
│ CANCELLING   │  ← Graceful shutdown in progress
└──────┬───────┘
       │
       ↓
┌──────────────┐
│ CANCELLED    │  ← Task stopped, partial results available
└──────────────┘
```

## User Experience

### UI Elements

#### 1. Cancel Button
Appears in the feedback panel during execution:

```
┌─────────────────────────────────────┐
│ 🧠 Agentic Task: Analyze Logs      │
│                                     │
│ ⏳ Streaming response...            │
│ ━━━━━━━━━━░░░░░░░░░░ 60%          │
│                                     │
│ Based on the log analysis, I can   │
│ see several critical errors...     │
│                                     │
│ [🛑 Cancel Task]                   │  ← NEW
└─────────────────────────────────────┘
```

#### 2. Cancellation Feedback
When user clicks cancel:

```
┌─────────────────────────────────────┐
│ 🧠 Agentic Task: Analyze Logs      │
│                                     │
│ ⚠️ Cancelling task...              │
│ ━━━━━━━━━━░░░░░░░░░░ 60%          │
│                                     │
│ Based on the log analysis, I can   │
│ see several critical errors...     │
│ (partial response - task cancelled) │
│                                     │
│ ✓ Task cancelled by user           │
└─────────────────────────────────────┘
```

### When Cancellation is Available

**Can Cancel:**
- ✅ During LLM streaming
- ✅ During MCP tool execution
- ✅ During thinking phase
- ✅ Between retries

**Cannot Cancel:**
- ❌ Task already completed
- ❌ Task already failed
- ❌ Task not started yet

## Technical Architecture

### Frontend Changes

#### agui-client.js

```javascript
class AGUIClient {
    // Track cancellable tasks
    constructor() {
        this.cancellableTasks = new Set();
        this.cancelledTasks = new Set();
    }

    // Send cancel request
    cancelTask(elementId, reason = "User cancelled") {
        if (!this.cancellableTasks.has(elementId)) {
            console.warn(`Task ${elementId} is not cancellable`);
            return;
        }

        this.send({
            type: 'task.cancel.request',
            elementId: elementId,
            reason: reason,
            timestamp: new Date().toISOString()
        });

        this.cancelledTasks.add(elementId);
    }

    // Handle cancellation events
    handleTaskCancelled(message) {
        const panel = this.getOrCreateFeedbackPanel(message.elementId);

        // Hide cancel button
        const cancelBtn = panel.querySelector('.cancel-task-btn');
        if (cancelBtn) cancelBtn.remove();

        // Show cancellation notice
        const notice = document.createElement('div');
        notice.className = 'cancellation-notice';
        notice.innerHTML = `
            <span class="cancel-icon">⚠️</span>
            Task cancelled by user
            <div class="cancel-reason">${message.reason || 'User requested cancellation'}</div>
        `;
        panel.appendChild(notice);

        // Mark as cancelled
        this.cancellableTasks.delete(message.elementId);
        this.cancelledTasks.add(message.elementId);
    }
}
```

### Backend Changes

#### agui_server.py

```python
class AGUIServer:
    def __init__(self, db_path: str = "agui_events.db"):
        # ... existing code ...

        # Track cancellation requests
        self.cancellation_requests: Dict[str, asyncio.Event] = {}
        self.cancelled_tasks: Set[str] = set()

    async def handle_client_message(self, message: Dict[str, Any], websocket: WebSocket):
        msg_type = message.get('type')

        if msg_type == 'task.cancel.request':
            element_id = message.get('elementId')
            reason = message.get('reason', 'User cancelled')

            logger.info(f"🛑 Cancel request for task: {element_id}")

            # Signal cancellation
            if element_id not in self.cancellation_requests:
                self.cancellation_requests[element_id] = asyncio.Event()

            self.cancellation_requests[element_id].set()
            self.cancelled_tasks.add(element_id)

            # Acknowledge cancellation
            await self.send_task_cancelled(element_id, reason)

    def is_cancelled(self, element_id: str) -> bool:
        """Check if task has been cancelled"""
        return element_id in self.cancelled_tasks

    async def send_task_cancellation_started(self, element_id: str):
        """Notify that cancellation is in progress"""
        await self.send_update({
            'type': 'task.cancelling',
            'elementId': element_id,
            'message': 'Stopping task gracefully...'
        })
```

#### task_executors.py

```python
class AgenticTaskExecutor(TaskExecutor):
    async def execute(self, task: Element, context: Dict[str, Any]) -> AsyncGenerator[TaskProgress, None]:
        """Execute agentic task with cancellation support"""

        # Register task preferences
        if self.agui_server:
            self.agui_server.register_task_preferences(task.id, props)

        # Execute with cancellation checks
        try:
            async for chunk in stream:
                # Check for cancellation before processing each chunk
                if self.agui_server and self.agui_server.is_cancelled(task.id):
                    logger.info(f"🛑 Task {task.id} cancelled during streaming")

                    # Send cancellation event
                    await self.agui_server.send_text_message_end(task.id, message_id)

                    # Return partial result
                    yield TaskProgress(
                        status='cancelled',
                        message='Task cancelled by user',
                        progress=0.6,
                        result={
                            'status': 'cancelled',
                            'partial_response': analysis_text,
                            'reason': 'User requested cancellation'
                        }
                    )
                    return

                # Process chunk normally
                if delta.content:
                    content_chunk = delta.content
                    analysis_text += content_chunk
                    # ... send to frontend ...

        except asyncio.CancelledError:
            # Task was cancelled via asyncio
            logger.info(f"🛑 Task {task.id} cancelled via asyncio")

            if self.agui_server:
                await self.agui_server.send_task_cancelled(task.id, "Task cancelled")

            raise

    async def _execute_mcp_tools(self, task_id: str, mcp_tools: list, ...):
        """Execute MCP tools with cancellation support"""

        for tool in tools_to_use:
            # Check cancellation before each tool
            if self.agui_server and self.agui_server.is_cancelled(task_id):
                logger.info(f"🛑 Cancelling tool execution for {task_id}")
                return tool_results  # Return partial results

            # Execute tool...
            await asyncio.sleep(0.5)

            # Check cancellation after tool
            if self.agui_server and self.agui_server.is_cancelled(task_id):
                return tool_results
```

## Event Flow

### Happy Path (Task Completes)

```
User                Frontend           Backend          OpenRouter
  │                    │                  │                 │
  │                    │   streaming...   │                 │
  │                    │ ←────────────────┼─────────────────┤
  │                    │                  │                 │
  │                    │   complete       │                 │
  │                    │ ←────────────────┤                 │
  │                    │                  │                 │
```

### Cancellation Path

```
User                Frontend           Backend          OpenRouter
  │                    │                  │                 │
  │  [Click Cancel]    │                  │                 │
  ├───────────────────→│                  │                 │
  │                    │ cancel.request   │                 │
  │                    ├─────────────────→│                 │
  │                    │                  │ [stop stream]   │
  │                    │                  ├────────────────→│
  │                    │ task.cancelling  │                 │
  │                    │←─────────────────┤                 │
  │  [Show "Cancelling..."]               │                 │
  │←───────────────────┤                  │                 │
  │                    │ task.cancelled   │                 │
  │                    │←─────────────────┤                 │
  │  [Show "Cancelled"]                   │                 │
  │←───────────────────┤                  │                 │
```

## Database Schema Changes

### New Column in `messages` Table

```sql
ALTER TABLE messages ADD COLUMN cancelled BOOLEAN DEFAULT FALSE;
ALTER TABLE messages ADD COLUMN cancellation_reason TEXT;
```

### Store Cancellation Events

```python
# event_store.py
def mark_message_cancelled(self, message_id: str, reason: str):
    """Mark a message as cancelled"""
    cursor = self.connection.cursor()
    cursor.execute("""
        UPDATE messages
        SET cancelled = TRUE,
            cancellation_reason = ?,
            status = 'cancelled',
            updated_at = CURRENT_TIMESTAMP
        WHERE message_id = ?
    """, (reason, message_id))
    self.connection.commit()
```

## Replay Behavior

When replaying a cancelled task:

```javascript
handleMessagesSnapshot(message) {
    // ... render events ...

    // Check if any messages were cancelled
    const cancelledMessages = message.messages.filter(m => m.cancelled);

    if (cancelledMessages.length > 0) {
        const notice = document.createElement('div');
        notice.className = 'replay-cancellation-notice';
        notice.innerHTML = `
            ⚠️ This task was cancelled during execution
            Reason: ${cancelledMessages[0].cancellation_reason}
        `;
        panel.appendChild(notice);
    }
}
```

## Error Handling

### Cancellation During Different Phases

1. **During LLM Streaming:**
   - Stop processing stream chunks
   - Send `text.message.end` with partial content
   - Return partial result

2. **During Tool Execution:**
   - Complete current tool
   - Don't start next tool
   - Return results from completed tools only

3. **Between Retries:**
   - Don't start next retry
   - Return error from last attempt

4. **Already Completed:**
   - Send `task.cancel.failed` event
   - Show message: "Task already completed"

### Race Conditions

**Scenario:** Task completes just as user clicks cancel

**Solution:**
```python
async def send_task_cancelled(self, element_id: str, reason: str):
    # Check if task already completed
    if element_id in self.completed_tasks:
        await self.send_update({
            'type': 'task.cancel.failed',
            'elementId': element_id,
            'error': 'Task already completed'
        })
        return

    # Mark as cancelled
    self.cancelled_tasks.add(element_id)

    await self.send_update({
        'type': 'task.cancelled',
        'elementId': element_id,
        'reason': reason
    })
```

## CSS Styling

```css
.cancel-task-btn {
    background: #dc3545;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    margin-top: 0.5rem;
    font-weight: bold;
}

.cancel-task-btn:hover {
    background: #c82333;
}

.cancel-task-btn:disabled {
    background: #6c757d;
    cursor: not-allowed;
}

.cancellation-notice {
    background: #fff3cd;
    border-left: 4px solid #ffc107;
    padding: 0.75rem;
    margin-top: 0.5rem;
    border-radius: 4px;
}

.cancel-icon {
    font-size: 1.2em;
    margin-right: 0.5rem;
}

.cancel-reason {
    font-size: 0.9em;
    color: #856404;
    margin-top: 0.25rem;
}

.task-cancelling {
    background: #f8d7da;
    animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}
```

## Testing Scenarios

### Test 1: Cancel During Streaming
1. Start agentic task
2. Wait for streaming to start
3. Click cancel button
4. **Expected:** Streaming stops, partial response shown, cancellation notice displayed

### Test 2: Cancel During Tool Execution
1. Start agentic task
2. Wait for tool to start
3. Click cancel button
4. **Expected:** Current tool completes, next tools don't run, partial results returned

### Test 3: Cancel Already Completed Task
1. Wait for task to complete
2. Try to click cancel
3. **Expected:** Cancel button disabled/hidden, or shows "Task already completed"

### Test 4: Replay Cancelled Task
1. Cancel a running task
2. Refresh page
3. Click feedback bubble
4. **Expected:** Replay shows partial response + cancellation notice

### Test 5: Multiple Concurrent Tasks
1. Start 3 agentic tasks
2. Cancel only the 2nd one
3. **Expected:** Only 2nd task stops, others continue normally

## Configuration

### Enable/Disable Cancellation

Add to task properties:

```javascript
agenticTask: [
    // ... existing fields ...
    {
        key: 'allowCancellation',
        label: 'Allow User Cancellation',
        type: 'checkbox',
        defaultValue: true,
        helpText: 'Allow users to cancel this task while running'
    }
]
```

### Backend Check

```python
if props.get('allowCancellation', True):
    # Show cancel button
    await self.agui_server.send_update({
        'type': 'task.cancellable',
        'elementId': task.id
    })
```

## Summary

✅ **Cancel Button** - Appears in feedback panel during execution
✅ **Graceful Shutdown** - Stops streaming and tool execution cleanly
✅ **Partial Results** - Returns data collected before cancellation
✅ **AG-UI Protocol** - Uses standard `task.cancel.request` / `task.cancelled` events
✅ **Database Persistence** - Cancelled state stored for replay
✅ **Error Handling** - Handles edge cases (already completed, race conditions)
✅ **Configurable** - Can enable/disable per task
✅ **Visual Feedback** - Clear UI indicators for cancellation state

This provides users with full control over long-running AI tasks!
