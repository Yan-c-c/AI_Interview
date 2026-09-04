from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


load_dotenv(Path(__file__).resolve().parents[2] / ".env")

ROLE_ADMIN = "admin"
ROLE_USER = "user"
ACTIVE_STATUS = "active"
DISABLED_STATUS = "disabled"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_security = HTTPBearer(auto_error=False)
AUTH_TOKEN_COOKIE = "ai_interview_auth_token"


class AuthService:
    def __init__(self) -> None:
        self.base_dir = Path(__file__).resolve().parents[2] / "data" / "admin"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.users_path = self.base_dir / "users.json"
        self.secret = os.getenv("ADMIN_AUTH_SECRET") or secrets.token_urlsafe(48)
        self.default_admin_email = os.getenv("ADMIN_DEFAULT_EMAIL") or "admin@example.com"
        self.default_admin_password = os.getenv("ADMIN_DEFAULT_PASSWORD")

    def register_user(self, *, name: str, email: str, password: str) -> dict[str, Any]:
        return self.create_user(name=name, email=email, password=password, role=ROLE_USER)

    def create_user(self, *, name: str, email: str, password: str, role: str = ROLE_USER) -> dict[str, Any]:
        name = name.strip()
        email = self._normalize_email(email)
        role = self._normalize_role(role)
        self._validate_password(password)
        if not name:
            raise ValueError("请输入用户姓名。")

        store = self._load_store()
        if self._find_user_by_email(email, store=store):
            raise ValueError("该邮箱已注册。")

        now = self._now()
        user = {
            "id": str(uuid.uuid4()),
            "name": name,
            "email": email,
            "role": role,
            "status": ACTIVE_STATUS,
            "password_hash": self._hash_password(password),
            "created_at": now,
            "updated_at": now,
            "last_login_at": None,
        }
        store["users"].append(user)
        self._save_store(store)
        return self.public_user(user)

    def authenticate(self, *, email: str, password: str) -> dict[str, Any]:
        user = self._find_user_by_email(self._normalize_email(email))
        if not user or not self._verify_password(password, str(user.get("password_hash") or "")):
            raise ValueError("邮箱或密码不正确。")
        if user.get("status") != ACTIVE_STATUS:
            raise ValueError("该账号已被停用，请联系管理员。")

        store = self._load_store()
        for item in store["users"]:
            if item.get("id") == user.get("id"):
                item["last_login_at"] = self._now()
                item["updated_at"] = item["last_login_at"]
                user = item
                break
        self._save_store(store)
        return self.public_user(user)

    def create_token(self, user: dict[str, Any], *, expires_in_hours: int = 24 * 7) -> str:
        payload = {
            "sub": user["id"],
            "email": user["email"],
            "role": user["role"],
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)).timestamp()),
        }
        body = self._b64encode(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        signature = self._sign(body)
        return f"{body}.{signature}"

    def verify_token(self, token: str) -> dict[str, Any]:
        try:
            body, signature = token.split(".", 1)
        except ValueError as exc:
            raise ValueError("登录状态无效，请重新登录。") from exc
        expected = self._sign(body)
        if not hmac.compare_digest(signature, expected):
            raise ValueError("登录状态无效，请重新登录。")
        try:
            payload = json.loads(self._b64decode(body).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("登录状态无效，请重新登录。") from exc
        if int(payload.get("exp") or 0) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("登录已过期，请重新登录。")
        user = self.get_user(str(payload.get("sub") or ""))
        if not user or user.get("status") != ACTIVE_STATUS:
            raise ValueError("账号不可用，请重新登录。")
        return self.public_user(user)

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        store = self._load_store()
        for user in store["users"]:
            if user.get("id") == user_id:
                return user
        return None

    def list_users(self) -> list[dict[str, Any]]:
        store = self._load_store()
        return [self.public_user(user) for user in sorted(store["users"], key=lambda item: str(item.get("created_at") or ""), reverse=True)]

    def update_user(self, user_id: str, *, name: str | None = None, role: str | None = None, user_status: str | None = None) -> dict[str, Any]:
        store = self._load_store()
        for user in store["users"]:
            if user.get("id") != user_id:
                continue
            if name is not None and name.strip():
                user["name"] = name.strip()
            if role is not None:
                user["role"] = self._normalize_role(role)
            if user_status is not None:
                user["status"] = self._normalize_status(user_status)
            user["updated_at"] = self._now()
            self._save_store(store)
            return self.public_user(user)
        raise ValueError("未找到该用户。")

    def delete_user(self, user_id: str) -> None:
        store = self._load_store()
        next_users = [user for user in store["users"] if user.get("id") != user_id]
        if len(next_users) == len(store["users"]):
            raise ValueError("未找到该用户。")
        store["users"] = next_users
        self._save_store(store)

    def public_user(self, user: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in user.items() if key != "password_hash"}

    def _find_user_by_email(self, email: str, *, store: dict[str, Any] | None = None) -> dict[str, Any] | None:
        store = store or self._load_store()
        for user in store["users"]:
            if str(user.get("email") or "").lower() == email.lower():
                return user
        return None

    def _load_store(self) -> dict[str, Any]:
        if not self.users_path.exists():
            store = {"users": []}
            self._seed_default_admin(store)
            self._save_store(store)
            return store
        try:
            data = json.loads(self.users_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {"users": []}
        if not isinstance(data, dict) or not isinstance(data.get("users"), list):
            data = {"users": []}
        if not data["users"]:
            self._seed_default_admin(data)
            self._save_store(data)
        return data

    def _save_store(self, store: dict[str, Any]) -> None:
        self.users_path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")

    def _seed_default_admin(self, store: dict[str, Any]) -> None:
        if not self.default_admin_password:
            return
        now = self._now()
        store["users"].append(
            {
                "id": str(uuid.uuid4()),
                "name": "系统管理员",
                "email": self.default_admin_email.lower(),
                "role": ROLE_ADMIN,
                "status": ACTIVE_STATUS,
                "password_hash": self._hash_password(self.default_admin_password),
                "created_at": now,
                "updated_at": now,
                "last_login_at": None,
            }
        )

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
        return f"pbkdf2_sha256${salt}${digest}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        try:
            algorithm, salt, digest = password_hash.split("$", 2)
        except ValueError:
            return False
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
        return hmac.compare_digest(candidate, digest)

    def _sign(self, body: str) -> str:
        digest = hmac.new(self.secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
        return self._b64encode(digest)

    def _b64encode(self, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

    def _b64decode(self, value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)

    def _normalize_email(self, email: str) -> str:
        normalized = email.strip().lower()
        if not _EMAIL_RE.match(normalized):
            raise ValueError("请输入有效的邮箱地址。")
        return normalized

    def _validate_password(self, password: str) -> None:
        if len(password) < 6:
            raise ValueError("密码至少需要 6 位。")

    def _normalize_role(self, role: str) -> str:
        if role not in {ROLE_ADMIN, ROLE_USER}:
            raise ValueError("用户角色不正确。")
        return role

    def _normalize_status(self, user_status: str) -> str:
        if user_status not in {ACTIVE_STATUS, DISABLED_STATUS}:
            raise ValueError("用户状态不正确。")
        return user_status

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")


auth_service = AuthService()


def require_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> dict[str, Any]:
    token = credentials.credentials if credentials else request.cookies.get(AUTH_TOKEN_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"message": "请先登录。"})
    try:
        return auth_service.verify_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"message": str(exc)}) from exc


def require_admin(current_user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if current_user.get("role") != ROLE_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"message": "需要管理员权限。"})
    return current_user
