# Email Approval Test Workflow - Quick Start

## What This Does

Send yourself an approval email with **Approve/Deny buttons** → Click a button → Workflow resumes automatically!

## Quick Setup (2 steps)

### 1. Configure .env File

```bash
cd backend
cp .env.example .env
nano .env
```

**Set your email:**
```bash
DEFAULT_TO_EMAIL=your-email@gmail.com
DEFAULT_FROM_EMAIL=your-email@gmail.com
NGROK_URL=https://abc123.ngrok.io
```

### 2. Run Workflow

```bash
# Start backend
cd backend
python main.py

# Import email-approval-test-workflow.yaml in UI
# Click Execute
# Check your email!
```

## What Happens

1. **Email arrives** with Approve/Deny buttons
2. **You click** Approve (or Deny)
3. **Webhook fires** → Workflow resumes
4. **Confirmation email** sent (approved or denied)

**You'll receive 2 emails total!**

## Expected Outcome

### First Email (Approval Request)

```
Subject: [Action Required] Approval Request - REQ-1234

┌──────────────────────────────┐
│ 🔔 Approval Request          │
│                              │
│ Request ID: REQ-1234         │
│ Amount: $250.00              │
│ Purpose: New laptop purchase │
│                              │
│  [✓ Approve]    [✗ Deny]     │
└──────────────────────────────┘
```

### Second Email (Confirmation)

```
Subject: ✅ Approved: REQ-1234

┌──────────────────────────────┐
│ ✅ APPROVED                   │
│ Your request has been        │
│ approved!                    │
│                              │
│ Request ID: REQ-1234         │
│ Amount: $250.00              │
└──────────────────────────────┘
```

## Troubleshooting

**No email?**
- Check spam folder
- Verify `DEFAULT_TO_EMAIL` in `.env` file
- Check backend logs: `grep "Email sent" backend.log`
- Restart backend after changing `.env`

**Button doesn't work?**
- Verify ngrok is running: `curl http://localhost:4040/api/tunnels`
- Check NGROK_URL in `.env` matches ngrok output
- Restart backend after changing `.env`

**Workflow doesn't resume?**
- Check backend logs: `grep "webhook message" backend.log`
- Verify correlation key matches
- Ensure receive task has `useWebhook: true`

## Full Documentation

- **Test Guide:** `EMAIL_APPROVAL_TEST_GUIDE.md` (step-by-step)
- **Implementation:** `EMAIL_APPROVAL_WORKFLOW.md` (complete docs)

## Test Now!

```bash
# 1. Edit YAML file with your email
# 2. Update .env with ngrok URL
# 3. Start backend
# 4. Import workflow in UI
# 5. Click Execute
# 6. Check your email! 📧
```

**Happy testing!** 🚀
