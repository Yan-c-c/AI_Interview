from __future__ import annotations

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.interview_question_agent import InterviewQuestionGenerationAgent
from app.core.json_utils import loads_json_response
from app.core.llms import get_llm_for_request
from app.schemas.agent_schema import AgentRequest
from app.services.file_parser_service import file_parser_service

router = APIRouter(prefix="/api/interview-question", tags=["面试题生成"])


class InterviewFollowUpRequest(BaseModel):
    question: str
    answer: str
    resume_profile: dict = Field(default_factory=dict)
    scenario: dict = Field(default_factory=dict)
    interview_status: str | None = None
    api_config: dict | None = None


class InterviewReportRequest(BaseModel):
    resume_profile: dict = Field(default_factory=dict)
    scenario: dict = Field(default_factory=dict)
    qa_history: list[dict] = Field(default_factory=list)
    api_config: dict | None = None


@router.post("/generate")
async def generate_interview_questions(request: AgentRequest) -> dict:
    record = file_parser_service.get_record(request.file_id) if request.file_id else None
    if request.file_id and not record:
        raise HTTPException(status_code=404, detail={"error": "FileNotFound", "message": "未找到上传文件，请重新上传。"})
    agent_request = request.model_copy(
        update={
            "filename": request.filename or (record.filename if record else None),
            "resume_text": request.resume_text or (record.parsed_text if record else None),
            "metadata": {**request.metadata, "filename": request.filename or (record.filename if record else "")},
        }
    )
    response = await InterviewQuestionGenerationAgent().run(agent_request)
    return {"success": response.success, "agent": response.agent, "result": response.result, "message": response.message}


@router.post("/follow-up")
async def generate_interview_follow_up(request: InterviewFollowUpRequest) -> dict:
    if request.interview_status == "completed":
        return {"success": False, "feedback": "", "follow_up": "", "answer_status": "completed"}
    if not request.answer.strip():
        raise HTTPException(status_code=400, detail={"error": "EmptyAnswer", "message": "回答内容为空，无法生成追问。"})
    try:
        llm = get_llm_for_request(request.api_config, channel="fast", temperature=0.3, max_tokens=900)
        response = await llm.ainvoke(
            [
                SystemMessage(content="你是模拟面试官。根据候选人的回答，给出一句简短反馈，并提出一个有针对性的追问。只输出 JSON。"),
                HumanMessage(
                    content=f"""面试场景：
{request.scenario}

简历画像：
{request.resume_profile}

当前问题：
{request.question}

候选人回答：
{request.answer}

输出 JSON：
{{
  "feedback": "一句话反馈，不要太长",
  "follow_up": "一个追问问题",
  "answer_status": "good | partial | weak"
}}"""
                ),
            ]
        )
        data = loads_json_response(str(response.content or ""))
        if not isinstance(data, dict):
            raise ValueError("follow-up response is not object")
        return {
            "success": True,
            "feedback": str(data.get("feedback") or "回答已收到，我想继续追问一个细节。"),
            "follow_up": str(data.get("follow_up") or "请结合简历中的具体项目，补充说明你的个人贡献。"),
            "answer_status": str(data.get("answer_status") or "partial"),
        }
    except Exception:
        return {
            "success": True,
            "feedback": "回答已收到，但细节还可以更具体。",
            "follow_up": "请补充一个具体例子，说明你在这个问题中的个人贡献、技术动作和结果指标。",
            "answer_status": "partial",
            "fallback": True,
        }


@router.post("/report")
async def generate_interview_report(request: InterviewReportRequest) -> dict:
    if not request.qa_history:
        raise HTTPException(status_code=400, detail={"error": "EmptyInterview", "message": "还没有面试问答记录，无法生成报告。"})
    try:
        llm = get_llm_for_request(request.api_config, channel="smart", temperature=0.2, max_tokens=2600)
        response = await llm.ainvoke(
            [
                SystemMessage(content="你是资深面试评估官。根据模拟面试问答生成结构化中文评估报告。只输出 JSON。"),
                HumanMessage(
                    content=f"""简历画像：
{request.resume_profile}

面试场景：
{request.scenario}

问答记录：
{request.qa_history}

请输出 JSON：
{{
  "overall_score": 0,
  "dimension_scores": {{
    "expression": 0,
    "technical_accuracy": 0,
    "project_depth": 0,
    "answer_completeness": 0
  }},
  "summary": "一句总评",
  "strengths": ["优点"],
  "problems": ["问题"],
  "suggestions": ["优化建议"],
  "review_directions": ["推荐复习方向"],
  "next_practice": "下一步练习建议"
}}"""
                ),
            ]
        )
        data = loads_json_response(str(response.content or ""))
        if not isinstance(data, dict):
            raise ValueError("report response is not object")
        return {"success": True, "report": _normalize_report(data)}
    except Exception:
        return {"success": True, "report": _fallback_report(request.qa_history), "fallback": True}


def _normalize_report(data: dict) -> dict:
    dimensions = data.get("dimension_scores") if isinstance(data.get("dimension_scores"), dict) else {}
    return {
        "overall_score": _score(data.get("overall_score"), 72),
        "dimension_scores": {
            "expression": _score(dimensions.get("expression"), 70),
            "technical_accuracy": _score(dimensions.get("technical_accuracy"), 70),
            "project_depth": _score(dimensions.get("project_depth"), 70),
            "answer_completeness": _score(dimensions.get("answer_completeness"), 70),
        },
        "summary": str(data.get("summary") or "本次模拟面试已完成，建议继续补充项目细节和量化结果。"),
        "strengths": _string_list(data.get("strengths"))[:5],
        "problems": _string_list(data.get("problems"))[:5],
        "suggestions": _string_list(data.get("suggestions"))[:6],
        "review_directions": _string_list(data.get("review_directions"))[:6],
        "next_practice": str(data.get("next_practice") or "围绕项目难点和技术原理继续练习追问。"),
    }


def _fallback_report(qa_history: list[dict]) -> dict:
    answered = [item for item in qa_history if str(item.get("answer") or "").strip()]
    base = min(85, 55 + len(answered) * 6)
    return {
        "overall_score": base,
        "dimension_scores": {
            "expression": base,
            "technical_accuracy": max(55, base - 4),
            "project_depth": max(55, base - 6),
            "answer_completeness": max(55, base - 3),
        },
        "summary": "当前为基础评估报告。建议补充更具体的技术细节、指标和复盘。",
        "strengths": ["能够完成主要问题回答", "具备基于简历项目展开表达的基础"],
        "problems": ["部分回答缺少量化结果", "技术方案的取舍和边界说明不足"],
        "suggestions": ["每题按背景、动作、结果、复盘组织回答", "补充项目指标、异常场景和个人贡献"],
        "review_directions": ["项目架构与核心链路", "数据库与缓存一致性", "接口性能优化", "常见线上问题排查"],
        "next_practice": "继续进行项目深挖轮，重点练习追问下的细节表达。",
    }


def _score(value, fallback: int) -> int:
    try:
        return max(0, min(100, int(float(value))))
    except (TypeError, ValueError):
        return fallback


def _string_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
