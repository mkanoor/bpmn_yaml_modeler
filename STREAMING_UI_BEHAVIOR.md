# Streaming UI Behavior - Summary

## How Streaming Works

### Backend ✅ Already Working

**File**: `/backend/task_executors.py`

The Agentic Task streams LLM responses sentence-by-sentence:

1. **OpenRouter streaming** - Receives tokens in real-time
2. **Sentence detection** - Detects complete sentences using `SentenceDetector`
3. **Per-sentence events** - Sends each sentence via `send_text_message_chunk()`
4. **SQLite storage** - Stores each sentence for replay

```python
# For each complete sentence
for sentence in completed_sentences:
    await self.agui_server.send_text_message_chunk(
        element_id=task_id,
        message_id=sentence_message_id,
        content=sentence,  # Complete sentence
        role='assistant'
    )
```

### Frontend ✅ Already Working

**File**: `/agui-client.js`

The `handleTextMessageChunk()` method displays sentences as they arrive:

```javascript
handleTextMessageChunk(message) {
    const panel = this.getOrCreateFeedbackPanel(message.elementId);

    // Count sentences
    const currentSentenceCount = panel.querySelectorAll('.feedback-message').length + 1;

    // Create event with sentence number
    timestamp.innerHTML = `<span class="sentence-number">#${currentSentenceCount}</span> ${timestampStr}`;

    // Display complete sentence
    messageContainer.textContent = message.content;

    // Auto-scroll
    panel.scrollTop = panel.scrollHeight;
}
```

## User Interaction Model

### Panel Visibility

**Hidden by default** - The feedback panel is created with `display: none`:

```javascript
panel.style.display = 'none';  // Hidden until user clicks bubble
```

**User must click bubble** - To see streaming content or replay:

1. During execution: Sentences accumulate in hidden panel
2. User clicks 💬 bubble icon on task
3. Panel shows with all sentences numbered `#1, #2, #3...`

**Why hidden by default?**

- Prevents UI clutter with multiple tasks
- User chooses which task to monitor
- Panel can be dragged and positioned
- User can close panel and re-open later

### Live vs Replay

**Live Streaming** (during execution):
- Sentences accumulate in panel as generated
- Panel hidden until user clicks bubble
- When opened, user sees sentences appearing one by one
- Auto-scrolls to show latest content

**Replay** (after completion):
- User clicks bubble after task completes
- Panel opens and requests replay from server
- Server sends stored sentences from SQLite
- Frontend displays identical to live experience
- Same sentence numbers, same timestamps

## Event Display Format

All events (live and replay) show consistently:

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

Each LLM response shows:
- ✅ Sentence number (`#1, #2, #3...`)
- ✅ Actual timestamp (when generated, not when displayed)
- ✅ Event icon (💬 for LLM, 🤔 for thinking, 🔧 for tools)
- ✅ Complete sentence text

## Key Features

✅ **Sentence-by-sentence streaming** - More readable than token-by-token
✅ **Sequential numbering** - Easy to track progress
✅ **Accurate timestamps** - Shows when event actually occurred
✅ **Hidden by default** - User controls visibility
✅ **Consistent replay** - Replay looks identical to live
✅ **Auto-scroll** - Always shows latest content
✅ **Chronological timeline** - All events in order
✅ **SQLite persistence** - Events stored for replay

## How to View Streaming

### During Execution

1. Click "▶ Execute Workflow"
2. Task starts executing
3. Look for 💬 bubble icon on task element
4. **Click the bubble** to open feedback panel
5. Watch sentences appear one by one

### After Execution

1. Workflow completes
2. Task shows ✓ completion mark
3. 💬 bubble remains visible
4. **Click the bubble** to replay
5. See all sentences with original timestamps

## Why This Design?

**Sentence boundary detection** provides:
- Cleaner, more readable output
- Better replay experience (each sentence stored separately)
- Less DOM manipulation overhead
- More semantic units for context
- Easier to correlate with backend logs

**Hidden panel** provides:
- Cleaner canvas with multiple tasks
- User-controlled visibility
- Draggable positioning
- No forced interruptions during execution
- Persistent data even when hidden

## Testing

1. **Refresh browser** to load updated JavaScript
2. **Execute workflow** with Agentic Task
3. **Click feedback bubble** during execution
4. **Watch sentences** appear with timestamps
5. **Close panel** and re-open to verify persistence
6. **After completion**, click bubble to verify replay
7. **Compare timestamps** between live and replay

## Files Involved

- `/backend/task_executors.py` - Streaming implementation, sentence detection
- `/backend/agui_server.py` - Event broadcasting, replay logic
- `/backend/event_store.py` - SQLite persistence
- `/agui-client.js` - Frontend event handlers, panel management
- `/app.js` - Canvas integration, feedback icon rendering

## Related Documentation

- `STREAMING_CONSISTENT_DISPLAY.md` - Timestamp fix for live/replay consistency
- `STREAMING_ERROR_DEBUG.md` - Error logging improvements
- `MCP_INTEGRATION_COMPLETE.md` - MCP tool integration
- `MODEL_DROPDOWN_FIX.md` - OpenRouter model ID fixes
