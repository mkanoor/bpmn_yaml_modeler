# Gmail Re-authentication Instructions

## Problem

You're seeing this error:
```
invalid_scope: Bad Request
Gmail authentication failed
```

This happens when the Gmail token (`token.json`) was created with different scopes than what the code now requires.

## Solution

Delete the old token and re-authenticate with the correct scopes.

## Steps

### Option 1: Automatic Re-authentication (Recommended)

The backend will automatically trigger OAuth flow when it detects the token is missing or invalid.

```bash
# 1. Delete the old token
cd backend
rm token.json

# 2. Restart the backend
# Stop the current backend (Ctrl+C)
python main.py

# 3. Run a workflow that sends email
# The first email send will trigger OAuth flow
# Your browser will open for authorization
# Approve the requested permissions
# token.json will be created automatically
```

### Option 2: Manual Re-authentication Script

```bash
cd backend

# If using virtual environment, activate it first
source /path/to/venv/bin/activate

# Run the re-auth script
python reauth_gmail.py
```

### Option 3: Quick Manual Method

```bash
cd backend

# Delete old token
rm token.json

# Open Python and authenticate
python
>>> from gmail_service import get_gmail_service
>>> service = get_gmail_service()
>>> service.authenticate()
# Browser will open for OAuth
# Approve the permissions
# token.json will be created
>>> exit()

# Now restart backend
python main.py
```

## What Scopes Are Needed

The code requires these Gmail API scopes:

```python
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',      # Send emails
    'https://www.googleapis.com/auth/gmail.readonly',  # Read emails
    'https://www.googleapis.com/auth/gmail.modify'     # Modify emails
]
```

## Troubleshooting

### Issue: OAuth window doesn't open

**Solution:**
1. Check that you're running on a machine with a browser
2. The URL will be printed in the console if browser fails
3. Copy the URL to a browser manually

### Issue: "Access blocked: This app's request is invalid"

**Cause:** OAuth consent screen not configured properly in Google Cloud Console.

**Solution:**
1. Go to https://console.cloud.google.com/apis/credentials/consent
2. Configure OAuth consent screen
3. Add your email as a test user
4. Make sure scopes are added:
   - `.../auth/gmail.send`
   - `.../auth/gmail.readonly`
   - `.../auth/gmail.modify`

### Issue: "The OAuth client was not found"

**Cause:** credentials.json is invalid or from wrong project.

**Solution:**
1. Download fresh credentials.json from Google Cloud Console
2. Go to https://console.cloud.google.com/apis/credentials
3. Click your OAuth 2.0 Client ID
4. Click "Download JSON"
5. Save as `backend/credentials.json`

### Issue: Re-authentication keeps failing

**Nuclear option:**
```bash
cd backend

# Delete everything
rm token.json credentials.json

# Start fresh
# 1. Download new credentials.json from Google Cloud Console
# 2. Restart backend - it will trigger OAuth flow
# 3. Approve all requested permissions
```

## After Re-authentication

Once you see:
```
✅ SUCCESS! Gmail is now authenticated.
```

You can:
1. Run the email approval test workflow
2. Run the log analysis workflow
3. Send emails from any workflow

The new `token.json` will have the correct scopes and will work properly.

## Check Authentication Status

```bash
cd backend
python -c "from gmail_service import is_gmail_configured; print('Gmail configured:', is_gmail_configured())"
```

## Automatic Token Refresh

The Gmail service automatically refreshes expired tokens. You should only need to re-authenticate if:
- Scopes change
- Token is revoked
- credentials.json changes
- Moving to a different machine

## Next Steps

After re-authentication:

1. **Restart backend:** `python main.py`
2. **Test email workflow:** Import and run `email-approval-test-workflow.yaml`
3. **Check your email:** You should receive test emails

If you still have issues, check the backend logs:
```bash
tail -f backend/logs/backend.log | grep -i gmail
```
