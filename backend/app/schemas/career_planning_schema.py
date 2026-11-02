from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class CareerPlanningGenerateRequest(BaseModel):
    message: str = "帮我做职业规划"
    file_id: Optional[str] = None
    resume_text: Optional[str] = None
    filename: Optional[str] = None
    current_identity: str = ""
    target_direction: str = ""
    current_stage: str = ""
    expected_city: str = ""
    expected_industry: str = ""
    expected_salary: str = ""
    available_time: str = ""
    confusion: str = ""
    personal_background: str = ""
    api_config: Optional[dict[str, Any]] = None


class CareerPlanningRewriteRequest(BaseModel):
    report: dict[str, Any] = Field(default_factory=dict)
    instruction: str
    api_config: Optional[dict[str, Any]] = None


class CareerPlanningExportRequest(BaseModel):
    report: dict[str, Any] = Field(default_factory=dict)
    format: str = "pdf"
    filename: Optional[str] = None


class CareerPlanningResponse(BaseModel):
    success: bool
    agent: str = "career_planning_agent"
    result: dict[str, Any]
    message: Optional[str] = None
