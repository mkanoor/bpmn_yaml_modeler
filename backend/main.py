"""
FastAPI Application - BPMN Workflow Execution Server
"""
import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, Any
import uvicorn

from agui_server import AGUIServer
from workflow_engine import WorkflowEngine, execute_workflow_from_file
from models import Workflow
from message_queue import get_message_queue
from mcp_client import MCPClient, create_default_mcp_client, initialize_mcp_servers

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

# Global MCP client instance (will be initialized at startup)
mcp_client: MCPClient = None

# Active workflow instances
active_workflows: Dict[str, WorkflowEngine] = {}

# Get the parent directory (project root)
BASE_DIR = Path(__file__).resolve().parent.parent


@app.on_event("startup")
async def startup_event():
    """Initialize MCP client on startup"""
    global mcp_client

    try:
        logger.info("🚀 Initializing MCP client...")
        mcp_client = create_default_mcp_client()
        await initialize_mcp_servers(mcp_client)
        logger.info("✅ MCP client initialized successfully")

        # Log available tools
        tools = await mcp_client.list_tools()
        logger.info(f"📋 Available MCP tools: {', '.join(tools)}")

    except Exception as e:
        logger.error(f"❌ Failed to initialize MCP client: {e}")
        logger.warning("⚠️ Workflows will run without MCP tool support")
        mcp_client = None


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown MCP client"""
    global mcp_client

    if mcp_client:
        try:
            logger.info("🛑 Shutting down MCP client...")
            await mcp_client.shutdown()
            logger.info("✅ MCP client shut down successfully")
        except Exception as e:
            logger.error(f"❌ Error during MCP client shutdown: {e}")


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "connected_clients": len(agui_server.clients),
        "mcp_enabled": mcp_client is not None,
        "mcp_tools": await mcp_client.list_tools() if mcp_client else []
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for AG-UI protocol"""
    logger.info("New WebSocket connection")
    await agui_server.handle_client(websocket)


@app.post("/workflows/execute")
async def execute_workflow(workflow_data: Dict[str, Any]):
    """
    Execute a workflow from YAML data or file path

    Request body:
    {
        "yaml": "workflow YAML content",  // OR
        "workflowFile": "path/to/workflow.yaml",  // file path
        "context": {
            "variable1": "value1",
            "variable2": "value2"
        }
    }
    """
    try:
        yaml_content = workflow_data.get('yaml')
        workflow_file = workflow_data.get('workflowFile')
        context = workflow_data.get('context', {})

        # Load from file if workflowFile provided
        if workflow_file and not yaml_content:
            logger.info(f"Loading workflow from file: {workflow_file}")
            with open(workflow_file, 'r') as f:
                yaml_content = f.read()

        if not yaml_content:
            raise HTTPException(status_code=400, detail="Missing 'yaml' or 'workflowFile' in request")

        # Create workflow engine with filename for logging and MCP client
        engine = WorkflowEngine(yaml_content, agui_server, mcp_client=mcp_client, workflow_file=workflow_file)

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

        # Create workflow engine with filename for logging and MCP client
        engine = WorkflowEngine(yaml_str, agui_server, mcp_client=mcp_client, workflow_file=file.filename)

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
async def approve_confirmation_page(message_ref: str, correlation_key: str):
    """
    Email approval webhook - Show confirmation page
    User clicks approve link in email

    GET /webhooks/approve/approvalRequest/order-12345
    Returns HTML page with confirmation button that POSTs
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Approval Confirmation</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                text-align: center;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                border-radius: 8px;
                padding: 40px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #27ae60;
                margin-bottom: 10px;
            }}
            p {{
                color: #555;
                line-height: 1.6;
                margin-bottom: 25px;
            }}
            .btn {{
                background: #27ae60;
                color: white;
                border: none;
                padding: 15px 40px;
                font-size: 16px;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.3s;
                font-weight: 600;
            }}
            .btn:hover {{
                background: #229954;
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }}
            .btn-cancel {{
                background: #95a5a6;
                margin-left: 10px;
            }}
            .btn-cancel:hover {{
                background: #7f8c8d;
            }}
            .info {{
                background: #f8f9fa;
                border-left: 4px solid #3498db;
                padding: 15px;
                margin: 25px 0;
                text-align: left;
                border-radius: 4px;
            }}
            .info p {{
                margin: 5px 0;
                font-size: 14px;
            }}
            .info strong {{
                color: #2c3e50;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✓ Confirm Approval</h1>
            <p>You are about to approve this request. Please confirm your decision.</p>

            <div class="info">
                <p><strong>Request ID:</strong> {message_ref}</p>
                <p><strong>Correlation:</strong> {correlation_key[:8] if correlation_key else 'N/A'}...</p>
            </div>

            <form method="POST" action="/webhooks/approve/{message_ref}/{correlation_key}">
                <button type="submit" class="btn">Approve</button>
                <button type="button" class="btn btn-cancel" onclick="window.close()">Cancel</button>
            </form>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/webhooks/approve/{message_ref}/{correlation_key}")
async def approve_via_email(message_ref: str, correlation_key: str):
    """
    Email approval webhook - Process approval (POST)
    User confirms approval via button

    POST /webhooks/approve/approvalRequest/order-12345
    """
    try:
        logger.info(f"📬 ========================================")
        logger.info(f"📬 Email approval CLICKED (POST)")
        logger.info(f"📬 Message ref: {message_ref}")
        logger.info(f"📬 Correlation key: {correlation_key}")
        logger.info(f"📬 Full URL: /webhooks/approve/{message_ref}/{correlation_key}")
        logger.info(f"📬 ========================================")

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

        # Return success HTML page
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Approval Confirmed</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                    max-width: 600px;
                    margin: 50px auto;
                    padding: 20px;
                    text-align: center;
                    background: #f5f5f5;
                }
                .container {
                    background: #d5f4e6;
                    border-radius: 8px;
                    padding: 40px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #27ae60;
                    margin-top: 10px;
                }
                .checkmark {
                    font-size: 64px;
                    color: #27ae60;
                    margin-bottom: 10px;
                }
                p {
                    color: #2c3e50;
                    font-size: 16px;
                    margin: 10px 0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="checkmark">✓</div>
                <h1>Approval Confirmed</h1>
                <p>Your approval has been recorded successfully.</p>
                <p>You may close this window.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    except Exception as e:
        logger.error(f"Error processing email approval: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/webhooks/deny/{message_ref}/{correlation_key}")
async def deny_confirmation_page(message_ref: str, correlation_key: str):
    """
    Email denial webhook - Show confirmation page
    User clicks deny link in email

    GET /webhooks/deny/approvalRequest/order-12345
    Returns HTML page with confirmation button that POSTs
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Denial Confirmation</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                text-align: center;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                border-radius: 8px;
                padding: 40px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #e74c3c;
                margin-bottom: 10px;
            }}
            p {{
                color: #555;
                line-height: 1.6;
                margin-bottom: 25px;
            }}
            .btn {{
                background: #e74c3c;
                color: white;
                border: none;
                padding: 15px 40px;
                font-size: 16px;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.3s;
                font-weight: 600;
            }}
            .btn:hover {{
                background: #c0392b;
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }}
            .btn-cancel {{
                background: #95a5a6;
                margin-left: 10px;
            }}
            .btn-cancel:hover {{
                background: #7f8c8d;
            }}
            .info {{
                background: #f8f9fa;
                border-left: 4px solid #3498db;
                padding: 15px;
                margin: 25px 0;
                text-align: left;
                border-radius: 4px;
            }}
            .info p {{
                margin: 5px 0;
                font-size: 14px;
            }}
            .info strong {{
                color: #2c3e50;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✗ Confirm Denial</h1>
            <p>You are about to deny this request. Please confirm your decision.</p>

            <div class="info">
                <p><strong>Request ID:</strong> {message_ref}</p>
                <p><strong>Correlation:</strong> {correlation_key[:8] if correlation_key else 'N/A'}...</p>
            </div>

            <form method="POST" action="/webhooks/deny/{message_ref}/{correlation_key}">
                <button type="submit" class="btn">Deny</button>
                <button type="button" class="btn btn-cancel" onclick="window.close()">Cancel</button>
            </form>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/webhooks/deny/{message_ref}/{correlation_key}")
async def deny_via_email(message_ref: str, correlation_key: str):
    """
    Email denial webhook - Process denial (POST)
    User confirms denial via button

    POST /webhooks/deny/approvalRequest/order-12345
    """
    try:
        logger.info(f"Email denial (POST): {message_ref}, correlation: {correlation_key}")

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

        # Return success HTML page
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Denial Confirmed</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                    max-width: 600px;
                    margin: 50px auto;
                    padding: 20px;
                    text-align: center;
                    background: #f5f5f5;
                }
                .container {
                    background: #fadbd8;
                    border-radius: 8px;
                    padding: 40px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #e74c3c;
                    margin-top: 10px;
                }
                .crossmark {
                    font-size: 64px;
                    color: #e74c3c;
                    margin-bottom: 10px;
                }
                p {
                    color: #2c3e50;
                    font-size: 16px;
                    margin: 10px 0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="crossmark">✗</div>
                <h1>Denial Confirmed</h1>
                <p>Your denial has been recorded successfully.</p>
                <p>You may close this window.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    except Exception as e:
        logger.error(f"Error processing email denial: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# Email Approval Webhook (Simple Query Parameter Version)
# ========================================

@app.get("/webhook/approval/{workflow_instance_id}")
async def email_approval_webhook(
    workflow_instance_id: str,
    decision: str = Query(..., description="approved or rejected")
):
    """
    Simple email approval webhook for Event-Based Gateway workflows

    Called when user clicks approval/rejection link in email.
    Sends message to diagnosticApproval queue with workflow instance ID correlation.

    Example:
        GET /webhook/approval/wf-2026-001?decision=approved
    """
    try:
        logger.info(f"📧 Email approval webhook triggered: {workflow_instance_id} → {decision}")

        # Validate decision
        if decision not in ["approved", "rejected"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid decision: {decision}. Must be 'approved' or 'rejected'"
            )

        # Prepare message payload
        message_payload = {
            "decision": decision,
            "approver": "email-user",  # Could be extracted from auth if available
            "method": "email-link",
            "timestamp": datetime.utcnow().isoformat()
        }

        # Send message to message queue for Event-Based Gateway
        # Message ref: "diagnosticApproval" (from workflow YAML)
        # Correlation key: workflow instance ID
        message_ref = "diagnosticApproval"
        correlation_key = workflow_instance_id
        correlation_id = f"{message_ref}:{correlation_key}"

        # Find the workflow instance
        if workflow_instance_id not in active_workflows:
            logger.error(f"❌ Workflow instance not found: {workflow_instance_id}")
            raise HTTPException(status_code=404, detail=f"Workflow instance not found: {workflow_instance_id}")

        engine = active_workflows[workflow_instance_id]

        # Create queue if it doesn't exist
        if correlation_id not in engine.message_queues:
            engine.message_queues[correlation_id] = asyncio.Queue()

        # Put message in queue
        await engine.message_queues[correlation_id].put(message_payload)

        logger.info(f"✅ Message sent to queue: {correlation_id}")
        logger.info(f"   Decision: {decision}")
        logger.info(f"   Payload: {message_payload}")

        # Return success HTML page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Approval {'Accepted' if decision == 'approved' else 'Rejected'}</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                    max-width: 600px;
                    margin: 50px auto;
                    padding: 20px;
                    text-align: center;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    border-radius: 8px;
                    padding: 40px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: {'#27ae60' if decision == 'approved' else '#e74c3c'};
                    margin-bottom: 10px;
                    font-size: 32px;
                }}
                .icon {{
                    font-size: 64px;
                    margin-bottom: 20px;
                }}
                p {{
                    color: #555;
                    line-height: 1.6;
                    margin-bottom: 15px;
                }}
                .info {{
                    background: #f8f9fa;
                    border-left: 4px solid #3498db;
                    padding: 15px;
                    margin: 25px 0;
                    text-align: left;
                    border-radius: 4px;
                }}
                .info p {{
                    margin: 5px 0;
                    font-size: 14px;
                }}
                .info strong {{
                    color: #2c3e50;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">{'✅' if decision == 'approved' else '❌'}</div>
                <h1>{'Approved!' if decision == 'approved' else 'Rejected'}</h1>
                <p>Your decision has been recorded successfully.</p>

                <div class="info">
                    <p><strong>Workflow ID:</strong> {workflow_instance_id}</p>
                    <p><strong>Decision:</strong> {decision.upper()}</p>
                    <p><strong>Method:</strong> Email Link</p>
                </div>

                <p style="margin-top: 30px; font-size: 14px; color: #7f8c8d;">
                    {'The workflow will now proceed with playbook generation.' if decision == 'approved' else 'The workflow has been stopped. No playbook will be generated.'}
                </p>

                <p style="margin-top: 20px; font-size: 12px; color: #95a5a6;">
                    You can safely close this window.
                </p>
            </div>
        </body>
        </html>
        """

        return HTMLResponse(content=html_content)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing email approval: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# Static File Serving (must be at the end!)
# ========================================

@app.get("/")
async def root():
    """Serve the main UI (index.html)"""
    index_path = BASE_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html")
    else:
        # Fallback to API info if index.html not found
        return {
            "status": "running",
            "service": "BPMN Workflow Execution Engine",
            "version": "1.0.0",
            "active_workflows": len(active_workflows),
            "note": "index.html not found - UI not available"
        }


@app.get("/{file_path:path}")
async def serve_static(file_path: str):
    """Serve static files (CSS, JS, images) from project root

    This must be the LAST route defined to act as a catch-all.
    """
    # Skip if it looks like an API endpoint
    if file_path.startswith(("api/", "workflows/", "webhooks/", "ws", "health")):
        raise HTTPException(status_code=404, detail="API endpoint not found")

    static_file_path = BASE_DIR / file_path

    # Security check - prevent directory traversal
    try:
        static_file_path = static_file_path.resolve()
        base_resolved = BASE_DIR.resolve()

        # Ensure the resolved path is within BASE_DIR
        if not str(static_file_path).startswith(str(base_resolved)):
            raise HTTPException(status_code=403, detail="Access forbidden")
    except Exception as e:
        logger.warning(f"Error resolving path {file_path}: {e}")
        raise HTTPException(status_code=404, detail="File not found")

    # Serve the file if it exists
    if static_file_path.is_file():
        # Determine media type based on file extension
        import mimetypes
        media_type, _ = mimetypes.guess_type(str(static_file_path))

        return FileResponse(
            str(static_file_path),
            media_type=media_type or "application/octet-stream"
        )

    # File not found
    raise HTTPException(status_code=404, detail=f"File not found: {file_path}")


if __name__ == "__main__":
    # Run the server
    logger.info("Starting BPMN Workflow Execution Engine...")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
