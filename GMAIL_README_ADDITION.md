# Gmail Integration Feature - README Addition

## Add this section to your main README.md

---

## 📧 Gmail Integration (NEW!)

Send real emails from your workflows using Gmail API.

### Quick Setup

1. **Get OAuth credentials** from [Google Cloud Console](https://console.cloud.google.com/)
2. **Enable Gmail API** in your project
3. **Download credentials** as `backend/credentials.json`
4. **Install dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

### Use in Workflows

Configure send tasks with:
- ✅ **Use Gmail API** checkbox
- Recipient email
- Subject and message body
- Optional: HTML format

### Documentation

- **Full Guide**: [GMAIL_API_INTEGRATION.md](GMAIL_API_INTEGRATION.md)
- **Quick Start**: [GMAIL_QUICK_START.md](GMAIL_QUICK_START.md)

### Example

```yaml
- id: send_notification
  type: sendTask
  name: Send Email
  properties:
    messageType: Email
    to: user@example.com
    subject: Workflow Complete
    messageBody: Your workflow finished successfully!
    useGmail: true
```

**First run:** Browser opens for OAuth authentication
**Future runs:** Automatically uses saved token

---

## Features Summary Table (Update)

Add Gmail to your features table:

| Feature | Status | Description |
|---------|--------|-------------|
| BPMN Elements | ✅ | All core BPMN 2.0 elements |
| Gateways | ✅ | Exclusive, Inclusive, Parallel |
| User Tasks | ✅ | Approval workflows with forms |
| **Gmail API** | ✅ **NEW** | Send real emails from workflows |
| Service Tasks | ✅ | External API integration |
| Script Tasks | ✅ | Python code execution |
| Agentic Tasks | ✅ | AI-powered tasks with MCP |
| Real-time UI | ✅ | WebSocket-based execution visualization |

---

## Screenshots Section (Add)

### Gmail Configuration

**Send Task Properties:**
```
┌─ Send Task Properties ──────────┐
│ Message Type: Email              │
│ To: admin@example.com            │
│ Subject: Notification            │
│ Message Body: [text area]        │
│ ☑ Use Gmail API                  │
│   Send via Gmail (OAuth required)│
│ From Email: sender@gmail.com     │
│ ☐ HTML Format                    │
└──────────────────────────────────┘
```

**Backend Logs:**
```bash
INFO - Executing send task: Send Notification
INFO - Gmail service authenticated successfully
INFO - Email sent successfully. Message ID: 18d1234567890abc
INFO - Sent Email via Gmail - Subject: Notification
```

---

## Installation Section (Update)

Add Gmail dependencies note:

```bash
# Backend dependencies (includes Gmail API)
cd backend
pip install -r requirements.txt
```

**Optional - Gmail Integration:**
- Setup: See [GMAIL_QUICK_START.md](GMAIL_QUICK_START.md)
- Credentials required from Google Cloud Console
- Free tier: 500 emails/day

---

## Environment Variables Section (Add)

```bash
# Gmail API (optional)
GMAIL_CREDENTIALS_FILE=backend/credentials.json  # OAuth credentials
GMAIL_TOKEN_FILE=backend/token.json              # Auto-generated token
```

---

Use these sections to update your main README.md file!
