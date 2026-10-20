from __future__ import annotations

from pydantic import BaseModel, Field


class AudioReviewUpdateItem(BaseModel):
    question_id: str
    question: str | None = None
    standard_answer: str | None = None
    knowledge_points: list[str] | None = None


class AudioReviewApproveRequest(BaseModel):
    reviewer: str = "讲师"
    updates: list[AudioReviewUpdateItem] = Field(default_factory=list)


class AudioReviewRejectRequest(BaseModel):
    reviewer: str = "讲师"
    reason: str = ""


class AudioReviewUpdateRequest(BaseModel):
    reviewer: str = "讲师"
    updates: list[AudioReviewUpdateItem]
