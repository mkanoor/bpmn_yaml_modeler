# Correlation Key Debugging Guide

## The Issue

Based on your logs, the email is being sent with one correlation key, but the receive task is waiting for a different correlation key:

```
Receive task waiting for:  34326566-e4d5-416d-84a1-9634b873a03c
Email approval sent with:  69bdb0fd-3d85-4eb9-abce-d46f27be641d
```

## New Logging Added

### 1. Workflow Instance Creation
Shows the exact instance ID when workflow starts:
```
🚀 ========================================
🚀 Starting NEW workflow execution
🚀 Instance ID: <uuid>
🚀 Context keys: [...]
🚀 ========================================
```

### 2. Email Send Task (element_22)
Shows what correlation key is being used in the email:
```
📧 Email approval setup:
   Message ref: diagnosticApproval
   Correlation key template: ${workflowInstanceId}
   Resolved correlation key: <uuid>
   Context workflowInstanceId: <uuid>

🔗 Building approval URLs:
   Message ref: diagnosticApproval
   Correlation key: <uuid>
   Ngrok URL: https://...
✅ APPROVE URL IN EMAIL: https://.../webhooks/approve/diagnosticApproval/<uuid>
❌ DENY URL IN EMAIL: https://.../webhooks/deny/diagnosticApproval/<uuid>
```

### 3. Receive Task (element_23)
Shows what correlation key the receive task is waiting for:
```
📥 Receive task setup:
   Message ref: diagnosticApproval
   Correlation key template: ${workflowInstanceId}
   Resolved correlation key: <uuid>
   Context workflowInstanceId: <uuid>
```

### 4. Email Approval Click
Shows what URL was actually clicked:
```
📬 ========================================
📬 Email approval CLICKED (POST)
📬 Message ref: diagnosticApproval
📬 Correlation key: <uuid>
📬 Full URL: /webhooks/approve/diagnosticApproval/<uuid>
📬 ========================================
```

## What to Look For

When you run a single workflow execution, trace through the logs:

### Step 1: Workflow starts
```
🚀 Instance ID: AAAA-BBBB-CCCC
```
**Note this ID!**

### Step 2: Email is sent
```
📧 Resolved correlation key: XXXX-YYYY-ZZZZ
✅ APPROVE URL IN EMAIL: .../approve/diagnosticApproval/XXXX-YYYY-ZZZZ
```
**Does XXXX-YYYY-ZZZZ match AAAA-BBBB-CCCC?**

### Step 3: Receive task waits
```
📥 Resolved correlation key: PPPP-QQQQ-RRRR
```
**Does PPPP-QQQQ-RRRR match AAAA-BBBB-CCCC?**

### Step 4: You click email link
```
📬 Correlation key: MMMM-NNNN-OOOO
```
**Does MMMM-NNNN-OOOO match the URL in the email (XXXX-YYYY-ZZZZ)?**

## Expected Result (All Should Match)

```
🚀 Instance ID:           12345678-1234-1234-1234-123456789ABC
📧 Email correlation:     12345678-1234-1234-1234-123456789ABC  ✅ MATCH
📥 Receive correlation:   12345678-1234-1234-1234-123456789ABC  ✅ MATCH
📬 Clicked URL:           12345678-1234-1234-1234-123456789ABC  ✅ MATCH
```

## If They Don't Match

### Scenario 1: Email and Receive tasks have different IDs
**Problem:** Context is not being shared between parallel paths
**Solution:** This would be a bug in the workflow engine

### Scenario 2: Clicked URL doesn't match email URL
**Problem:** You clicked an approval link from a DIFFERENT workflow execution
**Solution:** Make sure you're clicking the link from the most recent email

### Scenario 3: Different workflow instance ID
**Problem:** Multiple workflow executions are running
**Solution:** Only trigger ONE workflow, wait for both email and popup

## Testing Steps

1. **Clear any old emails** - Delete old approval emails to avoid confusion

2. **Start ONE workflow:**
   ```bash
   cd /Users/madhukanoor/devsrc/bpmn
   ./test_dual_approval.sh
   ```

3. **Note the instance ID from logs:**
   ```
   🚀 Instance ID: <copy-this-uuid>
   ```

4. **Wait for both paths:**
   - Manual approval popup appears in UI
   - Email arrives in inbox

5. **Check the email URL** in the backend logs:
   ```
   ✅ APPROVE URL IN EMAIL: <copy-this-url>
   ```

6. **Verify receive task correlation:**
   ```
   📥 Resolved correlation key: <should-match-instance-id>
   ```

7. **Click the email approval link**

8. **Check what URL was clicked:**
   ```
   📬 Correlation key: <should-match-email-url>
   ```

9. **Verify all 4 UUIDs match!**

## Next Steps

Please run one workflow execution and paste the complete logs showing all 4 sections:
1. 🚀 Workflow start
2. 📧 Email send
3. 📥 Receive task
4. 📬 Email clicked

This will help us identify exactly where the correlation key mismatch is occurring.
