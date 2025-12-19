# Approval Form Fix - Data Display & Rejection Handling

## Issues Fixed

### Issue 1: Approval Form Shows No Data ✅
**Problem:** When the approval form pops up, the "Data for Review" section is empty.

**Root Cause:** The UserTaskExecutor was only looking for `formFields` in properties, but the workflow doesn't specify which data to show.

**Fix:** Updated `backend/task_executors.py` (lines 43-58) to automatically include previous task results in the form data:

```python
# If no form fields specified, include previous task results
if not form_data:
    # Look for recent task results in context
    for key, value in context.items():
        if key.endswith('_result'):
            # Extract task name from key (e.g., "element_4_result" -> "element_4")
            task_name = key.replace('_result', '')
            form_data[f'{task_name} Results'] = value
```

**Result:** The approval form now shows the Agentic Task analysis results automatically!

---

### Issue 2: Workflow Continues After Rejection ✅
**Problem:** When you click "Reject" on the approval form, the workflow continues to the next tasks instead of stopping.

**Root Cause:** The workflow engine was not checking the decision from user tasks.

**Fix:** Updated `backend/workflow_engine.py` (lines 165-171) to check for rejection and stop:

```python
# Check if this was a user task that was rejected
if task.type == 'userTask':
    decision = self.context.get(f'{task.id}_decision')
    if decision == 'rejected':
        logger.warning(f"User task {task.name} was rejected, stopping workflow")
        # Raise exception to stop workflow
        raise Exception(f"Workflow terminated: User task '{task.name}' was rejected")
```

**Result:** Rejecting a user task now stops the entire workflow!

---

## How to Test

### Prerequisites

1. **Start MCP Servers:**
   ```bash
   ./start-mcp-servers.sh
   ```

2. **Start Backend:**
   ```bash
   cd backend
   python main.py
   ```

3. **Open UI:**
   ```bash
   open index.html
   ```

### Test 1: Approval Form Shows Data

1. **Import Workflow:**
   - Click "Import YAML"
   - Select `ai-log-analysis-workflow.yaml`
   - Workflow appears on canvas

2. **Execute Workflow:**
   - Click "▶ Execute Workflow"
   - Upload `sample-error.log` (or any log file)
   - Click "Start Execution"

3. **Watch Execution:**
   - Start Event executes
   - Receive Task executes
   - Store in S3 executes
   - **Agentic Task "Analyze Logs with MCP"** executes
     - Tool usage notifications appear
     - Analysis completes with findings
   - Generate Diagnostics executes
   - Gateway evaluates

4. **Approval Form Appears:**
   - Modal pops up with title: **"Review & Approve Diagnostics"**
   - **Check "Data for Review" section:**
     ```json
     {
       "element_4 Results": {
         "analysis": "Analysis completed using claude-3-opus",
         "log_file": "sample-error.log",
         "log_size": 2156,
         "tools_used": ["filesystem-read", "grep-search", "log-parser"],
         "confidence": 0.92,
         "findings": [
           "Found 8 errors, 6 warnings, 2 critical messages",
           "Potential disk space issue detected",
           "Potential memory issue detected"
         ]
       },
       "element_5 Results": {
         // Diagnostic generation results
       }
     }
     ```

5. **✅ Expected Result:** Form shows analysis data from previous Agentic Task!

---

### Test 2: Rejection Stops Workflow

**Same workflow, but this time we reject:**

1. **Execute workflow** (same as above)

2. **When approval form appears:**
   - Review the analysis results (should now show data!)
   - Add comments: "Analysis looks incorrect, rejecting"
   - Click **"✗ Reject"** button

3. **Expected Behavior:**
   - Modal closes
   - Notification appears: "Task Rejected - Your rejection has been submitted"
   - **Workflow STOPS** - no further elements execute
   - Console shows: `WARNING: User task Review & Approve Diagnostics was rejected, stopping workflow`
   - **Backend logs show:**
     ```
     WARNING:__main__:User task Review & Approve Diagnostics was rejected, stopping workflow
     ERROR:__main__:Error executing element Review & Approve Diagnostics: Workflow terminated: User task 'Review & Approve Diagnostics' was rejected
     ```

4. **✅ Expected Result:** Workflow terminates immediately, no playbook generation occurs!

---

### Test 3: Approval Continues Workflow

**Same workflow, but approve this time:**

1. **Execute workflow** (same as Test 1)

2. **When approval form appears:**
   - Review the analysis results
   - Add comments: "Analysis looks good, approved"
   - Click **"✓ Approve"** button

3. **Expected Behavior:**
   - Modal closes
   - Notification appears: "Task Approved - Your approval has been submitted"
   - **Workflow CONTINUES:**
     - Generate Ansible Playbook task executes
     - Validate Syntax task executes
     - Gateway evaluates
     - Store Playbook executes
     - Execute on Target Systems
     - Send Success Notification
     - Workflow Complete (End Event)

4. **✅ Expected Result:** Workflow completes all tasks successfully!

---

## What Changed in the Code

### File 1: `backend/task_executors.py`

**Location:** Lines 43-58

**Before:**
```python
# Extract form data from context
form_data = {}
for field in form_fields:
    if field in context:
        form_data[field] = context[field]
```

**After:**
```python
# Extract form data from context
form_data = {}

# Include form fields if specified
for field in form_fields:
    if field in context:
        form_data[field] = context[field]

# If no form fields specified, include previous task results
if not form_data:
    # Look for recent task results in context
    for key, value in context.items():
        if key.endswith('_result'):
            # Extract task name from key (e.g., "element_4_result" -> "element_4")
            task_name = key.replace('_result', '')
            form_data[f'{task_name} Results'] = value
```

**What it does:**
- Looks for any keys in context that end with `_result`
- These are created by task executors when they complete
- Includes them in the approval form data
- User sees all previous task outputs

---

### File 2: `backend/workflow_engine.py`

**Location:** Lines 165-171

**Before:**
```python
async def execute_task(self, task: Element):
    """Execute a task using appropriate executor"""
    logger.info(f"Executing task: {task.name} (type: {task.type})")

    # Get executor for task type
    executor = self.task_executors.get_executor(task.type)

    # Execute task and handle progress updates
    async for progress in executor.execute(task, self.context):
        # Broadcast progress to UI
        await self.agui_server.send_task_progress(...)

    logger.info(f"Task completed: {task.name}")
```

**After:**
```python
async def execute_task(self, task: Element):
    """Execute a task using appropriate executor"""
    logger.info(f"Executing task: {task.name} (type: {task.type})")

    # Get executor for task type
    executor = self.task_executors.get_executor(task.type)

    # Execute task and handle progress updates
    async for progress in executor.execute(task, self.context):
        # Broadcast progress to UI
        await self.agui_server.send_task_progress(...)

    # Check if this was a user task that was rejected
    if task.type == 'userTask':
        decision = self.context.get(f'{task.id}_decision')
        if decision == 'rejected':
            logger.warning(f"User task {task.name} was rejected, stopping workflow")
            # Raise exception to stop workflow
            raise Exception(f"Workflow terminated: User task '{task.name}' was rejected")

    logger.info(f"Task completed: {task.name}")
```

**What it does:**
- After a user task completes, checks the decision
- If decision is 'rejected', raises an exception
- Exception stops workflow execution immediately
- Error is logged and broadcast to UI

---

## Troubleshooting

### Approval Form Still Empty

**Check:**
1. Backend is running: `ps aux | grep "python main.py"`
2. WebSocket connected: Look for "✅ Connected" in browser status bar
3. Previous task completed: Check console for task completion logs
4. Context has results: Backend logs should show `element_X_result` being stored

**Solution:**
```bash
# Restart backend
cd backend
python main.py
```

### Workflow Still Continues After Rejection

**Check:**
1. Backend has latest code: `grep -n "rejected" backend/workflow_engine.py`
   - Should show line 168 with rejection check
2. Context has decision: Backend logs should show decision being stored
3. Task type is correct: Make sure it's a `userTask` not just `task`

**Solution:**
```bash
# Verify the fix is in place
cat backend/workflow_engine.py | grep -A 5 "Check if this was a user task"

# Should show:
# # Check if this was a user task that was rejected
# if task.type == 'userTask':
#     decision = self.context.get(f'{task.id}_decision')
#     if decision == 'rejected':
```

---

## Example: What You'll See

### Approval Form with Data

```
┌─────────────────────────────────────────────────┐
│ Review & Approve Diagnostics               × │
├─────────────────────────────────────────────────┤
│                                                 │
│ Assignee: devops@example.com                   │
│ Priority: High                                  │
│ Due: PT2H                                       │
│                                                 │
│ Data for Review:                                │
│ ┌─────────────────────────────────────────────┐ │
│ │ {                                           │ │
│ │   "element_4 Results": {                    │ │
│ │     "analysis": "Analysis completed...",    │ │
│ │     "log_file": "sample-error.log",         │ │
│ │     "confidence": 0.92,                     │ │
│ │     "findings": [                           │ │
│ │       "Found 8 errors, 6 warnings...",      │ │
│ │       "Potential disk space issue..."       │ │
│ │     ]                                       │ │
│ │   },                                        │ │
│ │   "element_5 Results": {                    │ │
│ │     "diagnosticSteps": [...]                │ │
│ │   }                                         │ │
│ │ }                                           │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ Comments:                                       │
│ ┌─────────────────────────────────────────────┐ │
│ │                                             │ │
│ │                                             │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ [✓ Approve]        [✗ Reject]                   │
└─────────────────────────────────────────────────┘
```

### Backend Logs - Rejection

```
INFO:__main__:Executing task: Review & Approve Diagnostics (type: userTask)
INFO:__main__:User task element_7 completed: rejected
WARNING:__main__:User task Review & Approve Diagnostics was rejected, stopping workflow
ERROR:__main__:Error executing element Review & Approve Diagnostics: Workflow terminated: User task 'Review & Approve Diagnostics' was rejected
```

### Backend Logs - Approval

```
INFO:__main__:Executing task: Review & Approve Diagnostics (type: userTask)
INFO:__main__:User task element_7 completed: approved
INFO:__main__:Task completed: Review & Approve Diagnostics
INFO:__main__:Executing element: Generate Ansible Playbook (agenticTask)
INFO:__main__:Executing task: Generate Ansible Playbook (type: agenticTask)
...
```

---

## Summary

✅ **Fixed Issue 1:** Approval form now shows previous task results automatically
✅ **Fixed Issue 2:** Rejecting a user task now stops the workflow immediately

**Changes made:**
- `backend/task_executors.py` - Auto-populate form data with task results
- `backend/workflow_engine.py` - Check for rejection and stop workflow

**Test with:**
```bash
# Start servers
./start-mcp-servers.sh

# Start backend
cd backend && python main.py

# Open UI
open index.html

# Import and execute: ai-log-analysis-workflow.yaml
```

**Your approval forms now work correctly!** 🎉
