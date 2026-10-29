from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.auth_service import require_admin
from app.services.audio_review_service import audio_review_service

router = APIRouter(prefix="/api/audio-review", tags=["面试录音快速审核"], dependencies=[Depends(require_admin)])


class ReviewUpdateItem(BaseModel):
    question_id: str
    question: str | None = None
    standard_answer: str | None = None
    knowledge_points: list[str] | None = None


class ReviewApproveRequest(BaseModel):
    reviewer: str = "讲师"
    updates: list[ReviewUpdateItem] = Field(default_factory=list)


class ReviewRejectRequest(BaseModel):
    reviewer: str = "讲师"
    reason: str = ""


class ReviewUpdateRequest(BaseModel):
    reviewer: str = "讲师"
    updates: list[ReviewUpdateItem]


@router.post("/{task_id}/approve")
async def approve_audio_review(task_id: str, request: ReviewApproveRequest) -> dict[str, Any]:
    try:
        return await audio_review_service.approve(
            task_id,
            reviewer=request.reviewer,
            updates=[item.model_dump(exclude_none=True) for item in request.updates],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc


@router.post("/{task_id}/reject")
async def reject_audio_review(task_id: str, request: ReviewRejectRequest) -> dict[str, Any]:
    try:
        return audio_review_service.reject(task_id, reviewer=request.reviewer, reason=request.reason)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc


@router.post("/{task_id}/update")
async def update_audio_review(task_id: str, request: ReviewUpdateRequest) -> dict[str, Any]:
    try:
        return audio_review_service.update(
            task_id,
            reviewer=request.reviewer,
            updates=[item.model_dump(exclude_none=True) for item in request.updates],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc


@router.get("/{task_id}/logs")
async def get_audio_review_logs(task_id: str) -> dict[str, Any]:
    return {"success": True, "logs": audio_review_service.logs(task_id)}
