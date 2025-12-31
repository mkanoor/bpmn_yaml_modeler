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

# Handle both relative and absolute imports
try:
    from .event_store import EventStore
    from .agui_event_filter import event_filter
except ImportError:
    from event_store import EventStore
    from agui_event_filter import event_filter

logger = logging.getLogger(__name__)


class AGUIServer:
    """WebSocket server implementing AG-UI protocol"""

    def __init__(self, db_path: str = "agui_events.db"):
        self.clients: Set[WebSocket] = set()
        self.user_task_completions: Dict[str, asyncio.Event] = {}
        self.user_task_results: Dict[str, Dict[str, Any]] = {}

        # Initialize SQLite event store for persistent history
        self.event_store = EventStore(db_path)

        # Track task preferences for event filtering
        self.task_preferences: Dict[str, Dict[str, Any]] = {}

        # Track cancellation requests
        self.cancellation_requests: Dict[str, asyncio.Event] = {}
        self.cancelled_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.cancellable_tasks: Set[str] = set()

        logger.info(f"✅ AG-UI Server initialized with SQLite persistence at {db_path}")

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

        elif msg_type == 'replay.request':
            # Client requesting history replay for an element
            element_id = message.get('elementId')
            logger.info(f"📼 Replay requested for element: {element_id}")
            await self.send_replay_snapshot(element_id, websocket)

        elif msg_type == 'clear.history':
            # Client requesting to clear all history
            logger.info(f"🗑️ Clear history requested")
            await self.clear_history()

        elif msg_type == 'task.cancel.request':
            # Client requesting task cancellation
            element_id = message.get('elementId')
            reason = message.get('reason', 'User cancelled')

            logger.info(f"🛑 Cancel request for task: {element_id}, reason: {reason}")

            # Check if task is cancellable
            if element_id not in self.cancellable_tasks:
                logger.warning(f"Task {element_id} is not cancellable")
                await websocket.send_json({
                    'type': 'task.cancel.failed',
                    'elementId': element_id,
                    'error': 'Task is not cancellable (may have already completed)',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                return

            # Check if already completed
            if element_id in self.completed_tasks:
                logger.warning(f"Task {element_id} already completed, cannot cancel")
                await websocket.send_json({
                    'type': 'task.cancel.failed',
                    'elementId': element_id,
                    'error': 'Task already completed',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                return

            # Signal cancellation
            if element_id not in self.cancellation_requests:
                self.cancellation_requests[element_id] = asyncio.Event()

            self.cancellation_requests[element_id].set()
            self.cancelled_tasks.add(element_id)
            self.cancellable_tasks.discard(element_id)

            logger.info(f"✅ Cancellation signal set for task: {element_id}")

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

    def register_task_preferences(self, element_id: str, task_properties: Dict[str, Any]):
        """Register task preferences for event filtering"""
        self.task_preferences[element_id] = task_properties
        enabled_categories = event_filter.get_enabled_categories(task_properties)
        logger.info(f"📋 Registered event preferences for {element_id}: {enabled_categories}")

    async def send_update(self, message: Dict[str, Any]):
        """Send AG-UI update with event filtering"""
        event_type = message.get('type')
        element_id = message.get('elementId')

        # Apply event filtering if element has registered preferences
        if element_id and element_id in self.task_preferences:
            task_prefs = self.task_preferences[element_id]
            if not event_filter.should_send_event(event_type, task_prefs):
                logger.debug(f"🚫 Filtered event '{event_type}' for element {element_id}")
                return  # Don't send this event

        await self.broadcast(message)

        # Store event in history for replay (AG-UI checkpointing)
        if element_id:
            await self._persist_event(element_id, message)

    async def _persist_event(self, element_id: str, event: Dict[str, Any]):
        """Persist event to SQLite for replay"""
        event_type = event.get('type')
        timestamp = event.get('timestamp', datetime.now(timezone.utc).isoformat())
        thread_id = f"thread_{element_id}"

        # Ensure thread exists
        self.event_store.ensure_thread(element_id, thread_id)

        # Store raw event
        self.event_store.store_event(element_id, event_type, event)

        # Handle event-specific persistence
        if event_type == 'text.message.start':
            # Start a new message
            message_id = event.get('messageId')
            self.event_store.store_message_start(element_id, thread_id, message_id, timestamp)
            logger.debug(f"💾 Stored message start: {message_id}")

        elif event_type == 'text.message.content':
            # Update message with accumulated content
            message_id = event.get('messageId')
            content = event.get('content', '')
            self.event_store.update_message_content(message_id, content)
            # Log every 100 characters to avoid spam
            if len(content) % 100 < 10:
                logger.debug(f"💾 Updated message content: {message_id} ({len(content)} chars)")

        elif event_type == 'text.message.end':
            # Mark message as complete
            message_id = event.get('messageId')
            self.event_store.complete_message(message_id)
            logger.debug(f"💾 Completed message: {message_id}")

        elif event_type == 'task.thinking':
            # Store thinking event
            message = event.get('message')
            self.event_store.store_thinking(element_id, thread_id, message, timestamp)
            logger.debug(f"💾 Stored thinking: {message[:50]}...")

        elif event_type == 'task.tool.start':
            # Start a new tool execution
            tool_name = event.get('toolName')
            tool_args = event.get('toolArgs', {})
            self.event_store.store_tool_start(element_id, thread_id, tool_name, tool_args, timestamp)
            logger.debug(f"💾 Stored tool start: {tool_name}")

        elif event_type == 'task.tool.end':
            # Complete tool execution
            tool_name = event.get('toolName')
            result = event.get('result')
            self.event_store.complete_tool(element_id, tool_name, result, timestamp)
            logger.debug(f"💾 Completed tool: {tool_name}")

        elif event_type == 'task.cancelled':
            # Mark any in-progress messages as cancelled
            reason = event.get('reason', 'User cancelled')
            # Find the most recent message for this element and mark it as cancelled
            # This will be reflected in replay
            logger.debug(f"💾 Task cancelled: {element_id}, reason: {reason}")

    # ===== CANCELLATION SUPPORT =====

    def mark_task_cancellable(self, element_id: str):
        """Mark a task as cancellable (can be stopped by user)"""
        self.cancellable_tasks.add(element_id)
        logger.debug(f"Task {element_id} marked as cancellable")

    def mark_task_completed(self, element_id: str):
        """Mark a task as completed (can no longer be cancelled)"""
        self.completed_tasks.add(element_id)
        self.cancellable_tasks.discard(element_id)
        logger.debug(f"Task {element_id} marked as completed")

    def is_cancelled(self, element_id: str) -> bool:
        """Check if a task has been cancelled"""
        return element_id in self.cancelled_tasks

    def is_cancellable(self, element_id: str) -> bool:
        """Check if a task can be cancelled"""
        return element_id in self.cancellable_tasks

    async def send_task_cancellable(self, element_id: str):
        """Notify frontend that task can be cancelled"""
        await self.send_update({
            'type': 'task.cancellable',
            'elementId': element_id
        })

    async def send_task_cancelling(self, element_id: str):
        """Notify that cancellation is in progress"""
        await self.send_update({
            'type': 'task.cancelling',
            'elementId': element_id,
            'message': 'Stopping task gracefully...'
        })

    async def send_task_cancelled_complete(self, element_id: str, reason: str, partial_result: Any = None):
        """Notify that task was successfully cancelled"""
        await self.send_update({
            'type': 'task.cancelled',
            'elementId': element_id,
            'reason': reason,
            'partialResult': partial_result
        })

    # ===== REPLAY SUPPORT =====

    async def send_replay_snapshot(self, element_id: str, websocket: WebSocket = None):
        """
        Replay messages sentence-by-sentence using TEXT_MESSAGE_CHUNK events.

        This sends each stored sentence as a separate chunk, simulating the
        original streaming experience.
        """
        # Load history from SQLite
        history = self.event_store.get_thread_history(element_id)

        if not history:
            logger.warning(f"No history found in SQLite for element: {element_id}")
            return

        logger.info(f"📼 Starting REPLAY for element {element_id} (from SQLite)")
        logger.info(f"   Thread ID: {history['threadId']}")
        logger.info(f"   Messages (sentences): {len(history['messages'])}")
        logger.info(f"   Thinking events: {len(history['thinking'])}")
        logger.info(f"   Tool events: {len(history['tools'])}")

        # Collect all events with timestamps for chronological replay
        all_events = []

        # Add thinking events
        for thinking in history['thinking']:
            all_events.append({
                'type': 'thinking',
                'timestamp': thinking['timestamp'],
                'data': thinking
            })

        # Add tool events (split into start and end)
        for tool in history['tools']:
            all_events.append({
                'type': 'tool.start',
                'timestamp': tool['startTime'],
                'data': tool
            })
            if tool.get('endTime'):
                all_events.append({
                    'type': 'tool.end',
                    'timestamp': tool['endTime'],
                    'data': tool
                })

        # Add message events (these are complete sentences)
        for message in history['messages']:
            all_events.append({
                'type': 'message.chunk',
                'timestamp': message['timestamp'],
                'data': message
            })

        # Sort events chronologically
        all_events.sort(key=lambda e: e['timestamp'])

        logger.info(f"📼 Replaying {len(all_events)} events in chronological order...")

        # Send events sequentially as TEXT_MESSAGE_CHUNK
        for event in all_events:
            if event['type'] == 'thinking':
                thinking_event = {
                    'type': 'task.thinking',
                    'elementId': element_id,
                    'message': event['data']['message'],
                    'timestamp': event['data']['timestamp']
                }
                if websocket:
                    await websocket.send_json(thinking_event)
                else:
                    await self.broadcast(thinking_event)

            elif event['type'] == 'tool.start':
                tool_start_event = {
                    'type': 'task.tool.start',
                    'elementId': element_id,
                    'toolName': event['data']['name'],
                    'toolArgs': event['data'].get('args', {}),
                    'timestamp': event['data']['startTime']
                }
                if websocket:
                    await websocket.send_json(tool_start_event)
                else:
                    await self.broadcast(tool_start_event)

            elif event['type'] == 'tool.end':
                tool_end_event = {
                    'type': 'task.tool.end',
                    'elementId': element_id,
                    'toolName': event['data']['name'],
                    'result': event['data'].get('result'),
                    'timestamp': event['data']['endTime']
                }
                if websocket:
                    await websocket.send_json(tool_end_event)
                else:
                    await self.broadcast(tool_end_event)

            elif event['type'] == 'message.chunk':
                # Send as TEXT_MESSAGE_CHUNK (complete sentence)
                chunk_event = {
                    'type': 'text.message.chunk',
                    'elementId': element_id,
                    'messageId': event['data']['id'],
                    'role': event['data']['role'],
                    'content': event['data']['content'],
                    'timestamp': event['data']['timestamp']
                }
                if websocket:
                    await websocket.send_json(chunk_event)
                else:
                    await self.broadcast(chunk_event)

                logger.info(f"   📦 Replayed sentence: {event['data']['id'][:20]}... ({len(event['data']['content'])} chars)")

            # Small delay between events for visual effect (optional)
            await asyncio.sleep(0.05)

        logger.info(f"📼 Replay complete for element {element_id}")

    async def clear_history(self, element_id: str = None):
        """Clear history from SQLite for an element or all elements"""
        if element_id:
            self.event_store.clear_element_history(element_id)
            logger.info(f"🗑️ Cleared SQLite history for element: {element_id}")
        else:
            self.event_store.clear_all_history()
            logger.info(f"🗑️ Cleared all SQLite history")

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

    async def send_workflow_started(self, instance_id: str, workflow_name: str, workflow_file: str = None):
        """Send workflow started event"""
        message = {
            'type': 'workflow.started',
            'instanceId': instance_id,
            'workflowName': workflow_name
        }
        if workflow_file:
            message['workflowFile'] = workflow_file
        await self.send_update(message)

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

        logger.info(f"📤 SENDING text.message.start for element: {element_id}, message: {msg_id}")
        logger.info(f"   Connected clients: {len(self.clients)}")

        await self.send_update({
            'type': 'text.message.start',
            'elementId': element_id,
            'messageId': msg_id
        })

        logger.info(f"✅ text.message.start sent successfully")
        return msg_id

    async def send_text_message_content(self, element_id: str, message_id: str, content: str, delta: str = None):
        """Send partial content for a streaming message"""
        # Log every 10th chunk to avoid spam
        if len(content) % 100 < 10:  # Rough approximation
            logger.debug(f"📤 Sending text.message.content chunk - element: {element_id}, cumulative length: {len(content)}, delta: {len(delta) if delta else 0}")

        await self.send_update({
            'type': 'text.message.content',
            'elementId': element_id,
            'messageId': message_id,
            'content': content,
            'delta': delta or content  # Delta is the new chunk, content is cumulative
        })

    async def send_text_message_end(self, element_id: str, message_id: str):
        """Signal end of a streaming message"""
        logger.info(f"📤 SENDING text.message.end for element: {element_id}, message: {message_id}")

        await self.send_update({
            'type': 'text.message.end',
            'elementId': element_id,
            'messageId': message_id
        })

        logger.info(f"✅ text.message.end sent successfully")

    async def send_text_message_chunk(self, element_id: str, message_id: str, content: str, role: str = 'assistant'):
        """
        Send a complete sentence as a TEXT_MESSAGE_CHUNK event.

        This is the simplified streaming pattern where each chunk is a complete sentence.
        The first chunk for a new message_id acts as START + CONTENT.
        Subsequent chunks with the same ID append content.
        """
        logger.debug(f"📤 SENDING text.message.chunk for element: {element_id}, message: {message_id}, length: {len(content)}")

        await self.send_update({
            'type': 'text.message.chunk',
            'elementId': element_id,
            'messageId': message_id,
            'content': content,
            'role': role,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    async def send_task_thinking(self, element_id: str, message: str = "Thinking..."):
        """Show thinking indicator for a task"""
        logger.info(f"📤 SENDING task.thinking for element: {element_id}, message: {message}")

        await self.send_update({
            'type': 'task.thinking',
            'elementId': element_id,
            'message': message
        })

        logger.info(f"✅ task.thinking sent successfully")

    async def send_task_tool_start(self, element_id: str, tool_name: str, tool_args: Dict[str, Any]):
        """Signal start of tool execution"""
        logger.info(f"📤 SENDING task.tool.start for element: {element_id}, tool: {tool_name}")

        await self.send_update({
            'type': 'task.tool.start',
            'elementId': element_id,
            'toolName': tool_name,
            'toolArgs': tool_args
        })

        logger.info(f"✅ task.tool.start sent successfully")

    async def send_task_tool_end(self, element_id: str, tool_name: str, result: Any = None):
        """Signal end of tool execution"""
        logger.info(f"📤 SENDING task.tool.end for element: {element_id}, tool: {tool_name}")

        await self.send_update({
            'type': 'task.tool.end',
            'elementId': element_id,
            'toolName': tool_name,
            'result': result
        })

        logger.info(f"✅ task.tool.end sent successfully")
