# Boundary Event Debugging Guide

## Issue
Boundary events are not appearing on the canvas when clicking on tasks after entering attachment mode.

## Debug Logging Added

I've added comprehensive console logging throughout the entire boundary event attachment flow to help identify where the issue is occurring.

### How to Debug

1. **Open the BPMN Modeler in your browser**
2. **Open Developer Tools** (F12 or right-click → Inspect)
3. **Go to the Console tab**
4. **Try to attach a boundary event:**
   - Click on a boundary event in the palette (e.g., "30s Timeout")
   - Click on a task element in the canvas

### Expected Console Output

If everything is working correctly, you should see this sequence:

```
🎯 Boundary event mode - handling click
   Click target: <svg element>
   Click target class: ...
   Checking element: rect element_xyz
   Found element with data-id: element_xyz
   ✅ Element is a task! Attaching boundary event...

📎 attachBoundaryEvent called with taskId: element_xyz
   Task found: My Task (type: userTask)
   Task position: x=400, y=300
   Boundary position calculated: x=445, y=275
   Creating boundary event of type: timerBoundaryEvent

🎨 renderElement called for: 30s Timeout (type: timerBoundaryEvent, id: element_abc)
   Creating shape for timerBoundaryEvent...
   🎨 Rendering boundary event: timerBoundaryEvent
      Color: #f39c12
      Added outer circle
      Added inner circle
      Added icon
      Added text label: 30s Timeout
   ✅ Boundary event shape created
   Adding 4 connection points
   Appending element to elementsLayer
✅ Element rendered successfully: 30s Timeout

✅ Boundary event created with ID: element_abc
   Boundary event object: {...}
✅ Attached timerBoundaryEvent to task My Task
```

### What to Check

Look for where the console output stops or shows an error:

#### 1. **Boundary Event Mode Not Entering**
If you don't see:
```
🎯 Boundary event mode - handling click
```

**Problem**: Click handler not being called or boundary event mode not set
**Check**: Did you click the palette item? Is there a purple hint message at the top?

#### 2. **Element Not Found**
If you see:
```
❌ No task found - cancelling boundary event mode
```

**Problem**: Click is not hitting a task element
**Check**: The "Checking element" logs - is it finding elements with data-id?

#### 3. **Element Not Recognized as Task**
If you see:
```
❌ Element is not a task - type check failed
   Element details: exclusiveGateway
```

**Problem**: You clicked on a non-task element (gateway, event, etc.)
**Solution**: Only tasks can have boundary events - click on a task box

#### 4. **Task Not Found in Array**
If you see:
```
❌ Task not found: element_xyz
```

**Problem**: Task ID doesn't exist in elements array
**Check**: Data corruption or race condition

#### 5. **Rendering Failure**
If you see attachBoundaryEvent logs but NO renderElement logs:

**Problem**: `addElement` or `renderElement` is failing silently
**Check**: Browser console for JavaScript errors

#### 6. **Shape Not Created**
If you see renderElement but NO "Rendering boundary event" logs:

**Problem**: The switch statement in createShape is not matching the boundary event type
**Check**: Is the element.type exactly "timerBoundaryEvent" (case-sensitive)?

#### 7. **SVG Not Appended**
If all logs appear but boundary event still not visible:

**Problem**: SVG rendering issue or z-index problem
**Check**:
- Inspect the DOM - is the SVG element there?
- Is it positioned off-screen (check x, y coordinates)?
- Is it hidden behind another element?

## Common Issues

### Issue: Clicked element is not a task
**Symptom**: You see "Element is not a task - type check failed"
**Solution**: Make sure you're clicking on a task box (blue rounded rectangle), not a gateway (diamond) or event (circle)

### Issue: Click not registering
**Symptom**: No console logs at all when clicking
**Solution**:
- Make sure you clicked the boundary event palette item first (purple hint should appear)
- Try clicking in a different part of the task (center vs edge)
- Check if another element is covering the task

### Issue: Boundary event created but invisible
**Symptom**: All logs show success but nothing visible on canvas
**Solution**:
1. Use browser DevTools → Elements tab
2. Search for the boundary event ID (e.g., "element_abc")
3. Check the `transform` attribute - coordinates might be way off screen
4. Check if `fill` or `stroke` colors are set correctly

## Quick Test Workflow

1. Load the modeler
2. Add a User Task to the canvas (drag from palette)
3. Click "30s Timeout" in the Boundary Events palette section
4. You should see purple hint: "Click on a task to attach 30s Timeout"
5. Click the center of the User Task box
6. Check console for the log sequence above
7. A small orange dashed circle should appear on the top-right corner of the task

## Report Format

If the issue persists, please provide:
1. **Full console output** (copy/paste all logs)
2. **Screenshot** of the canvas showing where you clicked
3. **Browser** and version (Chrome 120, Firefox 115, etc.)
4. **Element type** you're trying to attach to (userTask, serviceTask, etc.)

This will help pinpoint exactly where the attachment flow is breaking.
