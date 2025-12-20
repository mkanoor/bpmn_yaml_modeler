# Dual Approval Cancellation - Testing Guide

## What Was Implemented

### Backend Changes
1. **Active Task Tracking** (`workflow_engine.py`)
   - Tasks are added to `active_tasks` dict when they start executing
   - Tasks are removed when they complete
   - This allows us to identify which tasks are still waiting

2. **Inclusive Gateway Merge Logic** (`workflow_engine.py`)
   - First path to reach the merge gateway wins
   - Other paths are stopped (return empty list)
   - Competing tasks are cancelled via `cancel_competing_tasks()`

3. **Task Cancellation** (`workflow_engine.py`, `agui_server.py`)
   - New method: `cancel_competing_tasks()`
   - Sends `task.cancelled` WebSocket event to UI
   - Includes reason for cancellation

4. **Comprehensive Logging**
   - Logs when tasks are added/removed from active_tasks
   - Logs gateway merge decisions
   - Logs cancellation events being sent
   - Logs WebSocket broadcast status

### Frontend Changes
1. **Modal Data Attribute** (`agui-client.js`)
   - Approval modals tagged with `data-task-id` attribute
   - Allows precise targeting for cancellation

2. **Cancellation Handler** (`agui-client.js`)
   - Listens for `task.cancelled` events
   - Finds modal by task ID
   - Closes modal with fade animation
   - Shows notification explaining cancellation
   - Marks element as cancelled on canvas

3. **Enhanced Logging**
   - Logs when cancellation messages received
   - Logs modal search and closure
   - Logs all modals in DOM if not found

## The Previous Issue

The logs you shared showed TWO DIFFERENT workflow instances:
```
Manual approval waiting: correlation key 69bdb0fd-3d85-4eb9-abce-d46f27be641d
Email approval sent:     correlation key e22f6ff1-a1fb-4223-bdaf-aa8ff7d6a858
```

These are different workflow instances! The cancellation logic only works within the SAME instance.

## How to Test Properly

### Step 1: Start Fresh Workflow Instance

Run the test script:
```bash
cd /Users/madhukanoor/devsrc/bpmn
./test_dual_approval.sh
```

OR manually trigger via curl:
```bash
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "yaml": "..."  # Full YAML content
    "context": {
      "logFileName": "test-error.log",
      "logFileContent": "ERROR: Test error",
      "issueCount": "1",
      "severityLevel": "High",
      "diagnosticSteps": "Fix the error"
    }
  }'
```

### Step 2: Observe Parallel Paths

Within a few seconds:
1. ✅ Manual approval popup appears in UI
2. ✅ Email is sent with approval links
3. ✅ Both use the SAME `workflowInstanceId` as correlation key

### Step 3: Test Cancellation

**Scenario A: Approve via Email First**
1. Click the approval link in the email
2. Click "Approve" on confirmation page
3. **Expected:** Manual approval popup should automatically close
4. **Expected:** Notification: "Approval Cancelled - Another approval path completed first"

**Scenario B: Approve via Manual Popup First**
1. Click "Approve" on the popup
2. **Expected:** Email webhook will timeout (but won't block workflow)
3. **Expected:** Workflow continues with manual approval

### Step 4: Check Backend Logs

Look for these log entries:

**When gateway is reached:**
```
INFO - Executing gateway: Either Approved? (type: inclusiveGateway)
INFO - Current active_tasks when entering gateway: ['element_7', 'element_23']
INFO - Incoming connections to gateway element_24: ['element_23 -> element_24', 'element_7 -> element_24']
INFO - Gateway element_24 is a merge point with 2 incoming paths
```

**When first path wins:**
```
INFO - Inclusive gateway element_24: First path to arrive - continuing
INFO - === cancel_competing_tasks called for gateway element_24 (Either Approved?) ===
INFO - Number of incoming connections: 2
INFO - Active tasks: ['element_7']  # The OTHER task is still waiting!
INFO - Checking incoming connection from: element_23
INFO - ❌ Task element_23 not in active_tasks (already completed or not started)
INFO - Checking incoming connection from: element_7
INFO - ✅ CANCELLING task element_7 (Manual Review & Approve) - competing path lost to merge
INFO - 📤 SENDING task.cancelled event for element: element_7
INFO -    Reason: Another approval path completed first at Either Approved?
INFO -    Connected clients: 1
INFO - ✅ task.cancelled event sent successfully
```

**When second path arrives:**
```
INFO - Inclusive gateway element_24: Another path already passed - stopping this path
INFO - === cancel_competing_tasks called for gateway element_24 (Either Approved?) ===
INFO - Active tasks: []  # All tasks already completed or cancelled
```

### Step 5: Check Frontend Console

Look for these console entries:

```javascript
📨 Received: task.cancelled {elementId: "element_7", reason: "..."}
🚫🚫🚫 TASK CANCELLED MESSAGE RECEIVED 🚫🚫🚫
   Element ID: element_7
   Reason: Another approval path completed first at Either Approved?
🚫 handleTaskCancelled called
   Element ID: element_7
   Reason: Another approval path completed first at Either Approved?
   Looking for modal with selector: .approval-modal[data-task-id="element_7"]
   Modal found: <div class="approval-modal active">...</div>
✅ CLOSING modal for task: element_7
✅ Modal removed from DOM
```

## Debugging Tips

### If popup doesn't close:

1. **Check correlation keys match:**
   - Backend logs should show SAME correlation key for both paths
   - Look for: `correlation: <same-uuid>` in both email and manual approval logs

2. **Check active_tasks contains the manual approval:**
   - Look for: `Active tasks: ['element_7']` when gateway is reached
   - If empty, the task already completed before gateway was reached

3. **Check WebSocket connection:**
   - Frontend should show: `✅ Connected to AG-UI server`
   - Backend should show: `Connected clients: 1` (or more)

4. **Check modal selector:**
   - Verify modal has attribute: `data-task-id="element_7"`
   - Check if selector finds modal: `Modal found: <div>...`

5. **Check timing:**
   - Email approval might arrive BEFORE manual popup renders
   - Try waiting a few seconds after popup appears before clicking email link

## Expected Workflow Flow

```
START
  ↓
Parallel Gateway (element_21) - splits into 2 paths
  ├─→ Email Path (element_22 → element_23)
  └─→ Manual Path (element_7)
       ↓
  Both paths execute in parallel via asyncio.gather()
       ↓
  First path to complete reaches Inclusive Gateway (element_24)
       ├─→ Marks gateway as completed
       ├─→ Cancels competing task on other path
       └─→ Continues workflow
       ↓
  Second path reaches gateway
       └─→ Sees gateway already completed
       └─→ Stops execution (returns empty list)
       ↓
  Workflow continues from winning path
```

## Files Modified

### Backend
- `backend/workflow_engine.py` - Active task tracking, merge logic, cancellation
- `backend/agui_server.py` - Cancellation event sender
- `backend/main.py` - POST-based email approval webhooks

### Frontend
- `agui-client.js` - Cancellation handler, modal closing logic

### Test Files
- `test_dual_approval.sh` - Quick test script
- `DUAL_APPROVAL_TESTING.md` - This guide

## Next Steps

1. Run the test script to trigger a fresh workflow
2. Check that both paths start simultaneously
3. Approve via email and verify popup closes
4. Review logs to ensure cancellation events are sent/received
5. If issues persist, share the complete logs from both backend and frontend
