from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.agents.salary_negotiation_agent import SalaryNegotiationAgent
from app.schemas.agent_schema import AgentRequest
from app.schemas.salary_negotiation_schema import (
    SalaryAnalyzeRequest,
    SalaryExportRequest,
    SalaryNegotiationResponse,
    SalarySimulationRequest,
    SalaryStrategyRequest,
)
from app.services.document_export_service import document_export_service, safe_export_filename
from app.services.file_parser_service import file_parser_service
from app.services.salary_negotiation_service import salary_negotiation_service

router = APIRouter(prefix="/api/salary-negotiation", tags=["薪资谈判"])


@router.post("/analyze", response_model=SalaryNegotiationResponse)
async def analyze_salary(request: SalaryAnalyzeRequest) -> SalaryNegotiationResponse:
    record = file_parser_service.get_record(request.file_id) if request.file_id else None
    if request.file_id and not record:
        raise HTTPException(status_code=404, detail={"error": "FileNotFound", "message": "未找到上传文件，请重新上传。"})
    agent_request = AgentRequest(
        message=request.message,
        file_id=request.file_id,
        filename=record.filename if record else None,
        resume_text=request.resume_text or (record.parsed_text if record else None),
        api_config=request.api_config,
        metadata={
            "job_title": request.job_title,
            "experience_level": request.experience_level,
            "years_experience": request.years_experience,
            "country": request.country,
            "city": request.city,
            "company_size": request.company_size,
            "industry": request.industry,
            "employment_type": request.employment_type,
            "remote_ratio": request.remote_ratio,
            "education_required": request.education_required,
            "skills": request.skills,
            "current_offer": request.current_offer,
            "expected_salary": request.expected_salary,
        },
    )
    response = await SalaryNegotiationAgent().run(agent_request)
    return SalaryNegotiationResponse(success=response.success, result=response.result, message=response.message)


@router.post("/generate-strategy", response_model=SalaryNegotiationResponse)
async def generate_strategy(request: SalaryStrategyRequest) -> SalaryNegotiationResponse:
    strategy = await salary_negotiation_service.generate_strategy(
        profile=request.profile,
        prediction=request.prediction,
        trend=request.trend,
        simulation=request.simulation,
        api_config=request.api_config,
        message=request.message,
    )
    return SalaryNegotiationResponse(success=True, result={"strategy": strategy}, message="谈薪策略已生成。")


@router.post("/simulate", response_model=SalaryNegotiationResponse)
async def simulate_salary_negotiation(request: SalarySimulationRequest) -> SalaryNegotiationResponse:
    result = salary_negotiation_service.simulate(request.market_salary, request.exp_level, request.company_size)
    return SalaryNegotiationResponse(success=True, result={"simulation": result}, message=result.get("message"))


@router.post("/export")
async def export_salary_report(request: SalaryExportRequest):
    if not request.report:
        raise HTTPException(status_code=400, detail={"error": "EmptyReport", "message": "导出内容为空。"})
    fmt = request.format.lower().strip()
    if fmt not in {"markdown", "md", "docx", "pdf"}:
        raise HTTPException(status_code=400, detail={"error": "UnsupportedFormat", "message": "仅支持 Markdown、DOCX、PDF 导出。"})
    markdown = _salary_report_markdown(request.report)
    suffix = "md" if fmt in {"markdown", "md"} else fmt
    filename = safe_export_filename(request.filename or "薪资谈判报告", suffix)
    if suffix == "md":
        content = document_export_service.markdown_bytes(markdown)
        media_type = "text/markdown; charset=utf-8"
    elif suffix == "docx":
        content = document_export_service.docx_bytes(markdown)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        content = document_export_service.pdf_bytes("薪资谈判报告", markdown)
        media_type = "application/pdf"
    return Response(content, media_type=media_type, headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})


@router.get("/history")
async def salary_history(limit: int = 20) -> dict:
    return {"success": True, "items": salary_negotiation_service.history(limit=limit)}


def _salary_report_markdown(report: dict) -> str:
    profile = report.get("profile") or {}
    prediction = report.get("prediction") or {}
    strategy = report.get("strategy") or {}
    simulation = report.get("simulation") or {}
    return "\n\n".join(
        [
            "# 薪资谈判报告",
            f"岗位：{profile.get('job_title', '待补充')}",
            f"地区：{profile.get('country', '待补充')} {profile.get('city', '')}",
            f"预测薪资：{prediction.get('salary', '未知')}（{prediction.get('salary_low', '')} - {prediction.get('salary_high', '')}）",
            f"合理薪资区间：{strategy.get('reasonable_range', '')}",
            f"建议目标薪资：${int(strategy.get('target_salary') or 0):,}",
            f"最低可接受薪资：${int(strategy.get('minimum_acceptable_salary') or 0):,}",
            "## 是否建议接受 Offer",
            str(strategy.get("offer_decision") or "暂无"),
            "## 谈判策略",
            _markdown_list(strategy.get("negotiation_strategy")),
            "## 谈薪话术",
            _markdown_list(strategy.get("talking_scripts")),
            "## HR 压价应对",
            _markdown_list(strategy.get("hr_pushback_responses")),
            "## 风险提醒",
            _markdown_list(strategy.get("risk_alerts")),
            "## 谈判模拟",
            str(simulation.get("result_text") or simulation.get("message") or "暂无"),
            "## 最终报告",
            str(strategy.get("final_report") or "暂无"),
        ]
    )


def _markdown_list(value) -> str:
    if not isinstance(value, list) or not value:
        return "暂无"
    return "\n".join(f"- {item}" for item in value if str(item).strip())
