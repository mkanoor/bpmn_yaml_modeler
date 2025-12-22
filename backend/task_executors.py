"""
Task Executors - Execute different BPMN task types
"""
import asyncio
import json
import logging
import os
from typing import AsyncGenerator, Dict, Any, Optional, List
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta, date, time
from dotenv import load_dotenv

from models import Element, TaskProgress, UserTaskInstance

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class TaskExecutor(ABC):
    """Base class for task executors"""

    @abstractmethod
    async def execute(self, task: Element, context: Dict[str, Any]) -> AsyncGenerator[TaskProgress, None]:
        """Execute task and yield progress updates"""
        pass


class UserTaskExecutor(TaskExecutor):
    """Executes user tasks requiring human interaction"""

    def __init__(self, agui_server):
        self.agui_server = agui_server

    async def execute(self, task: Element, context: Dict[str, Any]) -> AsyncGenerator[TaskProgress, None]:
        """Execute user task - wait for human completion"""
        logger.info(f"Executing user task: {task.name}")

        # Extract user task configuration
        props = task.properties
        assignee = props.get('assignee', '')
        candidate_groups = props.get('candidateGroups', '').split(',') if props.get('candidateGroups') else []
        priority = props.get('priority', 'Medium')
        due_date = props.get('dueDate')
        form_fields = props.get('custom', {}).get('formFields', [])

        # Extract form data from context
        form_data = {}

        # Include form fields if specified
        for field in form_fields:
            if field in context:
                form_data[field] = context[field]

        # If no form fields specified, include previous task results
        if not form_data:
            # Look for recent task results in context
            for key, value in context.items():
                if key.endswith('_result'):
                    # Extract task name from key (e.g., "element_4_result" -> "element_4")
                    task_name = key.replace('_result', '')
                    form_data[f'{task_name} Results'] = value

        # Create task instance
        task_instance = {
            'taskId': task.id,
            'taskName': task.name,
            'assignee': assignee,
            'candidateGroups': candidate_groups,
            'priority': priority,
            'dueDate': due_date,
            'formFields': form_fields,
            'data': form_data
        }

        # Notify UI to show approval form
        await self.agui_server.send_user_task_created(task.id, task_instance)

        yield TaskProgress(
            status='waiting',
            message=f'Waiting for approval from {assignee or ", ".join(candidate_groups)}',
            progress=0.5
        )

        try:
            # Wait for user completion
            completion_data = await self.agui_server.wait_for_user_task_completion(task.id)

            # Store completion data in context
            context[f'{task.id}_decision'] = completion_data.get('decision')
            context[f'{task.id}_comments'] = completion_data.get('comments')
            context[f'{task.id}_completedBy'] = completion_data.get('completedBy')

            yield TaskProgress(
                status='completed',
                message=f'User task completed: {completion_data.get("decision")}',
                progress=1.0,
                result=completion_data
            )

        except asyncio.CancelledError:
            logger.info(f"🛑 User task {task.id} cancelled - another approval path completed first")
            yield TaskProgress(
                status='cancelled',
                message=f'Task cancelled - another approval path completed first',
                progress=0.5
            )
            # Re-raise to stop execution
            raise


class ServiceTaskExecutor(TaskExecutor):
    """Executes service tasks (external API calls)"""

    def __init__(self, http_client=None):
        self.http_client = http_client

    async def execute(self, task: Element, context: Dict[str, Any]) -> AsyncGenerator[TaskProgress, None]:
        """Execute service task"""
        logger.info(f"Executing service task: {task.name}")

        props = task.properties
        implementation = props.get('implementation', 'External')

        if implementation == 'External':
            # External worker pattern
            topic = props.get('topic', 'default-topic')

            yield TaskProgress(
                status='executing',
                message=f'Publishing to external topic: {topic}',
                progress=0.3
            )

            # Simulate external task execution
            await asyncio.sleep(1)

            result = {
                'topic': topic,
                'status': 'completed',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        elif implementation == 'Expression':
            # Expression evaluation
            expression = props.get('expression', '')

            yield TaskProgress(
                status='executing',
                message=f'Evaluating expression: {expression}',
                progress=0.3
            )

            # Evaluate expression (simplified)
            result = self.evaluate_expression(expression, context)

        else:
            yield TaskProgress(
                status='executing',
                message=f'Executing {implementation}',
                progress=0.3
            )

            result = {'implementation': implementation, 'status': 'completed'}

        # Store result in context
        result_variable = props.get('resultVariable', 'result')
        context[result_variable] = result

        yield TaskProgress(
            status='completed',
            message='Service task completed',
            progress=1.0,
            result=result
        )

    def evaluate_expression(self, expression: str, context: Dict[str, Any]) -> Any:
        """Evaluate expression (simplified)"""
        # In production, use safe expression evaluator
        try:
            # Replace ${variable} with context values
            import re
            def replacer(match):
                var_name = match.group(1).strip()
                return str(context.get(var_name, ''))

            resolved = re.sub(r'\$\{([^}]+)\}', replacer, expression)
            return resolved
        except Exception as e:
            logger.error(f"Expression evaluation error: {e}")
            return None


class ScriptTaskExecutor(TaskExecutor):
    """Executes script tasks"""

    async def execute(self, task: Element, context: Dict[str, Any]) -> AsyncGenerator[TaskProgress, None]:
        """Execute script task"""
        logger.info(f"Executing script task: {task.name}")

        props = task.properties
        script_format = props.get('scriptFormat', 'Python')
        script = props.get('script', '')

        yield TaskProgress(
            status='executing',
            message=f'Running {script_format} script',
            progress=0.3
        )

        # Execute script (in production, use sandboxed execution)
        try:
            if script_format == 'Python':
                # Import commonly used modules
                import random
                from datetime import datetime, timedelta, date, time

                # Create safe globals with limited builtins
                safe_builtins = {
                    'print': print,
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'range': range,
                    'sum': sum,
                    'min': min,
                    'max': max,
                    'abs': abs,
                    'round': round,
                    'isinstance': isinstance,
                    'enumerate': enumerate,
                    'True': True,
                    'False': False,
                    'None': None,
                }

                script_globals = {
                    '__builtins__': safe_builtins,
                    'context': context,
                    # Provide commonly used modules
                    'random': random,
                    'datetime': datetime,
                    'timezone': timezone,
                    'timedelta': timedelta,
                    'date': date,
                    'time': time,
                }

                # Execute script
                exec(script, script_globals)
                result = script_globals.get('result', None)
            else:
                result = f'Script format {script_format} not implemented'

            # Store result
            result_variable = props.get('resultVariable', 'scriptResult')
            context[result_variable] = result

            yield TaskProgress(
                status='completed',
                message='Script executed successfully',
                progress=1.0,
                result=result
            )

        except Exception as e:
            logger.error(f"Script execution error: {e}")
            yield TaskProgress(
                status='failed',
                message=f'Script error: {str(e)}',
                progress=0.5
            )
            raise


class SendTaskExecutor(TaskExecutor):
    """Executes send tasks (notifications)"""

    async def execute(self, task: Element, context: Dict[str, Any]) -> AsyncGenerator[TaskProgress, None]:
        """Execute send task"""
        logger.info(f"Executing send task: {task.name}")

        props = task.properties
        message_type = props.get('messageType', 'Email')

        # Get email addresses with environment variable fallbacks
        import os
        to = props.get('to', '') or os.getenv('DEFAULT_TO_EMAIL', '')
        from_email = props.get('fromEmail', '') or os.getenv('DEFAULT_FROM_EMAIL', '')

        subject = props.get('subject', '')
        message_body = props.get('messageBody', '')
        use_gmail = props.get('useGmail', False)
        html_format = props.get('htmlFormat', False)
        include_approval_links = props.get('includeApprovalLinks', False)
        approval_message_ref = props.get('approvalMessageRef', 'approvalRequest')
        approval_correlation_key = props.get('approvalCorrelationKey', '')

        # Resolve variables in message
        resolved_subject = self.resolve_variables(subject, context)
        resolved_body = self.resolve_variables(message_body, context)
        resolved_to = self.resolve_variables(to, context)

        # Add approval links if requested
        if include_approval_links:
            resolved_correlation_key = self.resolve_variables(approval_correlation_key, context)
            logger.info(f"📧 Email approval setup:")
            logger.info(f"   Message ref: {approval_message_ref}")
            logger.info(f"   Correlation key template: {approval_correlation_key}")
            logger.info(f"   Resolved correlation key: {resolved_correlation_key}")
            logger.info(f"   Context workflowInstanceId: {context.get('workflowInstanceId', 'NOT SET')}")

            resolved_body = self.add_approval_links(
                resolved_body,
                approval_message_ref,
                resolved_correlation_key,
                html_format
            )

        yield TaskProgress(
            status='executing',
            message=f'Sending {message_type} to {resolved_to}',
            progress=0.3
        )

        # Send email using Gmail API if configured
        if use_gmail and message_type == 'Email':
            try:
                result = await self.send_via_gmail(
                    to=resolved_to,
                    subject=resolved_subject,
                    body=resolved_body,
                    from_email=from_email,
                    html=html_format
                )

                logger.info(f"Sent Email via Gmail - Subject: {resolved_subject}, Message ID: {result.get('id')}")

                yield TaskProgress(
                    status='completed',
                    message=f'Email sent successfully via Gmail',
                    progress=1.0,
                    result={'to': resolved_to, 'sent': True, 'messageId': result.get('id'), 'method': 'gmail'}
                )
                return

            except Exception as e:
                logger.error(f"Gmail sending failed: {e}")
                yield TaskProgress(
                    status='failed',
                    message=f'Gmail sending failed: {str(e)}',
                    progress=0.5
                )
                raise

        # Fallback: Simulate sending (for non-Gmail or non-Email messages)
        await asyncio.sleep(0.5)

        logger.info(f"Sent {message_type} (simulated) - Subject: {resolved_subject}")

        yield TaskProgress(
            status='completed',
            message=f'{message_type} sent successfully (simulated)',
            progress=1.0,
            result={'to': resolved_to, 'sent': True, 'method': 'simulated'}
        )

    async def send_via_gmail(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        html: bool = False
    ) -> Dict[str, Any]:
        """
        Send email via Gmail API

        Args:
            to: Recipient email
            subject: Email subject
            body: Email body
            from_email: Sender email (optional)
            html: Send as HTML

        Returns:
            Gmail API response
        """
        from gmail_service import get_gmail_service, is_gmail_configured

        # Check if Gmail is configured
        if not is_gmail_configured():
            raise Exception(
                "Gmail not configured. Please add credentials.json file. "
                "See documentation for setup instructions."
            )

        # Get Gmail service
        gmail = get_gmail_service()

        # Send email (runs in thread pool to avoid blocking)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            gmail.send_message,
            to,
            subject,
            body,
            from_email,
            html
        )

        return result

    def resolve_variables(self, text: str, context: Dict[str, Any]) -> str:
        """Replace ${variable} with context values"""
        import re
        def replacer(match):
            var_name = match.group(1).strip()
            return str(context.get(var_name, ''))

        return re.sub(r'\$\{([^}]+)\}', replacer, text)

    def add_approval_links(
        self,
        body: str,
        message_ref: str,
        correlation_key: str,
        html_format: bool = False
    ) -> str:
        """
        Add approval/denial links to email body

        Args:
            body: Original email body
            message_ref: Message reference for webhook
            correlation_key: Correlation key for matching
            html_format: Whether email is HTML

        Returns:
            Email body with approval links appended
        """
        # Get ngrok URL from environment
        import os
        ngrok_url = os.getenv('NGROK_URL', 'http://localhost:8000')

        # Remove trailing slash
        if ngrok_url.endswith('/'):
            ngrok_url = ngrok_url[:-1]

        # Debug logging
        logger.info(f"🔗 Building approval URLs:")
        logger.info(f"   Message ref: {message_ref}")
        logger.info(f"   Correlation key: {correlation_key}")
        logger.info(f"   Ngrok URL: {ngrok_url}")

        # Build approval URLs
        approve_url = f"{ngrok_url}/webhooks/approve/{message_ref}/{correlation_key}"
        deny_url = f"{ngrok_url}/webhooks/deny/{message_ref}/{correlation_key}"

        logger.info(f"✅ APPROVE URL IN EMAIL: {approve_url}")
        logger.info(f"❌ DENY URL IN EMAIL: {deny_url}")

        if html_format:
            # HTML format with styled buttons
            approval_section = f"""
<div style="margin-top: 30px; padding: 20px; border-top: 2px solid #e0e0e0;">
    <p style="font-size: 16px; margin-bottom: 20px;">Please choose an action:</p>
    <table cellspacing="0" cellpadding="0" style="margin: 0;">
        <tr>
            <td style="padding-right: 10px;">
                <a href="{approve_url}"
                   style="display: inline-block; padding: 12px 30px; background-color: #28a745;
                          color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    ✓ Approve
                </a>
            </td>
            <td>
                <a href="{deny_url}"
                   style="display: inline-block; padding: 12px 30px; background-color: #dc3545;
                          color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    ✗ Deny
                </a>
            </td>
        </tr>
    </table>
    <p style="font-size: 12px; color: #666; margin-top: 20px;">
        Click a button above to submit your decision. This action will be recorded immediately.
    </p>
</div>
"""
        else:
            # Plain text format
            approval_section = f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Please choose an action:

✓ APPROVE: {approve_url}

✗ DENY: {deny_url}

Click a link above to submit your decision.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        return body + approval_section


class ReceiveTaskExecutor(TaskExecutor):
    """Executes receive tasks (wait for messages)"""

    async def execute(self, task: Element, context: Dict[str, Any]) -> AsyncGenerator[TaskProgress, None]:
        """Execute receive task"""
        logger.info(f"Executing receive task: {task.name}")

        props = task.properties
        message_ref = props.get('messageRef', '')
        correlation_key = props.get('correlationKey', '')
        timeout = int(props.get('timeout', 30000)) / 1000  # Convert to seconds
        use_webhook = props.get('useWebhook', False)

        # Resolve correlation key from context
        original_correlation_key = correlation_key
        if correlation_key:
            import re
            def replacer(match):
                var_name = match.group(1).strip()
                return str(context.get(var_name, ''))
            correlation_key = re.sub(r'\$\{([^}]+)\}', replacer, correlation_key)

        logger.info(f"📥 Receive task setup:")
        logger.info(f"   Message ref: {message_ref}")
        logger.info(f"   Correlation key template: {original_correlation_key}")
        logger.info(f"   Resolved correlation key: {correlation_key}")
        logger.info(f"   Context workflowInstanceId: {context.get('workflowInstanceId', 'NOT SET')}")
        logger.info(f"Waiting for message: {message_ref}, correlation: {correlation_key}, webhook: {use_webhook}")

        yield TaskProgress(
            status='waiting',
            message=f'Waiting for message: {message_ref}' + (f' (correlation: {correlation_key})' if correlation_key else ''),
            progress=0.3
        )

        if use_webhook and correlation_key:
            # Wait for webhook message via message queue
            try:
                from message_queue import get_message_queue

                message_queue = get_message_queue()

                logger.info(f"Task {task.id} waiting for webhook message...")

                # Wait for message with timeout
                message = await message_queue.wait_for_message(
                    task_id=task.id,
                    message_ref=message_ref,
                    correlation_key=correlation_key,
                    timeout_seconds=timeout
                )

                logger.info(f"Task {task.id} received webhook message")

                # Store received message in context
                context[f'{task.id}_message'] = message
                context[f'{task.id}_payload'] = message.get('payload', {})

                # Merge payload into context if it's a dict
                payload = message.get('payload', {})
                if isinstance(payload, dict):
                    for key, value in payload.items():
                        context[key] = value

                yield TaskProgress(
                    status='completed',
                    message=f'Message received via webhook',
                    progress=1.0,
                    result=message
                )

            except asyncio.CancelledError:
                logger.info(f"🛑 Task {task.id} cancelled while waiting for webhook")
                yield TaskProgress(
                    status='cancelled',
                    message=f'Task cancelled - another approval path completed first',
                    progress=0.5
                )
                # Re-raise to stop execution
                raise

            except asyncio.TimeoutError:
                logger.error(f"Task {task.id} timed out waiting for webhook")
                yield TaskProgress(
                    status='failed',
                    message=f'Timeout waiting for message: {message_ref}',
                    progress=0.5
                )
                raise Exception(f"Timeout waiting for webhook message: {message_ref}")

        else:
            # Simulate waiting for message (fallback)
            await asyncio.sleep(min(timeout, 2))

            # Store simulated message in context
            context[f'{task.id}_message'] = {
                'messageRef': message_ref,
                'correlationKey': correlation_key,
                'received': True,
                'simulated': True,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            yield TaskProgress(
                status='completed',
                message='Message received (simulated)',
                progress=1.0
            )


class ManualTaskExecutor(TaskExecutor):
    """Executes manual tasks (no system support)"""

    async def execute(self, task: Element, context: Dict[str, Any]) -> AsyncGenerator[TaskProgress, None]:
        """Execute manual task"""
        logger.info(f"Executing manual task: {task.name}")

        yield TaskProgress(
            status='executing',
            message='Manual task in progress',
            progress=0.5
        )

        # Manual tasks are assumed to be done immediately in this simulation
        await asyncio.sleep(1)

        yield TaskProgress(
            status='completed',
            message='Manual task completed',
            progress=1.0
        )


class BusinessRuleTaskExecutor(TaskExecutor):
    """Executes business rule tasks"""

    async def execute(self, task: Element, context: Dict[str, Any]) -> AsyncGenerator[TaskProgress, None]:
        """Execute business rule task"""
        logger.info(f"Executing business rule task: {task.name}")

        props = task.properties
        decision_ref = props.get('decisionRef', '')

        yield TaskProgress(
            status='executing',
            message=f'Evaluating decision: {decision_ref}',
            progress=0.3
        )

        # Simulate business rule evaluation
        await asyncio.sleep(0.5)

        result = {
            'decision': decision_ref,
            'outcome': 'approved',
            'confidence': 0.95
        }

        # Store result
        result_variable = props.get('resultVariable', 'decisionResult')
        context[result_variable] = result

        yield TaskProgress(
            status='completed',
            message='Business rule evaluated',
            progress=1.0,
            result=result
        )


class AgenticTaskExecutor(TaskExecutor):
    """Executes agentic tasks with AI/MCP tools"""

    def __init__(self, mcp_client=None, agui_server=None):
        self.mcp_client = mcp_client
        self.agui_server = agui_server

    async def execute(self, task: Element, context: Dict[str, Any]) -> AsyncGenerator[TaskProgress, None]:
        """Execute agentic task using AI model with MCP tools"""
        logger.info(f"Executing agentic task: {task.name}")

        # Extract configuration
        props = task.properties
        agent_type = props.get('agentType', 'generic-agent')
        model = props.get('model', 'claude-3-opus')
        capabilities = props.get('capabilities', '').split(',')
        custom = props.get('custom', {})
        mcp_tools = custom.get('mcpTools', [])
        system_prompt = custom.get('systemPrompt', '')
        confidence_threshold = float(props.get('confidenceThreshold', 0.8))
        max_retries = int(props.get('maxRetries', 3))

        # Send thinking indicator via AG-UI
        if self.agui_server:
            await self.agui_server.send_task_thinking(task.id, f"Initializing {agent_type} agent...")

        yield TaskProgress(
            status='initializing',
            message=f'Initializing {agent_type} agent with {model}',
            progress=0.1
        )

        # Execute agent with retries
        for attempt in range(max_retries):
            try:
                # Send thinking indicator via AG-UI
                if self.agui_server:
                    await self.agui_server.send_task_thinking(
                        task.id,
                        f"Analyzing with {model} (attempt {attempt + 1}/{max_retries})..."
                    )

                yield TaskProgress(
                    status='executing',
                    message=f'Agent analyzing (attempt {attempt + 1}/{max_retries})',
                    progress=0.3 + (attempt * 0.2)
                )

                # Run agent inference
                result = await self.run_agent(
                    task_id=task.id,
                    model=model,
                    system_prompt=system_prompt,
                    mcp_tools=mcp_tools,
                    context=context
                )

                # Check confidence
                confidence = result.get('confidence', 1.0)
                if confidence >= confidence_threshold:
                    # Store result in context
                    context[f'{task.id}_result'] = result

                    yield TaskProgress(
                        status='completed',
                        message=f'Analysis complete (confidence: {confidence:.2%})',
                        progress=1.0,
                        result=result
                    )
                    return
                else:
                    yield TaskProgress(
                        status='retry',
                        message=f'Low confidence ({confidence:.2%}), retrying...',
                        progress=0.5
                    )

            except Exception as e:
                logger.error(f"Agent execution error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise

                yield TaskProgress(
                    status='error',
                    message=f'Attempt failed: {str(e)}',
                    progress=0.4
                )

        # Failed after retries
        raise Exception(f"Agent failed after {max_retries} attempts")

    async def run_agent(self, task_id: str, model: str, system_prompt: str,
                       mcp_tools: list, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run AI agent with MCP tools using OpenRouter"""

        logger.info(f"Running agent with model: {model} via OpenRouter")

        # Check if we have log file content in context
        log_content = context.get('logFileContent', '')
        log_file_name = context.get('logFileName', 'unknown.log')

        # Execute MCP tools first (broadcast to UI)
        tool_results = await self._execute_mcp_tools(task_id, mcp_tools, log_content, log_file_name)

        # Call OpenRouter for AI analysis
        use_openrouter = os.getenv('OPENROUTER_API_KEY')

        if use_openrouter:
            try:
                analysis_result = await self._call_openrouter(
                    model=model,
                    system_prompt=system_prompt,
                    tool_results=tool_results,
                    log_content=log_content,
                    log_file_name=log_file_name
                )
                return analysis_result
            except Exception as e:
                logger.error(f"OpenRouter API call failed: {e}")
                logger.warning("Falling back to simple analysis")
                # Fall through to simple analysis
        else:
            logger.warning("OPENROUTER_API_KEY not set, using simple analysis")

        # Fallback: Simple analysis without AI
        return await self._simple_analysis(model, tool_results, log_content, log_file_name)

    async def _execute_mcp_tools(self, task_id: str, mcp_tools: list,
                                 log_content: str, log_file_name: str) -> List[Dict[str, Any]]:
        """Execute MCP tools and broadcast to UI using AG-UI streaming events"""
        tool_results = []
        tools_to_use = mcp_tools[:3] if len(mcp_tools) > 3 else mcp_tools

        for tool in tools_to_use:
            tool_args = {'context': 'analysis'}

            # Add specific arguments based on tool
            if tool == 'filesystem-read' and log_file_name:
                tool_args = {'path': log_file_name, 'encoding': 'utf-8'}
            elif tool == 'grep-search' and log_content:
                tool_args = {'pattern': 'ERROR|FATAL|CRITICAL',
                           'content_preview': log_content[:100] + '...'}
            elif tool == 'log-parser':
                tool_args = {'format': 'detect', 'file': log_file_name}

            if self.agui_server:
                # Send tool start event (new AG-UI streaming)
                await self.agui_server.send_task_tool_start(task_id, tool, tool_args)

                # Also send old format for backward compatibility
                await self.agui_server.send_agent_tool_use(task_id, tool, tool_args)

            # Simulate tool execution
            await asyncio.sleep(0.5)

            if self.agui_server:
                # Send tool end event (new AG-UI streaming)
                await self.agui_server.send_task_tool_end(task_id, tool, result={'status': 'success'})

            tool_results.append({'tool': tool, 'args': tool_args})

        return tool_results

    async def _call_openrouter(self, model: str, system_prompt: str,
                              tool_results: List[Dict], log_content: str,
                              log_file_name: str) -> Dict[str, Any]:
        """Call OpenRouter API for AI analysis"""
        from openai import AsyncOpenAI

        # Initialize OpenRouter client
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv('OPENROUTER_API_KEY')
        )

        # Prepare the analysis prompt
        user_prompt = self._build_analysis_prompt(log_content, log_file_name, tool_results)

        # Call OpenRouter
        logger.info(f"Calling OpenRouter with model: {model}")

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            extra_headers={
                "HTTP-Referer": os.getenv('OPENROUTER_APP_URL', 'http://localhost:8000'),
                "X-Title": os.getenv('OPENROUTER_APP_NAME', 'BPMN-Workflow-Executor')
            },
            temperature=0.3,
            max_tokens=2000
        )

        # Extract analysis from response
        analysis_text = response.choices[0].message.content

        logger.info(f"OpenRouter analysis complete. Usage: {response.usage}")

        # Parse the analysis (expecting JSON or structured text)
        try:
            # Try to parse as JSON
            analysis_data = json.loads(analysis_text)
            findings = analysis_data.get('findings', [analysis_text])
        except json.JSONDecodeError:
            # If not JSON, use the text as a single finding
            findings = [analysis_text]

        return {
            'analysis': f'Analysis completed using {model} via OpenRouter',
            'log_file': log_file_name,
            'log_size': len(log_content) if log_content else 0,
            'tools_used': [t['tool'] for t in tool_results],
            'confidence': 0.92,
            'findings': findings,
            'model_used': model,
            'tokens_used': response.usage.total_tokens if response.usage else 0
        }

    def _build_analysis_prompt(self, log_content: str, log_file_name: str,
                               tool_results: List[Dict]) -> str:
        """Build the analysis prompt for the AI"""
        prompt = f"""Analyze the following log file for errors, warnings, and issues.

Log File: {log_file_name}
Size: {len(log_content)} bytes

MCP Tools Used: {', '.join([t['tool'] for t in tool_results])}

Log Content:
{log_content[:4000]}  # Limit to first 4000 chars

Please provide:
1. Summary of errors, warnings, and critical issues found
2. Root cause analysis for major issues
3. Recommended actions to resolve the issues
4. Priority level for each issue (Critical, High, Medium, Low)

Format your response as JSON with this structure:
{{
    "findings": [
        "Summary of what was found...",
        "Root cause analysis...",
        "Recommended actions..."
    ]
}}
"""
        return prompt

    async def _simple_analysis(self, model: str, tool_results: List[Dict],
                               log_content: str, log_file_name: str) -> Dict[str, Any]:
        """Simple pattern-based analysis (fallback when OpenRouter not available)"""
        findings = []

        if log_content:
            # Simple log analysis
            errors = log_content.lower().count('error')
            warnings = log_content.lower().count('warning')
            critical = log_content.lower().count('critical')

            findings = [
                f'Found {errors} errors, {warnings} warnings, {critical} critical messages',
                'Analysis of log patterns complete',
                'Recommended actions generated'
            ]

            # Look for common issues
            if 'disk' in log_content.lower() or 'space' in log_content.lower():
                findings.append('Potential disk space issue detected')
            if 'memory' in log_content.lower() or 'oom' in log_content.lower():
                findings.append('Potential memory issue detected')
            if 'connection' in log_content.lower() or 'timeout' in log_content.lower():
                findings.append('Potential connection/timeout issue detected')
        else:
            findings = ['No log content available for analysis']

        return {
            'analysis': f'Simple analysis completed (OpenRouter not configured)',
            'log_file': log_file_name,
            'log_size': len(log_content) if log_content else 0,
            'tools_used': [t['tool'] for t in tool_results],
            'confidence': 0.75,  # Lower confidence for simple analysis
            'findings': findings
        }


class SubProcessExecutor(TaskExecutor):
    """Executes subprocesses"""

    def __init__(self, workflow_engine):
        self.workflow_engine = workflow_engine

    async def execute(self, task: Element, context: Dict[str, Any]) -> AsyncGenerator[TaskProgress, None]:
        """Execute subprocess"""
        logger.info(f"Executing subprocess: {task.name}")

        yield TaskProgress(
            status='executing',
            message='Executing subprocess',
            progress=0.3
        )

        # Execute child elements if expanded
        if task.expanded and task.childElements:
            # Execute subprocess flow
            for child in task.childElements:
                # Execute child element
                pass

        yield TaskProgress(
            status='completed',
            message='Subprocess completed',
            progress=1.0
        )


class TimerIntermediateCatchEventExecutor(TaskExecutor):
    """Executes timer intermediate catch events (wait/delay)"""

    async def execute(self, task: Element, context: Dict[str, Any]) -> AsyncGenerator[TaskProgress, None]:
        """Execute timer intermediate catch event - wait for duration/date"""
        logger.info(f"Executing timer intermediate catch event: {task.name}")

        props = task.properties
        timer_type = props.get('timerType', 'duration')

        yield TaskProgress(
            status='waiting',
            message=f'Timer started: {task.name}',
            progress=0.1
        )

        # Calculate wait time based on timer type
        wait_seconds = 0
        if timer_type == 'duration':
            # ISO 8601 duration format (PT5M, PT1H, P1D)
            duration_str = props.get('timerDuration', 'PT30S')
            wait_seconds = self.parse_duration(duration_str)
            logger.info(f"Timer will wait for {wait_seconds} seconds (duration: {duration_str})")

        elif timer_type == 'date':
            # ISO 8601 date/time format
            target_date = props.get('timerDate', '')
            wait_seconds = self.calculate_wait_until_date(target_date)
            logger.info(f"Timer will wait until {target_date} ({wait_seconds} seconds)")

        elif timer_type == 'cycle':
            # Cron-like cycle (R3/PT10M = repeat 3 times every 10 minutes)
            cycle_str = props.get('timerCycle', 'PT1M')
            wait_seconds = self.parse_cycle(cycle_str)
            logger.info(f"Timer cycle: {cycle_str}, waiting {wait_seconds} seconds")

        # Simulate waiting (in production, this would be actual timer)
        # For demo purposes, cap at 10 seconds
        actual_wait = min(wait_seconds, 10) if wait_seconds > 0 else 2

        await asyncio.sleep(actual_wait)

        # Store timer completion in context
        context[f'{task.id}_timer_completed'] = datetime.now(timezone.utc).isoformat()

        yield TaskProgress(
            status='completed',
            message=f'Timer completed: waited {actual_wait} seconds',
            progress=1.0,
            result={'waited_seconds': actual_wait, 'timer_type': timer_type}
        )

    def parse_duration(self, duration_str: str) -> float:
        """Parse ISO 8601 duration to seconds (simplified)"""
        import re
        # PT5M = 5 minutes, PT1H = 1 hour, P1D = 1 day
        seconds = 0

        # Days
        days_match = re.search(r'(\d+)D', duration_str)
        if days_match:
            seconds += int(days_match.group(1)) * 86400

        # Hours
        hours_match = re.search(r'(\d+)H', duration_str)
        if hours_match:
            seconds += int(hours_match.group(1)) * 3600

        # Minutes
        minutes_match = re.search(r'(\d+)M', duration_str)
        if minutes_match:
            seconds += int(minutes_match.group(1)) * 60

        # Seconds
        seconds_match = re.search(r'(\d+)S', duration_str)
        if seconds_match:
            seconds += int(seconds_match.group(1))

        return float(seconds) if seconds > 0 else 30.0  # Default 30 seconds

    def calculate_wait_until_date(self, date_str: str) -> float:
        """Calculate seconds until target date"""
        from dateutil import parser
        try:
            target = parser.parse(date_str)
            now = datetime.now(timezone.utc).replace(tzinfo=target.tzinfo)
            delta = (target - now).total_seconds()
            return max(0, delta)
        except Exception as e:
            logger.error(f"Error parsing date {date_str}: {e}")
            return 30.0  # Default 30 seconds

    def parse_cycle(self, cycle_str: str) -> float:
        """Parse cycle expression (R3/PT10M = repeat 3 times every 10 min)"""
        # Simplified: just parse the duration part
        import re
        duration_match = re.search(r'PT?[\d\w]+', cycle_str)
        if duration_match:
            return self.parse_duration(duration_match.group(0))
        return 60.0  # Default 1 minute


class BoundaryTimerEventExecutor(TaskExecutor):
    """Executes boundary timer events (timeouts attached to tasks)"""

    async def execute(self, task: Element, context: Dict[str, Any]) -> AsyncGenerator[TaskProgress, None]:
        """Execute boundary timer event - monitor attached task for timeout"""
        logger.info(f"Executing boundary timer event: {task.name}")

        props = task.properties
        timer_type = props.get('timerType', 'duration')
        cancel_activity = props.get('cancelActivity', True)
        attached_to = props.get('attachedTo', '')

        yield TaskProgress(
            status='monitoring',
            message=f'Monitoring task for timeout: {attached_to}',
            progress=0.3
        )

        # Calculate timeout duration
        timeout_seconds = 0
        if timer_type == 'duration':
            duration_str = props.get('timerDuration', 'PT30M')
            timeout_seconds = TimerIntermediateCatchEventExecutor().parse_duration(duration_str)
        elif timer_type == 'date':
            target_date = props.get('timerDate', '')
            timeout_seconds = TimerIntermediateCatchEventExecutor().calculate_wait_until_date(target_date)

        # Simulate monitoring (in production, this runs in parallel with attached task)
        actual_timeout = min(timeout_seconds, 5) if timeout_seconds > 0 else 2
        await asyncio.sleep(actual_timeout)

        # Store timeout event in context
        context[f'{task.id}_timeout_triggered'] = True
        context[f'{task.id}_timeout_seconds'] = actual_timeout
        context[f'{task.id}_cancel_activity'] = cancel_activity

        yield TaskProgress(
            status='completed',
            message=f'Timeout triggered after {actual_timeout} seconds',
            progress=1.0,
            result={
                'timeout_seconds': actual_timeout,
                'cancel_activity': cancel_activity,
                'attached_to': attached_to
            }
        )


class TaskExecutorRegistry:
    """Registry of task executors"""

    def __init__(self, agui_server=None, mcp_client=None):
        self.executors = {
            'userTask': UserTaskExecutor(agui_server),
            'serviceTask': ServiceTaskExecutor(),
            'scriptTask': ScriptTaskExecutor(),
            'sendTask': SendTaskExecutor(),
            'receiveTask': ReceiveTaskExecutor(),
            'manualTask': ManualTaskExecutor(),
            'businessRuleTask': BusinessRuleTaskExecutor(),
            'agenticTask': AgenticTaskExecutor(mcp_client, agui_server),
            'timerIntermediateCatchEvent': TimerIntermediateCatchEventExecutor(),
            'boundaryTimerEvent': BoundaryTimerEventExecutor(),
            'task': ManualTaskExecutor(),  # Default task type
        }

    def get_executor(self, task_type: str) -> TaskExecutor:
        """Get executor for task type"""
        executor = self.executors.get(task_type)
        if not executor:
            logger.warning(f"No executor found for task type: {task_type}, using default")
            return self.executors['task']
        return executor
