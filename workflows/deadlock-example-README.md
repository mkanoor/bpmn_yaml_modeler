# Deadlock Detection Example

This workflow demonstrates how the token animation system can detect deadlocks in parallel gateway joins.

## What is a Deadlock?

A **deadlock** occurs when a parallel gateway join is waiting for tokens that will never arrive. This happens when:
- One or more parallel paths throw exceptions and terminate early
- A path diverts to error handling and never reaches the join
- A path contains an infinite loop
- The workflow design has unbalanced fork/join (incorrect number of paths)

## The Example Workflow

### Structure:
```
Start → Parallel Fork (3 paths) → Parallel Join → Final Task → End
           ↓           ↓        ↓
         Path 1    Path 2    Path 3
         (✅)      (✅)      (❌ FAILS)
```

### Path Details:

**Path 1 (Blue Token - Top):**
- Quick task (1 second sleep)
- Completes successfully
- Token arrives at join gateway

**Path 2 (Red Token - Middle):**
- Medium task (2 seconds sleep)
- Completes successfully
- Token arrives at join gateway

**Path 3 (Green Token - Bottom):**
- **Fails intentionally** (throws exception)
- Diverts to error handling
- **Token never reaches join gateway** ❌

### Expected Behavior:

1. **Fork**: Blue token splits into 3 colored tokens (🔵 🔴 🟢)
2. **Execution**:
   - Path 1 completes in 1s → 🔵 arrives at join
   - Path 2 completes in 2s → 🔴 arrives at join
   - Path 3 fails → 🟢 diverts to error handler, ends early
3. **Join Gateway**: Waiting for 3 tokens, only 2 arrive (🔵 🔴)
4. **Deadlock Detection**: After 30 seconds, deadlock is detected

## Deadlock Detection Features

### Visual Indicators:
- ⚠️ **Red pulsing border** on the deadlocked gateway
- ⚠️ **Warning icon** above the gateway
- 📊 **Status text** showing "DEADLOCK (2/3)" - tokens arrived vs expected

### Console Output:
```
🚨 ═══════════════════════════════════════════════════════
🚨 DEADLOCK DETECTED!
🚨 ═══════════════════════════════════════════════════════
Gateway: join_gateway
Wait time: 30.0s
Tokens arrived: 2/3
Missing tokens: 1

✅ Tokens that arrived:
  1. 🔵 BLUE token (from task_path1) - arrived 29.0s ago
  2. 🔴 RED token (from task_path2) - arrived 28.0s ago

❌ Missing token paths (never arrived):
  ⚠️  Path from task_path3_fail - token never arrived

💡 Possible causes:
  • One or more parallel paths threw an exception
  • A path diverted to error handling and never reached join
  • A path contains an infinite loop or is still running
  • Incorrect workflow design - unbalanced fork/join
🚨 ═══════════════════════════════════════════════════════
```

### Browser Notification:
A notification appears in the top-right corner:
```
⚠️ Deadlock Detected
Gateway join_gateway is waiting for 1 more token(s)
but they will never arrive. Check console for details.
```

## How to Run

1. **Start the backend**:
   ```bash
   cd backend
   python main.py
   ```

2. **Open the frontend**:
   - Open `index.html` in your browser
   - Load the workflow: `workflows/deadlock-example.yaml`

3. **Execute the workflow**:
   - Click "Execute Workflow"
   - Use empty context: `{}`
   - Click "Start Execution"

4. **Watch the token flow**:
   - 🔵 Token starts at the fork
   - Splits into 🔵 🔴 🟢
   - Watch paths 1 and 2 complete
   - See path 3 fail and divert to error handler
   - After 30 seconds, deadlock is detected on the join gateway

## Configuration

### Deadlock Timeout
The deadlock detection timeout is configurable in `agui-client.js`:
```javascript
this.deadlockTimeout = 30000; // 30 seconds (default)
```

You can change this to detect deadlocks faster or slower:
- Fast detection: `10000` (10 seconds)
- Slower detection: `60000` (60 seconds)

## Use Cases

This deadlock detection is useful for:
- **Debugging workflows** - Identify why joins never complete
- **Production monitoring** - Alert when workflows are stuck
- **Testing error handling** - Verify error paths don't break joins
- **Workflow validation** - Ensure all fork/join pairs are balanced

## Fixing Deadlocks

### Option 1: Fix the failing path
Ensure all paths complete successfully and reach the join.

### Option 2: Use Inclusive Gateway
If some paths are optional, use an inclusive gateway instead of parallel gateway.

### Option 3: Add timeout handling
Add explicit timeout handlers to paths that might fail.

### Option 4: Redesign workflow
Separate error handling from the main parallel flow:
```
Fork → [Path 1] → Join → Continue
    → [Path 2] ↗
    → [Path 3] ↗

If path fails → Error Handler → Separate End Event
```
