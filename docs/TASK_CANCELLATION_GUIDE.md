# LLM Task Cancellation - User Guide

## Overview

The LLM Task Cancellation feature allows you to stop long-running agentic tasks mid-execution. This is particularly useful when:

- You realize the task is taking too long
- The task is heading in the wrong direction
- You want to modify the workflow and restart
- You need to free up resources immediately

**Key Features:**
- ✅ Graceful cancellation at safe checkpoints
- ✅ Partial results preserved and displayed
- ✅ Cancellation state persists in replay
- ✅ No data corruption or broken state
- ✅ Real-time visual feedback

---

## How to Cancel a Task

### 1. **Identify Cancellable Tasks**

Not all tasks can be cancelled. When a task becomes cancellable, you'll see:

- 💬 **Feedback bubble** appears on the BPMN element (click to open panel)
- 🛑 **Cancel Task button** at the top of the feedback panel (red button)

**Cancellable Task Types:**
- Agentic Tasks (with `allowCancellation=true` property)
- Tasks currently streaming LLM responses
- Tasks executing MCP tools
- Tasks with retry logic in progress

**Non-Cancellable Task Types:**
- Simple Service Tasks (execute too quickly)
- User Tasks (already waiting for human input)
- Gateway evaluations (instantaneous)
- Completed tasks

### 2. **Open the Feedback Panel**

Click the 💬 feedback bubble on the BPMN element to open the Task Activity panel.

**What you'll see:**
```
┌─────────────────────────────────────────┐
│ Task Activity                        × │
├─────────────────────────────────────────┤
│ 🛑 Cancel Task                         │ ← Click here to cancel
├─────────────────────────────────────────┤
│ 🤔 Thinking...                         │
│ 💬 LLM Response                        │
│ │ Analyzing customer feedback for     │
│ │ sentiment patterns and key themes...│
│ 🔧 analyze_sentiment ✓ Complete       │
└─────────────────────────────────────────┘
```

### 3. **Click Cancel Task**

When you click the 🛑 **Cancel Task** button:

**Immediate Feedback:**
- Button changes to ⏳ **Cancelling...**
- Button becomes disabled (grayed out)
- Yellow notice appears: "Stopping task gracefully..."

**What Happens Behind the Scenes:**
1. Cancellation request sent to backend
2. Backend marks task for cancellation
3. Task checks cancellation at next safe checkpoint:
   - Between LLM streaming chunks
   - Before each MCP tool execution
   - Between retry attempts
4. Task stops gracefully, preserves partial results
5. Cancellation complete event sent to UI

### 4. **Cancellation Complete**

When cancellation finishes, you'll see:

```
┌─────────────────────────────────────────┐
│ ⚠️ Task cancelled by user               │
│ User requested cancellation             │
│                                         │
│ Partial Result:                         │
│ {                                       │
│   "analysis": "Partially completed",    │
│   "partial_response": "...",            │
│   "tokens_used": 1234,                  │
│   "status": "cancelled"                 │
│ }                                       │
└─────────────────────────────────────────┘
```

**Visual Indicators:**
- ⚠️ Red warning icon
- Cancellation reason displayed
- Partial results shown (if any were collected)
- Element marked with special styling on canvas

---

## Cancellation Timing

### Safe Cancellation Points

The system checks for cancellation at these checkpoints:

| Checkpoint | When It Occurs | Data Preserved |
|------------|----------------|----------------|
| **Between Retries** | Before each retry attempt starts | Previous attempt results |
| **Between Tokens** | During LLM streaming, every token chunk | Accumulated response text |
| **Before Tools** | Before each MCP tool execution | Previous tool results |
| **After Tools** | After each tool completes | All tool outputs |

**Why Checkpoints?**
- Prevents data corruption
- Ensures database consistency
- Preserves work already completed
- Avoids breaking external API calls

### Cancellation Latency

| Task Phase | Expected Delay | Why? |
|------------|---------------|------|
| **Thinking** | < 100ms | Checked immediately |
| **LLM Streaming** | 100-500ms | Checked per token (~every 50ms) |
| **Tool Execution** | 1-3 seconds | Must finish current tool first |
| **Retrying** | < 100ms | Checked before next retry |

**Note:** You cannot cancel in the middle of a tool execution. The system waits for the current tool to finish, then cancels before starting the next one.

---

## Partial Results

When a task is cancelled, any data collected up to that point is preserved.

### Example: Cancelled During LLM Streaming

**Scenario:** Task is analyzing customer feedback. You cancel after 30% completion.

**Partial Result:**
```json
{
  "analysis": "Analysis partially completed (cancelled by user)",
  "partial_response": "Customer sentiment appears generally positive. Key themes identified:\n1. Product quality - mostly satisfied\n2. Customer service - ",
  "tokens_used": 456,
  "status": "cancelled"
}
```

**What You Get:**
- ✅ Incomplete but valid text up to cancellation point
- ✅ Token usage metrics (for cost tracking)
- ✅ Status indicator showing cancellation
- ❌ No final analysis or conclusions

### Example: Cancelled During Tool Execution

**Scenario:** Task is executing 5 MCP tools. You cancel after tool #3 completes.

**Partial Result:**
```json
{
  "tool_results": [
    {"tool": "fetch_data", "result": {...}, "status": "complete"},
    {"tool": "analyze_sentiment", "result": {...}, "status": "complete"},
    {"tool": "extract_keywords", "result": {...}, "status": "complete"}
  ],
  "status": "cancelled",
  "reason": "User cancelled before tool #4 (generate_report)"
}
```

**What You Get:**
- ✅ Results from all completed tools
- ✅ Clear indication of where cancellation occurred
- ❌ No results from tools #4 and #5

---

## Replay Behavior

Cancellation state persists in the event history. When you replay a workflow:

### Live Execution vs Replay

| Aspect | Live Execution | Replay |
|--------|----------------|--------|
| **Cancel Button** | ✅ Shown while task running | ❌ Not shown (read-only) |
| **Cancellation Notice** | ✅ Shown after cancel completes | ✅ Shown in same position |
| **Partial Results** | ✅ Displayed immediately | ✅ Loaded from database |
| **Visual Styling** | ✅ Red/yellow indicators | ✅ Same styling applied |

### Replay Example

Click the 💬 feedback bubble on a previously-cancelled task:

```
┌─────────────────────────────────────────┐
│ Task Activity                        × │
├─────────────────────────────────────────┤
│ 10:23:45 AM                             │
│ 🤔 Thinking...                          │
│ Analyzing customer feedback             │
├─────────────────────────────────────────┤
│ 10:23:48 AM                             │
│ 💬 LLM Response                         │
│ │ Customer sentiment appears generally  │
│ │ positive. Key themes identified:      │
│ │ 1. Product quality - mostly satisfied │
│ │ 2. Customer service -                 │
│ │ ⚠️ (Partial response - task          │
│ │    cancelled: User cancelled)         │
├─────────────────────────────────────────┤
│ ⚠️ This task was cancelled during       │
│    execution                            │
│    User requested cancellation          │
└─────────────────────────────────────────┘
```

**Key Differences:**
- ⏱️ Timestamps show when events occurred
- 📼 All events shown in chronological order
- 🔒 Read-only view (no cancel button)
- ⚠️ Clear indication that task was cancelled

---

## Edge Cases & Error Handling

### Case 1: Task Completes Before Cancellation

**Scenario:** You click cancel, but task finishes in the same instant.

**What Happens:**
```
┌─────────────────────────────────────────┐
│ ❌ Cannot cancel task                   │
│ Task already completed                  │
└─────────────────────────────────────────┘
```

**Resolution:** Error notice shown for 5 seconds, then disappears. Task result is already available.

### Case 2: Task Not Cancellable

**Scenario:** You try to cancel a task that doesn't support cancellation.

**What Happens:**
- No cancel button appears (prevention)
- If sent manually: Error message returned

**Why?** Task executor doesn't have `allowCancellation=true` property.

### Case 3: Network Disconnect During Cancel

**Scenario:** WebSocket disconnects while cancellation is in progress.

**What Happens:**
1. Frontend shows "Disconnected" status in header
2. Cancel button stays in "Cancelling..." state
3. On reconnect:
   - Backend checks task status
   - Sends latest state to frontend
   - UI updates accordingly

**Resolution:** Automatic recovery when connection restored.

### Case 4: Multiple Cancel Clicks

**Scenario:** User clicks cancel button multiple times rapidly.

**What Happens:**
- First click: Send cancel request, disable button
- Subsequent clicks: Ignored (button disabled)

**Why?** Prevents duplicate cancel requests and race conditions.

---

## Workflow Impact

### What Happens After Cancellation?

| Workflow Element | Behavior After Cancel |
|------------------|----------------------|
| **Next Element** | ❌ Not executed (workflow stops) |
| **Parallel Paths** | ⚠️ Other paths continue normally |
| **Gateway Merges** | ⚠️ May trigger if other paths complete |
| **Workflow Outcome** | ❌ Marked as "failed" |

### Example Workflow

```
Start → Task A → [Gateway] → Task B (cancelled) → End (Success)
                      ↓
                   Task C → End (Failure)
```

**Scenario:** Task B is cancelled.

**Result:**
- ✅ Task A completes normally
- 🛑 Task B cancelled (partial results saved)
- ❌ Gateway evaluates, chooses Task C path
- ✅ Task C executes
- ❌ Workflow completes with "failed" outcome

**Note:** Cancellation doesn't stop the entire workflow, only the cancelled task and its downstream elements on that path.

---

## Configuration

### Enable Cancellation for a Task

**In BPMN Modeler:**

1. Select Agentic Task element
2. Open Properties Panel (right side)
3. Scroll to "Custom Properties" section
4. Find **allowCancellation** checkbox
5. ✅ Check the box
6. Save workflow

**YAML Configuration:**

```yaml
elements:
  - id: analyze_feedback
    type: AgenticTask
    name: Analyze Customer Feedback
    properties:
      agentProvider: openrouter
      model: anthropic/claude-3.5-sonnet
      allowCancellation: true  # ← Enable cancellation
      custom:
        aguiEventCategories:
          - messaging
          - tool
```

**Default Value:** `false` (for safety)

### Disable Cancellation

Simply uncheck the **allowCancellation** box, or set to `false` in YAML.

**Why Disable?**
- Task must run to completion for data consistency
- Task is critical to workflow integrity
- Task executes very quickly (< 1 second)
- Task has side effects that can't be undone

---

## Best Practices

### ✅ DO

1. **Enable cancellation for long-running tasks**
   - Tasks that call LLMs with large prompts
   - Tasks that execute multiple MCP tools
   - Tasks with retry logic (may retry many times)

2. **Monitor task progress before cancelling**
   - Open feedback panel to see what's happening
   - Check if task is close to completion
   - Review partial results to decide if useful

3. **Use partial results when available**
   - Even incomplete LLM responses may contain useful insights
   - Completed tool results are fully valid
   - Token usage tracking helps estimate costs

4. **Clear execution state after cancellation**
   - Click "Clear Execution" button in toolbar
   - Removes all visual indicators from canvas
   - Prepares for fresh workflow run

### ❌ DON'T

1. **Don't cancel tasks with external side effects**
   - Tasks that send emails (email may already be sent)
   - Tasks that update databases (changes may be committed)
   - Tasks that call payment APIs (transaction may be in flight)

2. **Don't expect instant cancellation**
   - System waits for safe checkpoint
   - Current tool must finish first
   - Allow 1-3 seconds for graceful shutdown

3. **Don't cancel and immediately restart**
   - Wait for cancellation to complete
   - Check final state before restarting
   - Review partial results for clues

4. **Don't rely on cancellation for error handling**
   - Use proper try/catch and retry logic
   - Configure timeouts appropriately
   - Cancellation is for user control, not fault tolerance

---

## Troubleshooting

### Problem: Cancel button doesn't appear

**Possible Causes:**
1. Task doesn't have `allowCancellation=true` property
2. Task completed too quickly (before panel opened)
3. Task is not an Agentic Task type
4. WebSocket disconnected

**Solution:**
- Check task properties in modeler
- Enable `allowCancellation` checkbox
- Ensure WebSocket shows "● Connected" in header
- Refresh page and retry

### Problem: Cancellation takes too long

**Possible Causes:**
1. Task is executing a long-running MCP tool
2. Network latency between frontend and backend
3. LLM API is slow to respond to chunks

**Solution:**
- Wait for current tool to finish (up to 30 seconds)
- Check network connection quality
- Be patient - cancellation is graceful, not forced

### Problem: Partial results not showing

**Possible Causes:**
1. Task was cancelled before any work completed
2. Event store database not accessible
3. Message content not yet accumulated

**Solution:**
- If cancelled immediately, no results expected
- Check backend logs for database errors
- Try reopening feedback panel (may load asynchronously)

### Problem: Cancelled task keeps running

**Possible Causes:**
1. Backend didn't receive cancel request
2. Task executor doesn't check cancellation flags
3. Task is in non-cancellable phase (tool execution)

**Solution:**
- Check browser console for WebSocket errors
- Verify backend logs show cancel request received
- Wait for current tool to complete
- If persists: Restart backend server

---

## Technical Details

### AG-UI Protocol Events

The cancellation feature uses these standard AG-UI events:

| Event | Direction | Purpose |
|-------|-----------|---------|
| `task.cancellable` | Backend → Frontend | Notify that task can be cancelled |
| `task.cancel.request` | Frontend → Backend | User requests cancellation |
| `task.cancelling` | Backend → Frontend | Cancellation in progress |
| `task.cancelled` | Backend → Frontend | Cancellation complete, includes partial results |
| `task.cancel.failed` | Backend → Frontend | Cancellation failed (e.g., task already done) |

### Database Schema

Cancellation state is stored in SQLite:

```sql
CREATE TABLE messages (
    message_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    element_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL,  -- 'streaming', 'complete', 'cancelled'
    timestamp TEXT NOT NULL,
    cancelled BOOLEAN DEFAULT FALSE,
    cancellation_reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### Performance Impact

| Metric | Impact | Notes |
|--------|--------|-------|
| **CPU Usage** | +0.1% | Cancellation checks are lightweight |
| **Memory** | +5KB per task | Stores cancellation flags in memory |
| **Network** | +200 bytes | 5 additional event types |
| **Database** | +2 columns | `cancelled` and `cancellation_reason` |
| **Latency** | +10-50ms | Checkpoint checks during execution |

**Conclusion:** Negligible performance impact. Safe to enable for all long-running tasks.

---

## FAQ

**Q: Can I cancel a task that's already completed?**
A: No. Once a task finishes successfully, it cannot be cancelled. You'll receive a "Task already completed" error message.

**Q: What happens to tokens used before cancellation?**
A: They are counted and included in the partial results. You are charged for all tokens generated up to the cancellation point.

**Q: Can I cancel a task from the BPMN canvas directly?**
A: No. You must open the feedback panel by clicking the 💬 bubble, then click the cancel button inside.

**Q: Will cancellation stop the entire workflow?**
A: No. Only the cancelled task and its downstream elements on that path are stopped. Parallel paths continue running.

**Q: Can I re-run a cancelled task?**
A: Yes. Click "Clear Execution" in the toolbar, then click "Execute Workflow" again. The task will start fresh.

**Q: Are cancelled tasks logged for auditing?**
A: Yes. All cancellation events are stored in the event database with timestamps, reasons, and partial results.

**Q: Can I cancel tasks programmatically via API?**
A: Not yet. This feature may be added in the future. Currently, cancellation is user-initiated only.

**Q: What's the difference between cancelling and failing?**
A:
- **Cancel:** User-initiated, graceful shutdown, partial results preserved
- **Fail:** System-initiated due to error, may have retry logic, error message logged

---

## Summary

✅ **Cancellation gives you control** over long-running agentic tasks
✅ **Graceful shutdown** at safe checkpoints prevents data corruption
✅ **Partial results** preserve work already completed
✅ **Replay consistency** ensures cancelled state persists in history
✅ **Simple UX** - just click the red button in the feedback panel

**Remember:**
1. Enable `allowCancellation` in task properties
2. Open feedback panel by clicking 💬 bubble
3. Click 🛑 Cancel Task button
4. Wait for graceful shutdown (1-3 seconds)
5. Review partial results in cancellation notice

---

## Related Documentation

- [AG-UI Event Filtering Guide](AGUI_EVENT_FILTERING.md) - Configure which events to see
- [Agentic Task Configuration](AGENTIC_TASKS.md) - Complete property reference
- [AG-UI Cancellation Design](AGUI_CANCELLATION_DESIGN.md) - Technical architecture
- [Workflow Execution Guide](WORKFLOW_EXECUTION.md) - How workflows run

**Need Help?** Check the troubleshooting section above or review backend logs for detailed error messages.
