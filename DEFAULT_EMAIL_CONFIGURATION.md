# Default Email Configuration

## Overview

Configure default email addresses in `.env` file so you don't have to set them in every workflow task!

## How It Works

**Priority order for email addresses:**

1. **Task property** (highest priority)
2. **Environment variable** (fallback)
3. **Empty string** (if neither set)

## Environment Variables

Add to `backend/.env`:

```bash
# Default sender email (from address)
DEFAULT_FROM_EMAIL=workflows@yourcompany.com

# Default recipient email (to address)
DEFAULT_TO_EMAIL=admin@yourcompany.com

# Default notification email (for approvals, alerts)
DEFAULT_NOTIFICATION_EMAIL=manager@yourcompany.com
```

## Usage Examples

### Example 1: Use Default Recipient

**YAML:**
```yaml
- id: send_notification
  type: sendTask
  name: Send Notification
  properties:
    messageType: Email
    to: ""  # ← Empty! Uses DEFAULT_TO_EMAIL from .env
    subject: Workflow Complete
    messageBody: Your workflow finished successfully
    useGmail: true
```

**Sends to:** Whatever is in `DEFAULT_TO_EMAIL`

### Example 2: Override Default

**YAML:**
```yaml
- id: send_to_specific
  type: sendTask
  name: Send to Manager
  properties:
    to: manager@company.com  # ← Specified! Uses this instead
    subject: Approval Needed
    useGmail: true
```

**Sends to:** `manager@company.com` (ignores DEFAULT_TO_EMAIL)

### Example 3: Use Context Variable

**YAML:**
```yaml
- id: send_to_user
  type: sendTask
  name: Send to User
  properties:
    to: ${userEmail}  # ← Variable! Uses value from context
    subject: Your order is ready
    useGmail: true
```

**Sends to:** Whatever `userEmail` contains in workflow context

### Example 4: Default From Email

**YAML:**
```yaml
- id: send_with_default_sender
  type: sendTask
  name: Send Email
  properties:
    to: customer@example.com
    fromEmail: ""  # ← Empty! Uses DEFAULT_FROM_EMAIL
    subject: Order Confirmation
    useGmail: true
```

**Sends from:** Whatever is in `DEFAULT_FROM_EMAIL`

## Setup Steps

### Step 1: Copy Example File

```bash
cd backend
cp .env.example .env
```

### Step 2: Edit .env

```bash
nano .env
```

**Set your defaults:**
```bash
# Your workflow sender email (must be the Gmail account you authenticated)
DEFAULT_FROM_EMAIL=your-workflows@gmail.com

# Your default recipient (usually yourself for testing)
DEFAULT_TO_EMAIL=your-email@gmail.com

# Default notification recipient (manager, admin, etc.)
DEFAULT_NOTIFICATION_EMAIL=manager@company.com
```

**Save the file** (Ctrl+O, Enter, Ctrl+X)

### Step 3: Restart Backend

```bash
python main.py
```

Environment variables are loaded at startup!

## Test Workflow Example

The updated `email-approval-test-workflow.yaml` now uses defaults:

```yaml
properties:
  to: ""  # Uses DEFAULT_TO_EMAIL from .env
  subject: "[Action Required] Approval Request - ${requestId}"
  messageBody: |
    Please review this request...
  useGmail: true
```

**No email addresses hardcoded!** Just configure `.env` once.

## Complete .env Example

```bash
# ==========================================
# Webhook & ngrok Configuration
# ==========================================
NGROK_URL=https://abc123.ngrok.io


# ==========================================
# Gmail API Configuration
# ==========================================
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json

# Default email addresses
DEFAULT_FROM_EMAIL=workflows@yourcompany.com
DEFAULT_TO_EMAIL=admin@yourcompany.com
DEFAULT_NOTIFICATION_EMAIL=manager@yourcompany.com


# ==========================================
# OpenRouter API Configuration (Optional)
# ==========================================
OPENROUTER_API_KEY=your_api_key_here
```

## Priority Logic

### For "To" Address

```python
# 1. Check task property
to = task.properties.get('to', '')

# 2. If empty, use environment variable
if not to:
    to = os.getenv('DEFAULT_TO_EMAIL', '')

# 3. Resolve variables (${variable})
to = resolve_variables(to, context)
```

**Result:**
- Task has `to: "user@example.com"` → Uses `user@example.com`
- Task has `to: ""` → Uses `DEFAULT_TO_EMAIL` from .env
- Task has `to: "${userEmail}"` → Uses value from context
- Task has no `to` field → Uses `DEFAULT_TO_EMAIL` from .env

### For "From" Address

Same logic applies:

```python
from_email = task.properties.get('fromEmail', '') or os.getenv('DEFAULT_FROM_EMAIL', '')
```

## Benefits

✅ **No hardcoded emails** in workflows
✅ **Easy testing** - just update .env
✅ **Environment-specific** - different .env for dev/prod
✅ **Override when needed** - set task property to override
✅ **Works with variables** - still supports `${userEmail}`

## Use Cases

### Development/Testing

```bash
# .env for local testing
DEFAULT_TO_EMAIL=your-test-email@gmail.com
DEFAULT_FROM_EMAIL=test-workflows@gmail.com
```

All test workflows send to your test email!

### Production

```bash
# .env for production
DEFAULT_TO_EMAIL=notifications@company.com
DEFAULT_FROM_EMAIL=workflows@company.com
DEFAULT_NOTIFICATION_EMAIL=ops-team@company.com
```

Production workflows use company emails!

### Multi-Environment

**Development (.env.dev):**
```bash
DEFAULT_TO_EMAIL=dev-team@company.com
```

**Staging (.env.staging):**
```bash
DEFAULT_TO_EMAIL=qa-team@company.com
```

**Production (.env.prod):**
```bash
DEFAULT_TO_EMAIL=customers@company.com
```

Just swap .env file for different environments!

## Workflow Patterns

### Pattern 1: Send to Default Admin

```yaml
- type: sendTask
  properties:
    to: ""  # Admin
    subject: System Alert
    messageBody: Server is down!
```

### Pattern 2: Send to Specific User

```yaml
- type: sendTask
  properties:
    to: ${customerEmail}  # From context
    subject: Your Order
    messageBody: Order ${orderId} is ready
```

### Pattern 3: Send to Notification Email

```yaml
- type: sendTask
  properties:
    to: ""  # Could add DEFAULT_NOTIFICATION_EMAIL logic
    subject: Approval Needed
    includeApprovalLinks: true
```

### Pattern 4: Send to Multiple (Future)

```yaml
- type: sendTask
  properties:
    to: team@company.com,manager@company.com
    subject: Team Alert
```

## Troubleshooting

### Issue: Emails not sending

**Check .env file exists:**
```bash
ls backend/.env
```

**Check .env is loaded:**
```bash
# Add logging in task_executors.py
import os
logger.info(f"DEFAULT_TO_EMAIL: {os.getenv('DEFAULT_TO_EMAIL')}")
```

**Restart backend after changing .env:**
```bash
cd backend
python main.py
```

### Issue: Wrong email address used

**Check priority:**
1. Is `to` field set in YAML? (highest priority)
2. Is `DEFAULT_TO_EMAIL` in .env?
3. Did you restart backend after changing .env?

**Debug:**
```bash
# Check what's in .env
cat backend/.env | grep DEFAULT_TO_EMAIL

# Check backend logs
grep "Sending Email to" backend.log
```

### Issue: Variable not resolved

**Use `${variable}` syntax:**
```yaml
to: ${userEmail}  # ✓ Correct
to: $userEmail    # ✗ Wrong
to: {userEmail}   # ✗ Wrong
```

## Best Practices

### 1. Always Set Defaults in .env

Even for development:
```bash
DEFAULT_TO_EMAIL=your-email@gmail.com
```

### 2. Use Descriptive Variable Names

```bash
DEFAULT_ADMIN_EMAIL=admin@company.com
DEFAULT_SUPPORT_EMAIL=support@company.com
DEFAULT_ALERT_EMAIL=alerts@company.com
```

### 3. Document in .env.example

```bash
# Default recipient for workflow notifications
# Used when send task 'to' field is empty
DEFAULT_TO_EMAIL=your-email@gmail.com
```

### 4. Use Variables for Dynamic Recipients

```yaml
# Context has: userEmail = "john@example.com"
to: ${userEmail}  # Dynamic
```

### 5. Leave Empty in YAML for Defaults

```yaml
to: ""          # Uses DEFAULT_TO_EMAIL
fromEmail: ""   # Uses DEFAULT_FROM_EMAIL
```

## Security Note

**Don't commit .env to git!**

```bash
# .gitignore already includes:
backend/.env
backend/credentials.json
backend/token.json
```

**Only commit .env.example** with placeholder values.

## Summary

**With default email configuration:**

✅ Set `DEFAULT_TO_EMAIL` and `DEFAULT_FROM_EMAIL` in `.env`
✅ Leave `to` and `fromEmail` empty in workflows
✅ Emails automatically use defaults
✅ Override by setting task properties
✅ Still supports `${variables}` from context

**No more hardcoded emails in your workflows!** 🎉
