# Gmail Token Management

## Understanding Gmail Files

### `credentials.json` (OAuth Client Configuration)
- **What:** OAuth 2.0 client credentials from Google Cloud Console
- **Contains:** Client ID, Client Secret, redirect URIs
- **Source:** Downloaded from https://console.cloud.google.com/apis/credentials
- **Keep or Delete:** ✅ **KEEP** - This never needs to be deleted
- **In .gitignore:** Yes (never commit to git)

### `token.json` (OAuth Access Token)
- **What:** OAuth access and refresh tokens for your account
- **Contains:** Access token, refresh token, expiry, scopes
- **Source:** Auto-generated after OAuth authorization
- **Keep or Delete:** ⚠️ **DELETE if you see scope errors**
- **In .gitignore:** Yes (never commit to git)

## When to Delete `token.json`

Delete `token.json` when you see these errors:

```
❌ invalid_scope: Bad Request
❌ Gmail authentication failed
❌ Token has been expired or revoked
❌ The OAuth client was deleted
```

**Don't delete `credentials.json`!** That's your OAuth client configuration.

## How to Re-authenticate

### Method 1: Using start-backend.sh (Easiest)

```bash
# Start backend with automatic token deletion
./start-backend.sh --reauth
```

This will:
1. Delete `token.json` if it exists
2. Start the backend
3. On first email send, browser will open for OAuth
4. After authorization, new `token.json` is created

### Method 2: Manual Deletion

```bash
cd backend
rm token.json  # Delete the token
python main.py # Restart backend
```

### Method 3: Using the Re-auth Script

```bash
cd backend
python reauth_gmail.py
```

## OAuth Flow Explained

### First Time Setup

```
1. You have: credentials.json (from Google Cloud Console)
2. Backend starts
3. First email send triggers OAuth
4. Browser opens → Google login → Approve permissions
5. token.json is created with access & refresh tokens
6. Email is sent successfully
```

### Normal Operation

```
1. Backend starts
2. Loads token.json
3. Checks if token is expired
4. If expired: Uses refresh token to get new access token
5. Updates token.json automatically
6. Email is sent successfully
```

### When Scopes Change

```
1. Code is updated with new scopes
2. Old token.json has different scopes = invalid_scope error
3. Delete token.json
4. Restart backend
5. OAuth flow runs again with new scopes
6. New token.json is created
7. Email works with new scopes
```

## The --reauth Flag

### When to Use

Use `./start-backend.sh --reauth` when:
- ✅ You see "invalid_scope" errors
- ✅ Gmail authentication fails repeatedly
- ✅ You've changed the SCOPES in gmail_service.py
- ✅ You're switching Google accounts
- ✅ Token was revoked in Google account settings

### When NOT to Use

Don't use `--reauth` when:
- ❌ Everything is working fine
- ❌ You just want to restart the backend
- ❌ You're testing other (non-email) workflows

## Scopes Required

The backend requires these Gmail API scopes:

```python
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',      # Send emails
    'https://www.googleapis.com/auth/gmail.readonly',  # Read emails
    'https://www.googleapis.com/auth/gmail.modify'     # Modify emails
]
```

If you see "invalid_scope", it means your `token.json` was created with different scopes.

## Command Reference

```bash
# Normal start
./start-backend.sh

# Start with Gmail re-authentication
./start-backend.sh --reauth
./start-backend.sh -r  # Short form

# Manual token deletion
cd backend && rm token.json

# Check if token exists
ls -l backend/token.json

# Check if credentials exist
ls -l backend/credentials.json

# View token contents (for debugging)
cat backend/token.json | python -m json.tool
```

## Troubleshooting

### Issue: "invalid_scope: Bad Request"

**Solution:**
```bash
./start-backend.sh --reauth
```

### Issue: "credentials.json not found"

**Solution:**
1. Download OAuth credentials from Google Cloud Console
2. Save as `backend/credentials.json`
3. See `GMAIL_API_INTEGRATION.md` for detailed setup

### Issue: OAuth window doesn't open

**Solution:**
- URL will be printed in console
- Copy and paste it in your browser manually
- Complete authorization
- Return to terminal

### Issue: "Access blocked: This app's request is invalid"

**Solution:**
1. Go to Google Cloud Console → APIs & Services → OAuth consent screen
2. Add required scopes:
   - `gmail.send`
   - `gmail.readonly`
   - `gmail.modify`
3. Add your email as a test user
4. Save and re-authenticate

### Issue: Token keeps getting invalid

**Nuclear option:**
```bash
# Delete both files
cd backend
rm token.json credentials.json

# Download fresh credentials.json from Google Cloud Console
# Restart with --reauth
cd ..
./start-backend.sh --reauth
```

## Best Practices

### ✅ DO

- Keep `credentials.json` safe and secure
- Delete `token.json` when you see scope errors
- Use `--reauth` flag when switching accounts
- Commit neither file to git (.gitignore handles this)

### ❌ DON'T

- Don't delete `credentials.json` (unless starting fresh)
- Don't commit tokens to git
- Don't share `credentials.json` or `token.json`
- Don't manually edit `token.json`

## File Lifecycle

### credentials.json
```
Download from Google Cloud Console
        ↓
Place in backend/
        ↓
Never changes (unless you create new OAuth client)
        ↓
Used to initiate OAuth flow
```

### token.json
```
Doesn't exist initially
        ↓
Created after first OAuth authorization
        ↓
Auto-refreshed when access token expires
        ↓
Deleted if scopes change or errors occur
        ↓
Re-created via OAuth flow
```

## Summary

**The Issue:** Code updated with new Gmail scopes, but `token.json` has old scopes

**The Fix:** Delete `token.json` (NOT `credentials.json`) and re-authenticate

**The Command:**
```bash
./start-backend.sh --reauth
```

**What Happens:**
1. Token deleted
2. Backend starts
3. First email triggers OAuth
4. Browser opens for authorization
5. New token created with correct scopes
6. Emails work! ✅

---

**Remember:**
- `credentials.json` = Client configuration (keep forever)
- `token.json` = Access token (delete when errors occur)
