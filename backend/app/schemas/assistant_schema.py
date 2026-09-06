from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class AssistantChatRequest(BaseModel):
    message: str = ""
    file_id: Optional[str] = None
    session_id: Optional[str] = None
    api_config: Optional[dict[str, Any]] = None  # Backward compatible; frontend no longer sends API keys.


class AssistantChatResponse(BaseModel):
    success: bool
    intent: str
    agent: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    message: Optional[str] = None
