"""
MCP Client for communicating with stdio-based MCP servers.

This client manages connections to multiple MCP servers and routes
tool execution requests to the appropriate server.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import subprocess

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    command: List[str]  # e.g., ["python", "mcp_servers/redhat_security_server.py"]
    tools: List[str]  # Tool names this server provides


class MCPClient:
    """Client for managing MCP server connections and tool execution."""

    def __init__(self):
        self.servers: Dict[str, MCPServerConnection] = {}
        self.tool_to_server: Dict[str, str] = {}  # Map tool name to server name

    async def add_server(self, config: MCPServerConfig):
        """Add and start an MCP server connection."""
        try:
            logger.info(f"Starting MCP server: {config.name}")
            connection = MCPServerConnection(config)
            await connection.start()

            self.servers[config.name] = connection

            # Map each tool to this server
            for tool in config.tools:
                self.tool_to_server[tool] = config.name
                logger.info(f"  Registered tool: {tool} -> {config.name}")

            logger.info(f"✅ MCP server started: {config.name}")

        except Exception as e:
            logger.error(f"Failed to start MCP server {config.name}: {e}")
            raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on the appropriate MCP server."""
        # Find which server provides this tool
        server_name = self.tool_to_server.get(tool_name)

        if not server_name:
            raise ValueError(f"Unknown tool: {tool_name}")

        connection = self.servers.get(server_name)
        if not connection:
            raise RuntimeError(f"Server not connected: {server_name}")

        logger.info(f"Calling tool {tool_name} on server {server_name}")
        logger.debug(f"  Arguments: {arguments}")

        try:
            result = await connection.call_tool(tool_name, arguments)
            logger.info(f"✅ Tool {tool_name} completed successfully")
            logger.debug(f"  Result: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ Tool {tool_name} failed: {e}")
            raise

    async def list_tools(self) -> List[str]:
        """Get list of all available tools across all servers."""
        return list(self.tool_to_server.keys())

    async def shutdown(self):
        """Shutdown all MCP server connections."""
        logger.info("Shutting down MCP client...")
        for name, connection in self.servers.items():
            try:
                await connection.stop()
                logger.info(f"  Stopped server: {name}")
            except Exception as e:
                logger.error(f"  Error stopping {name}: {e}")

        self.servers.clear()
        self.tool_to_server.clear()


class MCPServerConnection:
    """Manages connection to a single MCP server via stdio."""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self._lock = asyncio.Lock()

    async def start(self):
        """Start the MCP server process."""
        try:
            # Start server process with stdio pipes
            self.process = await asyncio.create_subprocess_exec(
                *self.config.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            logger.info(f"Server process started (PID: {self.process.pid})")

            # TODO: Initialize MCP protocol handshake if needed
            # For now, assume server is ready after startup
            await asyncio.sleep(0.5)  # Give server time to initialize

        except Exception as e:
            logger.error(f"Failed to start server process: {e}")
            raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on this MCP server."""
        async with self._lock:
            self.request_id += 1
            request_id = self.request_id

            # Create MCP tool call request
            request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            # Send request to server
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()

            logger.debug(f"Sent request: {request}")

            # Read response from server
            response_line = await self.process.stdout.readline()
            response_json = response_line.decode().strip()

            if not response_json:
                raise RuntimeError("Empty response from MCP server")

            response = json.loads(response_json)
            logger.debug(f"Received response: {response}")

            # Check for errors
            if "error" in response:
                error = response["error"]
                raise RuntimeError(f"MCP error: {error.get('message', error)}")

            # Extract result
            if "result" not in response:
                raise RuntimeError("No result in MCP response")

            return response["result"]

    async def stop(self):
        """Stop the MCP server process."""
        if self.process:
            try:
                # Send shutdown request
                request = {
                    "jsonrpc": "2.0",
                    "method": "shutdown"
                }
                request_json = json.dumps(request) + "\n"
                self.process.stdin.write(request_json.encode())
                await self.process.stdin.drain()

                # Wait for graceful shutdown
                await asyncio.wait_for(self.process.wait(), timeout=5.0)

            except asyncio.TimeoutError:
                # Force kill if graceful shutdown times out
                logger.warning(f"Force killing server process {self.process.pid}")
                self.process.kill()
                await self.process.wait()

            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
                if self.process.returncode is None:
                    self.process.kill()
                    await self.process.wait()

            finally:
                self.process = None


# Tool name mapping - maps workflow tool names to actual MCP tool names
TOOL_NAME_MAPPING = {
    # Workflow tools -> MCP server tools
    "grep-search": "search_cve",  # Map to security server's CVE search
    "regex-match": "search_cve",  # Also use CVE search for pattern matching
    "log-parser": "search_solutions",  # Map to KB server's solution search
    "error-classifier": "search_by_symptom",  # Map to KB server's symptom search
    "security-lookup": "search_cve",  # Direct mapping to security server
    "kb-search": "search_kb",  # Direct mapping to KB server
}


def create_default_mcp_client() -> MCPClient:
    """
    Create MCP client with default server configurations.

    This configures connections to:
    - Red Hat Security Server (CVE and security advisories)
    - Red Hat Knowledge Base Server (articles and solutions)
    """
    client = MCPClient()

    # Note: Servers will be added asynchronously via add_server()
    # This just creates the client instance

    return client


async def initialize_mcp_servers(client: MCPClient):
    """Initialize all MCP servers."""

    # Red Hat Security Server
    security_config = MCPServerConfig(
        name="redhat_security",
        command=["python", "mcp_servers/redhat_security_server.py"],
        tools=["search_cve", "get_rhsa", "search_affected_packages", "get_errata"]
    )

    # Red Hat Knowledge Base Server
    kb_config = MCPServerConfig(
        name="redhat_kb",
        command=["python", "mcp_servers/redhat_kb_server.py"],
        tools=["search_kb", "get_kb_article", "search_solutions", "search_by_symptom"]
    )

    # Start both servers
    await client.add_server(security_config)
    await client.add_server(kb_config)

    logger.info("✅ All MCP servers initialized")
