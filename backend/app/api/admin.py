from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.auth_service import auth_service, require_admin, require_user

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




































