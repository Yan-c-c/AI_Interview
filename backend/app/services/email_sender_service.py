from __future__ import annotations

import os
import re
import smtplib
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not EMAIL_RE.match(normalized):
        raise ValueError("invalid_email")
    return normalized


class ResumeReportEmailSender:
    """Send resume report PDFs through the SMTP settings kept on the backend."""

    def send_report_pdf(self, *, email: str, pdf_bytes: bytes, filename: str) -> str:
        recipient = normalize_email(email)
        host = os.environ.get("WUZIQI_SMTP_HOST", "").strip()
        sender = (
            os.environ.get("WUZIQI_SMTP_FROM", "").strip()
            or os.environ.get("WUZIQI_SMTP_USER", "").strip()
        )
        if not host or not sender:
            raise RuntimeError("smtp_not_configured")

        try:
            port = int(os.environ.get("WUZIQI_SMTP_PORT", "587"))
        except ValueError as exc:
            raise RuntimeError("smtp_invalid_port") from exc

        username = os.environ.get("WUZIQI_SMTP_USER", "").strip()
        password = os.environ.get("WUZIQI_SMTP_PASSWORD", "")
        use_tls = os.environ.get("WUZIQI_SMTP_TLS", "1").lower() not in {"0", "false", "no"}
        use_ssl = os.environ.get("WUZIQI_SMTP_SSL", "0").lower() in {"1", "true", "yes"}

        message = EmailMessage()
        message["Subject"] = "智能面试助手 - 简历评估报告"
        message["From"] = sender
        message["To"] = recipient
        message.set_content(
            "你好，附件是智能面试助手生成的简历评估报告 PDF。\n\n"
            "报告由 DeepSeek 多专家圆桌会议与 Reflector 整合生成，仅供求职优化参考。"
        )
        message.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=filename,
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


resume_report_email_sender = ResumeReportEmailSender()
