from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.resume_schema import UploadResponse
from app.services.file_parser_service import FileParserError, UnsupportedFileTypeError, file_parser_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["文件上传"])


@router.post("/upload", response_model=UploadResponse)
@router.post("/upload/resume", response_model=UploadResponse)
async def upload_resume(file: UploadFile = File(...)) -> UploadResponse:
    try:
        record = await file_parser_service.parse_upload(file)
        return UploadResponse(
            success=True,
            file_id=record.file_id,
            filename=record.filename,
            file_type=record.file_type,
            parsed_text=record.parsed_text,
            parsed_char_count=record.parsed_char_count,
            is_audio=record.is_audio,
            file_sha256=record.file_sha256,
        )
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail={"error": "UnsupportedFileType", "message": str(exc)}) from exc
    except FileParserError as exc:
        raise HTTPException(status_code=400, detail={"error": "FileParserError", "message": str(exc)}) from exc
    except Exception as exc:
        logger.error("文件上传解析失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "InternalServerError", "message": "文件解析失败"}) from exc
