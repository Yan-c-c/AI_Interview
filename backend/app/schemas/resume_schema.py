from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class ResumeEvaluateRequest(BaseModel):
    message: str = "帮我评估简历"
    file_id: Optional[str] = None
    resume_text: Optional[str] = None
    filename: Optional[str] = None
    api_config: Optional[dict[str, Any]] = None


class ResumeEvaluateResponse(BaseModel):
    success: bool
    agent: str = "resume_evaluation_agent"
    result: dict[str, Any]


class ResumeReportPdfRequest(BaseModel):
    report: dict[str, Any]
    filename: Optional[str] = None


class ResumeReportShareRequest(BaseModel):
    email: str
    report: dict[str, Any]
    filename: Optional[str] = None


class ResumeReportShareResponse(BaseModel):
    success: bool
    message: str
    email: str


class UploadResponse(BaseModel):
    success: bool
    file_id: str
    filename: str
    file_type: str
    parsed_text: str
    parsed_char_count: int
    is_audio: bool = False
    file_sha256: str = ""
