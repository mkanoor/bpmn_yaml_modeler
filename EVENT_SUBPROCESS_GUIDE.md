# Event Sub-Process Guide

## Overview

Event Sub-Processes are a powerful BPMN 2.0 feature that allows workflows to react to events independently from the main process flow. Unlike regular subprocesses that are triggered by sequence flow, Event Sub-Processes are triggered by specific events and can run in parallel with or interrupt the main process.

## Key Characteristics

1. **Event-Driven**: Started by events (timer, error, message, signal, escalation) instead of sequence flow
2. **Independent Monitoring**: Runs independently, waiting for events to occur
3. **Interrupting or Non-Interrupting**: Can either cancel the main process or run in parallel
4. **Automatic Activation**: Starts monitoring as soon as the workflow begins

## Supported Event Types

### 1. Timer Start Event (`timerStartEvent`)
Triggers the subprocess after a specified time duration.

**Properties:**
- `timerDuration`: ISO 8601 duration (e.g., `PT5S` for 5 seconds, `PT30M` for 30 minutes)

**Use Cases:**
- SLA monitoring and escalations
- Timeout handling
- Scheduled reminders

### 2. Error Start Event (`errorStartEvent`)
Triggers when a specific error occurs in the parent process.

**Properties:**
- `errorCode`: Error code to catch (empty catches all errors)

**Use Cases:**
- Error recovery workflows
- Fallback processes
- Error logging and notification

### 3. Message Start Event (`messageStartEvent`)
Triggers when a specific message is received.

**Properties:**
- `messageRef`: Message identifier to listen for

**Use Cases:**
- External system notifications
- Asynchronous communication
- Event-driven updates

### 4. Signal Start Event (`signalStartEvent`)
Triggers when a broadcast signal is sent.

**Properties:**
- `signalRef`: Signal identifier to listen for

**Use Cases:**
- Broadcast notifications
- Process coordination
- System-wide events

### 5. Escalation Start Event (`escalationStartEvent`)
Triggers when an escalation is raised.

**Properties:**
- `escalationCode`: Escalation code to catch

**Use Cases:**
- Management escalations
- Priority handling
- Alert workflows

## Interrupting vs Non-Interrupting

### Interrupting Event Sub-Process
- **Behavior**: Cancels the main process when triggered
- **Configuration**: `isInterrupting: true` (default)
- **Use Cases**:
  - Critical errors that require stopping the main process
  - Hard timeouts
  - Cancellation requests

### Non-Interrupting Event Sub-Process
- **Behavior**: Runs in parallel with the main process
- **Configuration**: `isInterrupting: false`
- **Use Cases**:
  - Logging and monitoring
  - Parallel notifications
  - Non-critical escalations

## Workflow Structure

```yaml
process:
  id: example_workflow
  name: Workflow with Event Sub-Process

  elements:
    # Main Process
    - id: start1
      type: startEvent
      name: Start

    - id: task_main
      type: scriptTask
      name: Main Process Task

    - id: end1
      type: endEvent
      name: End

    # Event Sub-Process
    - id: event_subprocess_1
      type: eventSubProcess
      name: Timeout Handler
      properties:
        isInterrupting: false  # Non-interrupting
      childElements:
        # Must start with an event start event
        - id: timer_start
          type: timerStartEvent
          name: After 10s
          properties:
            timerDuration: PT10S

        - id: task_notify
          type: scriptTask
          name: Send Notification

        - id: end_subprocess
          type: endEvent
          name: Complete

      childConnections:
        - id: conn1
          from: timer_start
          to: task_notify

        - id: conn2
          from: task_notify
          to: end_subprocess

  connections:
    - id: main_conn1
      from: start1
      to: task_main

    - id: main_conn2
      from: task_main
      to: end1
```

## Example Workflows

### Example 1: Non-Interrupting Timer Event Sub-Process

**Scenario**: Send an escalation notification if order processing takes longer than 5 seconds, but continue processing.

```yaml
# See: workflows/event-subprocess-timer-example.yaml

Key Features:
- Timer triggers after 5 seconds
- Non-interrupting: main process continues
- Sends escalation notice in parallel
- Both processes complete successfully
```

**Timeline:**
```
Time 0s:  Main process starts (Receive Order)
Time 1s:  Main task starts (Process Order - 15s duration)
Time 5s:  Timer fires → Event Sub-Process triggered
Time 5s:  Escalation sent (parallel to main processing)
Time 6s:  Event Sub-Process completes
Time 16s: Main process completes
Time 17s: Workflow ends
```

### Example 2: Interrupting Error Event Sub-Process

**Scenario**: If a critical error occurs, stop processing and execute rollback procedure.

```yaml
- id: event_subprocess_error
  type: eventSubProcess
  name: Error Handler
  properties:
    isInterrupting: true  # Interrupting!
  childElements:
    - id: error_start
      type: errorStartEvent
      name: On Error
      properties:
        errorCode: CriticalError  # Catches specific error

    - id: task_rollback
      type: scriptTask
      name: Rollback Changes

    - id: task_notify_failure
      type: sendTask
      name: Notify Failure
```

## Triggering Events Programmatically

### Triggering Messages
Set context variables to trigger message event subprocesses:

```python
# In a script task
context['message_ORDER_UPDATED_received'] = True
context['message_ORDER_UPDATED_data'] = {
    'order_id': 'ORD-123',
    'status': 'updated'
}
```

### Triggering Signals
```python
# Broadcast signal
context['signal_URGENT_PRIORITY_triggered'] = True
context['signal_URGENT_PRIORITY_data'] = {
    'priority': 'high',
    'reason': 'VIP customer'
}
```

### Triggering Escalations
```python
# Raise escalation
context['escalation_MANAGER_APPROVAL_triggered'] = True
context['escalation_MANAGER_APPROVAL_data'] = {
    'amount': 50000,
    'requester': 'john.doe'
}
```

## Best Practices

### 1. Use Non-Interrupting for Monitoring
```yaml
# Good: Parallel monitoring
properties:
  isInterrupting: false

# Use for: logging, metrics, notifications
```

### 2. Use Interrupting for Critical Events
```yaml
# Good: Stop on critical error
properties:
  isInterrupting: true

# Use for: errors, cancellations, hard timeouts
```

### 3. Keep Event Sub-Processes Simple
- Focus on one responsibility (notification, logging, error handling)
- Avoid complex logic in event subprocesses
- Use clear naming to indicate purpose

### 4. Consider Multiple Event Sub-Processes
You can have multiple event subprocesses monitoring different events:

```yaml
elements:
  # Timeout escalation
  - id: timeout_subprocess
    type: eventSubProcess
    childElements:
      - type: timerStartEvent
        properties:
          timerDuration: PT30M

  # Error handling
  - id: error_subprocess
    type: eventSubProcess
    childElements:
      - type: errorStartEvent

  # External message handling
  - id: message_subprocess
    type: eventSubProcess
    childElements:
      - type: messageStartEvent
        properties:
          messageRef: CANCELLATION_REQUEST
```

## Testing Event Sub-Processes

### Test Non-Interrupting Timer
```bash
python3 test_simple.py \
  workflows/event-subprocess-timer-example.yaml \
  context-examples/event-subprocess-timer-context.json
```

**Expected Behavior:**
1. Main process starts and runs
2. Timer fires after specified duration
3. Event subprocess executes in parallel
4. Both processes complete
5. Workflow succeeds

### Verify Parallel Execution
Check logs for overlapping execution:
```
⚙️  Processing order: ORD-2026-001
   Progress: 20%
⚠️  ESCALATION: Order processing is taking too long!
   Progress: 27%  ← Main process continues while escalation runs
✅ Escalation notice sent
   Progress: 33%
```

## Common Patterns

### Pattern 1: SLA Monitoring
```yaml
# Non-interrupting timer for SLA breach notification
- type: eventSubProcess
  properties:
    isInterrupting: false
  childElements:
    - type: timerStartEvent
      properties:
        timerDuration: PT2H  # 2 hour SLA
```

### Pattern 2: Error Recovery
```yaml
# Interrupting error handler with rollback
- type: eventSubProcess
  properties:
    isInterrupting: true
  childElements:
    - type: errorStartEvent
      properties:
        errorCode: DatabaseError
```

### Pattern 3: External Event Reaction
```yaml
# Non-interrupting message handler for status updates
- type: eventSubProcess
  properties:
    isInterrupting: false
  childElements:
    - type: messageStartEvent
      properties:
        messageRef: STATUS_UPDATE
```

## Limitations and Considerations

1. **Event Sub-Processes start immediately** when workflow begins
2. **Only one start event** per event subprocess
3. **Context sharing**: Event subprocesses share context with parent
4. **Error handling**: Errors in event subprocesses are logged but don't fail the workflow
5. **Timer precision**: Timers use asyncio.sleep() - precision is ~100ms

## Troubleshooting

### Event Sub-Process Not Triggering

**Check:**
1. Event Sub-Process type is `eventSubProcess`
2. Start event type matches expected event type
3. Timer duration is correctly formatted (ISO 8601)
4. For messages/signals: context variables are set correctly

**Enable Debug Logging:**
```python
import logging
logging.basicConfig(level=logging.INFO)
```

Look for:
```
🎯 Found N Event Sub-Process(es) to monitor
📡 Monitoring Event Sub-Process: [name]
⏰ Timer Event Sub-Process will trigger in Xs
```

### Event Sub-Process Triggers Too Early/Late

**Timer Issues:**
- Verify `timerDuration` format: `PT5S`, `PT30M`, `PT2H`, `P1D`
- Check system time and asyncio event loop performance

**Message/Signal Issues:**
- Verify context variable names match exactly
- Check timing of when variables are set

## Advanced Topics

### Accessing Trigger Information

Event subprocesses can access trigger data:

```python
# In event subprocess script task
trigger_data = context.get('event_subprocess_timeout_trigger', {})
trigger_type = trigger_data.get('trigger_type')  # 'timer', 'message', etc.
duration = trigger_data.get('duration')  # For timer events
message_data = trigger_data.get('message_data')  # For message events
```

### Combining with Other BPMN Features

Event Sub-Processes work with:
- **Multi-Instance**: Can trigger during multi-instance execution
- **Compensation**: Can have compensation boundaries
- **Subprocesses**: Can be inside regular subprocesses
- **Pools/Lanes**: Can be placed in specific lanes

## Related Documentation

- [BPMN 2.0 Specification](https://www.omg.org/spec/BPMN/2.0/)
- [Subprocess Guide](SUBPROCESS_GUIDE.md)
- [Timer Events Guide](TIMER_EVENTS_GUIDE.md)
- [Boundary Events](BOUNDARY-EVENTS.md)

## Summary

Event Sub-Processes provide:
- ✅ Independent event monitoring
- ✅ Parallel or interrupting execution
- ✅ Multiple event type support (timer, error, message, signal, escalation)
- ✅ Context sharing with parent process
- ✅ Flexible SLA and error handling patterns

Use Event Sub-Processes when you need:
- Timeout monitoring and escalations
- Error recovery workflows
- Parallel event reactions
- SLA breach handling
- External event integration
