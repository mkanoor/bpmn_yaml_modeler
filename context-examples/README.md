# Workflow Execution Context Examples

This directory contains example context JSON files for executing workflows.

## 🔒 Privacy Notice

**The `.json` files in this directory are gitignored** to prevent accidentally committing personal email addresses. Only `.json.template` files are tracked in git.

## Quick Start

**First time setup:**
1. Copy a `.json.template` file to `.json` (e.g., `simple-test.json.template` → `simple-test.json`)
2. Edit the `.json` file with your actual email addresses
3. The `.json` file will NOT be committed to git (it's in `.gitignore`)

When executing a workflow, you can provide a context JSON object with variables that will be available to all tasks in the workflow.

## Context Files

### `simple-test.json`
Minimal context for testing workflows with email approvals.

```json
{
  "budgetApprover": "your.email@gmail.com",
  "hrApprover": "your.email@gmail.com"
}
```

**Use with:**
- `call-activity-with-mappings-demo.yaml`
- `call-activity-conditional-approval.yaml`

### `minimal-test.json`
Empty context - workflow script tasks will create all necessary data with default values.

```json
{}
```

**Use with:** Any workflow that doesn't require input variables

### `conditional-approval-context.json`
Context for the conditional approval workflow with custom email addresses.

```json
{
  "budgetApprover": "your.manager@gmail.com",
  "hrApprover": "hr.director@gmail.com"
}
```

**Use with:** `call-activity-conditional-approval.yaml`

## How Variables Work

### Context Variables in Script Tasks

Script tasks can read from the context:

```python
# Get variable from context with default fallback
budget_approver = context.get('budgetApprover', 'manager@example.com')
```

### Context Variables in Send Tasks

Send tasks use variable substitution with `${variable}` syntax:

```yaml
to: "${approverEmail}"
subject: "Approval Required: ${requestTitle}"
```

### Variable Mappings in Call Activities

Call activities use input/output mappings to pass data:

```yaml
inputMappings:
  - source: budgetRequest.approver    # From parent context
    target: approverEmail              # To subprocess context

outputMappings:
  - source: approvalResult             # From subprocess context
    target: budgetApprovalResult       # To parent context
```

## Common Variables

### Email Addresses

- `budgetApprover` - Email address for budget approval
- `hrApprover` - Email address for HR approval

### Requester Information

- `requesterName` - Name of the person requesting approval
- `requesterEmail` - Email of the requester
- `requesterDepartment` - Department of the requester

### Request Details

- `requestTitle` - Title of the request
- `requestDetails` - Detailed description
- `priority` - Priority level (high, medium, low)

## Example: Custom Context

```json
{
  "budgetApprover": "alice.manager@company.com",
  "hrApprover": "bob.hr@company.com",
  "requesterName": "Charlie Developer",
  "requesterEmail": "charlie@company.com",
  "requestTitle": "New Project Budget",
  "requestDetails": "Requesting $100,000 for Q2 project"
}
```

## Best Practices

1. **Use meaningful variable names** - `budgetApprover` is better than `approver1`
2. **Provide fallback defaults** - Always use `context.get('var', 'default')`
3. **Document required variables** - List what variables your workflow needs
4. **Test with minimal context** - Make sure defaults work
5. **Use real email addresses for testing** - Especially for Gmail-enabled workflows

## Troubleshooting

### Emails not being sent
- Check that email addresses in context are valid
- Verify Gmail is configured (see main README)
- Check that `useGmail: true` is set in sendTask

### Variables not found
- Check variable names match exactly (case-sensitive)
- Verify the variable is in the execution context
- Use browser console to inspect context being sent

### Subprocess not receiving data
- Verify input mappings are correct
- Check that source variables exist in parent context
- Use dot notation for nested fields: `budgetRequest.approver`
