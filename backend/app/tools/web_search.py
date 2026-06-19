"""Web search tool with pluggable provider adapters."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from app.tools.base import BaseTool, ToolOutput
from app.tools.sanitizer import sanitize_search_results


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "Search the web for current information on a topic. "
        "Returns a list of relevant results with titles, snippets, and URLs."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to look up",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (default: 5, max: 10)",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def __init__(self, provider: str = "tavily", api_key: str = "") -> None:
        self._provider = provider
        self._api_key = api_key

    async def execute(self, input: dict[str, Any]) -> ToolOutput:
        query = input.get("query", "")
        num_results = min(int(input.get("num_results", 5)), 10)

        if not query:
            return ToolOutput(
                content="Error: query is required",
                metadata={},
                error="query is required",
            )

        try:
            results = await self._search(query, num_results)
        except Exception as exc:
            return ToolOutput(
                content=f"Search failed: {exc}",
                metadata={},
                error=str(exc),
            )

        # Sanitize before LLM injection
        results = sanitize_search_results(results)

        # Format for LLM consumption
        formatted_lines = [f"Search results for: {query}\n"]
        for i, r in enumerate(results, 1):
            formatted_lines.append(
                f"[{i}] {r.get('title', 'No title')}\n"
                f"URL: {r.get('url', '')}\n"
                f"Domain: {r.get('domain', '')}\n"
                f"{r.get('snippet', '')}\n"
            )

        content = "\n".join(formatted_lines)
        metadata = {
            "results": results,
            "query": query,
            "provider": self._provider,
        }

        return ToolOutput(content=content, metadata=metadata, error=None)

    async def _search(self, query: str, num_results: int) -> list[dict[str, Any]]:
        if self._provider == "tavily":
            return await self._tavily_search(query, num_results)
        if self._provider == "brave":
            return await self._brave_search(query, num_results)
        if self._provider == "serper":
            return await self._serper_search(query, num_results)
        raise ValueError(f"Unknown search provider: {self._provider}")

    async def _tavily_search(self, query: str, num_results: int) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self._api_key,
                    "query": query,
                    "max_results": num_results,
                    "include_answer": False,
                },
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for r in data.get("results", []):
            url = r.get("url", "")
            domain = urlparse(url).netloc
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": url,
                    "domain": domain,
                    "snippet": r.get("content", ""),
                    "published_at": r.get("published_date", ""),
                }
            )
        return results

    async def _brave_search(self, query: str, num_results: int) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": num_results},
                headers={"X-Subscription-Token": self._api_key, "Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for r in data.get("web", {}).get("results", []):
            url = r.get("url", "")
            domain = urlparse(url).netloc
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": url,
                    "domain": domain,
                    "snippet": r.get("description", ""),
                    "published_at": r.get("age", ""),
                }
            )
        return results

    async def _serper_search(self, query: str, num_results: int) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://google.serper.dev/search",
                json={"q": query, "num": num_results},
                headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for r in data.get("organic", []):
            url = r.get("link", "")
            domain = urlparse(url).netloc
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": url,
                    "domain": domain,
                    "snippet": r.get("snippet", ""),
                    "published_at": r.get("date", ""),
                }
            )
        return results
