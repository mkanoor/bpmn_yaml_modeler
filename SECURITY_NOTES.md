# Security Notes

## Sensitive Files (DO NOT COMMIT)

The following files contain sensitive data and are excluded from Git via `.gitignore`:

### 1. Gmail OAuth Credentials
- `credentials.json` - OAuth client credentials from Google Cloud Console
- `token.json` - OAuth refresh token (auto-generated after first auth)
- `backend/credentials.json` - Alternative location
- `backend/token.json` - Alternative location

**Why:** These files contain OAuth credentials that allow sending emails from your Gmail account. If leaked, attackers could send emails as you.

### 2. SQLite Databases
- `agui_events.db` - AG-UI event storage (workflow execution events)
- `backend/agui_events.db` - Backend event storage
- `*.db`, `*.sqlite`, `*.sqlite3` - All SQLite database files

**Why:** Database files may contain:
- Log file contents with system information
- Diagnostic results from AI analysis
- Email addresses and personal information
- Approval decisions and comments
- Workflow execution history

### 3. Context Files
- `context-examples/*.json` - Workflow context with user data
- Exception: `context-examples/minimal-test.json` is safe (no personal data)

**Why:** Context files contain:
- Real email addresses
- User names and team information
- API keys and webhook URLs
- Organization-specific configuration

## Best Practices

1. **Never commit credentials** - Always use `.env` files or environment variables
2. **Review .gitignore** - Before committing, check `git status` for sensitive files
3. **Clean sensitive data** - Use `git rm --cached <file>` if accidentally committed
4. **Rotate compromised credentials** - If credentials are leaked:
   - Revoke OAuth tokens in Google Cloud Console
   - Delete and regenerate `credentials.json`
   - Delete `token.json` (will be regenerated on next auth)

## Checking for Leaks

```bash
# Check if sensitive files are tracked
git ls-files | grep -E "(credentials\.json|token\.json|\.db$|agui_events)"

# Check if files are properly ignored
git check-ignore -v credentials.json token.json *.db

# Remove accidentally committed file
git rm --cached <sensitive-file>
git commit -m "Remove sensitive file from tracking"
```

## Database Management

The SQLite databases are created automatically and grow over time. To clean them:

```bash
# Stop the backend server
./stop-backend.sh

# Delete old databases (workflow history will be lost)
rm -f agui_events.db backend/agui_events.db

# Restart server (fresh databases will be created)
./start-backend.sh
```

## Gmail Setup

See [GMAIL_SETUP.md](GMAIL_SETUP.md) for instructions on setting up Gmail OAuth credentials securely.
