from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.agents.cover_letter_agent import CoverLetterAgent
from app.schemas.agent_schema import AgentRequest
from app.schemas.cover_letter_schema import (
    CoverLetterExportRequest,
    CoverLetterGenerateRequest,
    CoverLetterResponse,
    CoverLetterRewriteRequest,
    CoverLetterSendEmailRequest,
)
from app.services.cover_letter_service import cover_letter_service
from app.services.document_export_service import document_export_service, safe_export_filename
from app.services.email_service import EmailAttachment, email_service
from app.services.file_parser_service import file_parser_service

router = APIRouter(prefix="/api/cover-letter", tags=["求职信生成"])


@router.post("/generate", response_model=CoverLetterResponse)
async def generate_cover_letter(request: CoverLetterGenerateRequest) -> CoverLetterResponse:
    record = file_parser_service.get_record(request.file_id) if request.file_id else None
    if request.file_id and not record:
        raise HTTPException(status_code=404, detail={"error": "FileNotFound", "message": "未找到上传文件，请重新上传。"})
    agent_request = AgentRequest(
        message=request.message,
        file_id=request.file_id,
        filename=request.filename or (record.filename if record else None),
        resume_text=request.resume_text or (record.parsed_text if record else None),
        api_config=request.api_config,
        metadata={
            "filename": request.filename or (record.filename if record else ""),
            "target_company": request.target_company,
            "target_position": request.target_position,
            "jd": request.jd,
            "recipient": request.recipient,
            "purpose": request.purpose,
            "style": request.style,
            "focus_points": request.focus_points,
            "word_count": request.word_count,
            "personal_background": request.personal_background,
        },
    )
    response = await CoverLetterAgent().run(agent_request)
    return CoverLetterResponse(success=response.success, result=response.result, message=response.message)


@router.post("/rewrite", response_model=CoverLetterResponse)
async def rewrite_cover_letter(request: CoverLetterRewriteRequest) -> CoverLetterResponse:
    if not request.report:
        raise HTTPException(status_code=400, detail={"error": "EmptyReport", "message": "请先生成求职信后再改写。"})
    try:
        report = await cover_letter_service.rewrite(report=request.report, instruction=request.instruction, api_config=request.api_config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "EmptyInstruction", "message": "请填写修改要求。"}) from exc
    return CoverLetterResponse(success=True, result=report, message="求职信已按要求改写。")


@router.post("/export")
async def export_cover_letter(request: CoverLetterExportRequest):
    if not request.report:
        raise HTTPException(status_code=400, detail={"error": "EmptyReport", "message": "导出内容为空。"})
    fmt = request.format.lower().strip()
    if fmt not in {"markdown", "md", "docx", "pdf"}:
        raise HTTPException(status_code=400, detail={"error": "UnsupportedFormat", "message": "仅支持 Markdown、DOCX、PDF 导出。"})
    markdown = document_export_service.cover_letter_markdown(request.report, request.version)
    suffix = "md" if fmt in {"markdown", "md"} else fmt
    filename = safe_export_filename(request.filename or "求职信", suffix)
    if suffix == "md":
        content = document_export_service.markdown_bytes(markdown)
        media_type = "text/markdown; charset=utf-8"
    elif suffix == "docx":
        content = document_export_service.docx_bytes(markdown)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        content = document_export_service.pdf_bytes("求职信", markdown)
        media_type = "application/pdf"
    return Response(content, media_type=media_type, headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})


@router.post("/send-email")
async def send_cover_letter_email(request: CoverLetterSendEmailRequest) -> dict:
    if not request.report:
        raise HTTPException(status_code=400, detail={"error": "EmptyReport", "message": "请先生成求职信。"})
    email_data = request.report.get("email") or {}
    subject = request.subject.strip() or str(email_data.get("subject") or "求职申请")
    body = request.body.strip() or str(email_data.get("body") or "")
    if request.save_draft:
        draft = email_service.save_draft(to_email=request.to_email, subject=subject, body=body, metadata={"source": "cover_letter"})
        return {"success": True, "status": "draft_saved", "message": "邮件草稿已保存。", "draft": draft}
    attachments: list[EmailAttachment] = []
    if request.attach_cover_letter:
        markdown = document_export_service.cover_letter_markdown(request.report, request.version)
        attachments.append(
            EmailAttachment(
                filename=safe_export_filename("求职信", "pdf"),
                content=document_export_service.pdf_bytes("求职信", markdown),
                maintype="application",
                subtype="pdf",
            )
        )
    if request.attach_resume_file and request.resume_file_id:
        record = file_parser_service.get_record(request.resume_file_id)
        if record and record.file_path and Path(record.file_path).exists():
            attachments.append(
                EmailAttachment(
                    filename=record.filename,
                    content=Path(record.file_path).read_bytes(),
                    maintype="application",
                    subtype="octet-stream",
                )
            )
    try:
        recipient = email_service.send(to_email=request.to_email, subject=subject, body=body, attachments=attachments)
    except RuntimeError as exc:
        messages = {
            "smtp_not_configured": "邮件服务未配置，不影响求职信生成和导出。",
            "smtp_invalid_port": "SMTP 端口配置不正确。",
            "email_send_failed": "邮件发送失败，请检查 SMTP 配置或稍后重试。",
        }
        return {"success": False, "status": str(exc), "message": messages.get(str(exc), "邮件发送失败。")}
    return {"success": True, "status": "sent", "message": "求职信邮件已发送。", "email": recipient}


@router.get("/history")
async def cover_letter_history(limit: int = 20) -> dict:
    return {"success": True, "items": cover_letter_service.history(limit=limit)}
