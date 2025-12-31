# Debug Checklist for Streaming Events

## Problem
Task Activity panel shows scrollbar but no event data appears in the UI.

## What I Added
Comprehensive debug logging throughout the entire event flow from backend to frontend.

## How to Debug

### 1. Run the Workflow
Execute the `ai-log-analysis-dual-approval-workflow.yaml` with a log file.

### 2. Check Backend Logs
Look for these log messages in the **backend terminal**:

#### When Agentic Task Starts:
```
📤 SENDING task.thinking for element: element_4, message: Initializing log-analyzer agent...
✅ task.thinking sent successfully

📤 SENDING task.tool.start for element: element_4, tool: filesystem-read
✅ task.tool.start sent successfully

📤 SENDING task.tool.end for element: element_4, tool: filesystem-read
✅ task.tool.end sent successfully
```

#### When LLM Streaming Starts:
```
📤 SENDING text.message.start for element: element_4, message: msg_element_4_1234567890
   Connected clients: 1
✅ text.message.start sent successfully

📡 Streaming chunk #10: 15 chars, total: 150 chars
📡 Streaming chunk #20: 12 chars, total: 312 chars
...

📊 Streaming complete: 45 total chunks, 42 content chunks, 523 chars

📤 SENDING text.message.end for element: element_4, message: msg_element_4_1234567890
✅ text.message.end sent successfully
```

**Key Questions:**
- Are these messages appearing? → Backend is sending events correctly
- Is "Connected clients: 1"? → Frontend is connected to WebSocket
- Are chunks being streamed? → OpenRouter streaming is working

### 3. Check Frontend Console (Browser DevTools)
Open browser console (F12) and look for these messages:

#### When WebSocket Receives Events:
```
📨 Received: task.thinking {type: 'task.thinking', elementId: 'element_4', message: '...'}
📨 Received: task.tool.start {type: 'task.tool.start', elementId: 'element_4', toolName: 'filesystem-read'}
📨 Received: text.message.start {type: 'text.message.start', elementId: 'element_4', messageId: 'msg_...'}
```

#### When Creating/Using Panel:
```
🔍 getOrCreateFeedbackPanel called for elementId: element_4
   Creating NEW panel for element_4
   Positioned panel at left: 450px, top: 330px
   Panel created and hidden (display: none)
   Panel appended to body
   Returning .feedback-content div, has 0 children
```

#### When Handling Events:
```
📝 Text message start: element_4 msg_element_4_1234567890
   Full message: {type: 'text.message.start', elementId: 'element_4', ...}
🔍 getOrCreateFeedbackPanel called for elementId: element_4
   Panel already exists for element_4
   Returning .feedback-content div, has 0 children
   Event item appended to panel. Panel children count: 1
   ✅ Panel auto-shown (was hidden)

🤔 Task thinking: element_4
🔍 getOrCreateFeedbackPanel called for elementId: element_4
   Panel already exists for element_4
   Returning .feedback-content div, has 1 children
```

**Key Questions:**
- Are "Received:" messages appearing? → Events reaching frontend
- Is panel being created? → DOM manipulation working
- Are children being added? → Events being appended
- Is panel being auto-shown? → Visibility logic working

### 4. Visual Inspection
After workflow runs, check:

1. **Is there a chat bubble icon (💬) on the BPMN element?**
   - YES → `showFeedbackIcon()` worked
   - NO → Icon creation failed

2. **Click the bubble icon - does panel appear?**
   - YES → Panel exists and manual show works
   - NO → Panel doesn't exist or positioning is off-screen

3. **If panel appears manually, does it have content?**
   - YES → Auto-show was the only issue
   - NO → Events aren't being appended to DOM

### 5. DOM Inspection
In browser DevTools, go to Elements tab and search for:
```html
<div id="feedback-panel-element_4" class="task-feedback-panel">
```

Check:
- Does it exist in DOM? → Panel was created
- What's its `style.display` value? → Should be 'block' if auto-shown
- Does `.feedback-content` have children? → Events were appended
- Are the children visible? → CSS not hiding them

### 6. Common Issues & Solutions

#### Issue 1: No backend logs
**Cause:** OpenRouter not configured or agentic task not running
**Solution:** Check OPENROUTER_API_KEY in .env

#### Issue 2: Backend logs but no frontend "Received:" messages
**Cause:** WebSocket not connected
**Solution:** Check WebSocket connection status indicator in UI

#### Issue 3: "Received:" messages but no panel creation logs
**Cause:** Event handlers not being called
**Solution:** Check `handleMessage()` switch statement matches event types

#### Issue 4: Panel created but "has 0 children" forever
**Cause:** Events not appending to correct element
**Solution:** Verify `panel.appendChild(eventItem)` is being called

#### Issue 5: Panel exists with children but not visible
**Cause:** `display: none` not being changed to `block`
**Solution:** Auto-show logic should set `panel.style.display = 'block'`

#### Issue 6: Panel visible but positioned off-screen
**Cause:** BPMN element position calculation failed
**Solution:** Check console for "Could not find BPMN element" warning

## Expected Full Flow
For a single LLM streaming message, you should see:

### Backend:
1. `📤 SENDING task.thinking` → `✅ task.thinking sent`
2. `📤 SENDING task.tool.start` (x3) → `✅ task.tool.start sent` (x3)
3. `📤 SENDING task.tool.end` (x3) → `✅ task.tool.end sent` (x3)
4. `📤 SENDING text.message.start` → `✅ text.message.start sent`
5. `📡 Streaming chunk #10...` (many times)
6. `📊 Streaming complete`
7. `📤 SENDING text.message.end` → `✅ text.message.end sent`

### Frontend Console:
1. `📨 Received: task.thinking`
2. `🤔 Task thinking: element_4`
3. `🔍 getOrCreateFeedbackPanel` → panel created
4. `📨 Received: task.tool.start` (x3)
5. `🔧 Tool start: element_4 filesystem-read` (etc.)
6. `📨 Received: text.message.start`
7. `📝 Text message start: element_4`
8. `✅ Panel auto-shown (was hidden)` ← KEY MOMENT
9. `📨 Received: text.message.content` (many times)
10. `📨 Received: text.message.end`
11. `✅ Text message complete`

### Visual Result:
- 💬 bubble appears on BPMN element
- Panel automatically shows next to element
- Panel contains timeline with:
  - Thinking event with timestamp
  - 3 tool execution events
  - LLM streaming message (cumulative text)
- Panel is scrollable (if content exceeds height)

## Next Steps
Run the workflow and share:
1. Backend terminal output (especially the 📤 and ✅ messages)
2. Browser console output (especially the 📨, 🔍, and ✅ messages)
3. Screenshot of the UI showing whether panel appears

This will help identify exactly where the flow is breaking.
