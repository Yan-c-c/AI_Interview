from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from app.services.aliyun_oss_service import AliyunOSSError, aliyun_oss_service
from app.services.baidu_asr_client import BaiduASRError, baidu_asr_client
from app.services.file_parser_service import ParsedFileRecord


class AudioTranscriptionService:
    def __init__(self) -> None:
        self.public_base_url = (os.getenv("BAIDU_ASR_PUBLIC_AUDIO_BASE_URL") or os.getenv("PUBLIC_BACKEND_BASE_URL") or "").rstrip("/")

    def build_audio_url(self, record: ParsedFileRecord, explicit_url: str | None = None) -> str:
        if explicit_url:
            return explicit_url
        if self.public_base_url and record.file_id:
            return f"{self.public_base_url}/api/interview-audio/audio/{record.file_id}"
        return ""

    async def transcribe(self, *, record: ParsedFileRecord | None = None, audio_url: str | None = None) -> dict[str, Any]:
        oss_upload: dict[str, Any] | None = None
        speech_url = audio_url or (self.build_audio_url(record) if record else "")
        if not speech_url and record:
            path = self.audio_file_path(record)
            if path and aliyun_oss_service.configured:
                upload_result = await asyncio.to_thread(aliyun_oss_service.upload_file, path, filename=record.filename)
                speech_url = upload_result.signed_url
                oss_upload = {
                    "bucket": upload_result.bucket,
                    "object_key": upload_result.object_key,
                    "public_url": upload_result.public_url,
                    "signed_url_expires_seconds": upload_result.expires_seconds,
                    "raw": upload_result.raw,
                }
        if not speech_url:
            raise BaiduASRError(
                "缺少可公网访问的音频 URL。请配置阿里云 OSS，或配置 BAIDU_ASR_PUBLIC_AUDIO_BASE_URL，"
                "或在请求中传入 audio_url；百度音频文件转写接口需要 speech_url。"
            )
        audio_format = (record.file_type if record else None) or os.getenv("BAIDU_ASR_FORMAT") or "mp3"
        task = await asyncio.to_thread(baidu_asr_client.create_task, speech_url, audio_format=audio_format)
        task_id = str(task.get("task_id") or "")
        result = await asyncio.to_thread(baidu_asr_client.wait_for_result, task_id)
        normalized = baidu_asr_client.normalize_result(result)
        return {
            "baidu_task_id": task_id,
            "speech_url": speech_url,
            "raw_task": task,
            "raw_result": result,
            "oss_upload": oss_upload,
            **normalized,
        }

    def audio_file_path(self, record: ParsedFileRecord) -> Path | None:
        if not record.file_path:
            return None
        path = Path(record.file_path)
        return path if path.exists() else None


audio_transcription_service = AudioTranscriptionService()
