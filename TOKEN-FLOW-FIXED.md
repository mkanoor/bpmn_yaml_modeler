# Token Flow Visualization - Enhanced with Debug Logging

## Changes Made

I've added extensive debug logging to the token flow visualization system to help diagnose why tokens may not be displaying during workflow execution.

## Files Modified

### 1. `/Users/madhukanoor/devsrc/bpmn/agui-client.js`

#### Added logging to `highlightElement()` (line 625-658)
```javascript
highlightElement(elementId) {
    console.log(`🔵 highlightElement called for: ${elementId}`);

    // Find element in DOM
    const element = document.querySelector(`[data-id="${elementId}"]`);
    if (element) {
        console.log(`  ✅ Found element in DOM: ${elementId}`);
        // ... highlight element ...
    } else {
        console.warn(`  ❌ Element NOT found in DOM: ${elementId}`);
    }

    // Create token if needed
    const tokensAtElement = this.tokens.get(elementId);
    if (!tokensAtElement || tokensAtElement.length === 0) {
        console.log(`  🎯 Creating token for ${elementId} (no existing tokens)`);
        const token = this.createToken(elementId);
        if (token) {
            console.log(`  ✅ Token created successfully`);
        } else {
            console.warn(`  ❌ Token creation FAILED`);
        }
    } else {
        console.log(`  ℹ️ Element already has ${tokensAtElement.length} token(s)`);
    }
}
```

#### Added logging to `createToken()` (line 405-476)
```javascript
createToken(elementId, offsetIndex = 0, colorIndex = 0) {
    console.log(`    🔵 createToken called: elementId=${elementId}, offsetIndex=${offsetIndex}, colorIndex=${colorIndex}`);

    const element = document.querySelector(`[data-id="${elementId}"]`);
    if (!element) {
        console.warn(`    ❌ createToken: Element ${elementId} not found in DOM`);
        return null;
    }

    // ... create token SVG element ...

    if (tokensLayer) {
        tokensLayer.appendChild(token);
        console.log(`    ✅ Token appended to tokensLayer`);
    } else {
        console.warn(`    ❌ tokensLayer not found - token NOT added to DOM!`);
    }

    // Store token
    this.tokens.get(elementId).push(token);

    const colorEmoji = this.getColorEmoji(color.name);
    console.log(`    ${colorEmoji} ${color.name.toUpperCase()} token created at element: ${elementId} (${this.tokens.get(elementId).length} total)`);
    console.log(`    Token position: cx=${token.getAttribute('cx')}, cy=${token.getAttribute('cy')}, r=${token.getAttribute('r')}`);
    console.log(`    Token visible in DOM:`, token.parentElement !== null);

    return token;
}
```

## How to Use Debug Logging

### Step 1: Open Browser Console
1. Open your browser's Developer Tools (F12 or Cmd+Option+I)
2. Go to the "Console" tab
3. Clear any existing logs

### Step 2: Execute a Workflow
1. Load one of the test workflows:
   - `workflows/boundary-events-simple-test.yaml`
   - `workflows/boundary-events-error-test.yaml`
   - `workflows/call-activity-with-boundary.yaml`

2. Start the backend server:
   ```bash
   cd backend
   python main.py
   ```

3. Click "Execute" button in the UI
4. Enter context (can be empty `{}`)
5. Click "Start Execution"

### Step 3: Observe Console Output

You should see output like this:

```
✅ Connected to AG-UI server

📨 Received: workflow.started {instanceId: "...", workflowName: "..."}

📨 Received: element.activated {elementId: "start_1", elementType: "startEvent", elementName: "Start"}
🔵 highlightElement called for: start_1
  ✅ Found element in DOM: start_1
  🎯 Creating token for start_1 (no existing tokens)
    🔵 createToken called: elementId=start_1, offsetIndex=0, colorIndex=0
    ✅ Token appended to tokensLayer
    🔵 BLUE token created at element: start_1 (1 total)
    Token position: cx=150, cy=200, r=8
    Token visible in DOM: true
  ✅ Token created successfully

📨 Received: element.completed {elementId: "start_1", duration: 0}
🔵 Moving token from start_1 to task_success
🔵 Token arrived at task_success

📨 Received: element.activated {elementId: "task_success", ...}
🔵 highlightElement called for: task_success
  ✅ Found element in DOM: task_success
  ℹ️ Element already has 1 token(s), not creating new one

... (continues for each element)
```

### Step 4: Diagnose Issues

Based on the console output, you can identify specific issues:

#### ✅ **Good - Everything Working**
```
✅ Found element in DOM
✅ Token created successfully
✅ Token appended to tokensLayer
Token visible in DOM: true
🔵 Moving token from X to Y
```

#### ❌ **Problem 1: Element Not Found**
```
❌ Element NOT found in DOM: task_1
```

**Cause**: Element ID in workflow YAML doesn't match rendered element in canvas.

**Fix**: Check that:
- Workflow was loaded correctly
- Element IDs in YAML match what's in the canvas
- Canvas has rendered all elements before execution

#### ❌ **Problem 2: Token Creation Failed**
```
❌ Token creation FAILED
❌ createToken: Element task_1 not found in DOM
```

**Cause**: Element exists in workflow but not in DOM.

**Fix**: Reload the workflow in the canvas before executing.

#### ❌ **Problem 3: tokensLayer Missing**
```
❌ tokensLayer not found - token NOT added to DOM!
```

**Cause**: SVG structure doesn't have tokensLayer group.

**Fix**: The code creates tokensLayer automatically, but if this appears, check browser console for other errors that might be preventing SVG creation.

#### ❌ **Problem 4: Token Not Visible**
```
✅ Token appended to tokensLayer
Token visible in DOM: false
```

**Cause**: Token created but not attached to DOM properly.

**Fix**: Check browser console for SVG errors. Ensure canvas SVG is properly initialized.

#### ❌ **Problem 5: No WebSocket Messages**
```
(No "📨 Received:" messages appear)
```

**Cause**: Backend not sending events or WebSocket not connected.

**Fix**:
1. Check connection status indicator shows "● Connected"
2. Check backend is running: `python backend/main.py`
3. Check backend logs for errors
4. Check backend is sending events (should see logs in backend console)

#### ❌ **Problem 6: Tokens Don't Move**
```
✅ Token created successfully
(But no "🔵 Moving token" messages)
```

**Cause**: Backend not sending `element.completed` events.

**Fix**: Check backend logs to ensure tasks are completing and events are being sent.

## Testing Workflow

Use this workflow to verify token flow is working:

### Test 1: Simulation Mode (No Backend Required)
1. Create any workflow in the canvas
2. Click "Simulate" button
3. Select speed (1x)
4. Click "Start Simulation"
5. **Expected**: Tokens animate through workflow
6. **Console**: Check for token creation and movement logs

**If simulation works**: Token rendering is working correctly. Issue is with backend event sending.

**If simulation doesn't work**: Issue is with token rendering (SVG, element IDs, etc.)

### Test 2: Real Execution Mode (Requires Backend)
1. Start backend: `cd backend && python main.py`
2. Check connection status shows "● Connected"
3. Load workflow: `workflows/boundary-events-simple-test.yaml`
4. Click "Execute"
5. Click "Start Execution"
6. **Expected**: Tokens animate during real execution
7. **Console**: Check for WebSocket messages and token logs

### Test 3: Verify Token Colors (Parallel Gateway)
1. Create workflow with parallel gateway:
   ```
   Start → Fork → Task A
                → Task B
          → Join → End
   ```
2. Execute workflow
3. **Expected**:
   - Blue token at Fork
   - Blue token continues to Task A
   - Red token created for Task B
   - Both tokens arrive at Join
   - Tokens merge (first-arrived kept)
   - Single token continues to End

## Expected Console Output (Full Example)

Here's what a complete successful execution looks like:

```
🚀 Starting NEW workflow execution
🚀 Workflow Name: Simple Boundary Events Test

✅ Connected to AG-UI server

📨 Received: workflow.started {instanceId: "abc-123", workflowName: "Simple Boundary Events Test"}

📨 Received: element.activated {elementId: "start_1"}
🔵 highlightElement called for: start_1
  ✅ Found element in DOM: start_1
  🎯 Creating token for start_1 (no existing tokens)
    🔵 createToken called: elementId=start_1, offsetIndex=0, colorIndex=0
    ✅ Token appended to tokensLayer
    🔵 BLUE token created at element: start_1 (1 total)
    Token position: cx=150, cy=200, r=8
    Token visible in DOM: true
  ✅ Token created successfully

📨 Received: element.completed {elementId: "start_1"}
🔵 Moving token from start_1 to task_success
🔵 Token arrived at task_success

📨 Received: element.activated {elementId: "task_success"}
🔵 highlightElement called for: task_success
  ✅ Found element in DOM: task_success
  ℹ️ Element already has 1 token(s), not creating new one

🔵 Quick task starting...
🔵 Quick task completed!

📨 Received: element.completed {elementId: "task_success"}
🔵 Moving token from task_success to merge_gateway

... (continues)

✅ Workflow completed!
```

## Documentation Created

I've created a comprehensive debug guide:

📄 **`TOKEN-FLOW-DEBUG-GUIDE.md`** - Complete reference including:
- Architecture overview
- Token lifecycle (creation, movement, deletion)
- Common issues and fixes
- Testing procedures
- Console output examples
- Troubleshooting steps

## Next Steps

1. **Test Simulation Mode**: Verify token rendering works without backend
2. **Test Execution Mode**: Verify tokens work with real backend execution
3. **Use Console Logs**: Follow the debug output to identify specific issues
4. **Refer to Debug Guide**: Use `TOKEN-FLOW-DEBUG-GUIDE.md` for detailed troubleshooting

The debug logging will show you exactly where token creation or movement is failing, making it much easier to fix any issues.

## Summary

**Problem**: "Token flow is not displaying the different tokens during execution"

**Solution Applied**:
1. Added extensive debug logging to `highlightElement()` function
2. Added debug logging to `createToken()` function
3. Added visibility checks for tokens in DOM
4. Created comprehensive debug guide documentation
5. Documented token flow architecture and expected behavior

**How to Use**:
1. Open browser console
2. Execute a workflow
3. Follow the debug logs to see exactly what's happening
4. Use the debug guide to troubleshoot specific issues

The logs will tell you:
- ✅ When elements are found/not found in DOM
- ✅ When tokens are created successfully
- ✅ When token creation fails (and why)
- ✅ Where tokens are positioned
- ✅ Whether tokens are visible in DOM
- ✅ When tokens move between elements
- ✅ WebSocket messages received from backend

This makes it very easy to diagnose and fix token visualization issues!
