# AG-UI Replay Mechanism - Event Sourcing and Checkpointing

## Overview

This BPMN workflow system now implements the **AG-UI Replay Protocol** for persistent event history and session replay. This allows users to:

1. **View full conversation history** when clicking on completed tasks
2. **Reconnect after page refresh** and see all past events
3. **Resume workflows** from where they left off
4. **Review agent interactions** including thinking steps, tool usage, and LLM responses

## Architecture

### Event Sourcing

Every AG-UI event (thinking, tool use, streaming messages) is **stored in memory** as it occurs:

```
Backend (agui_server.py)
├── event_history: {elementId: [raw_events]}
└── message_history: {elementId: {threadId, messages, thinking, tools}}
```

### Thread IDs

Each BPMN task element gets a unique **thread ID** for tracking its conversation:

```python
threadId = f"thread_{element_id}"
```

This thread ID persists across:
- Live streaming (real-time events)
- Replay (historical playback)
- Session restoration (page refresh)

### Checkpointing

When streaming events arrive, they are **automatically persisted** to the history:

```
Live Event Flow:
text.message.start → Broadcast + Store in history
text.message.content (200x) → Broadcast + Update history
text.message.end → Broadcast + Mark complete in history
```

### Snapshot Replay

When a client needs history (e.g., clicking a completed task), the backend sends a **MESSAGES_SNAPSHOT**:

```
Replay Flow:
User clicks bubble → Frontend sends replay.request
Backend retrieves history → Builds MESSAGES_SNAPSHOT
Frontend receives snapshot → Populates panel instantly
```

## Protocol Events

### Live Streaming Events

Used during active workflow execution:

| Event | Purpose | Data |
|-------|---------|------|
| `text.message.start` | Begin streaming message | `messageId`, `elementId` |
| `text.message.content` | Stream delta token | `delta`, `content` (cumulative), `messageId` |
| `text.message.end` | Complete message | `messageId` |
| `task.thinking` | Agent thinking | `message`, `elementId` |
| `task.tool.start` | Tool execution begins | `toolName`, `toolArgs` |
| `task.tool.end` | Tool completes | `toolName`, `result` |

### Replay Events

Used for historical playback:

| Event | Purpose | Data |
|-------|---------|------|
| `messages.snapshot` | Full conversation history | `threadId`, `messages[]`, `thinking[]`, `tools[]` |
| `replay.request` | Request history | `elementId` |
| `clear.history` | Clear all history | - |

## Implementation Details

### Backend Storage (`agui_server.py`)

#### History Structure

```python
# Event history (raw events)
self.event_history = {
    'element_4': [
        {'type': 'task.thinking', 'message': 'Analyzing...', 'timestamp': '...'},
        {'type': 'text.message.start', 'messageId': 'abc-123', ...},
        {'type': 'text.message.content', 'delta': 'Hello', ...},
        # ... hundreds more content events
        {'type': 'text.message.end', 'messageId': 'abc-123', ...}
    ]
}

# Message history (structured for replay)
self.message_history = {
    'element_4': {
        'threadId': 'thread_element_4',
        'messages': [
            {
                'id': 'abc-123',
                'role': 'assistant',
                'content': 'Hello world (full accumulated text)',
                'status': 'complete',
                'timestamp': '...'
            }
        ],
        'thinking': [
            {'message': 'Analyzing...', 'timestamp': '...'}
        ],
        'tools': [
            {
                'name': 'search_cve',
                'args': {...},
                'status': 'complete',
                'result': {...},
                'startTime': '...',
                'endTime': '...'
            }
        ]
    }
}
```

#### Persistence Logic

```python
async def _persist_event(self, element_id: str, event: Dict[str, Any]):
    """Persist event to history for replay"""

    # Store raw event
    self.event_history[element_id].append(event)

    # Update message history based on event type
    if event_type == 'text.message.start':
        # Create new message placeholder
        self.message_history[element_id]['messages'].append({
            'id': event.get('messageId'),
            'content': '',
            'status': 'streaming'
        })

    elif event_type == 'text.message.content':
        # Update message with accumulated content
        msg['content'] = event.get('content', '')  # Full text, not delta

    elif event_type == 'text.message.end':
        # Mark message as complete
        msg['status'] = 'complete'
```

#### Snapshot Generation

```python
async def send_replay_snapshot(self, element_id: str, websocket: WebSocket = None):
    """Send MESSAGES_SNAPSHOT for replay"""

    history = self.message_history[element_id]

    snapshot = {
        'type': 'messages.snapshot',
        'elementId': element_id,
        'threadId': history['threadId'],
        'messages': history['messages'],  # Fully accumulated messages
        'thinking': history['thinking'],
        'tools': history['tools']
    }

    await websocket.send_json(snapshot)
```

### Frontend Replay (`agui-client.js`)

#### Requesting Replay

When user clicks the feedback bubble on a completed task:

```javascript
// Check if panel is empty
if (contentDiv.children.length === 0) {
    console.log('Panel is empty - requesting replay from server');
    this.requestReplay(elementId);
}

requestReplay(elementId) {
    this.send({
        type: 'replay.request',
        elementId: elementId
    });
}
```

#### Handling Snapshot

```javascript
handleMessagesSnapshot(message) {
    const panel = this.getOrCreateFeedbackPanel(message.elementId);

    // Clear existing content
    panel.innerHTML = '';

    // Replay thinking events
    message.thinking.forEach(thinking => {
        // Create event item with 🤔 icon
    });

    // Replay tool events
    message.tools.forEach(tool => {
        // Create event item with 🔧 icon and status
    });

    // Replay messages (instant display, no typing animation)
    message.messages.forEach(msg => {
        // Create event item with full accumulated text
        messageContainer.textContent = msg.content;  // All at once
    });
}
```

## User Experience

### Live Streaming (Active Workflow)

1. Workflow executes agentic task
2. Events stream in real-time:
   - 🤔 "Thinking..." appears
   - 🔧 "Tool: search_cve" starts
   - 🔧 "Tool: search_cve" completes
   - 💬 "LLM Response" starts with typing indicator (●●●)
   - 💬 Text accumulates token by token: "Based", "Based on", "Based on the"...
   - 💬 Message marked complete (green border)
3. Panel hidden by default - user clicks 💬 bubble to view

### Replay (Completed Task)

1. User clicks 💬 bubble on completed task
2. Panel shows but is empty
3. Frontend requests replay: `replay.request`
4. Backend sends `messages.snapshot` with full history
5. Panel populates **instantly** with all events:
   - 🤔 Thinking events
   - 🔧 Tool executions (with results)
   - 💬 LLM responses (full text, no typing animation)

### After Page Refresh

1. User refreshes browser
2. Workflow has already completed
3. User clicks 💬 bubble on any task
4. Replay mechanism fetches full history
5. User sees complete conversation as it happened

## Benefits

### 1. **No Data Loss**
All events are preserved even if the user isn't watching the panel.

### 2. **Instant Replay**
Clicking a completed task shows full history immediately - no need to re-run the workflow.

### 3. **Efficient Streaming**
Live events use deltas for real-time efficiency. Replay uses snapshots for instant loading.

### 4. **Debugging**
Developers can review exactly what the agent did, including:
- What it thought about
- Which tools it used
- What the LLM said

### 5. **Session Persistence**
History survives page refreshes (stored in backend memory).

## Comparison: Live vs Replay

| Aspect | Live Streaming | Replay |
|--------|----------------|--------|
| **Event Type** | `text.message.content` (delta) | `messages.snapshot` (full) |
| **UI Effect** | Typing animation, character by character | Instant text display |
| **Network** | 200+ small messages | 1 large message |
| **User sees** | "Based" → "Based on" → "Based on the" | "Based on the data provided..." (all at once) |
| **Timeline** | Events appear as they happen | Events appear from history |

## Example Flow

### Live Execution

```
Backend sends:
1. task.thinking → message: "Analyzing CVE data..."
2. task.tool.start → toolName: "search_cve"
3. task.tool.end → toolName: "search_cve", result: {...}
4. text.message.start → messageId: "abc-123"
5. text.message.content → delta: "Based" (cumulative: "Based")
6. text.message.content → delta: " on" (cumulative: "Based on")
7. text.message.content → delta: " the" (cumulative: "Based on the")
   ... (200 more content events)
8. text.message.end → messageId: "abc-123"

Frontend displays:
- 🤔 Thinking: "Analyzing CVE data..."
- 🔧 Tool: search_cve (Running...)
- 🔧 Tool: search_cve (✓ Complete)
- 💬 LLM Response: "●●●" → "Based" → "Based on" → ... (typing animation)
```

### Replay (Later)

```
User clicks bubble → Frontend sends replay.request

Backend sends:
messages.snapshot → {
    threadId: "thread_element_4",
    thinking: [
        {message: "Analyzing CVE data...", timestamp: "..."}
    ],
    tools: [
        {name: "search_cve", status: "complete", result: {...}}
    ],
    messages: [
        {
            id: "abc-123",
            content: "Based on the data provided, there are several..." (FULL TEXT),
            status: "complete"
        }
    ]
}

Frontend displays (instantly):
- 🤔 Thinking: "Analyzing CVE data..."
- 🔧 Tool: search_cve (✓ Complete)
- 💬 LLM Response: "Based on the data provided, there are several..." (full text)
```

## Memory Management

### Current Implementation (In-Memory)

- History stored in Python dictionaries
- Persists until server restart
- Suitable for development and short sessions

### Future Enhancements

For production use, consider adding persistent storage:

```python
# Option 1: SQLite (Simple)
import sqlite3
async def _persist_event(self, element_id: str, event: Dict[str, Any]):
    db.execute("INSERT INTO events VALUES (?, ?, ?)",
               (element_id, event_type, json.dumps(event)))

# Option 2: PostgreSQL (Scalable)
async def _persist_event(self, element_id: str, event: Dict[str, Any]):
    await pool.execute("INSERT INTO events (...) VALUES (...)")

# Option 3: Redis (Fast)
async def _persist_event(self, element_id: str, event: Dict[str, Any]):
    await redis.lpush(f"events:{element_id}", json.dumps(event))
```

### Clearing History

Users can clear all history via "Clear Execution" button:

```
Frontend:
clearAllHighlights() → sends clear.history

Backend:
handle_client_message() → receives clear.history
clear_history() → deletes all event_history and message_history
```

## Testing Checklist

- [ ] **Live Streaming Works**
  - Run workflow with agentic task
  - Click 💬 bubble
  - See events appear in real-time with typing animation

- [ ] **Replay Works**
  - Complete a workflow
  - Refresh browser page
  - Click 💬 bubble on completed task
  - See full history appear instantly

- [ ] **History Persists**
  - Run workflow
  - Don't click bubble
  - Wait for completion
  - Click bubble later
  - See all events that occurred while hidden

- [ ] **Clear Works**
  - Run workflow
  - Click "Clear Execution" button
  - Click 💬 bubble
  - Panel should be empty (no history)

- [ ] **Multiple Tasks**
  - Run workflow with 3 agentic tasks
  - Each task should have its own threadId
  - Each task's history should be independent

## Console Logs

### Backend Logs

```
📤 SENDING text.message.start for element: element_4, message: abc-123
📤 Sending text.message.content chunk - element: element_4, cumulative length: 47
✅ text.message.end sent successfully
📼 Replay requested for element: element_4
📼 Sending MESSAGES_SNAPSHOT for element element_4
   Thread ID: thread_element_4
   Messages: 1
   Thinking events: 1
   Tool events: 3
🗑️ Clear history requested
🗑️ Cleared all history
```

### Frontend Logs

```
📨 Received: text.message.start
📝 Text message start: element_4 abc-123
📨 Received: text.message.content (x200)
📝 Message content updated: 47 → 59 chars
✅ Text message complete: element_4 abc-123
💬 Feedback bubble clicked for element_4
   Panel is now: VISIBLE
   Panel has 0 event items
   Panel is empty - requesting replay from server
📼 Requesting replay for element: element_4
📼 MESSAGES_SNAPSHOT received for element: element_4
   Thread ID: thread_element_4
   Messages: 1
   Thinking events: 1
   Tool events: 3
📼 Replay complete - panel populated with history
```

## Summary

The AG-UI Replay Mechanism provides:

✅ **Event Sourcing** - Every event is persisted as it occurs
✅ **Thread IDs** - Each task has a unique conversation identifier
✅ **Checkpointing** - History is stored for later replay
✅ **MESSAGES_SNAPSHOT** - Instant historical playback
✅ **Efficient Streaming** - Live events use deltas, replay uses snapshots
✅ **User Control** - Panel hidden by default, user requests replay on demand
✅ **Session Persistence** - History survives page refreshes (in memory)
✅ **Clear History** - Users can reset via "Clear Execution" button

This implementation follows the AG-UI protocol specification for professional agent interfaces, providing a seamless experience whether viewing live events or replaying historical conversations.
