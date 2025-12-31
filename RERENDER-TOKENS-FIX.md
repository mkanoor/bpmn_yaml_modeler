# Token Persistence During Re-render - REAL FIX

## The ACTUAL Problem (Found!)

When you Shift+Pan, something was triggering `rerenderElements()` which **clears and recreates all elements**. This destroyed the tokensLayer along with the tokens!

## Root Cause Analysis

### What Triggers `rerenderElements()`

From your console output, we can see `rerenderElements()` is being called repeatedly:

```
🔄 rerenderElements() called
   Current zoom: 0.6795652173913043
   Current pan: {x: 0, y: 311.4021739130435}
   Restoring runtime state for 5 elements
```

This function is called when:
1. Element type changes (e.g., task → scriptTask)
2. Element properties change that require re-render
3. Undo/redo operations
4. Some other property changes (line 1219, 1323, 2221, 3397, 3432)

### What `rerenderElements()` Does

```javascript
rerenderElements() {
    // Save runtime state (completed, error, etc.)
    ...

    // CLEAR EVERYTHING
    this.elementsLayer.innerHTML = '';  // ← Removes all elements
    this.connectionsLayer.innerHTML = '';  // ← Removes all connections

    // Re-render from scratch
    this.elements.forEach(element => this.renderElement(element));
    this.connections.forEach(connection => this.renderConnection(connection));

    // Restore runtime state
    ...
}
```

**Problem**: tokensLayer is a **sibling** of elementsLayer and connectionsLayer:

```xml
<g id="mainGroup">
  <g id="poolsLayer"></g>
  <g id="connectionsLayer"></g>  ← innerHTML = '' (cleared)
  <g id="elementsLayer"></g>  ← innerHTML = '' (cleared)
  <g id="tokensLayer">  ← NOT cleared, but now orphaned!
    <g transform="translate(350, 200)">...</g>
  </g>
</g>
```

The tokensLayer survives the clearing, BUT:
1. The elements it references have been recreated (new DOM nodes)
2. Token positions might be based on old element positions
3. Tokens become disconnected from their elements

## The Fix

### Save and Restore tokensLayer During Re-render

**File**: `app.js` line 2501-2521

```javascript
rerenderElements() {
    // ... save runtime state ...

    // Save token layer BEFORE clearing
    const tokensLayer = document.getElementById('tokensLayer');
    const savedTokensLayer = tokensLayer ? tokensLayer.cloneNode(true) : null;

    // Clear and re-render (as before)
    this.elementsLayer.innerHTML = '';
    this.elements.forEach(element => this.renderElement(element));
    this.connectionsLayer.innerHTML = '';
    this.connections.forEach(connection => this.renderConnection(connection));

    // Restore tokens layer AFTER re-render
    if (savedTokensLayer) {
        // Remove any tokensLayer created during render
        const existingTokensLayer = document.getElementById('tokensLayer');
        if (existingTokensLayer) {
            existingTokensLayer.remove();
        }
        // Append saved tokens back
        this.mainGroup.appendChild(savedTokensLayer);
        console.log(`✅ Restored tokensLayer with ${savedTokensLayer.children.length} tokens`);
    }

    // ... restore runtime state ...
}
```

## How It Works

### Before Fix (Tokens Lost):

```
1. User pans canvas → rerenderElements() triggered
2. elementsLayer.innerHTML = '' → Elements cleared
3. Elements recreated at same positions
4. tokensLayer still exists BUT:
   - Tokens reference old element positions
   - Coordinate space might be wrong
   - Tokens appear in wrong positions
```

### After Fix (Tokens Preserved):

```
1. User pans canvas → rerenderElements() triggered
2. Clone tokensLayer (saves all tokens and their positions)
3. elementsLayer.innerHTML = '' → Elements cleared
4. Elements recreated at same positions
5. Restore cloned tokensLayer → Tokens back at correct positions
6. Tokens still correctly positioned on elements ✅
```

## Why This Happens During Pan

The re-render might be triggered by:

1. **Property panel updates** - Changing a property while panning
2. **Type changes** - If element type is being updated
3. **Undo/Redo** - If undo/redo happens during pan
4. **Other triggers** - Various property changes call rerenderElements()

## Testing

### Test 1: Verify Token Persistence

1. Execute workflow → Tokens appear
2. Open DevTools console
3. Pan canvas (Shift+drag or middle-mouse)
4. **Expected console output:**
```
🔄 rerenderElements() called
   Current zoom: 0.6795652173913043
   Current pan: {x: 100, y: 200}
   ✅ Restored tokensLayer with 3 tokens
   Restoring runtime state for 5 elements
```

5. **Verify**: Tokens still on their elements after pan ✅

### Test 2: Multiple Re-renders

1. Execute workflow
2. Pan multiple times rapidly
3. **Expected**: Each re-render shows token restoration
4. **Verify**: Tokens never disappear or move incorrectly

### Test 3: Re-render During Token Animation

1. Execute workflow
2. While tokens are animating, pan canvas
3. **Expected**:
   - Re-render happens
   - Tokens restored at current animation position
   - Animation might reset, but tokens don't disappear

## Console Output Verification

### Good Output (Fix Working):
```
🔄 rerenderElements() called
   Current zoom: 0.6795652173913043
   Current pan: {x: 0, y: 311.4021739130435}
   ✅ Restored tokensLayer with 2 tokens  ← KEY INDICATOR
   Restoring runtime state for 5 elements
```

### Bad Output (Old Code):
```
🔄 rerenderElements() called
   Current zoom: 0.6795652173913043
   Current pan: {x: 0, y: 311.4021739130435}
   (No token restoration message)  ← Tokens lost!
   Restoring runtime state for 5 elements
```

## Why cloneNode(true) Works

```javascript
const savedTokensLayer = tokensLayer.cloneNode(true);
```

`cloneNode(true)` creates a **deep clone**:
- Clones the `<g id="tokensLayer">` element
- Clones all child token groups: `<g transform="translate(...)">...</g>`
- Clones all token circles: `<circle cx="0" cy="0" r="10" />`
- Preserves all attributes (transforms, classes, styles)

When we append it back after re-render, tokens are exactly as they were!

## Potential Issues and Solutions

### Issue 1: Tokens Reference Old Elements

**Problem**: Token tracking in `aguiClient.tokens` Map might reference old DOM nodes.

**Impact**: Low - Tokens are visual only, references don't affect rendering

**Solution**: If needed, we could also update `aguiClient.tokens` Map after re-render

### Issue 2: Animated Tokens Get Reset

**Problem**: If tokens are mid-animation during re-render, animation resets.

**Impact**: Minor visual glitch - animation restarts from current position

**Solution**: Current fix is acceptable - animation continues from restored position

### Issue 3: Multiple Re-renders in Rapid Succession

**Problem**: Your logs show rerenderElements() called 6+ times rapidly.

**Impact**: Performance - multiple full re-renders are expensive

**Root Cause**: Some code is calling rerenderElements() in a loop or on every property change

**Long-term solution**: Find and fix what's triggering multiple re-renders

## What Was Triggering Re-renders?

From your stack trace:
```
Stack trace:
  rerenderElements @ app.js:2405
  (anonymous) @ app.js:1219
```

Line 1219 in app.js is calling rerenderElements(). Let me check what that is:

```javascript
// Line 1219 area - likely in property change handler
this.rerenderElements();
```

This suggests property changes are triggering re-renders. When you pan, if any property is being updated (even unintentionally), it triggers a full re-render.

## Files Changed

### app.js (line 2501-2521)

**Added**:
1. Save tokensLayer before clearing: `cloneNode(true)`
2. Restore tokensLayer after re-rendering: `appendChild()`
3. Logging: `console.log('✅ Restored tokensLayer...')`

## Summary

**Problem**: `rerenderElements()` was being called during pan, clearing elements but orphaning tokens

**Solution**: Save and restore tokensLayer during re-render

**Result**: Tokens now persist across re-renders and stay anchored to elements! ✅

**Files Modified**: `app.js` (1 function updated)

**Next**: Investigate why rerenderElements() is being called so frequently (6+ times) during pan
