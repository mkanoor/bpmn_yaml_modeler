# BPMN Boundary Events - Error Handling Guide

## Overview

In BPMN, **Boundary Events** are the standard way to handle exceptions, timeouts, and other exceptional conditions. They attach to the border of activities and "catch" specific events.

---

## Types of Boundary Events

### 1. Error Boundary Event ⚠️
**Purpose:** Catch exceptions and errors (like try-catch in programming)

**Use Cases:**
- Script execution errors
- Service call failures
- Validation errors
- Database connection failures

**Visual:** Small circle on task boundary with lightning bolt icon ⚡

**Behavior:**
- **Interrupting** (default) - Stops the task when error occurs
- Task is marked as failed
- Flow continues on error path
- Original task path is NOT taken

**Example:**
```
┌─────────────────┐
│  Execute Script │ ⚡─→ [Handle Error] → End
│  (may fail)     │
└─────────────────┘
         ↓
    [Normal Path]
```

---

### 2. Timer Boundary Event ⏰
**Purpose:** Handle timeouts and time-based interruptions

**Use Cases:**
- Task execution timeout
- SLA violations
- Maximum wait time for user tasks
- Scheduled interruptions

**Visual:** Small circle with clock icon 🕐

**Behavior:**
- **Interrupting** - Cancels task when timer expires
- **Non-interrupting** - Triggers action but task continues

**Example:**
```
┌─────────────────┐
│  Wait for       │ ⏰─→ [Timeout Handler] → Escalate
│  Approval       │
│  (User Task)    │
└─────────────────┘
         ↓
    [Approved]
```

**Timer Formats:**
- `PT30S` - 30 seconds
- `PT5M` - 5 minutes
- `PT1H` - 1 hour
- `P1D` - 1 day
- ISO 8601 duration format

---

### 3. Escalation Boundary Event 🔺
**Purpose:** Escalate to higher authority without stopping task

**Use Cases:**
- Notify supervisor of delays
- Trigger additional checks
- Alert management
- Non-critical issues

**Visual:** Small circle with up-arrow icon ↗️

**Behavior:**
- **Non-interrupting** (typical) - Task continues
- Parallel flow for escalation
- Original task can still complete normally

---

### 4. Signal/Message Boundary Event 📨
**Purpose:** React to external signals or messages

**Use Cases:**
- Cancellation requests
- Priority changes
- External notifications
- Cross-process communication

---

## Error Boundary Event - Detailed Guide

### Configuration

**YAML Structure:**
```yaml
elements:
  # Task that might fail
  - id: task_1
    type: scriptTask
    name: Risky Operation
    properties:
      scriptFormat: Python
      script: |
        # May throw error
        result = process_data()

  # Error boundary event attached to task_1
  - id: error_boundary_1
    type: errorBoundaryEvent
    name: Catch Error
    attachedToRef: task_1  # KEY: Links to parent task
    cancelActivity: true    # Interrupting (default)
    properties:
      errorCode: ""         # Empty = catch all errors
      # OR specific: "ValidationError", "TimeoutError", etc.

connections:
  # Normal flow (if no error)
  - from: task_1
    to: next_task

  # Error flow (if error occurs)
  - from: error_boundary_1
    to: error_handler_task
```

### Error Handling Patterns

#### Pattern 1: Catch All Errors
```yaml
- id: boundary_catch_all
  type: errorBoundaryEvent
  attachedToRef: risky_task
  properties:
    errorCode: ""  # Catches ANY error
```

#### Pattern 2: Catch Specific Errors
```yaml
- id: boundary_validation_error
  type: errorBoundaryEvent
  attachedToRef: validate_task
  properties:
    errorCode: "ValidationError"  # Only catches ValidationError
```

#### Pattern 3: Multiple Error Handlers
```yaml
# Attach multiple boundary events to same task
- id: boundary_timeout
  type: errorBoundaryEvent
  attachedToRef: api_call_task
  properties:
    errorCode: "TimeoutError"

- id: boundary_connection
  type: errorBoundaryEvent
  attachedToRef: api_call_task
  properties:
    errorCode: "ConnectionError"

- id: boundary_other
  type: errorBoundaryEvent
  attachedToRef: api_call_task
  properties:
    errorCode: ""  # Catch any other error
```

---

## Timer Boundary Event - Detailed Guide

### Configuration

**YAML Structure:**
```yaml
- id: timer_boundary_1
  type: timerBoundaryEvent
  name: 30 Second Timeout
  attachedToRef: long_running_task
  cancelActivity: true  # Interrupting
  properties:
    timerDuration: "PT30S"  # ISO 8601 duration
    # OR
    timerDate: "2024-12-31T23:59:59Z"  # Specific datetime
```

### Timer Patterns

#### Pattern 1: Task Timeout
```yaml
- id: user_approval_task
  type: userTask
  name: Review and Approve

- id: timeout_boundary
  type: timerBoundaryEvent
  attachedToRef: user_approval_task
  cancelActivity: true
  properties:
    timerDuration: "PT2H"  # 2 hours

connections:
  - from: timeout_boundary
    to: auto_approve_task  # Fallback if no response
```

#### Pattern 2: Non-Interrupting Reminder
```yaml
- id: reminder_boundary
  type: timerBoundaryEvent
  attachedToRef: user_approval_task
  cancelActivity: false  # Non-interrupting
  properties:
    timerDuration: "PT1H"  # 1 hour

connections:
  - from: reminder_boundary
    to: send_reminder_email  # Send reminder but task continues
```

#### Pattern 3: Escalation Ladder
```yaml
# Multiple timers for escalation
- id: reminder_1h
  type: timerBoundaryEvent
  attachedToRef: approval_task
  cancelActivity: false
  properties:
    timerDuration: "PT1H"

- id: escalation_4h
  type: timerBoundaryEvent
  attachedToRef: approval_task
  cancelActivity: false
  properties:
    timerDuration: "PT4H"

- id: timeout_8h
  type: timerBoundaryEvent
  attachedToRef: approval_task
  cancelActivity: true  # Finally cancel
  properties:
    timerDuration: "PT8H"
```

---

## Complete Example: Robust Task with Error Handling

```yaml
elements:
  # Risky API call task
  - id: api_call_task
    type: serviceTask
    name: Call External API
    properties:
      serviceUrl: "https://api.example.com/data"
      timeout: 30000

  # Error boundary - catches exceptions
  - id: error_boundary
    type: errorBoundaryEvent
    name: Catch API Error
    attachedToRef: api_call_task
    cancelActivity: true
    properties:
      errorCode: ""

  # Timer boundary - catches timeouts
  - id: timeout_boundary
    type: timerBoundaryEvent
    name: 30s Timeout
    attachedToRef: api_call_task
    cancelActivity: true
    properties:
      timerDuration: "PT30S"

  # Error handler task
  - id: handle_error
    type: scriptTask
    name: Log Error & Retry
    properties:
      scriptFormat: Python
      script: |
        error_type = context.get('errorType', 'unknown')
        print(f"Error occurred: {error_type}")
        result = {'retry': True, 'attempts': context.get('attempts', 0) + 1}

  # Success path
  - id: process_result
    type: scriptTask
    name: Process API Response

connections:
  # Normal flow
  - from: api_call_task
    to: process_result

  # Error flow
  - from: error_boundary
    to: handle_error

  # Timeout flow
  - from: timeout_boundary
    to: handle_error
```

**Visual Diagram:**
```
                    ⚡ Error
                     ↓
┌─────────────────┐  ┌──────────────┐
│  Call External  │  │ Log Error &  │
│  API            │→ │ Retry        │
└─────────────────┘  └──────────────┘
         ↓ ⏰ Timeout
         ↓
    [Process Result]
```

---

## Implementation in Workflow Engine

### Backend Requirements

1. **Attach boundary events to tasks**
   - Store `attachedToRef` to link boundary to parent task
   - Position boundary on task border in UI

2. **Error catching mechanism**
   ```python
   try:
       await execute_task(task)
   except Exception as e:
       # Find error boundary events attached to this task
       error_boundaries = find_boundary_events(task.id, type='error')

       for boundary in error_boundaries:
           if matches_error_code(e, boundary.errorCode):
               # Trigger error boundary flow
               await execute_from_element(boundary.id)
               return  # Don't continue normal flow

       # No matching boundary - re-raise
       raise
   ```

3. **Timer implementation**
   ```python
   # Start timer when task starts
   timer_task = asyncio.create_task(
       wait_for_timeout(duration)
   )

   # Race between task completion and timeout
   done, pending = await asyncio.wait(
       {task_future, timer_task},
       return_when=asyncio.FIRST_COMPLETED
   )

   if timer_task in done:
       # Timeout occurred - trigger boundary event
       await execute_from_element(timer_boundary.id)
   ```

---

## Token Animation with Boundary Events

### Error Boundary Token Flow

**Normal Flow:**
```
🔵 Token → Task → ✅ Complete → Token moves to next task
```

**Error Flow:**
```
🔵 Token → Task → ❌ Error! → 🔴 Token jumps to boundary event → Error handler
                             ↓
                     (original path NOT taken)
```

### Timer Boundary Token Flow

**Interrupting Timer:**
```
🔵 Token → Task (running...) → ⏰ Timeout! → 🟡 Token to timeout handler
                               ↓
                        (task cancelled)
```

**Non-Interrupting Timer:**
```
🔵 Token → Task (running...) → ⏰ Timer! → 🟡 Clone token → Reminder sent
            ↓                              ↓
    (continues running)              (parallel flow)
            ↓
         Complete → Token continues
```

---

## Best Practices

### 1. Always Handle Errors for Critical Tasks
```yaml
# BAD - No error handling
- id: critical_payment
  type: serviceTask
  name: Process Payment
  # If this fails, workflow dies

# GOOD - Error boundary for resilience
- id: critical_payment
  type: serviceTask
  name: Process Payment

- id: payment_error
  type: errorBoundaryEvent
  attachedToRef: critical_payment
  → to: notify_admin_task
```

### 2. Use Timeouts for External Calls
```yaml
- id: api_call
  type: serviceTask

- id: api_timeout
  type: timerBoundaryEvent
  attachedToRef: api_call
  properties:
    timerDuration: "PT30S"  # Don't wait forever
```

### 3. Non-Interrupting for Notifications
```yaml
# Send reminder after 1 hour, but keep waiting
- id: reminder_timer
  type: timerBoundaryEvent
  attachedToRef: approval_task
  cancelActivity: false  # Non-interrupting
```

### 4. Specific Error Codes for Different Paths
```yaml
# Route different errors to different handlers
- type: errorBoundaryEvent
  attachedToRef: data_task
  properties:
    errorCode: "ValidationError"
  → to: fix_data_task

- type: errorBoundaryEvent
  attachedToRef: data_task
  properties:
    errorCode: "PermissionError"
  → to: request_permission_task
```

---

## Comparison: Try-Catch vs Boundary Events

### Programming (Python)
```python
try:
    result = risky_operation()
    process_result(result)
except ValueError as e:
    handle_validation_error(e)
except TimeoutError as e:
    handle_timeout(e)
except Exception as e:
    handle_generic_error(e)
```

### BPMN Equivalent
```
┌────────────────┐ ⚡ ValidationError → [Handle Validation]
│ Risky          │ ⚡ TimeoutError → [Handle Timeout]
│ Operation      │ ⚡ (any error) → [Handle Generic]
└────────────────┘
        ↓
  [Process Result]
```

Both achieve the same goal, but BPMN is visual and declarative!

---

## Summary

**Boundary Events are the BPMN standard for:**
- ✅ Exception handling (Error Boundary)
- ✅ Timeout handling (Timer Boundary)
- ✅ Escalation (Escalation Boundary)
- ✅ External interruptions (Signal/Message Boundary)

**Key Benefits:**
- Visual representation of error flows
- Declarative exception handling
- Standard BPMN notation
- Token animation shows error paths
- Non-interrupting options for parallel handling

**Next Steps:**
1. Implement Error Boundary Events in backend
2. Implement Timer Boundary Events
3. Add boundary event UI elements to palette
4. Update deadlock example to use proper error handling
