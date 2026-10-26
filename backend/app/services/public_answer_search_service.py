from __future__ import annotations

import asyncio
from typing import Any

from app.services.baidu_ai_search_client import BaiduAISearchError, baidu_ai_search_client
from app.services.knowledge_base import knowledge_base_service


class PublicAnswerSearchService:
    async def search(self, question: str) -> dict[str, Any]:
        lightrag_result = await knowledge_base_service.retrieve_for_agent(question, top_k=10)
        used_lightrag = lightrag_result.has_content
        baidu_result = None
        baidu_error = None
        if not used_lightrag:
            try:
                baidu_result = await asyncio.to_thread(baidu_ai_search_client.search, question)
            except (BaiduAISearchError, OSError, TimeoutError) as exc:
                baidu_error = str(exc)

        evidence_sources: list[dict[str, str]] = []
        if used_lightrag:
            for ref in lightrag_result.references[:5]:
                evidence_sources.append(
                    {
                        "source_type": "lightrag",
                        "title": str(ref.get("file_path") or "面试知识库"),
                        "url": "",
                        "summary": "\n".join(str(part) for part in ref.get("content") or [])[:600],
                    }
                )
        if baidu_result:
            evidence_sources.extend(baidu_result.sources)

        return {
            "lightrag": lightrag_result,
            "baidu_ai_search": baidu_result,
            "baidu_ai_search_error": baidu_error,
            "evidence_sources": evidence_sources,
            "source_status": "lightrag_hit" if used_lightrag else ("baidu_ai_search_hit" if baidu_result and (baidu_result.answer or baidu_result.sources) else "needs_deepseek_fallback"),
        }


public_answer_search_service = PublicAnswerSearchService()
