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










