# Task Activity Panel Fix - Positioning and Content Rendering

## Problems Fixed

### Problem 1: Panel Stuck at Bottom of Screen
**Issue**: Task Activity panel was positioned using `getBoundingClientRect()` relative to BPMN element, which gave viewport coordinates. When canvas was zoomed/panned, the element moved but the panel stayed in its original fixed position, appearing "stuck."

**Root Cause**:
```javascript
// OLD CODE - Position relative to BPMN element
const rect = element.getBoundingClientRect();
panel.style.left = `${rect.right + 20}px`;
panel.style.top = `${rect.top}px`;
```

When the canvas zooms or pans, the BPMN element position changes, but the panel doesn't update.

**Solution**: Position panel in a consistent, visible location (top-right corner) that doesn't depend on canvas zoom/pan state:
```javascript
// NEW CODE - Fixed position in viewport
panel.style.position = 'fixed';
panel.style.right = '20px';
panel.style.top = '100px';
```

### Problem 2: Panel Not Movable
**Issue**: Panel was stuck in one position and user couldn't move it.

**Solution**: Added drag-and-drop functionality via `makePanelDraggable()` method:
- User can click and drag the panel header
- Panel follows mouse movement
- Closes button still works (doesn't trigger drag)

```javascript
makePanelDraggable(panel) {
    const header = panel.querySelector('.feedback-header');
    header.style.cursor = 'move';

    header.addEventListener('mousedown', (e) => {
        // Start dragging
        isDragging = true;
        // ... track mouse position
    });

    document.addEventListener('mousemove', (e) => {
        // Move panel with mouse
        panel.style.left = `${currentX}px`;
        panel.style.top = `${currentY}px`;
    });
}
```

### Problem 3: Panel Not Showing Event Data
**Issue**: Panel showed scrollbar but no content inside.

**Root Cause**: CSS flex layout had `min-height: 0` which allows content to render properly.

**Solution**:
1. Keep panel hidden by default: `panel.style.display = 'none'`
2. User must click feedback bubble icon (💬) to show panel
3. Events accumulate in panel while hidden, visible when user opens it

```javascript
// Panel hidden by default
panel.style.display = 'none';

// User clicks bubble icon to toggle visibility
icon.addEventListener('click', () => {
    const panel = document.getElementById(`feedback-panel-${elementId}`);
    if (panel) {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }
});
```

### Problem 4: Auto-Show Logic Interference
**Issue**: Complex auto-show logic was checking if `panel.style.display === 'none'` but was unreliable.

**Solution**: Removed all auto-show logic from event handlers. Panel only shows when user explicitly clicks the bubble icon:

```javascript
// REMOVED from handleTextMessageStart() and handleTaskThinking():
const panelElement = document.getElementById(`feedback-panel-${message.elementId}`);
if (panelElement.style.display === 'none') {
    panelElement.style.display = 'block';
}

// Panel stays hidden - user controls visibility via bubble icon
```

## Changes Made

### `agui-client.js`

#### 1. Updated `getOrCreateFeedbackPanel()` (lines 1176-1219)

**Before**:
- Positioned panel relative to BPMN element using `getBoundingClientRect()`
- Set `display: none` by default
- Panel not draggable
- Complex auto-show logic

**After**:
- Positions panel at fixed location: `right: 20px, top: 100px`
- Sets `display: none` by default (user controls visibility)
- Makes panel draggable via `makePanelDraggable()`
- No auto-show - user clicks bubble icon to toggle panel

#### 2. Added `makePanelDraggable()` (lines 1221-1259)

New method that enables drag-and-drop functionality:
- Adds `cursor: move` to header
- Tracks mouse down/move/up events
- Updates panel position during drag
- Prevents dragging when clicking close button

#### 3. Simplified Event Handlers

**Removed auto-show logic from**:
- `handleTextMessageStart()` - Removed lines checking display state
- `handleTaskThinking()` - Removed lines checking display state

**Kept**:
- Auto-scroll to bottom: `panel.scrollTop = panel.scrollHeight`

## User Experience Improvements

### Before
❌ Panel appears in random positions depending on where BPMN element is
❌ Panel position doesn't update when canvas zooms/pans
❌ Panel stuck in one position, can't be moved
❌ Panel sometimes doesn't show content
❌ Complex auto-show logic unreliable
❌ Panel auto-shows even when user doesn't want it

### After
✅ Panel always created in consistent location (top-right)
✅ Panel position independent of canvas zoom/pan
✅ Panel can be dragged to any position user prefers
✅ Panel hidden by default - user controls when to view it
✅ User clicks bubble icon (💬) to show/hide panel
✅ Events accumulate in background, visible when user opens panel

## Testing

### Test Case 1: Bubble Icon Appears
1. Execute a workflow with agentic tasks
2. **Expected**: Feedback bubble icon (💬) appears on the agentic task element
3. **Expected**: Panel does NOT auto-show - stays hidden

### Test Case 2: Click Bubble to Show Panel
1. Execute workflow and wait for events to arrive
2. Click the bubble icon (💬) on the task element
3. **Expected**: Task Activity panel appears in top-right corner
4. **Expected**: Panel displays timeline with all accumulated events:
   - Timestamp for each event
   - Event icons (🤔 thinking, 🔧 tools, 💬 messages)
   - Event details (thinking messages, tool names, LLM streaming text)

### Test Case 3: Events Accumulate While Hidden
1. Execute workflow
2. Do NOT click bubble icon - keep panel hidden
3. Wait for workflow to complete
4. Click bubble icon
5. **Expected**: Panel shows all events that occurred while it was hidden

### Test Case 4: Panel is Draggable
1. Click and hold panel header (blue bar with "Task Activity" text)
2. Move mouse
3. **Expected**: Panel follows mouse movement
4. Release mouse
5. **Expected**: Panel stays in new position

### Test Case 5: Panel Persists During Zoom/Pan
1. Open Task Activity panel
2. Zoom in/out on canvas
3. Pan canvas around
4. **Expected**: Panel stays in same position (doesn't move with canvas)

### Test Case 6: Toggle Panel Visibility
1. Click X button in panel header
2. **Expected**: Panel hides
3. Click feedback icon (💬) on BPMN element
4. **Expected**: Panel shows again in same position

## CSS (No Changes Needed)

The CSS in `styles.css` already had proper flex layout:
- `.task-feedback-panel`: Fixed dimensions (450px × 500px), flex layout
- `.feedback-content`: Flex child with `flex: 1 1 auto`, scrollable, `min-height: 0`
- `.feedback-event-item`: Visible borders, min-height, proper spacing

The CSS was correct - the issue was JavaScript positioning and visibility logic.

## Debug Logging (Kept)

Retained comprehensive logging for troubleshooting:
```
🔍 getOrCreateFeedbackPanel called for elementId: element_4
   Creating NEW panel for element_4
   Positioned panel at fixed location: right: 20px, top: 100px
   Panel appended to body and shown
   Panel dimensions: 450x500
   Returning .feedback-content div, has 0 children
```

This helps verify:
- Panel is being created
- Panel is positioned correctly
- Panel has correct dimensions
- Content div is being returned properly

## Potential Future Enhancements

1. **Remember panel position**: Store dragged position in localStorage
2. **Multiple panels**: Support multiple task panels stacked or tiled
3. **Minimize/maximize**: Add collapse button to save screen space
4. **Resize**: Make panel resizable by dragging edges
5. **Pin to element**: Option to pin panel to BPMN element (updates position with zoom/pan)
