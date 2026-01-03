# Gmail Integration Setup Guide

The improved Event-Based Gateway workflow (`ai-log-analysis-event-based-approval.yaml`) sends email notifications for approval requests. To enable actual Gmail sending (instead of simulation), follow these steps:

## Quick Summary

**Current State:** Emails are being **simulated** (not actually sent)  
**Reason:** Gmail credentials not configured  
**Your Email:** mkanoor@gmail.com (already configured in context file)

---

## Setup Steps

### 1. Get Gmail API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable **Gmail API**:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Gmail API"
   - Click "Enable"

4. Create OAuth 2.0 Credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "+ CREATE CREDENTIALS" → "OAuth client ID"
   - Application type: **Desktop app**
   - Name: "BPMN Workflow Engine"
   - Download the credentials JSON file

5. Save the downloaded file as: **`credentials.json`** in project root

### 2. Configure Environment Variables (Optional)

```bash
# Set custom paths if needed
export GMAIL_CREDENTIALS_FILE="credentials.json"
export GMAIL_TOKEN_FILE="token.json"

# Set default email addresses
export DEFAULT_FROM_EMAIL="mkanoor@gmail.com"
export DEFAULT_TO_EMAIL="mkanoor@gmail.com"
```

### 3. First-Time Authentication

Run any workflow with `useGmail: true` - the system will:
1. Open your browser for Google OAuth
2. Ask you to sign in with your Gmail account (mkanoor@gmail.com)
3. Request permissions to send emails
4. Save credentials to `token.json` (auto-generated)

After first auth, future emails send automatically!

### 4. Verify Setup

```bash
# Check if credentials exist
ls -la credentials.json token.json

# Start the backend
./start-backend.sh

# Run the improved workflow
python3 test_simple.py \
  workflows/ai-log-analysis-event-based-approval.yaml \
  context-examples/ai-log-analysis-event-based-approval-context.json
```

---

## Current Workflow Configuration

The improved workflow sends 2 emails:

### 1. Send Approval Notifications (element_send_notifications)
- **Type:** scriptTask (non-blocking notification setup)
- **Purpose:** Prepare email + UI notifications
- **Sends Email:** ❌ No (just logs URLs)

### 2. Escalate to Senior Engineer (element_escalate_task)  
- **Type:** sendTask
- **Purpose:** Timeout escalation (after 2 hours)
- **Recipient:** mkanoor@gmail.com (from context)
- **useGmail:** ✅ Yes (line 332)
- **When:** If neither email nor manual approval received in 2 hours

---

## Why Emails Aren't Sending Now

Looking at the workflow YAML:

**Issue 1: Send Approval Notifications is a scriptTask**
```yaml
- id: element_send_notifications
  type: scriptTask  # ← This just logs, doesn't send email
  name: Send Approval Notifications
```

This task only **prints** approval URLs - it doesn't actually send emails. It's designed to:
- Log email approval URL
- Log UI approval URL
- Return notification metadata

**Issue 2: Only Timeout Path Sends Email**
The only actual email sent is the **escalation email** after 2-hour timeout.

---

## Solution Options

### Option A: Wait for Timeout (Tests Escalation)
1. Configure Gmail credentials
2. Run workflow
3. Wait 2 hours
4. Email will be sent to mkanoor@gmail.com

### Option B: Add Real Email Sending to Notifications Task

Change `element_send_notifications` from `scriptTask` to `sendTask`:

```yaml
# Replace lines 131-170 with:
- id: element_send_notifications
  type: sendTask  # ← Changed from scriptTask
  name: Send Approval Email
  x: 870
  y: 330
  poolId: pool_1
  laneId: lane_2
  properties:
    messageType: "Email"
    to: "${approvalRecipients.email}"
    fromEmail: "${requester.email}"
    subject: "🔔 Approval Required: ${logFileName}"
    messageBody: |
      Hello,

      AI has analyzed the log file and found critical issues requiring approval.

      **Log File:** ${logFileName}
      **Requester:** ${requester.name}
      **Issues Found:** ${diagnosticResults.issueCount}

      **Approve via Email:** Click link in approval email
      **Approve via UI:** ${uiBaseUrl}/ui/approve/${workflowInstanceId}

      Please review and approve within 2 hours.
    useGmail: true
    priority: "High"
```

### Option C: Use Email Sending in Script Task

Keep as scriptTask but call email service:

```python
# Add to element_send_notifications script
from backend.gmail_service import get_gmail_service, is_gmail_configured

if is_gmail_configured():
    gmail = get_gmail_service()
    gmail.send_message(
        to=context.get('approvalRecipients', {}).get('email'),
        subject=f"Approval Required: {context.get('logFileName')}",
        body=f"Please approve: {approval_data['approval_url_email']}",
        from_email=context.get('requester', {}).get('email')
    )
```

---

## Testing Without Gmail

For testing without Gmail setup, the workflow will:
- ✅ Simulate email sending (logs to console)
- ✅ Complete successfully
- ✅ Test Event-Based Gateway race condition
- ❌ Not send actual emails

To test messaging flow without Gmail:
```bash
# Send manual message to trigger event
curl -X POST http://localhost:8000/api/messages \
  -H "Content-Type: application/json" \
  -d '{
    "messageRef": "diagnosticApproval",
    "correlationKey": "wf-2026-001",
    "payload": {
      "decision": "approved",
      "approver": "mkanoor@gmail.com"
    }
  }'
```

---

## Files Reference

- **Workflow:** `workflows/ai-log-analysis-event-based-approval.yaml`
- **Context:** `context-examples/ai-log-analysis-event-based-approval-context.json`
- **Gmail Service:** `backend/gmail_service.py`
- **Task Executor:** `backend/task_executors.py` (SendTaskExecutor, line 321)
- **Credentials:** `credentials.json` (you need to create)
- **Token:** `token.json` (auto-generated after first auth)

---

## Quick Fix: Enable Immediate Email Notification

If you want the approval notification email to be sent immediately (not just on timeout), I can modify the workflow to add a sendTask that actually sends the email right after diagnostics complete.

Would you like me to:
1. ✅ Set up Gmail credentials guide (done above)
2. ❓ Modify workflow to send actual approval emails immediately
3. ❓ Create test scripts to simulate messages without email

Let me know!
