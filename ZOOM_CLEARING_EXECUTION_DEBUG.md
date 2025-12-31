# Zoom Clearing Execution State - Debug Investigation

## Problem

When zooming in/out on the BPMN canvas, runtime execution indicators (checkmarks ✓, skip marks ⊘, error marks ⚠, and active states) are being cleared. This should only happen when the "Clear Execution" button is clicked.

## Root Cause Analysis

### How Execution Indicators Work

1. **Backend Sends Events**: `agui_server.py` broadcasts WebSocket events like:
   - `element.activated` - Sets element active
   - `element.completed` - Adds green checkmark ✓
   - `task.error` - Adds error mark ⚠

2. **Frontend Adds Visual Indicators**: `agui-client.js` handles these events:
   ```javascript
   markElementComplete(elementId) {
       const element = document.querySelector(`[data-id="${elementId}"]`);
       element.classList.add('completed');

       // Add green checkmark as SVG <text> element
       const checkmark = document.createElementNS('http://www.w3.org/2000/svg', 'text');
       checkmark.setAttribute('class', 'completion-mark');
       element.appendChild(checkmark);  // ← Dynamically added to DOM
   }
   ```

3. **Indicators Not Stored in Data Model**: The checkmarks, skip marks, and classes are added ONLY to the DOM, not to the underlying `this.elements` array in `app.js`.

### Why They Get Cleared

In `app.js`, there are functions that **clear and re-render** all elements:

1. **`rerenderAll()`** (lines 2383-2404):
   ```javascript
   rerenderAll() {
       // Clear DOM - THIS REMOVES ALL EXECUTION INDICATORS!
       this.poolsLayer.innerHTML = '';
       this.elementsLayer.innerHTML = '';
       this.connectionsLayer.innerHTML = '';

       // Re-render from data model (which doesn't have execution state)
       this.elements.forEach(element => this.renderElement(element));
   }
   ```

2. **`rerenderElements()`** (lines 1853-1863):
   ```javascript
   rerenderElements() {
       this.elementsLayer.innerHTML = '';  // Wipes DOM including indicators
       this.elements.forEach(element => this.renderElement(element));
   }
   ```

When `innerHTML = ''` is called, it **destroys all DOM elements**, including:
- The `<g>` elements containing BPMN shapes
- Any child elements added by `agui-client.js` (checkmarks, etc.)
- CSS classes like `.completed`, `.active`, `.error`

Then `renderElement()` creates **fresh new `<g>` elements** from the data model, which has no knowledge of execution state.

### Current Hypothesis

Zoom operations (`setZoom()`, `handleWheel()`) themselves do NOT trigger re-rendering:
```javascript
setZoom(zoom) {
    this.zoom = Math.max(0.1, Math.min(3, zoom));
    this.updateTransform();  // Only applies SVG transform, no DOM changes
}

updateTransform() {
    this.mainGroup.setAttribute('transform',
        `translate(${this.panX}, ${this.panY}) scale(${this.zoom})`);
}
```

**Something else must be triggering `rerenderAll()` or `rerenderElements()` during/after zoom.**

Possible culprits:
1. Keyboard shortcuts (Ctrl+Z for undo) accidentally pressed while zooming
2. Mouse events triggering unexpected handlers
3. Some other code path we haven't identified yet

## Debug Logging Added

Added comprehensive logging to identify WHEN re-rendering happens:

### `app.js` Changes

1. **`rerenderAll()` logging** (lines 2384-2386):
   ```javascript
   rerenderAll() {
       console.log('🔄 rerenderAll() called');
       console.trace('Stack trace:');
       // ... rest of function
   }
   ```

2. **`rerenderElements()` logging** (lines 1854-1856):
   ```javascript
   rerenderElements() {
       console.log('🔄 rerenderElements() called');
       console.trace('Stack trace:');
       // ... rest of function
   }
   ```

## How to Debug

### Test Steps

1. **Open the BPMN modeler in browser** (http://localhost:5500)
2. **Open browser DevTools** (F12) and go to Console tab
3. **Execute a workflow** that shows execution indicators (run any workflow with tasks)
4. **Verify indicators appear**: checkmarks ✓, active glow, etc.
5. **Zoom in/out** using:
   - Mouse wheel
   - Zoom buttons (+/-)
   - Keyboard shortcuts if any
6. **Watch the console** for these messages:
   ```
   🔄 rerenderAll() called
   Stack trace:
   ```
   or
   ```
   🔄 rerenderElements() called
   Stack trace:
   ```

### Expected Results

**If zoom is NOT the problem:**
- No `🔄 rerenderAll()` or `🔄 rerenderElements()` messages appear during zoom
- Execution indicators remain visible
- Need to investigate other causes

**If zoom IS triggering re-render:**
- `🔄` messages appear when zooming
- Stack trace shows the exact code path that triggered re-rendering
- Can identify and fix the specific trigger

### Example Stack Trace

If undo/redo is being triggered:
```
🔄 rerenderAll() called
Stack trace:
    rerenderAll @ app.js:2385
    restoreState @ app.js:2380
    undo @ app.js:2331
    keydown event handler @ app.js:91
```

This would tell us that Ctrl+Z (undo) is being triggered during zoom.

## Potential Solutions

Once we identify the trigger, we can apply one of these solutions:

### Solution 1: Prevent Accidental Triggers
If keyboard shortcuts are the issue, prevent them during zoom/pan:
```javascript
document.addEventListener('keydown', (e) => {
    // Don't allow undo/redo while zooming or panning
    if (this.isPanning || this.isZooming) {
        return;
    }

    if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        this.undo();
    }
});
```

### Solution 2: Preserve Execution State
Store execution state in data model so it survives re-rendering:
```javascript
// In app.js, add execution state to element data
element.executionState = {
    active: false,
    completed: false,
    error: false,
    skipped: false
};

// In renderElement(), restore execution state
renderElement(element) {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    // ... create element

    // Restore execution state if present
    if (element.executionState) {
        if (element.executionState.completed) {
            g.classList.add('completed');
            // Add checkmark
        }
        // ... restore other states
    }
}
```

### Solution 3: Don't Clear Execution Indicators During Re-render
Modify `rerenderAll()` to preserve execution indicators:
```javascript
rerenderAll() {
    // Save execution state from DOM before clearing
    const executionState = new Map();
    document.querySelectorAll('.bpmn-element[data-id]').forEach(el => {
        const id = el.getAttribute('data-id');
        executionState.set(id, {
            classes: Array.from(el.classList),
            marks: el.querySelectorAll('.completion-mark, .skip-mark, .error-mark')
        });
    });

    // Clear and re-render
    this.elementsLayer.innerHTML = '';
    this.elements.forEach(element => this.renderElement(element));

    // Restore execution state
    executionState.forEach((state, id) => {
        const element = document.querySelector(`[data-id="${id}"]`);
        if (element) {
            state.classes.forEach(cls => element.classList.add(cls));
            state.marks.forEach(mark => element.appendChild(mark.cloneNode(true)));
        }
    });
}
```

## Next Steps

1. **User tests with debug logging** to identify the trigger
2. **Share console output** showing when/why re-render is called
3. **Choose and implement** appropriate solution based on findings
