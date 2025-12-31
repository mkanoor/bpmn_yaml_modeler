# Streaming Events Debug Summary

## Current Status

Based on your console logs, the streaming events ARE working correctly:
- ✅ Backend is sending `text.message.start`, `text.message.content`, `text.message.end`
- ✅ Frontend is receiving all events (hundreds of content deltas visible in console)
- ✅ Panel exists and has 6 children (event items)
- ✅ Message container is being found and updated

## Why You're Not Seeing Events

**The panel is HIDDEN by default** (as you requested: "I dont want the auto-show").

You need to **CLICK THE FEEDBACK BUBBLE ICON (💬)** on the BPMN task element to show the panel.

## How to View Events

### Step 1: Look for the Feedback Bubble Icon
After a workflow runs with agentic tasks, you should see a 💬 icon appear on the task element.

Console will show:
```
💬 Feedback icon added to element element_4 - CLICK IT to show panel
```

### Step 2: Click the Bubble Icon
Click the 💬 icon to toggle the Task Activity panel visibility.

Console will show:
```
💬 Feedback bubble clicked for element_4
   Panel is now: VISIBLE
   Panel has 6 event items
```

### Step 3: View the Timeline
The panel will appear in the top-right corner and show a timeline of events:

1. **🤔 Thinking** - Agent thinking messages
2. **🔧 Tool Execution** - Tools being used
3. **💬 LLM Response** - Streaming text response (accumulated from all deltas)

## What the Console Logs Show

Your logs show:

```
📨 Received: text.message.content {type: 'text.message.content', elementId: 'element_4', ...}
   delta: ' connections'
```

This means:
- ✅ Event received successfully
- ✅ Delta = ' connections' will be appended to the message container
- ✅ The message container accumulates ALL deltas into one growing message

**IMPORTANT**: You should NOT see hundreds of separate event items. The streaming protocol works by updating ONE message container with each delta. So:
- `text.message.start` → Creates ONE new "LLM Response" event item with typing indicator (●●●)
- `text.message.content` (sent 200 times) → Updates THAT SAME message by appending each delta
- `text.message.end` → Marks that message as complete

## New Debug Logging Added

I've added enhanced logging to help verify the content is being accumulated:

### Content Update Logging (every ~50 characters)
```
📝 Message content updated: 0 → 12 chars
   Delta added: " connections"
   Current text preview: "Based on t..."
```

This shows:
- Previous message length → New message length
- The delta that was just added
- Preview of current accumulated text

### Panel Visibility Logging
```
💬 Feedback bubble clicked for element_4
   Panel is now: VISIBLE
   Panel has 6 event items
```

### Message Container Not Found Warning
If the message container can't be found:
```
⚠️ Message container NOT found for messageId: abc-123
   Panel children count: 6
   Looking for: .feedback-message[data-message-id="abc-123"]
```

## Expected Console Output When Working Correctly

### 1. Text Message Start
```
📝 Text message start: element_4 abc-123
   Full message: {...}
🔍 getOrCreateFeedbackPanel called for elementId: element_4
   Panel already exists for element_4
   Event item appended to panel. Panel children count: 6
💬 Feedback icon added to element element_4 - CLICK IT to show panel
```

### 2. Text Message Content (repeated ~200 times)
```
📨 Received: text.message.content {elementId: 'element_4', messageId: 'abc-123', delta: ' connections'}
📝 Message content updated: 47 → 59 chars
   Delta added: " connections"
   Current text preview: "Based on the data provided, there are several connections..."
```

### 3. Text Message End
```
✅ Text message complete: element_4 abc-123
```

### 4. User Clicks Bubble
```
💬 Feedback bubble clicked for element_4
   Panel is now: VISIBLE
   Panel has 6 event items
```

## Testing Checklist

Run a workflow with an agentic task and verify:

- [ ] Console shows `💬 Feedback icon added to element element_X - CLICK IT to show panel`
- [ ] You can see the 💬 icon on the BPMN task element in the canvas
- [ ] Clicking the icon shows console message: `Panel is now: VISIBLE`
- [ ] Panel appears in top-right corner with blue border
- [ ] Panel shows timeline of events (thinking, tools, LLM response)
- [ ] Console shows `📝 Message content updated` logs with increasing character counts
- [ ] LLM Response event item contains the full accumulated message text
- [ ] Clicking the icon again hides the panel (`Panel is now: HIDDEN`)
- [ ] Panel can be dragged by clicking and holding the blue header

## Common Issues

### Issue: "I don't see the bubble icon"
**Solution**: Check if workflow actually executed agentic task. Console should show:
```
📤 SENDING text.message.start for element: element_4
```

### Issue: "I see the icon but nothing happens when I click it"
**Solution**: Check console for click logging:
```
💬 Feedback bubble clicked for element_4
   Panel is now: VISIBLE
```

### Issue: "Panel is empty"
**Solution**: Check if message container was created:
- Console should show event items being appended
- Check for warning: `⚠️ Message container NOT found`

### Issue: "I see hundreds of events in console but only 6 items in panel"
**Expected Behavior**: This is CORRECT. The hundreds of `text.message.content` events all update THE SAME message container. You should see:
- 1x Thinking event
- 3x Tool execution events
- 1x LLM Response event (contains all accumulated deltas)
- 1x (possibly) another event

Total = 6 separate timeline items, where the LLM Response grows as deltas arrive.

## Architecture Summary

### Backend (`task_executors.py`)
```python
# Send START
await agui_server.send_text_message_start(task_id, message_id)

# Stream content (200+ times)
async for chunk in stream:
    delta = chunk.choices[0].delta.content
    await agui_server.send_text_message_content(
        task_id, message_id,
        content=full_text,  # Cumulative
        delta=delta         # Just this chunk
    )

# Send END
await agui_server.send_text_message_end(task_id, message_id)
```

### Frontend (`agui-client.js`)
```javascript
// START - Creates ONE event item with message container
handleTextMessageStart(message) {
    const eventItem = document.createElement('div');
    // ... add timestamp, header
    const messageContainer = document.createElement('div');
    messageContainer.setAttribute('data-message-id', message.messageId);
    messageContainer.innerHTML = '<span class="typing-indicator">●●●</span>';
    eventItem.appendChild(messageContainer);
    panel.appendChild(eventItem);
}

// CONTENT - Updates SAME message container (200+ times)
handleTextMessageContent(message) {
    const messageContainer = panel.querySelector(
        `.feedback-message[data-message-id="${message.messageId}"]`
    );
    messageContainer.textContent += message.delta; // Append delta
    panel.scrollTop = panel.scrollHeight; // Auto-scroll
}

// END - Marks message as complete
handleTextMessageEnd(message) {
    messageContainer.classList.remove('streaming');
    messageContainer.classList.add('complete');
}
```

## Next Steps

1. **Run a workflow** with an agentic task
2. **Look for the 💬 icon** on the task element
3. **Click the icon** to show the panel
4. **Verify** you see the timeline with 6 events
5. **Check console** for the new debug messages showing content updates
6. **Report back** what you see in the panel and console

If the panel shows correctly when you click the bubble, then everything is working as designed. The "hundreds of events" you see in the console are the individual deltas that get accumulated into ONE growing message in the panel.
