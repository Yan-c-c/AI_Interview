from __future__ import annotations

import json
import mimetypes
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.schemas.email_campaign_schema import EmailCampaignCreateRequest, EmailCampaignSendRequest
from app.services.email_sender_service import normalize_email
from app.services.email_service import EmailAttachment
from app.services.file_parser_service import file_parser_service
from app.services.smtp_service import SMTPConfig, smtp_service

VARIABLE_RE = re.compile(r"\{\{\s*(name|company|position)\s*\}\}", flags=re.I)
MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024


class EmailCampaignService:
    def __init__(self) -> None:
        self.data_dir = Path(__file__).resolve().parents[2] / "data" / "email_campaigns"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def preview_workspace(self, *, filename: str = "", parsed_char_count: int = 0) -> dict[str, Any]:
        return {
            "agent": "email_campaign_agent",
            "task_type": "email_campaign",
            "success": True,
            "smtp_status": "unconfigured",
            "subject": "",
            "content": "",
            "recipients_count": 0,
            "attachments": [],
            "send_summary": {"total": 0, "success": 0, "failed": 0, "pending": 0},
            "send_results": [],
            "status": "draft",
            "message": "邮件群发工作台已准备好。请先配置 SMTP、添加收件人，再生成或填写邮件内容。",
            "metadata": {
                "filename": filename,
                "parsed_char_count": parsed_char_count,
                "supports_user_smtp": True,
                "stores_smtp_password": False,
            },
        }


    def create_task(self, request: EmailCampaignCreateRequest) -> dict[str, Any]:
        config = smtp_service.from_dict(request.smtp_config.model_dump())
        recipients, warnings = self._normalize_recipients([item.model_dump() for item in request.recipients])
        if not recipients:
            raise ValueError("empty_recipients")
        subject = request.subject.strip()
        content = request.content.strip()
        if not subject or not content:
            raise ValueError("empty_email_content")
        attachments = self._normalize_attachments([item.model_dump() for item in request.attachments])

        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat(timespec="seconds")
        send_results = [
            {
                "recipient_id": item["id"],
                "name": item["name"],
                "email": item["email"],
                "company": item["company"],
                "position": item["position"],
                "status": "pending",
                "error": "",
                "sent_at": "",
                "subject": self._render(subject, item) if request.personalize else subject,
                "content_preview": self._render(content, item)[:600] if request.personalize else content[:600],
            }
            for item in recipients
        ]
        task = {
            "task_id": task_id,
            "agent": "email_campaign_agent",
            "task_type": "email_campaign",
            "success": True,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
            "smtp_status": "configured",
            "smtp_config": config.masked(),
            "subject": subject,
            "content": content,
            "personalize": request.personalize,
            "recipients": recipients,
            "recipients_count": len(recipients),
            "attachments": attachments,
            "send_summary": self._summary(send_results),
            "send_results": send_results,
            "validation_warnings": warnings,
            "metadata": request.metadata,
        }
        self._save_task(task)
        return task


    def get_task(self, task_id: str) -> dict[str, Any] | None:
        path = self.data_dir / f"{task_id}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def history(self, limit: int = 30) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        paths = sorted(self.data_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        for path in paths[:limit]:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            items.append(
                {
                    "task_id": data.get("task_id"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "status": data.get("status"),
                    "sender": data.get("smtp_config", {}).get("from_email") or data.get("smtp_config", {}).get("username"),
                    "recipients_count": data.get("recipients_count", 0),
                    "subject": data.get("subject", ""),
                    "attachments": data.get("attachments", []),
                    "send_summary": data.get("send_summary", {}),
                }
            )
        return items

    def _normalize_recipients(self, recipients: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
        normalized: list[dict[str, Any]] = []
        warnings: list[str] = []
        seen: set[str] = set()
        for index, item in enumerate(recipients, start=1):
            try:
                email = normalize_email(str(item.get("email") or ""))
            except ValueError:
                warnings.append(f"第 {index} 个收件人邮箱格式无效，已跳过。")
                continue
            if email in seen:
                warnings.append(f"{email} 重复，已保留第一条。")
                continue
            seen.add(email)
            normalized.append(
                {
                    "id": str(item.get("id") or uuid.uuid4()),
                    "name": str(item.get("name") or "").strip(),
                    "email": email,
                    "company": str(item.get("company") or "").strip(),
                    "position": str(item.get("position") or "").strip(),
                    "note": str(item.get("note") or "").strip(),
                }
            )
        return normalized, warnings




    def _summary(self, results: list[dict[str, Any]]) -> dict[str, int]:
        counts = {"total": len(results), "success": 0, "failed": 0, "pending": 0, "sending": 0, "skipped": 0}
        for item in results:
            status = item.get("status") or "pending"
            counts[status] = counts.get(status, 0) + 1
        return counts


    def _touch(self, task: dict[str, Any]) -> None:
        task["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._save_task(task)

    def _save_task(self, task: dict[str, Any]) -> None:
        path = self.data_dir / f"{task['task_id']}.json"
        path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")


email_campaign_service = EmailCampaignService()
