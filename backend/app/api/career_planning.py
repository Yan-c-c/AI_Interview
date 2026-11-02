from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.agents.career_planning_agent import CareerPlanningAgent
from app.schemas.agent_schema import AgentRequest
from app.schemas.career_planning_schema import (
    CareerPlanningExportRequest,
    CareerPlanningGenerateRequest,
    CareerPlanningResponse,
    CareerPlanningRewriteRequest,
)
from app.services.career_planning_service import career_planning_service
from app.services.document_export_service import document_export_service, safe_export_filename
from app.services.file_parser_service import file_parser_service

router = APIRouter(prefix="/api/career-planning", tags=["职业规划"])


@router.post("/generate", response_model=CareerPlanningResponse)
async def generate_career_plan(request: CareerPlanningGenerateRequest) -> CareerPlanningResponse:
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
            "current_identity": request.current_identity,
            "target_direction": request.target_direction,
            "current_stage": request.current_stage,
            "expected_city": request.expected_city,
            "expected_industry": request.expected_industry,
            "expected_salary": request.expected_salary,
            "available_time": request.available_time,
            "confusion": request.confusion,
            "personal_background": request.personal_background,
        },
    )
    response = await CareerPlanningAgent().run(agent_request)
    return CareerPlanningResponse(success=response.success, result=response.result, message=response.message)


@router.post("/rewrite", response_model=CareerPlanningResponse)
async def rewrite_career_plan(request: CareerPlanningRewriteRequest) -> CareerPlanningResponse:
    if not request.report:
        raise HTTPException(status_code=400, detail={"error": "EmptyReport", "message": "请先生成职业规划后再调整。"})
    try:
        report = await career_planning_service.rewrite(report=request.report, instruction=request.instruction, api_config=request.api_config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "EmptyInstruction", "message": "请填写调整要求。"}) from exc
    return CareerPlanningResponse(success=True, result=report, message="职业规划已更新。")


@router.post("/export")
async def export_career_plan(request: CareerPlanningExportRequest):
    if not request.report:
        raise HTTPException(status_code=400, detail={"error": "EmptyReport", "message": "导出内容为空。"})
    fmt = request.format.lower().strip()
    if fmt not in {"markdown", "md", "docx", "pdf"}:
        raise HTTPException(status_code=400, detail={"error": "UnsupportedFormat", "message": "仅支持 Markdown、DOCX、PDF 导出。"})
    markdown = document_export_service.career_plan_markdown(request.report)
    suffix = "md" if fmt in {"markdown", "md"} else fmt
    filename = safe_export_filename(request.filename or "职业规划报告", suffix)
    if suffix == "md":
        content = document_export_service.markdown_bytes(markdown)
        media_type = "text/markdown; charset=utf-8"
    elif suffix == "docx":
        content = document_export_service.docx_bytes(markdown)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        content = document_export_service.pdf_bytes("职业规划报告", markdown)
        media_type = "application/pdf"
    return Response(content, media_type=media_type, headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})


@router.get("/history")
async def career_plan_history(limit: int = 20) -> dict:
    return {"success": True, "items": career_planning_service.history(limit=limit)}
