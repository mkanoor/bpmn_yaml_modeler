# Debugging Skip Marks - Model-Based Approach

## Problem Identified

The DOM-based position matching wasn't working reliably because:
- Element positions might not match exactly
- Tolerance (5px) was too strict
- Transform calculations were complex and error-prone

## New Solution: Model-Based Traversal

Instead of matching DOM positions, we now use the **modeler's data model** directly.

### How It Works

1. **Get Not-Taken Flow IDs** from DOM (has `.path-not-taken` class)
2. **Look up connection in model**: `modeler.connections.find(c => c.id === flowId)`
3. **Get target element ID**: `connection.to`
4. **Recursively traverse** using `modeler.connections.filter(c => c.from === elementId)`

### Code Flow

```javascript
markNotTakenPathsAsSkipped() {
    // 1. Find not-taken flows in DOM
    const notTakenFlows = document.querySelectorAll('.bpmn-connection.path-not-taken');

    // 2. Get their IDs
    notTakenFlowIds.forEach(flowId => {
        // 3. Look up in modeler's data
        const connection = modeler.connections.find(c => c.id === flowId);

        // 4. Start recursive traversal from target
        this.markElementAndDownstreamAsSkippedUsingModel(connection.to);
    });
}

markElementAndDownstreamAsSkippedUsingModel(elementId) {
    // 1. Mark this element
    this.markElementSkipped(elementId);

    // 2. Find outgoing connections using the model
    const outgoingConnections = modeler.connections.filter(c => c.from === elementId);

    // 3. Recursively mark each downstream element
    outgoingConnections.forEach(conn => {
        this.markElementAndDownstreamAsSkippedUsingModel(conn.to);
    });
}
```

## Console Output to Expect

When you execute the workflow, you should see:

```
✅ Workflow completed: success
🔍 Marking not-taken paths as skipped...
  Found not-taken flow: conn_6
  Connection conn_6: from element_3 to element_7
  📍 Marking element element_7 as skipped
    ⊘ Marking element element_7 as SKIPPED
    Found 1 outgoing connections from element_7
    Following connection conn_7 to element_8
  📍 Marking element element_8 as skipped
    ⊘ Marking element element_8 as SKIPPED
    Found 0 outgoing connections from element_8
```

Or if elements were already executed:

```
✅ Workflow completed: success
🔍 Marking not-taken paths as skipped...
  Found not-taken flow: conn_3
  Connection conn_3: from element_3 to element_4
  📍 Marking element element_4 as skipped
    ✅ Element element_4 is completed, not marking as skipped
  📍 Marking element element_5 as skipped
    ✅ Element element_5 is completed, not marking as skipped
  📍 Marking element element_6 as skipped
    ✅ Element element_6 is completed, not marking as skipped
```

## Testing Steps

### Step 1: Open Browser Console

1. Open the BPMN modeler in your browser
2. Open Developer Tools (F12)
3. Go to Console tab

### Step 2: Execute Workflow

1. Import `add-numbers-conditional-workflow.yaml`
2. Click "▶ Execute Workflow"
3. Watch the console output

### Step 3: Check Console Logs

Look for these key messages:

**Expected for Success Path (sum > 10):**
```
🔍 Marking not-taken paths as skipped...
  Found not-taken flow: conn_6
  Connection conn_6: from element_3 to element_7
  📍 Marking element element_7 as skipped
    ⊘ Marking element element_7 as SKIPPED
    Found 1 outgoing connections from element_7
    Following connection conn_7 to element_8
  📍 Marking element element_8 as skipped
    ⊘ Marking element element_8 as SKIPPED
    Found 0 outgoing connections from element_8
```

**This means:**
- ✅ Found the not-taken flow (conn_6 - default path)
- ✅ Marked "Send Failure Notification" (element_7) as skipped
- ✅ Found outgoing connection to "End Failed" (element_8)
- ✅ Marked "End Failed" as skipped
- ✅ No more outgoing connections - recursion stops

### Step 4: Visual Verification

After execution completes, verify in the canvas:

**Success Path (sum = 12):**
- [Send Failure Notification] should have **orange ⊘**
- [End: Failed - Sum Too Small] should have **orange ⊘**

**Default Path (sum = 8):**
- [Process Valid Sum] should have **orange ⊘**
- [Send Success Notification] should have **orange ⊘**
- [End: Success] should have **orange ⊘**

## Troubleshooting

### Issue: "⚠️ Modeler not available"

**Console shows:**
```
⚠️ Modeler not available, falling back to DOM-based marking
```

**Fix:**
- The `modeler` global variable is not accessible
- Check that `app.js` is loaded before `agui-client.js`
- Verify: `const modeler = new BPMNModeler();` is defined globally

### Issue: "Element XXX is completed, not marking as skipped"

**Console shows:**
```
✅ Element element_7 is completed, not marking as skipped
```

**This is CORRECT if:**
- The element was actually executed (it's on the taken path)
- This protection prevents overriding execution status

**This is WRONG if:**
- The element is on a skipped path but somehow got marked as completed
- This indicates a race condition or backend sending wrong messages

### Issue: "Element XXX not found in DOM"

**Console shows:**
```
⚠️ Element element_7 not found in DOM
```

**Possible causes:**
- Element ID in model doesn't match DOM
- Element hasn't been rendered yet
- YAML import issue

**Check:**
```javascript
// In console
modeler.connections
modeler.elements
```

Verify IDs match what's in the YAML.

### Issue: No console output at all

**Possible causes:**
- Workflow didn't complete
- Backend connection failed
- No not-taken paths found

**Check:**
1. Did you see "✅ Workflow completed: success"?
2. Are there any not-taken paths? (gray dashed lines with ✗)
3. Is WebSocket connected? (look for "● Connected" in toolbar)

## Expected Element IDs

From `add-numbers-conditional-workflow.yaml`:

| Element | ID | Type |
|---------|-----|------|
| Start | element_1 | startEvent |
| Add Two Numbers | element_2 | scriptTask |
| Sum > 10? (Gateway) | element_3 | exclusiveGateway |
| Process Valid Sum | element_4 | serviceTask |
| Send Success Notification | element_5 | sendTask |
| Success (End) | element_6 | endEvent |
| Send Failure Notification | element_7 | sendTask |
| Failed - Sum Too Small (End) | element_8 | endEvent |

**Connections:**
- conn_3: element_3 → element_4 (success path, condition: `${sum} > 10`)
- conn_6: element_3 → element_7 (default path, condition: `""`)
- conn_4: element_4 → element_5
- conn_5: element_5 → element_6
- conn_7: element_7 → element_8

## Summary

The new model-based approach is **much more reliable** because:

1. ✅ Uses actual data model instead of DOM positions
2. ✅ No complex transform calculations
3. ✅ No position tolerance issues
4. ✅ Direct `from` → `to` traversal
5. ✅ Clear console logging for debugging

**Check the browser console to see exactly what's happening!** 🔍
