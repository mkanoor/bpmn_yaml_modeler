"""
Workflow Execution Engine
Main orchestrator for BPMN workflow execution
"""
import asyncio
import uuid
import yaml
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from models import Workflow, Element, ExecutionStatus
from task_executors import TaskExecutorRegistry
from gateway_evaluator import GatewayEvaluator
from agui_server import AGUIServer

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Main orchestrator for workflow execution"""

    def __init__(self, yaml_content: str, agui_server: AGUIServer, mcp_client=None):
        self.workflow = self.parse_yaml(yaml_content)
        self.agui_server = agui_server
        self.mcp_client = mcp_client

        # Initialize components
        self.task_executors = TaskExecutorRegistry(agui_server, mcp_client)
        self.gateway_evaluator = GatewayEvaluator(self.workflow, agui_server)

        # Instance state
        self.instance_id: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.context: Dict[str, Any] = {}

        # Merge point tracking for gateways (tracks which paths have arrived)
        # Key: gateway_id, Value: set of incoming element IDs that have arrived
        self.merge_arrivals: Dict[str, set] = {}
        # Lock for merge point synchronization
        self.merge_locks: Dict[str, asyncio.Lock] = {}

    def parse_yaml(self, yaml_content: str) -> Workflow:
        """Parse YAML into workflow object model"""
        try:
            data = yaml.safe_load(yaml_content)
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

        logger.info(f"Starting workflow execution: {self.instance_id}")

        # Broadcast workflow started
        await self.agui_server.send_workflow_started(
            self.instance_id,
            self.workflow.process.name
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

            if element.is_task():
                await self.execute_task(element)
            elif element.is_gateway():
                # Gateway evaluation returns the specific next elements to follow
                next_elements = await self.execute_gateway(element)
            elif element.is_event():
                await self.handle_event(element)
            else:
                logger.warning(f"Unknown element type: {element.type}")

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
                await asyncio.gather(*tasks)

        except Exception as e:
            logger.error(f"Error executing element {element.name}: {e}")
            await self.agui_server.send_task_error(element.id, e, retryable=False)
            raise

    async def execute_task(self, task: Element):
        """Execute a task using appropriate executor"""
        logger.info(f"Executing task: {task.name} (type: {task.type})")

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

        # Check if this was a user task that was rejected
        if task.type == 'userTask':
            decision = self.context.get(f'{task.id}_decision')
            if decision == 'rejected':
                logger.warning(f"User task {task.name} was rejected, stopping workflow")
                # Raise exception to stop workflow
                raise Exception(f"Workflow terminated: User task '{task.name}' was rejected")

        logger.info(f"Task completed: {task.name}")

    async def execute_gateway(self, gateway: Element):
        """Execute a gateway and return next element(s) to follow"""
        logger.info(f"Executing gateway: {gateway.name} (type: {gateway.type})")

        # Check if this is a merge point (multiple incoming connections)
        incoming = self.workflow.get_incoming_connections(gateway)

        if len(incoming) > 1:
            # This is a merge gateway - need to handle merge semantics
            logger.info(f"Gateway {gateway.id} is a merge point with {len(incoming)} incoming paths")

            # Get or create lock for this merge point
            if gateway.id not in self.merge_locks:
                self.merge_locks[gateway.id] = asyncio.Lock()

            async with self.merge_locks[gateway.id]:
                # Track which path arrived
                if gateway.id not in self.merge_arrivals:
                    self.merge_arrivals[gateway.id] = set()

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
                    if len(self.merge_arrivals[gateway.id]) > 0:
                        # Another path already passed through - this path should stop
                        logger.info(f"Inclusive gateway {gateway.id}: Another path already passed - stopping this path")
                        return []  # Return empty list to stop this path
                    else:
                        # First path to arrive - mark and continue
                        logger.info(f"Inclusive gateway {gateway.id}: First path to arrive - continuing")
                        self.merge_arrivals[gateway.id].add('first')

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


async def execute_workflow_from_file(yaml_file: str, agui_server: AGUIServer, context: Dict[str, Any] = None):
    """Execute a workflow from a YAML file"""
    logger.info(f"Loading workflow from: {yaml_file}")

    # Load YAML file
    with open(yaml_file, 'r') as f:
        yaml_content = f.read()

    # Create engine
    engine = WorkflowEngine(yaml_content, agui_server)

    # Execute
    await engine.start_execution(context or {})

    return engine.instance_id
