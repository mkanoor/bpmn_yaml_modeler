# Gmail API Quick Start Guide

## 5-Minute Setup

### 1. Get OAuth Credentials (2 minutes)

1. Go to https://console.cloud.google.com/
2. Create project → Enable Gmail API
3. Create OAuth credentials (Desktop app)
4. Download as `credentials.json`
5. Place in: `/Users/madhukanoor/devsrc/bpmn/backend/credentials.json`

### 2. Install Dependencies (1 minute)

```bash
cd backend
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
```

### 3. Configure Send Task (1 minute)

In your BPMN modeler, select a send task and set:

- ✅ **Use Gmail API**: Checked
- **To**: `recipient@example.com`
- **Subject**: `Test Email`
- **Message Body**: `Hello from BPMN!`

### 4. Execute & Authenticate (1 minute)

1. Run workflow
2. Browser opens → Login to Google → Allow permissions
3. Email sent! ✅

`token.json` is created automatically for future runs.

## Minimal Example

```yaml
- id: send_email
  type: sendTask
  name: Send Email
  properties:
    messageType: Email
    to: user@example.com
    subject: Hello
    messageBody: This is a test email
    useGmail: true
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No browser opens | Check `credentials.json` exists |
| "API not enabled" | Enable Gmail API in Cloud Console |
| Email not sent | Check backend logs for error |
| Token expired | Delete `token.json`, re-authenticate |

## Next Steps

- Send HTML emails: Set `htmlFormat: true`
- Use variables: `${variableName}` in subject/body
- Read full docs: `GMAIL_API_INTEGRATION.md`

---

**That's it! You're now sending real emails!** 📧
