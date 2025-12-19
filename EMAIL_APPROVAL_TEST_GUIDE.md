# Email Approval Test Workflow - Step-by-Step Guide

## Overview

This guide walks you through testing the email approval feature using the provided test workflow.

## What This Test Does

1. **Creates** a test purchase request
2. **Sends** you an approval email with Approve/Deny buttons
3. **Waits** for your decision (you click a button in the email)
4. **Receives** your decision via webhook
5. **Routes** to approved or denied path
6. **Sends** you a confirmation email

**You'll receive 2 emails total:**
1. Approval request (with buttons)
2. Confirmation (approved or denied)

## Prerequisites

✅ Backend running with Gmail configured
✅ ngrok tunnel active
✅ `.env` file configured with `NGROK_URL`

## Setup (5 minutes)

### Step 1: Configure Your Email Address

**Edit the workflow file:**
```bash
cd /Users/madhukanoor/devsrc/bpmn
nano email-approval-test-workflow.yaml
```

**Find and replace `YOUR_EMAIL@gmail.com` with your actual email (3 occurrences):**

Line 50:
```yaml
to: YOUR_EMAIL@gmail.com  # ← Change this
```

Line 189:
```yaml
to: YOUR_EMAIL@gmail.com  # ← Change this
```

Line 260:
```yaml
to: YOUR_EMAIL@gmail.com  # ← Change this
```

**Save the file** (Ctrl+O, Enter, Ctrl+X in nano)

### Step 2: Start ngrok

```bash
ngrok http 8000
```

**Copy the HTTPS URL from output:**
```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            Copy this URL
```

### Step 3: Update .env File

```bash
cd backend
nano .env
```

**Set NGROK_URL:**
```bash
NGROK_URL=https://abc123.ngrok.io
```

**Save the file**

### Step 4: Start Backend

```bash
cd backend
python main.py
```

**Verify in logs:**
```
INFO - Starting BPMN Workflow Execution Engine...
INFO - Gmail service authenticated successfully  ← Should see this
```

### Step 5: Start Frontend

Open your browser to the BPMN modeler (or refresh if already open)

## Testing Steps (10 minutes)

### Step 1: Import Test Workflow

1. **Click** "📁 Import YAML" button in modeler
2. **Select** `email-approval-test-workflow.yaml`
3. **Workflow appears** on canvas

**You should see:**
- Start event
- Create Test Request (script task)
- Send Approval Email (send task)
- Wait for Approval Decision (receive task)
- Log Decision (script task)
- Approved? (gateway)
- Two paths: Approved and Denied

### Step 2: Execute Workflow

1. **Click** "▶ Execute Workflow" button
2. **Watch** workflow execute in UI

**Backend logs:**
```
INFO - Starting workflow execution: <instance-id>
INFO - Executing element: Create Test Request
INFO - Executing element: Send Approval Email
INFO - Sending Email to your@email.com
INFO - Email sent successfully via Gmail. Message ID: 18d...
INFO - Executing element: Wait for Approval Decision
INFO - Task element_4 waiting for webhook message...
```

**UI shows:**
- Green ✓ on completed tasks
- Yellow ⏸ on "Wait for Approval Decision" (paused)

**Workflow is now PAUSED, waiting for your decision!**

### Step 3: Check Your Email

**Within 30 seconds, you should receive:**

```
Subject: [Action Required] Approval Request - REQ-XXXX

┌─────────────────────────────────────┐
│    🔔 Approval Request              │
│    Action Required                  │
├─────────────────────────────────────┤
│                                     │
│ Purchase Approval Needed            │
│                                     │
│ Request ID:    REQ-1234             │
│ Amount:        $250.00              │
│ Requestor:     John Doe             │
│ Department:    Engineering          │
│ Purpose:       New laptop purchase  │
│                                     │
│ ────────────────────────────────── │
│ Please choose an action:            │
│                                     │
│   [✓ Approve]    [✗ Deny]           │
│                                     │
│ Click a button above to submit      │
└─────────────────────────────────────┘
```

**If you don't see it:**
- Check spam folder
- Check Gmail sent folder (email sent to yourself)
- Check backend logs for errors

### Step 4: Click Approve (or Deny)

**Click the green "✓ Approve" button**

**Browser opens to:**
```
https://abc123.ngrok.io/webhooks/approve/purchaseApproval/REQ-1234
```

**Shows JSON response:**
```json
{
  "status": "approved",
  "message": "Your approval has been recorded. You may close this window.",
  "messageRef": "purchaseApproval",
  "correlationKey": "REQ-1234"
}
```

**Backend logs immediately:**
```
INFO - Email approval: purchaseApproval, correlation: REQ-1234
INFO - Publishing message: purchaseApproval, correlation: REQ-1234
INFO - Message delivered to waiting task: element_4
INFO - Task element_4 received webhook message
INFO - Message received via webhook
INFO - Task completed: Wait for Approval Decision
INFO - Executing element: Log Decision
INFO - Executing gateway: Approved?
INFO - Condition matched: ${decision} == "approved"
INFO - Executing element: Process Approved Request
INFO - Executing element: Send Approval Confirmation
INFO - Email sent successfully via Gmail
INFO - Workflow completed successfully
```

**UI shows:**
- Green ✓ on all tasks in approved path
- Orange ⊘ on tasks in denied path (skipped)
- Green ✓ on "Request Approved" end event

**Workflow completed!**

### Step 5: Check Confirmation Email

**Within 30 seconds, you receive:**

```
Subject: ✅ Approved: REQ-1234 - Purchase Approved

┌─────────────────────────────────────┐
│        ✅ APPROVED                   │
│   Your request has been approved!   │
├─────────────────────────────────────┤
│                                     │
│ Purchase Request Approved           │
│                                     │
│ Request ID:      REQ-1234           │
│ Amount:          $250.00            │
│ Purpose:         New laptop...      │
│ Decision Method: email              │
│ Decided At:      2025-12-19...      │
│                                     │
│ ✓ Next Steps:                       │
│ Your purchase request will be       │
│ processed within 1-2 business days. │
└─────────────────────────────────────┘
```

**Success!** 🎉

## Test Again with Deny

### Option 1: Clear and Re-run

1. **Click** "Clear Execution" button in UI
2. **Click** "▶ Execute Workflow" again
3. **Check email** for new approval request (new REQ-XXXX)
4. **Click** red "✗ Deny" button this time
5. **Receive** denial confirmation email

### Option 2: Keep Testing

Just keep clicking "Execute Workflow" - each execution creates a new request ID!

## Expected Results

### If You Click Approve:

✅ Workflow completes via approved path
✅ Confirmation email says "APPROVED"
✅ Backend logs show: `Condition matched: ${decision} == "approved"`
✅ UI shows approved path as green ✓

### If You Click Deny:

✅ Workflow completes via denied path
✅ Confirmation email says "DENIED"
✅ Backend logs show: Taking default path (denied)
✅ UI shows denied path as green ✓

## Troubleshooting

### Issue: No email received

**Check:**
```bash
# Backend logs - look for
grep "Email sent successfully" backend.log

# If you see this, email was sent
```

**Solutions:**
- Check spam folder
- Verify email address in YAML file
- Ensure Gmail OAuth is working
- Check Gmail sent folder

### Issue: Approve button doesn't work

**Check:**
```bash
# Verify ngrok URL in .env
cat backend/.env | grep NGROK_URL

# Should match ngrok output
curl http://localhost:4040/api/tunnels | jq '.tunnels[0].public_url'
```

**Solutions:**
- Restart backend after changing `.env`
- Verify ngrok tunnel is active
- Check button URL in email source

### Issue: Workflow doesn't resume

**Check backend logs:**
```bash
# Look for
grep "waiting for webhook" backend.log
grep "received webhook" backend.log
```

**Check queue:**
```bash
curl http://localhost:8000/webhooks/queue/stats
```

**Solutions:**
- Verify correlation key matches (check backend logs)
- Ensure receive task has `useWebhook: true`
- Check message ref matches between send and receive tasks

### Issue: Workflow timeout

**Symptom:** After 1 hour, workflow fails with timeout

**This is expected behavior!**

**Solution:** Click the button within 1 hour (timeout configured as 3600000ms)

## Viewing Workflow Details

### Check Active Workflows

```bash
curl http://localhost:8000/workflows/active
```

**Response:**
```json
{
  "count": 1,
  "workflows": [{
    "instance_id": "abc-123-def",
    "workflow_name": "Email Approval Test Workflow",
    "start_time": "2025-12-19T10:30:00"
  }]
}
```

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
    "correlation_keys": ["REQ-1234"]
  }
}
```

### Check Specific Correlation Key

```bash
curl http://localhost:8000/webhooks/queue/REQ-1234
```

**Response:**
```json
{
  "correlationKey": "REQ-1234",
  "queued_messages": [],
  "waiting_tasks": ["element_4"]
}
```

## Backend Log Examples

### Successful Approval Flow

```
INFO - Starting workflow execution: abc-123-def
INFO - Executing element: Start (ElementType.START_EVENT)
INFO - Executing element: Create Test Request (ElementType.SCRIPT_TASK)
INFO - Executing script task: Create Test Request (type: scriptTask)
INFO - Task completed: Create Test Request
INFO - Executing element: Send Approval Email (ElementType.SEND_TASK)
INFO - Executing send task: Send Approval Email (type: sendTask)
INFO - Sending Email via Gmail API
INFO - Email sent successfully. Message ID: 18d1234567890abc
INFO - Sent Email via Gmail - Subject: [Action Required] Approval Request - REQ-1234
INFO - Task completed: Send Approval Email
INFO - Executing element: Wait for Approval Decision (ElementType.RECEIVE_TASK)
INFO - Executing receive task: Wait for Approval Decision
INFO - Waiting for message: purchaseApproval, correlation: REQ-1234, webhook: True
INFO - Task element_4 waiting for webhook message...

... User clicks Approve button in email ...

INFO - Email approval: purchaseApproval, correlation: REQ-1234
INFO - Publishing message: purchaseApproval, correlation: REQ-1234
INFO - Message delivered to waiting task: element_4
INFO - Task element_4 received webhook message
INFO - Message received via webhook
INFO - Task completed: Wait for Approval Decision
INFO - Executing element: Log Decision (ElementType.SCRIPT_TASK)
INFO - Task completed: Log Decision
INFO - Executing gateway: Approved? (type: exclusiveGateway)
INFO - Evaluating gateway: Approved? (exclusiveGateway)
INFO - Condition matched: ${decision} == "approved" (flow: conn_6)
INFO - Gateway evaluated: 1 path(s) to follow
INFO - Executing element: Process Approved Request (ElementType.SERVICE_TASK)
INFO - Task completed: Process Approved Request
INFO - Executing element: Send Approval Confirmation (ElementType.SEND_TASK)
INFO - Email sent successfully. Message ID: 18d9876543210xyz
INFO - Task completed: Send Approval Confirmation
INFO - Executing element: Request Approved (ElementType.END_EVENT)
INFO - Reached end event: Request Approved
INFO - Workflow completed successfully: abc-123-def
```

## What You Learned

✅ **Email approval workflow pattern**
✅ **Send task with approval links**
✅ **Receive task waiting for webhooks**
✅ **Webhook correlation and routing**
✅ **Gateway decision based on webhook data**
✅ **Context variables from webhook payload**
✅ **ngrok integration for local testing**

## Next Steps

Now that you've tested the basic flow, try:

1. **Customize the email template** in the YAML
2. **Add more approval steps** (multi-stage approval)
3. **Add timeout handling** with a third path
4. **Integrate with your own email addresses**
5. **Build real approval workflows** for your use cases

## Summary

**You successfully tested:**
- ✅ Sending approval email with clickable buttons
- ✅ Workflow pausing at receive task
- ✅ Clicking approve/deny in email
- ✅ Webhook triggering and correlation
- ✅ Workflow resuming automatically
- ✅ Conditional routing based on decision
- ✅ Sending confirmation email

**The email approval workflow is working perfectly!** 🎉

Need help? Check the full documentation: `EMAIL_APPROVAL_WORKFLOW.md`
