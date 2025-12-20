# BPMN Workflows

This directory contains example BPMN workflow definitions in YAML format.

## Workflow Files

### Basic Examples

**`task-types-example.yaml`**
- Demonstrates all available task types
- Shows different BPMN elements (User Task, Service Task, Script Task, etc.)
- Good starting point for learning BPMN modeling

**`add-numbers-conditional-workflow.yaml`**
- Simple workflow with conditional logic
- Uses exclusive gateways for decision-making
- Shows how to add and compare numbers

### Approval Workflows

**`approval-workflow.yaml`**
- Basic approval process example
- User task with approve/reject decision
- Email notifications

**`reusable-approval-workflow.yaml`**
- Reusable approval subprocess
- Can be called from other workflows
- Demonstrates call activities

**`email-approval-test-workflow.yaml`**
- Email-based approval workflow
- Tests Gmail integration
- Approval links in email

### AI/Agentic Workflows

**`agentic-workflow-example.yaml`**
- Demonstrates Agentic Tasks with AI/LLM
- Shows MCP tool integration
- AI-powered decision making

**`ai-log-analysis-workflow.yaml`**
- AI-powered log file analysis
- Uses Claude with MCP filesystem tools
- Error detection and classification
- Single manual approval path

**`ai-log-analysis-dual-approval-workflow.yaml`** ⭐ NEW
- AI-powered log analysis with dual approval paths
- Parallel approval: Email OR Manual approval
- First approval to complete (either path) wins
- Uses parallel and inclusive gateways
- Demonstrates advanced BPMN patterns
- Email approval with webhook integration
- Manual UI-based approval option

**`log-analysis-ansible-workflow.yaml`**
- Advanced log analysis with Red Hat integration
- Uses Red Hat Security Data API MCP server
- CVE lookup and RHSA advisory retrieval
- Ansible playbook generation

### Advanced Examples

**`expanded-subprocess-example.yaml`**
- Shows subprocess with nested elements
- Demonstrates expanded subprocess rendering
- Complex workflow structure

## How to Use

### Loading a Workflow

1. **Via UI:**
   - Click "Import YAML" button in the header
   - Select a workflow file from this directory
   - Workflow will be loaded and displayed on canvas

2. **Via Browser:**
   - Open `index.html` in your browser
   - Use the file picker to select a `.yaml` file
   - Canvas will render the BPMN diagram

### Creating New Workflows

1. Use the BPMN Modeler UI to design your workflow
2. Click "Export YAML" to save your workflow
3. Save the exported YAML file to this directory
4. Add documentation to this README

## Workflow Execution

To execute workflows, you need:

1. **Backend Server** (`backend/workflow-executor.py`)
   - Python 3.8+
   - Required packages: `pyyaml`, `anthropic`, `mcp`

2. **AG-UI Client** (for AI tasks)
   - Claude API key in environment
   - MCP servers configured (if using tools)

3. **Gmail Integration** (for email tasks)
   - Gmail API credentials (`credentials.json`)
   - OAuth token (`token.json`)

## Task Types

Available task types in workflows:

- **User Task** - Manual user interaction
- **Service Task** - External service calls
- **Script Task** - Execute scripts/code
- **Send Task** - Send messages/emails
- **Receive Task** - Wait for messages
- **Manual Task** - Manual human work
- **Business Rule Task** - Business rule evaluation
- **Agentic Task** - AI/LLM-powered tasks with MCP tools

## File Naming Convention

Use descriptive names with hyphens:
- `{purpose}-workflow.yaml` - Single purpose workflows
- `{domain}-{purpose}-workflow.yaml` - Domain-specific workflows
- `{type}-example.yaml` - Example/tutorial workflows

## Contributing

When adding new workflows:

1. Use clear, descriptive names
2. Add workflow to appropriate section in this README
3. Include a brief description
4. Document any special requirements
5. Test the workflow before committing

## Examples by Use Case

**Learning BPMN:**
- `task-types-example.yaml`
- `add-numbers-conditional-workflow.yaml`

**Approval Processes:**
- `approval-workflow.yaml`
- `email-approval-test-workflow.yaml`

**AI Integration:**
- `agentic-workflow-example.yaml`
- `ai-log-analysis-workflow.yaml`
- `ai-log-analysis-dual-approval-workflow.yaml` (advanced)

**DevOps/SRE:**
- `log-analysis-ansible-workflow.yaml`

**Complex Processes:**
- `expanded-subprocess-example.yaml`
- `reusable-approval-workflow.yaml`
- `ai-log-analysis-dual-approval-workflow.yaml`

## Advanced Patterns

### Dual Approval Path Pattern

The `ai-log-analysis-dual-approval-workflow.yaml` demonstrates an advanced BPMN pattern where approval can be obtained through **two parallel paths**:

**Pattern Overview:**
```
Parallel Gateway (Split)
    ├─→ Email Approval Path
    │   └─→ Send Email → Wait for Webhook Response
    │
    └─→ Manual Approval Path
        └─→ User Task (UI Form)

Both paths merge at Inclusive Gateway
    → First approval to complete wins
    → Workflow continues with approved decision
```

**Key Features:**
1. **Parallel Gateway** - Splits flow into two simultaneous approval paths
2. **Email Approval** - Send Task with approval links + Receive Task waiting for webhook
3. **Manual Approval** - Traditional User Task with form
4. **Inclusive Gateway** - Merges paths; first to complete determines outcome
5. **Either/Or Logic** - User can approve via email OR UI, whichever is faster

**Use Cases:**
- Give users flexibility in how they approve
- Faster approvals (user picks most convenient method)
- Redundancy (if one path fails, other can succeed)
- Mobile-friendly (email approval works on any device)

**BPMN Elements Used:**
- `parallelGateway` - Fork approval into two paths
- `inclusiveGateway` - Merge paths (first wins)
- `sendTask` - Email with approval links
- `receiveTask` - Wait for webhook callback
- `userTask` - Traditional form-based approval
