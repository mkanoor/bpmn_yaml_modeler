# Token Flow Visualization - Debug Guide

## Overview

The token flow visualization shows animated colored circles moving through the workflow during execution, representing the flow of control.

## Two Modes of Token Animation

### 1. Simulation Mode (Token Simulator)
**File**: `token-simulator.js`
**Purpose**: Simulate token flow WITHOUT executing the workflow
**How to use**: Click "Simulate" button in toolbar

**Features**:
- Runs entirely in the browser (no backend required)
- Uses colored tokens to show parallel paths (blue, red, green, orange, etc.)
- Configurable speed (0.5x, 1x, 2x, 4x)
- Pause/Resume/Stop controls
- Task delays configurable in code

**Flow**:
1. User clicks "Simulate" button
2. `tokenSimulator.startSimulation()` is called
3. Finds start event and calls `simulateElement()`
4. For each element, calls `aguiClient.highlightElement()` which creates a token
5. Token moves via `aguiClient.moveToken()`
6. When task completes, calls `aguiClient.markElementComplete()` which moves token to next element

### 2. Real Execution Mode (AGUI Client)
**File**: `agui-client.js`
**Purpose**: Show token flow during REAL workflow execution via backend
**How to use**: Click "Execute" button, workflow runs on backend

**Features**:
- Tokens created when backend sends `element.activated` messages
- Tokens move when backend sends `element.completed` messages
- Shows real-time execution progress
- Handles parallel gateways with colored tokens
- Shows token merging at join gateways

**Flow**:
1. User clicks "Execute" button
2. Backend starts workflow execution
3. Backend sends WebSocket message: `{ type: 'element.activated', elementId: 'start_1', ... }`
4. `agui-client.js` receives message and calls `handleMessage()`
5. Routes to `highlightElement(elementId)`
6. `highlightElement()` creates token at element if none exists
7. Backend sends `{ type: 'element.completed', elementId: 'start_1' }`
8. Routes to `markElementComplete(elementId)`
9. `markElementComplete()` calls `moveTokenToNextElements()`
10. Token animates to next element

## Token Lifecycle

### Creation
```javascript
createToken(elementId, offsetIndex = 0, colorIndex = 0)
```

**What it does**:
1. Finds element in DOM: `document.querySelector('[data-id="${elementId}"]')`
2. Gets element position from `transform` attribute
3. Creates SVG circle with radius 8px
4. Applies color from `tokenColors` array (blue, red, green, orange, purple, etc.)
5. Adds glow effect via `drop-shadow`
6. Appends to `tokensLayer` (or creates layer if missing)
7. Stores in `this.tokens` Map

**Returns**: SVG circle element or null if failed

### Movement
```javascript
moveToken(fromElementId, toElementId, specificToken = null, onComplete = null)
```

**What it does**:
1. Gets positions of from/to elements
2. Animates token movement over 800ms with easing
3. Updates token association (removes from source, adds to destination)
4. Calls `onComplete` callback when animation finishes

### Deletion
```javascript
removeToken(elementId, specificToken = null)
```

**What it does**:
1. Fades out token (opacity 0 over 300ms)
2. Removes from DOM after fade
3. Removes from `this.tokens` Map

## Debug Logging Added

I've added extensive debug logging to help diagnose token issues:

### In `highlightElement()`:
```
🔵 highlightElement called for: task_1
  ✅ Found element in DOM: task_1
  🎯 Creating token for task_1 (no existing tokens)
  ✅ Token created successfully
```

### In `createToken()`:
```
    🔵 createToken called: elementId=task_1, offsetIndex=0, colorIndex=0
    ✅ Token appended to tokensLayer
    🔵 BLUE token created at element: task_1 (1 total)
    Token position: cx=350, cy=200, r=8
    Token visible in DOM: true
```

### In `moveToken()`:
```
🔵 Moving token from task_1 to task_2
🔵 Token arrived at task_2
```

## Common Issues and Fixes

### Issue 1: "Tokens not appearing during execution"

**Symptoms**:
- Elements highlight (turn active) but no tokens appear
- Console shows no token creation logs

**Diagnosis**:
1. Open browser console (F12)
2. Execute a workflow
3. Look for `🔵 highlightElement called for: XXX` messages
4. Check if you see `🎯 Creating token` messages
5. Check if you see `✅ Token created successfully`

**Possible causes**:

A. **Backend not sending `element.activated` messages**
```javascript
// Check console for:
📨 Received: element.activated {elementId: "start_1", ...}
```
If missing, backend may not be sending events. Check `workflow_engine.py`.

B. **Element not found in DOM**
```javascript
// Console shows:
❌ Element NOT found in DOM: task_1
```
This means the workflow YAML has an element ID that doesn't match what's rendered. Check:
- Element IDs in YAML match what's displayed in canvas
- Workflow was loaded properly
- Canvas has rendered elements before execution starts

C. **tokensLayer not created**
```javascript
// Console shows:
❌ tokensLayer not found - token NOT added to DOM!
```
The SVG needs a `<g id="tokensLayer">` element. Check:
- `app.js` creates SVG properly
- tokensLayer is created in `createToken()` if missing

D. **Token created but not visible**
```javascript
// Console shows:
Token visible in DOM: false
```
Token was created but not attached to DOM. Check:
- tokensLayer exists
- tokensLayer is child of main SVG
- SVG viewport is correct

### Issue 2: "Tokens appear but don't move"

**Symptoms**:
- Token appears at start event
- Token doesn't move to next element
- No `🔵 Moving token` logs

**Diagnosis**:
1. Check console for `element.completed` messages
2. Check `moveTokenToNextElements()` logs

**Possible causes**:

A. **Backend not sending `element.completed` messages**
```javascript
// Missing:
📨 Received: element.completed {elementId: "start_1", ...}
```

B. **No outgoing connections found**
```javascript
// In moveTokenToNextElements():
// modeler.connections is empty or doesn't have connection from this element
```

Check:
- Connections exist in workflow YAML
- Connections loaded properly into `modeler.connections` array

### Issue 3: "Tokens disappear after first element"

**Symptoms**:
- Token appears at start event
- Token moves to first task
- Token disappears

**Possible cause**: Token is being removed instead of moved.

**Check**:
- `removeToken()` not being called prematurely
- `markElementComplete()` calls `moveTokenToNextElements()` not `removeToken()`

### Issue 4: "Multiple tokens for same path (not parallel gateway)"

**Symptoms**:
- Multiple colored tokens appear for single path
- Not a parallel gateway scenario

**Possible cause**: `highlightElement()` called multiple times for same element

**Check**:
- Backend not sending duplicate `element.activated` messages
- Token check in `highlightElement()` working properly

## How to Test Token Flow

### Test 1: Simple Linear Workflow
```yaml
Start → Task 1 → Task 2 → End
```

**Expected behavior**:
1. Blue token appears at Start
2. Token moves to Task 1
3. Token moves to Task 2
4. Token moves to End
5. Token removed at End

**Console logs**:
```
🔵 highlightElement called for: start_1
  🎯 Creating token for start_1
  🔵 BLUE token created
🔵 Moving token from start_1 to task_1
🔵 Token arrived at task_1
🔵 Moving token from task_1 to task_2
...
```

### Test 2: Parallel Gateway
```yaml
Start → Fork → Task 1
               → Task 2
          → Join → End
```

**Expected behavior**:
1. Blue token appears at Start
2. Token moves to Fork gateway
3. Token duplicates: Blue stays on first path, Red created for second path
4. Blue token flows through Task 1
5. Red token flows through Task 2
6. Both tokens arrive at Join gateway
7. Tokens merge (first-arrived kept, others removed)
8. Single token continues to End

**Console logs**:
```
🔵 Parallel gateway FORK gateway_1 - creating 2 tokens
🔵 BLUE token created
🔴 RED token created
🔵 Token arriving at parallel gateway JOIN
🔴 Token arriving at parallel gateway JOIN
✅ All tokens arrived at JOIN - merging
🏆 Keeping 🔵 BLUE token (arrived first), merging others
```

### Test 3: Exclusive Gateway
```yaml
Start → Gateway → Path A (if x > 5)
                → Path B (else)
        → Merge → End
```

**Expected behavior**:
1. Token appears at Start
2. Token moves to Gateway
3. Backend sends `gateway.path_taken` message
4. Token moves along chosen path ONLY
5. Unchosen path marked with gray dashed line and X
6. Token continues to Merge
7. Token moves to End

**Console logs**:
```
🔵 Gateway chose path: conn_a from gateway_1 to taskA
🔵 Moving token from gateway_1 to taskA
```

## Manual Testing Steps

### Step 1: Test Simulation Mode
1. Create simple workflow (Start → Task → End)
2. Click "Simulate" button
3. Select speed (1x)
4. Click "Start Simulation"
5. **Expected**: Blue token animates through workflow
6. **Check console** for simulation logs

### Step 2: Test Execution Mode
1. Start backend: `cd backend && python main.py`
2. Load simple workflow
3. Click "Execute" button
4. Enter context: `{}`
5. Click "Start Execution"
6. **Expected**: Token animates during real execution
7. **Check console** for:
   - WebSocket connection: `✅ Connected to AG-UI server`
   - Element activated messages
   - Token creation logs
   - Token movement logs

### Step 3: Test with Boundary Events Workflow
1. Load `workflows/boundary-events-simple-test.yaml`
2. Execute workflow
3. **Expected**:
   - Token appears at Start
   - Token forks to two tasks (Quick and Slow)
   - Quick task completes, token moves to Merge
   - Slow task times out after 3s, token moves to Timeout Handler
   - Timeout Handler completes, token moves to Merge
   - Both tokens arrive at Merge
   - Merged token moves to Complete task
   - Token moves to End

## Token Colors

Tokens use different colors for parallel paths:

| Color | Fill | Stroke | Usage |
|-------|------|--------|-------|
| 🔵 Blue | #3498db | #2980b9 | Primary path, first parallel path |
| 🔴 Red | #e74c3c | #c0392b | Second parallel path |
| 🟢 Green | #2ecc71 | #27ae60 | Third parallel path |
| 🟠 Orange | #f39c12 | #e67e22 | Fourth parallel path |
| 🟣 Purple | #9b59b6 | #8e44ad | Fifth parallel path |
| 🔵 Teal | #1abc9c | #16a085 | Sixth parallel path |
| 🩷 Pink | #e91e63 | #c2185b | Seventh parallel path |
| 🟡 Amber | #ff9800 | #f57c00 | Eighth parallel path |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (Frontend)                      │
│                                                             │
│  ┌─────────────────┐         ┌──────────────────┐         │
│  │ token-simulator │         │   agui-client    │         │
│  │     .js         │         │      .js         │         │
│  │                 │         │                  │         │
│  │ Simulation Mode │         │ Execution Mode   │         │
│  │ (Local only)    │         │ (WebSocket)      │         │
│  └────────┬────────┘         └────────┬─────────┘         │
│           │                           │                    │
│           └──────────┬────────────────┘                    │
│                      │                                     │
│           ┌──────────▼──────────┐                         │
│           │   Token Animation   │                         │
│           │                     │                         │
│           │ • createToken()     │                         │
│           │ • moveToken()       │                         │
│           │ • removeToken()     │                         │
│           │                     │                         │
│           │ Renders to:         │                         │
│           │ <g id="tokensLayer">│                         │
│           │   <circle.../>      │                         │
│           │ </g>                │                         │
│           └─────────────────────┘                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ WebSocket
                              │ (Execution Mode only)
                              │
┌─────────────────────────────▼─────────────────────────────┐
│                   Backend (Python)                        │
│                                                           │
│  ┌────────────────────┐        ┌──────────────────┐     │
│  │ workflow_engine.py │───────▶│ agui_server.py   │     │
│  │                    │        │                  │     │
│  │ Sends events:      │        │ Broadcasts via   │     │
│  │ • element.activated│        │ WebSocket        │     │
│  │ • element.completed│        │                  │     │
│  │ • gateway.path_taken│       │                  │     │
│  └────────────────────┘        └──────────────────┘     │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

## Next Steps

With the debug logging added, you can now:

1. Execute a workflow and watch the console
2. Identify exactly where token creation/movement fails
3. Fix the specific issue based on the logs
4. Use this guide to understand expected behavior

If you see tokens in **Simulation Mode** but not in **Execution Mode**, the issue is with:
- Backend WebSocket connection
- Backend not sending proper events
- Event handler routing in `agui-client.js`

If you don't see tokens in **either mode**, the issue is with:
- Token rendering (SVG, tokensLayer, element positions)
- DOM element IDs not matching workflow YAML
- Browser console errors blocking execution
