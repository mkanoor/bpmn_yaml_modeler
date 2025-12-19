# Webhook Receiver Integration with ngrok

## Overview

Your BPMN workflows can now **receive notifications** from external systems via webhooks! This allows workflows to pause at receive tasks and wait for real external events (payments, approvals, API callbacks, etc.).

Perfect for local development with **ngrok** - no port forwarding needed!

## Features

- ✅ **Webhook Endpoints** - Receive HTTP POST notifications
- ✅ **Message Correlation** - Match webhooks to specific workflow instances
- ✅ **Async Waiting** - Receive tasks pause until webhook arrives
- ✅ **Payload Extraction** - Webhook data automatically added to workflow context
- ✅ **Timeout Handling** - Configurable timeout for waiting tasks
- ✅ **ngrok Integration** - Expose local server to internet easily

## How It Works

### 1. Workflow Waits at Receive Task

```yaml
- id: wait_payment
  type: receiveTask
  name: Wait for Payment Confirmation
  properties:
    messageRef: paymentConfirmation
    correlationKey: ${orderId}
    timeout: 300000  # 5 minutes
    useWebhook: true
```

**Workflow pauses** here, waiting for webhook

### 2. External System Sends Webhook

External payment gateway sends POST request to your server:

```bash
POST https://your-ngrok-url.ngrok.io/webhooks/paymentConfirmation/order-12345
{
  "orderId": "12345",
  "amount": 99.99,
  "status": "paid",
  "transactionId": "txn_abc123"
}
```

### 3. Workflow Resumes

- Webhook matched to waiting receive task
- Payload data added to workflow context
- Workflow continues execution
- Next tasks can use `${amount}`, `${status}`, etc.

## Setup with ngrok

### Step 1: Install ngrok

```bash
# macOS (Homebrew)
brew install ngrok

# Or download from https://ngrok.com/download
```

### Step 2: Authenticate ngrok (One-Time)

```bash
ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN
```

Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken

### Step 3: Start Your Backend

```bash
cd backend
python main.py
```

Backend runs on `http://localhost:8000`

### Step 4: Start ngrok Tunnel

```bash
ngrok http 8000
```

**Output:**
```
ngrok

Session Status                online
Account                       your@email.com
Version                       3.x.x
Region                        United States (us)
Forwarding                    https://abc123.ngrok.io -> http://localhost:8000

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**Your public webhook URL:**
```
https://abc123.ngrok.io/webhooks/message
```

✅ **This URL is accessible from anywhere on the internet!**

### Step 5: Use Webhook URL in External System

Configure your external system (payment gateway, API, etc.) to send webhooks to:

```
https://abc123.ngrok.io/webhooks/{messageRef}/{correlationKey}
```

Or use the generic endpoint:

```
https://abc123.ngrok.io/webhooks/message
```

## Webhook Endpoints

### 1. Simple Endpoint (Recommended)

**Format:**
```
POST /webhooks/{messageRef}/{correlationKey}
```

**Example:**
```bash
curl -X POST https://abc123.ngrok.io/webhooks/paymentConfirmation/order-12345 \
  -H "Content-Type: application/json" \
  -d '{
    "orderId": "12345",
    "amount": 99.99,
    "status": "paid"
  }'
```

**Response:**
```json
{
  "status": "received",
  "messageRef": "paymentConfirmation",
  "correlationKey": "order-12345",
  "delivered": true
}
```

- `delivered: true` - Webhook was delivered to waiting receive task
- `delivered: false` - Webhook was queued (no task waiting yet)

### 2. Generic Endpoint

**Format:**
```
POST /webhooks/message
```

**Payload:**
```json
{
  "messageRef": "paymentConfirmation",
  "correlationKey": "order-12345",
  "payload": {
    "orderId": "12345",
    "amount": 99.99,
    "status": "paid"
  }
}
```

**Example:**
```bash
curl -X POST https://abc123.ngrok.io/webhooks/message \
  -H "Content-Type: application/json" \
  -d '{
    "messageRef": "paymentConfirmation",
    "correlationKey": "order-12345",
    "payload": {
      "orderId": "12345",
      "amount": 99.99,
      "status": "paid"
    }
  }'
```

## Message Correlation

**Correlation Key** matches webhooks to specific workflow instances.

### Example: Order Processing Workflow

**Workflow Context:**
```javascript
{
  orderId: "12345",
  customerId: "cust-789",
  amount: 99.99
}
```

**Receive Task Configuration:**
```yaml
properties:
  messageRef: paymentConfirmation
  correlationKey: ${orderId}  # Resolves to "12345"
  useWebhook: true
```

**Webhook Must Match:**
- **Message Ref:** `paymentConfirmation`
- **Correlation Key:** `order-12345` (same value)

**Webhook URL:**
```
POST /webhooks/paymentConfirmation/order-12345
```

### Multiple Workflow Instances

If you have 3 concurrent workflows waiting for payments:

| Instance | Order ID | Correlation Key | Webhook URL |
|----------|----------|-----------------|-------------|
| Instance 1 | order-12345 | order-12345 | `/webhooks/paymentConfirmation/order-12345` |
| Instance 2 | order-67890 | order-67890 | `/webhooks/paymentConfirmation/order-67890` |
| Instance 3 | order-11111 | order-11111 | `/webhooks/paymentConfirmation/order-11111` |

Each webhook is **routed to the correct instance** using correlation key!

## Receive Task Properties

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `messageRef` | String | Message type/topic | `paymentConfirmation` |
| `correlationKey` | String | Unique identifier (supports `${variable}`) | `${orderId}` |
| `timeout` | Number | Timeout in milliseconds | `300000` (5 min) |
| `useWebhook` | Boolean | Enable webhook mode | `true` |

## Workflow Context After Webhook

When webhook is received, **payload is merged into context**:

**Webhook Payload:**
```json
{
  "orderId": "12345",
  "amount": 99.99,
  "status": "paid",
  "transactionId": "txn_abc123"
}
```

**Context After:**
```javascript
{
  // Original context
  orderId: "12345",
  customerName: "John Doe",

  // Webhook payload merged in
  amount: 99.99,
  status: "paid",
  transactionId: "txn_abc123",

  // Full message stored separately
  element_3_message: {
    messageRef: "paymentConfirmation",
    correlationKey: "order-12345",
    payload: { ... },
    timestamp: "2025-12-19T10:30:00Z"
  },
  element_3_payload: { ... }
}
```

**Next tasks can use:**
- `${amount}`
- `${status}`
- `${transactionId}`

## Example Workflow YAML

```yaml
process:
  name: Order Payment Workflow
  id: order-payment-workflow
  elements:
    - id: element_1
      type: startEvent
      name: Start Order
      x: 100
      y: 150

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
          result = {'orderId': orderId, 'created': True}

    - id: element_3
      type: receiveTask
      name: Wait for Payment
      x: 450
      y: 150
      properties:
        messageRef: paymentConfirmation
        correlationKey: ${orderId}
        timeout: 300000  # 5 minutes
        useWebhook: true

    - id: element_4
      type: sendTask
      name: Send Confirmation Email
      x: 650
      y: 150
      properties:
        messageType: Email
        to: customer@example.com
        subject: Payment Received - Order ${orderId}
        messageBody: |
          Thank you for your payment!

          Order ID: ${orderId}
          Amount: $${amount}
          Transaction: ${transactionId}
          Status: ${status}
        useGmail: true

    - id: element_5
      type: endEvent
      name: Order Complete
      x: 850
      y: 150

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
```

## Testing Workflow

### 1. Start Workflow

**Execute** workflow in UI or via API:

```bash
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "yaml": "... workflow yaml ...",
    "context": {}
  }'
```

**Workflow pauses at receive task:**
```
Backend logs:
INFO - Executing element: Wait for Payment
INFO - Waiting for message: paymentConfirmation, correlation: order-12345
INFO - Task element_3 waiting for webhook message...
```

### 2. Send Webhook (While Workflow Waiting)

```bash
curl -X POST https://your-ngrok-url.ngrok.io/webhooks/paymentConfirmation/order-12345 \
  -H "Content-Type: application/json" \
  -d '{
    "orderId": "12345",
    "amount": 99.99,
    "status": "paid",
    "transactionId": "txn_abc123"
  }'
```

**Response:**
```json
{
  "status": "received",
  "messageRef": "paymentConfirmation",
  "correlationKey": "order-12345",
  "delivered": true
}
```

**Backend logs:**
```
INFO - Received webhook: paymentConfirmation, correlation: order-12345
INFO - Task element_3 received webhook message
INFO - Message received via webhook
INFO - Task completed: Wait for Payment
INFO - Executing element: Send Confirmation Email
...
```

**Workflow resumes and completes!**

## Monitoring & Debugging

### Check Queue Stats

```bash
curl http://localhost:8000/webhooks/queue/stats
```

**Response:**
```json
{
  "status": "ok",
  "queue_stats": {
    "total_queued_messages": 0,
    "total_waiting_tasks": 1,
    "correlation_keys": ["order-12345"]
  }
}
```

### Check Specific Correlation Key

```bash
curl http://localhost:8000/webhooks/queue/order-12345
```

**Response:**
```json
{
  "correlationKey": "order-12345",
  "queued_messages": [],
  "waiting_tasks": ["element_3"]
}
```

### Clear Queued Messages

```bash
curl -X DELETE http://localhost:8000/webhooks/queue/order-12345
```

## Behavior Scenarios

### Scenario 1: Webhook Arrives Before Workflow Starts

1. Webhook arrives → **Queued**
2. Workflow starts → Receive task checks queue
3. Message found → **Delivered immediately**
4. Workflow continues

### Scenario 2: Workflow Waiting, Webhook Arrives

1. Workflow starts → Receive task **waits**
2. Webhook arrives → **Delivered immediately**
3. Workflow continues

### Scenario 3: Timeout Expires

1. Workflow starts → Receive task **waits**
2. No webhook arrives
3. Timeout expires → **Workflow fails** with timeout error

### Scenario 4: Wrong Correlation Key

1. Workflow waiting for `order-12345`
2. Webhook arrives with `order-99999` → **Queued separately**
3. Workflow still waiting (no match)
4. Eventually times out

## ngrok Best Practices

### 1. Use Reserved Domain (Paid Plan)

**Free tier:** URL changes every time you restart ngrok
```
https://abc123.ngrok.io  (changes next restart)
```

**Paid tier:** Get permanent URL
```
https://mycompany.ngrok.io  (never changes)
```

### 2. Start ngrok in Background

```bash
ngrok http 8000 > /dev/null &
```

### 3. Get ngrok URL Programmatically

```bash
curl http://localhost:4040/api/tunnels | jq '.tunnels[0].public_url'
```

Output: `https://abc123.ngrok.io`

### 4. Use ngrok Config File

**Create `~/.ngrok2/ngrok.yml`:**
```yaml
authtoken: YOUR_AUTH_TOKEN
tunnels:
  bpmn:
    proto: http
    addr: 8000
    subdomain: my-bpmn  # Requires paid plan
```

**Start:**
```bash
ngrok start bpmn
```

## Security Considerations

### 1. Validate Webhook Signatures (Recommended)

Add signature validation to webhook endpoints:

```python
@app.post("/webhooks/message")
async def receive_webhook_message(request: Request):
    # Validate signature
    signature = request.headers.get('X-Webhook-Signature')
    if not validate_signature(await request.body(), signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Process webhook...
```

### 2. Use HTTPS Only

ngrok provides HTTPS by default ✅

### 3. IP Whitelisting

Configure ngrok to only accept requests from known IPs (paid feature)

### 4. Rate Limiting

Add rate limiting to prevent abuse:

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/webhooks/message")
@limiter.limit("10/minute")
async def receive_webhook_message(request: Request):
    ...
```

## Troubleshooting

### Issue: "delivered: false" but workflow waiting

**Cause:** Correlation key mismatch

**Fix:** Check that correlation keys match exactly:
```bash
# Check waiting tasks
curl http://localhost:8000/webhooks/queue/stats

# Verify correlation key in workflow context
```

### Issue: Workflow times out

**Cause:** Webhook never arrived or wrong correlation key

**Fix:**
1. Check webhook URL is correct
2. Verify external system is sending webhooks
3. Check ngrok tunnel is running
4. Review backend logs for received webhooks

### Issue: ngrok tunnel not accessible

**Cause:** ngrok not running or firewall blocking

**Fix:**
```bash
# Check ngrok status
curl http://localhost:4040/api/tunnels

# Restart ngrok
pkill ngrok
ngrok http 8000
```

### Issue: Multiple webhooks for same correlation key

**Cause:** External system retrying or duplicate sends

**Behavior:**
- First webhook → Delivered to waiting task
- Additional webhooks → Queued (no waiting task)

**Fix:** Clear queue after workflow completes:
```bash
curl -X DELETE http://localhost:8000/webhooks/queue/order-12345
```

## Backend Logs

**Workflow waiting:**
```
INFO - Executing receive task: Wait for Payment
INFO - Waiting for message: paymentConfirmation, correlation: order-12345, webhook: True
INFO - Task element_3 waiting for webhook message...
```

**Webhook received:**
```
INFO - Received webhook: paymentConfirmation, correlation: order-12345
INFO - Publishing message: paymentConfirmation, correlation: order-12345
INFO - Message delivered to waiting task: element_3
INFO - Task element_3 received webhook message
INFO - Message received via webhook
INFO - Task completed: Wait for Payment
```

## Summary

**Webhook integration allows your workflows to:**

✅ **Pause and wait** for real external events
✅ **Receive notifications** from any HTTP-capable system
✅ **Correlate messages** to specific workflow instances
✅ **Extract data** from webhook payloads into workflow context
✅ **Work locally** with ngrok (no port forwarding!)
✅ **Handle timeouts** gracefully

**Perfect for:**
- Payment confirmations
- API callbacks
- User approvals via external systems
- IoT sensor notifications
- Third-party integration events

**Get started in 5 minutes with ngrok!** 🚀
