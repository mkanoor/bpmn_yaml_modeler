# Subprocess Token Fix - Handling Internal Elements

## Issue Discovered

When executing workflows with **Call Activities** that invoke subprocesses, you saw this error:

```
❌ Element NOT found in DOM: sp_receive
❌ createToken: Element sp_receive not found in DOM
❌ Token creation FAILED
```

## Root Cause

### Subprocess Architecture

BPMN supports two types of subprocess elements:

1. **Subprocess Definitions** (`subProcessDefinitions` in YAML)
   - Defined in the workflow file
   - **NOT rendered on the main canvas**
   - Only visible when you expand a collapsed subprocess
   - Examples: `sp_receive`, `sp_send`, `sp_script`

2. **Call Activities** (rendered on main canvas)
   - Invoke subprocess definitions
   - **DO render on the main canvas**
   - Shown as collapsed rectangles
   - Examples: `task_validate`, `call_approval`

### The Problem

Backend sends `element.activated` and `element.completed` events for **ALL elements**, including:
- ✅ Main workflow elements (rendered in DOM)
- ❌ Subprocess internal elements (NOT rendered in DOM)

When frontend tries to create tokens for subprocess internal elements:
```javascript
const element = document.querySelector(`[data-id="sp_receive"]`);
// Returns null because sp_receive is NOT in the DOM!
```

### Why Subprocess Elements Aren't in DOM

From your workflow structure:
```yaml
process:
  subProcessDefinitions:
    - id: subprocess_approval_handler
      elements:
        - id: sp_receive        # ← This is INSIDE subprocess definition
          type: receiveTask
          # NOT rendered on main canvas!

  elements:
    - id: call_approval         # ← This IS on main canvas
      type: callActivity
      properties:
        calledElement: subprocess_approval_handler
```

**Main canvas shows**: Only `call_approval` (the Call Activity)
**NOT shown**: `sp_receive`, `sp_send`, `sp_script` (subprocess internals)

## The Fix

### Change 1: Skip Token Creation for Subprocess Elements

**File**: `agui-client.js` line 658-662

```javascript
highlightElement(elementId) {
    const element = document.querySelector(`[data-id="${elementId}"]`);

    if (element) {
        // Element found - create token
        element.classList.add('active');
        this.createToken(elementId);
    } else {
        // Element NOT found - likely subprocess internal element
        console.log(`ℹ️ Element ${elementId} not in DOM (likely subprocess internal element - skipping token)`);
        return; // Don't try to create token
    }
}
```

**Result**: No error when backend sends events for subprocess internal elements.

### Change 2: Handle Completion Gracefully

**File**: `agui-client.js` line 706-711

```javascript
markElementComplete(elementId) {
    const element = document.querySelector(`[data-id="${elementId}"]`);

    if (element) {
        // Element found - add checkmark
        element.classList.add('completed');
        // Add checkmark
    } else {
        // Element not found - subprocess internal
        console.log(`ℹ️ Element ${elementId} not in DOM (subprocess internal - skipping completion mark)`);
        // Still try to move tokens (in case it's needed)
        this.moveTokenToNextElements(elementId);
    }
}
```

## Expected Behavior After Fix

### Before (Errors):
```
❌ Element NOT found in DOM: sp_receive
❌ createToken: Element sp_receive not found in DOM
❌ Token creation FAILED
```

### After (Clean):
```
🔵 highlightElement called for: call_approval
  ✅ Found element in DOM: call_approval
  🎯 Creating token for call_approval
  ✅ Token created successfully

🔵 highlightElement called for: sp_receive
  ℹ️ Element sp_receive not in DOM (likely subprocess internal element - skipping token)

🔵 highlightElement called for: sp_send
  ℹ️ Element sp_send not in DOM (likely subprocess internal element - skipping token)
```

## Token Flow for Call Activities

When a Call Activity executes:

1. **Token appears at Call Activity** (e.g., `call_approval`)
2. Call Activity executes subprocess internally
3. Backend sends events for subprocess elements (`sp_receive`, `sp_send`)
4. Frontend **gracefully skips** these elements (no error)
5. **Token remains at Call Activity** until subprocess completes
6. Token moves to next element when Call Activity completes

### Visual Representation

```
Main Canvas (what you see):
┌─────────────────────────────────────────┐
│ Start → Call Activity 🔵 → End          │
│         (collapsed)                      │
└─────────────────────────────────────────┘

Subprocess (internal - not visible):
┌─────────────────────────────────────────┐
│ Start → Send → Receive → Process → End  │
│         (backend sends events for these) │
│         (frontend gracefully ignores)    │
└─────────────────────────────────────────┘
```

## Testing

### Test 1: Workflow with Call Activity
1. Load `workflows/call-activity-conditional-approval.yaml`
2. Execute workflow
3. **Expected**:
   - ✅ Token appears at Call Activity
   - ✅ No errors in console
   - ✅ Console shows "skipping token" for subprocess elements
   - ✅ Token moves to next element when Call Activity completes

### Test 2: Console Output
```
🔵 highlightElement called for: start_1
  ✅ Found element in DOM: start_1
  🎯 Creating token for start_1
  ✅ Token created successfully

🔵 Moving token from start_1 to call_approval
🔵 Token arrived at call_approval

🔵 highlightElement called for: call_approval
  ✅ Found element in DOM: call_approval
  ℹ️ Element already has 1 token(s), not creating new one

🔵 highlightElement called for: sp_send
  ℹ️ Element sp_send not in DOM (likely subprocess internal element - skipping token)

🔵 highlightElement called for: sp_receive
  ℹ️ Element sp_receive not in DOM (likely subprocess internal element - skipping token)

📨 Received: element.completed {elementId: "call_approval"}
🔵 Moving token from call_approval to next_task
```

## Future Enhancement: Expanded Subprocesses

Currently, subprocesses are **collapsed** on the canvas. If you implement **expanded subprocesses** in the future:

1. When subprocess is **expanded**:
   - Subprocess internal elements ARE rendered in DOM
   - Tokens WILL be created for them
   - No changes needed - current code will work!

2. When subprocess is **collapsed**:
   - Subprocess internal elements are NOT rendered
   - Frontend skips them (current fix)

The fix is **future-proof** - it handles both cases automatically by checking if element exists in DOM.

## Summary

**Problem**: Backend sends events for subprocess internal elements not in DOM
**Solution**: Check if element exists before creating tokens
**Result**: Clean execution with no errors for subprocess-based workflows

**Files Changed**:
- `agui-client.js` - 2 functions updated (`highlightElement`, `markElementComplete`)

**Benefit**: Workflows with Call Activities now execute cleanly without token creation errors!
