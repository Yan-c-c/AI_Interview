from __future__ import annotations

import json
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse

from app.agents.resume_evaluation_agent import ResumeEvaluationAgent
from app.router.agent_dispatcher import agent_dispatcher
from app.schemas.agent_schema import AgentRequest, Intent
from app.schemas.resume_schema import (
    ResumeEvaluateRequest,
    ResumeEvaluateResponse,
    ResumeReportPdfRequest,
    ResumeReportShareRequest,
    ResumeReportShareResponse,
)
from app.services.email_sender_service import normalize_email, resume_report_email_sender
from app.services.file_parser_service import file_parser_service
from app.services.report_pdf_service import resume_report_pdf_service

router = APIRouter(prefix="/api/resume", tags=["简历评估"])


def _safe_pdf_filename(filename: str | None) -> str:
    raw = (filename or "简历评估报告.pdf").strip()
    if not raw.lower().endswith(".pdf"):
        raw = f"{raw}.pdf"
    return raw.replace("\r", "").replace("\n", "")[:120]


@router.post("/evaluate", response_model=ResumeEvaluateResponse)
async def evaluate_resume(request: ResumeEvaluateRequest) -> ResumeEvaluateResponse:
    resume_text = request.resume_text
    filename = request.filename

    if request.file_id:
        record = file_parser_service.get_record(request.file_id)
        if not record:
            raise HTTPException(status_code=404, detail={"error": "FileNotFound", "message": "未找到上传文件，请重新上传。"})
        resume_text = record.parsed_text
        filename = record.filename

    if not resume_text or not resume_text.strip():
        raise HTTPException(status_code=400, detail={"error": "EmptyResume", "message": "未检测到简历文本。"})

    response = await agent_dispatcher.dispatch(
        Intent.resume_evaluation,
        AgentRequest(
            message=request.message,
            file_id=request.file_id,
            filename=filename,
            resume_text=resume_text,
            api_config=request.api_config,
            metadata={"filename": filename},
        ),
    )
    return ResumeEvaluateResponse(success=response.success, result=response.result)


@router.post("/evaluate/stream")
async def evaluate_resume_stream(request: ResumeEvaluateRequest):
    record = file_parser_service.get_record(request.file_id) if request.file_id else None
    resume_text = request.resume_text or (record.parsed_text if record else None)
    filename = request.filename or (record.filename if record else None)

    async def event_generator():
        if request.file_id and not record:
            yield f"data: {json.dumps({'type': 'result', 'success': False, 'message': '未找到上传文件，请重新上传。'}, ensure_ascii=False)}\n\n"
            return
        agent_request = AgentRequest(
            message=request.message,
            file_id=request.file_id,
            filename=filename,
            resume_text=resume_text,
            metadata={"filename": filename or ""},
        )
        async for event in ResumeEvaluationAgent().stream(agent_request):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/report/pdf")
async def download_resume_report_pdf(request: ResumeReportPdfRequest):
    if not request.report:
        raise HTTPException(status_code=400, detail={"error": "EmptyReport", "message": "报告内容为空，无法导出 PDF。"})

    filename = _safe_pdf_filename(request.filename or request.report.get("metadata", {}).get("filename") or "简历评估报告.pdf")
    try:
        pdf_bytes = resume_report_pdf_service.render(request.report)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": "PdfRenderFailed", "message": "PDF 生成失败，请稍后重试。"}) from exc

    quoted = quote(filename)
    return Response(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"},
    )


@router.post("/report/share", response_model=ResumeReportShareResponse)
async def share_resume_report(request: ResumeReportShareRequest) -> ResumeReportShareResponse:
    try:
        email = normalize_email(request.email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "InvalidEmail", "message": "请输入有效的邮箱地址。"}) from exc

    if not request.report:
        raise HTTPException(status_code=400, detail={"error": "EmptyReport", "message": "报告内容为空，无法分享。" })

    filename = _safe_pdf_filename(request.filename or request.report.get("metadata", {}).get("filename") or "简历评估报告.pdf")
    try:
        pdf_bytes = resume_report_pdf_service.render(request.report)
        resume_report_email_sender.send_report_pdf(email=email, pdf_bytes=pdf_bytes, filename=filename)
    except RuntimeError as exc:
        error_key = str(exc)
        if error_key == "smtp_not_configured":
            message = "后端 SMTP 未配置，无法发送报告邮件。"
        elif error_key == "smtp_invalid_port":
            message = "SMTP 端口配置不正确。"
        else:
            message = "报告邮件发送失败，请检查 SMTP 配置或稍后重试。"
        raise HTTPException(status_code=500, detail={"error": error_key, "message": message}) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": "ReportShareFailed", "message": "报告分享失败，请稍后重试。"}) from exc

    return ResumeReportShareResponse(success=True, message="报告 PDF 已发送到指定邮箱。", email=email)
