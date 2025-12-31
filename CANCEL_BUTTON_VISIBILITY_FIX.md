# Cancel Button Visibility Fix

## Problem

User reported: "The Cancel Task should only be visible when the task is running and should not get displayed if the Task has ended"

**Issue**: The Cancel Task button remained visible in the Task Activity panel even after the task had completed, which was confusing and inappropriate since completed tasks cannot be cancelled.

## Root Cause

The cancel button was added when the task became cancellable (`task.cancellable` event), but was only removed in two scenarios:
1. When user clicked cancel and the task was cancelled
2. When a task cancellation failed

**Missing removal scenarios**:
- When task completed successfully (normal completion)
- When viewing replay of a completed task

## Solution Implemented

### 1. Remove Cancel Button on Task Completion

**Added to `markElementComplete()` method**:

```javascript
markElementComplete(elementId) {
    // ... existing completion logic ...

    // Remove cancel button from feedback panel since task has completed
    this.removeCancelButton(elementId);

    // Mark task as no longer cancellable
    this.cancellableTasks.delete(elementId);
}
```

**New helper method**:

```javascript
removeCancelButton(elementId) {
    const panel = document.getElementById(`feedback-panel-${elementId}`);
    if (panel) {
        const contentDiv = panel.querySelector('.feedback-content');
        if (contentDiv) {
            const cancelBtn = contentDiv.querySelector('.cancel-task-btn');
            if (cancelBtn) {
                console.log(`🗑️ Removing cancel button for completed task: ${elementId}`);
                cancelBtn.remove();
            }
        }
    }
}
```

### 2. Ensure Cancel Button Removed During Replay

**Added to `handleMessagesSnapshot()` method** (end of replay):

```javascript
handleMessagesSnapshot(message) {
    // ... render all replay events ...

    // Ensure cancel button is removed for replayed (completed) tasks
    this.removeCancelButton(message.elementId);
    this.cancellableTasks.delete(message.elementId);

    console.log('📼 Replay complete - panel populated with history in chronological order');
}
```

**Note**: While `panel.innerHTML = ''` at the start of replay already clears the cancel button, this explicit removal ensures it's cleaned up from the tracking sets as well.

## Cancel Button Lifecycle

### Complete Flow

1. **Task Starts** → No cancel button
2. **Task Becomes Cancellable** → `task.cancellable` event → Cancel button added
3. **One of the following happens**:

   **Scenario A: Task Completes Successfully**
   - `element.completed` event → `markElementComplete()` called
   - ✅ Cancel button removed
   - ✅ Task removed from `cancellableTasks` set

   **Scenario B: User Cancels Task**
   - User clicks cancel button
   - `task.cancelled` event → `handleTaskCancelled()` called
   - ✅ Cancel button removed
   - ✅ Task removed from `cancellableTasks` set

   **Scenario C: Cancel Fails**
   - Cancel request fails
   - `task.cancel.failed` event → `handleTaskCancelFailed()` called
   - ✅ Cancel button re-enabled (not removed, since task still running)

   **Scenario D: Replay of Completed Task**
   - User clicks feedback bubble
   - `messages.snapshot` event → `handleMessagesSnapshot()` called
   - ✅ Panel cleared (`innerHTML = ''`)
   - ✅ Cancel button explicitly removed
   - ✅ Task removed from `cancellableTasks` set

## Expected Behavior

### Before Fix
- ❌ Cancel button visible after task completed
- ❌ Cancel button visible during replay
- ❌ User confused about whether task can still be cancelled
- ❌ Clicking cancel on completed task did nothing (but button was still there)

### After Fix
- ✅ Cancel button only visible while task is actively running
- ✅ Cancel button removed immediately when task completes
- ✅ Cancel button never appears during replay
- ✅ Clear visual indication of task state (running vs completed)

## Testing

1. **Test Normal Completion**:
   - Start an agentic task
   - Wait for "Cancel Task" button to appear
   - Wait for task to complete
   - ✅ Verify cancel button disappears when task completes

2. **Test User Cancellation**:
   - Start an agentic task
   - Click "Cancel Task" button
   - ✅ Verify button changes to "Cancelling..."
   - ✅ Verify button is removed after cancellation completes

3. **Test Replay**:
   - Complete a task (with or without cancelling)
   - Close and reopen the feedback panel (click 💬 bubble)
   - ✅ Verify cancel button does NOT appear during replay
   - ✅ Verify only historical events are shown

4. **Test Multiple Tasks**:
   - Run workflow with multiple agentic tasks
   - First task completes → cancel button removed
   - Second task still running → cancel button still visible
   - ✅ Verify each task's cancel button is independent

## Files Modified

- `/agui-client.js`:
  - Modified `markElementComplete()` to remove cancel button
  - Added `removeCancelButton()` helper method
  - Modified `handleMessagesSnapshot()` to ensure cancel button removed during replay

## Related Code

- `handleTaskCancellable()` - Adds cancel button when task becomes cancellable
- `handleTaskCancelled()` - Removes cancel button when task is cancelled
- `handleTaskCancelFailed()` - Re-enables cancel button if cancellation fails
- `markElementComplete()` - Now removes cancel button when task completes
- `handleMessagesSnapshot()` - Now removes cancel button during replay
