# Email Approval Workflow with Webhook Callbacks

## Overview

Send approval requests via email with **clickable Approve/Deny buttons** that trigger webhooks back to your workflow. Perfect for approval workflows without requiring users to access your app!

Users click a button in their email → Webhook triggered → Workflow resumes instantly!

## How It Works

### 1. Send Approval Email

```yaml
- id: send_approval
  type: sendTask
  name: Send Approval Request
  properties:
    messageType: Email
    to: manager@company.com
    subject: Approval Required - Order ${orderId}
    messageBody: |
      Please review and approve this order:

      Order ID: ${orderId}
      Amount: $${amount}
      Customer: ${customerName}
    useGmail: true
    htmlFormat: true
    includeApprovalLinks: true
    approvalMessageRef: approvalRequest
    approvalCorrelationKey: ${orderId}
```

### 2. Email Contains Approve/Deny Buttons

**HTML Email:**
```
┌────────────────────────────────────┐
│ Please review and approve this     │
│ order:                             │
│                                    │
│ Order ID: 12345                    │
│ Amount: $99.99                     │
│ Customer: John Doe                 │
│                                    │
│ ─────────────────────────────────  │
│ Please choose an action:           │
│                                    │
│  [✓ Approve]  [✗ Deny]             │
│                                    │
│ Click a button above to submit     │
│ your decision.                     │
└────────────────────────────────────┘
```

### 3. User Clicks Approve/Deny

**Approve button URL:**
```
https://abc123.ngrok.io/webhooks/approve/approvalRequest/order-12345
```

**Deny button URL:**
```
https://abc123.ngrok.io/webhooks/deny/approvalRequest/order-12345
```

### 4. Webhook Triggered

User clicks → HTTP GET request sent → Message published to workflow

### 5. Workflow Resumes

```yaml
- id: wait_approval
  type: receiveTask
  name: Wait for Approval Decision
  properties:
    messageRef: approvalRequest
    correlationKey: ${orderId}
    timeout: 3600000  # 1 hour
    useWebhook: true
```

**Workflow receives:**
```javascript
{
  decision: "approved",  // or "denied"
  method: "email",
  timestamp: "2025-12-19T10:30:00Z"
}
```

**Context updated:**
```javascript
{
  orderId: "12345",
  decision: "approved",  // ← Available for next tasks!
  method: "email"
}
```

### 6. Conditional Gateway Based on Decision

```yaml
- id: check_decision
  type: exclusiveGateway
  name: Approved?
  connections:
    - condition: ${decision} == "approved"
      to: process_order
    - condition: ${decision} == "denied"
      to: cancel_order
```

## Complete Workflow Example

```yaml
process:
  name: Order Approval via Email
  id: order-approval-email
  elements:
    # Start workflow
    - id: element_1
      type: startEvent
      name: Start
      x: 100
      y: 150

    # Create order
    - id: element_2
      type: scriptTask
      name: Create Order
      x: 250
      y: 150
      properties:
        scriptFormat: Python
        script: |
          import random
          orderId = f"order-{random.randint(10000, 99999)}"
          context['orderId'] = orderId
          context['amount'] = 99.99
          context['customerName'] = 'John Doe'
          result = {'orderId': orderId}

    # Send approval email
    - id: element_3
      type: sendTask
      name: Send Approval Email
      x: 450
      y: 150
      properties:
        messageType: Email
        to: manager@company.com
        subject: Approval Required - Order ${orderId}
        messageBody: |
          <html>
          <body>
            <h2>Order Approval Required</h2>
            <p>Please review and approve this order:</p>
            <ul>
              <li><strong>Order ID:</strong> ${orderId}</li>
              <li><strong>Amount:</strong> $${amount}</li>
              <li><strong>Customer:</strong> ${customerName}</li>
            </ul>
          </body>
          </html>
        useGmail: true
        htmlFormat: true
        includeApprovalLinks: true
        approvalMessageRef: approvalRequest
        approvalCorrelationKey: ${orderId}

    # Wait for approval decision
    - id: element_4
      type: receiveTask
      name: Wait for Decision
      x: 700
      y: 150
      properties:
        messageRef: approvalRequest
        correlationKey: ${orderId}
        timeout: 3600000  # 1 hour
        useWebhook: true

    # Check decision
    - id: element_5
      type: exclusiveGateway
      name: Approved?
      x: 900
      y: 150

    # Approved path
    - id: element_6
      type: serviceTask
      name: Process Order
      x: 1050
      y: 50
      properties:
        implementation: External

    - id: element_7
      type: sendTask
      name: Send Confirmation
      x: 1250
      y: 50
      properties:
        messageType: Email
        to: ${customerEmail}
        subject: Order Approved - ${orderId}
        messageBody: |
          Your order ${orderId} has been approved!
          Amount: $${amount}
        useGmail: true

    - id: element_8
      type: endEvent
      name: Order Complete
      x: 1450
      y: 50

    # Denied path
    - id: element_9
      type: sendTask
      name: Send Rejection Notice
      x: 1050
      y: 250
      properties:
        messageType: Email
        to: ${customerEmail}
        subject: Order Denied - ${orderId}
        messageBody: |
          Sorry, your order ${orderId} was not approved.
        useGmail: true

    - id: element_10
      type: endEvent
      name: Order Cancelled
      x: 1250
      y: 250

  connections:
    - id: conn_1
      from: element_1
      to: element_2

    - id: conn_2
      from: element_2
      to: element_3

    - id: conn_3
      from: element_3
      to: element_4

    - id: conn_4
      from: element_4
      to: element_5

    # Approved path
    - id: conn_5
      from: element_5
      to: element_6
      properties:
        condition: ${decision} == "approved"

    - id: conn_6
      from: element_6
      to: element_7

    - id: conn_7
      from: element_7
      to: element_8

    # Denied path
    - id: conn_8
      from: element_5
      to: element_9
      properties:
        condition: ""  # Default path

    - id: conn_9
      from: element_9
      to: element_10
```

## Setup Instructions

### 1. Configure ngrok URL in .env

```bash
cd backend
cp .env.example .env
```

**Edit `.env`:**
```bash
# Get this from ngrok output: ngrok http 8000
NGROK_URL=https://abc123.ngrok.io

# Gmail OAuth (already configured)
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json
```

### 2. Start ngrok

```bash
ngrok http 8000
```

**Copy the HTTPS URL:**
```
Forwarding https://abc123.ngrok.io -> http://localhost:8000
```

**Update `.env` with this URL!**

### 3. Start Backend

```bash
cd backend
python main.py
```

Backend loads `NGROK_URL` from `.env`

### 4. Execute Workflow

Workflow sends email with approval buttons pointing to your ngrok URL!

## Email Templates

### HTML Email (Recommended)

```yaml
properties:
  messageBody: |
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
      <h2 style="color: #333;">Approval Required</h2>
      <p>Please review the following request:</p>

      <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <p><strong>Order ID:</strong> ${orderId}</p>
        <p><strong>Amount:</strong> $${amount}</p>
        <p><strong>Submitted by:</strong> ${customerName}</p>
      </div>

      <p style="color: #666;">
        Click one of the buttons below to submit your decision.
      </p>
    </body>
    </html>
  htmlFormat: true
  includeApprovalLinks: true
```

**Approval buttons added automatically at the end!**

### Plain Text Email

```yaml
properties:
  messageBody: |
    Approval Required

    Please review the following request:

    Order ID: ${orderId}
    Amount: $${amount}
    Submitted by: ${customerName}

    Click a link below to submit your decision.
  htmlFormat: false
  includeApprovalLinks: true
```

**Approval links added as plain text URLs**

## Approval Link Formats

### HTML Buttons (when htmlFormat: true)

```html
<div style="margin-top: 30px; padding: 20px; border-top: 2px solid #e0e0e0;">
    <p style="font-size: 16px; margin-bottom: 20px;">Please choose an action:</p>
    <table>
        <tr>
            <td style="padding-right: 10px;">
                <a href="https://abc123.ngrok.io/webhooks/approve/approvalRequest/order-12345"
                   style="padding: 12px 30px; background-color: #28a745; color: white;
                          text-decoration: none; border-radius: 5px; font-weight: bold;">
                    ✓ Approve
                </a>
            </td>
            <td>
                <a href="https://abc123.ngrok.io/webhooks/deny/approvalRequest/order-12345"
                   style="padding: 12px 30px; background-color: #dc3545; color: white;
                          text-decoration: none; border-radius: 5px; font-weight: bold;">
                    ✗ Deny
                </a>
            </td>
        </tr>
    </table>
</div>
```

### Plain Text Links (when htmlFormat: false)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Please choose an action:

✓ APPROVE: https://abc123.ngrok.io/webhooks/approve/approvalRequest/order-12345

✗ DENY: https://abc123.ngrok.io/webhooks/deny/approvalRequest/order-12345

Click a link above to submit your decision.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Send Task Properties

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `includeApprovalLinks` | Boolean | Add approval/deny buttons | `true` |
| `approvalMessageRef` | String | Message reference for webhook | `approvalRequest` |
| `approvalCorrelationKey` | String | Correlation key (supports variables) | `${orderId}` |
| `htmlFormat` | Boolean | Send as HTML (styled buttons) | `true` |

## Webhook Endpoints

### Approve Endpoint

```
GET /webhooks/approve/{messageRef}/{correlationKey}
```

**Example:**
```
GET /webhooks/approve/approvalRequest/order-12345
```

**Publishes Message:**
```json
{
  "decision": "approved",
  "method": "email",
  "timestamp": "2025-12-19T10:30:00Z"
}
```

**Response (shown to user):**
```json
{
  "status": "approved",
  "message": "Your approval has been recorded. You may close this window.",
  "messageRef": "approvalRequest",
  "correlationKey": "order-12345"
}
```

### Deny Endpoint

```
GET /webhooks/deny/{messageRef}/{correlationKey}
```

**Example:**
```
GET /webhooks/deny/approvalRequest/order-12345
```

**Publishes Message:**
```json
{
  "decision": "denied",
  "method": "email",
  "timestamp": "2025-12-19T10:30:00Z"
}
```

## Testing

### 1. Execute Workflow

**Backend logs:**
```
INFO - Executing send task: Send Approval Email
INFO - Sending Email to manager@company.com
INFO - Email sent successfully via Gmail. Message ID: 18d123...
INFO - Executing receive task: Wait for Decision
INFO - Task element_4 waiting for webhook message...
```

**Workflow paused, waiting for decision**

### 2. Check Email

Manager receives email with buttons:

```
┌────────────────────────────┐
│ Approval Required          │
│                            │
│ Order ID: order-12345      │
│ Amount: $99.99             │
│                            │
│ [✓ Approve]  [✗ Deny]      │
└────────────────────────────┘
```

### 3. Click Approve

Browser opens:
```
https://abc123.ngrok.io/webhooks/approve/approvalRequest/order-12345
```

**Shows:**
```json
{
  "status": "approved",
  "message": "Your approval has been recorded. You may close this window."
}
```

### 4. Workflow Resumes

**Backend logs:**
```
INFO - Received webhook: approvalRequest, correlation: order-12345
INFO - Email approval: approvalRequest, correlation: order-12345
INFO - Task element_4 received webhook message
INFO - Message received via webhook
INFO - Executing gateway: Approved?
INFO - Condition matched: ${decision} == "approved"
INFO - Executing element: Process Order
...
```

**Workflow continues on approved path!**

## Environment Variables

**`.env` file:**
```bash
# Required for email approval links
NGROK_URL=https://abc123.ngrok.io

# Optional: Use production domain instead
# PUBLIC_URL=https://api.yourcompany.com

# Gmail OAuth
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json
```

**Backend loads automatically:**
```python
import os
ngrok_url = os.getenv('NGROK_URL', 'http://localhost:8000')
```

## Security Considerations

### 1. Use HTTPS (ngrok provides this)

All approval links use HTTPS by default ✅

### 2. Correlation Keys Should Be Unique

Use unique identifiers to prevent cross-workflow interference:
- ✅ `${orderId}` - Unique per order
- ✅ `${requestId}` - Unique per request
- ❌ `"approval"` - Not unique (all workflows would share)

### 3. Add Expiration (Optional)

Implement time-based expiration:

```yaml
- id: check_expired
  type: scriptTask
  name: Check If Expired
  properties:
    script: |
      from datetime import datetime, timedelta
      created = datetime.fromisoformat(context['createdAt'])
      if datetime.utcnow() - created > timedelta(hours=24):
          raise Exception("Approval request expired")
```

### 4. One-Time Use Links (Recommended)

Current implementation allows multiple clicks. To make one-time use:

1. Store approval state in database
2. Check if already approved/denied
3. Return error if duplicate

## Troubleshooting

### Issue: Approval links not working

**Cause:** NGROK_URL not set or incorrect

**Fix:**
```bash
# Check .env file
cat backend/.env

# Should have:
NGROK_URL=https://abc123.ngrok.io

# Restart backend after changing .env
python main.py
```

### Issue: Links point to localhost

**Cause:** NGROK_URL not loaded

**Fix:** Verify `.env` file exists and is in `backend/` directory

### Issue: "Your approval has been recorded" but workflow doesn't resume

**Cause:** Correlation key mismatch

**Check:**
```bash
# Get queue stats
curl http://localhost:8000/webhooks/queue/stats

# Check specific correlation key
curl http://localhost:8000/webhooks/queue/order-12345
```

**Verify:** Correlation key in email link matches receive task

### Issue: Email doesn't show buttons (shows raw HTML)

**Cause:** Email client doesn't support HTML or `htmlFormat: false`

**Fix:** Set `htmlFormat: true` in send task properties

## Best Practices

### 1. Always Set Timeout

```yaml
properties:
  timeout: 3600000  # 1 hour
```

Prevents workflow from waiting forever if user never clicks

### 2. Use Descriptive Correlation Keys

```yaml
approvalCorrelationKey: approval-${orderId}-${timestamp}
```

Makes debugging easier

### 3. Send Confirmation Email After Decision

```yaml
- id: send_confirmation
  type: sendTask
  name: Send Decision Confirmation
  properties:
    to: manager@company.com
    subject: Your decision was recorded
    messageBody: |
      Thank you for ${decision} order ${orderId}.
```

### 4. Handle Timeout Gracefully

Add timeout path from exclusive gateway:

```yaml
- condition: ${decision} == "approved"
  to: approve_path
- condition: ${decision} == "denied"
  to: deny_path
- condition: ""  # Default (timeout)
  to: timeout_handler
```

## Summary

**Email approval workflow allows:**

✅ **Approve/deny from email** - No app login required
✅ **Instant webhook callbacks** - Workflow resumes immediately
✅ **HTML or plain text** - Styled buttons or simple links
✅ **Works with ngrok** - Perfect for local development
✅ **Correlation matching** - Route to correct workflow instance
✅ **Gmail integration** - Real emails sent via Gmail API

**Perfect for:**
- Manager approvals
- Budget sign-offs
- Document reviews
- Order confirmations
- Any yes/no decision via email

**Get started in 5 minutes with ngrok!** 🚀
