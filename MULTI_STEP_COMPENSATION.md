# Multi-Step Compensation Example - LIFO Order Verification

## Overview

This workflow demonstrates **LIFO (Last In, First Out)** compensation order with **4 sequential steps** in an e-commerce order processing scenario.

When payment capture fails at the final step, all previous steps are automatically rolled back in **reverse order** to ensure proper cleanup.

## Business Scenario

**E-Commerce Order Processing** with multiple dependent steps:

1. **Reserve Inventory** - Lock items in warehouse
2. **Authorize Payment** - Place hold on customer's credit card
3. **Create Shipment** - Generate shipping label and tracking number
4. **Capture Payment** - Convert authorization hold to actual charge ← **FAILURE POINT**

If payment capture fails (card declined, expired, etc.), all previous steps must be undone in the correct order.

## Why LIFO Order Matters

### Incorrect Order Could Cause Issues:

```
❌ WRONG: Release inventory first
   → Shipment still exists with no inventory
   → Payment still on hold
   → Inconsistent state!

❌ WRONG: Release payment first
   → Shipment still active
   → Inventory still reserved
   → Carrier expects package that won't arrive
```

### Correct LIFO Order:

```
✅ CORRECT: Undo in reverse order
   1. Cancel Shipment (most recent) → No carrier confusion
   2. Release Payment Hold → No customer charge
   3. Release Inventory (oldest) → Items back in stock
   → Clean, consistent state!
```

## Workflow Steps

### Forward Execution (Success Path)

```
START
  ↓
1. Reserve Inventory
   ├─ Reserves: Laptop, Mouse, Cable
   ├─ Creates: INV-xxxxx
   └─ Registers compensation handler
  ↓
2. Authorize Payment
   ├─ Places hold: $1299.99
   ├─ Creates: AUTH-xxxxx
   └─ Registers compensation handler
  ↓
3. Create Shipment
   ├─ Generates label: TRACK-xxxxx
   ├─ Carrier: FedEx
   └─ Registers compensation handler
  ↓
4. Capture Payment
   ├─ Converts hold → charge
   ├─ Creates: TXN-xxxxx
   └─ SUCCESS → Send Confirmation Email
  ↓
END (Order Complete)
```

### Failure Path (LIFO Rollback)

```
4. Capture Payment
   ↓
   ❌ EXCEPTION: PaymentCaptureError
   ↓
Error Boundary Catches Exception
   ↓
Log Error
   ↓
🔄 Compensation Throw Event
   ↓
   Triggers compensation in LIFO order:
   ↓
   ┌────────────────────────────────────┐
   │ COMPENSATION STEP 1 (of 3)         │
   │ Cancel Shipment                    │
   │ (Most recent - undo first)         │
   │ - Void shipping label              │
   │ - Notify carrier: CANCELLED        │
   └────────────────────────────────────┘
   ↓
   ┌────────────────────────────────────┐
   │ COMPENSATION STEP 2 (of 3)         │
   │ Release Payment Authorization      │
   │ (Second to undo)                   │
   │ - Release hold on card             │
   │ - Return funds to available balance│
   └────────────────────────────────────┘
   ↓
   ┌────────────────────────────────────┐
   │ COMPENSATION STEP 3 (of 3)         │
   │ Release Inventory Reservation      │
   │ (Oldest - undo last)               │
   │ - Return items to available stock  │
   │ - Update warehouse system          │
   └────────────────────────────────────┘
   ↓
Send Failure Notification Email
   ↓
END (Order Failed, Fully Rolled Back)
```

## Files

### Workflow Definition
- **File**: `workflows/multi-step-compensation-example.yaml`
- **Process**: E-Commerce Order Processing
- **Tasks**: 4 main tasks + 3 compensation tasks
- **Lanes**: 2 (Order Processing, Compensation)

### Test Contexts
- **Success**: `context-examples/multi-comp-success-context.json`
  - `payment_capture_should_succeed: true`
  - All 4 steps complete successfully

- **Failure**: `context-examples/multi-comp-failure-context.json`
  - `payment_capture_should_succeed: false`
  - Payment capture fails → Full LIFO rollback

### Test Script
- **File**: `test_multi_compensation.py`
- **Usage**:
  ```bash
  python test_multi_compensation.py success   # Test success path
  python test_multi_compensation.py failure   # Test LIFO rollback
  ```

## Running the Test

### Test Failure Scenario (LIFO Rollback)

```bash
python test_multi_compensation.py failure
```

**Expected Console Output:**

```
================================================================================
MULTI-STEP COMPENSATION TEST - E-COMMERCE ORDER
================================================================================
Scenario: FAILURE
================================================================================

📋 Order Details:
   Order ID: ORD-2024-001
   Customer: mkanoor@gmail.com
   Items: Laptop, Wireless Mouse, USB-C Cable
   Total: $1299.99
   Payment Capture Will: FAIL

🚀 Starting NEW workflow execution
🚀 Workflow Name: E-Commerce Order with Multi-Step Rollback (LIFO)
🚀 Instance ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

📦 Step 1: Reserving inventory for order ORD-2024-001...
   Items: Laptop, Wireless Mouse, USB-C Cable
✅ Inventory reserved! Reservation ID: INV-xxxxxxxx
   Timestamp: 2024-12-31T...
📋 Registering compensation handler for task task_inventory: Release Inventory

💳 Step 2: Authorizing payment for $1299.99...
   Card ending in: 4242
✅ Payment authorized! Auth code: AUTH-xxxxxxxx
   Amount held: $1299.99
   Timestamp: 2024-12-31T...
📋 Registering compensation handler for task task_authorize: Release Payment Hold

📮 Step 3: Creating shipment to 123 Main St, San Francisco, CA 94102...
   Carrier: FedEx
✅ Shipment created! Tracking: TRACK-xxxxxxxx
   Estimated delivery: 3-5 business days
   Timestamp: 2024-12-31T...
📋 Registering compensation handler for task task_shipment: Cancel Shipment

💰 Step 4: Capturing payment (converting hold to actual charge)...
   Auth code: AUTH-xxxxxxxx
   Amount: $1299.99
❌ PAYMENT CAPTURE FAILED - Card was declined or expired
   ERROR: The authorized payment could not be captured
   All previous steps must be rolled back!

❌ Task Capture Payment failed with error: Exception: PaymentCaptureError: Card declined during capture
🎯 Error caught by boundary event: Capture Failed
   Error type: Exception
   Boundary catches: PaymentCaptureError

📝 ========================================
📝 CRITICAL ERROR - Payment capture failed!
📝 ========================================
   Order ID: ORD-2024-001
   Customer: mkanoor@gmail.com
   Amount: $1299.99
   Auth Code: AUTH-xxxxxxxx
   ERROR: Payment capture was declined
📝 Initiating FULL ROLLBACK of all completed steps...
📝 ========================================

🔄 ========================================
🔄 COMPENSATION TRIGGERED by: Trigger Full Rollback
🔄 Registered compensation handlers: ['task_inventory', 'task_authorize', 'task_shipment']
🔄 ========================================

🔄 Triggering compensation for task task_shipment: Cancel Shipment
➡️  Following compensation flow to: ['Cancel Shipment & Void Label']

🔄 ========================================
🔄 COMPENSATION STEP 1 (of 3)
🔄 Cancelling SHIPMENT (most recent step)
🔄 ========================================
   Tracking Number: TRACK-xxxxxxxx
   Carrier: FedEx
   ✅ Shipping label voided
   ✅ Carrier notified of cancellation
   ✅ Shipment status: CANCELLED
🔄 ========================================

🔄 Triggering compensation for task task_authorize: Release Payment Hold
➡️  Following compensation flow to: ['Release Payment Authorization']

🔄 ========================================
🔄 COMPENSATION STEP 2 (of 3)
🔄 Releasing PAYMENT AUTHORIZATION
🔄 ========================================
   Auth Code: AUTH-xxxxxxxx
   Held Amount: $1299.99
   ✅ Payment hold released
   ✅ Funds returned to customer's available balance
   ✅ No charge made to customer
🔄 ========================================

🔄 Triggering compensation for task task_inventory: Release Inventory
➡️  Following compensation flow to: ['Release Inventory Reservation']

🔄 ========================================
🔄 COMPENSATION STEP 3 (of 3)
🔄 Releasing INVENTORY RESERVATION (oldest step)
🔄 ========================================
   Reservation ID: INV-xxxxxxxx
   Items: Laptop, Wireless Mouse, USB-C Cable
   ✅ Inventory reservation cancelled
   ✅ Items returned to available stock
   ✅ Warehouse system updated
🔄 ========================================

✅ FULL ROLLBACK COMPLETE - All 3 steps undone in LIFO order
   Order state: Fully reverted, no customer impact

🔄 ======================================== (END COMPENSATION)

📧 Sending Email (or simulating)...

================================================================================
✅ WORKFLOW COMPLETED SUCCESSFULLY
================================================================================

================================================================================
LIFO ORDER VERIFICATION
================================================================================

Expected compensation order (LIFO - reverse of creation):

  FORWARD EXECUTION ORDER:
    1. Reserve Inventory    (task_inventory)
    2. Authorize Payment    (task_authorize)
    3. Create Shipment      (task_shipment)
    4. Capture Payment      (task_capture) ← FAILS HERE

  COMPENSATION ORDER (LIFO - REVERSE):
    1. Cancel Shipment      (comp_shipment)     ← Last completed, first undone
    2. Release Payment Auth (comp_authorize)    ← Second to undo
    3. Release Inventory    (comp_inventory)    ← First completed, last undone

📧 Check your email for detailed rollback notification!
   Email includes specific IDs for each cancelled step:
   - Tracking Number
   - Auth Code
   - Reservation ID

================================================================================
```

### Test Success Scenario

```bash
python test_multi_compensation.py success
```

**Expected Outcome:**
- All 4 steps complete successfully
- No compensation triggered
- Order confirmation email sent with all details

## Email Notifications

### Success Email (if Gmail configured)

```
Subject: ✅ Order Confirmed - Order #ORD-2024-001
To: mkanoor@gmail.com

Your order has been confirmed and is being processed!

ORDER DETAILS:
• Order ID: ORD-2024-001
• Items: Laptop, Wireless Mouse, USB-C Cable
• Total: $1299.99

PROCESSING STEPS COMPLETED:

1️⃣  INVENTORY RESERVED
   Reservation ID: INV-xxxxxxxx
   Items: Laptop, Wireless Mouse, USB-C Cable
   Status: reserved

2️⃣  PAYMENT AUTHORIZED & CAPTURED
   Auth Code: AUTH-xxxxxxxx
   Transaction ID: TXN-xxxxxxxx
   Amount Charged: $1299.99
   Status: captured

3️⃣  SHIPMENT CREATED
   Tracking Number: TRACK-xxxxxxxx
   Carrier: FedEx
   Estimated Delivery: 3-5 business days

Track your order: https://tracking.example.com/TRACK-xxxxxxxx

Thank you for your order!
E-Commerce Team
```

### Failure Email (if Gmail configured)

```
Subject: ❌ Order Failed - Order #ORD-2024-001
To: mkanoor@gmail.com

Unfortunately, we encountered an issue while processing your order.

ORDER DETAILS:
• Order ID: ORD-2024-001
• Items: Laptop, Wireless Mouse, USB-C Cable
• Total: $1299.99

WHAT HAPPENED:
Your payment authorization was successful, but when we attempted to capture
the final payment, your card was declined. This can happen if:
- Your card expired between authorization and capture
- Your bank flagged the transaction
- Insufficient funds at time of capture

AUTOMATIC ROLLBACK COMPLETED:
We have automatically reversed all steps that were completed:

3️⃣  SHIPMENT CANCELLED
   Tracking: TRACK-xxxxxxxx
   Status: CANCELLED - Shipping label voided

2️⃣  PAYMENT AUTHORIZATION RELEASED
   Auth Code: AUTH-xxxxxxxx
   Status: HOLD RELEASED - No charge to your card

1️⃣  INVENTORY RESERVATION RELEASED
   Reservation ID: INV-xxxxxxxx
   Status: RELEASED - Items returned to available stock

NEXT STEPS:
• Please update your payment information
• Verify your card has sufficient funds
• Try placing your order again

No charges have been made to your card. All holds have been released.

E-Commerce Team
```

## Key Implementation Details

### Compensation Handler Registration (workflow_engine.py)

When each task completes, its compensation boundary is registered:

```python
# Lines 565-570
if compensation_boundaries:
    for comp_boundary in compensation_boundaries:
        logger.info(f"📋 Registering compensation handler for task {task.id}: {comp_boundary.name}")
        self.compensation_handlers[task.id] = comp_boundary
```

After 3 tasks complete:
```python
compensation_handlers = {
    'task_inventory': comp_inventory,    # Registered 1st
    'task_authorize': comp_authorize,    # Registered 2nd
    'task_shipment': comp_shipment       # Registered 3rd
}
```

### LIFO Execution (workflow_engine.py)

When compensation is triggered, handlers execute in **reverse** order:

```python
# Lines 796-799
task_ids = list(self.compensation_handlers.keys())
# ['task_inventory', 'task_authorize', 'task_shipment']
task_ids.reverse()
# ['task_shipment', 'task_authorize', 'task_inventory']

for task_id in task_ids:
    # Execute compensation in LIFO order
```

**Execution order:**
1. `task_shipment` → `comp_shipment` → `task_cancel_shipment` (3rd registered, 1st undone)
2. `task_authorize` → `comp_authorize` → `task_release_payment` (2nd registered, 2nd undone)
3. `task_inventory` → `comp_inventory` → `task_release_inventory` (1st registered, 3rd undone)

### Error Boundary Trigger

```yaml
- id: error_capture
  type: errorBoundaryEvent
  attachedToRef: task_capture
  properties:
    errorCode: PaymentCaptureError
    cancelActivity: true
```

Catches exception and follows error path:
```
error_capture → task_log_error → comp_throw → task_notify_failure → end_failure
```

## Verification Checklist

When running `python test_multi_compensation.py failure`, verify:

- ✅ **Step 1** executes: Reserve Inventory
  - Console shows: "Inventory reserved! Reservation ID: INV-xxxxx"
  - Compensation handler registered

- ✅ **Step 2** executes: Authorize Payment
  - Console shows: "Payment authorized! Auth code: AUTH-xxxxx"
  - Compensation handler registered

- ✅ **Step 3** executes: Create Shipment
  - Console shows: "Shipment created! Tracking: TRACK-xxxxx"
  - Compensation handler registered

- ✅ **Step 4** fails: Capture Payment
  - Console shows: "PAYMENT CAPTURE FAILED"
  - Exception raised: `PaymentCaptureError`

- ✅ **Error boundary** catches exception
  - Console shows: "Error caught by boundary event"

- ✅ **Compensation triggers** in LIFO order
  - Console shows: "COMPENSATION TRIGGERED"
  - Shows: "Registered compensation handlers: ['task_inventory', 'task_authorize', 'task_shipment']"

- ✅ **Shipment compensated FIRST**
  - Console shows: "COMPENSATION STEP 1 (of 3)"
  - Console shows: "Cancelling SHIPMENT (most recent step)"

- ✅ **Payment compensated SECOND**
  - Console shows: "COMPENSATION STEP 2 (of 3)"
  - Console shows: "Releasing PAYMENT AUTHORIZATION"

- ✅ **Inventory compensated LAST**
  - Console shows: "COMPENSATION STEP 3 (of 3)"
  - Console shows: "Releasing INVENTORY RESERVATION (oldest step)"

- ✅ **Email notification** sent with all IDs
  - Includes tracking number, auth code, reservation ID

## Customization

### Test with Different Failure Points

To test compensation with only 2 steps (if payment authorization fails):

1. Move error boundary from `task_capture` to `task_authorize`
2. Change context: `payment_authorization_should_succeed: false`
3. Only inventory will be compensated (only 1 handler registered)

### Add More Steps

To add a 5th step (e.g., "Notify Warehouse"):

1. Add task after `task_shipment`
2. Add compensation boundary
3. Add compensation task in lane 2
4. Connect compensation flow

The LIFO order will automatically include the new step.

## Comparison with Previous Example

### Travel Booking (2 tasks):
- Flight booking
- Hotel booking
- Payment fails → Both cancelled

### E-Commerce Order (3 tasks + 1 failure point):
- Inventory reservation
- Payment authorization
- Shipment creation
- Payment capture fails → **All 3 undone in reverse order**

This example clearly demonstrates LIFO with **more steps**, making the reverse order more visible and meaningful.

## Troubleshooting

### Issue: Compensation doesn't execute in reverse order

**Check:**
- `workflow_engine.py:796-799` - Does it call `task_ids.reverse()`?
- Console output - Does it show LIFO order?

### Issue: Not all compensation handlers registered

**Check:**
- Each task has `compensationBoundaryEvent` with `attachedToRef`
- Console shows "Registering compensation handler" for each task
- `self.compensation_handlers` dict has all task IDs

### Issue: Email doesn't show IDs

**Check:**
- `task_executors.py:447-472` - Variable resolution supports nested properties
- Email template uses `${object.property}` syntax
- Context has all result variables (`inventory_result`, `payment_auth_result`, etc.)

## Next Steps

1. **Run the test**: `python test_multi_compensation.py failure`
2. **Verify LIFO order** in console output
3. **Check email** for detailed rollback notification
4. **Compare with success path**: `python test_multi_compensation.py success`
5. **Customize** for your own multi-step business processes

## Summary

This workflow proves that **BPMN Compensation Events execute in LIFO order**, which is critical for:
- Database transaction rollback
- Distributed system cleanup
- Multi-step API call reversals
- Financial transaction undoing
- Resource deallocation

The LIFO guarantee ensures that dependent operations are undone in the correct sequence, preventing inconsistent states and data corruption.
