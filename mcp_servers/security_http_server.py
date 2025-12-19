#!/usr/bin/env python3
"""
HTTP-based MCP Server for Red Hat Security Data API

Provides REST API endpoints to search CVEs, security advisories, and affected packages
using Red Hat's public Security Data API.

API Documentation: https://access.redhat.com/documentation/en-us/red_hat_security_data_api/

Run with: python security_http_server.py
Default port: 8001
"""

import json
import sys
from typing import Any, Dict, List, Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


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
    title="Red Hat Security MCP Server",
    description="HTTP-based MCP server for Red Hat Security Data API",
    version="2.0.0",
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "name": "Red Hat Security MCP Server",
        "version": "2.0.0",
        "status": "running",
        "tools_count": 4,
    }


@app.get("/tools", response_model=List[ToolInfo])
async def list_tools():
    """List available security tools"""
    return [
        ToolInfo(
            name="search_cve",
            description="Search Red Hat CVE database for vulnerabilities by CVE ID or package name",
            input_schema={
                "type": "object",
                "properties": {
                    "cve_id": {
                        "type": "string",
                        "description": "CVE ID (e.g., CVE-2024-1234). Use this OR package, not both.",
                    },
                    "package": {
                        "type": "string",
                        "description": "Package name to search vulnerabilities for (e.g., openssl, nginx)",
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "important", "moderate", "low"],
                        "description": "Filter by severity level (only works with package search)",
                    },
                },
            },
        ),
        ToolInfo(
            name="get_rhsa",
            description="Get Red Hat Security Advisory (RHSA) details including affected products and CVEs",
            input_schema={
                "type": "object",
                "properties": {
                    "advisory_id": {
                        "type": "string",
                        "description": "RHSA ID (e.g., RHSA-2024:1234)",
                    }
                },
                "required": ["advisory_id"],
            },
        ),
        ToolInfo(
            name="search_affected_packages",
            description="Find which RHEL packages and versions are affected by a specific CVE",
            input_schema={
                "type": "object",
                "properties": {
                    "cve_id": {
                        "type": "string",
                        "description": "CVE ID (e.g., CVE-2024-1234)",
                    },
                    "rhel_version": {
                        "type": "string",
                        "description": "Filter by RHEL major version (e.g., '8', '9')",
                    },
                },
                "required": ["cve_id"],
            },
        ),
        ToolInfo(
            name="get_errata",
            description="Get errata information by ID (RHSA, RHBA, or RHEA)",
            input_schema={
                "type": "object",
                "properties": {
                    "errata_id": {
                        "type": "string",
                        "description": "Errata ID (e.g., RHSA-2024:1234, RHBA-2024:5678)",
                    }
                },
                "required": ["errata_id"],
            },
        ),
    ]


@app.post("/call", response_model=ToolCallResponse)
async def call_tool(request: ToolCallRequest):
    """Call a tool with arguments"""
    try:
        if request.tool_name == "search_cve":
            result = await search_cve(request.arguments)
        elif request.tool_name == "get_rhsa":
            result = await get_rhsa(request.arguments)
        elif request.tool_name == "search_affected_packages":
            result = await search_affected_packages(request.arguments)
        elif request.tool_name == "get_errata":
            result = await get_errata(request.arguments)
        else:
            raise HTTPException(status_code=404, detail=f"Tool not found: {request.tool_name}")

        return ToolCallResponse(success=True, result=result)

    except Exception as e:
        return ToolCallResponse(success=False, result=None, error=str(e))


# ===== Tool Implementations =====

async def search_cve(args: dict) -> dict:
    """Search Red Hat CVE database"""
    base_url = "https://access.redhat.com/hydra/rest/securitydata"

    async with httpx.AsyncClient(timeout=30.0) as client:
        if "cve_id" in args:
            # Get specific CVE
            cve_id = args["cve_id"]
            url = f"{base_url}/cve/{cve_id}.json"

            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                # Extract description
                description = None
                if isinstance(data.get("bugzilla"), dict):
                    description = data["bugzilla"].get("description")
                elif data.get("bugzilla_description"):
                    description = data.get("bugzilla_description")

                if not description and data.get("details"):
                    details = data.get("details")
                    if isinstance(details, list) and len(details) > 0:
                        description = details[0] if isinstance(details[0], str) else details[0].get("value")

                # Extract mitigation
                mitigation = data.get("mitigation")
                if isinstance(mitigation, dict):
                    mitigation = mitigation.get("value")

                result = {
                    "cve_id": data.get("name") or data.get("CVE"),
                    "severity": data.get("threat_severity") or data.get("severity"),
                    "cvss3_score": data.get("cvss3", {}).get("cvss3_base_score"),
                    "cvss3_vector": data.get("cvss3", {}).get("cvss3_scoring_vector"),
                    "description": description,
                    "affected_packages": [
                        {
                            "product": pkg.get("product_name"),
                            "package": pkg.get("package"),
                            "advisory": pkg.get("advisory"),
                        }
                        for pkg in data.get("affected_release", [])
                    ],
                    "package_state": [
                        {
                            "product": state.get("product_name"),
                            "fix_state": state.get("fix_state"),
                            "package": state.get("package_name"),
                        }
                        for state in data.get("package_state", [])
                    ],
                    "advisories": data.get("advisories", []),
                    "public_date": data.get("public_date"),
                    "mitigation": mitigation,
                    "references": data.get("references", []),
                    "cwe": data.get("CWE"),
                    "statement": data.get("statement"),
                    "acknowledgement": data.get("acknowledgement"),
                }

                return result

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return {"error": f"CVE {cve_id} not found in Red Hat database"}
                raise

        elif "package" in args:
            # Search by package name
            url = f"{base_url}/cve.json"
            params = {"package": args["package"]}

            if "severity" in args:
                params["severity"] = args["severity"]

            response = await client.get(url, params=params)
            response.raise_for_status()
            cves = response.json()

            # Limit results
            cves = cves[:10]

            result = {
                "package": args["package"],
                "cve_count": len(cves),
                "cves": [
                    {
                        "cve_id": cve.get("CVE"),
                        "severity": cve.get("severity"),
                        "public_date": cve.get("public_date"),
                        "bugzilla_description": cve.get("bugzilla_description"),
                    }
                    for cve in cves
                ],
            }

            return result
        else:
            return {"error": "Must provide either cve_id or package"}


async def get_rhsa(args: dict) -> dict:
    """Get RHSA advisory details"""
    advisory_id = args["advisory_id"]
    base_url = "https://access.redhat.com/hydra/rest/securitydata"

    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{base_url}/cvrf/{advisory_id}.json"

        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            # Extract key information
            doc = data.get("cvrfdoc", {})
            result = {
                "advisory_id": advisory_id,
                "title": doc.get("document_title"),
                "severity": doc.get("aggregate_severity"),
                "issued_date": doc.get("document_tracking", {}).get("current_release_date"),
                "cves": [vuln.get("cve") for vuln in doc.get("vulnerability", []) if vuln.get("cve")],
                "affected_products": [
                    branch.get("full_product_name", {}).get("text")
                    for branch in doc.get("product_tree", {}).get("branch", [])
                ],
                "references": doc.get("references", []),
            }

            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"error": f"Advisory {advisory_id} not found"}
            raise


async def search_affected_packages(args: dict) -> dict:
    """Find affected packages for a CVE"""
    cve_id = args["cve_id"]
    base_url = "https://access.redhat.com/hydra/rest/securitydata"

    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{base_url}/cve/{cve_id}.json"

        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            # Extract affected packages
            affected = data.get("affected_release", [])
            package_state = data.get("package_state", [])

            # Filter by RHEL version if specified
            if "rhel_version" in args:
                rhel_ver = args["rhel_version"]
                affected = [pkg for pkg in affected if rhel_ver in pkg.get("product_name", "")]
                package_state = [pkg for pkg in package_state if rhel_ver in pkg.get("product_name", "")]

            result = {
                "cve_id": cve_id,
                "affected_releases": [
                    {
                        "product": pkg.get("product_name"),
                        "package": pkg.get("package"),
                        "advisory": pkg.get("advisory"),
                        "cpe": pkg.get("cpe"),
                    }
                    for pkg in affected
                ],
                "package_states": [
                    {
                        "product": state.get("product_name"),
                        "package": state.get("package_name"),
                        "fix_state": state.get("fix_state"),
                    }
                    for state in package_state
                ],
            }

            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"error": f"CVE {cve_id} not found"}
            raise


async def get_errata(args: dict) -> dict:
    """Get errata information"""
    errata_id = args["errata_id"]
    base_url = "https://access.redhat.com/hydra/rest/securitydata"

    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{base_url}/cvrf/{errata_id}.json"

        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            doc = data.get("cvrfdoc", {})
            result = {
                "errata_id": errata_id,
                "title": doc.get("document_title"),
                "type": doc.get("document_type"),
                "severity": doc.get("aggregate_severity"),
                "issued_date": doc.get("document_tracking", {}).get("current_release_date"),
                "description": doc.get("notes", [{}])[0].get("text") if doc.get("notes") else None,
                "cves": [vuln.get("cve") for vuln in doc.get("vulnerability", []) if vuln.get("cve")],
            }

            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"error": f"Errata {errata_id} not found"}
            raise


# ===== Main =====

if __name__ == "__main__":
    import os

    port = int(os.getenv("SECURITY_SERVER_PORT", "8001"))

    print("=" * 60)
    print("  Red Hat Security MCP Server (HTTP)")
    print("=" * 60)
    print(f"\nStarting server on http://localhost:{port}")
    print(f"API Docs: http://localhost:{port}/docs")
    print("\nAvailable tools:")
    print("  - search_cve: Search CVE database")
    print("  - get_rhsa: Get security advisory details")
    print("  - search_affected_packages: Find affected packages")
    print("  - get_errata: Get errata information")
    print("\nPress Ctrl+C to stop\n")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
