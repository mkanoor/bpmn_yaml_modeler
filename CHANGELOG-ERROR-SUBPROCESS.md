# Error Event Sub-Process Implementation

## Summary

Implemented full support for **Error Event Sub-Processes** in the BPMN workflow engine, allowing workflows to catch and handle errors gracefully with dedicated recovery workflows.

## What Was Implemented

### 1. Error Detection and Triggering (`workflow_engine.py`)

**New Method: `check_and_trigger_error_subprocess()`**
- Searches for error Event Sub-Processes that can handle a given error
- Matches errors by `errorCode` property (empty = catch all)
- Triggers the appropriate Event Sub-Process when error occurs

```python
async def check_and_trigger_error_subprocess(self, error: Exception) -> Optional[Element]:
    """Check if there's an error Event Sub-Process that can handle this error"""
    # Find matching error Event Sub-Process
    # Trigger recovery workflow
    # Return subprocess if handled, None otherwise
```

### 2. Clean Error Handling

**New Exception: `EventSubProcessHandledError`**
- Special exception to signal error was successfully handled
- Prevents error logging while allowing interrupting subprocesses to cancel main flow
- Carries both subprocess name and original error

**Updated Error Flow:**
```python
try:
    # Execute task
except Exception as e:
    subprocess = await self.check_and_trigger_error_subprocess(e)
    if subprocess:
        raise EventSubProcessHandledError(subprocess.name, e)
    else:
        raise  # Re-raise if not handled
```

### 3. Success Completion for Handled Errors

**Updated `start_execution()` Method:**
```python
except EventSubProcessHandledError as e:
    # Error was handled - report as SUCCESS
    logger.info(f"✅ Workflow completed via Event Sub-Process: {e.subprocess_name}")
    await self.agui_server.send_workflow_completed(
        self.instance_id,
        'success',  # Success because error was handled
        duration
    )
```

### 4. Proper Task Cancellation Timing

**Fixed Interrupting Subprocess Logic:**
- Store tasks to cancel BEFORE executing recovery workflow
- Execute recovery workflow completely
- THEN cancel main process tasks

This ensures recovery completes successfully before main process is interrupted.

### 5. Example Workflow and Documentation

**Created Files:**
- `workflows/event-subprocess-error-example.yaml` - Payment processing with error recovery
- `context-examples/event-subprocess-error-context.json` - Test context
- `workflows/README-ERROR-SUBPROCESS.md` - Comprehensive user guide

## How It Works

### Workflow Structure

```yaml
elements:
  # Main Process
  - id: start1
    type: startEvent

  - id: task_process
    type: scriptTask
    # This task might fail

  # Error Event Sub-Process
  - id: error_subprocess
    type: eventSubProcess
    properties:
      isInterrupting: true  # Cancel main process
    childElements:
      - id: error_start
        type: errorStartEvent
        properties:
          errorCode: ""  # Catch all errors

      - id: recovery_task
        type: scriptTask
        name: Handle Error
```

### Execution Flow

**When Error Occurs:**
1. Task raises exception
2. `execute_task_body()` catches exception
3. `check_and_trigger_error_subprocess()` searches for handler
4. If found, triggers Event Sub-Process
5. Recovery workflow executes completely
6. If interrupting, main process tasks cancelled
7. Workflow completes with SUCCESS status

**Logging Output:**
```
🔍 Checking for error Event Sub-Process to handle: Exception: PaymentLimitExceeded
✅ Found matching error Event Sub-Process: Payment Error Recovery Handler
🎯 Triggering EVENT SUB-PROCESS
⚠️  Interrupting Event Sub-Process - will cancel main process flow after recovery
[Recovery tasks execute...]
🎯 Event Sub-Process completed: Payment Error Recovery Handler
✅ Error handled by Event Sub-Process: Payment Error Recovery Handler
✅ Workflow completed via Event Sub-Process: Payment Error Recovery Handler
```

## Error Matching Rules

### Catch All Errors
```yaml
errorCode: ""  # Empty string = catch ALL errors
```

### Catch Specific Error
```yaml
errorCode: "PaymentLimitExceeded"  # Only if error message contains this
```

The matcher checks: `error_code in str(error)`

## Interrupting vs Non-Interrupting

### Interrupting (Default)
```yaml
isInterrupting: true
```
- ✅ Stops main process after recovery completes
- ✅ Recovery workflow runs to completion first
- ✅ Use for: Critical errors, rollbacks, failure handling

### Non-Interrupting
```yaml
isInterrupting: false
```
- ✅ Main process continues
- ✅ Recovery runs in parallel
- ✅ Use for: Logging, notifications, monitoring

## Testing

### Test the Example
```bash
python3 test_simple.py \
  workflows/event-subprocess-error-example.yaml \
  context-examples/event-subprocess-error-context.json
```

### Expected Output
```
💳 Validating payment for order: ORD-2026-ERR-001
✅ Card validation successful

💰 Processing payment: $1500.0
❌ PAYMENT FAILED: Amount exceeds limit

🚨 ERROR RECOVERY: Payment processing failed!
📝 Error logged to database

📧 Sending failure notification to customer
✅ Customer notified of payment failure

💸 Initiating automatic refund
✅ Refund process started

✅ Workflow completed successfully!
```

## Benefits

1. **Clean Error Handling**
   - No ERROR logs when errors are properly handled
   - Clear success indicators
   - Proper workflow completion status

2. **Separation of Concerns**
   - Happy path in main process
   - Error handling in Event Sub-Process
   - Recovery logic isolated and reusable

3. **Flexible Recovery**
   - Interrupting or non-interrupting
   - Catch all errors or specific errors
   - Full context access for informed recovery

4. **Production Ready**
   - Proper task cancellation
   - Complete recovery before interruption
   - Success status when error handled

## Integration with Existing Features

- ✅ Works with boundary events (different scopes)
- ✅ Works with multi-instance tasks
- ✅ Works with compensation
- ✅ Works with nested subprocesses
- ✅ Works with pools and lanes

## Technical Details

### Files Modified
- `backend/workflow_engine.py`
  - Added `EventSubProcessHandledError` exception class
  - Added `check_and_trigger_error_subprocess()` method
  - Updated error handling in `execute_task_body()`
  - Updated error handling in `execute_from_element()`
  - Updated completion handling in `start_execution()`
  - Fixed interrupting subprocess task cancellation timing

### Key Changes
1. Line 20-29: New `EventSubProcessHandledError` exception
2. Line 470-489: Error catching and Event Sub-Process triggering in `execute_task_body()`
3. Line 209-213: Skip error logging for handled errors in `execute_from_element()`
4. Line 127-138: Success completion for handled errors in `start_execution()`
5. Line 1367-1373: Store tasks to cancel before recovery execution
6. Line 1416-1421: Cancel main process tasks AFTER recovery completes

## Future Enhancements

Potential improvements:
- Error event correlation by error code
- Error event data passing
- Multiple error Event Sub-Processes with priority
- Error retry mechanisms
- Error event broadcasting

## Related Documentation

- [Event Sub-Process Guide](EVENT_SUBPROCESS_GUIDE.md)
- [Timer Event Sub-Process Example](workflows/event-subprocess-timer-example.yaml)
- [Error Event Sub-Process README](workflows/README-ERROR-SUBPROCESS.md)
- [Boundary Events](BOUNDARY-EVENTS.md)
