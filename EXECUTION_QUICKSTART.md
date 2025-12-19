# BPMN Workflow Execution - Quick Start Guide

Get your BPMN workflows executing with real-time UI feedback in 5 minutes!

## Prerequisites

- Python 3.9+
- Modern web browser
- Terminal

## Step 1: Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This installs:
- FastAPI (web framework)
- Uvicorn (ASGI server)
- WebSockets (real-time communication)
- PyYAML (workflow parsing)
- Other dependencies

## Step 2: Start the Backend Server

```bash
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Keep this terminal window open!**

## Step 3: Open the Frontend

Open `index.html` in your browser:

```bash
# On macOS
open index.html

# On Linux
xdg-open index.html

# On Windows
start index.html
```

You should see:
- BPMN Modeler interface
- Green "● Connected" indicator in the header (AG-UI connection)

## Step 4: Execute a Test Workflow

### Option A: Use the Pre-Built AI Log Analysis Workflow

1. In the modeler, click **"Import YAML"**
2. Select `ai-log-analysis-workflow.yaml`
3. Click **"▶ Execute Workflow"**
4. Enter context (or use default):
```json
{
  "logFileUrl": "s3://devops-logs/nginx-error.log",
  "logFileName": "nginx-error.log",
  "requester": {
    "email": "admin@example.com",
    "name": "Test User"
  }
}
```
5. Click OK

### Option B: Execute via API

```bash
curl -X POST http://localhost:8000/test/execute-log-analysis
```

## Step 5: Watch Real-Time Execution

You'll see:

1. **Workflow Started** notification
2. **Elements light up** as they execute (blue glow with pulse animation)
3. **Progress bars** appear under tasks showing execution status
4. **Tool usage notifications** pop up when AI agents use MCP tools
5. **Checkmarks appear** ✓ when elements complete
6. **Approval form appears** when user task is reached
7. **Gateway paths highlight** in green when taken
8. **Completion notification** when workflow finishes

## Real-Time Updates Explained

### Visual Indicators

| Indicator | Meaning |
|-----------|---------|
| Blue glow + pulse | Element is currently executing |
| Green checkmark ✓ | Element completed successfully |
| Red warning ⚠ | Element encountered error |
| Progress bar | Task execution progress (0-100%) |
| Green path highlight | Gateway path taken |

### Notifications (Top Right)

- **Workflow Started** - Execution began
- **Tool Use** - AI agent used an MCP tool (e.g., filesystem-read)
- **Task Progress** - Status updates from tasks
- **Workflow Completed** - Execution finished

### Approval Forms

When a User Task is reached:
1. Modal dialog appears
2. Shows task data for review
3. Two buttons: **Approve** or **Reject**
4. Add comments (optional)
5. Submit decision
6. Workflow continues based on decision

## Example Execution Timeline

Here's what happens with the AI log analysis workflow:

```
Time | Element                  | Visual Update
-----|--------------------------|----------------------------------
0:00 | Start Event              | Blue glow
0:01 | Receive Log File         | Progress: "Receiving log..."
0:05 | Receive Log File         | ✓ Checkmark appears
0:05 | Store in S3              | Progress: "Storing in S3..."
0:07 | Store in S3              | ✓ Checkmark
0:07 | Analyze Logs (AI)        | Progress: "Initializing agent..."
     |                          | 🔧 Tool notification: filesystem-read
     |                          | 🔧 Tool notification: grep-search
0:45 | Analyze Logs (AI)        | ✓ Checkmark
0:45 | Generate Diagnostics     | Progress: "Executing..."
1:05 | Generate Diagnostics     | ✓ Checkmark
1:05 | Valid Results?           | Gateway evaluating...
     |                          | Green path: "yes"
1:06 | Review & Approve         | 📋 APPROVAL FORM APPEARS
     |                          | (Waiting for human)
     |                          | User clicks "Approve"
1:35 | Review & Approve         | ✓ Form closes, checkmark
1:35 | Approved?                | Green path: "approved"
1:36 | Generate Playbook        | Progress: "Generating..."
2:10 | Generate Playbook        | ✓ Checkmark
2:10 | Validate Syntax          | Progress: "Validating..."
2:15 | Validate Syntax          | ✓ Checkmark
2:15 | Valid Playbook?          | Green path: "valid"
2:16 | Store Playbook           | Progress: "Storing..."
2:20 | Store Playbook           | ✓ Checkmark
2:20 | Execute on Systems       | Progress: "Executing..."
2:45 | Execute on Systems       | ✓ Checkmark
2:45 | Send Notification        | Progress: "Sending email..."
2:47 | Send Notification        | ✓ Checkmark
2:47 | End Event                | ✅ "Workflow success" notification
```

## API Endpoints Reference

### Execute Workflow

```bash
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "yaml": "...",
    "context": {"key": "value"}
  }'
```

### Check Health

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "connected_clients": 1
}
```

### List Active Workflows

```bash
curl http://localhost:8000/workflows/active
```

### Get Workflow Status

```bash
curl http://localhost:8000/workflows/{instance_id}/status
```

### Cancel Workflow

```bash
curl -X POST http://localhost:8000/workflows/{instance_id}/cancel
```

## Customizing Workflows

### Add Context Variables

When prompted, enter any variables your workflow needs:

```json
{
  "userId": "12345",
  "environment": "production",
  "logLevel": "debug",
  "notifyEmail": "alerts@company.com"
}
```

These are accessible in the workflow as `${userId}`, `${environment}`, etc.

### Use in Gateway Conditions

```yaml
connections:
  - from: gateway_1
    to: prod_task
    name: "${environment == 'production'}"

  - from: gateway_1
    to: dev_task
    name: "${environment == 'development'}"
```

### Use in Task Properties

```yaml
properties:
  to: "${notifyEmail}"
  subject: "Alert for user ${userId}"
```

## Troubleshooting

### "Backend is not running" error

**Solution:**
1. Check terminal running `python main.py`
2. Verify server started on port 8000
3. Check no other process using port 8000

### "Disconnected" status in UI

**Solution:**
1. Refresh the browser page
2. Check WebSocket connection: `ws://localhost:8000/ws`
3. Ensure CORS is configured (already done in code)

### Workflow hangs at User Task

**Expected behavior!**
- User tasks require manual approval
- Click the approve/reject button in the modal
- Check browser console for form errors

### No visual updates

**Solution:**
1. Check browser console for errors
2. Verify AG-UI client connected (green indicator)
3. Check backend logs for WebSocket messages

### Agent tasks fail

**Expected in demo!**
- Agentic tasks are simulated (no real AI calls)
- They simulate tool usage and return mock results
- To integrate real AI:
  - Add API keys to environment
  - Implement MCP client
  - Connect to actual AI service

## Next Steps

### 1. Create Your Own Workflow

1. Use the BPMN modeler to create a workflow
2. Add elements (tasks, gateways, events)
3. Configure properties
4. Click "Execute Workflow"

### 2. Integrate Real AI Services

In `backend/task_executors.py`, update `AgenticTaskExecutor.run_agent()`:

```python
async def run_agent(self, task_id, model, system_prompt, mcp_tools, context):
    # Replace simulation with actual AI calls
    import anthropic
    client = anthropic.Anthropic(api_key="your-key")

    # Use MCP tools
    for tool in mcp_tools:
        # Call actual MCP server
        pass

    # Call AI model
    response = await client.messages.create(
        model=model,
        system=system_prompt,
        messages=[...]
    )

    return response
```

### 3. Add Database Persistence

Currently state is in-memory. For production:

1. Add PostgreSQL
2. Update `workflow_engine.py` to save state
3. Implement recovery on server restart

### 4. Add Authentication

Protect endpoints:

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/workflows/execute")
async def execute_workflow(
    workflow_data: dict,
    token: str = Depends(security)
):
    # Verify token
    pass
```

## Complete Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Browser                           │
│                                                      │
│  ┌─────────────────┐      ┌──────────────────┐     │
│  │  BPMN Modeler   │      │  AG-UI Client    │     │
│  │  (index.html)   │      │  (agui-client.js)│     │
│  └────────┬────────┘      └────────┬─────────┘     │
└───────────┼──────────────────────────┼──────────────┘
            │ HTTP                     │ WebSocket
            │ POST /workflows/execute  │ ws://localhost:8000/ws
            ▼                          ▼
┌──────────────────────────────────────────────────────┐
│              FastAPI Backend (main.py)               │
│                                                      │
│  ┌─────────────────┐      ┌──────────────────┐     │
│  │  REST API       │      │  AG-UI Server    │     │
│  │  Endpoints      │      │  (WebSocket)     │     │
│  └────────┬────────┘      └────────┬─────────┘     │
│           │                        │               │
│           ▼                        │               │
│  ┌────────────────────────────────┼─────────┐     │
│  │     Workflow Engine             │         │     │
│  │  - Parse YAML                   │         │     │
│  │  - Execute elements ◄───────────┘         │     │
│  │  - Emit AG-UI updates                     │     │
│  └────────┬──────────────────────────────────┘     │
│           │                                         │
│           ▼                                         │
│  ┌──────────────────────────────────────────┐      │
│  │        Task Executor Registry            │      │
│  │  - UserTaskExecutor                      │      │
│  │  - ServiceTaskExecutor                   │      │
│  │  - AgenticTaskExecutor                   │      │
│  │  - ScriptTaskExecutor                    │      │
│  └──────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────┘
```

## Resources

- **Full Documentation:** `backend/README.md`
- **Architecture Details:** `BACKEND_EXECUTION_ARCHITECTURE.md`
- **Example Workflows:**
  - `ai-log-analysis-workflow.yaml`
  - `approval-workflow.yaml`
  - `task-types-example.yaml`
- **Guides:**
  - `TASK_TYPES_GUIDE.md`
  - `CUSTOM_EXTENSIONS_GUIDE.md`
  - `PROPERTIES_CONFIGURATION_GUIDE.md`

## Success!

You now have a complete BPMN execution engine with:
- ✅ Real-time visual feedback
- ✅ Human approval workflows
- ✅ AI agent integration (simulated)
- ✅ Gateway logic
- ✅ WebSocket communication
- ✅ REST API

**Happy workflow executing!** 🚀
