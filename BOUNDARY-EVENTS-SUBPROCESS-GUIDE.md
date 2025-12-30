# Boundary Events with Subprocesses - Design Guide

## Quick Answer

✅ **Attach boundary events to the Call Activity in the main workflow**
❌ **Do NOT add boundary events inside subprocess definitions**

## Why This Approach?

### 1. BPMN 2.0 Standard Compliance
The BPMN specification states that boundary events monitor **activities** (tasks, subprocesses, call activities). When you attach a boundary event to a Call Activity, it monitors the **entire subprocess execution** as a single unit.

### 2. Reusability
Subprocess definitions should be **generic and reusable**:
- Same subprocess can be called from multiple workflows
- Each caller can apply different error/timeout handling
- Subprocess focuses on its core logic, not error handling

### 3. Visibility
Error handling is **visible in the main workflow**:
- Easy to see what happens on error/timeout
- No hidden error handling buried in subprocess
- Better for documentation and understanding

## Architecture Pattern

```
┌─────────────────────────────────────────────────────────────┐
│ Main Workflow (contains error handling)                      │
│                                                               │
│   Start → Call Activity → Process → End                      │
│              ↓                                                │
│              🔴 Error Boundary → Log & Notify                 │
│              🟠 Timer (5min)   → Escalate                     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                 ↓ calls
┌─────────────────────────────────────────────────────────────┐
│ Subprocess Definition (reusable, no error handling)          │
│                                                               │
│   Start → Validate → Transform → Save → End                  │
│   (focuses on business logic only)                           │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Implementation in Your Modeler

### Step 1: Create Subprocess Definition

1. Click **"+ Add Subprocess Definition"** in the Subprocess Definitions panel
2. Name it (e.g., "Order Validation")
3. Click **Edit** to enter subprocess editor mode
4. Add tasks: Start → Validate → Check → End
5. Click **"Exit Subprocess Editor"** to return to main workflow

**Important:** Do NOT add boundary events while in subprocess editor mode!

### Step 2: Add Call Activity to Main Workflow

1. In main workflow, drag **"Call Activity"** from palette
2. In properties panel, select subprocess from **"Subprocess Definition"** dropdown
3. Configure variable mappings if needed

### Step 3: Attach Boundary Events to Call Activity

1. Click **"Error Boundary"** or **"Timer Boundary"** in palette
2. Click on the **Call Activity box** (not inside the subprocess!)
3. Boundary event attaches to the Call Activity
4. Configure properties:
   - Error: `errorCode` (empty = catch all)
   - Timer: `timerDuration` (e.g., PT5M = 5 minutes)

### Step 4: Connect Error Handling Flow

1. Click **"Sequence Flow"** in palette
2. Click connection point on boundary event
3. Click target element (error handler task)
4. Create error/timeout handling logic

## Example Workflows

### Example 1: Simple Error Handling

```yaml
Main Workflow:
  - Call Activity: "Validate Data"
    - Error Boundary → Log Error → End
    - Normal Path → Process Data → End

Subprocess "Validate Data":
  - Start → Check Schema → Validate Business Rules → End
  - (Can throw errors that bubble up to caller)
```

### Example 2: Timeout with Retry

```yaml
Main Workflow:
  - Call Activity: "External API Call"
    - Timer (30s) → Retry Task → Loop back to Call Activity
    - Error Boundary → Log Failure → End
    - Normal Path → Continue → End

Subprocess "External API Call":
  - Start → HTTP Request → Parse Response → End
  - (Simple, reusable, no timeout logic)
```

### Example 3: Multiple Boundary Events

```yaml
Main Workflow:
  - Call Activity: "Complex Processing"
    - Error (ValidationError) → Fix Data → Retry
    - Error (BusinessError) → Notify User → End
    - Error (all others) → Log → Escalate
    - Timer (10min) → Cancel → Notify Timeout → End
    - Normal Path → Success → End

Subprocess "Complex Processing":
  - Start → Step 1 → Step 2 → Step 3 → End
  - (Can fail at any step, all caught by boundaries)
```

## Backend Execution Behavior

### How It Works

When `execute_task_with_boundary_events()` is called for a Call Activity:

1. **Subprocess starts** via `execute_subprocess()`
2. **Boundary events monitor** the subprocess execution:
   - Error boundaries: Wrap in try-catch
   - Timer boundaries: Race subprocess vs timer
3. **If subprocess succeeds**: Continue main workflow
4. **If error occurs**: Boundary catches it, follows error flow
5. **If timeout occurs**: Boundary cancels subprocess, follows timeout flow

### Code Flow

```python
# In workflow_engine.py
async def execute_task_with_boundary_events(task):
    if task.type == 'callActivity':
        # 1. Find boundaries attached to this call activity
        error_boundaries = [b for b in elements if b.attachedToRef == task.id]
        timer_boundaries = [...]

        # 2. Wrap subprocess execution with boundaries
        try:
            await execute_subprocess(...)  # ← Subprocess runs here
        except Exception as e:
            # 3. Error boundary catches exceptions from subprocess
            for boundary in error_boundaries:
                if boundary matches error:
                    follow_boundary_flow(boundary)
```

## Common Patterns

### Pattern 1: Fail-Safe with Logging

```
Call Activity → (Normal) → Continue
             → (Error) → Log Error → Continue with Fallback Data
```

**Use case:** Non-critical subprocess, workflow should continue even on failure

### Pattern 2: Critical with Escalation

```
Call Activity → (Normal) → Continue
             → (Error) → Notify Admin → End (workflow stops)
             → (Timeout) → Escalate to Manager → End
```

**Use case:** Critical subprocess, failures must be handled by humans

### Pattern 3: Retry with Backoff

```
Call Activity → (Normal) → Continue
             → (Error) → Wait 5s → Loop back to Call Activity
             → (Timeout) → Increase Timeout → Loop back
             → (Max Retries) → Give Up → End
```

**Use case:** Transient failures (network, external API), automatic recovery

## What NOT to Do

### ❌ Anti-Pattern 1: Boundary Events Inside Subprocess

```
Subprocess Definition:
  - Start
  - Task 1 (with error boundary) ← BAD!
  - Task 2
  - End
```

**Problem:** Subprocess is no longer reusable, error handling is hidden

### ❌ Anti-Pattern 2: Duplicate Error Handling

```
Main Workflow:
  - Call Activity (with error boundary)
    → calls →
Subprocess with internal error handling:
  - Task 1 → Error → Internal Handler → End
```

**Problem:** Two layers of error handling, confusing behavior

### ❌ Anti-Pattern 3: No Error Handling at All

```
Main Workflow:
  - Call Activity (no boundaries)
    → If subprocess fails, entire workflow crashes!
```

**Problem:** Unhandled errors crash the workflow engine

## Best Practices

1. ✅ **Always add error boundary** to Call Activities (at minimum)
2. ✅ **Add timer boundary** for long-running or external subprocesses
3. ✅ **Keep subprocess definitions simple** - just business logic
4. ✅ **Handle errors in main workflow** - visible and configurable
5. ✅ **Use specific error codes** when you need different handling for different errors
6. ✅ **Test error paths** - don't just test the happy path!

## Testing Your Setup

### Test 1: Error Boundary
1. Create subprocess that throws an error (e.g., division by zero)
2. Add error boundary to Call Activity
3. Connect to error handler task
4. Run workflow → should catch error and follow error flow ✅

### Test 2: Timer Boundary
1. Create subprocess with long-running task (e.g., sleep 60s)
2. Add timer boundary (PT10S = 10 seconds)
3. Connect to timeout handler
4. Run workflow → should timeout after 10s and follow timeout flow ✅

### Test 3: Success Path
1. Create normal subprocess that completes successfully
2. Add boundaries but they should NOT trigger
3. Run workflow → should complete normally, boundaries ignored ✅

## Example Workflow File

See: `/Users/madhukanoor/devsrc/bpmn/workflows/call-activity-with-boundary.yaml`

This example demonstrates:
- Subprocess definition with validation logic
- Call Activity invoking the subprocess
- Error boundary catching validation failures
- Timer boundary catching timeouts
- Proper flow merging after error handling

Load it in the modeler to see the complete pattern!
