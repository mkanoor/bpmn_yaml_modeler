# Subprocess Variable Mappings - Customizing Data for Reusable Subprocesses

## Overview

Variable mappings allow you to **customize the data** fed into a reusable subprocess, making it truly flexible and reusable across different contexts.

## How It Works

When calling a subprocess via **Call Activity**, you can:

1. **Input Mappings**: Map variables from the parent process **into** the subprocess
2. **Output Mappings**: Map variables from the subprocess **back** to the parent process
3. **Inherit All Variables**: Optionally pass all parent variables automatically

## Variable Mapping Strategies

### Strategy 1: Inherit All Variables (Simple)

**When to use**: When subprocess needs access to everything

```yaml
- id: call_approval
  type: callActivity
  name: Approval
  properties:
    calledElement: email_approval_subprocess
    inheritVariables: true  # ← Pass everything
```

**Pros:**
- ✅ Simple - no configuration needed
- ✅ Subprocess sees all parent variables

**Cons:**
- ❌ Tight coupling - subprocess depends on parent variable names
- ❌ Name collisions possible
- ❌ Less reusable across different processes

---

### Strategy 2: Explicit Input/Output Mappings (Recommended)

**When to use**: For truly reusable subprocesses

```yaml
- id: call_budget_approval
  type: callActivity
  name: Budget Approval
  properties:
    calledElement: email_approval_subprocess
    inheritVariables: false  # ← Don't inherit, use explicit mappings
    inputMappings:
      - source: budgetRequest.title
        target: requestTitle
      - source: budgetRequest.details
        target: requestDetails
      - source: budgetRequest.approver
        target: approverEmail
    outputMappings:
      - source: approvalResult
        target: budgetApprovalResult
```

**Pros:**
- ✅ **Loose coupling** - parent and subprocess have independent variable names
- ✅ **Highly reusable** - same subprocess works with different data structures
- ✅ **Clear contract** - explicitly shows what data flows in/out
- ✅ **No name collisions** - each call can map to different parent variables

**Cons:**
- ❌ Requires configuration for each call activity

---

## Practical Example: Same Subprocess, Different Data

### Subprocess Definition

**File**: Subprocess definition (reusable template)

```yaml
subProcessDefinitions:
  - id: email_approval_subprocess
    name: Email Approval Subprocess
    elements:
      - id: sp_send
        type: sendTask
        name: Send Approval Email
        properties:
          to: "${approverEmail}"           # ← Subprocess expects this variable
          subject: "Approval: ${requestTitle}"  # ← And this
          messageBody: |
            Title: ${requestTitle}
            Details: ${requestDetails}
            Requester: ${requesterName}
            Priority: ${requestPriority}
```

**Key Point**: The subprocess uses **generic variable names** (`requestTitle`, `requestDetails`, etc.) that work for any type of request.

---

### Use Case 1: Budget Approval

**Parent Process Variables:**
```javascript
budgetRequest = {
    title: 'Q1 2024 Marketing Budget',
    details: 'Requesting $50,000 for campaigns',
    requester: { name: 'Alice', email: 'alice@example.com' },
    approver: 'manager@example.com',
    priority: 'high'
}
```

**Call Activity Configuration:**
```yaml
- id: budget_approval
  type: callActivity
  name: Budget Approval
  properties:
    calledElement: email_approval_subprocess
    inheritVariables: false
    inputMappings:
      - source: budgetRequest.title        # Map budget title...
        target: requestTitle                # ...to generic name
      - source: budgetRequest.details
        target: requestDetails
      - source: budgetRequest.requester.name
        target: requesterName
      - source: budgetRequest.priority
        target: requestPriority
      - source: budgetRequest.approver
        target: approverEmail
    outputMappings:
      - source: approvalResult              # Subprocess output...
        target: budgetApprovalResult        # ...to specific parent variable
```

**Result**: Subprocess receives:
```javascript
{
    requestTitle: 'Q1 2024 Marketing Budget',
    requestDetails: 'Requesting $50,000 for campaigns',
    requesterName: 'Alice',
    requestPriority: 'high',
    approverEmail: 'manager@example.com'
}
```

---

### Use Case 2: HR Approval (SAME subprocess, DIFFERENT data)

**Parent Process Variables:**
```javascript
hrRequest = {
    title: 'New Hire - Senior Developer',
    details: 'Approval to hire full-stack developer',
    requester: { name: 'Bob', email: 'bob@example.com' },
    approver: 'hr-director@example.com',
    priority: 'medium',
    salary: 120000
}
```

**Call Activity Configuration:**
```yaml
- id: hr_approval
  type: callActivity
  name: HR Approval
  properties:
    calledElement: email_approval_subprocess  # ← SAME subprocess!
    inheritVariables: false
    inputMappings:
      - source: hrRequest.title            # Different source...
        target: requestTitle               # ...same target
      - source: hrRequest.details
        target: requestDetails
      - source: hrRequest.requester.name
        target: requesterName
      - source: hrRequest.priority
        target: requestPriority
      - source: hrRequest.approver
        target: approverEmail
    outputMappings:
      - source: approvalResult
        target: hrApprovalResult           # Different output variable
```

**Result**: Subprocess receives:
```javascript
{
    requestTitle: 'New Hire - Senior Developer',
    requestDetails: 'Approval to hire full-stack developer',
    requesterName: 'Bob',
    requestPriority: 'medium',
    approverEmail: 'hr-director@example.com'
}
```

---

## Key Benefits Demonstrated

✅ **One Subprocess, Many Contexts**
- `email_approval_subprocess` works for budget requests, HR requests, purchase orders, etc.
- Just map different parent variables to the same subprocess variables

✅ **No Variable Name Conflicts**
- Budget approval result → `budgetApprovalResult`
- HR approval result → `hrApprovalResult`
- Both can exist in parent process simultaneously

✅ **Flexible Data Structures**
- Parent can have nested objects (`budgetRequest.requester.name`)
- Subprocess only sees flat variables (`requesterName`)
- Clean separation of concerns

---

## Mapping Syntax

### Dot Notation for Nested Objects

**Source (Parent Process):**
```javascript
budgetRequest = {
    requester: {
        name: 'Alice',
        department: 'Marketing'
    }
}
```

**Mapping:**
```yaml
inputMappings:
  - source: budgetRequest.requester.name
    target: requesterName
  - source: budgetRequest.requester.department
    target: requesterDepartment
```

**Target (Subprocess):**
```javascript
{
    requesterName: 'Alice',
    requesterDepartment: 'Marketing'
}
```

---

## UI Usage

### In the BPMN Modeler:

1. **Add Call Activity** to canvas
2. **Select it** and open Properties panel
3. **Select Subprocess Definition** from dropdown
4. **Uncheck "Inherit All Variables"** (for explicit mappings)
5. **Click "+ Add Mapping"** under Input Mappings
6. **Enter:**
   - Source: `budgetRequest.title`
   - Target: `requestTitle`
7. **Repeat** for each variable
8. **Add Output Mappings** to get results back

### Visual Example:

```
Input Mappings:
┌──────────────────────────────────────────────┐
│ budgetRequest.title  →  requestTitle     [✕] │
│ budgetRequest.details → requestDetails   [✕] │
│ budgetRequest.approver → approverEmail   [✕] │
│                                              │
│         [+ Add Mapping]                      │
└──────────────────────────────────────────────┘

Output Mappings:
┌──────────────────────────────────────────────┐
│ approvalResult  →  budgetApprovalResult  [✕] │
│                                              │
│         [+ Add Mapping]                      │
└──────────────────────────────────────────────┘
```

---

## Best Practices

### 1. Use Generic Names in Subprocess Definitions

**Good:**
```yaml
# Subprocess uses generic names
requestTitle
requestDetails
requesterName
approverEmail
```

**Bad:**
```yaml
# Subprocess hardcoded to specific use case
budgetTitle
hrRequestDetails
purchaseOrderRequester
```

### 2. Use Specific Names in Parent Process

**Good:**
```yaml
# Parent process has context-specific names
budgetRequest
hrRequest
purchaseOrderRequest
```

### 3. Document Expected Variables

Add documentation to subprocess definition:

```yaml
subProcessDefinitions:
  - id: email_approval_subprocess
    name: Email Approval Subprocess
    documentation: |
      Expected Input Variables:
        - requestTitle: string
        - requestDetails: string
        - requesterName: string
        - requestPriority: 'high' | 'medium' | 'low'
        - approverEmail: string

      Output Variables:
        - approvalResult: {
            approved: boolean,
            decision: string,
            approvedBy: string,
            approvalTimestamp: string,
            comments: string
          }
```

---

## Demo Files

1. **Simple reuse**: `/workflows/call-activity-approval-demo.yaml`
   - Shows subprocess used twice
   - Uses `inheritVariables: true` (simpler but less flexible)

2. **Variable mappings**: `/workflows/call-activity-with-mappings-demo.yaml`
   - Shows explicit input/output mappings
   - Budget approval + HR approval with different data
   - Demonstrates true reusability

---

## Testing

1. **Refresh browser**
2. **Import** `call-activity-with-mappings-demo.yaml`
3. **Click** subprocess definition in left panel to edit it
4. **Select** Budget Approval call activity
5. **View** Input/Output Mappings in properties
6. **Notice** how budget and HR approvals map different variables to same subprocess

---

## Summary

**Variable mappings transform subprocesses from static templates into truly reusable components.**

- **Without mappings**: Subprocess tightly coupled to parent variable names
- **With mappings**: Subprocess is a generic template that works with any data

This is the **BPMN standard pattern** for building reusable, maintainable workflows.
