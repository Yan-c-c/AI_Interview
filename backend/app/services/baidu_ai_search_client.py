from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


class BaiduAISearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class BaiduAISearchResult:
    answer: str
    sources: list[dict[str, str]]
    raw: dict[str, Any]


class BaiduAISearchClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("BAIDU_AI_SEARCH_API_KEY") or ""
        self.base_url = os.getenv("BAIDU_AI_SEARCH_BASE_URL") or "https://qianfan.baidubce.com/v2/ai_search/chat/completions"
        self.model = os.getenv("BAIDU_AI_SEARCH_MODEL") or "ernie-4.5-turbo-32k"
        self.max_results = int(os.getenv("BAIDU_AI_SEARCH_MAX_RESULTS") or "5")
        self.search_source = os.getenv("BAIDU_AI_SEARCH_SOURCE") or "baidu_search_v1"
        self.timeout = int(os.getenv("BAIDU_AI_SEARCH_TIMEOUT_SECONDS") or "30")

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.base_url)

    def search(self, query: str) -> BaiduAISearchResult:
        if not self.configured:
            raise BaiduAISearchError("未配置百度 AI 搜索 API Key 或 URL")
        payload = {
            "messages": [{"role": "user", "content": query}],
            "search_source": self.search_source,
            "search_recency_filter": "year",
            "stream": False,
            "model": self.model,
            "enable_deep_search": False,
        }
        request = urllib.request.Request(
            self.base_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Appbuilder-Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            body = response.read().decode("utf-8")
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise BaiduAISearchError(f"百度 AI 搜索返回非 JSON：{body[:160]}") from exc
        answer = self._extract_answer(data)
        sources = self._extract_sources(data)[: self.max_results]
        return BaiduAISearchResult(answer=answer, sources=sources, raw=data)

    def _extract_answer(self, data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message") if isinstance(choices[0], dict) else None
            if isinstance(message, dict):
                return str(message.get("content") or "").strip()
        return str(data.get("result") or data.get("answer") or data.get("content") or "").strip()

    def _extract_sources(self, data: dict[str, Any]) -> list[dict[str, str]]:
        candidates: list[Any] = []
        for key in ("references", "search_results", "sources", "web_search_results"):
            value = data.get(key)
            if isinstance(value, list):
                candidates.extend(value)
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message") if isinstance(choices[0], dict) else None
            if isinstance(message, dict):
                for key in ("references", "search_results", "sources"):
                    value = message.get(key)
                    if isinstance(value, list):
                        candidates.extend(value)

        sources: list[dict[str, str]] = []
        for index, item in enumerate(candidates, start=1):
            if not isinstance(item, dict):
                continue
            sources.append(
                {
                    "source_type": "baidu_ai_search",
                    "title": str(item.get("title") or item.get("name") or f"公开搜索来源 {index}"),
                    "url": str(item.get("url") or item.get("link") or ""),
                    "summary": str(item.get("summary") or item.get("snippet") or item.get("content") or "")[:600],
                }
            )
        return sources


baidu_ai_search_client = BaiduAISearchClient()
