from __future__ import annotations

import json
import os
import smtplib
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

from app.services.email_sender_service import normalize_email

load_dotenv()
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


@dataclass
class EmailAttachment:
    filename: str
    content: bytes
    maintype: str
    subtype: str


class EmailService:
    def __init__(self) -> None:
        self.draft_dir = Path(__file__).resolve().parents[2] / "data" / "email_drafts"
        self.draft_dir.mkdir(parents=True, exist_ok=True)

    def is_configured(self) -> bool:
        return bool(self._env("SMTP_HOST", "WUZIQI_SMTP_HOST") and self._sender())

    def send(
        self,
        *,
        to_email: str,
        subject: str,
        body: str,
        attachments: Iterable[EmailAttachment] = (),
    ) -> str:
        recipient = normalize_email(to_email)
        host = self._env("SMTP_HOST", "WUZIQI_SMTP_HOST")
        sender = self._sender()
        if not host or not sender:
            raise RuntimeError("smtp_not_configured")

        try:
            port = int(self._env("SMTP_PORT", "WUZIQI_SMTP_PORT") or "587")
        except ValueError as exc:
            raise RuntimeError("smtp_invalid_port") from exc

        username = self._env("SMTP_USER", "WUZIQI_SMTP_USER")
        password = self._env("SMTP_PASSWORD", "WUZIQI_SMTP_PASSWORD")
        use_ssl = self._bool_env("SMTP_USE_SSL", "WUZIQI_SMTP_SSL", default=False)
        use_tls = self._bool_env("SMTP_USE_TLS", "WUZIQI_SMTP_TLS", default=not use_ssl)

        message = EmailMessage()
        message["Subject"] = subject or "智能面试助手邮件"
        message["From"] = sender
        message["To"] = recipient
        message.set_content(body or "你好，附件是智能面试助手生成的内容。")
        for attachment in attachments:
            message.add_attachment(
                attachment.content,
                maintype=attachment.maintype,
                subtype=attachment.subtype,
                filename=attachment.filename,
            )

        smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        try:
            with smtp_class(host, port, timeout=12) as smtp:
                if use_tls and not use_ssl:
                    smtp.starttls()
                if username and password:
                    smtp.login(username, password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise RuntimeError("email_send_failed") from exc
        return recipient

    def save_draft(self, *, to_email: str, subject: str, body: str, metadata: dict | None = None) -> dict:
        draft_id = str(uuid.uuid4())
        now = datetime.now().isoformat(timespec="seconds")
        payload = {
            "draft_id": draft_id,
            "to_email": to_email.strip(),
            "subject": subject.strip(),
            "body": body,
            "metadata": metadata or {},
            "created_at": now,
        }
        (self.draft_dir / f"{draft_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    def _sender(self) -> str:
        return self._env("SMTP_FROM_EMAIL", "SMTP_FROM", "WUZIQI_SMTP_FROM", "WUZIQI_SMTP_USER")

    def _env(self, *names: str) -> str:
        for name in names:
            value = os.environ.get(name, "").strip()
            if value:
                return value
        return ""

    def _bool_env(self, *names: str, default: bool) -> bool:
        value = self._env(*names)
        if not value:
            return default
        return value.lower() not in {"0", "false", "no", "off"}


email_service = EmailService()
