from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class InterviewAudioAnalyzeRequest(BaseModel):
    message: str = "请分析这段面试录音"
    file_id: str | None = None
    audio_url: str | None = None
    session_id: str | None = None
    api_config: dict[str, Any] | None = None


class TranscriptSegment(BaseModel):
    segment_id: str
    speaker: str
    role: str | None = None
    text: str
    start_time: str = "00:00"
    end_time: str = "00:00"


class AudioQAPair(BaseModel):
    question_id: str
    question: str
    answer: str
    interviewer_segments: list[dict[str, Any]] = Field(default_factory=list)
    candidate_segments: list[dict[str, Any]] = Field(default_factory=list)
    start_time: str = "00:00"
    end_time: str = "00:00"


class InterviewAudioAnalysisResponse(BaseModel):
    success: bool
    task_id: str
    agent: str = "interview_audio_analysis_agent"
    task_type: str = "interview_audio_analysis"
    summary: dict[str, Any] = Field(default_factory=dict)
    transcript: dict[str, Any] = Field(default_factory=dict)
    qa_analysis: list[dict[str, Any]] = Field(default_factory=list)
    review_status: str = "pending_review"
    metadata: dict[str, Any] = Field(default_factory=dict)
