# BPMN Compensation Events - Rollback & Undo

## Overview

Compensation events in BPMN provide a mechanism to **undo or rollback business transactions** when errors occur. This is essential for maintaining data consistency in workflows that perform multiple operations that need to be reversed if a later step fails.

## Key Concepts

### Compensation Boundary Event
- **Attached to tasks**: Defines a compensation handler (undo logic) for a specific task
- **Non-interrupting by default**: Does NOT fire automatically when attached task completes
- **Triggered by**: Compensation intermediate throw event
- **Execution order**: LIFO (Last In, First Out) - most recent tasks are compensated first
- **Icon**: Double backward arrows (`<<`) in orange color (#d35400)

### Compensation Intermediate Throw Event
- **Explicit trigger**: Manually triggers compensation for all completed tasks
- **Typical use**: Placed in error handling flows
- **Effect**: Executes ALL registered compensation handlers in reverse order

## How It Works

1. **Task Executes Successfully**
   - If task has a compensation boundary event attached, it's **registered** for later compensation
   - The compensation handler does NOT execute automatically

2. **Error Occurs Later**
   - An error boundary event catches the error
   - Error flow leads to a compensation throw event

3. **Compensation Triggered**
   - Compensation throw event activates
   - ALL registered compensation handlers execute in **REVERSE order** (LIFO)
   - Each handler performs undo/rollback operations

## Example: Travel Booking with Rollback

```yaml
Book Flight (with compensation)
  ↓
Book Hotel (with compensation)
  ↓
Process Payment (with error boundary)
  ↓
  ├─ Success → Send Confirmation → End
  │
  └─ Error → Log Error → TRIGGER COMPENSATION → Notify Customer → End
                            ↓
                    [Executes in reverse order:]
                    1. Cancel Hotel (undo)
                    2. Cancel Flight (undo)
```

### Workflow Files

**Workflow**: `workflows/compensation-rollback-example.yaml`

**Context for Success** (payment succeeds, no compensation):
```bash
python backend/main.py \
  workflows/compensation-rollback-example.yaml \
  context-examples/compensation-success-context.json
```

**Context for Failure** (payment fails, triggers compensation):
```bash
python backend/main.py \
  workflows/compensation-rollback-example.yaml \
  context-examples/compensation-failure-context.json
```

**Quick Test Script**:
```bash
./test_compensation.sh
```

### Important Notes

- **Task Type**: Use `scriptTask` type for tasks with inline Python scripts
- **Context Variables**: Variables from context are automatically unpacked and available directly in scripts
  - You can use: `payment_should_succeed`
  - Instead of: `context['payment_should_succeed']`
- **Error Matching**: The error boundary `errorCode` can match:
  - Exception type name (e.g., `ValueError`)
  - Substring in exception message (e.g., `PaymentError` matches `"PaymentError: Insufficient funds"`)
  - Empty `errorCode` catches all exceptions

## Execution Flow Details

### Success Scenario (payment_should_succeed: true)

1. ✅ Book Flight → Registers compensation handler (Cancel Flight)
2. ✅ Book Hotel → Registers compensation handler (Cancel Hotel)
3. ✅ Process Payment → Succeeds
4. ✅ Send Confirmation Email
5. ✅ End (Booking Complete)

**Result**: No compensation triggered, bookings remain active

### Failure Scenario (payment_should_succeed: false)

1. ✅ Book Flight → Registers compensation handler (Cancel Flight)
2. ✅ Book Hotel → Registers compensation handler (Cancel Hotel)
3. ❌ Process Payment → **Raises PaymentError**
4. ⚡ Error Boundary → Catches PaymentError
5. 📝 Log Payment Error
6. 🔄 **Trigger Rollback** (Compensation Throw Event)
   - Executes: Cancel Hotel (LIFO - last booked first)
   - Executes: Cancel Flight
7. 📧 Notify Customer of Failure
8. ❌ End (Booking Failed)

**Result**: All bookings automatically cancelled via compensation

## Implementation Details

### Frontend (app.js)

- Added `compensationBoundaryEvent` to palette (interrupting and non-interrupting)
- Icon: Double backward arrows in orange (#d35400)
- Rendering: Standard boundary event circles with compensation icon

### Backend (workflow_engine.py)

**Compensation Registry**:
```python
self.compensation_handlers: Dict[str, Element] = {}
```

**Registration** (when task with compensation boundary completes):
```python
if compensation_boundaries:
    for comp_boundary in compensation_boundaries:
        self.compensation_handlers[task.id] = comp_boundary
```

**Triggering** (when compensation throw event executes):
```python
async def trigger_compensation(self, throw_event: Element):
    # Execute handlers in REVERSE order (LIFO)
    task_ids = list(self.compensation_handlers.keys())
    task_ids.reverse()

    for task_id in task_ids:
        comp_boundary = self.compensation_handlers[task_id]
        # Execute compensation flow
        next_elements = self.workflow.get_outgoing_elements(comp_boundary)
        for elem in next_elements:
            await self.execute_from_element(elem)
```

## Design Patterns

### Pattern 1: Error-Triggered Rollback
```
Task 1 (with compensation) → Task 2 (with compensation) → Task 3 (with error boundary)
                                                              ↓ (on error)
                                                          Trigger Compensation
```

**Use case**: Multi-step transactions where later failures require undoing earlier steps

### Pattern 2: Conditional Rollback
```
Gateway: Should Cancel?
  ├─ Yes → Trigger Compensation
  └─ No → Continue
```

**Use case**: Business decision to rollback based on conditions

### Pattern 3: Partial Rollback
```
Sub-Process (with compensation) → Main Flow
                                     ↓ (on error)
                                  Trigger Compensation
                                  (only undoes sub-process)
```

**Use case**: Rolling back a specific sub-transaction without affecting the entire workflow

## Best Practices

1. **LIFO Order**: Always execute compensation in reverse order of task completion
2. **Idempotent Handlers**: Compensation logic should be safe to run multiple times
3. **Logging**: Log all compensation activities for audit trail
4. **Error Handling**: Compensation handlers should handle their own errors gracefully
5. **Scope**: Each compensation handler should only undo its own task's effects
6. **Testing**: Test both success path (no compensation) and failure path (with compensation)

## Comparison with Other Boundary Events

| Event Type | Trigger | Cancels Task | Use Case |
|------------|---------|--------------|----------|
| **Error Boundary** | Exception thrown | Yes (if interrupting) | Catch and handle errors |
| **Timer Boundary** | Time elapsed | Yes (if interrupting) | Timeout/escalation |
| **Compensation Boundary** | Explicit throw event | No (task already complete) | Undo completed work |

## BPMN 2.0 Compliance

This implementation follows BPMN 2.0 specifications for compensation events:
- ✅ Compensation handlers attached via boundary events
- ✅ Triggered by compensation throw events
- ✅ LIFO execution order
- ✅ Scoped to completed activities only
- ✅ Visual notation: Double backward arrows

## Logging Output

When compensation is triggered, you'll see:
```
🔄 ========================================
🔄 COMPENSATION TRIGGERED by: Trigger Rollback
🔄 Registered compensation handlers: ['task_hotel', 'task_flight']
🔄 ========================================
🔄 Triggering compensation for task task_hotel: Cancel Hotel
➡️  Following compensation flow to: ['Cancel Hotel Booking']
🔄 COMPENSATING: Cancelling hotel booking HOTEL-12345678...
✅ Hotel booking HOTEL-12345678 successfully cancelled
🔄 Triggering compensation for task task_flight: Cancel Flight
➡️  Following compensation flow to: ['Cancel Flight Booking']
🔄 COMPENSATING: Cancelling flight booking FLIGHT-12345678...
✅ Flight booking FLIGHT-12345678 successfully cancelled
🔄 ======================================== (END COMPENSATION)
```

## Future Enhancements

- [ ] Selective compensation (target specific tasks)
- [ ] Compensation sub-processes
- [ ] Nested compensation scopes
- [ ] Compensation event propagation in call activities
- [ ] Timeout handling for compensation handlers
