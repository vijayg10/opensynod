"""Tool Registry: per-session registry of available tools."""

from __future__ import annotations

from typing import Any

from app.llm.base import ToolDefinition
from app.tools.base import BaseTool


class ToolNotFoundError(KeyError):
    pass


class ToolRegistry:
    """Per-session registry of available tools.

    Each session gets its own ToolRegistry instance built at session start from:
    1. Panel-level tool config (which tools are allowed for this panel)
    2. Org-level MCP server registrations
    3. Session context documents (triggers RAG tool init)
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool. Overwrites any existing tool with the same name."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        """Retrieve a tool by name. Raises ToolNotFoundError if not found."""
        if name not in self._tools:
            raise ToolNotFoundError(f"Tool '{name}' not found in registry. Available: {self.names()}")
        return self._tools[name]

    def names(self) -> list[str]:
        """Return list of registered tool names."""
        return list(self._tools.keys())

    def all_definitions(self) -> list[ToolDefinition]:
        """Return all registered tools as ToolDefinition objects for passing to LLM clients."""
        return [
            ToolDefinition(
                name=tool.name,
                description=tool.description,
                input_schema=tool.input_schema,
            )
            for tool in self._tools.values()
        ]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    @classmethod
    async def build_for_session(
        cls,
        panel_config: dict[str, Any],
        mcp_server_configs: list[dict[str, Any]] | None = None,
        session_documents: list[dict[str, Any]] | None = None,
        settings: Any | None = None,
    ) -> "ToolRegistry":
        """Factory: build a session-scoped ToolRegistry from configuration.

        Args:
            panel_config: Panel definition dict including allowed_tools list.
            mcp_server_configs: List of MCP server config dicts with name/url/auth_token.
            session_documents: List of document dicts to index in the RAG tool.
            settings: Application settings (for API keys, vector store config).
        """
        registry = cls()

        # Determine which tools are allowed for this panel
        allowed_tools: list[str] = panel_config.get("allowed_tools", ["web_search", "document_search"])

        # Register web search if allowed
        if "web_search" in allowed_tools and settings:
            from app.tools.web_search import WebSearchTool
            search_tool = WebSearchTool(
                provider=settings.search_provider,
                api_key=getattr(settings, f"{settings.search_provider}_api_key", ""),
            )
            registry.register(search_tool)

        # Register RAG tool if allowed and documents provided
        if "document_search" in allowed_tools:
            from app.tools.rag_tool import RAGTool
            rag_params: dict[str, Any] = {}
            if settings:
                rag_params["database_url"] = settings.database_url
            rag_tool = RAGTool(
                backend=settings.vector_store if settings else "pgvector",
                connection_params=rag_params,
            )
            registry.register(rag_tool)

        # Register MCP server tools
        if mcp_server_configs:
            from app.tools.mcp_client import MCPServerConfig, fetch_mcp_tools
            for server_cfg in mcp_server_configs:
                server = MCPServerConfig(
                    name=server_cfg["name"],
                    url=server_cfg["url"],
                    auth_token=server_cfg.get("auth_token", ""),
                )
                try:
                    mcp_tools = await fetch_mcp_tools(server)
                    for mcp_tool in mcp_tools:
                        registry.register(mcp_tool)
                except Exception:
                    # Non-fatal: log and continue if one MCP server is unavailable
                    pass

        return registry
