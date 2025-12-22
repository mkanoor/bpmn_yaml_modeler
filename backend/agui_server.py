"""
AG-UI WebSocket Server
Broadcasts workflow execution updates to connected clients
"""
import asyncio
import json
import logging
from typing import Set, Dict, Any
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class AGUIServer:
    """WebSocket server implementing AG-UI protocol"""

    def __init__(self):
        self.clients: Set[WebSocket] = set()
        self.user_task_completions: Dict[str, asyncio.Event] = {}
        self.user_task_results: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket):
        """Accept new client connection"""
        await websocket.accept()
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")

    async def disconnect(self, websocket: WebSocket):
        """Handle client disconnection"""
        self.clients.discard(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def handle_client(self, websocket: WebSocket):
        """Handle messages from a client"""
        try:
            await self.connect(websocket)
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)

                # Route message
                await self.handle_client_message(message, websocket)

        except WebSocketDisconnect:
            await self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Error handling client: {e}")
            await self.disconnect(websocket)

    async def handle_client_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Process messages from UI"""
        msg_type = message.get('type')

        if msg_type == 'userTask.complete':
            # User completed an approval task
            task_id = message.get('taskId')
            decision = message.get('decision')
            comments = message.get('comments', '')
            user = message.get('user', 'anonymous')

            logger.info(f"User task {task_id} completed: {decision}")

            # Store completion data
            self.user_task_results[task_id] = {
                'decision': decision,
                'comments': comments,
                'completedBy': user,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Signal completion event
            if task_id in self.user_task_completions:
                self.user_task_completions[task_id].set()

        elif msg_type == 'ping':
            # Respond to ping
            await websocket.send_json({
                'type': 'pong',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.clients:
            logger.debug("No clients connected, skipping broadcast")
            return

        # Add timestamp if not present
        if 'timestamp' not in message:
            message['timestamp'] = datetime.now(timezone.utc).isoformat()

        # Serialize message
        message_json = json.dumps(message, default=str)

        # Send to all clients
        disconnected = set()
        for client in self.clients:
            try:
                await client.send_text(message_json)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.add(client)

        # Remove disconnected clients
        self.clients -= disconnected

    async def send_update(self, message: Dict[str, Any]):
        """Send AG-UI update (alias for broadcast)"""
        await self.broadcast(message)

    async def wait_for_user_task_completion(self, task_id: str) -> Dict[str, Any]:
        """Wait for user task to be completed"""
        # Create event if not exists
        if task_id not in self.user_task_completions:
            self.user_task_completions[task_id] = asyncio.Event()

        # Wait for completion
        await self.user_task_completions[task_id].wait()

        # Get and return result
        result = self.user_task_results.get(task_id, {})

        # Cleanup
        del self.user_task_completions[task_id]
        if task_id in self.user_task_results:
            del self.user_task_results[task_id]

        return result

    async def send_workflow_started(self, instance_id: str, workflow_name: str):
        """Send workflow started event"""
        await self.send_update({
            'type': 'workflow.started',
            'instanceId': instance_id,
            'workflowName': workflow_name
        })

    async def send_workflow_completed(self, instance_id: str, outcome: str, duration: float):
        """Send workflow completed event"""
        await self.send_update({
            'type': 'workflow.completed',
            'instanceId': instance_id,
            'outcome': outcome,
            'duration': duration
        })

    async def send_element_activated(self, element_id: str, element_type: str, element_name: str):
        """Send element activated event"""
        await self.send_update({
            'type': 'element.activated',
            'elementId': element_id,
            'elementType': element_type,
            'elementName': element_name
        })

    async def send_element_completed(self, element_id: str, duration: float = 0, result: Any = None):
        """Send element completed event"""
        await self.send_update({
            'type': 'element.completed',
            'elementId': element_id,
            'duration': duration,
            'result': result
        })

    async def send_task_progress(self, element_id: str, progress: float, status: str, message: str):
        """Send task progress update"""
        await self.send_update({
            'type': 'task.progress',
            'elementId': element_id,
            'progress': progress,
            'status': status,
            'message': message
        })

    async def send_agent_tool_use(self, element_id: str, tool: str, arguments: Dict[str, Any], result: Any = None):
        """Send agent tool use notification"""
        await self.send_update({
            'type': 'agent.tool_use',
            'elementId': element_id,
            'tool': tool,
            'arguments': arguments,
            'result': result
        })

    async def send_user_task_created(self, element_id: str, task_instance: Dict[str, Any]):
        """Send user task created event"""
        await self.send_update({
            'type': 'userTask.created',
            'elementId': element_id,
            'taskInstance': task_instance,
            'action': 'showApprovalForm'
        })

    async def send_gateway_evaluating(self, element_id: str, gateway_type: str, paths: int):
        """Send gateway evaluating event"""
        await self.send_update({
            'type': 'gateway.evaluating',
            'elementId': element_id,
            'gatewayType': gateway_type,
            'paths': paths
        })

    async def send_gateway_path_taken(self, element_id: str, flow_id: str, condition: str = None):
        """Send gateway path taken event"""
        await self.send_update({
            'type': 'gateway.path_taken',
            'elementId': element_id,
            'flowId': flow_id,
            'condition': condition
        })

    async def send_task_error(self, element_id: str, error: Exception, retryable: bool = False):
        """Send task error event"""
        await self.send_update({
            'type': 'task.error',
            'elementId': element_id,
            'error': {
                'message': str(error),
                'type': type(error).__name__
            },
            'retryable': retryable
        })

    async def send_task_cancelled(self, element_id: str, reason: str = "Another path completed first"):
        """Send task cancellation event (e.g., for inclusive gateway merge)"""
        logger.info(f"📤 SENDING task.cancelled event for element: {element_id}")
        logger.info(f"   Reason: {reason}")
        logger.info(f"   Connected clients: {len(self.clients)}")

        await self.send_update({
            'type': 'task.cancelled',
            'elementId': element_id,
            'reason': reason
        })

        logger.info(f"✅ task.cancelled event sent successfully")

    # AG-UI Streaming Events (for real-time task feedback)

    async def send_text_message_start(self, element_id: str, message_id: str = None):
        """Signal start of a new streaming message from a task"""
        import uuid
        msg_id = message_id or str(uuid.uuid4())

        await self.send_update({
            'type': 'text.message.start',
            'elementId': element_id,
            'messageId': msg_id
        })

        return msg_id

    async def send_text_message_content(self, element_id: str, message_id: str, content: str, delta: str = None):
        """Send partial content for a streaming message"""
        await self.send_update({
            'type': 'text.message.content',
            'elementId': element_id,
            'messageId': message_id,
            'content': content,
            'delta': delta or content  # Delta is the new chunk, content is cumulative
        })

    async def send_text_message_end(self, element_id: str, message_id: str):
        """Signal end of a streaming message"""
        await self.send_update({
            'type': 'text.message.end',
            'elementId': element_id,
            'messageId': message_id
        })

    async def send_task_thinking(self, element_id: str, message: str = "Thinking..."):
        """Show thinking indicator for a task"""
        await self.send_update({
            'type': 'task.thinking',
            'elementId': element_id,
            'message': message
        })

    async def send_task_tool_start(self, element_id: str, tool_name: str, tool_args: Dict[str, Any]):
        """Signal start of tool execution"""
        await self.send_update({
            'type': 'task.tool.start',
            'elementId': element_id,
            'toolName': tool_name,
            'toolArgs': tool_args
        })

    async def send_task_tool_end(self, element_id: str, tool_name: str, result: Any = None):
        """Signal end of tool execution"""
        await self.send_update({
            'type': 'task.tool.end',
            'elementId': element_id,
            'toolName': tool_name,
            'result': result
        })
