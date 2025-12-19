#!/usr/bin/env python3
"""
MCP Server for Red Hat Customer Portal API

Provides tools to search Knowledge Base articles and solutions.

Note: Some endpoints require Red Hat customer credentials.
Set REDHAT_USERNAME and REDHAT_PASSWORD environment variables if needed.

API Documentation: https://access.redhat.com/documentation/en-us/red_hat_customer_portal/1/html-single/red_hat_customer_portal_api_guide/
"""

import asyncio
import json
import os
import sys
from typing import Any, Optional

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


app = Server("redhat-kb")

# Optional credentials for authenticated endpoints
REDHAT_USERNAME = os.getenv("REDHAT_USERNAME")
REDHAT_PASSWORD = os.getenv("REDHAT_PASSWORD")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Red Hat KB tools"""
    return [
        Tool(
            name="search_kb",
            description="Search Red Hat Knowledge Base for articles and solutions",
            inputSchema={
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
        Tool(
            name="get_kb_article",
            description="Get full Red Hat KB article or solution by ID",
            inputSchema={
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
        Tool(
            name="search_solutions",
            description="Search for solutions to specific error messages or problems",
            inputSchema={
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
        Tool(
            name="search_by_symptom",
            description="Search KB articles by symptom or issue description",
            inputSchema={
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


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    try:
        if name == "search_kb":
            return await search_kb(arguments)
        elif name == "get_kb_article":
            return await get_kb_article(arguments)
        elif name == "search_solutions":
            return await search_solutions(arguments)
        elif name == "search_by_symptom":
            return await search_by_symptom(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


def get_auth() -> Optional[tuple[str, str]]:
    """Get authentication credentials if available"""
    if REDHAT_USERNAME and REDHAT_PASSWORD:
        return (REDHAT_USERNAME, REDHAT_PASSWORD)
    return None


async def search_kb(args: dict) -> list[TextContent]:
    """Search Red Hat Knowledge Base"""
    base_url = "https://access.redhat.com/hydra/rest/search/kcs"

    query = args["query"]
    limit = args.get("limit", 10)

    params = {"q": query, "rows": limit, "fl": "id,allTitle,abstract,documentKind,view_uri,lastModifiedDate"}

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
                        "id": article.get("id"),
                        "title": article.get("allTitle"),
                        "abstract": article.get("abstract"),
                        "type": article.get("documentKind"),
                        "url": f"https://access.redhat.com{article.get('view_uri')}"
                        if article.get("view_uri")
                        else None,
                        "last_modified": article.get("lastModifiedDate"),
                    }
                    for article in results
                ],
            }

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return [
                    TextContent(
                        type="text",
                        text="Authentication required. Set REDHAT_USERNAME and REDHAT_PASSWORD environment variables.",
                    )
                ]
            raise


async def get_kb_article(args: dict) -> list[TextContent]:
    """Get specific KB article"""
    article_id = args["article_id"]
    url = f"https://access.redhat.com/hydra/rest/v1/solutions/{article_id}"

    auth = get_auth()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, auth=auth)
            response.raise_for_status()
            article = response.json()

            result = {
                "id": article.get("id"),
                "title": article.get("title"),
                "url": f"https://access.redhat.com/solutions/{article_id}",
                "issue": article.get("issue"),
                "resolution": article.get("resolution"),
                "environment": article.get("environment"),
                "root_cause": article.get("rootCause"),
                "diagnostic_steps": article.get("diagnosticSteps"),
                "last_modified": article.get("lastModifiedDate"),
                "created_date": article.get("createdDate"),
                "case_count": article.get("caseCount"),
                "view_count": article.get("viewCount"),
            }

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return [TextContent(type="text", text=f"Article {article_id} not found")]
            elif e.response.status_code == 401:
                return [
                    TextContent(
                        type="text",
                        text="Authentication required. Set REDHAT_USERNAME and REDHAT_PASSWORD environment variables.",
                    )
                ]
            raise


async def search_solutions(args: dict) -> list[TextContent]:
    """Search for solutions to error messages"""
    error_msg = args["error_message"]
    limit = args.get("limit", 5)

    # Build search query
    query = f'"{error_msg}"'

    if "product_version" in args:
        query += f" {args['product_version']}"

    # Search KB with error message
    search_args = {"query": query, "limit": limit}

    return await search_kb(search_args)


async def search_by_symptom(args: dict) -> list[TextContent]:
    """Search KB articles by symptom"""
    symptom = args["symptom"]

    # Build search query
    query = symptom

    if "component" in args:
        query += f" {args['component']}"

    # Search KB
    search_args = {"query": query, "limit": 10}

    return await search_kb(search_args)


async def main():
    """Main entry point for the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
