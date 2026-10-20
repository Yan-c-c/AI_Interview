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


class TextToSpeechRequest(BaseModel):
    text: str
    per: int = Field(default=4115)
    spd: int = Field(default=5)


class AnalyzeAudioJsonRequest(BaseModel):
    message: str = "请分析这段面试录音"
    file_id: str | None = None
    audio_url: str | None = None
    session_id: str | None = None
    api_config: dict[str, Any] | None = None


@router.post("/analyze")
async def analyze_interview_audio(request: Request) -> dict:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        audio = form.get("audio") or form.get("file")
        message = str(form.get("message") or "请分析这段面试录音")
        audio_url = str(form.get("audio_url") or "") or None
        if not isinstance(audio, UploadFile) and not audio_url:
            raise HTTPException(status_code=400, detail={"message": "请上传音频文件或提供 audio_url。"})
        record = None
        if isinstance(audio, UploadFile):
            try:
                record = await file_parser_service.parse_upload(audio)
            except (UnsupportedFileTypeError, FileParserError) as exc:
                raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
        agent_request = AgentRequest(
            message=message,
            file_id=record.file_id if record else None,
            filename=record.filename if record else "远程面试录音",
            metadata={"audio_url": audio_url, "file_record": record.__dict__ if record else None},
        )
    else:
        payload = await request.json()
        data = AnalyzeAudioJsonRequest(**payload)
        record = file_parser_service.get_record(data.file_id) if data.file_id else None
        if data.file_id and not record:
            raise HTTPException(status_code=404, detail={"message": "未找到上传的音频文件。"})
        agent_request = AgentRequest(
            message=data.message,
            file_id=data.file_id,
            filename=record.filename if record else "远程面试录音",
            session_id=data.session_id,
            api_config=data.api_config,
            metadata={"audio_url": data.audio_url, "file_record": record.__dict__ if record else None},
        )
    response = await InterviewAudioAnalysisAgent().run(agent_request)
    if not response.success:
        return response.result
    return response.result




@router.get("/audio/{file_id}")
async def get_audio_file(file_id: str) -> FileResponse:
    record = file_parser_service.get_record(file_id)
    if not record or not record.is_audio or not record.file_path:
        raise HTTPException(status_code=404, detail={"message": "未找到音频文件。"})
    path = Path(record.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail={"message": "音频文件不存在。"})
    media_type = "audio/mpeg" if record.file_type == "mp3" else f"audio/{record.file_type}"
    return FileResponse(path, media_type=media_type, filename=record.filename)


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


@router.post("/tts")
async def text_to_speech(request: TextToSpeechRequest) -> Response:
    try:
        audio = baidu_speech_service.text_to_speech(request.text, per=request.per, spd=request.spd)
    except BaiduSpeechError as exc:
        raise HTTPException(status_code=503, detail={"error": "BaiduSpeechError", "message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"error": "SpeechServiceUnavailable", "message": "语音合成服务暂时不可用。"}) from exc
    return Response(content=audio, media_type="audio/wav")
