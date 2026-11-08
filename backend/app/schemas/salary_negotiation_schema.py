from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class SalaryAnalyzeRequest(BaseModel):
    message: str = "帮我分析这个 offer 是否合理"
    file_id: Optional[str] = None
    resume_text: str = ""
    job_title: str = "AI Engineer"
    experience_level: str = "MI"
    years_experience: int = 3
    country: str = "UNITED STATES"
    city: str = ""
    company_size: str = "M"
    industry: str = "Technology"
    employment_type: str = "FT"
    remote_ratio: int = 50
    education_required: str = "Bachelor"
    skills: list[str] = Field(default_factory=lambda: ["Python", "SQL", "Machine Learning"])
    current_offer: Optional[int] = None
    expected_salary: Optional[int] = None
    api_config: Optional[dict[str, Any]] = None


class SalaryStrategyRequest(BaseModel):
    profile: dict[str, Any] = Field(default_factory=dict)
    prediction: dict[str, Any] = Field(default_factory=dict)
    trend: dict[str, Any] = Field(default_factory=dict)
    simulation: dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    api_config: Optional[dict[str, Any]] = None


class SalarySimulationRequest(BaseModel):
    market_salary: float = 119000
    exp_level: int = 1
    company_size: int = 1
    current_offer: Optional[float] = None
    target_salary: Optional[float] = None


class SalaryExportRequest(BaseModel):
    report: dict[str, Any] = Field(default_factory=dict)
    format: str = "pdf"
    filename: Optional[str] = None


class SalaryNegotiationResponse(BaseModel):
    success: bool
    agent: str = "salary_negotiation_agent"
    result: dict[str, Any]
    message: Optional[str] = None
