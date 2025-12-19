# Webhook Receiver - Quick Start

## 5-Minute Setup with ngrok

### 1. Start Backend (1 min)

```bash
cd backend
python main.py
```

Backend runs on `http://localhost:8000`

### 2. Start ngrok (1 min)

```bash
ngrok http 8000
```

**Copy your public URL:**
```
https://abc123.ngrok.io
```

### 3. Create Receive Task (2 min)

In BPMN modeler, add receive task:

- **Message Reference:** `paymentConfirmation`
- **Correlation Key:** `${orderId}`
- **Timeout:** `300000` (5 minutes)
- ✅ **Use Webhook:** Checked

### 4. Execute Workflow (30 sec)

Workflow pauses at receive task, waiting for webhook.

**Backend logs:**
```
INFO - Task element_3 waiting for webhook message...
```

### 5. Send Test Webhook (30 sec)

```bash
curl -X POST https://abc123.ngrok.io/webhooks/paymentConfirmation/order-12345 \
  -H "Content-Type: application/json" \
  -d '{"status": "paid", "amount": 99.99}'
```

**Workflow resumes!** ✅

## Webhook URL Format

```
POST https://your-ngrok-url.ngrok.io/webhooks/{messageRef}/{correlationKey}
```

**Example:**
```
POST https://abc123.ngrok.io/webhooks/paymentConfirmation/order-12345
```

## How It Works

1. **Workflow starts** → Pauses at receive task
2. **External system sends webhook** → POST to ngrok URL
3. **Message correlated** → Matched to waiting task
4. **Workflow resumes** → Continues execution

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Webhook not received | Check ngrok is running: `curl http://localhost:4040/api/tunnels` |
| Correlation mismatch | Ensure correlation key matches exactly |
| Timeout | Increase timeout in receive task properties |

## Next Steps

- Read full documentation: `WEBHOOK_RECEIVER_INTEGRATION.md`
- Test with external API (Stripe, PayPal, etc.)
- Add multiple receive tasks for complex workflows

**You're ready to receive webhooks!** 🎉
