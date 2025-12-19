"""
Gateway Evaluator - Evaluates gateway conditions
"""
import re
import logging
from typing import List, Dict, Any

from models import Element, Workflow, Connection

logger = logging.getLogger(__name__)


class GatewayEvaluator:
    """Evaluates gateway conditions to determine flow"""

    def __init__(self, workflow: Workflow, agui_server=None):
        self.workflow = workflow
        self.agui_server = agui_server

    async def evaluate_gateway(self, gateway: Element, context: Dict[str, Any]) -> List[Element]:
        """Evaluate gateway and return next elements"""
        logger.info(f"Evaluating gateway: {gateway.name} ({gateway.type})")

        if gateway.type == 'exclusiveGateway':
            return await self.evaluate_exclusive_gateway(gateway, context)
        elif gateway.type == 'parallelGateway':
            return await self.evaluate_parallel_gateway(gateway, context)
        elif gateway.type == 'inclusiveGateway':
            return await self.evaluate_inclusive_gateway(gateway, context)
        else:
            raise ValueError(f"Unknown gateway type: {gateway.type}")

    async def evaluate_exclusive_gateway(self, gateway: Element, context: Dict[str, Any]) -> List[Element]:
        """Evaluate exclusive gateway (XOR) - one path taken"""
        outgoing_flows = self.workflow.get_outgoing_connections(gateway)

        # Notify UI
        if self.agui_server:
            await self.agui_server.send_gateway_evaluating(
                gateway.id,
                'exclusive',
                len(outgoing_flows)
            )

        # Evaluate each flow condition in order
        for flow in outgoing_flows:
            # Use explicit condition from properties, not the name
            condition = flow.properties.get('condition', '')

            # Empty condition means default path
            if condition == '':
                logger.info(f"Taking default path: {flow.id} (name: {flow.name})")
                if self.agui_server:
                    await self.agui_server.send_gateway_path_taken(gateway.id, flow.id, 'default')

                return [self.workflow.get_element_by_id(flow.to)]

            # Evaluate condition
            if self.evaluate_condition(condition, context):
                logger.info(f"Condition matched: {condition} (flow: {flow.id})")
                if self.agui_server:
                    await self.agui_server.send_gateway_path_taken(gateway.id, flow.id, condition)

                return [self.workflow.get_element_by_id(flow.to)]

        # No condition matched - this is an error
        raise Exception(f"No path matched for exclusive gateway {gateway.id}")

    async def evaluate_parallel_gateway(self, gateway: Element, context: Dict[str, Any]) -> List[Element]:
        """Evaluate parallel gateway (AND) - all paths taken"""
        outgoing_flows = self.workflow.get_outgoing_connections(gateway)

        # Notify UI
        if self.agui_server:
            await self.agui_server.send_gateway_evaluating(
                gateway.id,
                'parallel',
                len(outgoing_flows)
            )

        # All paths are taken in parallel
        target_elements = []
        for flow in outgoing_flows:
            target = self.workflow.get_element_by_id(flow.to)
            target_elements.append(target)

            if self.agui_server:
                await self.agui_server.send_gateway_path_taken(gateway.id, flow.id, 'parallel')

        return target_elements

    async def evaluate_inclusive_gateway(self, gateway: Element, context: Dict[str, Any]) -> List[Element]:
        """Evaluate inclusive gateway (OR) - one or more paths taken"""
        outgoing_flows = self.workflow.get_outgoing_connections(gateway)

        # Notify UI
        if self.agui_server:
            await self.agui_server.send_gateway_evaluating(
                gateway.id,
                'inclusive',
                len(outgoing_flows)
            )

        # Evaluate all conditions, take matching paths
        target_elements = []
        for flow in outgoing_flows:
            # Use explicit condition from properties, not the name
            condition = flow.properties.get('condition', '')

            # Empty condition = default (always taken), or evaluate condition
            if condition == '' or self.evaluate_condition(condition, context):
                target = self.workflow.get_element_by_id(flow.to)
                target_elements.append(target)

                if self.agui_server:
                    await self.agui_server.send_gateway_path_taken(gateway.id, flow.id, condition or 'default')

        if not target_elements:
            raise Exception(f"No paths matched for inclusive gateway {gateway.id}")

        return target_elements

    def evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition expression against context"""
        logger.debug(f"Evaluating condition: {condition}")

        # Simple condition types:
        # 1. Direct variable reference: "approved" -> checks if context['approved'] is truthy
        # 2. Expression: "${confidence >= 0.8}" -> evaluates expression
        # 3. String match: "yes", "true", "approved" -> checks if value matches

        # Resolve variables
        resolved = self.resolve_variables(condition, context)

        # Try to evaluate as expression
        try:
            # Safe evaluation (limited scope)
            result = eval(resolved, {"__builtins__": {}}, context)
            return bool(result)
        except:
            # If not an expression, check as string
            resolved_lower = resolved.lower().strip()
            return resolved_lower in ['true', 'yes', '1', 'approved']

    def resolve_variables(self, expression: str, context: Dict[str, Any]) -> str:
        """Replace ${variable} with context values"""
        def replacer(match):
            var_name = match.group(1).strip()
            value = context.get(var_name, '')

            # Convert to string representation suitable for eval
            if isinstance(value, str):
                return f'"{value}"'
            else:
                return str(value)

        # Replace ${var} syntax
        resolved = re.sub(r'\$\{([^}]+)\}', replacer, expression)

        # Also handle direct variable names (no ${})
        if resolved == expression and expression in context:
            return str(context[expression])

        return resolved
