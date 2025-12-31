# Debugging Runtime Marker Positioning

## Issue Description

Runtime execution markers (✓ checkmarks, ⊘ skip marks, etc.) may appear to become misaligned when:
1. Zooming in on the canvas
2. Panning with Shift+Drag or middle-click
3. Both zooming and panning together

## Expected Behavior

Runtime markers should:
- Move with their parent element at all zoom levels
- Stay in the same relative position to the element (e.g., checkmark at top-right corner)
- Remain visible and correctly positioned after panning
- Persist through any re-renders

## Debugging Steps

### 1. Open Browser Console

Open your browser's developer tools (F12) and go to the Console tab.

### 2. Check Element Structure

After a workflow execution completes, inspect a completed task element:

```javascript
// Find a completed element
const completedElement = document.querySelector('.bpmn-element.completed');
console.log('Element:', completedElement);
console.log('Element transform:', completedElement.getAttribute('transform'));
console.log('Element children:', completedElement.children);

// Find the checkmark
const checkmark = completedElement.querySelector('.completion-mark');
console.log('Checkmark:', checkmark);
console.log('Checkmark x:', checkmark.getAttribute('x'));
console.log('Checkmark y:', checkmark.getAttribute('y'));
console.log('Checkmark parent:', checkmark.parentElement);
```

**Expected output:**
- Checkmark should be a child of the completed element's `<g>` group
- Checkmark x should be "20" and y should be "-20" (relative coordinates)
- Checkmark parent should be the same as completedElement

### 3. Test Zoom and Pan

```javascript
// Before zooming/panning
const element = document.querySelector('.bpmn-element.completed');
const checkmark = element.querySelector('.completion-mark');
console.log('Before - Element:', element.getAttribute('transform'));
console.log('Before - Checkmark position:', checkmark.getAttribute('x'), checkmark.getAttribute('y'));
console.log('Before - Checkmark screen position:', checkmark.getBoundingClientRect());

// Now zoom in and pan manually

// After zooming/panning
console.log('After - Element:', element.getAttribute('transform'));
console.log('After - Checkmark position:', checkmark.getAttribute('x'), checkmark.getAttribute('y'));
console.log('After - Checkmark screen position:', checkmark.getBoundingClientRect());
```

**What to check:**
- Element's transform attribute should NOT change during pan/zoom (it's always `translate(elementX, elementY)`)
- Checkmark's x and y attributes should NOT change (they're relative coordinates)
- Checkmark's screen position (getBoundingClientRect) SHOULD change to reflect zoom/pan
- Checkmark should still be a child of the element

### 4. Check for Re-renders

The app has debugging logs for re-renders. When you zoom/pan, watch the console:

```
🔄 rerenderElements() called
   Current zoom: 1.5
   Current pan: { x: 100, y: 50 }
Stack trace:
```

**If you see this during normal pan/zoom:**
- This means something is triggering an unnecessary re-render
- The re-render code SHOULD preserve markers (we implemented this fix)
- Check if markers are being restored correctly

**If you DON'T see this during pan/zoom:**
- Good! Re-renders should only happen when changing properties or dragging pools
- The issue might be a CSS/SVG rendering problem in your browser

### 5. Manual Marker Test

Create a test marker manually to see if it behaves correctly:

```javascript
// Find an element
const element = document.querySelector('.bpmn-element[data-id]');

// Add a test marker
const testMark = document.createElementNS('http://www.w3.org/2000/svg', 'text');
testMark.setAttribute('class', 'test-mark');
testMark.setAttribute('x', '20');
testMark.setAttribute('y', '-20');
testMark.setAttribute('font-size', '20');
testMark.setAttribute('fill', 'red');
testMark.textContent = '⭐';
element.appendChild(testMark);

// Now zoom/pan and see if the star moves correctly with the element
```

If the test marker moves correctly but the runtime markers don't, there might be an issue with how they're being created.

### 6. Check Main Group Transform

The entire canvas uses a main group transform for zoom/pan:

```javascript
const mainGroup = document.getElementById('mainGroup');
console.log('Main group transform:', mainGroup.getAttribute('transform'));
// Should be something like: translate(100, 50) scale(1.5)
```

This transform is applied to ALL elements equally.

### 7. Browser-Specific Issues

Some browsers have issues with SVG text element transforms. Try:

```javascript
// Force a repaint
const element = document.querySelector('.bpmn-element.completed');
element.style.display = 'none';
setTimeout(() => { element.style.display = ''; }, 10);
```

## Common Issues and Solutions

### Issue 1: Markers disappear when zooming

**Cause:** Re-render is called but marker restoration fails
**Solution:** Check console for restoration logs. Markers should be restored with their original x/y coordinates.

### Issue 2: Markers stay in one place while elements move

**Cause:** Markers might be added to the wrong parent (e.g., connectionsLayer instead of element group)
**Solution:**
```javascript
// Check marker's parent
const checkmark = document.querySelector('.completion-mark');
console.log('Parent element class:', checkmark.parentElement.getAttribute('class'));
// Should be "bpmn-element", NOT "connectionsLayer" or "elementsLayer"
```

### Issue 3: Markers positioned incorrectly after re-render

**Cause:** Coordinates being saved as computed values instead of original relative values
**Solution:** Check the saved coordinates in the restoration log:
```
Restoring 1 marks for element task_1
   - completion-mark at (20, -20)  // ✅ GOOD - relative coordinates
   - completion-mark at (520, 180) // ❌ BAD - absolute screen coordinates
```

### Issue 4: Markers multiply after re-render

**Cause:** Restoration code adding duplicates
**Solution:** The code should check for existing markers before adding. Look for duplicate checkmarks on the same element.

## Fix Verification

After the fix is applied, this should work correctly:

1. Load a workflow
2. Execute it to completion (you should see ✓ checkmarks on completed tasks)
3. Zoom in to 2x (Ctrl+Scroll up)
4. Pan around with Shift+Drag
5. Checkmarks should move with their tasks and stay in the same relative position
6. Zoom back to 1x
7. Checkmarks should still be correctly positioned

## Additional Diagnostics

### Check if events are being listened to properly:

```javascript
// Check for pan start
document.addEventListener('mousedown', (e) => {
    if (e.shiftKey && e.button === 0) {
        console.log('Pan start detected');
    }
});
```

### Monitor transform changes:

```javascript
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'transform') {
            console.log('Transform changed on:', mutation.target.getAttribute('class'));
            console.log('New transform:', mutation.target.getAttribute('transform'));
        }
    });
});

const mainGroup = document.getElementById('mainGroup');
observer.observe(mainGroup, { attributes: true });
```

This will log every time the transform changes, helping you see if unwanted transforms are being applied.

## Contact

If none of these debugging steps reveal the issue, please:
1. Note which browser and version you're using
2. Share console logs from steps above
3. Describe exactly when the misalignment occurs (after zoom? after pan? after both?)
4. Include a screenshot showing the misalignment
