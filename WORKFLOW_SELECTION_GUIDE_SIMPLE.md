# Which Workflow Should I Use?

## Quick Answer

**If you're uploading log content directly (no S3):**
```bash
USE: workflows/log-analysis-ansible-workflow.yaml
```

**If you need dual approval paths (email + manual) with S3:**
```bash
USE: workflows/ai-log-analysis-dual-approval-workflow.yaml
```

---

## How to Tell Which Workflow You're Running

Check your backend logs for:
```
🚀 Starting workflow execution for: workflows/XXXXX.yaml
🚀 Instance ID: 918c69af-1234-5678-abcd-1234567890ab
```

**OR** check your error messages:
- If you see "Store in S3" → You're running a workflow with S3 tasks
- If you see S3/boto3 errors → You're running the wrong workflow!

---

## Workflow Comparison

### log-analysis-ansible-workflow.yaml ✅ SIMPLE

**What it does:**
- Upload log content when starting workflow ✅
- AI analyzes logs (no S3 needed) ✅
- Manual approval (if configured) ✅
- Email notification sent ✅
- Done! ✅

**Environment needed:**
```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxx
DEFAULT_TO_EMAIL=you@example.com
```

**Execute:**
```bash
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflowFile": "workflows/log-analysis-ansible-workflow.yaml",
    "context": {
      "logFileContent": "2024-01-15 ERROR Something broke",
      "logFileName": "errors.log"
    }
  }'
```

---

### ai-log-analysis-dual-approval-workflow.yaml ⚠️ ADVANCED

**What it does:**
- Stores logs to S3 ⚠️
- AI analyzes logs ✅
- Stores results to S3 ⚠️
- **TWO approval paths** (email + manual) ✅
- **First approval wins**, other auto-cancels ✅
- Email notification sent ✅
- Done! ✅

**Environment needed:**
```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxx
DEFAULT_TO_EMAIL=you@example.com
AWS_ACCESS_KEY_ID=AKIAxxxxx      ← Need S3!
AWS_SECRET_ACCESS_KEY=xxxxx      ← Need S3!
S3_BUCKET_NAME=my-bucket         ← Need S3!
NGROK_URL=https://xxx.ngrok.io   ← For email webhooks
```

**Execute:**
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

## Common Error: Wrong Workflow

### You said: "I don't want S3"

### But you're seeing this error:
```
NameError: name 'boto3' is not defined
```

### Why?
You're running `ai-log-analysis-dual-approval-workflow.yaml` which has S3 tasks!

### Fix:
Switch to `log-analysis-ansible-workflow.yaml`:
```bash
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflowFile": "workflows/log-analysis-ansible-workflow.yaml",  ← THIS ONE!
    "context": {
      "logFileContent": "...",
      "logFileName": "errors.log"
    }
  }'
```

---

## Visual Comparison

```
log-analysis-ansible-workflow.yaml (SIMPLE)
┌──────────────────────────────────────────────┐
│ 1. Start                                      │
│ 2. Prepare (script validates logFileContent) │
│ 3. AI Analyzes Logs ← OpenRouter             │
│ 4. Manual Approval? (optional)               │
│ 5. Send Email Notification                   │
│ 6. End                                        │
│                                               │
│ NO S3 STORAGE                                 │
│ Simple approval (manual only)                 │
└──────────────────────────────────────────────┘

ai-log-analysis-dual-approval-workflow.yaml (ADVANCED)
┌───────────────────────────────────────────────┐
│ 1. Start                                       │
│ 2. Prepare Log                                 │
│ 3. Store Log in S3 ⚠️                          │
│ 4. AI Analyzes Logs                            │
│ 5. Store Results in S3 ⚠️                      │
│ 6. Parallel Gateway → TWO PATHS:               │
│    ├─ Path A: Email with Approve/Deny links   │
│    │   └─ Wait for Email Click                │
│    └─ Path B: Manual Approval Popup           │
│                                                │
│ 7. Inclusive Gateway (FIRST WINS!)            │
│    └─ Cancels the other approval task         │
│                                                │
│ 8. Send Email Notification                    │
│ 9. End                                         │
│                                                │
│ REQUIRES S3 + NGROK                            │
│ Dual approval with cancellation                │
└────────────────────────────────────────────────┘
```

---

## Decision Tree

```
Do you want S3 storage?
├─ NO  → log-analysis-ansible-workflow.yaml
│
└─ YES → Do you need DUAL approval (email + manual)?
         ├─ NO  → log-analysis-ansible-workflow.yaml
         │        (still has manual approval, just not dual)
         │
         └─ YES → ai-log-analysis-dual-approval-workflow.yaml
                  (requires S3 + NGROK_URL)
```

---

## Summary

**Most common use case (No S3, direct upload):**
```
workflows/log-analysis-ansible-workflow.yaml
```

**Advanced use case (Dual approval, S3 storage):**
```
workflows/ai-log-analysis-dual-approval-workflow.yaml
```

**Check which you're running:**
```bash
# Look for this in logs:
grep "Starting workflow execution" backend/logs/*.log

# Should show:
🚀 Starting workflow execution for: workflows/XXXXX.yaml
```

**Still confused?**
- If error mentions "Store in S3" → Wrong workflow
- If error mentions boto3/S3 → Wrong workflow
- Switch to `log-analysis-ansible-workflow.yaml` if you don't need S3
