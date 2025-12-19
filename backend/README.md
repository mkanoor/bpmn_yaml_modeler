# BPMN Workflow Execution Backend

Complete backend execution engine for BPMN workflows defined in YAML, with real-time UI updates via AG-UI protocol.

## Features

- ✅ **YAML-Based Workflows** - Load and execute BPMN workflows from YAML files
- ✅ **Task Executors** - Support for all BPMN task types (User, Service, Script, Send, Receive, Agentic, etc.)
- ✅ **Agentic Tasks** - AI agents with MCP tool integration
- ✅ **Real-Time Updates** - WebSocket-based AG-UI protocol for live workflow visualization
- ✅ **Gateway Evaluation** - Exclusive, Parallel, and Inclusive gateways with condition evaluation
- ✅ **Human Approval** - User tasks block until human completes approval forms
- ✅ **Error Handling** - Retry logic, error paths, and escalation
- ✅ **RESTful API** - FastAPI-based REST endpoints for workflow management

## Architecture

```
┌─────────────────────────────────────────┐
│         Frontend (BPMN Modeler)         │
│     WebSocket (AG-UI Client)            │
└────────────┬────────────────────────────┘
             │ ws://localhost:8000/ws
             ▼
┌─────────────────────────────────────────┐
│       AG-UI Server (WebSocket)          │
│    - Broadcasts execution updates       │
│    - Receives user task completions     │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│      Workflow Execution Engine          │
│  - Parses YAML workflows                │
│  - Executes tasks via executors         │
│  - Evaluates gateways                   │
│  - Manages workflow state               │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│         Task Executors                  │
│  - UserTaskExecutor                     │
│  - ServiceTaskExecutor                  │
│  - AgenticTaskExecutor (with MCP)       │
│  - ScriptTaskExecutor                   │
│  - SendTaskExecutor                     │
│  - etc.                                 │
└─────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.9 or higher
- pip

### Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Quick Start

### 1. Start the Backend Server

```bash
cd backend
python main.py
```

Server will start on `http://localhost:8000`

### 2. Open the Frontend

Open `index.html` in your browser. The AG-UI client will automatically connect to `ws://localhost:8000/ws`.

### 3. Execute a Workflow

**Option A: From UI**
1. Create or import a BPMN workflow in the modeler
2. Click "Execute Workflow" button
3. Enter context variables (JSON)
4. Watch real-time execution updates

**Option B: Via API**
```bash
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "yaml": "process:\n  id: test\n  ...",
    "context": {
      "variable1": "value1"
    }
  }'
```

**Option C: Test Endpoint**
```bash
curl -X POST http://localhost:8000/test/execute-log-analysis
```

This executes the pre-configured AI log analysis workflow.

## API Endpoints

### Health Check

```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "connected_clients": 2
}
```

### Execute Workflow

```bash
POST /workflows/execute
Content-Type: application/json

{
  "yaml": "...",  // YAML workflow definition
  "context": {}   // Initial context variables
}
```

Response:
```json
{
  "status": "started",
  "instance_id": "uuid",
  "message": "Workflow execution started"
}
```

### Execute from File

```bash
POST /workflows/execute-file
Content-Type: multipart/form-data

file: workflow.yaml
context: {"key": "value"}
```

### Get Workflow Status

```bash
GET /workflows/{instance_id}/status
```

Response:
```json
{
  "instance_id": "uuid",
  "status": "running",
  "workflow_name": "AI Log Analysis",
  "start_time": "2025-01-15T10:30:00",
  "context_keys": ["logFileUrl", "requester"]
}
```

### List Active Workflows

```bash
GET /workflows/active
```

Response:
```json
{
  "count": 2,
  "workflows": [
    {
      "instance_id": "uuid1",
      "workflow_name": "Log Analysis",
      "start_time": "2025-01-15T10:30:00"
    }
  ]
}
```

### Cancel Workflow

```bash
POST /workflows/{instance_id}/cancel
```

## AG-UI Protocol

### WebSocket Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
```

### Message Types

#### Workflow Events

```javascript
// Workflow started
{
  "type": "workflow.started",
  "instanceId": "uuid",
  "workflowName": "AI Log Analysis",
  "timestamp": "2025-01-15T10:30:00"
}

// Workflow completed
{
  "type": "workflow.completed",
  "instanceId": "uuid",
  "outcome": "success",  // or "failed"
  "duration": 125.5,
  "timestamp": "2025-01-15T10:32:05"
}
```

#### Element Events

```javascript
// Element activated
{
  "type": "element.activated",
  "elementId": "element_1",
  "elementType": "agenticTask",
  "elementName": "Analyze Logs",
  "timestamp": "2025-01-15T10:30:01"
}

// Element completed
{
  "type": "element.completed",
  "elementId": "element_1",
  "duration": 45.2,
  "timestamp": "2025-01-15T10:30:46"
}
```

#### Task Progress

```javascript
{
  "type": "task.progress",
  "elementId": "element_1",
  "progress": 0.5,  // 0.0 to 1.0
  "status": "executing",
  "message": "Agent analyzing (attempt 1/3)",
  "timestamp": "2025-01-15T10:30:20"
}
```

#### Agent Tool Use

```javascript
{
  "type": "agent.tool_use",
  "elementId": "element_4",
  "tool": "filesystem-read",
  "arguments": {
    "path": "s3://logs/nginx.log"
  },
  "timestamp": "2025-01-15T10:30:10"
}
```

#### User Task

```javascript
// User task created (shows approval form)
{
  "type": "userTask.created",
  "elementId": "element_7",
  "taskInstance": {
    "taskId": "element_7",
    "taskName": "Review & Approve Diagnostics",
    "assignee": "user@example.com",
    "priority": "High",
    "formFields": ["diagnosticSteps", "severityLevel"],
    "data": {
      "diagnosticSteps": [...]
    }
  },
  "action": "showApprovalForm",
  "timestamp": "2025-01-15T10:31:00"
}

// User completes task (sent from UI)
{
  "type": "userTask.complete",
  "taskId": "element_7",
  "decision": "approved",
  "comments": "Looks good",
  "user": "user@example.com"
}
```

#### Gateway Events

```javascript
// Gateway evaluating
{
  "type": "gateway.evaluating",
  "elementId": "element_6",
  "gatewayType": "exclusive",
  "paths": 2,
  "timestamp": "2025-01-15T10:30:50"
}

// Path taken
{
  "type": "gateway.path_taken",
  "elementId": "element_6",
  "flowId": "conn_6",
  "condition": "approved",
  "timestamp": "2025-01-15T10:30:51"
}
```

#### Error Events

```javascript
{
  "type": "task.error",
  "elementId": "element_10",
  "error": {
    "message": "Validation failed",
    "type": "ValidationError"
  },
  "retryable": true,
  "timestamp": "2025-01-15T10:32:00"
}
```

## Task Executors

### User Task Executor

Handles human interaction tasks:
- Creates approval forms in UI
- Waits for user completion
- Stores decision in context

**Configuration:**
```yaml
type: userTask
properties:
  assignee: "user@example.com"
  candidateGroups: "managers, approvers"
  priority: "High"
  dueDate: "PT2H"
  custom:
    formFields:
      - "data_to_review"
      - "decision"
```

### Service Task Executor

Calls external services:
- HTTP requests
- External worker pattern
- Expression evaluation

**Configuration:**
```yaml
type: serviceTask
properties:
  implementation: "External"
  topic: "payment-processing"
  resultVariable: "paymentResult"
```

### Agentic Task Executor

Executes AI agents with MCP tools:
- Supports multiple AI models
- MCP tool integration
- Confidence thresholds
- Automatic retries

**Configuration:**
```yaml
type: agenticTask
properties:
  agentType: "log-analyzer"
  model: "claude-3-opus"
  confidenceThreshold: 0.8
  maxRetries: 3
  custom:
    mcpTools:
      - "filesystem-read"
      - "grep-search"
    systemPrompt: |
      You are an expert analyzing logs...
```

### Script Task Executor

Executes scripts:
- Python scripts (sandboxed)
- Access to context variables
- Store results

**Configuration:**
```yaml
type: scriptTask
properties:
  scriptFormat: "Python"
  script: |
    result = context.get('value', 0) * 2
  resultVariable: "doubledValue"
```

### Send Task Executor

Sends notifications:
- Email
- SMS
- Webhooks
- Variable substitution

**Configuration:**
```yaml
type: sendTask
properties:
  messageType: "Email"
  to: "${requester.email}"
  subject: "Workflow Complete"
  messageBody: |
    Your workflow ${workflowName} has completed.
```

## Gateway Evaluation

### Exclusive Gateway (XOR)

One path taken based on conditions:

```yaml
connections:
  - from: gateway_1
    to: task_success
    name: "${confidence >= 0.8}"

  - from: gateway_1
    to: task_retry
    name: "${confidence < 0.8}"
```

### Parallel Gateway (AND)

All paths taken simultaneously:

```yaml
# No conditions needed
# All outgoing flows execute in parallel
```

### Inclusive Gateway (OR)

One or more paths based on conditions:

```yaml
connections:
  - from: gateway_2
    to: notify_email
    name: "${notify_email == true}"

  - from: gateway_2
    to: notify_sms
    name: "${notify_sms == true}"
```

## Expression Syntax

Conditions support:
- Variable references: `${variableName}`
- Comparisons: `${value >= 10}`
- Boolean logic: `${approved == true}`
- String matching: `approved`, `yes`, `true`

## Development

### Project Structure

```
backend/
├── main.py                  # FastAPI application
├── models.py                # Pydantic data models
├── workflow_engine.py       # Main execution engine
├── task_executors.py        # Task executor implementations
├── gateway_evaluator.py     # Gateway evaluation logic
├── agui_server.py          # AG-UI WebSocket server
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

### Running Tests

```bash
pytest
```

### Logging

Logs are output to console with INFO level. Configure in `main.py`:

```python
logging.basicConfig(level=logging.DEBUG)  # For verbose logging
```

## Deployment

### Docker

```dockerfile
FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t bpmn-engine .
docker run -p 8000:8000 bpmn-engine
```

### Production

For production deployment:

1. **Use production ASGI server:**
```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

2. **Add database for state persistence**

3. **Configure CORS properly** (in `main.py`, replace `allow_origins=["*"]`)

4. **Add authentication** for API endpoints

5. **Set up reverse proxy** (nginx)

## Troubleshooting

### WebSocket Connection Failed

Check:
1. Backend server is running: `curl http://localhost:8000/health`
2. No firewall blocking port 8000
3. CORS configuration allows your frontend origin

### Workflow Execution Hangs

Check:
1. User tasks require manual completion
2. Gateway conditions evaluate correctly
3. No infinite loops in subprocess

### Agent Tasks Fail

Check:
1. MCP server is running
2. AI model API keys configured
3. Confidence threshold not too high

## Examples

See the parent directory for example workflows:
- `ai-log-analysis-workflow.yaml` - Complete AI-powered DevOps workflow
- `approval-workflow.yaml` - Multi-stage approval process
- `task-types-example.yaml` - Demonstrates all task types

## License

MIT License

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-repo/issues
- Documentation: See parent directory guides
