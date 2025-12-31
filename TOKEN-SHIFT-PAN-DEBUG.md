# Token Shift-Pan Debug Guide

## Issue Report

User reports: "When Shift+Panning is done, the tokens don't move and are left out on the side"

## Expected vs Actual Behavior

### Expected (After Fix):
1. Execute workflow → Tokens appear on tasks
2. Hold Shift + Drag canvas → Canvas pans
3. **Tokens should move with canvas** (stay on tasks)

### Actual (Reported Issue):
1. Execute workflow → Tokens appear on tasks
2. Hold Shift + Drag canvas → Canvas pans
3. **Tokens don't move** → Left in original position ❌

## Hypothesis

The token group transform fix should work for all pan operations (regular pan, Shift+pan, middle-mouse pan) because they all call the same `updateTransform()` function which updates `mainGroup`'s transform.

**Possible causes:**

### Cause 1: Browser Cache (Most Likely)
The old JavaScript (with `cx/cy` tokens) is still cached in the browser.

**Solution**: Hard reload
- Chrome/Firefox: `Ctrl+Shift+R` or `Cmd+Shift+R`
- Safari: `Cmd+Option+R`

### Cause 2: Token Created Before Fix Applied
Tokens created with old code (before hard reload) still use `cx/cy`.

**Solution**: After hard reload, execute workflow fresh to create new tokens

### Cause 3: tokensLayer Not Inside mainGroup
If tokensLayer gets appended to root SVG instead of mainGroup, it won't transform.

**Solution**: Check console logs for "appended to mainGroup"

## Debug Steps

### Step 1: Verify Fix is Loaded

1. Hard reload browser (`Ctrl+Shift+R` or `Cmd+Shift+R`)
2. Open Console (F12)
3. Execute a workflow
4. Look for this log:

```
🔵 createToken called: elementId=start_1, offsetIndex=0, colorIndex=0
  ✅ Created tokensLayer and appended to mainGroup (will render on top of all elements)
  ✅ Token group appended to tokensLayer
  Token position: transform=translate(150, 200), r=10
  Token visible in DOM: true
```

**Key indicators:**
- ✅ `Token group appended` (not "Token appended")
- ✅ `transform=translate(...)` (not `cx=... cy=...`)

If you see the OLD logs:
```
❌ Token position: cx=150, cy=200, r=10
```

Then the fix is **NOT loaded** - hard reload again and clear cache.

### Step 2: Inspect DOM Structure

1. Open DevTools (F12)
2. Go to "Elements" or "Inspector" tab
3. Find the SVG structure
4. Verify it looks like this:

```xml
<svg>
  <g id="mainGroup" transform="translate(0, 0) scale(1)">
    <g id="poolsLayer">...</g>
    <g id="connectionsLayer">...</g>
    <g id="elementsLayer">...</g>
    <g id="tokensLayer">  ✅ MUST be inside mainGroup!
      <g transform="translate(350, 200)" class="bpmn-token-group">  ✅ Group, not circle!
        <circle cx="0" cy="0" r="10" class="bpmn-token" />
      </g>
    </g>
  </g>
</svg>
```

**❌ WRONG Structure (Old Code):**
```xml
<svg>
  <g id="mainGroup">...</g>
  <g id="tokensLayer">  ❌ Outside mainGroup!
    <circle cx="350" cy="200" class="bpmn-token" />  ❌ No group wrapper!
  </g>
</svg>
```

### Step 3: Test Panning

1. Execute workflow
2. Wait for tokens to appear
3. **Regular pan test**:
   - Click middle mouse button + drag
   - **Expected**: Tokens move with canvas ✅

4. **Shift+pan test**:
   - Hold Shift
   - Click left mouse button + drag
   - **Expected**: Tokens move with canvas ✅

5. **Watch mainGroup transform**:
   - In DevTools, watch `mainGroup`'s transform attribute
   - Should change as you pan: `translate(100, 50) scale(1)`
   - Tokens should follow automatically

### Step 4: Monitor Transform Changes

Add this to browser console to watch transforms:

```javascript
// Watch mainGroup transform changes
const mainGroup = document.getElementById('mainGroup');
const observer = new MutationObserver((mutations) => {
  mutations.forEach((mutation) => {
    if (mutation.attributeName === 'transform') {
      console.log('mainGroup transform:', mainGroup.getAttribute('transform'));

      // Check if tokens are inside
      const tokensLayer = document.getElementById('tokensLayer');
      console.log('tokensLayer parent:', tokensLayer?.parentElement?.id);
      console.log('Token count:', tokensLayer?.children.length);
    }
  });
});
observer.observe(mainGroup, { attributes: true });
```

**Expected output when panning:**
```
mainGroup transform: translate(0, 0) scale(1)
tokensLayer parent: mainGroup  ✅
Token count: 1

mainGroup transform: translate(50, 30) scale(1)
tokensLayer parent: mainGroup  ✅
Token count: 1

mainGroup transform: translate(100, 60) scale(1)
tokensLayer parent: mainGroup  ✅
Token count: 1
```

## How Pan Should Work

### Pan Mechanism

When you Shift+Drag:

1. `handlePanStart()` sets `isPanning = true`
2. `handlePanMove()` updates `panX` and `panY`:
   ```javascript
   this.panX = e.clientX - this.panStart.x;
   this.panY = e.clientY - this.panStart.y;
   this.updateTransform();
   ```
3. `updateTransform()` updates mainGroup:
   ```javascript
   mainGroup.setAttribute('transform', `translate(${panX}, ${panY}) scale(${zoom})`);
   ```

### Token Transform Cascade

```
mainGroup transform: translate(100, 50) scale(1)
  ↓
tokensLayer (no transform, inherits parent)
  ↓
tokenGroup transform: translate(350, 200)
  ↓
token circle cx=0 cy=0

Final position = (100 + 350, 50 + 200) = (450, 250)
```

If pan changes to `translate(200, 100)`:
```
Final position = (200 + 350, 100 + 200) = (550, 300)
```

Token moves automatically! ✅

## Troubleshooting

### Issue: Tokens Still Don't Move After Hard Reload

**Diagnosis:**
1. Check console for token creation logs
2. Verify `transform=translate(...)` not `cx=...`
3. Inspect DOM - verify group structure

**Possible causes:**
- Service worker caching old JS
- Multiple browser tabs with old version
- Proxy/CDN caching

**Solutions:**
1. Close ALL browser tabs
2. Clear browser cache completely:
   - Chrome: Settings → Privacy → Clear Data → Cached images
3. Disable service workers (DevTools → Application → Service Workers → Unregister)
4. Restart browser
5. Try different browser (Firefox, Safari) to rule out cache

### Issue: Some Tokens Move, Others Don't

**Diagnosis:** Mixed old and new token types

**Cause:** Some tokens created before reload, some after

**Solution:**
1. Clear all tokens (click "Clear Execution")
2. Execute workflow fresh
3. All tokens should be created with new code

### Issue: Tokens Move on Zoom but Not Pan

**Diagnosis:** Transform order issue

**Possible cause:** `scale` before `translate` in transform

**Check:**
```javascript
// Expected:
mainGroup.getAttribute('transform')
// "translate(100, 50) scale(1.5)"  ✅

// Wrong:
// "scale(1.5) translate(100, 50)"  ❌
```

If wrong, the pan is being scaled which causes weird positioning.

**Verify in code** (`app.js` line 2801):
```javascript
`translate(${this.panX}, ${this.panY}) scale(${this.zoom})`
```

This is correct - translate comes BEFORE scale.

### Issue: Tokens Snap to Wrong Position When Panning Stops

**Diagnosis:** Token position being recalculated somewhere

**Possible cause:** Some code is calling `moveToken()` or updating token position

**Check:** Search for any code that might be updating tokens during pan events

## Quick Test Script

Paste this in browser console after executing workflow:

```javascript
// Test pan with token
const testPan = async () => {
  console.log('=== Testing Token Panning ===');

  const mainGroup = document.getElementById('mainGroup');
  const tokensLayer = document.getElementById('tokensLayer');

  console.log('1. Initial state:');
  console.log('  mainGroup transform:', mainGroup.getAttribute('transform'));
  console.log('  tokensLayer parent:', tokensLayer.parentElement.id);
  console.log('  Token count:', tokensLayer.children.length);

  if (tokensLayer.children.length > 0) {
    const token = tokensLayer.children[0];
    console.log('  Token class:', token.getAttribute('class'));
    console.log('  Token transform:', token.getAttribute('transform'));
  }

  // Simulate pan to (100, 100)
  console.log('\n2. Simulating pan to (100, 100)...');
  mainGroup.setAttribute('transform', 'translate(100, 100) scale(1)');

  console.log('  mainGroup transform:', mainGroup.getAttribute('transform'));
  console.log('  ✅ If tokens moved with canvas, test PASSED');
  console.log('  ❌ If tokens stayed in place, fix NOT loaded');

  // Reset
  setTimeout(() => {
    console.log('\n3. Resetting...');
    mainGroup.setAttribute('transform', 'translate(0, 0) scale(1)');
  }, 2000);
};

testPan();
```

**Expected output:**
```
=== Testing Token Panning ===
1. Initial state:
  mainGroup transform: translate(0, 0) scale(1)
  tokensLayer parent: mainGroup  ✅
  Token count: 1
  Token class: bpmn-token-group  ✅
  Token transform: translate(350, 200)  ✅

2. Simulating pan to (100, 100)...
  mainGroup transform: translate(100, 100) scale(1)
  ✅ If tokens moved with canvas, test PASSED

3. Resetting...
```

If tokens **didn't move**, you'll see them stay in their original position while the canvas moves.

## Conclusion

The fix SHOULD work because:

1. ✅ tokensLayer is inside mainGroup
2. ✅ Token groups use transform (not cx/cy)
3. ✅ SVG transform cascade works automatically
4. ✅ All pan operations call same `updateTransform()` function

**Most likely cause of issue:** Browser cache

**Solution:** Hard reload, clear cache, execute workflow fresh

If issue persists after all debugging steps, there may be a different root cause that needs investigation.
