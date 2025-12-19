# BPMN Workflow Execution Backend Architecture

## Overview

This document describes a backend architecture for executing BPMN workflows defined in YAML format, with real-time UI feedback using the AG-UI protocol.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (UI)                         │
│  - BPMN Canvas (index.html)                                 │
│  - AG-UI Client (receives real-time updates)                │
└────────────────┬────────────────────────────────────────────┘
                 │ WebSocket (AG-UI Protocol)
                 │
┌────────────────▼────────────────────────────────────────────┐
│                   AG-UI Server Layer                         │
│  - WebSocket Server                                          │
│  - UI Update Broadcaster                                     │
│  - Event Stream Handler                                      │
└────────────────┬────────────────────────────────────────────┘
                 │ Events
                 │
┌────────────────▼────────────────────────────────────────────┐
│              Workflow Execution Engine                       │
│  ┌──────────────────────────────────────────────────┐       │
│  │  YAML Parser → Process Instance → State Machine  │       │
│  └──────────────────────────────────────────────────┘       │
│                                                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │           Task Executor Registry                  │       │
│  │  - UserTaskExecutor                              │       │
│  │  - ServiceTaskExecutor                           │       │
│  │  - AgenticTaskExecutor (MCP Integration)         │       │
│  │  - ScriptTaskExecutor                            │       │
│  │  - SendTaskExecutor                              │       │
│  └──────────────────────────────────────────────────┘       │
│                                                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │         Gateway Evaluator                         │       │
│  │  - ExclusiveGateway                              │       │
│  │  - ParallelGateway                               │       │
│  │  - InclusiveGateway                              │       │
│  └──────────────────────────────────────────────────┘       │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│                 External Integrations                        │
│  - MCP Server (for Agentic Tasks)                           │
│  - Database (workflow state persistence)                     │
│  - Message Queue (async task execution)                      │
│  - External APIs (service tasks)                             │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Workflow Execution Engine

**Responsibilities:**
- Parse YAML workflow definitions
- Create and manage process instances
- Execute tasks in sequence
- Evaluate gateways and control flow
- Maintain execution state
- Emit events for UI updates

**Key Classes:**

```python
class WorkflowEngine:
    """Main orchestrator for workflow execution"""

    def __init__(self, yaml_content: str, ui_broadcaster):
        self.workflow = self.parse_yaml(yaml_content)
        self.ui_broadcaster = ui_broadcaster
        self.state = WorkflowState()
        self.task_executors = TaskExecutorRegistry()
        self.gateway_evaluator = GatewayEvaluator()

    def parse_yaml(self, yaml_content: str) -> Workflow:
        """Parse YAML into workflow object model"""
        data = yaml.safe_load(yaml_content)
        return Workflow.from_dict(data['process'])

    async def start_execution(self, context: dict = None):
        """Start workflow execution from start event"""
        instance_id = self.create_instance()

        # Broadcast workflow started
        await self.ui_broadcaster.send_update({
            'type': 'workflow.started',
            'instanceId': instance_id,
            'timestamp': datetime.utcnow().isoformat()
        })

        # Find start event
        start_event = self.workflow.get_start_event()
        await self.execute_from_element(start_event, context or {})

    async def execute_from_element(self, element, context: dict):
        """Execute workflow from a given element"""
        # Mark element as active
        await self.ui_broadcaster.send_update({
            'type': 'element.activated',
            'elementId': element.id,
            'elementType': element.type,
            'elementName': element.name
        })

        # Execute based on element type
        if element.is_task():
            await self.execute_task(element, context)
        elif element.is_gateway():
            await self.evaluate_gateway(element, context)
        elif element.is_event():
            await self.handle_event(element, context)

    async def execute_task(self, task, context: dict):
        """Execute a task using appropriate executor"""
        executor = self.task_executors.get_executor(task.type)

        try:
            # Execute with progress updates
            async for progress in executor.execute(task, context):
                await self.ui_broadcaster.send_update({
                    'type': 'task.progress',
                    'elementId': task.id,
                    'progress': progress
                })

            # Mark task as completed
            await self.ui_broadcaster.send_update({
                'type': 'element.completed',
                'elementId': task.id,
                'timestamp': datetime.utcnow().isoformat()
            })

            # Continue to next element(s)
            next_elements = self.workflow.get_outgoing_elements(task)
            for next_elem in next_elements:
                await self.execute_from_element(next_elem, context)

        except Exception as e:
            await self.handle_task_error(task, e, context)
```

### 2. Task Executor Registry

**Pattern**: Strategy Pattern - each task type has its own executor

```python
class TaskExecutorRegistry:
    """Registry of task executors by task type"""

    def __init__(self):
        self.executors = {
            'userTask': UserTaskExecutor(),
            'serviceTask': ServiceTaskExecutor(),
            'scriptTask': ScriptTaskExecutor(),
            'sendTask': SendTaskExecutor(),
            'receiveTask': ReceiveTaskExecutor(),
            'manualTask': ManualTaskExecutor(),
            'businessRuleTask': BusinessRuleTaskExecutor(),
            'agenticTask': AgenticTaskExecutor(),
            'subProcess': SubProcessExecutor(),
            'callActivity': CallActivityExecutor()
        }

    def get_executor(self, task_type: str) -> TaskExecutor:
        """Get executor for task type"""
        executor = self.executors.get(task_type)
        if not executor:
            raise ValueError(f"No executor found for task type: {task_type}")
        return executor
```

### 3. Agentic Task Executor (MCP Integration)

**Critical for AI Log Analysis Workflow**

```python
class AgenticTaskExecutor(TaskExecutor):
    """Executes agentic tasks with MCP tool support"""

    def __init__(self, mcp_client, ui_broadcaster):
        self.mcp_client = mcp_client
        self.ui_broadcaster = ui_broadcaster

    async def execute(self, task, context: dict):
        """Execute agentic task using AI model with MCP tools"""

        # Extract agentic task configuration
        config = task.properties
        agent_type = config.get('agentType')
        model = config.get('model')
        capabilities = config.get('capabilities', '').split(',')
        mcp_tools = config.get('custom', {}).get('mcpTools', [])
        system_prompt = config.get('custom', {}).get('systemPrompt', '')
        confidence_threshold = float(config.get('confidenceThreshold', 0.8))
        max_retries = int(config.get('maxRetries', 3))

        # Broadcast agent initialization
        yield {
            'status': 'initializing',
            'message': f'Initializing {agent_type} agent with {model}',
            'progress': 0.1
        }

        # Initialize AI agent with MCP tools
        agent = await self.create_agent(
            model=model,
            system_prompt=system_prompt,
            tools=await self.get_mcp_tools(mcp_tools),
            capabilities=capabilities
        )

        # Execute agent with retries
        for attempt in range(max_retries):
            try:
                yield {
                    'status': 'executing',
                    'message': f'Agent analyzing (attempt {attempt + 1}/{max_retries})',
                    'progress': 0.3 + (attempt * 0.2)
                }

                # Run agent inference
                result = await agent.run(
                    input_data=context,
                    on_tool_use=lambda tool, args: self.broadcast_tool_use(task.id, tool, args)
                )

                # Check confidence
                confidence = result.get('confidence', 0)
                if confidence >= confidence_threshold:
                    # Store result in context
                    context[f'{task.id}_result'] = result

                    yield {
                        'status': 'completed',
                        'message': f'Analysis complete (confidence: {confidence:.2%})',
                        'progress': 1.0,
                        'result': result
                    }
                    return
                else:
                    yield {
                        'status': 'retry',
                        'message': f'Low confidence ({confidence:.2%}), retrying...',
                        'progress': 0.5
                    }

            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                yield {
                    'status': 'error',
                    'message': f'Attempt failed: {str(e)}',
                    'progress': 0.4
                }

        # Failed after retries
        raise TaskExecutionError(f"Agent failed after {max_retries} attempts")

    async def get_mcp_tools(self, tool_names: list):
        """Get MCP tool implementations"""
        tools = []
        for tool_name in tool_names:
            tool = await self.mcp_client.get_tool(tool_name)
            tools.append(tool)
        return tools

    async def broadcast_tool_use(self, task_id: str, tool_name: str, args: dict):
        """Broadcast when agent uses a tool"""
        await self.ui_broadcaster.send_update({
            'type': 'agent.tool_use',
            'elementId': task_id,
            'tool': tool_name,
            'arguments': args,
            'timestamp': datetime.utcnow().isoformat()
        })
```

### 4. User Task Executor (Human Approval)

```python
class UserTaskExecutor(TaskExecutor):
    """Executes user tasks requiring human interaction"""

    def __init__(self, task_queue, ui_broadcaster):
        self.task_queue = task_queue
        self.ui_broadcaster = ui_broadcaster

    async def execute(self, task, context: dict):
        """Execute user task - wait for human completion"""

        # Extract user task configuration
        assignee = task.properties.get('assignee')
        candidate_groups = task.properties.get('candidateGroups', '').split(',')
        priority = task.properties.get('priority', 'Medium')
        due_date = task.properties.get('dueDate')
        form_fields = task.properties.get('custom', {}).get('formFields', [])

        # Create task instance
        task_instance = {
            'taskId': task.id,
            'taskName': task.name,
            'assignee': assignee,
            'candidateGroups': candidate_groups,
            'priority': priority,
            'dueDate': due_date,
            'formFields': form_fields,
            'data': self.extract_form_data(context, form_fields)
        }

        # Add to task queue
        await self.task_queue.add_task(task_instance)

        # Broadcast user task created
        yield {
            'status': 'waiting',
            'message': f'Waiting for user approval from {assignee or candidate_groups}',
            'progress': 0.5,
            'taskInstance': task_instance
        }

        # Send UI notification to show approval form
        await self.ui_broadcaster.send_update({
            'type': 'userTask.created',
            'elementId': task.id,
            'taskInstance': task_instance,
            'action': 'showApprovalForm'  # UI should display form
        })

        # Wait for completion (blocking)
        completion_data = await self.task_queue.wait_for_completion(task.id)

        # Store completion data in context
        context[f'{task.id}_decision'] = completion_data.get('decision')
        context[f'{task.id}_comments'] = completion_data.get('comments')

        yield {
            'status': 'completed',
            'message': f'User task completed: {completion_data.get("decision")}',
            'progress': 1.0,
            'completionData': completion_data
        }
```

### 5. Service Task Executor

```python
class ServiceTaskExecutor(TaskExecutor):
    """Executes service tasks (external API calls)"""

    def __init__(self, http_client, ui_broadcaster):
        self.http_client = http_client
        self.ui_broadcaster = ui_broadcaster

    async def execute(self, task, context: dict):
        """Execute service task"""

        implementation = task.properties.get('implementation')

        if implementation == 'External':
            # External worker pattern
            topic = task.properties.get('topic')
            yield {
                'status': 'executing',
                'message': f'Publishing to external topic: {topic}',
                'progress': 0.3
            }

            result = await self.execute_external_task(topic, task, context)

        elif implementation == 'Web Service':
            # Direct HTTP call
            endpoint = task.properties.get('custom', {}).get('endpoint')
            method = task.properties.get('custom', {}).get('method', 'POST')

            yield {
                'status': 'executing',
                'message': f'Calling {method} {endpoint}',
                'progress': 0.3
            }

            result = await self.http_client.request(
                method=method,
                url=endpoint,
                json=context
            )

        else:
            raise ValueError(f"Unsupported implementation: {implementation}")

        # Store result
        result_variable = task.properties.get('resultVariable', 'result')
        context[result_variable] = result

        yield {
            'status': 'completed',
            'message': 'Service call completed',
            'progress': 1.0,
            'result': result
        }
```

### 6. Gateway Evaluator

```python
class GatewayEvaluator:
    """Evaluates gateway conditions to determine flow"""

    def __init__(self, workflow, ui_broadcaster):
        self.workflow = workflow
        self.ui_broadcaster = ui_broadcaster

    async def evaluate_exclusive_gateway(self, gateway, context: dict):
        """Evaluate exclusive gateway (XOR) - one path taken"""

        outgoing_flows = self.workflow.get_outgoing_connections(gateway)

        # Broadcast gateway evaluation
        await self.ui_broadcaster.send_update({
            'type': 'gateway.evaluating',
            'elementId': gateway.id,
            'gatewayType': 'exclusive',
            'paths': len(outgoing_flows)
        })

        # Evaluate each flow condition
        for flow in outgoing_flows:
            condition = flow.name or flow.properties.get('condition')

            if not condition or condition == '' or self.evaluate_condition(condition, context):
                # This path is taken
                await self.ui_broadcaster.send_update({
                    'type': 'gateway.path_taken',
                    'elementId': gateway.id,
                    'flowId': flow.id,
                    'condition': condition
                })

                # Return the target element
                return [self.workflow.get_element_by_id(flow.to)]

        # No condition matched - error
        raise GatewayEvaluationError(f"No path matched for exclusive gateway {gateway.id}")

    async def evaluate_parallel_gateway(self, gateway, context: dict):
        """Evaluate parallel gateway (AND) - all paths taken"""

        outgoing_flows = self.workflow.get_outgoing_connections(gateway)

        await self.ui_broadcaster.send_update({
            'type': 'gateway.evaluating',
            'elementId': gateway.id,
            'gatewayType': 'parallel',
            'paths': len(outgoing_flows)
        })

        # Return all target elements (parallel execution)
        target_elements = []
        for flow in outgoing_flows:
            target = self.workflow.get_element_by_id(flow.to)
            target_elements.append(target)

        return target_elements

    def evaluate_condition(self, condition: str, context: dict) -> bool:
        """Evaluate a condition expression against context"""
        # Simple expression evaluator
        # Example conditions:
        #   - "approved" (checks if context['approved'] is truthy)
        #   - "${confidence >= 0.8}" (expression evaluation)
        #   - "yes" (checks if matches flow name)

        # Replace variables
        resolved = self.resolve_variables(condition, context)

        # Evaluate as Python expression (CAREFUL: sanitize in production!)
        try:
            return bool(eval(resolved, {"__builtins__": {}}, context))
        except:
            return resolved.lower() in ['true', 'yes', '1']

    def resolve_variables(self, expression: str, context: dict) -> str:
        """Replace ${variable} with context values"""
        import re
        def replacer(match):
            var_name = match.group(1).strip()
            return str(context.get(var_name, ''))

        return re.sub(r'\$\{([^}]+)\}', replacer, expression)
```

## AG-UI Protocol Integration

### AG-UI Message Format

```typescript
interface AGUIMessage {
    type: string;              // Message type identifier
    elementId?: string;        // BPMN element ID
    timestamp: string;         // ISO timestamp
    data: any;                 // Payload specific to message type
}

// Message types for workflow execution:

// 1. Workflow lifecycle
interface WorkflowStarted extends AGUIMessage {
    type: 'workflow.started';
    instanceId: string;
    workflowName: string;
}

interface WorkflowCompleted extends AGUIMessage {
    type: 'workflow.completed';
    instanceId: string;
    duration: number;
    outcome: 'success' | 'failed' | 'terminated';
}

// 2. Element state changes
interface ElementActivated extends AGUIMessage {
    type: 'element.activated';
    elementId: string;
    elementType: string;
    elementName: string;
}

interface ElementCompleted extends AGUIMessage {
    type: 'element.completed';
    elementId: string;
    duration: number;
    result?: any;
}

// 3. Task progress
interface TaskProgress extends AGUIMessage {
    type: 'task.progress';
    elementId: string;
    progress: number;          // 0.0 to 1.0
    status: string;            // 'initializing', 'executing', 'completed'
    message: string;
}

// 4. Agentic task events
interface AgentToolUse extends AGUIMessage {
    type: 'agent.tool_use';
    elementId: string;
    tool: string;              // MCP tool name
    arguments: any;
    result?: any;
}

// 5. User task events
interface UserTaskCreated extends AGUIMessage {
    type: 'userTask.created';
    elementId: string;
    taskInstance: {
        taskId: string;
        taskName: string;
        assignee: string;
        formFields: string[];
        data: any;
    };
    action: 'showApprovalForm';
}

// 6. Gateway events
interface GatewayEvaluating extends AGUIMessage {
    type: 'gateway.evaluating';
    elementId: string;
    gatewayType: 'exclusive' | 'parallel' | 'inclusive';
    paths: number;
}

interface GatewayPathTaken extends AGUIMessage {
    type: 'gateway.path_taken';
    elementId: string;
    flowId: string;
    condition?: string;
}

// 7. Error events
interface TaskError extends AGUIMessage {
    type: 'task.error';
    elementId: string;
    error: {
        message: string;
        code?: string;
        stack?: string;
    };
    retryable: boolean;
}
```

### AG-UI Server Implementation

```python
import asyncio
import websockets
import json
from typing import Set

class AGUIServer:
    """WebSocket server implementing AG-UI protocol"""

    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()

    async def start(self):
        """Start WebSocket server"""
        async with websockets.serve(self.handle_client, self.host, self.port):
            print(f"AG-UI Server started on ws://{self.host}:{self.port}")
            await asyncio.Future()  # Run forever

    async def handle_client(self, websocket, path):
        """Handle new client connection"""
        self.clients.add(websocket)
        try:
            async for message in websocket:
                # Handle incoming messages from UI
                data = json.loads(message)
                await self.handle_ui_message(data, websocket)
        finally:
            self.clients.remove(websocket)

    async def handle_ui_message(self, message: dict, websocket):
        """Process messages from UI (e.g., user task completion)"""
        msg_type = message.get('type')

        if msg_type == 'userTask.complete':
            # User completed an approval task
            task_id = message.get('taskId')
            decision = message.get('decision')
            comments = message.get('comments')

            # Notify task queue
            await self.complete_user_task(task_id, {
                'decision': decision,
                'comments': comments,
                'completedBy': message.get('user'),
                'timestamp': datetime.utcnow().isoformat()
            })

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if self.clients:
            # Add timestamp if not present
            if 'timestamp' not in message:
                message['timestamp'] = datetime.utcnow().isoformat()

            # Serialize and send
            message_json = json.dumps(message)
            await asyncio.gather(
                *[client.send(message_json) for client in self.clients],
                return_exceptions=True
            )

    async def send_to_client(self, client_id: str, message: dict):
        """Send message to specific client"""
        # Implementation depends on how clients are identified
        pass
```

### Frontend AG-UI Client

```javascript
class AGUIClient {
    constructor(url = 'ws://localhost:8765') {
        this.url = url;
        this.ws = null;
        this.handlers = {};
        this.connect();
    }

    connect() {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log('Connected to AG-UI server');
        };

        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.ws.onclose = () => {
            console.log('Disconnected from AG-UI server');
            // Attempt reconnection
            setTimeout(() => this.connect(), 5000);
        };
    }

    handleMessage(message) {
        const { type } = message;

        // Route to appropriate handler
        switch(type) {
            case 'element.activated':
                this.highlightElement(message.elementId);
                break;

            case 'element.completed':
                this.markElementComplete(message.elementId);
                break;

            case 'task.progress':
                this.updateTaskProgress(message.elementId, message.progress, message.message);
                break;

            case 'agent.tool_use':
                this.showAgentToolUse(message.elementId, message.tool, message.arguments);
                break;

            case 'userTask.created':
                this.showApprovalForm(message.taskInstance);
                break;

            case 'gateway.path_taken':
                this.highlightPath(message.flowId);
                break;

            case 'task.error':
                this.showErrorOnElement(message.elementId, message.error);
                break;
        }

        // Call custom handlers
        if (this.handlers[type]) {
            this.handlers[type].forEach(handler => handler(message));
        }
    }

    highlightElement(elementId) {
        const element = document.querySelector(`[data-id="${elementId}"]`);
        if (element) {
            element.classList.add('active', 'pulsing');
        }
    }

    markElementComplete(elementId) {
        const element = document.querySelector(`[data-id="${elementId}"]`);
        if (element) {
            element.classList.remove('active', 'pulsing');
            element.classList.add('completed');

            // Add checkmark
            const checkmark = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            checkmark.textContent = '✓';
            checkmark.setAttribute('class', 'completion-mark');
            element.appendChild(checkmark);
        }
    }

    updateTaskProgress(elementId, progress, message) {
        // Create or update progress indicator
        let progressBar = document.querySelector(`#progress-${elementId}`);
        if (!progressBar) {
            progressBar = this.createProgressBar(elementId);
        }

        progressBar.style.width = `${progress * 100}%`;
        progressBar.setAttribute('data-message', message);

        // Show tooltip with message
        this.showTooltip(elementId, message);
    }

    showAgentToolUse(elementId, tool, args) {
        // Create tool use indicator
        const indicator = document.createElement('div');
        indicator.className = 'tool-use-indicator';
        indicator.innerHTML = `
            <div class="tool-name">${tool}</div>
            <div class="tool-args">${JSON.stringify(args, null, 2)}</div>
        `;

        // Position near element
        const element = document.querySelector(`[data-id="${elementId}"]`);
        if (element) {
            const rect = element.getBoundingClientRect();
            indicator.style.left = `${rect.right + 10}px`;
            indicator.style.top = `${rect.top}px`;
            document.body.appendChild(indicator);

            // Fade out after 3 seconds
            setTimeout(() => indicator.remove(), 3000);
        }
    }

    showApprovalForm(taskInstance) {
        // Create modal with approval form
        const modal = document.createElement('div');
        modal.className = 'approval-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <h2>${taskInstance.taskName}</h2>
                <div class="form-fields">
                    ${this.renderFormFields(taskInstance.formFields, taskInstance.data)}
                </div>
                <div class="approval-actions">
                    <button class="btn approve" onclick="this.approveTask('${taskInstance.taskId}')">
                        Approve
                    </button>
                    <button class="btn reject" onclick="this.rejectTask('${taskInstance.taskId}')">
                        Reject
                    </button>
                </div>
                <textarea placeholder="Comments" id="approval-comments-${taskInstance.taskId}"></textarea>
            </div>
        `;
        document.body.appendChild(modal);
    }

    approveTask(taskId) {
        const comments = document.getElementById(`approval-comments-${taskId}`).value;
        this.send({
            type: 'userTask.complete',
            taskId: taskId,
            decision: 'approved',
            comments: comments,
            user: this.getCurrentUser()
        });

        // Close modal
        document.querySelector('.approval-modal').remove();
    }

    rejectTask(taskId) {
        const comments = document.getElementById(`approval-comments-${taskId}`).value;
        this.send({
            type: 'userTask.complete',
            taskId: taskId,
            decision: 'rejected',
            comments: comments,
            user: this.getCurrentUser()
        });

        // Close modal
        document.querySelector('.approval-modal').remove();
    }

    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
    }

    on(messageType, handler) {
        if (!this.handlers[messageType]) {
            this.handlers[messageType] = [];
        }
        this.handlers[messageType].push(handler);
    }
}

// Initialize AG-UI client
const aguiClient = new AGUIClient();

// Register custom handlers
aguiClient.on('workflow.started', (msg) => {
    console.log('Workflow started:', msg.instanceId);
});

aguiClient.on('workflow.completed', (msg) => {
    alert(`Workflow completed with outcome: ${msg.outcome}`);
});
```

## Complete Example: AI Log Analysis Execution

### Backend Main Execution

```python
import asyncio
from workflow_engine import WorkflowEngine
from agui_server import AGUIServer
from mcp_client import MCPClient

async def execute_log_analysis_workflow(yaml_file_path: str, log_file_path: str):
    """Execute the AI log analysis workflow"""

    # Initialize components
    agui_server = AGUIServer()
    mcp_client = MCPClient()

    # Start AG-UI server
    asyncio.create_task(agui_server.start())

    # Load workflow YAML
    with open(yaml_file_path, 'r') as f:
        yaml_content = f.read()

    # Create workflow engine
    engine = WorkflowEngine(
        yaml_content=yaml_content,
        ui_broadcaster=agui_server
    )

    # Start execution with context
    context = {
        'logFileUrl': log_file_path,
        'logFileName': log_file_path.split('/')[-1],
        'requester': {
            'email': 'user@example.com',
            'name': 'John Doe'
        }
    }

    try:
        await engine.start_execution(context)
        print("Workflow completed successfully")
    except Exception as e:
        print(f"Workflow failed: {e}")
        await agui_server.broadcast({
            'type': 'workflow.failed',
            'error': str(e)
        })

# Run
if __name__ == '__main__':
    asyncio.run(execute_log_analysis_workflow(
        'ai-log-analysis-workflow.yaml',
        's3://devops-logs/nginx-error.log'
    ))
```

### Execution Flow Timeline

```
Time  | Element              | Event                          | AG-UI Update
------|----------------------|--------------------------------|---------------------------
0:00  | Start Event          | workflow.started               | Highlight start event
0:01  | Receive Log File     | element.activated              | Show "Receiving log..."
0:05  | Receive Log File     | element.completed              | Mark complete ✓
0:05  | Store in S3          | element.activated              | Show "Storing in S3..."
0:07  | Store in S3          | element.completed              | Mark complete ✓
      |                      | task.progress: Uploading       |
0:07  | Analyze Logs (AI)    | element.activated              | Show "Analyzing logs..."
      |                      | task.progress: Initializing    | Progress: 10%
      |                      | agent.tool_use: filesystem-read| Show tool usage popup
      |                      | agent.tool_use: grep-search    | Show tool usage popup
      |                      | task.progress: Analyzing       | Progress: 50%
0:45  | Analyze Logs (AI)    | element.completed              | Mark complete ✓
0:45  | Generate Diagnostics | element.activated              | Show "Generating steps..."
      |                      | task.progress: Executing       | Progress: 30%
1:05  | Generate Diagnostics | element.completed              | Mark complete ✓
1:05  | Valid Results?       | gateway.evaluating             | Show gateway active
      |                      | gateway.path_taken: "yes"      | Highlight flow
1:06  | Review & Approve     | element.activated              | Show element active
      |                      | userTask.created               | **SHOW APPROVAL FORM**
------|----------------------|--------------------------------|---------------------------
      | [USER INTERACTION]   |                                | User reviews diagnostics
      |                      |                                | User clicks "Approve"
      |                      | userTask.complete (from UI)    |
------|----------------------|--------------------------------|---------------------------
1:35  | Review & Approve     | element.completed              | Close form, mark complete
1:35  | Approved?            | gateway.evaluating             | Show gateway active
      |                      | gateway.path_taken: "approved" | Highlight flow
1:36  | Generate Playbook    | element.activated              | Show "Generating playbook"
      |                      | task.progress: Executing       | Progress: 20%
      |                      | agent.tool_use: ansible-validator| Tool usage popup
2:10  | Generate Playbook    | element.completed              | Mark complete ✓
2:10  | Validate Syntax      | element.activated              | Show "Validating..."
2:15  | Validate Syntax      | element.completed              | Mark complete ✓
2:15  | Valid Playbook?      | gateway.evaluating             | Show gateway active
      |                      | gateway.path_taken: "valid"    | Highlight flow
2:16  | Store Playbook       | element.activated              | Show "Storing..."
2:20  | Store Playbook       | element.completed              | Mark complete ✓
2:20  | Execute on Systems   | element.activated              | Show "Executing..."
2:45  | Execute on Systems   | element.completed              | Mark complete ✓
2:45  | Send Notification    | element.activated              | Show "Sending email..."
2:47  | Send Notification    | element.completed              | Mark complete ✓
2:47  | End Event            | workflow.completed             | Show success message
```

## State Persistence

```python
class WorkflowState:
    """Persistent state for workflow execution"""

    def __init__(self, db_connection):
        self.db = db_connection

    async def save_instance(self, instance_id: str, data: dict):
        """Save workflow instance state"""
        await self.db.upsert('workflow_instances', {
            'instance_id': instance_id,
            'state': 'running',
            'current_element': data.get('current_element'),
            'context': json.dumps(data.get('context', {})),
            'start_time': data.get('start_time'),
            'updated_at': datetime.utcnow()
        })

    async def save_element_execution(self, instance_id: str, element_id: str, status: str, result: any):
        """Save element execution history"""
        await self.db.insert('element_executions', {
            'instance_id': instance_id,
            'element_id': element_id,
            'status': status,
            'result': json.dumps(result),
            'timestamp': datetime.utcnow()
        })

    async def get_instance(self, instance_id: str):
        """Retrieve instance state"""
        return await self.db.query_one(
            'SELECT * FROM workflow_instances WHERE instance_id = ?',
            (instance_id,)
        )
```

## MCP Client Integration

```python
class MCPClient:
    """Client for MCP (Model Context Protocol) tool access"""

    def __init__(self, mcp_server_url='http://localhost:8080'):
        self.server_url = mcp_server_url
        self.tools_cache = {}

    async def get_tool(self, tool_name: str):
        """Get MCP tool by name"""
        if tool_name in self.tools_cache:
            return self.tools_cache[tool_name]

        # Fetch tool definition from MCP server
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{self.server_url}/tools/{tool_name}') as resp:
                tool_def = await resp.json()
                tool = MCPTool(tool_name, tool_def, self)
                self.tools_cache[tool_name] = tool
                return tool

    async def invoke_tool(self, tool_name: str, arguments: dict):
        """Invoke MCP tool"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.server_url}/tools/{tool_name}/invoke',
                json=arguments
            ) as resp:
                return await resp.json()

class MCPTool:
    """Wrapper for MCP tool"""

    def __init__(self, name: str, definition: dict, client: MCPClient):
        self.name = name
        self.definition = definition
        self.client = client

    async def __call__(self, **kwargs):
        """Execute the tool"""
        return await self.client.invoke_tool(self.name, kwargs)
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Production Setup                     │
└─────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐
│   Frontend   │         │   Backend    │
│  (Static)    │◄────────┤   (API)      │
│              │  HTTP   │              │
└──────┬───────┘         └──────┬───────┘
       │                        │
       │ WebSocket (AG-UI)      │
       │                        │
       └────────►┌──────────────▼───────┐
                 │  AG-UI Server        │
                 │  (WebSocket)         │
                 └──────────┬───────────┘
                            │
                 ┌──────────▼───────────┐
                 │ Workflow Engine      │
                 │ (Asyncio Workers)    │
                 └──────────┬───────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
    ┌────▼────┐      ┌──────▼──────┐   ┌──────▼──────┐
    │   MCP   │      │  Database   │   │   Message   │
    │  Server │      │ (Postgres)  │   │   Queue     │
    └─────────┘      └─────────────┘   │  (Redis)    │
                                       └─────────────┘
```

## Technology Stack Recommendations

### Backend
- **Language**: Python 3.9+ (asyncio support)
- **Web Framework**: FastAPI (for REST API + WebSocket)
- **Workflow Engine**: Custom (as described above)
- **Database**: PostgreSQL (state persistence)
- **Message Queue**: Redis / RabbitMQ (async task execution)
- **MCP Integration**: Custom client or existing SDK

### Frontend
- **Keep existing**: HTML + SVG + Vanilla JS
- **Add**: WebSocket client for AG-UI protocol
- **Styling**: Existing CSS + animations for state changes

### Infrastructure
- **Container**: Docker
- **Orchestration**: Kubernetes (optional, for scale)
- **Observability**: Prometheus + Grafana for workflow metrics

## Summary

This architecture provides:

1. **YAML-Driven Execution**: Parse workflow definitions and execute tasks
2. **Task Executor Pattern**: Extensible executors for each task type
3. **MCP Integration**: Agentic tasks can use filesystem-read, grep-search, etc.
4. **Real-Time UI Updates**: AG-UI protocol broadcasts execution state
5. **Human Approval**: User tasks block until human completes form
6. **Gateway Logic**: Evaluate conditions to route flow
7. **State Persistence**: Save execution state for recovery
8. **Error Handling**: Retries, escalation, and error paths

The system can execute the AI log analysis workflow end-to-end with live UI feedback!
