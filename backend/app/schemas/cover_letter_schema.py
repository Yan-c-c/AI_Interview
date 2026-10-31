from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class CoverLetterGenerateRequest(BaseModel):
    message: str = "帮我生成求职信"
    file_id: Optional[str] = None
    resume_text: Optional[str] = None
    filename: Optional[str] = None
    target_company: str = ""
    target_position: str = ""
    jd: str = ""
    recipient: str = "HR"
    purpose: str = "求职申请"
    style: str = "正式专业"
    focus_points: list[str] = Field(default_factory=list)
    word_count: int = 500
    personal_background: str = ""
    api_config: Optional[dict[str, Any]] = None


class CoverLetterRewriteRequest(BaseModel):
    report: dict[str, Any] = Field(default_factory=dict)
    instruction: str
    api_config: Optional[dict[str, Any]] = None


class CoverLetterExportRequest(BaseModel):
    report: dict[str, Any] = Field(default_factory=dict)
    format: str = "pdf"
    version: str = "standard"
    filename: Optional[str] = None


class CoverLetterSendEmailRequest(BaseModel):
    report: dict[str, Any] = Field(default_factory=dict)
    to_email: str = ""
    subject: str = ""
    body: str = ""
    version: str = "standard"
    attach_cover_letter: bool = True
    attach_resume_file: bool = False
    resume_file_id: Optional[str] = None
    save_draft: bool = False


class CoverLetterResponse(BaseModel):
    success: bool
    agent: str = "cover_letter_agent"
    result: dict[str, Any]
    message: Optional[str] = None
