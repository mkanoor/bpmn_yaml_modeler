# Token Flow Simulation Mode

The BPMN Modeler now includes a **Token Flow Simulation** feature that animates tokens through your workflow **without executing actual tasks**. This is perfect for:

- 📊 **Workflow validation** - Verify your design before deployment
- 🎓 **Training & demonstrations** - Show how workflows execute
- 🐛 **Debugging flow logic** - Identify routing issues visually
- ⚡ **Quick testing** - No backend required

---

## Features

### 🎬 Simulation vs. Execution

| Feature | Simulation Mode | Execution Mode |
|---------|----------------|----------------|
| Requires backend | ❌ No | ✅ Yes |
| Executes actual tasks | ❌ No (visual only) | ✅ Yes |
| Token animation | ✅ Yes | ✅ Yes |
| Speed control | ✅ Adjustable (0.5x - 10x) | ❌ Real-time only |
| Pause/Resume | ✅ Yes | ❌ No |
| Gateway decisions | 🎲 Random/Default | ✅ Condition-based |
| Colored tokens (parallel) | ✅ Yes | ✅ Yes |
| Deadlock detection | ✅ Yes (30s timeout) | ✅ Yes (30s timeout) |

### ⚙️ Simulation Capabilities

**Supported Elements:**
- ✅ Start/End Events
- ✅ All Task Types (scriptTask, userTask, serviceTask, etc.)
- ✅ Exclusive Gateways (chooses default or first path)
- ✅ Parallel Gateways (fork/join with colored tokens)
- ✅ Inclusive Gateways (random path selection)
- ✅ Call Activities
- ✅ Pools and Lanes

**Animation Features:**
- 🔵🔴🟢 Colored tokens for parallel paths
- ⬥ Automatic fork/join handling
- 🏆 Shows which parallel path arrives first at joins
- ⚠️ Deadlock detection for incomplete joins
- 📍 Element highlighting during execution
- ✅ Completion markers on finished elements

---

## How to Use

### 1. Open Simulation Mode

1. Design your workflow in the modeler
2. Click the **"🎬 Simulate Token Flow"** button in the toolbar
3. The simulation modal will appear

### 2. Configure Simulation

**Choose Speed:**
- **0.5x (Slow)** - Best for presentations, training (4s per task)
- **1x (Normal)** - Default speed (2s per task)
- **2x (Fast)** - Quick validation (1s per task)
- **5x (Very Fast)** - Rapid testing (0.4s per task)
- **10x (Ultra Fast)** - Maximum speed (0.2s per task)

### 3. Start Simulation

Click **"🎬 Start Simulation"**

The workflow will:
1. Clear any previous execution state
2. Find the start event
3. Create a blue token at the start
4. Animate through the workflow

### 4. Control Playback

Once running, you can:
- **⏸️ Pause** - Freeze simulation at current element
- **▶️ Resume** - Continue from where you paused
- **⏹️ Stop** - End simulation immediately
- **Change Speed** - Adjust speed during playback

---

## Gateway Behavior in Simulation

### Exclusive Gateway (XOR)
```
      ┌─→ Path A (condition: x > 10)
Gateway │
      └─→ Path B (default)
```
**Simulation:** Takes the first path without a condition, or the first path if all have conditions.

### Parallel Gateway (AND)
```
        ┌─→ Path A (🔵 blue token)
Gateway ┼─→ Path B (🔴 red token)
        └─→ Path C (🟢 green token)
```
**Simulation:** Creates colored tokens for each path, executes in parallel, merges at join.

### Inclusive Gateway (OR)
```
        ┌─→ Path A (may activate)
Gateway ┼─→ Path B (may activate)
        └─→ Path C (may activate)
```
**Simulation:** Randomly activates 1 to N paths.

---

## Timing Configuration

Default timing (at 1x speed):

| Element Type | Duration |
|--------------|----------|
| Task execution | 2000ms (2s) |
| Token movement | 800ms (0.8s) |
| Gateway evaluation | 500ms (0.5s) |
| Parallel fork delay | 200ms between tokens |

To customize, edit `token-simulator.js`:
```javascript
this.delays = {
    taskExecution: 2000,      // Task "execution" time
    tokenMovement: 800,       // Animation speed
    gatewayEvaluation: 500,   // Decision time
    parallelForkDelay: 200    // Stagger parallel tokens
};
```

---

## Example Use Cases

### 1. Validating Parallel Flow Design

**Scenario:** You have a 3-way parallel fork and want to verify all paths reach the join.

**Steps:**
1. Load workflow with parallel gateway
2. Start simulation at 1x speed
3. Watch 🔵🔴🟢 tokens fork
4. Verify all three tokens reach the join
5. Check console for arrival order

**Expected:** "🏆 Keeping [COLOR] token (arrived first), merging others"

---

### 2. Training New Team Members

**Scenario:** Explain how approval workflows work.

**Steps:**
1. Load `call-activity-conditional-approval.yaml`
2. Start simulation at **0.5x speed** (slow)
3. Explain each step as tokens move:
   - "Token starts here..."
   - "Budget approval happens here..."
   - "Gateway checks if approved..."
   - "If denied, goes here..."

**Benefit:** Visual, hands-on learning without needing backend setup.

---

### 3. Quick Design Iteration

**Scenario:** Testing different gateway placements.

**Steps:**
1. Design workflow variant A
2. Simulate at **10x speed** (ultra fast)
3. Observe token flow
4. Modify design to variant B
5. Simulate again
6. Compare approaches

**Benefit:** Rapid prototyping without deployment.

---

### 4. Deadlock Detection Demo

**Scenario:** Show what happens when parallel paths don't all complete.

**Steps:**
1. Load `deadlock-example.yaml`
2. Start simulation at 2x speed
3. Watch path 3 fail and divert to error handler
4. Wait 30 seconds (15s at 2x speed)
5. See deadlock warning appear on join gateway

**Expected:**
```
🚨 DEADLOCK DETECTED!
Gateway: join_gateway
Tokens arrived: 2/3
Missing tokens: 1
```

---

## Console Output

Simulation provides detailed logging:

```
🎬 ═══════════════════════════════════════════════════════
🎬 STARTING TOKEN FLOW SIMULATION
🎬 Speed: 2.0x
🎬 ═══════════════════════════════════════════════════════

🟢 Start event - beginning workflow
📍 Simulating: startEvent "Start" (start_1)
⬥ Parallel gateway FORK "Fork into 3 Paths" - creating 3 parallel paths
🔵 BLUE token created at element: fork_gateway (1 total)
🔴 RED token created at element: fork_gateway (2 total)
🟢 GREEN token created at element: fork_gateway (3 total)
⚙️ Executing task "Path 1 - Quick Task" (0.5s)
⚙️ Executing task "Path 2 - Medium Task" (1.0s)
⚙️ Executing task "Path 3 - Task" (0.5s)
🔵 Token arriving at parallel gateway JOIN: join_gateway from task_path1
🔴 RED token arrived at JOIN (1/3)
🔵 Token arriving at parallel gateway JOIN: join_gateway from task_path2
🔵 BLUE token arrived at JOIN (2/3)
🔴 Token arriving at parallel gateway JOIN: join_gateway from task_path3
🟢 GREEN token arrived at JOIN (3/3)
✅ All tokens arrived at JOIN join_gateway - merging
📊 Arrival order:
  1. 🔴 RED token (from task_path1)
  2. 🔵 BLUE token (from task_path2)
  3. 🟢 GREEN token (from task_path3)
🏆 Keeping 🔴 RED token (arrived first), merging others
🏁 End event - workflow complete
✅ Simulation completed successfully
```

---

## Limitations

### Current Limitations:
1. **Gateway decisions are not condition-based** - Uses default/random paths
2. **No actual task execution** - Scripts, emails, webhooks are not triggered
3. **No context variables** - Cannot test condition expressions
4. **Subprocess call activities** - Simulated as regular tasks (don't expand)
5. **Error handling** - All tasks "succeed" in simulation

### What Still Works:
- ✅ Token animation and movement
- ✅ Parallel fork/join logic
- ✅ Deadlock detection
- ✅ Visual element states (active, completed)
- ✅ Path highlighting for gateways
- ✅ Colored tokens for parallel flows

---

## Integration with Real Execution

Simulation and execution modes are independent:

**Workflow:**
1. Design workflow in modeler
2. **Simulate** to validate flow logic
3. Fix any issues found
4. **Execute** with real backend for integration testing
5. Deploy to production

**Best Practice:**
- Simulate first for quick validation
- Execute for testing actual task logic
- Use simulation for demos/training
- Use execution for production workflows

---

## Troubleshooting

### Simulation doesn't start
- **Check console** for errors
- **Verify start event exists** in workflow
- **Reload page** and try again

### Tokens don't move
- Check if simulation is paused
- Try stopping and restarting
- Verify connections exist between elements

### Parallel tokens don't merge
- Check that join gateway has correct number of incoming connections
- Wait 30 seconds for deadlock detection
- Check console for merge messages

### Speed changes don't apply
- Speed changes apply to future delays only
- Current animations complete at previous speed
- Stop and restart for immediate effect

---

## Keyboard Shortcuts

Coming soon! Planned shortcuts:
- `Space` - Pause/Resume simulation
- `Escape` - Stop simulation
- `+/-` - Increase/Decrease speed
- `R` - Restart simulation

---

## Advanced: Programmatic Control

You can also control simulation via JavaScript console:

```javascript
// Start simulation
tokenSimulator.startSimulation();

// Change speed during simulation
tokenSimulator.setSpeed(5); // 5x speed

// Pause
tokenSimulator.pauseSimulation();

// Resume
tokenSimulator.resumeSimulation();

// Stop
tokenSimulator.stopSimulation();

// Custom delays
tokenSimulator.delays.taskExecution = 5000; // 5 second tasks
```

---

## Future Enhancements

Planned features:
- 🎯 Step-through mode (manual token advancement)
- 📊 Execution statistics (total time, path frequencies)
- 💾 Record and replay simulations
- 🎨 Custom token colors
- 🔍 Simulation history viewer
- 📸 Export simulation as GIF/video
- 🧪 Batch simulation (run 100 times, see statistics)
- 🎲 Configurable gateway probabilities

---

## Summary

Token Flow Simulation is a powerful tool for:
- ✅ Validating workflow design without backend
- ✅ Training and demonstrations
- ✅ Quick iteration and testing
- ✅ Visual debugging of flow logic

Use it alongside real execution for a complete workflow development experience!
