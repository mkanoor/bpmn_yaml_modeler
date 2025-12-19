#!/usr/bin/env python3
"""
HTTP-based MCP Server for Red Hat Customer Portal API

Provides REST API endpoints to search Knowledge Base articles and solutions.

Note: Some endpoints may require Red Hat customer credentials.
Set REDHAT_USERNAME and REDHAT_PASSWORD environment variables if needed.

API Documentation: https://access.redhat.com/documentation/en-us/red_hat_customer_portal/1/html-single/red_hat_customer_portal_api_guide/

Run with: python kb_http_server.py
Default port: 8002
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


# ===== Configuration =====

REDHAT_USERNAME = os.getenv("REDHAT_USERNAME")
REDHAT_PASSWORD = os.getenv("REDHAT_PASSWORD")


# ===== API Models =====

class ToolInfo(BaseModel):
    """Tool metadata"""
    name: str
    description: str
    input_schema: Dict[str, Any]


class ToolCallRequest(BaseModel):
    """Request to call a tool"""
    tool_name: str
    arguments: Dict[str, Any]


class ToolCallResponse(BaseModel):
    """Response from tool call"""
    success: bool
    result: Any
    error: Optional[str] = None


# ===== FastAPI App =====

app = FastAPI(
    title="Red Hat Knowledge Base MCP Server",
    description="HTTP-based MCP server for Red Hat Customer Portal API",
    version="2.0.0",
)


@app.get("/")
async def root():
    """Health check endpoint"""
    has_auth = bool(REDHAT_USERNAME and REDHAT_PASSWORD)
    return {
        "name": "Red Hat Knowledge Base MCP Server",
        "version": "2.0.0",
        "status": "running",
        "tools_count": 4,
        "authentication": "configured" if has_auth else "not configured",
    }


@app.get("/tools", response_model=List[ToolInfo])
async def list_tools():
    """List available KB tools"""
    return [
        ToolInfo(
            name="search_kb",
            description="Search Red Hat Knowledge Base for articles and solutions",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (error message, topic, keywords)",
                    },
                    "product": {
                        "type": "string",
                        "description": "Filter by product name (e.g., 'Red Hat Enterprise Linux 9')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": ["query"],
            },
        ),
        ToolInfo(
            name="get_kb_article",
            description="Get full Red Hat KB article or solution by ID",
            input_schema={
                "type": "object",
                "properties": {
                    "article_id": {
                        "type": "string",
                        "description": "KB article/solution ID (numeric)",
                    }
                },
                "required": ["article_id"],
            },
        ),
        ToolInfo(
            name="search_solutions",
            description="Search for solutions to specific error messages or problems",
            input_schema={
                "type": "object",
                "properties": {
                    "error_message": {
                        "type": "string",
                        "description": "Error message from logs or system",
                    },
                    "product_version": {
                        "type": "string",
                        "description": "RHEL version (e.g., 'RHEL 8', 'RHEL 9')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of solutions to return",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["error_message"],
            },
        ),
        ToolInfo(
            name="search_by_symptom",
            description="Search KB articles by symptom or issue description",
            input_schema={
                "type": "object",
                "properties": {
                    "symptom": {
                        "type": "string",
                        "description": "Symptom description (e.g., 'service crash', 'high CPU usage')",
                    },
                    "component": {
                        "type": "string",
                        "description": "Affected component or service (e.g., 'nginx', 'systemd')",
                    },
                },
                "required": ["symptom"],
            },
        ),
    ]


@app.post("/call", response_model=ToolCallResponse)
async def call_tool(request: ToolCallRequest):
    """Call a tool with arguments"""
    try:
        if request.tool_name == "search_kb":
            result = await search_kb(request.arguments)
        elif request.tool_name == "get_kb_article":
            result = await get_kb_article(request.arguments)
        elif request.tool_name == "search_solutions":
            result = await search_solutions(request.arguments)
        elif request.tool_name == "search_by_symptom":
            result = await search_by_symptom(request.arguments)
        else:
            raise HTTPException(status_code=404, detail=f"Tool not found: {request.tool_name}")

        return ToolCallResponse(success=True, result=result)

    except Exception as e:
        return ToolCallResponse(success=False, result=None, error=str(e))


# ===== Helper Functions =====

def get_auth() -> Optional[tuple]:
    """Get authentication credentials if available"""
    if REDHAT_USERNAME and REDHAT_PASSWORD:
        return (REDHAT_USERNAME, REDHAT_PASSWORD)
    return None


# ===== Tool Implementations =====

async def search_kb(args: dict) -> dict:
    """Search Red Hat Knowledge Base"""
    base_url = "https://access.redhat.com/hydra/rest/search/kcs"

    query = args["query"]
    limit = args.get("limit", 10)

    params = {
        "q": query,
        "rows": limit,
        "fl": "id,allTitle,abstract,documentKind,view_uri,lastModifiedDate"
    }

    if "product" in args:
        params["fq"] = f'product:"{args["product"]}"'

    auth = get_auth()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(base_url, params=params, auth=auth)
            response.raise_for_status()
            data = response.json()

            results = data.get("response", {}).get("docs", [])
            total_found = data.get("response", {}).get("numFound", 0)

            result = {
                "query": query,
                "total_results": total_found,
                "returned_results": len(results),
                "product_filter": args.get("product"),
                "articles": [
                    {
                        "id": doc.get("id"),
                        "title": doc.get("allTitle"),
                        "abstract": doc.get("abstract"),
                        "type": doc.get("documentKind"),
                        "url": doc.get("view_uri"),
                        "last_modified": doc.get("lastModifiedDate"),
                    }
                    for doc in results
                ],
            }

            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return {"error": "Authentication required. Set REDHAT_USERNAME and REDHAT_PASSWORD."}
            raise


async def get_kb_article(args: dict) -> dict:
    """Get KB article details"""
    article_id = args["article_id"]
    base_url = "https://access.redhat.com/hydra/rest/search/kcs"

    params = {"q": f"id:{article_id}", "fl": "id,allTitle,abstract,body,documentKind,view_uri,lastModifiedDate"}

    auth = get_auth()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(base_url, params=params, auth=auth)
            response.raise_for_status()
            data = response.json()

            docs = data.get("response", {}).get("docs", [])

            if not docs:
                return {"error": f"Article {article_id} not found"}

            doc = docs[0]
            result = {
                "id": doc.get("id"),
                "title": doc.get("allTitle"),
                "abstract": doc.get("abstract"),
                "body": doc.get("body"),
                "type": doc.get("documentKind"),
                "url": doc.get("view_uri"),
                "last_modified": doc.get("lastModifiedDate"),
            }

            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return {"error": "Authentication required. Set REDHAT_USERNAME and REDHAT_PASSWORD."}
            raise


async def search_solutions(args: dict) -> dict:
    """Search for solutions to error messages"""
    error_message = args["error_message"]
    limit = args.get("limit", 5)

    # Build search query focusing on solutions
    query = f'"{error_message}" AND documentKind:Solution'

    if "product_version" in args:
        query += f' AND product:"{args["product_version"]}"'

    base_url = "https://access.redhat.com/hydra/rest/search/kcs"
    params = {
        "q": query,
        "rows": limit,
        "fl": "id,allTitle,abstract,documentKind,view_uri,lastModifiedDate,resolution"
    }

    auth = get_auth()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(base_url, params=params, auth=auth)
            response.raise_for_status()
            data = response.json()

            results = data.get("response", {}).get("docs", [])
            total_found = data.get("response", {}).get("numFound", 0)

            result = {
                "error_message": error_message,
                "total_solutions": total_found,
                "returned_solutions": len(results),
                "solutions": [
                    {
                        "id": doc.get("id"),
                        "title": doc.get("allTitle"),
                        "abstract": doc.get("abstract"),
                        "resolution": doc.get("resolution"),
                        "url": doc.get("view_uri"),
                        "last_modified": doc.get("lastModifiedDate"),
                    }
                    for doc in results
                ],
            }

            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return {"error": "Authentication required. Set REDHAT_USERNAME and REDHAT_PASSWORD."}
            raise


async def search_by_symptom(args: dict) -> dict:
    """Search KB by symptom description"""
    symptom = args["symptom"]
    component = args.get("component")

    # Build search query
    query = f'"{symptom}"'
    if component:
        query += f' AND "{component}"'

    base_url = "https://access.redhat.com/hydra/rest/search/kcs"
    params = {
        "q": query,
        "rows": 10,
        "fl": "id,allTitle,abstract,documentKind,view_uri,lastModifiedDate"
    }

    auth = get_auth()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(base_url, params=params, auth=auth)
            response.raise_for_status()
            data = response.json()

            results = data.get("response", {}).get("docs", [])
            total_found = data.get("response", {}).get("numFound", 0)

            result = {
                "symptom": symptom,
                "component": component,
                "total_results": total_found,
                "returned_results": len(results),
                "articles": [
                    {
                        "id": doc.get("id"),
                        "title": doc.get("allTitle"),
                        "abstract": doc.get("abstract"),
                        "type": doc.get("documentKind"),
                        "url": doc.get("view_uri"),
                        "last_modified": doc.get("lastModifiedDate"),
                    }
                    for doc in results
                ],
            }

            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return {"error": "Authentication required. Set REDHAT_USERNAME and REDHAT_PASSWORD."}
            raise


# ===== Main =====

if __name__ == "__main__":
    port = int(os.getenv("KB_SERVER_PORT", "8002"))

    print("=" * 60)
    print("  Red Hat Knowledge Base MCP Server (HTTP)")
    print("=" * 60)
    print(f"\nStarting server on http://localhost:{port}")
    print(f"API Docs: http://localhost:{port}/docs")

    if REDHAT_USERNAME and REDHAT_PASSWORD:
        print(f"✓ Authentication: Configured (user: {REDHAT_USERNAME})")
    else:
        print("⚠️  Authentication: Not configured (some features may be limited)")
        print("   Set REDHAT_USERNAME and REDHAT_PASSWORD environment variables")

    print("\nAvailable tools:")
    print("  - search_kb: Search Knowledge Base")
    print("  - get_kb_article: Get article details")
    print("  - search_solutions: Find solutions to errors")
    print("  - search_by_symptom: Search by symptom")
    print("\nPress Ctrl+C to stop\n")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
