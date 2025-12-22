# AG-UI Streaming Feedback Implementation

## Overview

This implementation adds real-time, streaming feedback from tasks to the BPMN workflow UI using the AG-UI (Agent-User Interaction) protocol. Tasks can now provide live updates, thinking indicators, and tool execution progress as they run.

## AG-UI Protocol

AG-UI uses a "partial then complete" message pattern for streaming real-time feedback:

| Stage    | Event Type           | Purpose |
|----------|---------------------|---------|
| Start    | `text.message.start` | Signal start of a new message stream |
| Partial  | `text.message.content` | Send incremental chunks of text as generated |
| Complete | `text.message.end` | Signal message is finished |

## Features Implemented

### 1. AG-UI Streaming Events (Backend)

Added to `agui_server.py`:

- **`send_text_message_start(element_id, message_id)`** - Start a new streaming message
- **`send_text_message_content(element_id, message_id, content, delta)`** - Send partial content
- **`send_text_message_end(element_id, message_id)`** - Complete the message
- **`send_task_thinking(element_id, message)`** - Show thinking indicator
- **`send_task_tool_start(element_id, tool_name, tool_args)`** - Tool execution start
- **`send_task_tool_end(element_id, tool_name, result)`** - Tool execution complete

### 2. Visual Feedback UI (Frontend)

Added to `agui-client.js`:

**Feedback Icon (💬)**:
- Appears on BPMN elements when task activity occurs
- Clickable to show/hide feedback panel
- Pulses when new activity arrives

**Feedback Panel**:
- Floating panel next to active tasks
- Shows real-time task activity
- Displays:
  - Streaming text messages
  - Thinking indicators (🤔 with animation)
  - Tool execution status (🔧)
  - Completion markers

**Event Handlers**:
- `handleTextMessageStart()` - Create message container with typing indicator
- `handleTextMessageContent()` - Append text chunks in real-time
- `handleTextMessageEnd()` - Mark message as complete
- `handleTaskThinking()` - Show animated thinking indicator
- `handleTaskToolStart()` - Show tool execution start
- `handleTaskToolEnd()` - Mark tool as complete

### 3. Task Executor Integration

Updated `AgenticTaskExecutor` in `task_executors.py`:

```python
# Send thinking indicator
await self.agui_server.send_task_thinking(
    task.id,
    "Analyzing with claude-3.5-sonnet..."
)

# Tool execution with streaming events
await self.agui_server.send_task_tool_start(task.id, tool_name, tool_args)
# ... execute tool ...
await self.agui_server.send_task_tool_end(task.id, tool_name, result)
```

### 4. Styles (CSS)

Added to `styles.css`:

- `.task-feedback-panel` - Floating feedback container
- `.feedback-message` - Message bubbles with typing indicators
- `.feedback-thinking` - Thinking indicator with rotating icon
- `.feedback-tool` - Tool execution display
- `.feedback-icon` - Clickable icon on BPMN elements
- Animations: slideIn, pulse, rotate, iconPulse

## Usage Example

### In a Task Executor:

```python
async def execute(self, task: Element, context: Dict[str, Any]):
    # 1. Show thinking
    await self.agui_server.send_task_thinking(
        task.id,
        "Analyzing log file..."
    )

    # 2. Start a streaming message
    msg_id = await self.agui_server.send_text_message_start(task.id)

    # 3. Send content in chunks (simulating AI streaming)
    chunks = ["Found", " 5 errors", " in the", " log file."]
    full_content = ""
    for chunk in chunks:
        full_content += chunk
        await self.agui_server.send_text_message_content(
            task.id,
            msg_id,
            content=full_content,
            delta=chunk
        )
        await asyncio.sleep(0.1)  # Simulate streaming delay

    # 4. Complete the message
    await self.agui_server.send_text_message_end(task.id, msg_id)

    # 5. Show tool execution
    await self.agui_server.send_task_tool_start(
        task.id,
        "log-parser",
        {"file": "error.log"}
    )
    # ... run tool ...
    await self.agui_server.send_task_tool_end(
        task.id,
        "log-parser",
        result={"errors": 5}
    )
```

### UI Experience:

1. **Task starts** → 💬 icon appears on BPMN element
2. **User clicks icon** → Feedback panel slides in
3. **Thinking phase** → "🤔 Analyzing log file..." with rotating icon
4. **Streaming text** → "Found" → "Found 5" → "Found 5 errors" → "Found 5 errors in the log file." (typewriter effect)
5. **Tool execution** → "🔧 log-parser Running..." → "🔧 log-parser Complete"
6. **Completion** → Message marked complete with green border

## Event Flow Diagram

```
Task Executor
    ↓
send_task_thinking("Analyzing...")
    ↓ WebSocket
Frontend: Show 🤔 with "Analyzing..."

    ↓
send_text_message_start(msg_id)
    ↓ WebSocket
Frontend: Create message container with ●●●

    ↓
send_text_message_content(msg_id, "Found")
    ↓ WebSocket
Frontend: Replace ●●● with "Found"

    ↓
send_text_message_content(msg_id, " 5 errors")
    ↓ WebSocket
Frontend: Append " 5 errors" → "Found 5 errors"

    ↓
send_text_message_end(msg_id)
    ↓ WebSocket
Frontend: Mark message complete (green border)

    ↓
send_task_tool_start("log-parser", {...})
    ↓ WebSocket
Frontend: Show 🔧 log-parser Running...

    ↓
send_task_tool_end("log-parser", result)
    ↓ WebSocket
Frontend: Update to Complete ✓
```

## Benefits

1. **Real-time Feedback** - Users see task progress as it happens
2. **Transparency** - View agent thinking process and tool execution
3. **Better UX** - No more black-box waiting
4. **Debugging** - See exactly what tasks are doing
5. **AI/Agent Visibility** - Perfect for agentic workflows where agents use tools
6. **Streaming Ready** - Designed for LLM streaming responses

## Use Cases

### 1. AI Log Analysis
```
🤔 Analyzing log file with Claude...
📝 Found 3 critical errors:
   - Memory leak in service A
   - Connection timeout in service B
   - Disk space warning on node C
🔧 Running log-parser... Complete ✓
🔧 Running error-classifier... Complete ✓
```

### 2. Long-Running Tasks
```
🤔 Processing large dataset...
📝 Progress: 25% complete (1,000 / 4,000 records)
📝 Progress: 50% complete (2,000 / 4,000 records)
📝 Progress: 75% complete (3,000 / 4,000 records)
📝 Progress: 100% complete - All records processed ✓
```

### 3. Multi-Tool Agent
```
🤔 Planning diagnostic steps...
🔧 filesystem-read... Complete ✓
🔧 grep-search... Complete ✓
🔧 log-parser... Complete ✓
📝 Analysis complete. Found 5 issues requiring attention.
```

## API Reference

### Backend (agui_server.py)

#### `send_text_message_start(element_id, message_id=None)`
Start a new streaming message.
- **Returns:** message_id (auto-generated if not provided)

#### `send_text_message_content(element_id, message_id, content, delta=None)`
Send partial message content.
- **content:** Full cumulative text
- **delta:** New chunk (optional, defaults to content)

#### `send_text_message_end(element_id, message_id)`
Signal message completion.

#### `send_task_thinking(element_id, message="Thinking...")`
Show thinking indicator.

#### `send_task_tool_start(element_id, tool_name, tool_args)`
Signal tool execution start.

#### `send_task_tool_end(element_id, tool_name, result=None)`
Signal tool execution complete.

### Frontend (agui-client.js)

#### Event Handlers (automatic)
- `handleTextMessageStart(message)`
- `handleTextMessageContent(message)`
- `handleTextMessageEnd(message)`
- `handleTaskThinking(message)`
- `handleTaskToolStart(message)`
- `handleTaskToolEnd(message)`

#### Utility Methods
- `getOrCreateFeedbackPanel(elementId)` - Get or create feedback panel
- `showFeedbackIcon(elementId)` - Show 💬 icon on element

## Configuration

No configuration required! The system automatically:
- Creates feedback panels when events arrive
- Positions panels next to BPMN elements
- Handles cleanup on workflow reset
- Manages multiple concurrent feedback streams

## Backward Compatibility

✅ **Fully backward compatible**
- Old `send_agent_tool_use()` still works
- New streaming events are additive
- Tasks without streaming work as before
- UI gracefully handles missing events

## Future Enhancements

Possible improvements:
1. **Message persistence** - Save feedback to database
2. **Export capability** - Download task activity logs
3. **Filtering** - Show/hide specific event types
4. **Customization** - User-configurable panel position/size
5. **Rich media** - Support images, charts in feedback
6. **Voice synthesis** - Read messages aloud (accessibility)
7. **Notifications** - Alert on critical events

## Files Modified

1. **backend/agui_server.py** - Added 6 new streaming event methods
2. **agui-client.js** - Added 7 event handlers + feedback panel UI
3. **styles.css** - Added feedback panel styles and animations
4. **backend/task_executors.py** - Integrated streaming in AgenticTaskExecutor

## Testing

To test the streaming feedback:

1. Run a workflow with an agentic task (AI log analysis)
2. Watch for 💬 icon to appear on the task element
3. Click the icon to open the feedback panel
4. Observe:
   - 🤔 Thinking indicators
   - 🔧 Tool execution progress
   - 📝 Streaming text messages
   - ✓ Completion markers

The feedback provides real-time visibility into what the task is doing!
