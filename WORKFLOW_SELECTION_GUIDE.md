# Workflow Selection Guide

## Overview

This BPMN workflow executor includes multiple AI log analysis workflows. This guide helps you choose the right one for your use case.

## Available Workflows

### 1. `log-analysis-ansible-workflow.yaml` ✅ RECOMMENDED for In-Memory Log Analysis

**Use this when:**
- You want to upload log content directly when starting the workflow
- You don't want to use S3 storage
- You prefer simple, in-memory processing

**Features:**
- Accepts `logFileContent` and `logFileName` in execution context
- No S3 dependencies
- Single manual approval path
- Uses OpenRouter AI for log analysis
- Results stored in context only

**Tasks:**
1. **Start Event** - Workflow begins
2. **Prepare Log Analysis** (Script Task) - Validates log content from context
3. **Analyze Logs with AI Agent** (Agentic Task) - OpenRouter AI analysis with MCP tools
4. **Approval Required?** (Exclusive Gateway) - Checks if approval needed
5. **Manual Review** (User Task) - Human approval if required
6. **Send Notification** (Send Task) - Email notification with results
7. **End Event** - Workflow completes

**Example Execution:**
```bash
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflowFile": "workflows/log-analysis-ansible-workflow.yaml",
    "context": {
      "logFileContent": "2024-01-15 10:23:45 ERROR Database connection failed\n2024-01-15 10:23:46 CRITICAL Service unavailable",
      "logFileName": "app-errors.log"
    }
  }'
```

---

### 2. `ai-log-analysis-dual-approval-workflow.yaml` ⚠️ Advanced: Dual Approval with Email

**Use this when:**
- You need dual approval paths (email + manual)
- First approval wins, other gets cancelled
- You have S3 configured for log storage
- You want webhook-based email approval

**Features:**
- Parallel approval paths (email + manual)
- Inclusive gateway merge (first-wins cancellation)
- S3 storage for logs and results
- Email approval via clickable links
- Asyncio task cancellation

**Tasks:**
1. Start Event
2. Prepare Log Analysis (Script Task)
3. Store Log in S3 (Script Task) ⚠️ **Requires S3**
4. Analyze Logs (Agentic Task)
5. Store Results in S3 (Script Task) ⚠️ **Requires S3**
6. **Parallel Gateway (AND Split)** - Creates two approval paths:
   - Path A: Send Email Approval → Wait for Email Response
   - Path B: Manual Approval Task
7. **Inclusive Gateway (OR Merge)** - First approval wins, cancels other path
8. Send Final Notification
9. End Event

**Requirements:**
- S3 bucket configured (`S3_BUCKET_NAME` env var)
- boto3 installed
- NGROK_URL for email webhook callbacks

**Example Execution:**
```bash
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflowFile": "workflows/ai-log-analysis-dual-approval-workflow.yaml",
    "context": {
      "logFileContent": "...",
      "logFileName": "errors.log"
    }
  }'
```

---

### 3. `ai-log-analysis-workflow.yaml` - Simple AI Analysis with S3

**Use this when:**
- You want S3 storage for logs and results
- You don't need approval workflows
- You want the simplest AI analysis flow

**Features:**
- S3 storage for persistence
- OpenRouter AI analysis
- No approval steps
- Email notification only

**Tasks:**
1. Start Event
2. Prepare Log Analysis
3. Store Log in S3 ⚠️ **Requires S3**
4. Analyze Logs (Agentic Task)
5. Store Results in S3 ⚠️ **Requires S3**
6. Send Notification
7. End Event

---

## Decision Tree

```
Do you need S3 storage for logs/results?
├─ NO  → Use log-analysis-ansible-workflow.yaml ✅
│
└─ YES → Do you need approval workflows?
         ├─ NO  → Use ai-log-analysis-workflow.yaml
         │
         └─ YES → Do you need dual approval (email + manual)?
                  ├─ NO  → Use log-analysis-ansible-workflow.yaml
                  │        (has manual approval)
                  │
                  └─ YES → Use ai-log-analysis-dual-approval-workflow.yaml
                           (requires NGROK_URL + S3)
```

---

## Common Errors and Solutions

### Error: `NameError: name 'open' is not defined`

**Cause:** ScriptTaskExecutor sandbox missing builtins

**Solution:** ✅ Fixed in latest version (added `open`, `__import__`, etc. to safe_builtins)

---

### Error: S3 bucket not found (but you don't want S3)

**Cause:** Running wrong workflow file

**Problem:** You're running `ai-log-analysis-dual-approval-workflow.yaml` or `ai-log-analysis-workflow.yaml`

**Solution:** Switch to `log-analysis-ansible-workflow.yaml`

**How to tell which workflow you're running:**
```bash
# Check your logs for this line:
🚀 Starting workflow execution for: workflows/XXXXX.yaml
```

If you see mentions of "Store in S3" in error traces, you're running the wrong workflow.

---

### Error: Popup not closing after email approval

**Cause:** Clicking approval link from OLD workflow execution

**How to identify:**
1. Check logs for correlation keys:
```
📧 Email approval setup:
   Resolved correlation key: 918c69af-1234-5678-abcd-1234567890ab

📬 Email approval CLICKED (POST)
   Correlation key: 69bdb0fd-5678-9012-cdef-5678901234cd  ❌ DIFFERENT!
```

2. If correlation keys don't match, you clicked an old email link

**Solution:**
- Always use the email from the CURRENT workflow execution
- Delete old approval emails to avoid confusion
- Check workflow instance ID in logs

---

## Environment Variables

### Required for ALL workflows:
```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxx   # AI analysis
DEFAULT_TO_EMAIL=you@example.com    # Notification recipient
```

### Required for S3 workflows:
```bash
AWS_ACCESS_KEY_ID=AKIAXXXXX
AWS_SECRET_ACCESS_KEY=xxxxx
S3_BUCKET_NAME=my-log-bucket
```

### Required for dual approval workflow:
```bash
NGROK_URL=https://abc123.ngrok.io   # Webhook endpoint for email clicks
```

---

## Workflow Feature Comparison

| Feature | ansible-workflow | dual-approval | simple-workflow |
|---------|-----------------|---------------|-----------------|
| S3 Storage | ❌ No | ✅ Yes | ✅ Yes |
| In-Memory Logs | ✅ Yes | ✅ Yes* | ✅ Yes* |
| Manual Approval | ✅ Yes | ✅ Yes | ❌ No |
| Email Approval | ❌ No | ✅ Yes | ❌ No |
| Dual Paths | ❌ No | ✅ Yes | ❌ No |
| Task Cancellation | ❌ No | ✅ Yes | ❌ No |
| Complexity | Simple | Advanced | Simple |

\* But also stores to S3

---

## Recommended Setup

**For Local Development (No S3):**
```bash
# .env file
OPENROUTER_API_KEY=sk-or-v1-xxxxx
DEFAULT_TO_EMAIL=dev@example.com

# Use this workflow:
workflows/log-analysis-ansible-workflow.yaml
```

**For Production (With S3 + Approvals):**
```bash
# .env file
OPENROUTER_API_KEY=sk-or-v1-xxxxx
DEFAULT_TO_EMAIL=ops@example.com
AWS_ACCESS_KEY_ID=xxxxx
AWS_SECRET_ACCESS_KEY=xxxxx
S3_BUCKET_NAME=prod-logs
NGROK_URL=https://prod.yourdomain.com

# Use this workflow:
workflows/ai-log-analysis-dual-approval-workflow.yaml
```

---

## Testing Workflows

### Test ansible-workflow (No S3):
```bash
# 1. Prepare log content
cat > /tmp/test-log.txt << 'EOF'
2024-01-15 10:23:45 ERROR Database connection timeout after 30s
2024-01-15 10:23:50 CRITICAL Service unavailable - retrying
2024-01-15 10:24:00 ERROR Failed to connect to cache server
2024-01-15 10:24:10 WARNING Memory usage at 85%
EOF

# 2. Execute workflow
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d "{
    \"workflowFile\": \"workflows/log-analysis-ansible-workflow.yaml\",
    \"context\": {
      \"logFileContent\": \"$(cat /tmp/test-log.txt | sed 's/"/\\"/g')\",
      \"logFileName\": \"test-errors.log\"
    }
  }"

# 3. Watch for workflow execution in browser
# 4. If approval task appears, approve or reject in UI
# 5. Check email for final notification
```

### Test dual-approval workflow (With S3):
```bash
# 1. Ensure S3 + NGROK configured
# 2. Execute workflow (same as above but different workflow file)
# 3. Watch for TWO approval paths:
#    - Email approval (check your inbox)
#    - Manual approval (popup in UI)
# 4. Complete ONE approval (the other should auto-cancel)
# 5. Verify cancelled task's popup closes automatically
```

---

## Troubleshooting

### "How do I know which workflow I'm running?"

Check the backend logs for:
```
🚀 Starting workflow execution for: workflows/XXXXX.yaml
🚀 Instance ID: 918c69af-1234-5678-abcd-1234567890ab
```

### "I keep getting S3 errors but don't want S3"

**Solution:** You're running the wrong workflow file.

**Quick check:** If your error mentions "Store in S3", you're NOT running `log-analysis-ansible-workflow.yaml`

**Fix:**
1. Change your curl command to use `log-analysis-ansible-workflow.yaml`
2. Restart the execution
3. Verify logs show correct workflow file

### "Email approval doesn't cancel manual popup"

**Checklist:**
1. ✅ Are correlation keys matching in logs?
2. ✅ Did you click the LATEST email (not an old one)?
3. ✅ Is WebSocket connected (see "● Connected" in UI)?
4. ✅ Are you running `dual-approval-workflow.yaml`?
5. ✅ Is asyncio task cancellation enabled? (check logs for "🔴 Cancelling asyncio task")

---

## Summary

**Most Common Use Case (In-Memory, No S3):**
```bash
USE: workflows/log-analysis-ansible-workflow.yaml
REQUIRES: OPENROUTER_API_KEY, DEFAULT_TO_EMAIL
FEATURES: AI analysis, manual approval, email notification
```

**Advanced Use Case (Dual Approval, S3 Storage):**
```bash
USE: workflows/ai-log-analysis-dual-approval-workflow.yaml
REQUIRES: All above + AWS keys + S3_BUCKET_NAME + NGROK_URL
FEATURES: Parallel approvals, task cancellation, S3 persistence
```

**Choose based on your needs, not complexity!**
