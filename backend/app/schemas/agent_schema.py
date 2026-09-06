from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Intent(str, Enum):
    resume_evaluation = "resume_evaluation"
    interview_audio_analysis = "interview_audio_analysis"
    interview_question_generation = "interview_question_generation"
    cover_letter_generation = "cover_letter_generation"
    email_campaign = "email_campaign"
    salary_negotiation = "salary_negotiation"
    career_planning = "career_planning"
    unknown = "unknown"


class AgentRequest(BaseModel):
    message: str = ""
    file_id: Optional[str] = None
    filename: Optional[str] = None
    resume_text: Optional[str] = None
    session_id: Optional[str] = None
    api_config: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    success: bool
    agent: str
    task_type: str
    result: dict[str, Any] = Field(default_factory=dict)
    status: Optional[str] = None
    message: Optional[str] = None
