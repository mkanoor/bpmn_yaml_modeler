# Token Cleanup Fix - Clearing Tokens Between Executions

## Issue

When importing a new workflow or re-executing an existing workflow, **tokens from the previous execution were not being cleared**. This caused:

1. **Old tokens to remain visible** on the canvas
2. **Token overlap** between executions
3. **Confusion** about which execution the tokens represent
4. **tokensLayer accumulation** (layer wasn't removed, just emptied)

## Root Cause

The token cleanup was incomplete in several places:

### 1. **Workflow Load (Import YAML)** ❌
When loading a new workflow via `File → Load`, the `newDiagram()` function cleared the three main SVG layers:
```javascript
this.poolsLayer.innerHTML = '';
this.connectionsLayer.innerHTML = '';
this.elementsLayer.innerHTML = '';
```

But **didn't clear tokensLayer** or call AG-UI cleanup.

### 2. **Workflow Re-execution** ❌
When clicking "Execute" again on the same workflow, no cleanup happened before starting the new execution.

### 3. **tokensLayer Persistence** ❌
The `removeAllTokens()` function removed individual token elements but **left the empty tokensLayer container** in the DOM. This meant:
- tokensLayer accumulated in DOM
- Potential for stale layer references

## The Fixes

### Fix 1: Clear Tokens on Workflow Start

**File**: `agui-client.js` line 227-229

**Added automatic cleanup when new workflow execution starts:**

```javascript
handleWorkflowStarted(message) {
    console.log('🚀 Workflow started:', message.instanceId);

    // Clear any existing tokens and highlights from previous execution
    console.log('🧹 Clearing previous execution state (tokens, highlights, checkmarks)');
    this.clearAllHighlights();  // ← NEW: Auto-clear on execution start

    this.showNotification('Workflow Started', ...);
}
```

**Result**: Every time you execute a workflow (even the same one), tokens from the previous run are automatically cleared.

---

### Fix 2: Clear Tokens on Workflow Load

**File**: `app.js` line 2912-2923

**Added token cleanup when loading a new workflow:**

```javascript
newDiagram(skipConfirm = false) {
    if (skipConfirm || confirm('Create a new diagram?')) {
        // ... existing code to clear elements, connections, pools ...

        this.poolsLayer.innerHTML = '';
        this.connectionsLayer.innerHTML = '';
        this.elementsLayer.innerHTML = '';

        // Clear tokens layer if it exists
        const tokensLayer = document.getElementById('tokensLayer');
        if (tokensLayer) {
            tokensLayer.remove();  // ← NEW: Remove tokensLayer
            console.log('🧹 Removed tokensLayer (will be recreated on next execution)');
        }

        // Clear AG-UI execution state if client exists
        if (typeof aguiClient !== 'undefined' && aguiClient) {
            console.log('🧹 Clearing AG-UI execution state');
            aguiClient.clearAllHighlights();  // ← NEW: Clear highlights, tokens, checkmarks
        }
    }
}
```

**Result**: When you load a new workflow, all execution state (tokens, checkmarks, highlights) is cleared.

---

### Fix 3: Remove tokensLayer Container

**File**: `agui-client.js` line 629-636

**Enhanced `removeAllTokens()` to also remove the container:**

```javascript
removeAllTokens() {
    // Remove all individual token elements
    this.tokens.forEach((tokensArray, elementId) => {
        tokensArray.forEach(token => {
            token.remove();
        });
    });
    this.tokens.clear();

    // Also remove the tokensLayer container itself
    const tokensLayer = document.getElementById('tokensLayer');
    if (tokensLayer) {
        tokensLayer.remove();  // ← NEW: Remove container
        console.log('🔵 All tokens removed and tokensLayer cleared');
    }
}
```

**Result**: tokensLayer is completely removed and will be recreated fresh on next execution.

---

## How Token Cleanup Works Now

### Scenario 1: Re-executing Same Workflow

**Steps:**
1. Execute workflow → tokens animate
2. Click "Execute" again
3. Backend sends `workflow.started` message
4. `handleWorkflowStarted()` automatically calls `clearAllHighlights()`
5. `clearAllHighlights()` calls `removeAllTokens()`
6. All tokens removed, tokensLayer removed
7. New execution starts with clean canvas
8. New tokens created fresh

**Console output:**
```
🚀 Workflow started: abc-123
🧹 Clearing previous execution state (tokens, highlights, checkmarks)
🔵 All tokens removed and tokensLayer cleared
🗑️ Requested backend to clear history

🔵 highlightElement called for: start_1
  🎯 Creating token for start_1
    ✅ Created tokensLayer and appended to mainGroup (will render on top of all elements)
    ✅ Token appended to tokensLayer
    🔵 BLUE token created at element: start_1
```

---

### Scenario 2: Loading New Workflow

**Steps:**
1. Workflow A is loaded with execution state (tokens, checkmarks)
2. Click "File" → "Load" → Select Workflow B
3. `importYAML()` calls `newDiagram(true)`
4. `newDiagram()` removes tokensLayer
5. `newDiagram()` calls `aguiClient.clearAllHighlights()`
6. Canvas is now clean
7. Workflow B loads fresh

**Console output:**
```
🧹 Removed tokensLayer (will be recreated on next execution)
🧹 Clearing AG-UI execution state
🔵 All tokens removed and tokensLayer cleared
```

---

### Scenario 3: Clicking "Clear Execution" Button

**Steps:**
1. Workflow completes with tokens, checkmarks visible
2. User clicks "Clear Execution" button
3. Button calls `aguiClient.clearAllHighlights()`
4. All tokens, checkmarks, highlights removed
5. Canvas is clean, ready for next execution

**Console output:**
```
🔵 All tokens removed and tokensLayer cleared
🗑️ Requested backend to clear history
```

---

## Complete Token Lifecycle

### Creation
```
1. Workflow starts
2. handleWorkflowStarted() → clearAllHighlights() → Clean slate
3. element.activated → highlightElement() → createToken()
4. tokensLayer created (if not exists) inside mainGroup
5. Token SVG element created and appended
```

### Movement
```
1. element.completed → markElementComplete()
2. moveTokenToNextElements() → moveToken()
3. Token animates from source to destination (800ms)
4. Token removed from source, added to destination
```

### Cleanup (Multiple Trigger Points)
```
Trigger 1: New execution starts
  → handleWorkflowStarted()
  → clearAllHighlights()
  → removeAllTokens()
  → tokensLayer removed

Trigger 2: New workflow loaded
  → importYAML() → newDiagram()
  → tokensLayer.remove()
  → clearAllHighlights()
  → removeAllTokens()
  → tokensLayer removed

Trigger 3: User clicks "Clear Execution"
  → clearExecutionBtn click
  → clearAllHighlights()
  → removeAllTokens()
  → tokensLayer removed
```

---

## Testing

### Test 1: Re-execute Same Workflow
1. Load and execute `workflows/boundary-events-simple-test.yaml`
2. Wait for completion (tokens visible)
3. Click "Execute" again
4. **Expected**:
   - ✅ Console shows "🧹 Clearing previous execution state"
   - ✅ All old tokens disappear
   - ✅ New tokens appear fresh
   - ✅ No token overlap

### Test 2: Load Different Workflow
1. Execute Workflow A
2. File → Load → Select Workflow B
3. **Expected**:
   - ✅ Console shows "🧹 Removed tokensLayer"
   - ✅ All tokens from Workflow A gone
   - ✅ Canvas is clean
   - ✅ Execute Workflow B → fresh tokens

### Test 3: Clear Execution Button
1. Execute workflow
2. Wait for completion
3. Click "Clear Execution" button
4. **Expected**:
   - ✅ All tokens removed
   - ✅ All checkmarks removed
   - ✅ All highlights removed
   - ✅ Canvas is clean

### Test 4: Multiple Rapid Executions
1. Execute workflow
2. Immediately click "Execute" again (don't wait for completion)
3. Repeat 3-4 times
4. **Expected**:
   - ✅ No token buildup
   - ✅ Each execution starts fresh
   - ✅ No errors in console

---

## Console Verification

### Good Output (After Fix)
```
🚀 Workflow started: abc-123
🧹 Clearing previous execution state (tokens, highlights, checkmarks)
🔵 All tokens removed and tokensLayer cleared
🗑️ Requested backend to clear history

🔵 highlightElement called for: start_1
  🎯 Creating token for start_1 (no existing tokens)
    ✅ Created tokensLayer and appended to mainGroup
    🔵 BLUE token created at element: start_1 (1 total)
```

### Bad Output (Before Fix)
```
🚀 Workflow started: abc-123
(No cleanup messages)

🔵 highlightElement called for: start_1
  ℹ️ Element already has 2 token(s), not creating new one
(Old tokens still there from previous execution!)
```

---

## Summary

**Problem**: Tokens weren't cleared between executions or workflow loads

**Solution**: Added cleanup at three key points:
1. **Workflow execution start** - Auto-clear before new execution
2. **Workflow load** - Clear when loading new workflow
3. **tokensLayer removal** - Remove container, not just tokens

**Result**: Clean token flow with no residue between executions

**Files Changed**:
- `agui-client.js` - 2 functions updated
- `app.js` - 1 function updated

**Benefit**: Every execution starts with a clean slate! 🎉

---

## Next Steps

1. **Hard reload browser** (`Ctrl+Shift+R` or `Cmd+Shift+R`)
2. **Test re-execution**: Execute same workflow twice
3. **Test workflow load**: Load different workflows
4. **Check console**: Look for cleanup messages

Tokens should now be completely cleared between executions! ✅
