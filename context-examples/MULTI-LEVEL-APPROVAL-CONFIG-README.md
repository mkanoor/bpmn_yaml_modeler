# Multi-Level Approval Workflow Configuration

This document explains how to configure the multi-level approval workflow using the `multi-level-approval-config.json` file.

## Overview

The configuration file (`multi-level-approval-config.json`) provides a centralized way to manage all workflow settings without editing the YAML workflow file directly.

## Configuration Sections

### 1. Workflow Metadata

```json
{
  "name": "Multi-Level Approval with Escalation",
  "description": "IT approval workflow with escalation..."
}
```

Basic workflow identification and description.

### 2. Actors

Define the three key roles in the approval process:

```json
"actors": {
  "requester": {
    "id": "user123",
    "name": "John Doe",
    "email": "john.doe@example.com"
  },
  "itAdmin": {
    "id": "admin456",
    "name": "Sarah Admin",
    "email": "sarah.admin@example.com"
  },
  "itManager": {
    "id": "manager789",
    "name": "Michael Manager",
    "email": "michael.manager@example.com"
  }
}
```

**What to fill in:**
- `id`: Unique identifier for the user
- `name`: Full name of the user
- `email`: Email address where notifications will be sent

### 3. Timeouts

Configure all timing-related settings:

```json
"timeouts": {
  "adminWarningMinutes": 3,
  "adminWarningDuration": "PT3M",
  "adminEscalationMinutes": 5,
  "adminEscalationDuration": "PT5M",
  "managerTimeoutMinutes": 10,
  "managerTimeoutDuration": "PT10M"
}
```

**What to fill in:**
- `adminWarningMinutes`: When to send warning to IT Admin (in minutes)
- `adminWarningDuration`: ISO 8601 format duration (PT3M = 3 minutes)
- `adminEscalationMinutes`: When to escalate to manager (in minutes)
- `adminEscalationDuration`: ISO 8601 format (PT5M = 5 minutes)
- `managerTimeoutMinutes`: When to fail process if manager doesn't respond
- `managerTimeoutDuration`: ISO 8601 format (PT10M = 10 minutes)

**ISO 8601 Duration Format Examples:**
- PT30S = 30 seconds
- PT5M = 5 minutes
- PT1H = 1 hour
- P1D = 1 day
- PT2H30M = 2 hours 30 minutes

### 4. Email Settings

Configure email delivery and templates:

```json
"emailSettings": {
  "useGmail": true,
  "htmlFormat": true,
  "includeApprovalLinks": true,

  "itAdminEmail": {
    "subject": "[ACTION REQUIRED] Approval Request from ${requesterName}",
    "template": "default-admin-approval",
    "approvalMessageRef": "itAdminApproval"
  }
}
```

**What to fill in:**
- `useGmail`: true to use Gmail API, false for SMTP
- `htmlFormat`: true to send HTML emails, false for plain text
- `includeApprovalLinks`: true to include clickable approve/reject buttons
- `subject`: Email subject line (supports variables like ${requesterName})
- `template`: Which email template to use (defined in emailTemplates section)
- `approvalMessageRef`: Unique identifier for tracking approval responses

### 5. Approval Settings

Configure default approval behavior:

```json
"approvalSettings": {
  "defaultPriority": "Medium",
  "requestType": "Software Installation",
  "urgency": "Normal",
  "requireReason": true,
  "allowResubmit": true
}
```

**What to fill in:**
- `defaultPriority`: Low, Medium, High, Critical
- `requestType`: Type of request (Software Installation, Access Request, etc.)
- `urgency`: Normal, Urgent, Emergency
- `requireReason`: true if rejection reason is required
- `allowResubmit`: true if requester can resubmit after rejection

### 6. Webhook Settings

Configure webhook endpoints for approval responses:

```json
"webhookSettings": {
  "enabled": true,
  "baseUrl": "https://your-ngrok-url.ngrok.io",
  "approvalEndpoint": "/webhook/approval",
  "correlationKeyField": "requestId",
  "timeout": 300000
}
```

**What to fill in:**
- `enabled`: true to use webhooks for approval responses
- `baseUrl`: Your public webhook URL (use ngrok for testing)
- `approvalEndpoint`: Path for approval webhook
- `correlationKeyField`: Which field to use for matching requests (usually requestId)
- `timeout`: Webhook timeout in milliseconds

### 7. Variables

Define all process variables and their default values:

```json
"variables": {
  "requestId": "${uuid()}",
  "requestType": "Software Installation",
  "requestDetails": "Install Visual Studio Code and extensions",
  "priority": "Medium",
  "requesterName": "John Doe",
  "itAdminEmail": "sarah.admin@example.com",
  "adminTimeoutMinutes": 5
}
```

**What to fill in:**
- All variables used in email templates and workflow logic
- Use `${uuid()}` for unique IDs
- Use `${now()}` for current timestamp
- Update email addresses to match your actors

### 8. Email Templates

Customize the content of all notification emails:

```json
"emailTemplates": {
  "defaultAdminApproval": {
    "body": "Hello ${itAdminName},\n\nYou have received a new approval request..."
  },
  "defaultEscalation": {
    "body": "Hello ${itManagerName},\n\nThis request has been ESCALATED..."
  }
}
```

**What to fill in:**
- Customize the body text for each email type
- Use variables like `${requesterName}`, `${requestId}`, etc.
- Use `\n` for line breaks in plain text
- Available templates:
  - `defaultAdminApproval`: Initial email to IT Admin
  - `defaultWarning`: Warning email to IT Admin
  - `defaultEscalation`: Escalation email to IT Manager
  - `defaultApprovalConfirmation`: Approval notification to requester
  - `defaultRejection`: Rejection notification to requester
  - `defaultTimeout`: Timeout notification to all parties

### 9. SLA Settings

Define Service Level Agreement enforcement:

```json
"slaSettings": {
  "adminResponseSLA": {
    "minutes": 5,
    "warnAtMinutes": 3,
    "escalateAtMinutes": 5,
    "enforcementLevel": "strict"
  },
  "managerResponseSLA": {
    "minutes": 10,
    "failAtMinutes": 10,
    "enforcementLevel": "strict"
  }
}
```

**What to fill in:**
- `minutes`: Total SLA duration
- `warnAtMinutes`: When to send warning (null = no warning)
- `escalateAtMinutes`: When to escalate
- `failAtMinutes`: When to fail the process
- `enforcementLevel`: strict, moderate, or lenient

### 10. Notification Settings

Configure notification behavior:

```json
"notificationSettings": {
  "sendWarnings": true,
  "sendEscalationNotices": true,
  "sendTimeoutNotices": true,
  "ccManagerOnEscalation": false,
  "bccAdminEmail": null
}
```

**What to fill in:**
- `sendWarnings`: true to send warning emails
- `sendEscalationNotices`: true to notify when escalating
- `sendTimeoutNotices`: true to send timeout notifications
- `ccManagerOnEscalation`: true to CC manager when sending to admin
- `bccAdminEmail`: Email address for BCC (or null)

## Using the Configuration

### Option 1: Manual Application

1. Open `multi-level-approval-config.json`
2. Fill in your organization's values
3. Manually update the YAML workflow file with these values

### Option 2: Programmatic Application (Recommended)

Create a script to merge the configuration into the workflow:

```javascript
const fs = require('fs');
const yaml = require('js-yaml');

// Load configuration
const config = JSON.parse(fs.readFileSync('multi-level-approval-config.json', 'utf8'));

// Load workflow
const workflow = yaml.load(fs.readFileSync('multi-level-approval-escalation.yaml', 'utf8'));

// Apply configuration
workflow.process.name = config.workflowConfig.name;

// Update timeouts
const adminWaitTask = workflow.process.elements.find(e => e.id === 'element_8');
adminWaitTask.properties.timeout = config.workflowConfig.timeouts.adminEscalationMinutes * 60 * 1000;

// Update boundary timers
const warningTimer = workflow.process.elements.find(e => e.id === 'element_9');
warningTimer.properties.timerDuration = config.workflowConfig.timeouts.adminWarningDuration;

const escalationTimer = workflow.process.elements.find(e => e.id === 'element_10');
escalationTimer.properties.timerDuration = config.workflowConfig.timeouts.adminEscalationDuration;

// ... continue updating all elements ...

// Save updated workflow
fs.writeFileSync('workflow-configured.yaml', yaml.dump(workflow));
```

### Option 3: Runtime Configuration

Pass configuration as process variables at runtime:

```javascript
const processInstance = await engine.startProcess('multi-level-approval', {
  requesterName: config.workflowConfig.actors.requester.name,
  requesterEmail: config.workflowConfig.actors.requester.email,
  itAdminName: config.workflowConfig.actors.itAdmin.name,
  itAdminEmail: config.workflowConfig.actors.itAdmin.email,
  itManagerName: config.workflowConfig.actors.itManager.name,
  itManagerEmail: config.workflowConfig.actors.itManager.email,
  adminTimeoutMinutes: config.workflowConfig.timeouts.adminEscalationMinutes,
  managerTimeoutMinutes: config.workflowConfig.timeouts.managerTimeoutMinutes
});
```

## Example Configuration

Here's a complete example for a software development team:

```json
{
  "workflowConfig": {
    "name": "Dev Tools Approval Workflow",

    "actors": {
      "requester": {
        "id": "dev001",
        "name": "Alice Developer",
        "email": "alice@devteam.com"
      },
      "itAdmin": {
        "id": "admin001",
        "name": "Bob SysAdmin",
        "email": "bob@devteam.com"
      },
      "itManager": {
        "id": "mgr001",
        "name": "Carol Manager",
        "email": "carol@devteam.com"
      }
    },

    "timeouts": {
      "adminWarningMinutes": 2,
      "adminWarningDuration": "PT2M",
      "adminEscalationMinutes": 5,
      "adminEscalationDuration": "PT5M",
      "managerTimeoutMinutes": 10,
      "managerTimeoutDuration": "PT10M"
    },

    "approvalSettings": {
      "defaultPriority": "High",
      "requestType": "Development Tool License",
      "urgency": "Normal"
    }
  }
}
```

## Variable Reference

All variables that can be used in email templates:

| Variable | Description | Example |
|----------|-------------|---------|
| `${requestId}` | Unique request identifier | `req_12345` |
| `${requesterName}` | Name of requester | `John Doe` |
| `${requesterEmail}` | Email of requester | `john@example.com` |
| `${requestType}` | Type of request | `Software Installation` |
| `${requestDetails}` | Detailed description | `Install VS Code` |
| `${priority}` | Request priority | `Medium` |
| `${itAdminName}` | IT Admin name | `Sarah Admin` |
| `${itAdminEmail}` | IT Admin email | `sarah@example.com` |
| `${itManagerName}` | IT Manager name | `Michael Manager` |
| `${itManagerEmail}` | IT Manager email | `michael@example.com` |
| `${adminTimeoutMinutes}` | Admin timeout duration | `5` |
| `${escalationMinutes}` | Escalation timeout | `5` |
| `${managerTimeoutMinutes}` | Manager timeout | `10` |
| `${submittedTime}` | When request submitted | `2024-01-15T10:30:00Z` |
| `${approverName}` | Who approved/rejected | `Sarah Admin` |
| `${approvedTime}` | When approved | `2024-01-15T10:35:00Z` |
| `${rejectedTime}` | When rejected | `2024-01-15T10:35:00Z` |
| `${rejectionReason}` | Why rejected | `Out of budget` |

## Quick Start Checklist

1. ✅ **Update Actors Section**
   - [ ] Set requester name and email
   - [ ] Set IT Admin name and email
   - [ ] Set IT Manager name and email

2. ✅ **Configure Timeouts**
   - [ ] Set admin warning time (default: 3 minutes)
   - [ ] Set admin escalation time (default: 5 minutes)
   - [ ] Set manager timeout time (default: 10 minutes)

3. ✅ **Configure Email Settings**
   - [ ] Set useGmail to true/false
   - [ ] Update email subjects
   - [ ] Review email templates

4. ✅ **Configure Webhooks (if using)**
   - [ ] Set your ngrok or public URL
   - [ ] Set approval endpoint path

5. ✅ **Review SLA Settings**
   - [ ] Verify SLA enforcement level
   - [ ] Adjust timeout values if needed

6. ✅ **Test Configuration**
   - [ ] Load workflow in modeler
   - [ ] Execute with test data
   - [ ] Verify emails are sent correctly
   - [ ] Test timeout and escalation paths

## Support

For questions or issues with this configuration:
- Review the YAML workflow file: `multi-level-approval-escalation.yaml`
- Check the BPMN modeler documentation
- Verify all email addresses are valid
- Ensure webhook URLs are accessible

## Version History

- v1.0 (2024-12-30): Initial configuration template created
