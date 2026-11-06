from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from typing import Iterable

from app.services.email_sender_service import normalize_email
from app.services.email_service import EmailAttachment


@dataclass
class SMTPConfig:
    host: str
    port: int
    username: str
    password: str
    from_name: str = ""
    from_email: str = ""
    use_ssl: bool = True
    use_tls: bool = False

    @property
    def sender(self) -> str:
        return self.from_email.strip() or self.username.strip()

    def masked(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "username": self._mask(self.username),
            "from_name": self.from_name,
            "from_email": self.sender,
            "use_ssl": self.use_ssl,
            "use_tls": self.use_tls,
        }

    def _mask(self, value: str) -> str:
        if not value:
            return ""
        if "@" in value:
            name, domain = value.split("@", 1)
            return f"{name[:2]}***@{domain}"
        return f"{value[:2]}***"


class SMTPService:
    def from_dict(self, data: dict) -> SMTPConfig:
        try:
            port = int(data.get("port") or 465)
        except (TypeError, ValueError):
            raise RuntimeError("smtp_invalid_port")
        config = SMTPConfig(
            host=str(data.get("host") or "").strip(),
            port=port,
            username=str(data.get("username") or "").strip(),
            password=str(data.get("password") or ""),
            from_name=str(data.get("from_name") or "").strip(),
            from_email=str(data.get("from_email") or "").strip(),
            use_ssl=bool(data.get("use_ssl", True)),
            use_tls=bool(data.get("use_tls", False)),
        )
        if not config.host or not config.sender:
            raise RuntimeError("smtp_not_configured")
        normalize_email(config.sender)
        return config

    def test_connection(self, config: SMTPConfig) -> dict:
        try:
            with self._connect(config) as smtp:
                if config.username and config.password:
                    smtp.login(config.username, config.password)
        except RuntimeError:
            raise
        except smtplib.SMTPAuthenticationError as exc:
            raise RuntimeError("smtp_auth_failed") from exc
        except (OSError, smtplib.SMTPException) as exc:
            raise RuntimeError("smtp_connection_failed") from exc
        return {"success": True, "smtp_status": "success", "message": "SMTP 配置可用。", "config": config.masked()}

    def send(
        self,
        *,
        config: SMTPConfig,
        to_email: str,
        subject: str,
        body: str,
        attachments: Iterable[EmailAttachment] = (),
    ) -> str:
        recipient = normalize_email(to_email)
        message = EmailMessage()
        message["Subject"] = subject or "求职邮件"
        sender = formataddr((config.from_name, config.sender)) if config.from_name else config.sender
        message["From"] = sender
        message["To"] = recipient
        message.set_content(body or "")
        for attachment in attachments:
            message.add_attachment(
                attachment.content,
                maintype=attachment.maintype,
                subtype=attachment.subtype,
                filename=attachment.filename,
            )
        try:
            with self._connect(config) as smtp:
                if config.username and config.password:
                    smtp.login(config.username, config.password)
                smtp.send_message(message)
        except RuntimeError:
            raise
        except smtplib.SMTPAuthenticationError as exc:
            raise RuntimeError("smtp_auth_failed") from exc
        except (OSError, smtplib.SMTPException) as exc:
            raise RuntimeError("email_send_failed") from exc
        return recipient

    def _connect(self, config: SMTPConfig):
        if config.use_ssl:
            return smtplib.SMTP_SSL(config.host, config.port, timeout=12)
        smtp = smtplib.SMTP(config.host, config.port, timeout=12)
        if config.use_tls:
            smtp.starttls()
        return smtp


smtp_service = SMTPService()
