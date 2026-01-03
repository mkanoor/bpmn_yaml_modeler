# Error Event Sub-Process Example

## Overview

This workflow demonstrates **interrupting error Event Sub-Processes** - a powerful BPMN 2.0 feature that catches errors in the main process and executes a recovery workflow.

## Workflow: `event-subprocess-error-example.yaml`

### Scenario
A payment processing workflow that:
1. Validates payment details
2. Processes payment (will fail if amount > $1000)
3. Sends confirmation (only if payment succeeds)

When the payment fails, an **Error Event Sub-Process** is triggered that:
1. Logs error details
2. Notifies the customer
3. Initiates a refund process

### Key Features

#### Interrupting Event Sub-Process
```yaml
- id: event_subprocess_error
  type: eventSubProcess
  name: Payment Error Recovery Handler
  properties:
    isInterrupting: true  # ← Stops main process when triggered
```

#### Error Start Event (Catch-All)
```yaml
- id: esp_error_start
  type: errorStartEvent
  name: On Payment Error
  properties:
    errorCode: ""  # ← Empty = catches ALL errors
```

To catch specific errors, set `errorCode`:
```yaml
properties:
  errorCode: "PaymentLimitExceeded"  # Only catches this error
```

### Execution Flow

**Normal Flow (when amount ≤ $1000):**
```
Start → Validate → Process Payment → Send Confirmation → End
```

**Error Flow (when amount > $1000):**
```
Start → Validate → Process Payment (FAILS)
                         ↓
                   [Error Caught]
                         ↓
              Event Sub-Process Triggered:
                Log Error → Notify Customer → Refund → End
                         ↓
                Main Process CANCELLED
```

## Testing

### Run the Example
```bash
python3 test_simple.py \
  workflows/event-subprocess-error-example.yaml \
  context-examples/event-subprocess-error-context.json
```

### Expected Behavior

**Context:**
```json
{
  "order_id": "ORD-2026-ERR-001",
  "payment_amount": 1500.00,  // > $1000 limit
  "card_number": "4111111111111111",
  "customer_email": "customer@example.com"
}
```

**Output:**
```
💳 Validating payment for order: ORD-2026-ERR-001
✅ Card validation successful

💰 Processing payment: $1500.0
❌ PAYMENT FAILED: Amount exceeds limit

========================================
🚨 ERROR RECOVERY: Payment processing failed!
========================================
📝 Error logged to database

📧 Sending failure notification to customer
✅ Customer notified of payment failure

💸 Initiating automatic refund
✅ Refund process started
```

The workflow ends with `CancelledError` because the main process was **interrupted** - this is expected and correct behavior!

## Comparison with Non-Interrupting

### Interrupting (This Example)
```yaml
isInterrupting: true
```
- ✅ Stops main process immediately
- ✅ Recovery runs instead of main process
- ✅ Use for: Critical errors, rollbacks, failure handling

### Non-Interrupting
```yaml
isInterrupting: false
```
- ✅ Main process continues
- ✅ Recovery runs in parallel
- ✅ Use for: Logging, notifications, monitoring

## Error Matching Rules

### Catch All Errors
```yaml
errorCode: ""  # Empty string catches ALL errors
```

### Catch Specific Error
```yaml
errorCode: "PaymentLimitExceeded"  # Only this error
```

The error matcher checks if the `errorCode` appears in the exception message.

## Common Patterns

### Pattern 1: Payment Processing with Rollback
```yaml
# Main: Process Payment
# Error Sub-Process: Refund + Notify
```

### Pattern 2: Data Processing with Cleanup
```yaml
# Main: Import Data
# Error Sub-Process: Delete Partial Data + Log
```

### Pattern 3: External API Call with Retry
```yaml
# Main: Call API
# Error Sub-Process: Log Failure + Queue Retry
```

## Integration with Other Features

### With Boundary Events
You can combine error Event Sub-Processes with error boundary events:
- **Boundary Events**: Catch errors on specific tasks
- **Event Sub-Processes**: Catch errors from entire workflow

### With Multi-Instance
Error Event Sub-Processes work during multi-instance execution:
```yaml
# If any instance fails, trigger recovery
```

### With Compensation
Can trigger compensation handlers from error recovery:
```yaml
# Error Sub-Process → Trigger Compensation
```

## Best Practices

### 1. Use Interrupting for Critical Errors
```yaml
# Payment failures, data corruption, security breaches
isInterrupting: true
```

### 2. Log Before Taking Action
```yaml
childElements:
  - Log Error Details    # ← Always log first
  - Notify Stakeholders
  - Initiate Rollback
```

### 3. Provide Context to Recovery
Error Event Sub-Processes share context with main process:
```python
# Access order details in error handler
order_id = context['order_id']
payment_amount = context['payment_amount']
```

### 4. Clean Up Resources
```yaml
# Close connections, release locks, cancel external requests
```

## Troubleshooting

### Error Not Caught
**Check:**
1. Event Sub-Process type is `eventSubProcess`
2. Start event type is `errorStartEvent`
3. `errorCode` matches error message (or is empty for catch-all)
4. Error occurred in main process (not in Event Sub-Process itself)

### Workflow Still Fails
If an interrupting Event Sub-Process completes successfully but workflow still shows error:
- **This is expected!** Interrupting = cancels main process
- The Event Sub-Process **DID** execute successfully
- Check logs to confirm recovery tasks completed

### Error Sub-Process Not Triggered
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

Look for:
```
🔍 Checking for error Event Sub-Process to handle: [error]
✅ Found matching error Event Sub-Process
```

## Related Documentation

- [Event Sub-Process Guide](../EVENT_SUBPROCESS_GUIDE.md)
- [Timer Event Sub-Process Example](event-subprocess-timer-example.yaml)
- [Boundary Events](../BOUNDARY-EVENTS.md)

## Summary

Error Event Sub-Processes provide:
- ✅ Automatic error detection and recovery
- ✅ Clean separation of happy path and error handling
- ✅ Ability to interrupt or run in parallel
- ✅ Context sharing for informed recovery
- ✅ Integration with other BPMN features

Perfect for:
- Payment processing failures
- API call errors
- Data validation failures
- Resource allocation errors
- Transaction rollbacks
