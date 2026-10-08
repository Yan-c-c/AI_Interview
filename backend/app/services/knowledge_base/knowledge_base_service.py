from __future__ import annotations

import asyncio
from typing import Any

from fastapi import UploadFile

from .config import KnowledgeBaseConfig, knowledge_base_config
from .document_index_service import DocumentIndexService, document_index_service
from .graph_search_service import GraphSearchService, graph_search_service
from .lightrag_client import LightRAGClient, LightRAGQueryResult, lightrag_client


class KnowledgeBaseService:
    """Unified interview knowledge base service for agents and API routes."""

    def __init__(
        self,
        *,
        config: KnowledgeBaseConfig | None = None,
        client: LightRAGClient | None = None,
        document_index: DocumentIndexService | None = None,
        graph_search: GraphSearchService | None = None,
    ) -> None:
        self.config = config or knowledge_base_config
        self.client = client or lightrag_client
        self.document_index = document_index or document_index_service
        self.graph_search = graph_search or graph_search_service

    async def status(self) -> dict[str, Any]:
        external = {"available": False, "status": "unavailable", "base_url": self.client.base_url}
        try:
            health = await self.client.health()
            external = {"available": True, "status": "healthy", "base_url": self.client.base_url, "raw": health}
        except Exception as exc:
            external["error"] = str(exc)
        local = self.document_index.status()
        graph = self.graph_search.status()
        return {
            "success": True,
            "module": "interview_knowledge_base",
            "external_retrieval": external,
            "local_index": local,
            "graph": graph,
            "config": {
                "query_mode": self.config.query_mode,
                "top_k": self.config.top_k,
                "chunk_top_k": self.config.chunk_top_k,
                "summary_language": self.config.summary_language,
            },
        }

    async def list_documents(self) -> list[dict[str, Any]]:
        return self.document_index.list_documents()

    async def upload_document(self, upload: UploadFile) -> dict[str, Any]:
        return await self.document_index.upload_document(upload)

    async def insert_text(self, *, title: str | None, text: str) -> dict[str, Any]:
        external: dict[str, Any] | None = None
        try:
            external = await self.client.insert_text(title or "面试题库收录.md", text)
        except Exception:
            external = None
        local = self.document_index.insert_text(title=title, text=text, source_path=title or "手动录入题库内容.md")
        if external:
            local["external_ingest"] = external
        return local

    async def delete_document(self, document_id: str) -> bool:
        return self.document_index.delete_document(document_id)

    async def query(self, query: str, *, mode: str | None = None, top_k: int | None = None) -> dict[str, Any]:
        result = await self.retrieve_for_agent(query, mode=mode, top_k=top_k)
        return {
            "success": True,
            "query": result.query,
            "available": result.available,
            "status": result.status,
            "answer": result.response,
            "references": result.references,
            "source": "external_service" if result.available else "local_embedded_index",
            "error": result.error,
        }

    async def retrieve_for_agent(self, query: str, *, mode: str | None = None, top_k: int | None = None) -> LightRAGQueryResult:
        external = await self.client.query(query, mode=mode, top_k=top_k)
        if external.has_content:
            return external
        local = self._local_result(query, top_k=top_k)
        if local.has_content:
            if external.error:
                local.error = external.error
            return local
        return external if external.available else local

    async def retrieve_many(self, queries: list[str]) -> list[LightRAGQueryResult]:
        if not queries:
            return []
        return await asyncio.gather(*(self.retrieve_for_agent(query) for query in queries))

    async def graph_labels(self, *, query: str | None = None, limit: int = 60) -> list[dict[str, Any]]:
        if query:
            return self.graph_search.search_labels(query, limit=limit)
        return self.graph_search.popular_labels(limit=limit)

    async def graph(self, *, label: str | None = None, max_depth: int = 2, max_nodes: int = 120) -> dict[str, Any]:
        return self.graph_search.get_graph(label, max_depth=max_depth, max_nodes=max_nodes)

    def _local_result(self, query: str, *, top_k: int | None = None) -> LightRAGQueryResult:
        hits = self.document_index.search(query, top_k=top_k or self.config.top_k)
        references = [
            {
                "reference_id": hit.chunk_id,
                "file_path": hit.file_path,
                "content": [hit.snippet],
                "score": hit.score,
            }
            for hit in hits
        ]
        response = ""
        if hits:
            response = "\n".join(f"- {hit.snippet}" for hit in hits[:3])
        return LightRAGQueryResult(
            available=False,
            status="local_hit" if hits else "empty",
            query=query,
            response=response,
            references=references,
            raw={"source": "embedded_local_index", "hit_count": len(hits)},
        )


knowledge_base_service = KnowledgeBaseService()
