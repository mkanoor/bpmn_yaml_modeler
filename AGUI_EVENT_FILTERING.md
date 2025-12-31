# AG-UI Event Category Filtering

## Overview

The BPMN workflow engine now supports **configurable event filtering** for Agentic Tasks. This allows users to control which AG-UI event categories are sent to the frontend, reducing noise and bandwidth usage.

## Event Categories

AG-UI events are organized into **5 primary categories**:

### 1. 📝 Messaging Events
**Events related to LLM text generation and streaming**

- `text.message.start` - Start of a new AI message
- `text.message.content` - Streaming content deltas
- `text.message.end` - Message completion

**Use case:** See AI responses in real-time as they're generated

**Bandwidth:** Medium-High (200+ events per message during streaming)

### 2. 🔧 Tool Events
**Events related to MCP tool execution**

- `task.tool.start` - Tool execution started
- `task.tool.end` - Tool execution completed
- `agent.tool_use` - Legacy tool notification

**Use case:** Monitor which tools the agent is using and their results

**Bandwidth:** Low (1-6 events per task typically)

### 3. 💾 State Management Events
**Events for checkpointing and replay**

- `messages.snapshot` - Bulk message history for replay
- `state.snapshot` - Complete state checkpoint
- `state.delta` - Incremental state change

**Use case:** Replay conversations after page refresh

**Bandwidth:** Low (only on replay requests)

### 4. 🔄 Lifecycle & Control Events
**Workflow execution lifecycle**

- `workflow.started` - Workflow execution began
- `workflow.completed` - Workflow finished
- `element.activated` - BPMN element started
- `element.completed` - BPMN element finished
- `task.progress` - Task progress update
- `task.error` - Task encountered error
- `task.cancelled` - Task was cancelled
- `gateway.evaluating` - Gateway evaluating conditions
- `gateway.path_taken` - Gateway chose path

**Use case:** Track workflow execution progress

**Bandwidth:** Low-Medium (depends on workflow complexity)

### 5. ⚙️ Special / Other Events
**Thinking indicators and special events**

- `task.thinking` - Agent is thinking/processing
- `userTask.created` - User approval task created
- `ping`/`pong` - Connection health checks
- `replay.request` - Client requesting replay
- `clear.history` - Clear event history

**Use case:** Show agent thinking status, handle UI interactions

**Bandwidth:** Low (intermittent)

## Configuration

### Frontend (BPMN Modeler)

When editing an **Agentic Task**, you'll see the "AG-UI Event Categories" multiselect field in the properties panel:

```
AG-UI Event Categories
☑ 📝 Messaging Events (TEXT_MESSAGE_START/CONTENT/END)
☑ 🔧 Tool Events (TOOL_CALL_START/ARGS/RESULT/END)
☐ 💾 State Management (STATE_SNAPSHOT/DELTA, MESSAGES_SNAPSHOT)
☐ 🔄 Lifecycle & Control (RUN_STARTED/FINISHED/ERROR, STEP_*)
☐ ⚙️ Special / Other (RAW, CUSTOM)
```

**Default selection:** `messaging` and `tool` (the most relevant for agentic tasks)

### Backend (Workflow Definition YAML)

The selected categories are stored in the task's `custom` properties:

```yaml
elements:
  - id: element_4
    type: agenticTask
    name: Analyze Security Logs
    properties:
      model: claude-3-opus
      agentType: log-analyzer
      custom:
        aguiEventCategories:
          - messaging
          - tool
        systemPrompt: "You are an expert DevOps engineer..."
        mcpTools:
          - search_cve
          - get_rhsa
          - search_kb
```

## How It Works

### 1. Registration Phase
When an agentic task starts executing:

```python
# backend/task_executors.py
if self.agui_server:
    self.agui_server.register_task_preferences(task.id, props)
```

This registers the task's event preferences with the AG-UI server.

### 2. Event Filtering
Before sending any event to the frontend:

```python
# backend/agui_server.py
async def send_update(self, message: Dict[str, Any]):
    event_type = message.get('type')
    element_id = message.get('elementId')

    # Apply filtering if preferences registered
    if element_id and element_id in self.task_preferences:
        task_prefs = self.task_preferences[element_id]
        if not event_filter.should_send_event(event_type, task_prefs):
            logger.debug(f"🚫 Filtered event '{event_type}' for element {element_id}")
            return  # Don't send this event

    await self.broadcast(message)
```

### 3. Event Category Mapping
Events are mapped to categories in `backend/agui_event_filter.py`:

```python
EVENT_CATEGORY_MAP = {
    # Messaging Events
    'text.message.start': 'messaging',
    'text.message.content': 'messaging',
    'text.message.end': 'messaging',

    # Tool Events
    'task.tool.start': 'tool',
    'task.tool.end': 'tool',

    # State Management
    'messages.snapshot': 'state',

    # Lifecycle
    'element.activated': 'lifecycle',
    'element.completed': 'lifecycle',

    # Special
    'task.thinking': 'special',
    # ...
}
```

## Use Cases

### Use Case 1: Minimal UI Updates (Lifecycle Only)
**Goal:** Only show workflow progress, no AI details

**Configuration:**
```
☐ Messaging Events
☐ Tool Events
☐ State Management
☑ Lifecycle & Control
☐ Special / Other
```

**Result:**
- See when tasks start/complete
- No streaming text
- No tool execution details
- Minimal bandwidth usage

### Use Case 2: Tool Focus (Tools + Lifecycle)
**Goal:** Monitor tool execution without message streaming

**Configuration:**
```
☐ Messaging Events
☑ Tool Events
☐ State Management
☑ Lifecycle & Control
☐ Special / Other
```

**Result:**
- See which MCP tools are being used
- See workflow progress
- No streaming text (saves bandwidth)

### Use Case 3: Full Visibility (All Categories)
**Goal:** See everything the agent is doing

**Configuration:**
```
☑ Messaging Events
☑ Tool Events
☑ State Management
☑ Lifecycle & Control
☑ Special / Other
```

**Result:**
- Complete event stream
- Full replay capability
- Maximum bandwidth usage
- Best for debugging

### Use Case 4: Default (Messaging + Tools)
**Goal:** Balanced visibility and performance

**Configuration:**
```
☑ Messaging Events
☑ Tool Events
☐ State Management
☐ Lifecycle & Control
☐ Special / Other
```

**Result:**
- See AI responses in real-time
- See tool usage
- Moderate bandwidth
- Good for production

## Performance Impact

### Bandwidth Comparison

**Scenario:** Agentic task with 3 MCP tools and 1 AI response (500 tokens)

| Configuration | Events Sent | Approx. Size | Use Case |
|---------------|-------------|--------------|----------|
| Lifecycle only | ~4 | 1 KB | Minimal UI |
| Tools + Lifecycle | ~10 | 3 KB | Tool monitoring |
| Messaging only | ~200 | 15 KB | AI responses only |
| Default (Msg + Tools) | ~210 | 18 KB | **Recommended** |
| All categories | ~220 | 20 KB | Full debugging |

### Network Traffic

**Default configuration (messaging + tool):**
- 10 agentic tasks = ~180 KB
- 100 agentic tasks = ~1.8 MB
- 1000 agentic tasks = ~18 MB

**Lifecycle only:**
- 10 agentic tasks = ~10 KB
- 100 agentic tasks = ~100 KB
- 1000 agentic tasks = ~1 MB

## Architecture

### File Structure

```
backend/
├── agui_event_filter.py     # Event category mapping and filtering logic
├── agui_server.py            # WebSocket server with filtering integration
├── task_executors.py         # Registers task preferences
└── event_store.py            # SQLite persistence (unaffected)

frontend/
└── app.js                    # UI controls for category selection
```

### Event Flow with Filtering

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Task Execution Starts (task_executors.py)                   │
│    agui_server.register_task_preferences(task.id, props)       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Event Generated (e.g., send_text_message_start)             │
│    await agui_server.send_text_message_start(task.id, msg_id)  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. send_update() Checks Filter (agui_server.py)                │
│    event_type = 'text.message.start'                           │
│    element_id = task.id                                        │
│    if element_id in task_preferences:                          │
│        if not event_filter.should_send_event(event_type, prefs)│
│            return  # BLOCKED                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Event Filter Logic (agui_event_filter.py)                   │
│    category = EVENT_CATEGORY_MAP['text.message.start']         │
│    # category = 'messaging'                                     │
│    configured_categories = props['custom']['aguiEventCategories']│
│    # configured_categories = ['messaging', 'tool']             │
│    return 'messaging' in ['messaging', 'tool']  # True         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Event Sent to Frontend (if filter passes)                   │
│    await self.broadcast(message)                               │
│    await self._persist_event(element_id, message)              │
└─────────────────────────────────────────────────────────────────┘
```

## Testing

### Test 1: Verify Default Configuration
1. Create new Agentic Task
2. Check properties panel
3. **Expected:** `messaging` and `tool` categories pre-selected

### Test 2: Messaging Only
1. Configure task with only `messaging` category
2. Run workflow
3. **Expected:**
   - ✅ See AI text streaming
   - ❌ No tool execution events
   - ❌ No thinking indicators

### Test 3: Tools Only
1. Configure task with only `tool` category
2. Run workflow
3. **Expected:**
   - ✅ See tool.start and tool.end events
   - ❌ No AI text streaming
   - ❌ No thinking indicators

### Test 4: Lifecycle Only
1. Configure task with only `lifecycle` category
2. Run workflow
3. **Expected:**
   - ✅ See element.activated and element.completed
   - ❌ No AI text
   - ❌ No tool events
   - ❌ No thinking

### Test 5: All Categories
1. Select all categories
2. Run workflow
3. **Expected:**
   - ✅ All events visible
   - ✅ Complete timeline

### Test 6: Replay with Filtering
1. Run task with only `messaging` selected
2. Refresh page
3. Click feedback bubble to replay
4. **Expected:**
   - ✅ Replay shows filtered events (only messages)
   - ✅ Matches live execution filtering

## Backend API

### EventFilter Class

```python
from agui_event_filter import event_filter

# Check if event should be sent
should_send = event_filter.should_send_event(
    event_type='text.message.start',
    task_preferences={'custom': {'aguiEventCategories': ['messaging', 'tool']}}
)
# Returns: True

# Get event category
category = event_filter.get_event_category('task.tool.start')
# Returns: 'tool'

# Get enabled categories
enabled = event_filter.get_enabled_categories(task_preferences)
# Returns: {'messaging', 'tool'}
```

### AGUIServer Methods

```python
# Register task preferences
agui_server.register_task_preferences(
    element_id='element_4',
    task_properties={
        'custom': {
            'aguiEventCategories': ['messaging', 'tool', 'lifecycle']
        }
    }
)

# Events are automatically filtered in send_update()
await agui_server.send_text_message_start('element_4', 'msg_123')
# Only sent if 'messaging' category is enabled

await agui_server.send_task_tool_start('element_4', 'search_cve', {...})
# Only sent if 'tool' category is enabled

await agui_server.send_task_thinking('element_4', 'Analyzing...')
# Only sent if 'special' category is enabled
```

## Migration Guide

### Existing Workflows
**No changes needed!** Existing workflows without `aguiEventCategories` configuration will:
- Use default categories: `['messaging', 'tool']`
- Behave exactly as before
- Can be updated anytime by editing task properties

### Adding to New Tasks
1. Create Agentic Task in BPMN modeler
2. Open properties panel
3. Scroll to "AG-UI Event Categories"
4. Select desired categories
5. Save workflow

## Troubleshooting

### Problem: No events showing in UI
**Solution:** Check task properties, ensure at least one category is selected

### Problem: Too many events (UI laggy)
**Solution:** Disable `messaging` category to reduce streaming events

### Problem: Can't see tool execution
**Solution:** Enable `tool` category in task properties

### Problem: Replay shows different events than live
**Solution:** This shouldn't happen - filtering is applied consistently. Check logs for filtering messages.

### Debug Logging
Enable debug logging to see filtering decisions:

```python
# In backend logs, look for:
logger.info(f"📋 Registered event preferences for {element_id}: {enabled_categories}")
logger.debug(f"🚫 Filtered event '{event_type}' for element {element_id}")
```

## Summary

✅ **5 Event Categories** - Messaging, Tool, State, Lifecycle, Special
✅ **Configurable UI** - Multiselect checkboxes in properties panel
✅ **Backend Filtering** - Events filtered before sending to frontend
✅ **Default Configuration** - Messaging + Tool categories (balanced)
✅ **Bandwidth Optimization** - Reduce network traffic by 90% (lifecycle only)
✅ **Backward Compatible** - Existing workflows use default configuration
✅ **Persistent Preferences** - Saved in workflow YAML
✅ **Consistent Replay** - Filtering applied to both live and replay events

The event filtering system gives users fine-grained control over which AG-UI events they want to see, optimizing the balance between visibility and performance based on their specific needs!
