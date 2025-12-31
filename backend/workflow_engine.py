"""
Workflow Execution Engine
Main orchestrator for BPMN workflow execution
"""
import asyncio
import uuid
import yaml
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from models import Workflow, Element, ExecutionStatus
from task_executors import TaskExecutorRegistry
from gateway_evaluator import GatewayEvaluator
from agui_server import AGUIServer

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Main orchestrator for workflow execution"""

    def __init__(self, yaml_content: str, agui_server: AGUIServer, mcp_client=None, workflow_file: str = None):
        self.workflow = self.parse_yaml(yaml_content)
        self.agui_server = agui_server
        self.mcp_client = mcp_client
        self.workflow_file = workflow_file  # Store filename for logging

        # Extract subprocess definitions if present
        logger.info(f"DEBUG: workflow.process attributes: {dir(self.workflow.process)}")
        logger.info(f"DEBUG: hasattr subprocess_definitions: {hasattr(self.workflow.process, 'subprocess_definitions')}")
        self.subprocess_definitions = self.workflow.process.subprocess_definitions
        logger.info(f"DEBUG: subprocess_definitions value: {self.subprocess_definitions}")
        logger.info(f"Loaded {len(self.subprocess_definitions)} subprocess definitions")

        # Initialize components (pass self for callActivity support)
        self.task_executors = TaskExecutorRegistry(agui_server, mcp_client, workflow_engine=self)
        self.gateway_evaluator = GatewayEvaluator(self.workflow, agui_server)

        # Instance state
        self.instance_id: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.context: Dict[str, Any] = {}

        # Merge point tracking for gateways (tracks which paths have arrived)
        # Key: gateway_id, Value: dict with 'completed' flag and 'elements' set
        self.merge_arrivals: Dict[str, Dict[str, Any]] = {}
        # Lock for merge point synchronization
        self.merge_locks: Dict[str, asyncio.Lock] = {}
        # Track active tasks that may need cancellation (key: element_id, value: element)
        self.active_tasks: Dict[str, Element] = {}
        # Track asyncio tasks for proper cancellation (key: element_id, value: asyncio.Task)
        self.running_tasks: Dict[str, asyncio.Task] = {}

    def parse_yaml(self, yaml_content: str) -> Workflow:
        """Parse YAML into workflow object model"""
        try:
            data = yaml.safe_load(yaml_content)
            logger.info(f"DEBUG parse_yaml: Keys in data['process']: {list(data.get('process', {}).keys())}")
            logger.info(f"DEBUG parse_yaml: Has subProcessDefinitions: {'subProcessDefinitions' in data.get('process', {})}")
            if 'subProcessDefinitions' in data.get('process', {}):
                logger.info(f"DEBUG parse_yaml: Number of subProcessDefinitions in YAML: {len(data['process']['subProcessDefinitions'])}")

            # Print the YAML content that was received
            logger.info("=" * 80)
            logger.info("FULL YAML CONTENT RECEIVED BY BACKEND:")
            logger.info("=" * 80)
            logger.info(yaml_content)
            logger.info("=" * 80)

            return Workflow(**data)
        except Exception as e:
            logger.error(f"Error parsing YAML: {e}")
            raise ValueError(f"Invalid YAML workflow: {e}")

    async def start_execution(self, initial_context: Dict[str, Any] = None):
        """Start workflow execution from start event"""
        # Create instance
        self.instance_id = str(uuid.uuid4())
        self.start_time = datetime.now(timezone.utc)
        self.context = initial_context or {}

        # Add instance ID to context for use in workflows (e.g., approval correlation keys)
        self.context['workflowInstanceId'] = self.instance_id

        logger.info(f"🚀 ========================================")
        logger.info(f"🚀 Starting NEW workflow execution")
        if self.workflow_file:
            logger.info(f"🚀 Workflow File: {self.workflow_file}")
        logger.info(f"🚀 Workflow Name: {self.workflow.process.name}")
        logger.info(f"🚀 Instance ID: {self.instance_id}")
        logger.info(f"🚀 Context keys: {list(self.context.keys())}")
        logger.info(f"🚀 ========================================")

        # Broadcast workflow started
        await self.agui_server.send_workflow_started(
            self.instance_id,
            self.workflow.process.name,
            self.workflow_file
        )

        try:
            # Find start event
            start_event = self.workflow.get_start_event()
            if not start_event:
                raise ValueError("No start event found in workflow")

            # Execute from start event
            await self.execute_from_element(start_event)

            # Workflow completed successfully
            duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            await self.agui_server.send_workflow_completed(
                self.instance_id,
                'success',
                duration
            )

            logger.info(f"Workflow completed successfully: {self.instance_id}")

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)

            # Broadcast failure
            duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            await self.agui_server.send_workflow_completed(
                self.instance_id,
                'failed',
                duration
            )

            raise

    async def execute_from_element(self, element: Element):
        """Execute workflow from a given element"""
        if not element:
            return

        element_start = datetime.now(timezone.utc)

        # Mark element as activated
        await self.agui_server.send_element_activated(
            element.id,
            element.type,
            element.name
        )

        logger.info(f"Executing element: {element.name} ({element.type})")

        try:
            # Execute based on element type
            next_elements = None
            task_was_cancelled = False  # Track if task was cancelled by boundary event

            if element.is_task():
                task_was_cancelled = await self.execute_task_with_boundary_events(element)
            elif element.is_gateway():
                # Gateway evaluation returns the specific next elements to follow
                next_elements = await self.execute_gateway(element)
            elif element.is_event():
                await self.handle_event(element)
            else:
                logger.warning(f"Unknown element type: {element.type}")

            # If task was cancelled by an interrupting boundary event, don't continue the normal flow
            if task_was_cancelled:
                logger.info(f"🚫 Task {element.name} was cancelled by interrupting boundary event - skipping normal outgoing flows")
                return

            # Mark element as completed
            duration = (datetime.now(timezone.utc) - element_start).total_seconds()
            await self.agui_server.send_element_completed(element.id, duration)

            # Continue to next element(s)
            # For gateways, use the evaluated next elements, otherwise get all outgoing
            if next_elements is None:
                next_elements = self.workflow.get_outgoing_elements(element)

            if not next_elements:
                logger.info("Reached end of workflow path")
                return

            # Execute next elements (may be parallel)
            if len(next_elements) == 1:
                # Sequential execution
                await self.execute_from_element(next_elements[0])
            else:
                # Parallel execution
                tasks = [self.execute_from_element(elem) for elem in next_elements]
                # Use return_exceptions=True to handle cancelled tasks gracefully
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Log any cancellations but don't propagate them
                for i, result in enumerate(results):
                    if isinstance(result, asyncio.CancelledError):
                        logger.info(f"✅ Parallel path {i} was cancelled (expected for merge gateways)")

        except asyncio.CancelledError:
            # This path was cancelled - stop execution silently
            logger.info(f"🛑 Execution path cancelled at {element.name}")
            raise

        except Exception as e:
            import traceback
            logger.error(f"Error executing element {element.name}: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            await self.agui_server.send_task_error(element.id, e, retryable=False)
            raise

    async def cancel_competing_tasks(self, gateway: Element, incoming_connections):
        """Cancel tasks from paths that haven't reached the merge yet"""
        logger.info(f"=== cancel_competing_tasks called for gateway {gateway.id} ({gateway.name}) ===")
        logger.info(f"Number of incoming connections: {len(incoming_connections)}")
        logger.info(f"Active tasks: {list(self.active_tasks.keys())}")
        logger.info(f"Running asyncio tasks: {list(self.running_tasks.keys())}")

        # For each incoming connection, walk backward to find active tasks
        for conn in incoming_connections:
            from_element_id = conn.from_
            logger.info(f"Checking incoming connection from: {from_element_id}")

            if from_element_id in self.active_tasks:
                task = self.active_tasks[from_element_id]
                logger.info(f"✅ CANCELLING task {task.id} ({task.name}) - competing path lost to merge")

                # Send cancellation event to UI FIRST (before cancelling the task)
                # This ensures the UI receives the task.cancelled event before any
                # task.progress events from the executor's CancelledError handler
                await self.agui_server.send_task_cancelled(
                    task.id,
                    reason=f"Another approval path completed first at {gateway.name}"
                )

                # Cancel the asyncio task if it exists
                if task.id in self.running_tasks:
                    asyncio_task = self.running_tasks[task.id]
                    logger.info(f"🔴 Cancelling asyncio task for {task.id}")
                    asyncio_task.cancel()

                    # Wait a moment for cancellation to propagate
                    try:
                        await asyncio.wait_for(asyncio.shield(asyncio_task), timeout=0.1)
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        pass  # Expected when task is cancelled

                    # Remove from running tasks (if not already removed by task cleanup)
                    if task.id in self.running_tasks:
                        del self.running_tasks[task.id]
                        logger.info(f"✅ Asyncio task cancelled and removed")
                    else:
                        logger.info(f"✅ Asyncio task already cleaned up")
                else:
                    logger.info(f"⚠️ No asyncio task found for {task.id}")

                # Remove from active tasks (if not already removed by task cleanup)
                if task.id in self.active_tasks:
                    del self.active_tasks[task.id]
                    logger.info(f"Task {task.id} removed from active_tasks")
                else:
                    logger.info(f"Task {task.id} already removed from active_tasks")
            else:
                logger.info(f"❌ Task {from_element_id} not in active_tasks (already completed or not started)")

    async def execute_task(self, task: Element):
        """Execute a task using appropriate executor"""
        # Mark task as active
        self.active_tasks[task.id] = task

        # Store current asyncio task for cancellation support
        current_task = asyncio.current_task()
        if current_task:
            self.running_tasks[task.id] = current_task
            logger.info(f"📌 Registered asyncio task for {task.id}")

        logger.info(f"Executing task: {task.name} (type: {task.type})")
        logger.info(f"✅ Task {task.id} added to active_tasks. Current active: {list(self.active_tasks.keys())}")

        try:
            # Get executor for task type
            executor = self.task_executors.get_executor(task.type)

            # Execute task and handle progress updates
            async for progress in executor.execute(task, self.context):
                # Broadcast progress to UI
                await self.agui_server.send_task_progress(
                    task.id,
                    progress.progress,
                    progress.status,
                    progress.message
                )

                # Log progress
                logger.debug(f"Task {task.name}: {progress.status} - {progress.message}")

        except asyncio.CancelledError:
            logger.info(f"🛑 Task {task.id} ({task.name}) was cancelled")
            # Remove from tracking
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]
            # Re-raise to stop this execution path
            raise

        finally:
            # Remove from active tasks
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]

        # Check if this was a user task that was rejected
        if task.type == 'userTask':
            decision = self.context.get(f'{task.id}_decision')
            if decision == 'rejected':
                logger.warning(f"User task {task.name} was rejected, will continue workflow to handle rejection")
                # Don't raise exception - let workflow continue so rejection can be handled
                # The rejection decision is already in context as {task.id}_decision

        logger.info(f"Task completed: {task.name}")

    async def execute_gateway(self, gateway: Element):
        """Execute a gateway and return next element(s) to follow"""
        logger.info(f"Executing gateway: {gateway.name} (type: {gateway.type})")
        logger.info(f"Current active_tasks when entering gateway: {list(self.active_tasks.keys())}")

        # Check if this is a merge point (multiple incoming connections)
        incoming = self.workflow.get_incoming_connections(gateway)
        logger.info(f"Incoming connections to gateway {gateway.id}: {[f'{c.from_} -> {c.to}' for c in incoming]}")

        if len(incoming) > 1:
            # This is a merge gateway - need to handle merge semantics
            logger.info(f"Gateway {gateway.id} is a merge point with {len(incoming)} incoming paths")

            # Get or create lock for this merge point
            if gateway.id not in self.merge_locks:
                self.merge_locks[gateway.id] = asyncio.Lock()

            async with self.merge_locks[gateway.id]:
                # Track which path arrived
                if gateway.id not in self.merge_arrivals:
                    self.merge_arrivals[gateway.id] = {
                        'completed': False,
                        'elements': set(),
                        'winning_path': None
                    }

                # For now, we can't easily track which path we arrived from
                # So we'll use a simplified approach:
                # - Parallel gateways: wait for ALL incoming paths
                # - Inclusive gateways: first path wins (continue immediately)
                # - Exclusive gateways: only one path arrives anyway

                if gateway.type == 'parallelGateway':
                    # Parallel merge: wait for all paths
                    # This would require more sophisticated tracking - for now, just pass through
                    logger.info(f"Parallel gateway merge - passing through (simplified)")
                elif gateway.type == 'inclusiveGateway':
                    # Inclusive merge: first path wins
                    if self.merge_arrivals[gateway.id]['completed']:
                        # Another path already passed through - this path should stop
                        logger.info(f"Inclusive gateway {gateway.id}: Another path already passed - stopping this path")

                        # Find and cancel any active tasks from other paths
                        # Look for tasks that are still waiting at this merge point
                        await self.cancel_competing_tasks(gateway, incoming)

                        return []  # Return empty list to stop this path
                    else:
                        # First path to arrive - mark and continue
                        logger.info(f"Inclusive gateway {gateway.id}: First path to arrive - continuing")
                        self.merge_arrivals[gateway.id]['completed'] = True

                        # Cancel any tasks from other paths that haven't reached the merge yet
                        await self.cancel_competing_tasks(gateway, incoming)

        # Evaluate gateway to get next element(s)
        next_elements = await self.gateway_evaluator.evaluate_gateway(gateway, self.context)

        logger.info(f"Gateway evaluated: {len(next_elements)} path(s) to follow")

        # Return the specific elements to execute next (based on gateway evaluation)
        return next_elements

    async def handle_event(self, event: Element):
        """Handle event"""
        logger.info(f"Handling event: {event.name} (type: {event.type})")

        if event.type == 'startEvent':
            # Start event - just pass through
            pass
        elif event.type == 'endEvent':
            # End event - workflow path complete
            logger.info(f"Reached end event: {event.name}")
        elif event.type == 'intermediateEvent':
            # Intermediate event - might trigger actions
            pass
        else:
            logger.warning(f"Unknown event type: {event.type}")

    def get_subprocess_definition(self, subprocess_id: str) -> Optional[Dict[str, Any]]:
        """Get subprocess definition by ID"""
        for subprocess_def in self.subprocess_definitions:
            if subprocess_def.get('id') == subprocess_id:
                logger.info(f"Found subprocess definition: {subprocess_def.get('name')} (id: {subprocess_id})")
                return subprocess_def

        logger.warning(f"Subprocess definition not found: {subprocess_id}")
        return None

    async def execute_subprocess(self, subprocess_def: Dict[str, Any], context: Dict[str, Any], parent_task_id: str = None) -> Dict[str, Any]:
        """Execute a subprocess definition as a mini-workflow"""
        subprocess_id = subprocess_def.get('id')
        subprocess_name = subprocess_def.get('name')

        logger.info(f"🔹 ========================================")
        logger.info(f"🔹 Starting SUBPROCESS execution")
        logger.info(f"🔹 Subprocess: {subprocess_name} (id: {subprocess_id})")
        logger.info(f"🔹 Parent Task ID: {parent_task_id}")
        logger.info(f"🔹 Subprocess context keys: {list(context.keys())}")
        logger.info(f"🔹 ========================================")

        # Create temporary workflow structure for subprocess
        # We need to convert the subprocess definition into a mini-workflow
        subprocess_elements = subprocess_def.get('elements', [])
        subprocess_connections = subprocess_def.get('connections', [])

        if not subprocess_elements:
            logger.warning(f"Subprocess {subprocess_name} has no elements")
            return context

        # Convert dict elements to Element objects (if they aren't already)
        from models import Element as ElementModel, Connection as ConnectionModel

        element_objects = []
        elements_map = {}
        for elem_data in subprocess_elements:
            if isinstance(elem_data, dict):
                # Create Element object from dict
                elem = ElementModel(
                    id=elem_data.get('id'),
                    type=elem_data.get('type'),
                    name=elem_data.get('name', ''),
                    x=elem_data.get('x', 0),
                    y=elem_data.get('y', 0),
                    properties=elem_data.get('properties', {})
                )
            else:
                elem = elem_data

            element_objects.append(elem)
            elements_map[elem.id] = elem

        # Convert dict connections to Connection objects
        connection_objects = []
        for conn_data in subprocess_connections:
            if isinstance(conn_data, dict):
                conn = ConnectionModel(
                    id=conn_data.get('id'),
                    type=conn_data.get('type', 'sequenceFlow'),
                    name=conn_data.get('name', ''),
                    **{'from': conn_data.get('from')},
                    to=conn_data.get('to'),
                    properties=conn_data.get('properties', {})
                )
            else:
                conn = conn_data

            connection_objects.append(conn)

        # Find start event in subprocess
        start_event = None
        for elem in elements_map.values():
            if elem.type == 'startEvent':
                start_event = elem
                break

        if not start_event:
            logger.error(f"Subprocess {subprocess_name} has no start event")
            raise ValueError(f"Subprocess {subprocess_name} requires a start event")

        # Create a temporary mini-workflow structure for element lookup
        # Store original workflow and temporarily replace
        original_workflow = self.workflow

        # Create mini workflow with proper objects
        mini_workflow = {
            'process': {
                'id': subprocess_id,
                'name': subprocess_name,
                'elements': element_objects,
                'connections': connection_objects,
                'pools': []
            }
        }

        # Temporarily replace workflow (for get_outgoing_elements, etc.)
        from models import Workflow as WorkflowModel
        self.workflow = WorkflowModel(**mini_workflow)

        # Execute subprocess from start event
        # Store original context and use subprocess context
        original_context = self.context
        self.context = context.copy()

        try:
            # Execute the subprocess flow
            await self.execute_from_element(start_event)

            # The context has been updated by the subprocess execution
            # Return the updated context
            logger.info(f"🔹 Subprocess {subprocess_name} completed successfully")
            logger.info(f"🔹 Updated context keys: {list(self.context.keys())}")

            # Return the updated context (which is self.context after execution)
            result_context = self.context.copy()

        except Exception as e:
            logger.error(f"Subprocess {subprocess_name} execution failed: {e}", exc_info=True)
            raise

        finally:
            # Restore original workflow and context
            self.workflow = original_workflow
            self.context = original_context

        logger.info(f"🔹 ======================================== (END SUBPROCESS)")

        return result_context

    async def execute_task_with_boundary_events(self, task: Element) -> bool:
        """Execute a task with error and timer boundary event support

        Returns:
            True if task was cancelled by an interrupting boundary event, False otherwise
        """
        # Find any boundary events attached to this task
        logger.info(f"🔍 Checking for boundary events on task {task.id}")

        error_boundaries = [
            e for e in self.workflow.process.elements
            if e.type == 'errorBoundaryEvent' and e.attachedToRef == task.id
        ]
        timer_boundaries = [
            e for e in self.workflow.process.elements
            if e.type == 'timerBoundaryEvent' and e.attachedToRef == task.id
        ]

        logger.info(f"🔍 Found {len(error_boundaries)} error boundaries, {len(timer_boundaries)} timer boundaries")

        # If no boundary events, execute normally
        if not error_boundaries and not timer_boundaries:
            logger.info(f"🔍 No boundary events found for {task.id}, executing normally")
            await self.execute_task(task)
            return False

        # If only error boundaries (no timers), wrap with try-catch
        if error_boundaries and not timer_boundaries:
            await self.execute_task_with_error_boundaries(task, error_boundaries)
            return False  # Error boundaries don't cancel the normal flow in this implementation

        # If only timer boundaries (no error handlers), use timer wrapping
        if timer_boundaries and not error_boundaries:
            was_cancelled = await self.execute_task_with_timer_boundaries(task, timer_boundaries)
            return was_cancelled

        # If both error and timer boundaries, combine them
        was_cancelled = await self.execute_task_with_combined_boundaries(task, error_boundaries, timer_boundaries)
        return was_cancelled

    async def execute_task_with_error_boundaries(self, task: Element, error_boundaries: List[Element]):
        """Execute task with error boundary event support"""
        try:
            # Execute the task normally
            await self.execute_task(task)
            # Task completed successfully
            logger.info(f"✅ Task {task.name} completed successfully (no errors)")

        except asyncio.CancelledError:
            # Task was cancelled - re-raise without catching
            logger.info(f"🛑 Task {task.id} ({task.name}) was cancelled")
            raise

        except Exception as e:
            logger.error(f"❌ Task {task.name} failed with error: {type(e).__name__}: {e}")

            # Check if any boundary event catches this error
            for boundary in error_boundaries:
                error_code = boundary.properties.get('errorCode', '')
                cancel_activity = boundary.properties.get('cancelActivity', True)

                # Empty error code catches all errors
                # Otherwise check if exception type matches
                error_type = type(e).__name__
                if not error_code or error_type == error_code or str(e).find(error_code) >= 0:
                    logger.info(f"🎯 Error caught by boundary event: {boundary.name}")
                    logger.info(f"   Error type: {error_type}")
                    logger.info(f"   Boundary catches: {'all errors' if not error_code else error_code}")

                    # Send boundary event triggered
                    await self.agui_server.send_element_activated(
                        boundary.id,
                        boundary.type,
                        f"{boundary.name} (caught {error_type})"
                    )

                    # Add error info to context
                    self.context[f'{boundary.id}_errorType'] = error_type
                    self.context[f'{boundary.id}_errorMessage'] = str(e)

                    # Mark boundary event as completed
                    await self.agui_server.send_element_completed(boundary.id, 0)

                    # Follow boundary event's outgoing flow
                    next_elements = self.workflow.get_outgoing_elements(boundary)
                    if next_elements:
                        logger.info(f"➡️  Following error boundary flow to: {[e.name for e in next_elements]}")
                        for elem in next_elements:
                            await self.execute_from_element(elem)

                    return  # Error handled, don't propagate

            # No boundary caught the error - re-raise
            logger.error(f"❌ No error boundary event caught {error_type} - re-raising")
            raise

    async def execute_task_with_timer_boundaries(self, task: Element, timer_boundaries: List[Element]) -> bool:
        """Execute task with timer boundary event support

        Returns:
            True if task was cancelled by an interrupting boundary event, False otherwise
        """
        # Create task future
        task_future = asyncio.create_task(self.execute_task(task))

        # Create timer futures
        timer_futures = []
        for boundary in timer_boundaries:
            duration_str = boundary.properties.get('timerDuration', 'PT30S')
            duration_seconds = self.parse_iso8601_duration(duration_str)
            timer_future = asyncio.create_task(asyncio.sleep(duration_seconds))
            timer_futures.append((timer_future, boundary, duration_seconds))
            logger.info(f"⏰ Timer boundary event '{boundary.name}' set for {duration_seconds}s")

        # Wait for first to complete
        all_futures = [task_future] + [t[0] for t in timer_futures]
        done, pending = await asyncio.wait(all_futures, return_when=asyncio.FIRST_COMPLETED)

        # Check what completed
        if task_future in done:
            # Task completed before timeout
            logger.info(f"✅ Task {task.name} completed before timer")
            for timer_future, _, _ in timer_futures:
                timer_future.cancel()
            return False  # Task completed normally

        # Timer expired - handle all timers that fire
        while True:
            # Find which timer(s) completed
            completed_timer = None
            for timer_future, boundary, duration in timer_futures:
                if timer_future in done:
                    completed_timer = (timer_future, boundary, duration)
                    break

            if not completed_timer:
                break

            timer_future, boundary, duration = completed_timer
            cancel_activity = boundary.properties.get('cancelActivity', True)

            logger.info(f"⏰ Timer boundary event '{boundary.name}' triggered after {duration}s")

            if cancel_activity:
                # Cancel the task
                task_future.cancel()
                logger.info(f"🛑 Task {task.name} cancelled by timer {boundary.name}")

            # Send boundary event triggered
            await self.agui_server.send_element_activated(
                boundary.id,
                boundary.type,
                f"{boundary.name} (timeout after {duration}s)"
            )

            # Mark boundary event as completed
            await self.agui_server.send_element_completed(boundary.id, 0)

            # Follow boundary flow
            next_elements = self.workflow.get_outgoing_elements(boundary)
            if next_elements:
                logger.info(f"➡️  Following timer boundary flow to: {[e.name for e in next_elements]}")
                for elem in next_elements:
                    await self.execute_from_element(elem)

            if cancel_activity:
                # Interrupting boundary event - cancel all other timers and stop
                logger.info(f"🛑 Interrupting boundary event - cancelling remaining timers")
                for other_timer, _, _ in timer_futures:
                    if other_timer != timer_future:
                        other_timer.cancel()
                return True  # Task was cancelled

            # Non-interrupting boundary event - continue waiting for task or other timers
            logger.info(f"⏭️  Non-interrupting boundary event - task continues, waiting for completion or other timers")

            # Remove the completed timer from the list
            timer_futures = [(tf, b, d) for tf, b, d in timer_futures if tf != timer_future]

            if not timer_futures:
                # No more timers, just wait for task
                try:
                    await task_future
                    logger.info(f"✅ Task {task.name} completed after non-interrupting timer")
                    return False
                except asyncio.CancelledError:
                    logger.info(f"🛑 Task was cancelled")
                    raise

            # Wait for next timer or task completion
            remaining_futures = [task_future] + [t[0] for t in timer_futures]
            done, pending = await asyncio.wait(remaining_futures, return_when=asyncio.FIRST_COMPLETED)

            # Check if task completed
            if task_future in done:
                logger.info(f"✅ Task {task.name} completed before remaining timers")
                for timer_future, _, _ in timer_futures:
                    timer_future.cancel()
                return False  # Task completed normally

        return False  # Should never reach here, but default to not cancelled

    async def execute_task_with_combined_boundaries(self, task: Element, error_boundaries: List[Element], timer_boundaries: List[Element]) -> bool:
        """Execute task with both error and timer boundary events

        Returns:
            True if task was cancelled by an interrupting boundary event, False otherwise
        """
        try:
            # Execute with timer boundaries (which includes error handling internally)
            was_cancelled = await self.execute_task_with_timer_boundaries(task, timer_boundaries)
            return was_cancelled
        except Exception as e:
            # If an error occurs, check error boundaries
            await self.execute_task_with_error_boundaries(task, error_boundaries)
            return False  # Error boundaries don't cancel the normal flow in this implementation

    def parse_iso8601_duration(self, duration_str: str) -> float:
        """Parse ISO 8601 duration string to seconds"""
        # Simple parser for common durations: PT30S, PT5M, PT1H, P1D
        # P = Period, T = Time separator
        # S = seconds, M = minutes, H = hours, D = days

        if not duration_str.startswith('P'):
            logger.warning(f"Invalid duration format: {duration_str}, using 30s default")
            return 30.0

        duration_str = duration_str[1:]  # Remove 'P'
        total_seconds = 0.0

        if 'T' in duration_str:
            # Has time component
            parts = duration_str.split('T')
            date_part = parts[0] if len(parts) > 0 else ''
            time_part = parts[1] if len(parts) > 1 else ''

            # Parse date part (days)
            if 'D' in date_part:
                days = float(date_part.replace('D', ''))
                total_seconds += days * 24 * 3600

            # Parse time part
            if 'H' in time_part:
                hours_str = time_part.split('H')[0]
                hours = float(hours_str)
                total_seconds += hours * 3600
                time_part = time_part.split('H')[1] if 'H' in time_part else ''

            if 'M' in time_part:
                minutes_str = time_part.split('M')[0]
                minutes = float(minutes_str)
                total_seconds += minutes * 60
                time_part = time_part.split('M')[1] if 'M' in time_part else ''

            if 'S' in time_part:
                seconds_str = time_part.replace('S', '')
                if seconds_str:
                    seconds = float(seconds_str)
                    total_seconds += seconds

        else:
            # Only date part (days)
            if 'D' in duration_str:
                days = float(duration_str.replace('D', ''))
                total_seconds = days * 24 * 3600

        logger.info(f"Parsed duration '{duration_str}' = {total_seconds} seconds")
        return total_seconds if total_seconds > 0 else 30.0  # Default 30s


async def execute_workflow_from_file(yaml_file: str, agui_server: AGUIServer, context: Dict[str, Any] = None, mcp_client=None):
    """Execute a workflow from a YAML file"""
    logger.info(f"Loading workflow from: {yaml_file}")

    # Load YAML file
    with open(yaml_file, 'r') as f:
        yaml_content = f.read()

    # Create engine with filename for logging and MCP client
    engine = WorkflowEngine(yaml_content, agui_server, mcp_client=mcp_client, workflow_file=yaml_file)

    # Execute
    await engine.start_execution(context or {})

    return engine.instance_id
