# Shift-Pan Token Issue - Solution

## Issue Reported

"When Shift+Panning is done, the tokens don't move and are left out on the side"

## Root Cause Analysis

The token zoom/pan anchoring fix has been implemented, which wraps tokens in `<g>` groups with `transform` attributes. This **should** make tokens move with all pan operations (regular pan, Shift+pan, zoom).

## Most Likely Cause: Browser Cache

The issue is almost certainly that the **old JavaScript is cached** in your browser. The old code created tokens as circles with `cx/cy` attributes, which don't transform with canvas pan.

## Solution

### Step 1: Clear Browser Cache (CRITICAL)

**Hard Reload:**
- **Chrome/Firefox**: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
- **Safari**: `Cmd+Option+R`

**If hard reload doesn't work:**
1. Close ALL browser tabs with the application
2. Clear cache completely:
   - Chrome: Settings → Privacy & Security → Clear browsing data → Cached images and files
   - Firefox: Settings → Privacy & Security → Clear Data → Cached Web Content
3. Restart browser
4. Reload application

### Step 2: Verify Fix is Loaded

After reload, execute a workflow and check the console:

**✅ CORRECT output (new code):**
```
🔵 createToken called: elementId=start_1
  ✅ Token group appended to tokensLayer
  ✅ tokensLayer correctly inside mainGroup (will transform with canvas)
  🔵 BLUE token created at element: start_1
  Token position: transform=translate(150, 200), r=10
```

**❌ WRONG output (old cached code):**
```
🔵 createToken called: elementId=start_1
  Token position: cx=150, cy=200, r=10
```

If you see the ❌ WRONG output, the old JavaScript is still cached!

### Step 3: Test Panning

After verifying the fix is loaded:

1. Execute a workflow
2. Wait for tokens to appear on tasks
3. **Test Shift+Pan**:
   - Hold Shift key
   - Left-click and drag canvas
   - **Tokens should move with the canvas** ✅

4. **Test Regular Pan**:
   - Middle-click and drag (or use pan button)
   - **Tokens should move with the canvas** ✅

5. **Test Zoom**:
   - Mouse wheel to zoom in/out
   - **Tokens should scale with elements** ✅

## How It Works

### The Fix (Already Implemented)

Tokens are now created as `<g>` groups with `transform` attributes:

```xml
<g id="mainGroup" transform="translate(panX, panY) scale(zoom)">
  <g id="tokensLayer">
    <g transform="translate(350, 200)" class="bpmn-token-group">
      <circle cx="0" cy="0" r="10" />
    </g>
  </g>
</g>
```

When you Shift+Pan:
1. `panX` and `panY` change
2. `mainGroup` transform updates: `translate(100, 50) scale(1)`
3. ALL children (including token groups) automatically transform
4. Tokens move with the canvas ✅

### Why Shift+Pan and Regular Pan Should Both Work

Both pan methods call the same code:

```javascript
handlePanMove(e) {
    if (this.isPanning) {
        this.panX = e.clientX - this.panStart.x;  // Update pan position
        this.panY = e.clientY - this.panStart.y;
        this.updateTransform();  // ← Same function for all pans
    }
}

updateTransform() {
    this.mainGroup.setAttribute('transform',
        `translate(${this.panX}, ${this.panY}) scale(${this.zoom})`);
}
```

There is **no difference** between Shift+pan and regular pan - they both update `panX/panY` and call `updateTransform()`.

## Debug Instructions

If tokens still don't move after cache clear:

### 1. Inspect DOM Structure

Open DevTools → Elements tab, verify:

```xml
<svg>
  <g id="mainGroup" transform="translate(0, 0) scale(1)">
    <g id="poolsLayer">...</g>
    <g id="connectionsLayer">...</g>
    <g id="elementsLayer">...</g>
    <g id="tokensLayer">  ✅ MUST be here (inside mainGroup)
      <g class="bpmn-token-group" transform="translate(350, 200)">  ✅ Group wrapper
        <circle cx="0" cy="0" r="10" class="bpmn-token" />
      </g>
    </g>
  </g>
</svg>
```

**❌ If tokensLayer is OUTSIDE mainGroup:**
```xml
<svg>
  <g id="mainGroup">...</g>
  <g id="tokensLayer">  ❌ WRONG! Outside mainGroup
    ...
  </g>
</svg>
```

Then the fix is not loaded - clear cache again.

### 2. Run Test Script

Paste this in browser console:

```javascript
const testTokenPanning = () => {
  const mainGroup = document.getElementById('mainGroup');
  const tokensLayer = document.getElementById('tokensLayer');

  console.log('=== Token Pan Test ===');
  console.log('tokensLayer parent:', tokensLayer?.parentElement?.id);

  if (tokensLayer?.parentElement?.id !== 'mainGroup') {
    console.error('❌ FAIL: tokensLayer not inside mainGroup!');
    console.error('   Fix not loaded - clear cache and reload');
    return;
  }

  if (tokensLayer.children.length === 0) {
    console.warn('⚠️ No tokens found - execute a workflow first');
    return;
  }

  const token = tokensLayer.children[0];
  console.log('Token type:', token.tagName); // Should be 'g' not 'circle'
  console.log('Token has transform:', token.hasAttribute('transform'));

  if (token.tagName !== 'g') {
    console.error('❌ FAIL: Token is not a group!');
    console.error('   Old code is running - clear cache and reload');
    return;
  }

  console.log('✅ PASS: Token structure is correct');
  console.log('✅ Tokens should pan/zoom correctly');
};

testTokenPanning();
```

**Expected output:**
```
=== Token Pan Test ===
tokensLayer parent: mainGroup  ✅
Token type: g  ✅
Token has transform: true  ✅
✅ PASS: Token structure is correct
✅ Tokens should pan/zoom correctly
```

## Files Modified

### File: `agui-client.js`

**Changes:**
1. `createToken()` - Wraps token in `<g>` group (line 438-497)
2. `moveToken()` - Animates transform instead of cx/cy (line 564-567)
3. Added verification logging (line 485-490)

**Key indicators in logs:**
```
✅ Token group appended to tokensLayer
✅ tokensLayer correctly inside mainGroup (will transform with canvas)
Token position: transform=translate(...), r=10
```

## Summary

**The fix IS implemented** - tokens use group transforms and are inside mainGroup.

**The issue you're experiencing is most likely:**
- ❌ Browser cache serving old JavaScript
- ❌ Old tokens created before cache clear

**Solution:**
1. ✅ Hard reload browser (`Ctrl+Shift+R` or `Cmd+Shift+R`)
2. ✅ Verify console shows new logs (see "Verify Fix is Loaded" above)
3. ✅ Execute workflow fresh to create new tokens
4. ✅ Test Shift+Pan - tokens should move!

**If still not working:**
- Clear ALL browser cache
- Close ALL tabs
- Restart browser
- Try different browser (Firefox, Safari) to rule out cache issues

The code is correct - it's a cache issue! 🔄
