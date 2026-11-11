from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.auth_service import auth_service, require_admin, require_user
from app.services.audio_review_service import audio_review_service
from app.services.knowledge_base import knowledge_base_service

router = APIRouter(prefix="/api/admin", tags=["后台管理"])

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    email: str = Field(..., min_length=3, max_length=160)
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class CreateUserRequest(RegisterRequest):
    role: Literal["user", "admin"] = "user"


class UpdateUserRequest(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    role: Literal["user", "admin"] | None = None
    status: Literal["active", "disabled"] | None = None


@router.post("/auth/register")
async def register(request: RegisterRequest) -> dict[str, Any]:
    try:
        user = auth_service.register_user(name=request.name, email=request.email, password=request.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    token = auth_service.create_token(user)
    return {"success": True, "user": user, "token": token}


@router.post("/auth/login")
async def login(request: LoginRequest) -> dict[str, Any]:
    try:
        user = auth_service.authenticate(email=request.email, password=request.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail={"message": str(exc)}) from exc
    token = auth_service.create_token(user)
    return {"success": True, "user": user, "token": token}


@router.get("/auth/me")
async def me(current_user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    return {"success": True, "user": current_user}


@router.get("/status")
async def admin_status(current_user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return {
        "success": True,
        "status": "ready",
        "message": "后台管理 API 已启用。",
        "current_user": current_user,
    }


@router.get("/users")
async def list_users(_: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    users = auth_service.list_users()
    return {"success": True, "users": users, "total": len(users), "analytics": _user_analytics(users)}


@router.post("/users")
async def create_user(request: CreateUserRequest, _: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    try:
        user = auth_service.create_user(name=request.name, email=request.email, password=request.password, role=request.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return {"success": True, "user": user}


@router.patch("/users/{user_id}")
async def update_user(user_id: str, request: UpdateUserRequest, current_user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    if user_id == current_user.get("id") and request.status == "disabled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message": "不能停用当前登录账号。"})
    try:
        user = auth_service.update_user(user_id, name=request.name, role=request.role, user_status=request.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc
    return {"success": True, "user": user}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    if user_id == current_user.get("id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message": "不能删除当前登录账号。"})
    try:
        auth_service.delete_user(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc
    return {"success": True, "deleted": True, "user_id": user_id}


@router.get("/overview")
async def overview(_: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    users = auth_service.list_users()
    question_bank = await _question_bank_summary()
    audio = _audio_review_summary()
    agent_counts = _agent_counts(audio["total_tasks"])
    activity_total = sum(item["runs"] for item in agent_counts)
    metrics = [
        {"label": "注册用户", "value": len(users), "hint": f"{_user_analytics(users)['active']} 个账号可用", "tone": "blue"},
        {"label": "题库资料", "value": question_bank["documents"], "hint": f"{question_bank['chunks']} 个检索分块", "tone": "green"},
        {"label": "Agent 产物", "value": activity_total, "hint": "来自本地历史文件和审核任务", "tone": "orange"},
        {"label": "待审核录音", "value": audio["pending_review"], "hint": f"{audio['approved']} 个任务已入库", "tone": "red" if audio["pending_review"] else "gray"},
    ]
    return {
        "success": True,
        "metrics": metrics,
        "users": _user_analytics(users),
        "question_bank": question_bank,
        "audio_reviews": audio,
        "agent_counts": agent_counts,
    }


@router.get("/agent-monitoring")
async def agent_monitoring(_: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    audio = _audio_review_summary()
    agents = [
        {
            "key": "resume_evaluation",
            "name": "简历评估 Agent",
            "runs": 0,
            "status": "online",
            "success_rate": None,
            "note": "当前未持久化简历评估历史，仅监控接口可用性。",
        },
        {
            "key": "interview_question",
            "name": "模拟面试 Agent",
            "runs": 0,
            "status": "online",
            "success_rate": None,
            "note": "运行依赖题库检索，题库状态在题库管理面板查看。",
        },
        {
            "key": "interview_audio",
            "name": "面试录音分析 Agent",
            "runs": audio["total_tasks"],
            "status": "attention" if audio["pending_review"] else "online",
            "success_rate": _ratio(audio["completed_tasks"], audio["total_tasks"]),
            "note": f"{audio['pending_review']} 个任务待管理员审核。",
        },
        {
            "key": "cover_letter",
            "name": "求职信 Agent",
            "runs": _count_json_files(DATA_DIR / "cover_letters"),
            "status": "online",
            "success_rate": None,
            "note": "根据历史文件统计生成次数。",
        },
        {
            "key": "career_planning",
            "name": "职业规划 Agent",
            "runs": _count_json_files(DATA_DIR / "career_plans"),
            "status": "online",
            "success_rate": None,
            "note": "根据历史文件统计生成次数。",
        },
        {
            "key": "email_campaign",
            "name": "邮件群发 Agent",
            "runs": _count_json_files(DATA_DIR / "email_campaigns"),
            "status": "online",
            "success_rate": None,
            "note": "发送成功率需进入具体邮件任务查看。",
        },
        {
            "key": "salary_negotiation",
            "name": "薪资谈判 Agent",
            "runs": _count_json_files(DATA_DIR / "salary_negotiations"),
            "status": "online",
            "success_rate": None,
            "note": "根据历史文件统计生成次数。",
        },
    ]
    return {"success": True, "agents": agents, "recent_events": _recent_audio_events()}


@router.get("/audio-reviews")
async def audio_reviews(_: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    tasks = []
    for task in sorted(_load_audio_tasks().values(), key=lambda item: str(item.get("updated_at") or ""), reverse=True):
        result = task.get("result") if isinstance(task.get("result"), dict) else None
        qa_analysis = result.get("qa_analysis") if isinstance(result, dict) and isinstance(result.get("qa_analysis"), list) else []
        summary = result.get("summary") if isinstance(result, dict) and isinstance(result.get("summary"), dict) else {}
        tasks.append(
            {
                "task_id": task.get("task_id"),
                "status": task.get("status"),
                "review_status": task.get("review_status"),
                "audio_filename": task.get("audio_filename") or (result or {}).get("metadata", {}).get("audio_filename"),
                "created_at": task.get("created_at"),
                "updated_at": task.get("updated_at"),
                "error": task.get("error"),
                "qa_count": len(qa_analysis),
                "overall_score": summary.get("overall_score"),
                "has_result": result is not None,
                "result": result,
            }
        )
    return {"success": True, "tasks": tasks, "total": len(tasks), "summary": _audio_review_summary()}


@router.get("/question-bank/summary")
async def question_bank_summary(_: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return {"success": True, "question_bank": await _question_bank_summary()}


def _user_analytics(users: list[dict[str, Any]]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    new_7d = 0
    by_role = {"admin": 0, "user": 0}
    by_status = {"active": 0, "disabled": 0}
    for user in users:
        role = str(user.get("role") or "user")
        user_status = str(user.get("status") or "active")
        by_role[role] = by_role.get(role, 0) + 1
        by_status[user_status] = by_status.get(user_status, 0) + 1
        created_at = _parse_datetime(str(user.get("created_at") or ""))
        if created_at and created_at >= now - timedelta(days=7):
            new_7d += 1
    return {
        "total": len(users),
        "active": by_status.get("active", 0),
        "disabled": by_status.get("disabled", 0),
        "admins": by_role.get("admin", 0),
        "regular_users": by_role.get("user", 0),
        "new_7d": new_7d,
        "by_role": by_role,
        "by_status": by_status,
    }


async def _question_bank_summary() -> dict[str, Any]:
    status_data = await knowledge_base_service.status()
    documents = await knowledge_base_service.list_documents()
    local_index = status_data.get("local_index") or {}
    graph = status_data.get("graph") or {}
    external = status_data.get("external_retrieval") or {}
    return {
        "documents": int(local_index.get("document_count") or len(documents)),
        "chunks": int(local_index.get("chunk_count") or 0),
        "graph_nodes": int(graph.get("node_count") or 0),
        "graph_edges": int(graph.get("edge_count") or 0),
        "external_status": external.get("status") or "unknown",
        "external_available": bool(external.get("available")),
        "recent_documents": documents[:6],
    }


def _audio_review_summary() -> dict[str, Any]:
    tasks = list(_load_audio_tasks().values())
    approved = 0
    rejected = 0
    failed = 0
    pending_review = 0
    completed = 0
    for task in tasks:
        review_status = str(task.get("review_status") or "")
        task_status = str(task.get("status") or "")
        if review_status == "approved":
            approved += 1
        elif review_status == "rejected":
            rejected += 1
        elif task_status == "failed" or review_status == "analysis_failed":
            failed += 1
        elif review_status in {"pending_review", "pending_analysis"} or task_status in {"created", "transcribing", "transcribed"}:
            pending_review += 1
        if task_status in {"completed", "reviewed"}:
            completed += 1
    return {
        "total_tasks": len(tasks),
        "completed_tasks": completed,
        "approved": approved,
        "rejected": rejected,
        "failed": failed,
        "pending_review": pending_review,
        "logs": len(audio_review_service.logs()),
    }


def _agent_counts(audio_task_count: int) -> list[dict[str, Any]]:
    return [
        {"key": "cover_letter", "label": "求职信", "runs": _count_json_files(DATA_DIR / "cover_letters")},
        {"key": "career_planning", "label": "职业规划", "runs": _count_json_files(DATA_DIR / "career_plans")},
        {"key": "email_campaign", "label": "邮件群发", "runs": _count_json_files(DATA_DIR / "email_campaigns")},
        {"key": "salary_negotiation", "label": "薪资谈判", "runs": _count_json_files(DATA_DIR / "salary_negotiations")},
        {"key": "interview_audio", "label": "录音分析", "runs": audio_task_count},
    ]


def _recent_audio_events() -> list[dict[str, Any]]:
    events = []
    for log in audio_review_service.logs()[-12:]:
        events.append(
            {
                "type": "audio_review",
                "title": f"录音审核 {log.get('action')}",
                "description": f"任务 {log.get('task_id')}",
                "created_at": log.get("created_at"),
            }
        )
    for task in list(_load_audio_tasks().values())[-8:]:
        events.append(
            {
                "type": "audio_task",
                "title": f"录音任务 {task.get('status')}",
                "description": str(task.get("audio_filename") or task.get("task_id") or ""),
                "created_at": task.get("updated_at") or task.get("created_at"),
            }
        )
    return sorted(events, key=lambda item: str(item.get("created_at") or ""), reverse=True)[:12]


def _load_audio_tasks() -> dict[str, Any]:
    path = DATA_DIR / "audio_reviews" / "audio_analysis_tasks.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _count_json_files(path: Path) -> int:
    if not path.exists():
        return 0
    return len([item for item in path.glob("*.json") if item.is_file()])


def _ratio(numerator: int, denominator: int) -> int | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator * 100)


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
