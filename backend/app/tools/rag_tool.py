"""RAG (Retrieval-Augmented Generation) tool with pluggable vector store backends."""

from __future__ import annotations

from typing import Any

from app.tools.base import BaseTool, ToolOutput
from app.tools.sanitizer import sanitize_tool_output


class RAGTool(BaseTool):
    name = "document_search"
    description = (
        "Search through uploaded context documents and knowledge base. "
        "Use this to retrieve relevant information from documents provided for this session."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to look up in documents",
            },
            "namespace": {
                "type": "string",
                "description": "Optional namespace to scope the search (e.g., session ID)",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of chunks to retrieve (default: 5)",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def __init__(
        self,
        backend: str = "pgvector",
        connection_params: dict[str, Any] | None = None,
    ) -> None:
        self._backend = backend
        self._connection_params = connection_params or {}

    async def execute(self, input: dict[str, Any]) -> ToolOutput:
        query = input.get("query", "")
        namespace = input.get("namespace")
        top_k = min(int(input.get("top_k", 5)), 20)

        if not query:
            return ToolOutput(
                content="Error: query is required",
                metadata={},
                error="query is required",
            )

        try:
            chunks = await self._retrieve(query, namespace, top_k)
        except Exception as exc:
            return ToolOutput(
                content=f"Document search failed: {exc}",
                metadata={},
                error=str(exc),
            )

        if not chunks:
            return ToolOutput(
                content=f"No documents found matching: {query}",
                metadata={"query": query, "results": []},
                error=None,
            )

        formatted_lines = [f"Document search results for: {query}\n"]
        for i, chunk in enumerate(chunks, 1):
            content = sanitize_tool_output(chunk.get("content", ""))
            formatted_lines.append(
                f"[{i}] Source: {chunk.get('source', 'Unknown')}\n"
                f"Score: {chunk.get('score', 0):.3f}\n"
                f"{content}\n"
            )

        content_str = "\n".join(formatted_lines)
        metadata = {
            "query": query,
            "namespace": namespace,
            "results": [
                {
                    "source": c.get("source", ""),
                    "score": c.get("score", 0),
                    "chunk_id": c.get("chunk_id", ""),
                }
                for c in chunks
            ],
        }

        return ToolOutput(content=content_str, metadata=metadata, error=None)

    async def _retrieve(
        self, query: str, namespace: str | None, top_k: int
    ) -> list[dict[str, Any]]:
        if self._backend == "pgvector":
            return await self._pgvector_retrieve(query, namespace, top_k)
        if self._backend == "qdrant":
            return await self._qdrant_retrieve(query, namespace, top_k)
        if self._backend == "chroma":
            return await self._chroma_retrieve(query, namespace, top_k)
        raise ValueError(f"Unknown vector store backend: {self._backend}")

    async def _pgvector_retrieve(
        self, query: str, namespace: str | None, top_k: int
    ) -> list[dict[str, Any]]:
        # pgvector requires embeddings — this is a minimal implementation
        # Full impl requires an embedding model; for Phase 3 we scaffold the interface
        # and return empty results when no embeddings are configured
        database_url = self._connection_params.get("database_url", "")
        if not database_url:
            return []

        # Placeholder: full implementation would compute embeddings and run vector search
        return []

    async def _qdrant_retrieve(
        self, query: str, namespace: str | None, top_k: int
    ) -> list[dict[str, Any]]:
        qdrant_url = self._connection_params.get("url", "http://localhost:6333")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Placeholder: real impl computes embeddings first
                response = await client.post(
                    f"{qdrant_url}/collections/{namespace or 'default'}/points/search",
                    json={"vector": [0.0] * 1536, "limit": top_k, "with_payload": True},
                )
                response.raise_for_status()
                data = response.json()
                return [
                    {
                        "content": p.get("payload", {}).get("content", ""),
                        "source": p.get("payload", {}).get("source", ""),
                        "score": p.get("score", 0),
                        "chunk_id": str(p.get("id", "")),
                    }
                    for p in data.get("result", [])
                ]
        except Exception:
            return []

    async def _chroma_retrieve(
        self, query: str, namespace: str | None, top_k: int
    ) -> list[dict[str, Any]]:
        # Placeholder for Chroma integration
        return []

    async def index_document(
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Any],
        namespace: str | None = None,
    ) -> bool:
        """Index a document for later retrieval. Returns True on success."""
        # Full implementation would chunk, embed, and store
        # Scaffolded here for Phase 3; will be implemented when embedding model is configured
        return True
