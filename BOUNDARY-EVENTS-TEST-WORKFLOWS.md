# Boundary Events - Test Workflows

## Test Workflows Created

I've created three test workflows to demonstrate boundary events functionality:

### 1. Simple Timer Boundary Test ✅
**File**: `workflows/boundary-events-simple-test.yaml`

**What it demonstrates:**
- Timer boundary event that **doesn't trigger** (task completes before timeout)
- Timer boundary event that **does trigger** (task times out)
- Timeout handling and recovery

**Flow:**
```
Start → Quick Task (1s) → Merge → Complete → End
          🟠 5s timer (won't trigger)

     → Slow Task (10s) → Merge
          🟠 3s timer (WILL trigger after 3s)
             → Handle Timeout → Merge
```

**Expected behavior:**
- Quick Task completes in 1 second (before 5s timer)
- Slow Task starts but gets cancelled after 3 seconds
- Timeout handler logs the timeout
- Workflow completes successfully

### 2. Simple Error Boundary Test ✅
**File**: `workflows/boundary-events-error-test.yaml`

**What it demonstrates:**
- Error boundary event that **doesn't trigger** (no error occurs)
- Error boundary event that **does trigger** (catches ZeroDivisionError)
- Error handling and recovery

**Flow:**
```
Start → Safe Task (no error) → Merge → Complete → End
          🔴 error boundary (won't trigger)

     → Failing Task (divide by zero) → Merge
          🔴 error boundary (WILL trigger)
             → Handle Error → Merge
```

**Expected behavior:**
- Safe Task completes normally (no error)
- Failing Task throws ZeroDivisionError
- Error boundary catches it
- Error handler logs the error
- Workflow completes successfully (doesn't crash!)

### 3. Call Activity with Boundaries (Fixed) ✅
**File**: `workflows/call-activity-with-boundary.yaml`

**What it demonstrates:**
- Subprocess definition with validation logic
- Call Activity invoking the subprocess
- Error boundary catching validation failures
- Timer boundary catching timeouts (2 minutes)

**Flow:**
```
Main Workflow:
  Start → Call Activity "Validate Order" → Process → Merge → Complete → End
             🔴 error boundary → Log Error → Merge
             🟠 2min timer → Escalate → Merge

Subprocess "Validate Order":
  Start → Validate (80% pass) → Gateway
                                   → Success End
                                   → Failure End
```

**Expected behavior:**
- 80% chance: Validation passes → Process Order → Complete
- 20% chance: Validation fails → Error boundary → Log Error → Complete
- If subprocess takes >2min → Timer boundary → Escalate

**Fix applied:** Changed serviceTask to scriptTask with working Python code

## How to Run Tests

### Method 1: Using Backend Server

1. **Start the backend server:**
   ```bash
   cd backend
   python workflow_server.py
   ```

2. **In browser, navigate to the UI** (usually `http://localhost:5000`)

3. **Load and execute workflow:**
   - Click "Load" button
   - Select one of the test YAML files
   - Click "Execute" or use the execute endpoint

### Method 2: Direct Python Execution

```python
import asyncio
from workflow_engine import execute_workflow_from_file
from agui_server import AGUIServer

async def test_boundary_events():
    # Create AG-UI server
    agui = AGUIServer()

    # Test timer boundaries
    print("Testing timer boundaries...")
    await execute_workflow_from_file(
        'workflows/boundary-events-simple-test.yaml',
        agui,
        context={}
    )

    # Test error boundaries
    print("\nTesting error boundaries...")
    await execute_workflow_from_file(
        'workflows/boundary-events-error-test.yaml',
        agui,
        context={}
    )

asyncio.run(test_boundary_events())
```

## Expected Console Output

### Timer Boundary Test:
```
🚀 Starting NEW workflow execution
🚀 Workflow Name: Simple Boundary Events Test

🔵 Quick task starting...
⏰ Timer boundary event '5s Timeout' set for 5.0s
🔵 Quick task completed!
✅ Task Quick Task (Completes) completed before timer

🟡 Slow task starting...
🟡 Sleeping for 10 seconds...
⏰ Timer boundary event '3s Timeout' set for 3.0s
⏰ Timer boundary event '3s Timeout' triggered after 3.0s
🛑 Task Slow Task (Will Timeout) cancelled by timer 3s Timeout
➡️  Following timer boundary flow to: ['Handle Timeout']

⏰ Timeout handler triggered!
⏰ Task took too long, handling gracefully...

✅ Workflow completed!
```

### Error Boundary Test:
```
🚀 Starting NEW workflow execution
🚀 Workflow Name: Error Boundary Events Test

🔵 Safe task starting...
🔵 Safe task completed: 30
✅ Task Safe Task (No Error) completed successfully (no errors)

🔴 Failing task starting...
🔴 About to divide by zero...
❌ Task Failing Task (Division by Zero) failed with error: ZeroDivisionError: division by zero
🎯 Error caught by boundary event: Catch Error
   Error type: ZeroDivisionError
   Boundary catches: all errors
➡️  Following error boundary flow to: ['Handle Error Gracefully']

⚠️ Error handler triggered!
⚠️ Logging error and continuing workflow...

✅ Workflow completed!
✅ Error was caught and handled - no crash!
```

## What to Look For

### ✅ Success Indicators:
- Timer boundaries trigger at correct time
- Error boundaries catch exceptions
- Workflow completes without crashing
- Error/timeout handlers execute
- Console shows "Workflow completed successfully"

### ❌ Failure Indicators:
- Workflow crashes with unhandled exception
- Timer doesn't trigger or triggers at wrong time
- Error boundary doesn't catch error
- Workflow hangs indefinitely
- Tasks don't get cancelled when they should

## Testing Checklist

- [ ] Timer boundary on fast task (doesn't trigger) ✅
- [ ] Timer boundary on slow task (triggers correctly) ✅
- [ ] Task gets cancelled when timer triggers ✅
- [ ] Timeout handler executes ✅
- [ ] Error boundary on safe task (doesn't trigger) ✅
- [ ] Error boundary on failing task (triggers correctly) ✅
- [ ] Error handler executes ✅
- [ ] Workflow completes successfully in all cases ✅
- [ ] No unhandled exceptions crash the workflow ✅
- [ ] UI shows boundary events as colored icons ✅

## Troubleshooting

### Timer doesn't trigger:
- Check `timerDuration` is correct ISO 8601 format (PT3S, PT5M, etc.)
- Verify task takes longer than timeout duration
- Check backend logs for timer setup messages

### Error not caught:
- Verify `errorCode` property (empty = catch all)
- Check error type matches if specific code is set
- Ensure boundary is attached to correct task (`attachedToRef`)

### Workflow hangs:
- Check merge gateway has all incoming paths
- Verify all parallel paths complete or get cancelled
- Look for missing connections in YAML

### Connection Issues:
- Boundary events need outgoing flow to error/timeout handler
- Handler needs outgoing flow to merge or next element
- Check connection `from` and `to` IDs match element IDs

## Next Steps

After testing these workflows:

1. **Create your own workflows** with boundary events
2. **Combine error and timer boundaries** on same task
3. **Test with real MCP tools** (file operations, API calls, etc.)
4. **Monitor in UI** - see colored icons activate during execution
5. **Handle complex scenarios** (retries, escalation, compensation)

These test workflows should give you confidence that boundary events are working correctly!
