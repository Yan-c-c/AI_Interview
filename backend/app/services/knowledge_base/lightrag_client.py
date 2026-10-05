from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import KnowledgeBaseConfig, knowledge_base_config

logger = logging.getLogger(__name__)


@dataclass
class LightRAGQueryResult:
    available: bool
    status: str
    query: str
    response: str = ""
    references: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    raw: dict[str, Any] | str | None = None

    @property
    def has_content(self) -> bool:
        if self.references:
            return True
        normalized = (self.response or "").strip().lower()
        return bool(normalized and normalized not in {"no relevant context found for the query.", "no relevant context found"})


class LightRAGClient:
    """Internal adapter for a compatible LightRAG HTTP service.

    Business agents should use KnowledgeBaseService. This client is kept as the
    low-level HTTP boundary so the rest of the system does not depend on raw
    LightRAG endpoints.
    """

    def __init__(self, config: KnowledgeBaseConfig | None = None) -> None:
        self.config = config or knowledge_base_config
        self.base_url = self.config.base_url
        self.api_key = self.config.api_key
        self.mode = self.config.query_mode
        self.timeout = self.config.timeout_seconds
        self.top_k = self.config.top_k

    async def health(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._get_json, "/health")

    async def documents(self) -> dict[str, Any] | list[dict[str, Any]]:
        return await asyncio.to_thread(self._get_json, "/documents")

    async def insert_text(self, title: str, text: str) -> dict[str, Any]:
        payload = {"text": text, "file_source": title}
        data = await asyncio.to_thread(self._post_json, "/documents/text", payload)
        return data if isinstance(data, dict) else {"raw": data}

    async def query(self, query: str, *, mode: str | None = None, top_k: int | None = None) -> LightRAGQueryResult:
        text = (query or "").strip()
        if len(text) < 2:
            return LightRAGQueryResult(available=False, status="invalid_query", query=text, error="query too short")
        return await asyncio.to_thread(self._query_sync, text, mode or self.mode, top_k or self.top_k)

    async def graph_labels(self) -> list[str]:
        data = await asyncio.to_thread(self._get_json, "/graph/label/list")
        if isinstance(data, list):
            return [str(item) for item in data]
        if isinstance(data, dict):
            labels = data.get("labels") or data.get("data") or []
            if isinstance(labels, list):
                return [str(item) for item in labels]
        return []

    async def graph(self, label: str, *, max_depth: int = 2, max_nodes: int = 120) -> dict[str, Any]:
        path = f"/graphs?label={self._quote(label)}&max_depth={max_depth}&max_nodes={max_nodes}"
        data = await asyncio.to_thread(self._get_json, path)
        return data if isinstance(data, dict) else {"nodes": [], "edges": []}

    def _query_sync(self, query: str, mode: str, top_k: int) -> LightRAGQueryResult:
        payload = {
            "query": query,
            "mode": mode,
            "top_k": top_k,
            "chunk_top_k": self.config.chunk_top_k,
            "response_type": "Bullet Points",
            "include_references": True,
            "include_chunk_content": True,
            "stream": False,
        }
        try:
            data = self._post_json("/query", payload)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            logger.info("Knowledge base HTTP query unavailable: %s", exc)
            return LightRAGQueryResult(available=False, status="error", query=query, error=str(exc))

        response_text = ""
        references: list[dict[str, Any]] = []
        if isinstance(data, dict):
            response_text = str(data.get("response") or data.get("result") or data.get("answer") or "")
            references = self._normalize_references(data.get("references") or data.get("sources"))
        elif isinstance(data, str):
            response_text = data

        return LightRAGQueryResult(
            available=True,
            status="hit" if response_text or references else "empty",
            query=query,
            response=response_text,
            references=references,
            raw=data,
        )

    def _get_json(self, path: str) -> dict[str, Any] | list[Any] | str:
        request = Request(self._url(path), headers=self._headers(), method="GET")
        with urlopen(request, timeout=self.timeout) as response:
            raw = response.read().decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any] | list[Any] | str:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {**self._headers(), "Content-Type": "application/json"}
        request = Request(self._url(path), data=body, headers=headers, method="POST")
        with urlopen(request, timeout=self.timeout) as response:
            raw = response.read().decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _url(self, path: str) -> str:
        suffix = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}{suffix}"

    def _quote(self, text: str) -> str:
        from urllib.parse import quote

        return quote(text, safe="")

    def _normalize_references(self, references: Any) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        if not isinstance(references, list):
            return normalized
        for index, item in enumerate(references, start=1):
            if not isinstance(item, dict):
                continue
            content = item.get("content") or item.get("snippets") or item.get("text") or []
            if isinstance(content, str):
                snippets = [content]
            elif isinstance(content, list):
                snippets = [str(part) for part in content if str(part).strip()]
            else:
                snippets = []
            normalized.append(
                {
                    "reference_id": str(item.get("reference_id") or item.get("id") or index),
                    "file_path": str(item.get("file_path") or item.get("source") or item.get("title") or "面试知识库"),
                    "content": snippets[:3],
                }
            )
        return normalized


lightrag_client = LightRAGClient()
