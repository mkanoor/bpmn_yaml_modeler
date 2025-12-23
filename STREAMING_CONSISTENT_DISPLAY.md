# Streaming Consistent Display - Live and Replay

## Summary

Fixed timestamp display to ensure **identical appearance** for both live streaming and replay events. Each sentence now shows its actual generation timestamp from the backend.

## Problem

The frontend was generating **new timestamps** locally instead of using the backend timestamps:

```javascript
// BEFORE (Line 1199)
timestamp.innerHTML = `<span class="sentence-number">#${currentSentenceCount}</span> ${new Date().toLocaleTimeString()}`;
```

This caused:
- **Live streaming**: Showed time when browser received the message ❌
- **Replay**: Showed time when replay was clicked ❌
- **Inconsistent timing**: Replay timestamps were different from live timestamps

## Solution

**File**: `/agui-client.js` (lines 1196-1203)

Now uses the `message.timestamp` from backend:

```javascript
// AFTER
const timestampStr = message.timestamp
    ? new Date(message.timestamp).toLocaleTimeString()
    : new Date().toLocaleTimeString();
timestamp.innerHTML = `<span class="sentence-number">#${currentSentenceCount}</span> ${timestampStr}`;
```

## How It Works

### Live Streaming

1. Backend streams sentence from OpenRouter
2. Backend calls `send_text_message_chunk()` with timestamp
3. Frontend receives `text.message.chunk` event with `timestamp` field
4. Frontend displays: `#1 11:45:32` (actual generation time)

### Replay

1. User clicks feedback bubble 💬 after task completes
2. Frontend requests replay from backend
3. Backend sends stored `text.message.chunk` events from SQLite
4. Each event includes original `timestamp` from when it was generated
5. Frontend displays: `#1 11:45:32` (same as live!)

## User Experience

### Before Fix

**Live streaming**:
```
#1  11:45:32  (when browser received it)
#2  11:45:34  (when browser received it)
#3  11:45:36  (when browser received it)
```

**Replay** (clicked at 12:00:00):
```
#1  12:00:00  (WRONG - shows current time!)
#2  12:00:00  (WRONG - shows current time!)
#3  12:00:00  (WRONG - shows current time!)
```

### After Fix

**Live streaming**:
```
#1  11:45:32  (when sentence was generated)
#2  11:45:34  (when sentence was generated)
#3  11:45:36  (when sentence was generated)
```

**Replay** (clicked at 12:00:00):
```
#1  11:45:32  (CORRECT - shows original time!)
#2  11:45:34  (CORRECT - shows original time!)
#3  11:45:36  (CORRECT - shows original time!)
```

## Event Display Format

All events now use consistent format:

```
┌─────────────────────────────────────────────────┐
│ Task Activity                      5 items    × │
├─────────────────────────────────────────────────┤
│ #1  11:45:30                                    │
│ 💬 LLM Response                                 │
│ The log file shows several critical errors...   │
├─────────────────────────────────────────────────┤
│ #2  11:45:32                                    │
│ 💬 LLM Response                                 │
│ The root cause appears to be disk space...      │
├─────────────────────────────────────────────────┤
│ 🤔  11:45:34                                    │
│ Thinking: Analyzing error patterns...           │
├─────────────────────────────────────────────────┤
│ 🔧  11:45:35                                    │
│ search_kb - Running...                          │
├─────────────────────────────────────────────────┤
│ #3  11:45:38                                    │
│ 💬 LLM Response                                 │
│ Recommended action: Clear old logs from...      │
└─────────────────────────────────────────────────┘
```

Each event shows:
- ✅ **Sentence number** (for LLM responses): `#1, #2, #3...`
- ✅ **Actual timestamp**: When the event originally occurred
- ✅ **Event icon**: 💬 (LLM), 🤔 (Thinking), 🔧 (Tool)
- ✅ **Event content**: The actual message/status

## Consistency Across Event Types

All event types now use backend timestamps:

| Event Type | Live | Replay | Timestamp Source |
|------------|------|--------|------------------|
| LLM Response (`text.message.chunk`) | ✅ Backend | ✅ Backend | `message.timestamp` |
| Thinking (`task.thinking`) | ✅ Backend | ✅ Backend | `event.data.timestamp` |
| Tool Start (`task.tool.start`) | ✅ Backend | ✅ Backend | `event.data.startTime` |
| Tool End (`task.tool.end`) | ✅ Backend | ✅ Backend | `event.data.endTime` |

## Backend Timestamp Flow

### Live Streaming

**File**: `/backend/task_executors.py`

```python
# Line 1051-1052
sentence_message_id = f"msg_{task_id}_s{sentence_count}_{int(time.time() * 1000)}"
timestamp = datetime.now(timezone.utc).isoformat()

# Line 1073-1079
await self.agui_server.send_text_message_chunk(
    element_id=task_id,
    message_id=sentence_message_id,
    content=sentence,
    role='assistant'
)
```

**File**: `/backend/agui_server.py` (send_text_message_chunk)

```python
# Line 625-635
await self.send_update({
    'type': 'text.message.chunk',
    'elementId': element_id,
    'messageId': message_id,
    'role': role,
    'content': content,
    'timestamp': datetime.now(timezone.utc).isoformat()  # ← Backend timestamp
})
```

### Replay

**File**: `/backend/agui_server.py` (send_replay_snapshot)

```python
# Line 411-424
elif event['type'] == 'message.chunk':
    chunk_event = {
        'type': 'text.message.chunk',
        'elementId': element_id,
        'messageId': event['data']['id'],
        'role': event['data']['role'],
        'content': event['data']['content'],
        'timestamp': event['data']['timestamp']  # ← Original timestamp from SQLite
    }
```

## Benefits

✅ **Accurate timing**: Shows when sentences were actually generated
✅ **Consistent replay**: Replay looks identical to live streaming
✅ **Debugging**: Can see exact timing of each event
✅ **Event correlation**: Easy to correlate events across backend logs and UI
✅ **Historical accuracy**: Timestamps reflect reality, not browser display time

## Testing

1. **Refresh browser** to load updated JavaScript
2. **Execute workflow** with Agentic Task
3. **Watch timestamps** during live streaming
4. **Note the times** shown for each sentence
5. **Click feedback bubble** after completion
6. **Verify timestamps match** between live and replay

## Example

### Live Execution (11:45:30 - 11:45:38)

User executes workflow, sees sentences appear in real-time:

```
#1  11:45:30  First sentence appears
#2  11:45:32  Second sentence appears
#3  11:45:38  Third sentence appears
```

### Replay (12:00:00)

User clicks bubble at noon to review:

```
#1  11:45:30  ← Same as live!
#2  11:45:32  ← Same as live!
#3  11:45:38  ← Same as live!
```

## Files Modified

- `/agui-client.js` (lines 1196-1203) - Use `message.timestamp` instead of `new Date()`

## No Backend Changes Needed

Backend was already sending correct timestamps in both live and replay modes. Only frontend needed to use them instead of generating new ones.

## Related Features

- **Panel stays hidden by default** - User must click 💬 bubble to view
- **Live streaming** - Sentences appear one by one as generated
- **Replay** - Identical display to live experience
- **Sentence numbering** - Each LLM response gets sequential number
- **Auto-scroll** - Panel scrolls to show latest content
- **Event timeline** - All events (thinking, tools, messages) in chronological order
