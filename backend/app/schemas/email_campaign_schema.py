from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class SMTPConfigSchema(BaseModel):
    host: str = ""
    port: int = 465
    username: str = ""
    password: str = ""
    from_name: str = ""
    from_email: str = ""
    use_ssl: bool = True
    use_tls: bool = False
    save_config: bool = False


class EmailRecipientSchema(BaseModel):
    id: Optional[str] = None
    name: str = ""
    email: str
    company: str = ""
    position: str = ""
    note: str = ""


class EmailAttachmentSchema(BaseModel):
    file_id: str
    filename: str = ""
    selected: bool = True


class EmailCampaignContentRequest(BaseModel):
    message: str = ""
    file_id: Optional[str] = None
    resume_text: str = ""
    cover_letter: str = ""
    target_company: str = ""
    target_position: str = ""
    purpose: str = "投递简历"
    style: str = "自然"
    subject: str = ""
    content: str = ""
    api_config: Optional[dict[str, Any]] = None


class EmailCampaignTestSMTPRequest(BaseModel):
    smtp_config: SMTPConfigSchema


class EmailCampaignCreateRequest(BaseModel):
    smtp_config: SMTPConfigSchema
    recipients: list[EmailRecipientSchema] = Field(default_factory=list)
    subject: str = ""
    content: str = ""
    attachments: list[EmailAttachmentSchema] = Field(default_factory=list)
    personalize: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmailCampaignSendRequest(BaseModel):
    task_id: str
    smtp_config: SMTPConfigSchema
    confirm: bool = False


class EmailCampaignResponse(BaseModel):
    success: bool
    agent: str = "email_campaign_agent"
    result: dict[str, Any]
    message: Optional[str] = None
