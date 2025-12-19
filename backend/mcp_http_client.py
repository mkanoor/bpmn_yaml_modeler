"""
HTTP Client for Red Hat MCP Servers

Connects to HTTP-based MCP servers and calls tools via REST API.
"""
import logging
from typing import Any, Dict, List
import httpx

logger = logging.getLogger(__name__)


class MCPHTTPClient:
    """Client for HTTP-based MCP servers"""

    def __init__(self):
        self.base_urls = {
            'security': 'http://localhost:8001',
            'kb': 'http://localhost:8002'
        }
        self.client = httpx.AsyncClient(timeout=30.0)

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool via HTTP"""

        # Determine which server has this tool
        server = self._get_server_for_tool(tool_name)
        if not server:
            raise ValueError(f"Unknown tool: {tool_name}")

        base_url = self.base_urls[server]

        try:
            # Call the tool
            response = await self.client.post(
                f"{base_url}/call",
                json={
                    "tool_name": tool_name,
                    "arguments": arguments
                }
            )
            response.raise_for_status()

            result = response.json()

            if not result.get('success'):
                raise Exception(result.get('error', 'Tool call failed'))

            logger.info(f"MCP tool {tool_name} executed successfully")
            return result['result']

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling {tool_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error calling {tool_name}: {e}")
            raise

    def _get_server_for_tool(self, tool_name: str) -> str:
        """Determine which server provides this tool"""
        security_tools = ['search_cve', 'get_rhsa', 'search_affected_packages', 'get_errata']
        kb_tools = ['search_kb', 'get_kb_article', 'search_solutions', 'search_by_symptom']

        if tool_name in security_tools:
            return 'security'
        elif tool_name in kb_tools:
            return 'kb'
        else:
            return None

    async def get_tools(self, server: str) -> List[Dict[str, Any]]:
        """Get list of available tools from a server"""
        base_url = self.base_urls.get(server)
        if not base_url:
            raise ValueError(f"Unknown server: {server}")

        try:
            response = await self.client.get(f"{base_url}/tools")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting tools from {server}: {e}")
            raise

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
