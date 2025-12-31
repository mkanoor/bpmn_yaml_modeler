# Token Zoom/Pan Anchoring Fix

## Issue

When zooming or resetting the view, **tokens were left out and not anchored to their tasks**. Tokens would appear to float away or stay in the wrong position when you:

- Clicked "Reset View" button
- Zoomed in/out using mouse wheel
- Panned the canvas

## Root Cause

### Original Implementation (Broken)

Tokens were created as **SVG circles with absolute `cx` and `cy` coordinates**:

```javascript
// BEFORE (Broken):
const token = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
token.setAttribute('cx', 350);  // Absolute X position
token.setAttribute('cy', 200);  // Absolute Y position
tokensLayer.appendChild(token);
```

**Problem**: Even though `tokensLayer` was inside `mainGroup` (which has zoom/pan transforms), the circle's `cx` and `cy` attributes are **absolute coordinates**. When `mainGroup`'s transform changes:

```xml
<g id="mainGroup" transform="scale(1.5) translate(100, 50)">
  <g id="tokensLayer">
    <circle cx="350" cy="200" />  ❌ Still at absolute 350,200!
  </g>
</g>
```

The token circle stays at absolute coordinates (350, 200) instead of transforming with the canvas.

### Why This Happened

In SVG:
- **Transform attributes** on parent elements affect child elements
- BUT `cx` and `cy` attributes on circles are **not affected** by parent transforms
- They remain at absolute coordinates in the SVG coordinate system

**Example**:
```xml
<!-- mainGroup at zoom=1, pan=0 -->
<g id="mainGroup" transform="translate(0, 0) scale(1)">
  <circle cx="100" cy="100" />  <!-- Shows at 100,100 ✓ -->
</g>

<!-- User zooms to 2x and pans +50,+50 -->
<g id="mainGroup" transform="translate(50, 50) scale(2)">
  <circle cx="100" cy="100" />  <!-- Still at 100,100! ❌ Not zoomed/panned! -->
</g>
```

## The Fix

### New Implementation (Working)

Wrap each token in a **`<g>` group element with a `transform` attribute**:

```javascript
// AFTER (Fixed):
const tokenGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
tokenGroup.setAttribute('transform', `translate(350, 200)`);  // Group positioned
tokenGroup.setAttribute('class', 'bpmn-token-group');
tokenGroup.setAttribute('data-element-id', elementId);

const token = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
token.setAttribute('cx', 0);  // Relative to group origin
token.setAttribute('cy', 0);  // Relative to group origin
token.setAttribute('r', 10);

tokenGroup.appendChild(token);  // Circle inside group
tokensLayer.appendChild(tokenGroup);
```

**Result**:
```xml
<g id="mainGroup" transform="translate(0, 0) scale(1)">
  <g id="tokensLayer">
    <g transform="translate(350, 200)" class="bpmn-token-group">
      <circle cx="0" cy="0" r="10" />  <!-- Relative position -->
    </g>
  </g>
</g>
```

When user zooms/pans:
```xml
<g id="mainGroup" transform="translate(50, 50) scale(2)">
  <g id="tokensLayer">
    <g transform="translate(350, 200)">  <!-- Gets transformed! ✓ -->
      <circle cx="0" cy="0" r="10" />
    </g>
  </g>
</g>
```

The group's transform is **affected by parent transforms**, so the token moves with the canvas!

## Code Changes

### Change 1: Create Token as Group (line 438-462)

**Before:**
```javascript
const token = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
token.setAttribute('cx', x);  // Absolute position
token.setAttribute('cy', y);
```

**After:**
```javascript
const tokenGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
tokenGroup.setAttribute('transform', `translate(${x}, ${y})`);  // Transform attribute
tokenGroup.setAttribute('class', 'bpmn-token-group');
tokenGroup.setAttribute('data-element-id', elementId);

const token = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
token.setAttribute('cx', 0);  // Relative to group
token.setAttribute('cy', 0);
token.setAttribute('r', 10);

tokenGroup.appendChild(token);
```

### Change 2: Append and Store Group (line 461-497)

**Before:**
```javascript
tokensLayer.appendChild(token);  // Append circle directly
this.tokens.get(elementId).push(token);  // Store circle
return token;
```

**After:**
```javascript
tokenGroup.appendChild(token);  // Circle inside group
tokensLayer.appendChild(tokenGroup);  // Append group
this.tokens.get(elementId).push(tokenGroup);  // Store group
return tokenGroup;
```

### Change 3: Animate Transform (line 564-567)

**Before:**
```javascript
token.setAttribute('cx', x);  // Update absolute position
token.setAttribute('cy', y);
```

**After:**
```javascript
token.setAttribute('transform', `translate(${x}, ${y})`);  // Update transform
token.setAttribute('data-element-id', toElementId);
```

## SVG Structure Comparison

### Before (Broken)
```xml
<svg>
  <g id="mainGroup" transform="scale(1) translate(0, 0)">
    <g id="poolsLayer">...</g>
    <g id="connectionsLayer">...</g>
    <g id="elementsLayer">
      <g transform="translate(350, 200)" data-id="task_1">
        <rect ... />
      </g>
    </g>
    <g id="tokensLayer">
      <circle cx="350" cy="200" class="bpmn-token" />  ❌ Absolute position
    </g>
  </g>
</svg>
```

**Problem**: Circle uses `cx/cy` which don't transform with parent.

### After (Fixed)
```xml
<svg>
  <g id="mainGroup" transform="scale(1) translate(0, 0)">
    <g id="poolsLayer">...</g>
    <g id="connectionsLayer">...</g>
    <g id="elementsLayer">
      <g transform="translate(350, 200)" data-id="task_1">
        <rect ... />
      </g>
    </g>
    <g id="tokensLayer">
      <g transform="translate(350, 200)" class="bpmn-token-group">  ✓ Transform
        <circle cx="0" cy="0" r="10" class="bpmn-token" />
      </g>
    </g>
  </g>
</svg>
```

**Solution**: Group uses `transform` which DOES transform with parent.

## How It Works Now

### Scenario 1: Zoom In (2x)

**Before zoom:**
```xml
<g id="mainGroup" transform="scale(1)">
  <g transform="translate(350, 200)">  <!-- Task -->
    <rect />
  </g>
  <g transform="translate(350, 200)">  <!-- Token -->
    <circle />
  </g>
</g>
```
Task at 350,200. Token at 350,200. ✓ Aligned.

**After zoom 2x:**
```xml
<g id="mainGroup" transform="scale(2)">
  <g transform="translate(350, 200)">  <!-- Task -->
    <rect />  <!-- Appears at 700,400 in viewport -->
  </g>
  <g transform="translate(350, 200)">  <!-- Token -->
    <circle />  <!-- Also appears at 700,400! ✓ -->
  </g>
</g>
```
Task scaled to 700,400. Token also scaled to 700,400. ✓ Still aligned!

### Scenario 2: Reset View

**User clicks "Reset View" button:**
```javascript
resetView() {
    this.zoom = 1;
    this.panX = 0;
    this.panY = 0;
    this.updateTransform();  // Updates mainGroup transform
}
```

**Result:**
```xml
<g id="mainGroup" transform="translate(0, 0) scale(1)">
  <!-- All children (including token groups) are now at zoom=1, pan=0 -->
</g>
```

Tokens stay aligned with their elements because they **share the same parent transform**.

### Scenario 3: Pan Canvas

**User pans +100,+100:**
```xml
<g id="mainGroup" transform="translate(100, 100) scale(1)">
  <g transform="translate(350, 200)">  <!-- Task -->
    <rect />  <!-- Appears at 450,300 -->
  </g>
  <g transform="translate(350, 200)">  <!-- Token -->
    <circle />  <!-- Also at 450,300 ✓ -->
  </g>
</g>
```

Both task and token are panned together. ✓ Stay aligned!

## Benefits

### 1. Tokens Always Anchored to Elements ✓
No matter how you zoom, pan, or reset, tokens stay perfectly positioned on their elements.

### 2. No Manual Position Updates Needed ✓
We don't need to:
- Listen for zoom/pan events
- Recalculate token positions
- Update token coordinates manually

The SVG transform cascade handles it automatically!

### 3. Consistent with Element Positioning ✓
Elements use `transform="translate(x, y)"` - now tokens use the same pattern.

### 4. Better Performance ✓
Animating `transform` is hardware-accelerated in modern browsers.
Animating `cx/cy` is not.

## Testing

### Test 1: Token Movement with Zoom
1. Execute workflow
2. Token appears at task
3. Zoom in 2x (mouse wheel or zoom button)
4. **Expected**: Token scales with task, stays centered
5. Token moves to next task
6. **Expected**: Token animates correctly at 2x zoom

### Test 2: Reset View During Execution
1. Execute workflow
2. Zoom in and pan around
3. While tokens are animating, click "Reset View"
4. **Expected**:
   - View resets to zoom=1, pan=0
   - Tokens snap to correct positions on their elements
   - Animation continues smoothly

### Test 3: Zoom Out/In Repeatedly
1. Execute workflow
2. Rapidly zoom out to 0.5x
3. Zoom in to 2x
4. Reset view
5. Repeat while workflow executes
6. **Expected**: Tokens always stay anchored to elements

### Test 4: Multiple Tokens (Parallel Gateway)
1. Execute workflow with parallel gateway
2. Fork creates multiple colored tokens
3. Zoom/pan while tokens are on different paths
4. **Expected**: All tokens (blue, red, green) stay on their elements

## Console Verification

### What You Should See:

```
🔵 createToken called: elementId=task_1, offsetIndex=0, colorIndex=0
  ✅ Token group appended to tokensLayer
  🔵 BLUE token created at element: task_1 (1 total)
  Token position: transform=translate(350, 200), r=10
  Token visible in DOM: true

🔵 Moving token from task_1 to task_2
(Token animates via transform updates)
🔵 Token arrived at task_2
```

**Key indicator**: `Token position: transform=translate(...)` instead of `cx=... cy=...`

## Backward Compatibility

This change is **fully backward compatible**:

1. ✅ Token creation API unchanged (same function signature)
2. ✅ Token animation behavior unchanged (still 800ms smooth animation)
3. ✅ Token storage unchanged (`this.tokens` Map still works)
4. ✅ Token colors unchanged (same color scheme)
5. ✅ Token removal unchanged (`removeToken()` still works)

The only difference is the internal implementation (group vs circle).

## Summary

**Problem**: Tokens had absolute `cx/cy` coordinates, didn't transform with canvas zoom/pan

**Solution**: Wrap tokens in `<g>` groups with `transform` attributes

**Result**: Tokens now perfectly anchored to elements through all zoom/pan operations

**Files Changed**: `agui-client.js` - 3 functions updated
- `createToken()` - Create group instead of standalone circle
- `moveToken()` - Animate transform instead of cx/cy
- Storage/return - Store and return group instead of circle

**Benefit**: Tokens stay locked to their elements no matter what! 🎯
