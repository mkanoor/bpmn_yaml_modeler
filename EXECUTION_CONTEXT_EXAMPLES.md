# Execution Context Examples for Subprocess Workflows

## Overview

When executing a workflow with Call Activities and variable mappings, you need to provide **initial context data** that matches what your workflow expects.

---

## Example 1: Simple Call Activity (Budget + HR Approvals)

### Workflow: `call-activity-with-mappings-demo.yaml`

This workflow has two script tasks that create `budgetRequest` and `hrRequest` objects, which are then mapped into the subprocess.

### **Context to Provide:**

Since the script tasks **create** the data, you only need to provide the **email addresses** for the approvers:

```json
{
  "budgetApprover": "manager@example.com",
  "hrApprover": "hr-director@example.com"
}
```

**Note**: The workflow's script tasks will create the full request objects. You just need to ensure the email variables are available if referenced.

---

## Example 2: Pre-Populated Context (No Script Tasks)

If you want to **skip the script tasks** and provide data directly:

```json
{
  "budgetRequest": {
    "title": "Q1 2024 Marketing Budget",
    "details": "Requesting $50,000 for digital marketing campaigns",
    "amount": 50000,
    "requester": {
      "name": "Alice Johnson",
      "email": "alice@example.com",
      "department": "Marketing"
    },
    "priority": "high",
    "approver": "manager@example.com"
  },
  "hrRequest": {
    "title": "New Hire - Senior Developer",
    "details": "Approval to hire a senior full-stack developer",
    "salary": 120000,
    "requester": {
      "name": "Bob Smith",
      "email": "bob@example.com",
      "department": "Engineering"
    },
    "priority": "medium",
    "approver": "hr-director@example.com"
  }
}
```

---

## Example 3: Single Approval Request

For a simple workflow with just one approval:

```json
{
  "request": {
    "title": "Purchase New Laptops",
    "details": "Need to purchase 5 MacBook Pros for the development team",
    "requester": {
      "name": "Charlie Davis",
      "email": "charlie@example.com",
      "department": "IT"
    },
    "priority": "high",
    "amount": 15000,
    "approver": "cto@example.com"
  }
}
```

---

## Example 4: Multiple Approvers (Same Subprocess, Different Recipients)

```json
{
  "requests": [
    {
      "type": "budget",
      "title": "Annual Software Licenses",
      "details": "Renewal of Adobe Creative Cloud for 20 users",
      "requester": {
        "name": "David Lee",
        "email": "david@example.com"
      },
      "priority": "high",
      "approver": "finance-manager@example.com"
    },
    {
      "type": "equipment",
      "title": "Office Furniture Purchase",
      "details": "Standing desks and ergonomic chairs for new office space",
      "requester": {
        "name": "Emma Wilson",
        "email": "emma@example.com"
      },
      "priority": "medium",
      "approver": "facilities-manager@example.com"
    }
  ]
}
```

---

## How Variable Mappings Use This Context

### Workflow Configuration:

```yaml
# Call Activity with Input Mappings
inputMappings:
  - source: budgetRequest.title        # From context
    target: requestTitle                # To subprocess
  - source: budgetRequest.approver
    target: approverEmail
```

### Execution Flow:

1. **User provides context** (JSON above)
2. **Parent process** has `budgetRequest.title = "Q1 2024 Marketing Budget"`
3. **Input mapping** extracts `budgetRequest.title`
4. **Subprocess receives** `requestTitle = "Q1 2024 Marketing Budget"`
5. **Email template uses** `${requestTitle}` and `${approverEmail}`
6. **Email sent to** `manager@example.com` with title in subject

---

## Minimal Context for `call-activity-with-mappings-demo.yaml`

### Option A: Let Script Tasks Create Data (Minimal)

```json
{}
```

Yes, **empty object works!** The script tasks will create all the data.

### Option B: Override Script Task Data

```json
{
  "budgetRequest": {
    "title": "Custom Budget Request",
    "details": "My custom budget details",
    "requester": {
      "name": "Your Name",
      "email": "your.email@example.com"
    },
    "priority": "high",
    "approver": "your.manager@example.com"
  }
}
```

This will **override** what the script task creates.

---

## Testing Different Email Recipients

### Test 1: Send to Gmail

```json
{
  "budgetRequest": {
    "title": "Test Approval Request",
    "details": "This is a test",
    "requester": {
      "name": "Test User"
    },
    "priority": "medium",
    "approver": "youremail@gmail.com"
  }
}
```

### Test 2: Send to Multiple People (Separate Workflows)

**First Execution:**
```json
{
  "budgetRequest": {
    "approver": "manager1@example.com"
  }
}
```

**Second Execution:**
```json
{
  "budgetRequest": {
    "approver": "manager2@example.com"
  }
}
```

Same subprocess, different email recipients!

---

## Context for Simple Approval Workflow

### Workflow: `call-activity-approval-demo.yaml`

**Minimal Context:**

```json
{
  "processData": {
    "task": "Initial Processing",
    "data": "Important data",
    "requiresApproval": true
  },
  "taskName": "Budget Approval",
  "taskDetails": "Please approve the Q1 budget request",
  "approverEmail": "manager@example.com"
}
```

---

## Best Practice: Use Script Tasks to Build Context

Instead of providing complex nested objects in the execution context, use **Script Tasks** to prepare the data:

```python
# Script Task: Prepare Request
result = {
    'title': 'Q1 Budget',
    'details': 'Marketing campaign budget',
    'requester': {
        'name': context.get('userName', 'Unknown'),
        'email': context.get('userEmail', 'user@example.com')
    },
    'approver': context.get('managerEmail', 'manager@example.com'),
    'priority': 'high'
}
```

**Then provide simple context:**

```json
{
  "userName": "Alice Johnson",
  "userEmail": "alice@example.com",
  "managerEmail": "manager@example.com"
}
```

---

## Summary

### For `call-activity-with-mappings-demo.yaml`:

**Simplest (empty context):**
```json
{}
```

**Override emails:**
```json
{
  "budgetRequest": {
    "approver": "your.email@gmail.com"
  },
  "hrRequest": {
    "approver": "another.email@gmail.com"
  }
}
```

**Full custom data:**
```json
{
  "budgetRequest": {
    "title": "My Custom Request",
    "details": "Custom details here",
    "requester": {
      "name": "Your Name",
      "email": "you@example.com"
    },
    "priority": "high",
    "approver": "recipient@example.com"
  }
}
```

The **key insight**: Variable mappings let the subprocess work with **any data structure** - you just map the right fields!
