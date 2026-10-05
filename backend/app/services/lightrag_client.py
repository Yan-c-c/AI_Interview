from __future__ import annotations

# Compatibility shim. New code should import from app.services.knowledge_base.
from app.services.knowledge_base import LightRAGClient, LightRAGQueryResult, lightrag_client

__all__ = ["LightRAGClient", "LightRAGQueryResult", "lightrag_client"]
