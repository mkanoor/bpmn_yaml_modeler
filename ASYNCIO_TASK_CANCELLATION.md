# Asyncio Task Cancellation Implementation

## Overview

This implementation adds proper asyncio task cancellation to the workflow engine, ensuring that when a competing approval path completes first in a dual approval workflow, the other path is **immediately cancelled** instead of continuing to wait.

## Problem Statement

### Before This Implementation:

When one approval path completed first:
1. ✅ Gateway marked as completed (first path wins)
2. ✅ UI cancellation event sent
3. ✅ Task removed from `active_tasks`
4. ❌ **But the asyncio task kept running in the background!**

**Example:**
- Manual approval completes at T+0
- Email receive task keeps waiting until timeout (2 hours!)
- Email denial arrives at T+10 minutes
- Receive task processes the denial (wasted work)
- Gateway rejects the path (but only after unnecessary processing)

### After This Implementation:

When one approval path completes first:
1. ✅ Gateway marked as completed (first path wins)
2. ✅ **Asyncio task immediately cancelled**
3. ✅ UI cancellation event sent
4. ✅ Task removed from tracking
5. ✅ Execution path stops immediately

**Example:**
- Manual approval completes at T+0
- **Email receive task is cancelled immediately**
- Email denial arrives at T+10 minutes
- **Message is ignored (no task waiting for it)**
- No wasted resources!

## Implementation Details

### 1. Asyncio Task Tracking

Added `running_tasks` dict to track asyncio tasks:

```python
# workflow_engine.py
self.running_tasks: Dict[str, asyncio.Task] = {}
```

When a task starts executing:
```python
current_task = asyncio.current_task()
if current_task:
    self.running_tasks[task.id] = current_task
    logger.info(f"📌 Registered asyncio task for {task.id}")
```

### 2. Task Cancellation

In `cancel_competing_tasks()`, we now cancel the actual asyncio task:

```python
if task.id in self.running_tasks:
    asyncio_task = self.running_tasks[task.id]
    logger.info(f"🔴 Cancelling asyncio task for {task.id}")
    asyncio_task.cancel()

    # Wait for cancellation to propagate
    try:
        await asyncio.wait_for(asyncio.shield(asyncio_task), timeout=0.1)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass  # Expected

    del self.running_tasks[task.id]
    logger.info(f"✅ Asyncio task cancelled and removed")
```

### 3. Cancellation Handling

#### In `execute_task()`:
```python
try:
    # Execute task...
    async for progress in executor.execute(task, self.context):
        # ...
except asyncio.CancelledError:
    logger.info(f"🛑 Task {task.id} ({task.name}) was cancelled")
    # Cleanup and re-raise
    raise
finally:
    # Always cleanup
    if task.id in self.active_tasks:
        del self.active_tasks[task.id]
    if task.id in self.running_tasks:
        del self.running_tasks[task.id]
```

#### In `execute_from_element()`:
```python
# Parallel execution with graceful cancellation
tasks = [self.execute_from_element(elem) for elem in next_elements]
results = await asyncio.gather(*tasks, return_exceptions=True)

# Log cancellations but don't propagate
for i, result in enumerate(results):
    if isinstance(result, asyncio.CancelledError):
        logger.info(f"✅ Parallel path {i} was cancelled (expected)")
```

#### In Task Executors:

**UserTaskExecutor:**
```python
try:
    completion_data = await self.agui_server.wait_for_user_task_completion(task.id)
    # Process completion...
except asyncio.CancelledError:
    logger.info(f"🛑 User task {task.id} cancelled")
    yield TaskProgress(status='cancelled', message='Task cancelled', progress=0.5)
    raise
```

**ReceiveTaskExecutor:**
```python
try:
    message = await message_queue.wait_for_message(...)
    # Process message...
except asyncio.CancelledError:
    logger.info(f"🛑 Task {task.id} cancelled while waiting for webhook")
    yield TaskProgress(status='cancelled', message='Task cancelled', progress=0.5)
    raise
```

## Flow Diagram

### Dual Approval with Cancellation:

```
Parallel Gateway
    ├─→ Email Path (element_22 → element_23)
    │   - Send Email
    │   - Receive Task WAITS for webhook
    │   - Asyncio task registered in running_tasks
    │
    └─→ Manual Path (element_7)
        - User Task WAITS for manual approval
        - Asyncio task registered in running_tasks

↓ User approves manually

Manual Path Completes First:
    ├─→ Reaches Inclusive Gateway (element_24)
    ├─→ Gateway marks itself as completed
    ├─→ cancel_competing_tasks() called
    │   ├─→ Finds element_23 in active_tasks
    │   ├─→ Finds asyncio task in running_tasks
    │   ├─→ Calls asyncio_task.cancel()
    │   └─→ Sends task.cancelled UI event
    │
    └─→ Workflow continues with manual approval

Email Path (Being Cancelled):
    ├─→ Receive task gets CancelledError
    ├─→ Yields TaskProgress(status='cancelled')
    ├─→ Cleanup in finally block
    └─→ Execution path stops

↓ 10 minutes later, email denial arrives

Email webhook arrives:
    ├─→ Message queue receives it
    ├─→ No task waiting for this correlation key
    └─→ Message is ignored (or times out in queue)
```

## Benefits

1. **Resource Efficiency**
   - No wasted CPU cycles waiting for messages that won't be processed
   - Immediate cleanup of waiting tasks
   - Reduced memory usage

2. **Predictable Behavior**
   - Tasks stop immediately when cancelled
   - No surprise message processing after cancellation
   - Clear logging of cancellation flow

3. **Correct BPMN Semantics**
   - Inclusive gateway merge: first path wins, others truly stop
   - Parallel paths can be properly cancelled
   - Gateway merge points work as expected

4. **Better Debugging**
   - Clear logging with 🔴 🛑 ✅ emojis
   - Track which asyncio tasks are running
   - See exactly when and why cancellation occurs

## Logging Output

When cancellation works correctly:

```
INFO - 📌 Registered asyncio task for element_23
INFO - 📌 Registered asyncio task for element_7

... Manual approval completes first ...

INFO - === cancel_competing_tasks called for gateway element_24 ===
INFO - Running asyncio tasks: ['element_23', 'element_7']
INFO - Checking incoming connection from: element_23
INFO - ✅ CANCELLING task element_23 (Await Email Response)
INFO - 🔴 Cancelling asyncio task for element_23
INFO - ✅ Asyncio task cancelled and removed
INFO - 📤 SENDING task.cancelled event for element: element_23
INFO - 🛑 Task element_23 cancelled while waiting for webhook
INFO - 🛑 Execution path cancelled at Await Email Response
INFO - ✅ Parallel path 0 was cancelled (expected for merge gateways)
```

## Testing

### Test Scenario 1: Email Approves First
1. Start workflow
2. Both email and manual approval paths start
3. Click email approval link
4. **Expected:** Manual approval popup closes immediately
5. **Expected:** Logs show user task cancelled

### Test Scenario 2: Manual Approves First
1. Start workflow
2. Both email and manual approval paths start
3. Click "Approve" on popup
4. **Expected:** Receive task cancelled immediately
5. **Expected:** Email denial arriving later is ignored

### Test Scenario 3: Email Denies First
1. Start workflow
2. Both paths start
3. Click email denial link
4. **Expected:** Manual approval popup closes
5. **Expected:** Workflow stops (rejection path)

## Files Modified

1. **backend/workflow_engine.py**
   - Added `running_tasks` tracking dict
   - Modified `cancel_competing_tasks()` to cancel asyncio tasks
   - Added CancelledError handling in `execute_task()`
   - Modified `execute_from_element()` to handle parallel cancellations
   - Enhanced logging throughout

2. **backend/task_executors.py**
   - Added CancelledError handling in `UserTaskExecutor`
   - Added CancelledError handling in `ReceiveTaskExecutor`
   - Both yield 'cancelled' status progress before re-raising

## Edge Cases Handled

1. **Task completes before cancellation**
   - Check if task.id still in running_tasks before cancelling
   - Gracefully handle if task already removed

2. **Multiple parallel paths**
   - `gather(..., return_exceptions=True)` prevents one cancellation from breaking others
   - Log each cancellation individually

3. **Nested cancellations**
   - CancelledError propagates up through execution stack
   - Finally blocks ensure cleanup always happens

4. **Race conditions**
   - Locks in gateway merge prevent concurrent cancellation
   - Asyncio shield used during cancellation wait

## Future Enhancements

Possible improvements:
1. Add cancellation reason to CancelledError for better tracking
2. Support for cancellation callbacks (cleanup hooks)
3. Metrics/monitoring for cancellation events
4. Configurable cancellation timeout
5. Support for graceful vs immediate cancellation

## Backward Compatibility

✅ **Fully backward compatible**
- Workflows without parallel gateways work unchanged
- Single-path workflows unaffected
- Only enhances behavior of inclusive/parallel gateway merges
- No breaking changes to existing APIs

## Performance Impact

Minimal overhead:
- ✅ One dict lookup per task (running_tasks)
- ✅ One asyncio.current_task() call per task
- ✅ Cancellation only occurs at gateway merges (rare)
- ✅ No impact on single-path workflows
- ✅ Actually improves performance by stopping unnecessary work
