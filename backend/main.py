"""
FastAPI Application - BPMN Workflow Execution Server
"""
import asyncio
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any
import uvicorn

from agui_server import AGUIServer
from workflow_engine import WorkflowEngine, execute_workflow_from_file
from models import Workflow
from message_queue import get_message_queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="BPMN Workflow Execution Engine", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global AG-UI server instance
agui_server = AGUIServer()

# Active workflow instances
active_workflows: Dict[str, WorkflowEngine] = {}


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "BPMN Workflow Execution Engine",
        "version": "1.0.0",
        "active_workflows": len(active_workflows)
    }


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "connected_clients": len(agui_server.clients)
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for AG-UI protocol"""
    logger.info("New WebSocket connection")
    await agui_server.handle_client(websocket)


@app.post("/workflows/execute")
async def execute_workflow(workflow_data: Dict[str, Any]):
    """
    Execute a workflow from YAML data

    Request body:
    {
        "yaml": "workflow YAML content",
        "context": {
            "variable1": "value1",
            "variable2": "value2"
        }
    }
    """
    try:
        yaml_content = workflow_data.get('yaml')
        context = workflow_data.get('context', {})

        if not yaml_content:
            raise HTTPException(status_code=400, detail="Missing 'yaml' in request")

        # Create workflow engine
        engine = WorkflowEngine(yaml_content, agui_server)

        # Store instance
        instance_id = None

        # Start execution in background
        async def execute():
            nonlocal instance_id
            await engine.start_execution(context)
            instance_id = engine.instance_id

            # Remove from active workflows when done
            if instance_id in active_workflows:
                del active_workflows[instance_id]

        # Run in background
        asyncio.create_task(execute())

        # Wait a moment for instance_id to be set
        await asyncio.sleep(0.1)

        # Get instance_id from engine if available
        if hasattr(engine, 'instance_id') and engine.instance_id:
            instance_id = engine.instance_id
            active_workflows[instance_id] = engine

        return {
            "status": "started",
            "instance_id": instance_id or "pending",
            "message": "Workflow execution started"
        }

    except Exception as e:
        logger.error(f"Error executing workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/workflows/execute-file")
async def execute_workflow_file(file: UploadFile = File(...), context: Dict[str, Any] = None):
    """
    Execute a workflow from uploaded YAML file
    """
    try:
        # Read file content
        yaml_content = await file.read()
        yaml_str = yaml_content.decode('utf-8')

        # Create workflow engine
        engine = WorkflowEngine(yaml_str, agui_server)

        # Start execution in background
        async def execute():
            await engine.start_execution(context or {})

            # Remove from active workflows when done
            if engine.instance_id in active_workflows:
                del active_workflows[engine.instance_id]

        asyncio.create_task(execute())

        # Wait for instance_id
        await asyncio.sleep(0.1)

        instance_id = engine.instance_id
        if instance_id:
            active_workflows[instance_id] = engine

        return {
            "status": "started",
            "instance_id": instance_id,
            "message": "Workflow execution started"
        }

    except Exception as e:
        logger.error(f"Error executing workflow from file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workflows/{instance_id}/status")
async def get_workflow_status(instance_id: str):
    """Get status of a workflow instance"""
    if instance_id not in active_workflows:
        return {
            "instance_id": instance_id,
            "status": "not_found",
            "message": "Workflow instance not found or completed"
        }

    engine = active_workflows[instance_id]

    return {
        "instance_id": instance_id,
        "status": "running",
        "workflow_name": engine.workflow.process.name,
        "start_time": engine.start_time.isoformat() if engine.start_time else None,
        "context_keys": list(engine.context.keys())
    }


@app.get("/workflows/active")
async def list_active_workflows():
    """List all active workflow instances"""
    workflows = []

    for instance_id, engine in active_workflows.items():
        workflows.append({
            "instance_id": instance_id,
            "workflow_name": engine.workflow.process.name,
            "start_time": engine.start_time.isoformat() if engine.start_time else None
        })

    return {
        "count": len(workflows),
        "workflows": workflows
    }


@app.post("/workflows/{instance_id}/cancel")
async def cancel_workflow(instance_id: str):
    """Cancel a running workflow"""
    if instance_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow instance not found")

    # Remove from active workflows
    del active_workflows[instance_id]

    # Send cancellation event
    await agui_server.send_update({
        'type': 'workflow.cancelled',
        'instanceId': instance_id
    })

    return {
        "status": "cancelled",
        "instance_id": instance_id
    }


@app.post("/test/execute-log-analysis")
async def test_log_analysis_workflow():
    """
    Test endpoint to execute the AI log analysis workflow
    """
    try:
        # Load the AI log analysis workflow
        yaml_file = '../ai-log-analysis-workflow.yaml'

        # Context for the workflow
        context = {
            'logFileUrl': 's3://devops-logs/nginx-error.log',
            'logFileName': 'nginx-error.log',
            'requester': {
                'email': 'admin@example.com',
                'name': 'Test User'
            }
        }

        # Execute workflow
        instance_id = await execute_workflow_from_file(yaml_file, agui_server, context)

        return {
            "status": "started",
            "instance_id": instance_id,
            "workflow": "AI Log Analysis & Remediation",
            "message": "Workflow execution started. Connect to WebSocket to see real-time updates."
        }

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="ai-log-analysis-workflow.yaml not found. Make sure it exists in the parent directory."
        )
    except Exception as e:
        logger.error(f"Error executing test workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhooks/message")
async def receive_webhook_message(request: Request):
    """
    Webhook endpoint to receive external messages for workflows

    POST /webhooks/message
    {
        "messageRef": "paymentConfirmation",
        "correlationKey": "order-12345",
        "payload": {
            "orderId": "12345",
            "amount": 99.99,
            "status": "paid"
        }
    }
    """
    try:
        data = await request.json()

        message_ref = data.get('messageRef')
        correlation_key = data.get('correlationKey')
        payload = data.get('payload', {})

        if not message_ref or not correlation_key:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: messageRef and correlationKey"
            )

        logger.info(f"Received webhook: {message_ref}, correlation: {correlation_key}")

        # Publish to message queue
        message_queue = get_message_queue()
        delivered = await message_queue.publish_message(message_ref, correlation_key, payload)

        return {
            "status": "received",
            "messageRef": message_ref,
            "correlationKey": correlation_key,
            "delivered": delivered,
            "timestamp": data.get('timestamp')
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhooks/{message_ref}/{correlation_key}")
async def receive_webhook_simple(
    message_ref: str,
    correlation_key: str,
    request: Request
):
    """
    Simplified webhook endpoint with message ref and correlation key in URL

    POST /webhooks/paymentConfirmation/order-12345
    {
        "orderId": "12345",
        "amount": 99.99,
        "status": "paid"
    }
    """
    try:
        payload = await request.json()

        logger.info(f"Received webhook: {message_ref}, correlation: {correlation_key}")

        # Publish to message queue
        message_queue = get_message_queue()
        delivered = await message_queue.publish_message(message_ref, correlation_key, payload)

        return {
            "status": "received",
            "messageRef": message_ref,
            "correlationKey": correlation_key,
            "delivered": delivered
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/webhooks/queue/stats")
async def get_queue_stats():
    """Get message queue statistics"""
    message_queue = get_message_queue()
    stats = await message_queue.get_stats()

    return {
        "status": "ok",
        "queue_stats": stats
    }


@app.get("/webhooks/queue/{correlation_key}")
async def get_queued_messages(correlation_key: str):
    """Get queued messages for a correlation key"""
    message_queue = get_message_queue()

    messages = await message_queue.get_queued_messages(correlation_key)
    waiting_tasks = await message_queue.get_waiting_tasks(correlation_key)

    return {
        "correlationKey": correlation_key,
        "queued_messages": messages,
        "waiting_tasks": waiting_tasks
    }


@app.delete("/webhooks/queue/{correlation_key}")
async def clear_queued_messages(correlation_key: str):
    """Clear queued messages for a correlation key"""
    message_queue = get_message_queue()
    await message_queue.clear_messages(correlation_key)

    return {
        "status": "cleared",
        "correlationKey": correlation_key
    }


@app.get("/webhooks/approve/{message_ref}/{correlation_key}")
async def approve_via_email(message_ref: str, correlation_key: str):
    """
    Email approval webhook - Approve action
    User clicks approve link in email

    GET /webhooks/approve/approvalRequest/order-12345
    """
    try:
        logger.info(f"Email approval: {message_ref}, correlation: {correlation_key}")

        # Publish approval message
        message_queue = get_message_queue()
        delivered = await message_queue.publish_message(
            message_ref=message_ref,
            correlation_key=correlation_key,
            payload={
                'decision': 'approved',
                'method': 'email',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )

        # Return user-friendly HTML response
        return JSONResponse(
            content={
                "status": "approved",
                "message": "Your approval has been recorded. You may close this window.",
                "messageRef": message_ref,
                "correlationKey": correlation_key
            },
            headers={"Content-Type": "application/json"}
        )

    except Exception as e:
        logger.error(f"Error processing email approval: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/webhooks/deny/{message_ref}/{correlation_key}")
async def deny_via_email(message_ref: str, correlation_key: str):
    """
    Email approval webhook - Deny action
    User clicks deny link in email

    GET /webhooks/deny/approvalRequest/order-12345
    """
    try:
        logger.info(f"Email denial: {message_ref}, correlation: {correlation_key}")

        # Publish denial message
        message_queue = get_message_queue()
        delivered = await message_queue.publish_message(
            message_ref=message_ref,
            correlation_key=correlation_key,
            payload={
                'decision': 'denied',
                'method': 'email',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )

        # Return user-friendly HTML response
        return JSONResponse(
            content={
                "status": "denied",
                "message": "Your denial has been recorded. You may close this window.",
                "messageRef": message_ref,
                "correlationKey": correlation_key
            },
            headers={"Content-Type": "application/json"}
        )

    except Exception as e:
        logger.error(f"Error processing email denial: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Run the server
    logger.info("Starting BPMN Workflow Execution Engine...")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
