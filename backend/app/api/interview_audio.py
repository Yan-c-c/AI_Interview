from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from app.agents.interview_audio_agent import InterviewAudioAnalysisAgent
from app.schemas.agent_schema import AgentRequest
from app.services.audio_review_service import audio_review_service
from app.services.baidu_asr_client import BaiduASRError
from app.services.baidu_speech_service import BaiduSpeechError, baidu_speech_service
from app.services.file_parser_service import FileParserError, ParsedFileRecord, UnsupportedFileTypeError, file_parser_service

router = APIRouter(prefix="/api/interview-audio", tags=["面试录音分析"])












@router.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    format: str = Form(default="pcm"),
    rate: int = Form(default=16000),
) -> dict:
    audio_data = await audio.read()
    if not audio_data:
        raise HTTPException(status_code=400, detail={"error": "EmptyAudio", "message": "录音内容为空。"})
    try:
        text = baidu_speech_service.speech_to_text(audio_data, audio_format=format, rate=rate)
    except BaiduSpeechError as exc:
        raise HTTPException(status_code=503, detail={"error": "BaiduSpeechError", "message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"error": "SpeechServiceUnavailable", "message": "语音识别服务暂时不可用。"}) from exc
    return {"success": True, "status": "success", "text": text}


