# Sentence-Level Streaming Implementation

## Overview

Implemented sentence-boundary detection for LLM streaming responses to enable:
- **Real-time sentence display** during live execution
- **Sentence-by-sentence replay** from SQLite storage
- **Better user experience** with meaningful chunks instead of individual tokens

## Architecture

### Flow Diagram

```
OpenRouter API (streaming tokens)
    ↓
SentenceDetector (buffers & detects sentence boundaries)
    ↓
SQLite Storage (one row per sentence with unique message_id)
    ↓
TEXT_MESSAGE_CHUNK events → Frontend
    ↓
Display sentence-by-sentence in feedback panel
```

## Components

### 1. Backend: Sentence Detection

**File**: `/backend/sentence_detector.py` (NEW)

- **Class**: `SentenceDetector`
- **Purpose**: Detect sentence boundaries in streaming LLM output
- **Features**:
  - Regex-based pattern matching for `.`, `!`, `?` followed by space/capital/newline
  - Handles abbreviations (Mr., Dr., U.S.A., etc.)
  - Handles decimals ($4.99, 3.14)
  - Handles ellipses (...)
  - Buffers tokens until complete sentence detected

**Key Methods**:
- `add_chunk(chunk: str) -> List[str]`: Add token, return completed sentences
- `flush() -> str`: Flush remaining buffer as final sentence
- `_is_false_positive(text: str) -> bool`: Check for abbreviations/decimals

### 2. Backend: Streaming Handler

**File**: `/backend/task_executors.py`

**Modified**: `AgenticTaskExecutor._call_openrouter()`

**Changes**:
1. Import `SentenceDetector`
2. Initialize sentence detector before streaming loop
3. For each OpenRouter token chunk:
   - Add to sentence detector
   - When sentence completes:
     - Generate unique `message_id` per sentence
     - Store sentence in SQLite
     - Send `TEXT_MESSAGE_CHUNK` event to frontend
4. After streaming ends, flush remaining buffer as final sentence

**Logging**:
```
🚀 STARTING STREAMING - Listening for chunks from OpenRouter
   Using SENTENCE BOUNDARY DETECTION for replay

📝 SENTENCE #1 COMPLETE
   Message ID: msg_element_4_s1_1703456789
   Length: 47 chars
   Text: I'll analyze this log file to identify issues.
   💾 Stored in SQLite
   ✅ Sent TEXT_MESSAGE_CHUNK to frontend

✅ STREAMING COMPLETE
   Total OpenRouter chunks: 347
   Total content tokens: 347
   Total sentences detected: 12
   Final text length: 1542 chars
```

### 3. Backend: AG-UI Server

**File**: `/backend/agui_server.py`

**New Method**: `send_text_message_chunk()`
- Sends `TEXT_MESSAGE_CHUNK` event
- Includes: element_id, message_id, content, role, timestamp

**Updated Method**: `send_replay_snapshot()`
- Changed from sending bulk `messages.snapshot` to sending individual `TEXT_MESSAGE_CHUNK` events
- Replays events chronologically (thinking → tools → messages)
- Sends each sentence as separate chunk
- 50ms delay between events for visual effect

### 4. Frontend: Event Handler

**File**: `/agui-client.js`

**New Handler**: `handleTextMessageChunk(message)`
- Receives `TEXT_MESSAGE_CHUNK` events
- Creates new event item for each sentence
- Displays complete sentence immediately
- Auto-scrolls to bottom

**Event Structure**:
```javascript
{
  type: 'text.message.chunk',
  elementId: 'element_4',
  messageId: 'msg_element_4_s1_1703456789',
  role: 'assistant',
  content: 'Complete sentence here.',
  timestamp: '2025-12-23T10:30:45.123Z'
}
```

## SQLite Schema

**Table**: `messages`

Each sentence is stored as a separate row:

| Column | Type | Description |
|--------|------|-------------|
| message_id | TEXT | Unique per sentence (e.g., `msg_element_4_s1_1703456789`) |
| thread_id | TEXT | Thread for the element |
| element_id | TEXT | BPMN element ID |
| role | TEXT | 'assistant' |
| content | TEXT | Complete sentence text |
| status | TEXT | 'complete' |
| timestamp | TEXT | ISO 8601 timestamp |

**Example**:
```
message_id                       | content
---------------------------------|-------------------------------
msg_element_4_s1_1703456789000   | I'll analyze this log file.
msg_element_4_s2_1703456789050   | Found 3 error patterns.
msg_element_4_s3_1703456789100   | Root cause is CVE-2024-1234.
```

## Event Flow

### Live Execution

1. **OpenRouter sends tokens**: "I", "'ll", " analyze", " this", " log", " file", "."
2. **SentenceDetector buffers**: "I'll analyze this log file."
3. **Sentence detected** (period + space/newline)
4. **Store in SQLite** with `msg_element_4_s1_1703456789`
5. **Send `TEXT_MESSAGE_CHUNK`** to frontend
6. **Frontend displays** complete sentence

### Replay

1. **User clicks feedback bubble** (💬 icon)
2. **Frontend sends** `replay.request` message
3. **Backend loads** sentences from SQLite
4. **Backend sends** `TEXT_MESSAGE_CHUNK` events sequentially
5. **Frontend displays** sentence-by-sentence with 50ms delay

## Benefits

### Before (Token Streaming)
- ❌ Hundreds of tiny deltas per second
- ❌ No meaningful storage units
- ❌ Replay shows all text at once
- ❌ Console flooded with micro-chunks

### After (Sentence Streaming)
- ✅ One chunk per sentence
- ✅ Each sentence stored separately in SQLite
- ✅ Replay shows sentences appearing one-by-one
- ✅ Clean console logs with complete sentences

## Testing

### Test Sentence Detector

```bash
cd /Users/madhukanoor/devsrc/bpmn/backend
python sentence_detector.py
```

Expected output:
```
Testing SentenceDetector:
✅ Input: 'Hello world. '
   Expected: ['Hello world.']
   Got:      ['Hello world.']

✅ Input: 'Mr. Smith went to the store. '
   Expected: ['Mr. Smith went to the store.']
   Got:      ['Mr. Smith went to the store.']
```

### Test Live Streaming

1. Start backend: `python main.py`
2. Open frontend in browser
3. Run workflow with agentic task
4. Watch backend logs for sentence detection
5. Watch frontend console for `TEXT_MESSAGE_CHUNK` events
6. Check feedback panel displays sentences

### Test Replay

1. Complete a workflow with agentic task
2. Click the 💬 bubble on the element
3. Sentences should appear one-by-one
4. Check backend logs for replay activity

## Configuration

No configuration needed - sentence detection is automatic.

To adjust sentence detector behavior, modify `/backend/sentence_detector.py`:
- Add more abbreviations to `self.abbreviations`
- Adjust regex pattern in `self.sentence_pattern`
- Change false positive detection logic

## Troubleshooting

### Issue: Sentences not detected

**Cause**: Model output doesn't have proper punctuation
**Solution**: Sentence detector will flush remaining text as final sentence

### Issue: False sentence breaks

**Cause**: Abbreviation not in whitelist
**Solution**: Add abbreviation to `self.abbreviations` set

### Issue: Replay shows all at once

**Cause**: Frontend not handling `TEXT_MESSAGE_CHUNK`
**Solution**: Check browser console for event handler errors

### Issue: SQLite empty

**Cause**: Event store not initialized
**Solution**: Check backend logs for SQLite initialization

## Files Modified

1. **Created**: `/backend/sentence_detector.py` (NEW)
2. **Modified**: `/backend/task_executors.py` (AgenticTaskExecutor._call_openrouter)
3. **Modified**: `/backend/agui_server.py` (send_text_message_chunk, send_replay_snapshot)
4. **Modified**: `/agui-client.js` (handleTextMessageChunk)
5. **Created**: `/SENTENCE_STREAMING.md` (this file)

## Future Enhancements

1. **Advanced NLP**: Use spaCy or NLTK for better sentence detection
2. **Configurable delay**: Allow users to adjust replay speed
3. **Pause/resume replay**: Add controls to pause sentence replay
4. **Sentence highlighting**: Highlight sentences as they appear during replay
5. **Partial sentence indicator**: Show "..." for incomplete sentence in buffer
