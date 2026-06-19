"""MCP (Model Context Protocol) tool adapter.

Wraps a single tool from an MCP server as a BaseTool, allowing any MCP server
to register its tools in the session's ToolRegistry transparently.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.tools.base import BaseTool, ToolOutput
from app.tools.sanitizer import sanitize_tool_output


class MCPServerConfig:
    def __init__(self, name: str, url: str, auth_token: str = "") -> None:
        self.name = name
        self.url = url.rstrip("/")
        self.auth_token = auth_token

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers


class MCPToolAdapter(BaseTool):
    """Wraps a single tool from an MCP server as a BaseTool."""

    def __init__(
        self,
        server: MCPServerConfig,
        tool_name: str,
        tool_description: str,
        tool_schema: dict[str, Any],
    ) -> None:
        self._server = server
        self.name = tool_name
        self.description = tool_description
        self.input_schema = tool_schema

    async def execute(self, input: dict[str, Any]) -> ToolOutput:
        try:
            result = await self._call_mcp_tool(input)
            sanitized_content = sanitize_tool_output(result.get("content", ""))
            return ToolOutput(
                content=sanitized_content,
                metadata={
                    "mcp_server": self._server.name,
                    "tool_name": self.name,
                    "raw_metadata": result.get("metadata", {}),
                },
                error=result.get("error"),
            )
        except Exception as exc:
            return ToolOutput(
                content=f"MCP tool call failed: {exc}",
                metadata={"mcp_server": self._server.name, "tool_name": self.name},
                error=str(exc),
            )

    async def _call_mcp_tool(self, input: dict[str, Any]) -> dict[str, Any]:
        """Call the MCP server tool endpoint using the MCP protocol."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": self.name,
                "arguments": input,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._server.url}/mcp",
                json=payload,
                headers=self._server._headers(),
            )
            response.raise_for_status()
            data = response.json()

        if "error" in data:
            error = data["error"]
            raise RuntimeError(f"MCP error {error.get('code')}: {error.get('message')}")

        result = data.get("result", {})
        content_parts = result.get("content", [])
        content_text = ""
        for part in content_parts:
            if isinstance(part, dict) and part.get("type") == "text":
                content_text += part.get("text", "")
            elif isinstance(part, str):
                content_text += part

        return {"content": content_text, "metadata": result.get("metadata", {})}


async def fetch_mcp_tools(server: MCPServerConfig) -> list[MCPToolAdapter]:
    """Connect to an MCP server and return all its tools as MCPToolAdapter instances."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{server.url}/mcp",
                json=payload,
                headers=server._headers(),
            )
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch tools from MCP server {server.name}: {exc}") from exc

    if "error" in data:
        error = data["error"]
        raise RuntimeError(
            f"MCP server {server.name} returned error: {error.get('message')}"
        )

    tools_data = data.get("result", {}).get("tools", [])
    adapters: list[MCPToolAdapter] = []

    for tool_def in tools_data:
        adapter = MCPToolAdapter(
            server=server,
            tool_name=tool_def["name"],
            tool_description=tool_def.get("description", ""),
            tool_schema=tool_def.get("inputSchema", {"type": "object", "properties": {}}),
        )
        adapters.append(adapter)

    return adapters
