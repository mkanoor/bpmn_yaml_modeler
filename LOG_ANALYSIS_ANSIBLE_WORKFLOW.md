# Log Analysis to Ansible Playbook Workflow

## Overview

This advanced workflow demonstrates a complete AI-powered DevOps automation pipeline:

1. **📊 Log Analysis** - AI analyzes system logs to identify issues
2. **✉️ Email Approval** - Send analysis report for human review
3. **🤖 Ansible Generation** - AI creates remediation playbook
4. **📧 Results Display** - Email the generated playbook

## Workflow Architecture

```
Start
  ↓
Prepare Log Analysis (Script)
  ↓
AI Log Analysis (Agentic Task #1)
  ↓
Send Analysis Report for Approval (Email with Approve/Deny)
  ↓
Wait for Approval Decision (Receive Webhook)
  ↓
Log Approval Decision (Script)
  ↓
Approved? (Gateway)
  ├─ YES → Generate Ansible Playbook (Agentic Task #2)
  │         ↓
  │        Format Playbook for Display (Service Task)
  │         ↓
  │        Send Playbook Report (Email)
  │         ↓
  │        Playbook Generated (End)
  │
  └─ NO  → Send Rejection Notification (Email)
            ↓
           Analysis Rejected (End)
```

## Features

### 1. AI-Powered Log Analysis
- Uses Claude 3.5 Sonnet for intelligent log analysis
- Identifies critical errors, performance issues, security concerns
- Provides root cause analysis and recommendations
- Confidence threshold: 85%

### 2. Email Approval System
- Beautiful HTML email with analysis findings
- Clickable Approve/Deny buttons
- Shows AI confidence, severity, and detailed findings
- 2-hour timeout for approval decision

### 3. Ansible Playbook Generation
- Second AI agent generates remediation playbook
- Production-ready Ansible YAML
- Includes error handling and verification tasks
- Follows Ansible best practices
- Confidence threshold: 90%

### 4. Results Display
- Comprehensive email with generated playbook
- Execution metrics and statistics
- Next steps for deployment
- Safety warnings and recommendations

## Prerequisites

### 1. Environment Variables

Update `backend/.env`:

```bash
# Email configuration
DEFAULT_TO_EMAIL=your-email@gmail.com
DEFAULT_FROM_EMAIL=your-workflow-sender@gmail.com

# Webhook configuration
NGROK_URL=https://your-ngrok-url.ngrok.io

# AI configuration (REQUIRED for this workflow)
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENROUTER_APP_URL=http://localhost:8000
OPENROUTER_APP_NAME=BPMN-Workflow-Executor
```

### 2. Gmail API Setup

Follow the Gmail setup guide if not already configured:
- `credentials.json` in `backend/` directory
- Run OAuth flow to generate `token.json`

### 3. OpenRouter API Key

**REQUIRED** - This workflow uses AI models:

1. Sign up at https://openrouter.ai
2. Generate API key at https://openrouter.ai/keys
3. Add to `.env` file as shown above

### 4. ngrok Running

```bash
ngrok http 8000
# Copy the https URL to .env NGROK_URL
```

## Quick Start

### Step 1: Start Backend

```bash
cd backend
python main.py
```

### Step 2: Import Workflow

1. Open UI: http://localhost:8000
2. Click **Import**
3. Select `log-analysis-ansible-workflow.yaml`

### Step 3: Execute Workflow

1. Click **Execute** button
2. Check your email for the analysis report
3. Click **Approve** or **Deny** in the email
4. If approved, check email for the generated Ansible playbook

## Workflow Steps Explained

### Step 1: Prepare Log Analysis

**Script Task** that sets up the analysis context:
- Loads sample log content (in production, would read uploaded file)
- Generates unique analysis ID
- Sets severity level
- Prepares context for AI analysis

### Step 2: AI Log Analysis (Agentic Task)

**First AI Agent** analyzes the logs:

```yaml
model: anthropic/claude-3.5-sonnet
confidenceThreshold: 0.85
tools:
  - log-parser
  - grep-search
  - pattern-matcher
```

**What it does:**
- Identifies critical errors, warnings, and issues
- Performs root cause analysis
- Determines severity levels
- Recommends remediation actions
- Prioritizes fixes

**Output:** Analysis report stored in `element_3_result`

### Step 3: Send Analysis Report for Approval

**Send Task** creates beautiful HTML email:
- Shows analysis ID, severity, confidence
- Lists all findings from AI analysis
- Displays tools used and log file details
- Includes Approve/Deny buttons

**Email includes:**
- Analysis summary
- AI confidence score
- Detailed findings
- Clickable approval buttons

### Step 4: Wait for Approval Decision

**Receive Task** waits for webhook:
- Correlation key: `${analysisId}`
- Timeout: 2 hours (7200000 ms)
- Webhook: `https://your-ngrok.ngrok.io/webhooks/approve/analysisApproval/ANALYSIS-1234`

### Step 5: Log Approval Decision

**Script Task** records the decision:
- Stores decision (approved/denied)
- Records timestamp
- Captures approval method

### Step 6: Decision Gateway

**Exclusive Gateway** routes based on decision:
- Condition: `${decision} == "approved"`
- Approved → Generate Ansible Playbook
- Denied → Send Rejection Notification

### Step 7a: Generate Ansible Playbook (APPROVED)

**Second AI Agent** generates remediation:

```yaml
model: anthropic/claude-3.5-sonnet
confidenceThreshold: 0.90
tools:
  - yaml-validator
  - ansible-lint
  - template-generator
```

**What it does:**
- Creates Ansible playbook based on findings
- Implements remediation tasks
- Adds monitoring and preventive measures
- Includes security hardening
- Follows Ansible best practices

**Output:** Production-ready Ansible YAML

### Step 8a: Format Playbook for Display

**Service Task** prepares playbook for presentation:
- Formats the generated playbook
- Adds metadata
- Prepares for email delivery

### Step 9a: Send Playbook Report

**Send Task** delivers the playbook:
- Beautiful HTML email with playbook
- Shows generation metrics
- Includes original analysis summary
- Provides deployment instructions
- Displays safety warnings

### Step 10a: Playbook Generated (Success End)

**End Event** - Workflow complete, playbook delivered!

### Step 7b: Send Rejection Notification (DENIED)

**Send Task** notifies of rejection:
- Confirms analysis was rejected
- Shows original analysis summary
- Explains no playbook was generated

### Step 8b: Analysis Rejected (Denied End)

**End Event** - Workflow complete, no playbook generated.

## Email Examples

### 1. Analysis Approval Email

```
Subject: [Action Required] Log Analysis Report - ANALYSIS-1234

┌─────────────────────────────────────┐
│ 🔍 Log Analysis Report              │
│ AI-Powered System Analysis Complete │
└─────────────────────────────────────┘

Analysis Summary
━━━━━━━━━━━━━━━━
Analysis ID: ANALYSIS-1234
Log File: application.log
Severity: HIGH
AI Model: anthropic/claude-3.5-sonnet
Confidence: 0.92

AI Analysis Findings
━━━━━━━━━━━━━━━━
Found critical database connection issues,
memory usage at 95%, disk space warnings...

[✓ Approve]  [✗ Deny]
```

### 2. Playbook Generated Email (After Approval)

```
Subject: ✅ Ansible Playbook Generated - ANALYSIS-1234

┌─────────────────────────────────────┐
│ ✅ Ansible Playbook Generated       │
│ AI-Generated Infrastructure Remedy  │
└─────────────────────────────────────┘

PLAYBOOK READY

Generation Details
━━━━━━━━━━━━━━━
Analysis ID: ANALYSIS-1234
Approved By: email-webhook
AI Model: anthropic/claude-3.5-sonnet
Confidence: 0.94

Generated Ansible Playbook
━━━━━━━━━━━━━━━━━━━━━━━━
---
- name: Remediate System Issues
  hosts: production
  become: yes
  tasks:
    - name: Fix database connection
      ...
    - name: Clean disk space
      ...
    - name: Optimize memory
      ...

📋 Next Steps
1. Review the playbook carefully
2. Test in staging first
3. Run: ansible-playbook playbook.yml
```

## Context Variables

The workflow uses these context variables:

| Variable | Source | Description |
|----------|--------|-------------|
| `logFileName` | Script Task | Name of log file analyzed |
| `logFileContent` | Script Task | Actual log content |
| `analysisId` | Script Task | Unique analysis identifier |
| `analysisTimestamp` | Script Task | When analysis started |
| `severity` | Script Task | Issue severity level |
| `element_3_result` | AI Agent #1 | Log analysis results |
| `decision` | Webhook | Approval decision (approved/denied) |
| `method` | Webhook | How decision was made |
| `approvalTimestamp` | Script Task | When decision was made |
| `element_8_result` | AI Agent #2 | Generated Ansible playbook |

## Customization

### Change AI Model

Edit the workflow YAML:

```yaml
properties:
  model: anthropic/claude-3.5-sonnet  # or any OpenRouter model
  confidenceThreshold: 0.85           # adjust confidence
```

**Available models:**
- `anthropic/claude-3.5-sonnet` (recommended)
- `anthropic/claude-3-opus`
- `openai/gpt-4-turbo`
- `google/gemini-pro-1.5`

### Adjust Approval Timeout

```yaml
properties:
  timeout: 7200000  # 2 hours in milliseconds
  # 3600000 = 1 hour
  # 14400000 = 4 hours
```

### Modify Log Content

Edit the script task to load from file:

```python
# Read from uploaded file
with open('/path/to/logfile.log', 'r') as f:
    context['logFileContent'] = f.read()
    context['logFileName'] = 'actual-log.log'
```

### Customize Email Templates

Edit the `messageBody` in send tasks to change:
- Colors and styling
- Content layout
- Information displayed

## Testing

### Test with Sample Data

The workflow includes sample log data:
- Database connection errors
- Memory usage warnings
- Disk space issues
- Performance degradation

### Test Without OpenRouter

If `OPENROUTER_API_KEY` is not set:
- Agentic tasks will use fallback simple analysis
- Workflow will complete but with mock data
- Good for testing workflow logic

### Test Email Flow

1. Run workflow
2. Check email for analysis report
3. Click Approve button
4. Check email for playbook
5. Verify playbook contains Ansible YAML

## Troubleshooting

### Issue: No email received

**Check:**
```bash
# Verify Gmail is configured
ls backend/credentials.json backend/token.json

# Check .env has email addresses
grep DEFAULT_TO_EMAIL backend/.env

# Check backend logs
tail -f backend/logs/backend.log | grep Email
```

### Issue: Approval button doesn't work

**Check:**
```bash
# Verify ngrok is running
curl http://localhost:4040/api/tunnels

# Check NGROK_URL matches
grep NGROK_URL backend/.env

# Test webhook endpoint
curl https://your-ngrok.ngrok.io/webhooks/approve/analysisApproval/TEST-123
```

### Issue: AI analysis fails

**Check:**
```bash
# Verify OpenRouter API key
grep OPENROUTER_API_KEY backend/.env

# Test API key
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"

# Check backend logs for AI errors
tail -f backend/logs/backend.log | grep -i openrouter
```

### Issue: Workflow stuck at receive task

**Symptom:** Workflow waits forever at "Wait for Approval Decision"

**Solution:**
1. Check webhook was published: `GET http://localhost:8000/webhooks/queue/stats`
2. Verify correlation key matches
3. Check 2-hour timeout hasn't expired
4. Restart backend if message queue is stuck

## Production Deployment

### 1. Use Real Log Files

Replace script task with file upload:

```python
# Read from uploaded file or API
import os
log_file = os.getenv('LOG_FILE_PATH', '/var/log/application.log')
with open(log_file, 'r') as f:
    context['logFileContent'] = f.read()
```

### 2. Configure Multiple Recipients

Update send tasks:

```yaml
properties:
  to: "devops-team@company.com,sre-team@company.com"
```

### 3. Add Slack Notifications

Add send tasks with:

```yaml
properties:
  messageType: Slack
  webhookUrl: ${SLACK_WEBHOOK_URL}
```

### 4. Store Playbooks

Add script task after playbook generation:

```python
# Save playbook to file
playbook = context.get('element_8_result', {}).get('findings', '')
filename = f"playbooks/remediation-{context['analysisId']}.yml"
with open(filename, 'w') as f:
    f.write(playbook)
```

### 5. Integrate with CI/CD

Trigger workflow from CI/CD on build failures:

```bash
# From GitLab CI, GitHub Actions, etc.
curl -X POST http://your-server:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflowId": "log-analysis-ansible",
    "context": {
      "logFilePath": "/var/log/build.log",
      "severity": "HIGH"
    }
  }'
```

## Advanced Features

### Add Manual Review Task

Insert before playbook generation:

```yaml
- id: manual_review
  type: userTask
  name: Manual Playbook Review
  properties:
    assignee: devops-lead
    priority: High
    formFields:
      - playbookApproved
      - reviewComments
```

### Add Parallel Analysis

Use parallel gateway to analyze with multiple AI models:

```yaml
- id: parallel_gateway
  type: parallelGateway
  name: Split for Multiple Models

# Then multiple agentic tasks
- model: anthropic/claude-3.5-sonnet
- model: openai/gpt-4-turbo
- model: google/gemini-pro-1.5

# Join results
- id: join_gateway
  type: parallelGateway
  name: Combine Results
```

### Add Playbook Execution

After generation, automatically execute:

```yaml
- id: execute_playbook
  type: scriptTask
  name: Execute Ansible Playbook
  properties:
    script: |
      import subprocess
      playbook = context['element_8_result']['findings']

      # Save to file
      with open('/tmp/playbook.yml', 'w') as f:
          f.write(playbook)

      # Execute
      result = subprocess.run(
          ['ansible-playbook', '/tmp/playbook.yml'],
          capture_output=True
      )

      context['playbookExecution'] = {
          'exitCode': result.returncode,
          'stdout': result.stdout.decode(),
          'stderr': result.stderr.decode()
      }
```

## Benefits

### 1. Automated DevOps Workflow
- Manual log analysis → AI-powered analysis in seconds
- Hours of playbook writing → AI generates in minutes
- Reduces human error
- Consistent remediation approach

### 2. Human-in-the-Loop
- AI provides insights, human makes decision
- Email approval ensures oversight
- Audit trail of all decisions

### 3. Production-Ready Output
- AI generates deployable Ansible code
- Follows best practices
- Includes error handling
- Ready to test and deploy

### 4. Complete Automation
- From log analysis to remediation
- Email notifications at each step
- Full audit trail
- Extensible architecture

## Summary

This workflow demonstrates:
- ✅ AI-powered log analysis (Agentic Task #1)
- ✅ Email approval system with webhooks
- ✅ AI-powered Ansible generation (Agentic Task #2)
- ✅ Beautiful HTML email reports
- ✅ Conditional routing with gateways
- ✅ Context variable usage throughout
- ✅ Production-ready architecture

**Perfect for:**
- DevOps automation
- Incident response
- Infrastructure remediation
- AI-powered operations
- Human-in-the-loop workflows

**Next Steps:**
1. Import workflow in UI
2. Configure OpenRouter API key
3. Run workflow and check email
4. Approve the analysis
5. Receive generated Ansible playbook!

Enjoy your AI-powered DevOps automation! 🚀
