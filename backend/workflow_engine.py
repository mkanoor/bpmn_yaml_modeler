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


class EventSubProcessHandledError(Exception):
    """
    Special exception to signal that an error was successfully handled
    by an Event Sub-Process. This prevents error logging while still
    allowing the interrupting subprocess to cancel the main flow.
    """
    def __init__(self, subprocess_name: str, original_error: Exception):
        self.subprocess_name = subprocess_name
        self.original_error = original_error
        super().__init__(f"Error handled by Event Sub-Process: {subprocess_name}")


class WorkflowEngine:
    """Main orchestrator for workflow execution"""

    def __init__(self, yaml_content: str, agui_server: AGUIServer, mcp_client=None, workflow_file: str = None):
        self.workflow = self.parse_yaml(yaml_content)
        self.agui_server = agui_server
        self.mcp_client = mcp_client
        self.workflow_file = workflow_file  # Store filename for logging

        # Extract subprocess definitions if present
        self.subprocess_definitions = self.workflow.process.subprocess_definitions
        if self.subprocess_definitions:
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
        # Track completed tasks with compensation handlers (key: task_id, value: compensation_boundary_element)
        self.compensation_handlers: Dict[str, Element] = {}
        # Track event sub-processes and their monitoring tasks
        self.event_subprocess_tasks: Dict[str, asyncio.Task] = {}  # key: subprocess_id, value: monitor task
        self.event_subprocess_triggered: Dict[str, bool] = {}  # key: subprocess_id, value: triggered flag

    def parse_yaml(self, yaml_content: str) -> Workflow:
        """Parse YAML into workflow object model"""
        try:
            data = yaml.safe_load(yaml_content)

            # Debug: Check Event Sub-Process elements in raw YAML
            for elem in data.get('process', {}).get('elements', []):
                if elem.get('type') == 'eventSubProcess':
                    logger.info(f"🔍 Found Event Sub-Process in YAML: {elem.get('name')}")
                    logger.info(f"   childElements in YAML: {elem.get('childElements') is not None}")
                    logger.info(f"   Number of childElements in YAML: {len(elem.get('childElements', []))}")

            workflow = Workflow(**data)

            # Debug: Check Event Sub-Process elements after Pydantic parsing
            for elem in workflow.process.elements:
                if elem.type == 'eventSubProcess':
                    logger.info(f"🔍 After Pydantic parsing: {elem.name}")
                    logger.info(f"   childElements after parsing: {elem.childElements is not None}")
                    logger.info(f"   Number of childElements after parsing: {len(elem.childElements) if elem.childElements else 0}")

            return workflow
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
            # Start monitoring Event Sub-Processes
            await self.start_event_subprocesses()

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

        except EventSubProcessHandledError as e:
            # Error was handled by Event Sub-Process - this is a success
            logger.info(f"✅ Workflow completed via Event Sub-Process: {e.subprocess_name}")
            logger.info(f"   Original error: {type(e.original_error).__name__}: {e.original_error}")

            # Broadcast as successful (error was handled)
            duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            await self.agui_server.send_workflow_completed(
                self.instance_id,
                'success',  # Success because error was handled
                duration
            )

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

        except EventSubProcessHandledError as e:
            # Error was handled by Event Sub-Process - log success, not error
            logger.info(f"✅ {element.name} error handled by: {e.subprocess_name}")
            # Re-raise to stop execution path (for interrupting subprocesses)
            # DO NOT send task.error event - this is a successful recovery
            raise

        except Exception as e:
            # Only log and send error events for REAL errors (not handled ones)
            # Double-check: don't send task.error if this is a handled error
            if not isinstance(e, EventSubProcessHandledError):
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

    async def execute_multi_instance_task(self, task: Element):
        """Execute a multi-instance task (loop over collection)"""
        props = task.properties or {}

        # Get multi-instance configuration
        is_sequential = props.get('isSequential', False)
        input_collection_name = props.get('inputCollection')
        input_element_name = props.get('inputElement', 'item')
        output_collection_name = props.get('outputCollection')
        output_element_name = props.get('outputElement', 'result')

        if not input_collection_name:
            logger.error(f"Multi-instance task {task.name} missing inputCollection property")
            return

        # Get the collection from context
        collection = self.context.get(input_collection_name, [])
        if not isinstance(collection, (list, tuple)):
            logger.error(f"Input collection '{input_collection_name}' is not a list/tuple")
            return

        logger.info(f"🔄 Executing multi-instance task: {task.name}")
        logger.info(f"   Collection: {input_collection_name} ({len(collection)} items)")
        logger.info(f"   Mode: {'Sequential' if is_sequential else 'Parallel'}")

        results = []

        if is_sequential:
            # Sequential execution - one after another
            for idx, item in enumerate(collection):
                logger.info(f"   Instance {idx + 1}/{len(collection)}: Processing {input_element_name}")

                # Create instance-specific context
                instance_context = self.context.copy()
                instance_context[input_element_name] = item
                instance_context['loopCounter'] = idx
                instance_context['nrOfInstances'] = len(collection)
                instance_context['nrOfCompletedInstances'] = idx
                instance_context['nrOfActiveInstances'] = 1

                # Save current context, execute with instance context
                original_context = self.context
                self.context = instance_context

                try:
                    # Execute the task body (not execute_task to avoid recursion)
                    await self.execute_task_body(task)

                    # Collect output if specified
                    if output_element_name and output_element_name in self.context:
                        results.append(self.context[output_element_name])
                finally:
                    # Restore original context
                    self.context = original_context

                logger.info(f"   Instance {idx + 1} completed")

        else:
            # Parallel execution - all at once
            async def execute_instance(idx, item):
                """Execute a single instance of the multi-instance task"""
                logger.info(f"   Instance {idx + 1}/{len(collection)}: Processing {input_element_name}")

                # Create instance-specific context
                instance_context = self.context.copy()
                instance_context[input_element_name] = item
                instance_context['loopCounter'] = idx
                instance_context['nrOfInstances'] = len(collection)
                instance_context['nrOfActiveInstances'] = len(collection)

                # Execute with instance context WITHOUT modifying self.context
                # This prevents race conditions when running in parallel
                try:
                    # Get executor for task type
                    executor = self.task_executors.get_executor(task.type)

                    # Execute task directly with instance context (not self.context)
                    async for progress in executor.execute(task, instance_context):
                        # Broadcast progress to UI
                        await self.agui_server.send_task_progress(
                            task.id,
                            progress.progress,
                            progress.status,
                            progress.message
                        )

                    # Collect output if specified
                    if output_element_name and output_element_name in instance_context:
                        return instance_context[output_element_name]
                    else:
                        return None

                except Exception as e:
                    logger.error(f"   Instance {idx + 1} failed: {e}")
                    raise

            # Create tasks for all instances
            tasks = [execute_instance(idx, item) for idx, item in enumerate(collection)]

            # Execute all in parallel
            logger.info(f"   Executing {len(tasks)} instances in parallel...")
            instance_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Collect results (filter out None and exceptions)
            for idx, result in enumerate(instance_results):
                if isinstance(result, Exception):
                    logger.error(f"   Instance {idx + 1} failed: {result}")
                    results.append({'error': str(result), 'instance': idx})
                elif result is not None:
                    results.append(result)

        # Store collected results in output collection
        if output_collection_name:
            self.context[output_collection_name] = results
            logger.info(f"✅ Multi-instance complete: {len(results)} results stored in {output_collection_name}")

    async def execute_standard_loop_task(self, task: Element):
        """Execute a task with standard loop (repeat until condition is false)"""
        props = task.properties or {}

        loop_condition = props.get('loopCondition')
        loop_maximum = props.get('loopMaximum', 100)  # Safety limit

        logger.info(f"🔁 Executing standard loop task: {task.name}")
        logger.info(f"   Condition: {loop_condition}")
        logger.info(f"   Maximum iterations: {loop_maximum}")

        loop_counter = 0

        while loop_counter < loop_maximum:
            logger.info(f"   Loop iteration {loop_counter + 1}")

            # Add loop counter to context
            self.context['loopCounter'] = loop_counter

            # Execute the task
            await self.execute_task_body(task)

            # Increment counter
            loop_counter += 1

            # Evaluate loop condition
            if loop_condition:
                # Use gateway evaluator to evaluate the condition
                evaluator = GatewayEvaluator(self.workflow)
                should_continue = evaluator.evaluate_condition(loop_condition, self.context)

                logger.info(f"   Loop condition evaluated to: {should_continue}")

                if not should_continue:
                    logger.info(f"   Loop condition false - exiting after {loop_counter} iterations")
                    break
            else:
                # No condition means execute once
                logger.info(f"   No loop condition - executed once")
                break

        logger.info(f"✅ Standard loop complete: {loop_counter} iterations")

    async def execute_task_body(self, task: Element):
        """Execute the actual task body (without multi-instance or loop checks)"""
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

        except Exception as e:
            # Check if there's an error Event Sub-Process that can handle this
            error_subprocess = await self.check_and_trigger_error_subprocess(e)

            if error_subprocess:
                # Error was caught by Event Sub-Process
                logger.info(f"✅ Error handled by Event Sub-Process: {error_subprocess.name}")
                # Remove from tracking before Event Sub-Process executes
                if task.id in self.active_tasks:
                    del self.active_tasks[task.id]
                if task.id in self.running_tasks:
                    del self.running_tasks[task.id]

                # Raise special exception to signal error was handled
                # This allows interrupting subprocesses to cancel the main flow
                # without logging errors
                raise EventSubProcessHandledError(error_subprocess.name, e)
            else:
                # No Event Sub-Process to handle this error - re-raise
                raise

        finally:
            # Remove from active tasks
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]

    async def execute_task(self, task: Element):
        """Execute a task using appropriate executor"""
        # Check if this is a multi-instance task
        if task.properties and task.properties.get('isMultiInstance'):
            return await self.execute_multi_instance_task(task)

        # Check if this is a standard loop task
        if task.properties and task.properties.get('loopCondition'):
            return await self.execute_standard_loop_task(task)

        # Regular task execution
        await self.execute_task_body(task)

        # Check if this was a user task that was rejected
        if task.type == 'userTask':
            decision = self.context.get(f'{task.id}_decision')
            if decision == 'rejected':
                logger.warning(f"User task {task.name} was rejected, will continue workflow to handle rejection")
                # Don't raise exception - let workflow continue so rejection can be handled
                # The rejection decision is already in context as {task.id}_decision

        logger.info(f"Task completed: {task.name}")

    def get_expected_parallel_paths(self, join_gateway: Element, incoming) -> int:
        """
        Find the matching parallel fork gateway and count how many paths it created.
        This is needed because boundary event handlers add extra incoming connections to the join,
        but we should only wait for the number of paths created by the fork.
        """
        # Walk backwards from incoming connections to find the parallel fork
        # The fork is the parallel gateway that has multiple outgoing connections
        # and leads to this join gateway

        visited = set()
        fork_candidates = []

        def find_fork_backwards(element_id, depth=0):
            if depth > 10 or element_id in visited:  # Prevent infinite loops
                return
            visited.add(element_id)

            # Get the element
            element = None
            for elem in self.workflow.process.elements:
                if elem.id == element_id:
                    element = elem
                    break

            if not element:
                return

            # If this is a parallel gateway with multiple outgoing connections, it might be the fork
            if element.type == 'parallelGateway':
                outgoing = self.workflow.get_outgoing_connections(element)
                if len(outgoing) > 1:
                    fork_candidates.append((element, len(outgoing), depth))
                    logger.info(f"Found parallel fork candidate: {element.id} with {len(outgoing)} outgoing paths (depth {depth})")

            # Continue walking backwards
            incoming_to_element = self.workflow.get_incoming_connections(element)
            for conn in incoming_to_element:
                find_fork_backwards(conn.from_, depth + 1)

        # Start from all incoming connections to the join
        for conn in incoming:
            find_fork_backwards(conn.from_)

        # Use the fork with the most outgoing paths and closest depth (most likely match)
        if fork_candidates:
            # Sort by number of outgoing paths (desc), then by depth (asc)
            fork_candidates.sort(key=lambda x: (-x[1], x[2]))
            fork, num_paths, depth = fork_candidates[0]
            logger.info(f"Using fork {fork.id} ({fork.name}) with {num_paths} outgoing paths")
            return num_paths

        # Fallback: use incoming connection count (old behavior)
        logger.warning(f"Could not find matching fork for join {join_gateway.id}, using incoming count")
        return len(incoming)

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
                    # Parallel merge: wait for all paths to arrive
                    logger.info(f"Parallel gateway merge - tracking arrivals")

                    # Get the current execution path identifier (use asyncio task id)
                    current_task_id = id(asyncio.current_task())
                    self.merge_arrivals[gateway.id]['elements'].add(current_task_id)

                    arrivals = len(self.merge_arrivals[gateway.id]['elements'])

                    # For parallel join, we need to find the matching fork gateway
                    # and count how many paths it created (not count incoming connections which may include boundary handlers)
                    expected = self.get_expected_parallel_paths(gateway, incoming)

                    logger.info(f"Parallel join {gateway.id}: {arrivals}/{expected} paths arrived")

                    if arrivals < expected:
                        # Not all paths have arrived yet - this path should wait/stop
                        logger.info(f"Parallel join {gateway.id}: Waiting for {expected - arrivals} more path(s) - stopping this path")
                        return []  # Stop this execution path
                    else:
                        # All paths have arrived - mark as completed and continue
                        logger.info(f"Parallel join {gateway.id}: All {expected} paths arrived - continuing")
                        self.merge_arrivals[gateway.id]['completed'] = True
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

        # Convert enum to string for comparison
        event_type_str = str(event.type).replace('ElementType.', '').replace('_', '')

        if event.type == 'startEvent' or event_type_str.lower() == 'startevent':
            # Start event - just pass through
            pass
        elif event.type == 'endEvent' or event_type_str.lower() == 'endevent':
            # End event - workflow path complete
            logger.info(f"Reached end event: {event.name}")
        elif event.type == 'intermediateEvent' or event_type_str.lower() == 'intermediateevent':
            # Intermediate event - might trigger actions
            pass
        elif event.type == 'compensationIntermediateThrowEvent' or event_type_str.lower() == 'compensationintermediatethrowevent':
            # Compensation throw event - trigger rollback of completed tasks
            logger.info(f"🔄 Compensation throw event detected - triggering rollback")
            await self.trigger_compensation(event)
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
        """Execute a task with error, timer, and compensation boundary event support

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
        compensation_boundaries = [
            e for e in self.workflow.process.elements
            if e.type == 'compensationBoundaryEvent' and e.attachedToRef == task.id
        ]

        logger.info(f"🔍 Found {len(error_boundaries)} error boundaries, {len(timer_boundaries)} timer boundaries, {len(compensation_boundaries)} compensation boundaries")

        # Register compensation handlers (they don't execute automatically - only when triggered)
        if compensation_boundaries:
            for comp_boundary in compensation_boundaries:
                logger.info(f"📋 Registering compensation handler for task {task.id}: {comp_boundary.name}")
                # Store compensation boundary for later triggering
                self.compensation_handlers[task.id] = comp_boundary

        # If no error/timer boundary events, execute normally
        if not error_boundaries and not timer_boundaries:
            logger.info(f"🔍 No error/timer boundaries found for {task.id}, executing normally")
            await self.execute_task(task)
            # Task completed successfully - compensation handler is now available if registered
            return False

        # If only error boundaries (no timers), wrap with try-catch
        if error_boundaries and not timer_boundaries:
            was_cancelled = await self.execute_task_with_error_boundaries(task, error_boundaries)
            return was_cancelled  # Return whether task was cancelled by interrupting error boundary

        # If only timer boundaries (no error handlers), use timer wrapping
        if timer_boundaries and not error_boundaries:
            was_cancelled = await self.execute_task_with_timer_boundaries(task, timer_boundaries)
            return was_cancelled

        # If both error and timer boundaries, combine them
        was_cancelled = await self.execute_task_with_combined_boundaries(task, error_boundaries, timer_boundaries)
        return was_cancelled

    async def execute_task_with_error_boundaries(self, task: Element, error_boundaries: List[Element]) -> bool:
        """Execute task with error boundary event support

        Returns:
            True if task was cancelled by an interrupting error boundary, False otherwise
        """
        try:
            # Execute the task normally
            await self.execute_task(task)
            # Task completed successfully
            logger.info(f"✅ Task {task.name} completed successfully (no errors)")
            return False  # Task completed without error

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

                    # Return True if interrupting, False if non-interrupting
                    if cancel_activity:
                        logger.info(f"🛑 Interrupting error boundary - task cancelled, normal flow will NOT continue")
                        return True  # Task was cancelled, don't continue normal flow
                    else:
                        logger.info(f"⏭️  Non-interrupting error boundary - task continues, normal flow will continue")
                        return False  # Task continues, normal flow continues

            # No boundary caught the error - check if Event Sub-Process can handle it
            logger.info(f"❌ No error boundary event caught {error_type}")

            # Check if there's an error Event Sub-Process that can handle this
            error_subprocess = await self.check_and_trigger_error_subprocess(e)

            if error_subprocess:
                # Error was caught by Event Sub-Process
                logger.info(f"✅ Error handled by Event Sub-Process: {error_subprocess.name}")
                # Raise special exception to signal error was handled
                raise EventSubProcessHandledError(error_subprocess.name, e)
            else:
                # No Event Sub-Process to handle this error - re-raise
                logger.error(f"❌ No Event Sub-Process found to handle error - re-raising")
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

    async def trigger_compensation(self, throw_event: Element):
        """Trigger compensation for all completed tasks with compensation handlers

        This executes compensation flows in REVERSE order (LIFO - last in, first out)
        to properly undo/rollback transactions.
        """
        logger.info(f"🔄 ========================================")
        logger.info(f"🔄 COMPENSATION TRIGGERED by: {throw_event.name}")
        logger.info(f"🔄 Registered compensation handlers: {list(self.compensation_handlers.keys())}")
        logger.info(f"🔄 ========================================")

        if not self.compensation_handlers:
            logger.warning(f"⚠️  No compensation handlers registered - nothing to compensate")
            return

        # Execute compensation handlers in REVERSE order (LIFO)
        # This ensures proper rollback order: last completed task is compensated first
        task_ids = list(self.compensation_handlers.keys())
        task_ids.reverse()

        for task_id in task_ids:
            comp_boundary = self.compensation_handlers[task_id]
            logger.info(f"🔄 Triggering compensation for task {task_id}: {comp_boundary.name}")

            # Activate the compensation boundary event
            await self.agui_server.send_element_activated(
                comp_boundary.id,
                comp_boundary.type,
                f"{comp_boundary.name} (compensating {task_id})"
            )

            # Mark boundary event as completed
            await self.agui_server.send_element_completed(comp_boundary.id, 0)

            # Follow the compensation flow (execute the undo/rollback tasks)
            next_elements = self.workflow.get_outgoing_elements(comp_boundary)
            if next_elements:
                logger.info(f"➡️  Following compensation flow to: {[e.name for e in next_elements]}")
                for elem in next_elements:
                    await self.execute_from_element(elem)
            else:
                logger.warning(f"⚠️  Compensation boundary {comp_boundary.name} has no outgoing flow")

        logger.info(f"🔄 ======================================== (END COMPENSATION)")

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

    async def start_event_subprocesses(self):
        """Start monitoring all Event Sub-Processes in the workflow"""
        # Find all Event Sub-Processes
        event_subprocesses = [
            elem for elem in self.workflow.process.elements
            if elem.type == 'eventSubProcess'
        ]

        if not event_subprocesses:
            logger.info("No Event Sub-Processes found in workflow")
            return

        logger.info(f"🎯 Found {len(event_subprocesses)} Event Sub-Process(es) to monitor")

        for subprocess in event_subprocesses:
            # Start monitoring this event subprocess
            monitor_task = asyncio.create_task(
                self.monitor_event_subprocess(subprocess)
            )
            self.event_subprocess_tasks[subprocess.id] = monitor_task
            logger.info(f"🎯 Started monitoring Event Sub-Process: {subprocess.name} (id: {subprocess.id})")

    async def monitor_event_subprocess(self, subprocess: Element):
        """Monitor an Event Sub-Process for its triggering event"""
        logger.info(f"📡 Monitoring Event Sub-Process: {subprocess.name}")

        # Get properties
        props = subprocess.properties or {}
        is_interrupting = props.get('isInterrupting', True)

        # Find the start event within this subprocess
        start_event = None
        if subprocess.childElements:
            for child in subprocess.childElements:
                if child.type in ['errorStartEvent', 'timerStartEvent', 'messageStartEvent',
                                  'signalStartEvent', 'escalationStartEvent', 'compensationStartEvent']:
                    start_event = child
                    break

        if not start_event:
            logger.warning(f"Event Sub-Process {subprocess.name} has no event start event")
            return

        logger.info(f"📡 Event Sub-Process {subprocess.name} triggered by: {start_event.type}")

        # Monitor based on event type
        try:
            if start_event.type == 'timerStartEvent':
                await self.monitor_timer_start_event(subprocess, start_event, is_interrupting)
            elif start_event.type == 'errorStartEvent':
                await self.monitor_error_start_event(subprocess, start_event, is_interrupting)
            elif start_event.type == 'messageStartEvent':
                await self.monitor_message_start_event(subprocess, start_event, is_interrupting)
            elif start_event.type == 'signalStartEvent':
                await self.monitor_signal_start_event(subprocess, start_event, is_interrupting)
            elif start_event.type == 'escalationStartEvent':
                await self.monitor_escalation_start_event(subprocess, start_event, is_interrupting)
            else:
                logger.warning(f"Unsupported event type for Event Sub-Process: {start_event.type}")

        except asyncio.CancelledError:
            logger.info(f"🛑 Event Sub-Process monitoring cancelled: {subprocess.name}")
            raise
        except Exception as e:
            logger.error(f"Error monitoring Event Sub-Process {subprocess.name}: {e}", exc_info=True)

    async def monitor_timer_start_event(self, subprocess: Element, start_event: Element, is_interrupting: bool):
        """Monitor a timer start event for Event Sub-Process"""
        props = start_event.properties or {}
        duration_str = props.get('timerDuration', 'PT30S')
        duration_seconds = self.parse_iso8601_duration(duration_str)

        logger.info(f"⏰ Timer Event Sub-Process will trigger in {duration_seconds}s")

        # Wait for timer
        await asyncio.sleep(duration_seconds)

        logger.info(f"⏰ Timer Event Sub-Process triggered: {subprocess.name}")

        # Execute the subprocess
        await self.trigger_event_subprocess(subprocess, start_event, is_interrupting, {
            'trigger_type': 'timer',
            'duration': duration_seconds
        })

    async def monitor_error_start_event(self, subprocess: Element, start_event: Element, is_interrupting: bool):
        """Monitor for errors that should trigger this Event Sub-Process"""
        # This is passive monitoring - errors will be caught in execute_task_with_error_boundaries
        # and will call trigger_event_subprocess directly
        logger.info(f"🔴 Error Event Sub-Process ready to catch errors: {subprocess.name}")

        # Wait indefinitely until cancelled or triggered
        try:
            while not self.event_subprocess_triggered.get(subprocess.id, False):
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise

    async def monitor_message_start_event(self, subprocess: Element, start_event: Element, is_interrupting: bool):
        """Monitor for messages that should trigger this Event Sub-Process"""
        props = start_event.properties or {}
        message_ref = props.get('messageRef', '')

        logger.info(f"📨 Message Event Sub-Process waiting for message: {message_ref}")

        # Poll context for message arrival
        try:
            while True:
                # Check if message has arrived in context
                message_key = f'message_{message_ref}_received'
                if self.context.get(message_key, False):
                    logger.info(f"📨 Message received, triggering Event Sub-Process: {subprocess.name}")

                    await self.trigger_event_subprocess(subprocess, start_event, is_interrupting, {
                        'trigger_type': 'message',
                        'message_ref': message_ref,
                        'message_data': self.context.get(f'message_{message_ref}_data', {})
                    })
                    break

                await asyncio.sleep(0.5)  # Poll every 500ms
        except asyncio.CancelledError:
            raise

    async def monitor_signal_start_event(self, subprocess: Element, start_event: Element, is_interrupting: bool):
        """Monitor for signals that should trigger this Event Sub-Process"""
        props = start_event.properties or {}
        signal_ref = props.get('signalRef', '')

        logger.info(f"📡 Signal Event Sub-Process waiting for signal: {signal_ref}")

        # Poll context for signal
        try:
            while True:
                signal_key = f'signal_{signal_ref}_triggered'
                if self.context.get(signal_key, False):
                    logger.info(f"📡 Signal received, triggering Event Sub-Process: {subprocess.name}")

                    await self.trigger_event_subprocess(subprocess, start_event, is_interrupting, {
                        'trigger_type': 'signal',
                        'signal_ref': signal_ref,
                        'signal_data': self.context.get(f'signal_{signal_ref}_data', {})
                    })
                    break

                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            raise

    async def monitor_escalation_start_event(self, subprocess: Element, start_event: Element, is_interrupting: bool):
        """Monitor for escalations that should trigger this Event Sub-Process"""
        props = start_event.properties or {}
        escalation_code = props.get('escalationCode', '')

        logger.info(f"🔺 Escalation Event Sub-Process waiting for escalation: {escalation_code}")

        # Poll context for escalation
        try:
            while True:
                escalation_key = f'escalation_{escalation_code}_triggered'
                if self.context.get(escalation_key, False):
                    logger.info(f"🔺 Escalation received, triggering Event Sub-Process: {subprocess.name}")

                    await self.trigger_event_subprocess(subprocess, start_event, is_interrupting, {
                        'trigger_type': 'escalation',
                        'escalation_code': escalation_code,
                        'escalation_data': self.context.get(f'escalation_{escalation_code}_data', {})
                    })
                    break

                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            raise

    async def check_and_trigger_error_subprocess(self, error: Exception) -> Optional[Element]:
        """Check if there's an error Event Sub-Process that can handle this error, and trigger it"""
        logger.info(f"🔍 Checking for error Event Sub-Process to handle: {type(error).__name__}: {str(error)}")

        # Find all error Event Sub-Processes
        error_subprocesses = [
            elem for elem in self.workflow.process.elements
            if elem.type == 'eventSubProcess'
        ]

        logger.info(f"🔍 Found {len(error_subprocesses)} Event Sub-Process(es) in workflow")

        for subprocess in error_subprocesses:
            logger.info(f"🔍 Checking Event Sub-Process: {subprocess.name} (id: {subprocess.id})")
            logger.info(f"   Has childElements: {subprocess.childElements is not None}")
            logger.info(f"   Number of childElements: {len(subprocess.childElements) if subprocess.childElements else 0}")

            if not subprocess.childElements:
                logger.info(f"   ⚠️ Skipping - no childElements")
                continue

            # Find the start event
            logger.info(f"   Child element types: {[e.type for e in subprocess.childElements]}")
            start_events = [e for e in subprocess.childElements if e.type == 'errorStartEvent']
            logger.info(f"   Found {len(start_events)} errorStartEvent(s)")

            if not start_events:
                logger.info(f"   ⚠️ Skipping - no errorStartEvent found")
                continue

            start_event = start_events[0]
            props = start_event.properties or {}
            error_code = props.get('errorCode', '')

            logger.info(f"   Error code filter: '{error_code}' (empty = catch all)")
            logger.info(f"   Error message: '{str(error)}'")
            logger.info(f"   Match check: error_code=='' is {error_code == ''}, '{error_code}' in '{str(error)}' is {error_code in str(error)}")

            # Check if this subprocess can handle this error
            # Empty error code = catch all errors
            # Otherwise check if error message contains the error code
            if error_code == '' or error_code in str(error):
                logger.info(f"✅ Found matching error Event Sub-Process: {subprocess.name}")

                # Get interrupting flag
                is_interrupting = subprocess.properties.get('isInterrupting', True)

                # Trigger the Event Sub-Process
                await self.trigger_event_subprocess(subprocess, start_event, is_interrupting, {
                    'trigger_type': 'error',
                    'error_type': type(error).__name__,
                    'error_message': str(error),
                    'error_code': error_code
                })

                return subprocess

        logger.info(f"❌ No error Event Sub-Process found to handle this error")
        return None

    async def trigger_event_subprocess(self, subprocess: Element, start_event: Element, is_interrupting: bool, trigger_data: Dict[str, Any]):
        """Trigger and execute an Event Sub-Process"""
        logger.info(f"🎯 ========================================")
        logger.info(f"🎯 Triggering EVENT SUB-PROCESS")
        logger.info(f"🎯 Subprocess: {subprocess.name} (id: {subprocess.id})")
        logger.info(f"🎯 Trigger: {trigger_data.get('trigger_type')}")
        logger.info(f"🎯 Interrupting: {is_interrupting}")
        logger.info(f"🎯 ========================================")

        # Mark as triggered
        self.event_subprocess_triggered[subprocess.id] = True

        # Add trigger data to context
        self.context[f'{subprocess.id}_trigger'] = trigger_data

        # If interrupting, store tasks to cancel AFTER subprocess execution
        tasks_to_cancel = {}
        if is_interrupting:
            logger.warning(f"⚠️  Interrupting Event Sub-Process - will cancel main process flow after recovery")
            # Store list of tasks to cancel (before subprocess execution adds its own tasks)
            tasks_to_cancel = dict(self.running_tasks.items())
            logger.info(f"📝 Stored {len(tasks_to_cancel)} tasks to cancel after Event Sub-Process completes")

        # Execute the subprocess
        if subprocess.childElements:
            # Find next element after start event
            next_elements = []
            if subprocess.childConnections:
                for conn in subprocess.childConnections:
                    if conn.from_ == start_event.id:
                        # Find the target element
                        for elem in subprocess.childElements:
                            if elem.id == conn.to:
                                next_elements.append(elem)

            # Create temporary workflow structure for subprocess execution
            from models import Workflow as WorkflowModel

            # Store original workflow
            original_workflow = self.workflow

            # Create mini workflow with subprocess elements
            mini_workflow = {
                'process': {
                    'id': subprocess.id,
                    'name': subprocess.name,
                    'elements': subprocess.childElements,
                    'connections': subprocess.childConnections or [],
                    'pools': []
                }
            }

            self.workflow = WorkflowModel(**mini_workflow)

            # Execute subprocess elements
            try:
                for elem in next_elements:
                    await self.execute_from_element(elem)

                logger.info(f"🎯 Event Sub-Process completed: {subprocess.name}")
            finally:
                # Restore original workflow
                self.workflow = original_workflow

        # If interrupting, NOW cancel the main process tasks (after recovery is complete)
        if is_interrupting and tasks_to_cancel:
            logger.warning(f"🛑 Now cancelling {len(tasks_to_cancel)} main process tasks")
            for task_id, task in tasks_to_cancel.items():
                logger.info(f"🛑 Cancelling task {task_id}")
                task.cancel()

        logger.info(f"🎯 ======================================== (END EVENT SUB-PROCESS)")


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
