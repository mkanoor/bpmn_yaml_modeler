#!/usr/bin/env python3
"""
MCP Server for Red Hat Security Data API

Provides tools to search CVEs, security advisories, and affected packages
using Red Hat's public Security Data API.

API Documentation: https://access.redhat.com/documentation/en-us/red_hat_security_data_api/
"""

import asyncio
import json
import sys
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


app = Server("redhat-security")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Red Hat Security API tools"""
    return [
        Tool(
            name="search_cve",
            description="Search Red Hat CVE database for vulnerabilities by CVE ID or package name",
            inputSchema={
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
        Tool(
            name="get_rhsa",
            description="Get Red Hat Security Advisory (RHSA) details including affected products and CVEs",
            inputSchema={
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
        Tool(
            name="search_affected_packages",
            description="Find which RHEL packages and versions are affected by a specific CVE",
            inputSchema={
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
        Tool(
            name="get_errata",
            description="Get errata information by ID (RHSA, RHBA, or RHEA)",
            inputSchema={
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


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    try:
        if name == "search_cve":
            return await search_cve(arguments)
        elif name == "get_rhsa":
            return await get_rhsa(arguments)
        elif name == "search_affected_packages":
            return await search_affected_packages(arguments)
        elif name == "get_errata":
            return await get_errata(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def search_cve(args: dict) -> list[TextContent]:
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

                # Extract description from bugzilla or details
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

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return [TextContent(type="text", text=f"CVE {cve_id} not found in Red Hat database")]
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

            result = {
                "package": args["package"],
                "total_cves": len(cves),
                "severity_filter": args.get("severity"),
                "cves": [
                    {
                        "cve_id": cve.get("CVE"),
                        "severity": cve.get("threat_severity") or cve.get("severity"),
                        "cvss3_score": cve.get("cvss3_score"),
                        "public_date": cve.get("public_date"),
                        "bugzilla_description": cve.get("bugzilla_description"),
                        "advisories": cve.get("advisories", []),
                        "resource_url": cve.get("resource_url"),
                    }
                    for cve in cves[:50]  # Limit to 50 for readability
                ],
            }

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

    return [TextContent(type="text", text="No CVE data found. Provide either 'cve_id' or 'package'.")]


async def get_rhsa(args: dict) -> list[TextContent]:
    """Get Red Hat Security Advisory"""
    base_url = "https://access.redhat.com/hydra/rest/securitydata"
    advisory_id = args["advisory_id"]

    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{base_url}/cvrf/{advisory_id}.json"

        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            cvrfdoc = data.get("cvrfdoc", {})

            result = {
                "advisory_id": advisory_id,
                "title": cvrfdoc.get("DocumentTitle"),
                "type": cvrfdoc.get("DocumentType"),
                "severity": cvrfdoc.get("aggregate_severity"),
                "released_on": cvrfdoc.get("DocumentPublisher", {}).get("IssuingAuthority"),
                "cves": [vuln.get("CVE") for vuln in cvrfdoc.get("Vulnerability", [])],
                "affected_products": [
                    branch.get("FullProductName", {}).get("content")
                    for branch in cvrfdoc.get("ProductTree", {}).get("Branch", [])
                    if "FullProductName" in branch
                ],
                "references": [
                    {"type": ref.get("Type"), "url": ref.get("URL")}
                    for ref in cvrfdoc.get("References", [])
                ],
            }

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return [TextContent(type="text", text=f"Advisory {advisory_id} not found")]
            raise


async def search_affected_packages(args: dict) -> list[TextContent]:
    """Find affected packages for a CVE"""
    cve_id = args["cve_id"]
    base_url = "https://access.redhat.com/hydra/rest/securitydata"

    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{base_url}/cve/{cve_id}.json"

        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            affected = data.get("affected_release", [])

            # Filter by RHEL version if specified
            if "rhel_version" in args:
                rhel_version = args["rhel_version"]
                affected = [
                    pkg
                    for pkg in affected
                    if f"Red Hat Enterprise Linux {rhel_version}" in pkg.get("product_name", "")
                    or f"RHEL {rhel_version}" in pkg.get("product_name", "")
                ]

            package_state = data.get("package_state", [])
            if "rhel_version" in args:
                rhel_version = args["rhel_version"]
                package_state = [
                    state
                    for state in package_state
                    if f"Red Hat Enterprise Linux {rhel_version}" in state.get("product_name", "")
                    or f"RHEL {rhel_version}" in state.get("product_name", "")
                ]

            result = {
                "cve_id": cve_id,
                "severity": data.get("severity"),
                "rhel_version_filter": args.get("rhel_version"),
                "affected_releases": [
                    {
                        "product": pkg.get("product_name"),
                        "package": pkg.get("package"),
                        "advisory": pkg.get("advisory"),
                        "cpe": pkg.get("cpe"),
                        "release_date": pkg.get("release_date"),
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

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return [TextContent(type="text", text=f"CVE {cve_id} not found")]
            raise


async def get_errata(args: dict) -> list[TextContent]:
    """Get errata information"""
    errata_id = args["errata_id"]

    # Use CVRF endpoint which works for all errata types
    return await get_rhsa({"advisory_id": errata_id})


async def main():
    """Main entry point for the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
