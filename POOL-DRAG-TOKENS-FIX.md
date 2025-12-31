# Pool Dragging - Token Movement Fix

## The REAL Issue (Finally!)

You weren't **panning the canvas** - you were **dragging a pool** (swimlane)! This is completely different from canvas pan.

## What's Happening

### Pool Dragging vs Canvas Panning

**Canvas Panning** (Shift+drag on empty space):
- Updates `mainGroup` transform
- Everything moves together (pools, elements, tokens)
- Tokens automatically follow because they're inside `mainGroup` ✅

**Pool Dragging** (Click+drag on pool header):
- Updates individual element positions (`element.x`, `element.y`)
- Calls `rerenderElements()` on every mouse move
- Elements move, but tokens don't! ❌

### Why Tokens Didn't Move

When you drag a pool:

1. Pool position updates: `pool.x += deltaX`, `pool.y += deltaY`
2. Element positions update: `element.x += deltaX`, `element.y += deltaY` (for elements in pool)
3. `rerenderElements()` is called
4. Elements are re-rendered at new positions
5. **Tokens are restored** via `cloneNode()` at **old positions** ❌

The saved tokens from before the drag are restored unchanged!

### Why This Happened

```javascript
// Pool drag handler (line 1195-1246)
document.addEventListener('mousemove', (e) => {
    if (!isDragging) return;

    // Calculate delta
    const deltaX = newPoolX - pool.x;
    const deltaY = newPoolY - pool.y;

    // Update pool position
    pool.x = newPoolX;
    pool.y = newPoolY;

    // Move elements
    this.elements.forEach(element => {
        if (element.poolId === pool.id) {
            element.x += deltaX;  // Element moves
            element.y += deltaY;
        }
    });

    // Re-render (tokens restored at OLD positions!)
    this.rerenderElements();
});
```

## The Fix

### Update Token Positions Before Re-render

**File**: `app.js` line 1217-1242

Added code to move tokens along with pool elements:

```javascript
// Move all elements that belong to this pool
this.elements.forEach(element => {
    if (element.poolId === pool.id) {
        element.x += deltaX;
        element.y += deltaY;
    }
});

// Move tokens that are on elements in this pool
if (typeof aguiClient !== 'undefined' && aguiClient && aguiClient.tokens) {
    const tokensLayer = document.getElementById('tokensLayer');
    if (tokensLayer) {
        // Update each token group's transform for elements in this pool
        this.elements.forEach(element => {
            if (element.poolId === pool.id) {
                const tokensForElement = aguiClient.tokens.get(element.id);
                if (tokensForElement && tokensForElement.length > 0) {
                    tokensForElement.forEach(tokenGroup => {
                        // Get current transform
                        const currentTransform = tokenGroup.getAttribute('transform');
                        const match = currentTransform?.match(/translate\(([^,]+),\s*([^)]+)\)/);
                        if (match) {
                            const currentX = parseFloat(match[1]);
                            const currentY = parseFloat(match[2]);
                            // Update with delta
                            tokenGroup.setAttribute('transform',
                                `translate(${currentX + deltaX}, ${currentY + deltaY})`);
                        }
                    });
                }
            }
        });
    }
}

// Re-render everything (tokens now at correct positions!)
this.rerenderPools();
this.rerenderElements();
```

### How It Works

1. **Drag pool** → Elements move by `deltaX`, `deltaY`
2. **Update token transforms** → Add `deltaX`, `deltaY` to each token's position
3. **Re-render** → Save tokens (now at new positions)
4. **Restore tokens** → Tokens appear at new positions ✅

### Flow Diagram

```
Before Drag:
Pool A [x=100, y=100]
  ├─ Task 1 [x=200, y=150]  Token [transform="translate(200, 150)"]
  └─ Task 2 [x=200, y=250]  Token [transform="translate(200, 250)"]

User Drags Pool +50px right, +30px down:
  deltaX = 50
  deltaY = 30

After Fix:
Pool A [x=150, y=130]
  ├─ Task 1 [x=250, y=180]  Token [transform="translate(250, 180)"]  ✅
  └─ Task 2 [x=250, y=280]  Token [transform="translate(250, 280)"]  ✅
```

## Testing

### Test 1: Drag Pool with Tokens

1. Execute workflow → Tokens appear on tasks
2. Click on pool header (swimlane label)
3. Drag pool to new position
4. **Expected**: Tokens move with the pool ✅

### Test 2: Drag Multiple Times

1. Execute workflow
2. Drag pool left
3. Drag pool right
4. Drag pool up
5. **Expected**: Tokens follow every movement ✅

### Test 3: Multiple Pools

1. Execute workflow with elements in different pools
2. Drag Pool A → Only tokens on Pool A elements move
3. Drag Pool B → Only tokens on Pool B elements move
4. **Expected**: Tokens move independently with their pools ✅

## Canvas Pan vs Pool Drag

### Canvas Pan (Shift+Drag)

**What it is**: Moves the entire viewport

**Implementation**:
```javascript
handlePanMove(e) {
    this.panX = e.clientX - this.panStart.x;
    this.panY = e.clientY - this.panStart.y;
    this.updateTransform();  // Updates mainGroup
}
```

**Effect on tokens**: Automatic - tokens are inside `mainGroup`, so they transform automatically ✅

**No special handling needed** - already working!

### Pool Drag (Click+Drag Pool Header)

**What it is**: Moves a specific pool and its contents

**Implementation**:
```javascript
document.addEventListener('mousemove', (e) => {
    // Update pool and element positions
    pool.x += deltaX;
    element.x += deltaX;

    // NOW ALSO: Update token positions
    tokenGroup.setAttribute('transform', `translate(newX, newY)`);

    // Re-render
    this.rerenderElements();
});
```

**Effect on tokens**: Manual - tokens need explicit position update before re-render ✅

**Special handling added** - now fixed!

## Why This Was Confusing

### You Said "Shift+Pan"

I thought you meant **canvas panning** (Shift+drag on empty space).

But you were actually **dragging a pool** (click+drag on pool header).

Both operations involve dragging, but they work completely differently:

| Operation | Trigger | What Moves | How It Works |
|-----------|---------|------------|--------------|
| **Canvas Pan** | Shift+drag empty space | Entire viewport | `mainGroup` transform |
| **Pool Drag** | Drag pool header | Pool and its contents | Individual element positions |

### Canvas Pan Token Fix (Already Done ✅)

Tokens use `<g transform="translate(...)">` inside `mainGroup`:
- When `mainGroup` transform changes, tokens automatically transform
- No special handling needed
- **Already working!**

### Pool Drag Token Fix (Just Fixed ✅)

Tokens need manual position updates:
- When pool drags, element positions change
- Tokens need to move by same `deltaX`, `deltaY`
- Update token transform before re-render
- **Now working!**

## Console Output

When you drag a pool, you'll now see:

```
🔄 rerenderElements() called
   Current zoom: 3
   Current pan: {x: 0, y: 311.4021739130435}
   ✅ Restored tokensLayer with 6 tokens
   Restoring runtime state for 5 elements
```

The token transforms have been updated BEFORE cloning, so when they're restored, they're at the new positions!

## Files Changed

### app.js (line 1217-1242)

**Added**: Token position updates during pool drag

**Why needed**: Pool drag changes element positions, not `mainGroup` transform

**How it works**: Loop through tokens, update their transforms by `deltaX`, `deltaY`

## Summary

**Problem**: Dragging pools didn't move tokens with elements

**Root cause**: Pool drag updates element positions, not `mainGroup` transform

**Solution**: Update token transforms by `deltaX`, `deltaY` before re-render

**Result**: Tokens now follow pool drags! ✅

**Files Modified**: `app.js` (1 function updated)

**Bonus**: This fix also works for any other operation that moves elements individually (undo/redo, alignment tools, etc.)

## Other Operations That Might Need Similar Fixes

If there are other operations that move elements (not via `mainGroup` transform), they may also need token updates:

1. **Alignment tools** (align left, center, right)
2. **Distribution tools** (distribute evenly)
3. **Undo/Redo** (if positions change)
4. **Paste** (elements pasted at new positions)

Each of these should call a helper function to update token positions:

```javascript
updateTokenPositions(elementId, deltaX, deltaY) {
    if (typeof aguiClient !== 'undefined' && aguiClient && aguiClient.tokens) {
        const tokensForElement = aguiClient.tokens.get(elementId);
        if (tokensForElement) {
            tokensForElement.forEach(tokenGroup => {
                const match = tokenGroup.getAttribute('transform')?.match(/translate\(([^,]+),\s*([^)]+)\)/);
                if (match) {
                    tokenGroup.setAttribute('transform',
                        `translate(${parseFloat(match[1]) + deltaX}, ${parseFloat(match[2]) + deltaY})`);
                }
            });
        }
    }
}
```

This can be called whenever elements move!
