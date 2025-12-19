# Log Analysis to Ansible Workflow - Quick Start

## What This Does

🔍 **AI analyzes logs** → ✉️ **Email you for approval** → 🤖 **AI generates Ansible playbook** → 📧 **Email you the playbook**

You'll receive **2 emails**:
1. Analysis report with Approve/Deny buttons
2. Generated Ansible playbook (if approved)

## Quick Setup (3 steps)

### 1. Configure .env File

```bash
cd backend
nano .env
```

**Required settings:**
```bash
# Email (for sending/receiving)
DEFAULT_TO_EMAIL=your-email@gmail.com
DEFAULT_FROM_EMAIL=your-email@gmail.com

# Webhook (for approval buttons)
NGROK_URL=https://abc123.ngrok.io

# AI (REQUIRED for this workflow)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
```

**Get OpenRouter API key:**
1. Go to https://openrouter.ai/keys
2. Sign up (free tier available)
3. Generate API key
4. Copy to .env file

### 2. Start Services

```bash
# Terminal 1: Start ngrok
ngrok http 8000

# Terminal 2: Start backend
cd backend
python main.py
```

### 3. Run Workflow

1. Open UI: http://localhost:8000
2. Click **Import**
3. Select `log-analysis-ansible-workflow.yaml`
4. Click **Execute**
5. **Check your email!**

## What Happens

### Email 1: Analysis Report (arrives immediately)

```
Subject: [Action Required] Log Analysis Report - ANALYSIS-1234

┌──────────────────────────────────┐
│ 🔍 Log Analysis Report           │
│                                  │
│ Analysis ID: ANALYSIS-1234       │
│ Severity: HIGH                   │
│ AI Model: Claude 3.5 Sonnet      │
│ Confidence: 92%                  │
│                                  │
│ Findings:                        │
│ • Database connection errors     │
│ • Memory usage at 95%            │
│ • Disk space warnings            │
│                                  │
│  [✓ Approve]    [✗ Deny]         │
└──────────────────────────────────┘
```

**Click Approve or Deny!**

### Email 2: Ansible Playbook (after approval)

```
Subject: ✅ Ansible Playbook Generated - ANALYSIS-1234

┌──────────────────────────────────┐
│ ✅ PLAYBOOK READY                │
│                                  │
│ Generated Ansible Playbook:      │
│                                  │
│ ---                              │
│ - name: Remediate System Issues  │
│   hosts: production              │
│   tasks:                         │
│     - name: Fix database         │
│       ...                        │
│     - name: Clean disk           │
│       ...                        │
│                                  │
│ Ready to deploy!                 │
└──────────────────────────────────┘
```

## Workflow Steps

```
1. Prepare Log Analysis (Script)
   ↓ Loads sample log with errors

2. AI Log Analysis (Agentic Task #1)
   ↓ AI analyzes logs, finds issues

3. Send Analysis for Approval (Email)
   ↓ Email with Approve/Deny buttons

4. Wait for Decision (Receive Webhook)
   ↓ Waits for you to click button

5. Decision Gateway
   ├─ APPROVED → AI Generate Playbook (Agentic Task #2)
   │             ↓ AI creates Ansible YAML
   │             Send Playbook Email
   │             ↓
   │             Done! ✅
   │
   └─ DENIED  → Send Rejection Email
                ↓
                Done ❌
```

## Requirements Checklist

- [ ] Gmail OAuth configured (`credentials.json`, `token.json`)
- [ ] OpenRouter API key in `.env`
- [ ] ngrok running and URL in `.env`
- [ ] Default emails set in `.env`
- [ ] Backend server running
- [ ] Workflow imported in UI

## Troubleshooting

### No email received?

```bash
# Check Gmail is configured
ls backend/credentials.json backend/token.json

# Check .env
grep DEFAULT_TO_EMAIL backend/.env

# Check logs
tail backend/logs/backend.log | grep Email
```

### Approval button doesn't work?

```bash
# Check ngrok is running
curl http://localhost:4040/api/tunnels

# Check .env has correct URL
grep NGROK_URL backend/.env
```

### AI analysis fails?

```bash
# Check OpenRouter API key
grep OPENROUTER_API_KEY backend/.env

# Test the key
curl https://openrouter.ai/api/v1/auth/key \
  -H "Authorization: Bearer YOUR_KEY"
```

## What Gets Analyzed

The workflow includes sample logs showing:
- Database connection errors
- Memory usage at 95%
- Disk space warnings (92% full)
- Redis cache timeouts
- Performance degradation

**In production**, replace the script task to load real log files.

## AI Models Used

### Log Analysis (Agentic Task #1)
- Model: `anthropic/claude-3.5-sonnet`
- Confidence: 85%
- Tools: log-parser, grep-search, pattern-matcher

### Ansible Generation (Agentic Task #2)
- Model: `anthropic/claude-3.5-sonnet`
- Confidence: 90%
- Tools: yaml-validator, ansible-lint, template-generator

## Cost Estimate

OpenRouter pricing for Claude 3.5 Sonnet:
- Input: $3 per million tokens
- Output: $15 per million tokens

**Typical workflow:**
- Log analysis: ~2000 tokens in, ~1000 tokens out = $0.02
- Playbook generation: ~3000 tokens in, ~2000 tokens out = $0.04
- **Total per run: ~$0.06**

Free tier includes credits to get started!

## Next Steps

After receiving the playbook:

1. **Review** - Read the generated Ansible YAML carefully
2. **Test** - Run in staging environment first
3. **Customize** - Adjust variables as needed
4. **Deploy** - Execute: `ansible-playbook playbook.yml`
5. **Monitor** - Watch execution and verify fixes

## Full Documentation

See `LOG_ANALYSIS_ANSIBLE_WORKFLOW.md` for:
- Complete architecture
- All workflow steps explained
- Customization options
- Production deployment
- Advanced features

## Test It Now!

```bash
# 1. Make sure .env is configured
cat backend/.env | grep -E "DEFAULT_TO_EMAIL|NGROK_URL|OPENROUTER_API_KEY"

# 2. Start backend
cd backend && python main.py

# 3. Import workflow in UI and click Execute

# 4. Check your email!
```

**You'll receive 2 emails - analysis report and Ansible playbook!** 🎉
