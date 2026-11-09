from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.resume_evaluation_agent import ResumeEvaluationAgent
from app.router.agent_dispatcher import agent_dispatcher
from app.router.intent_router import intent_router
from app.schemas.agent_schema import AgentRequest, Intent
from app.schemas.assistant_schema import AssistantChatRequest, AssistantChatResponse
from app.services.file_parser_service import file_parser_service
from app.services.general_chat_service import general_chat_service

router = APIRouter(prefix="/api/assistant", tags=["统一助手"])

TEXT_INPUT_INTENTS = {Intent.resume_evaluation, Intent.interview_question_generation, Intent.interview_audio_analysis}


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/chat", response_model=AssistantChatResponse)
async def assistant_chat(request: AssistantChatRequest) -> AssistantChatResponse:
    record = file_parser_service.get_record(request.file_id) if request.file_id else None
    route = intent_router.route(request.message, has_file=bool(record or request.file_id))

    if route.needs_clarification:
        return AssistantChatResponse(success=True, intent=Intent.unknown.value, message=route.message)

    if route.intent == Intent.unknown:
        try:
            reply = await general_chat_service.chat(request.message, request.api_config)
        except Exception as exc:
            raise HTTPException(status_code=500, detail={"error": "LLMChatFailed", "message": "大模型对话暂时不可用，请检查后端 API 配置。"}) from exc
        return AssistantChatResponse(success=True, intent="general_chat", agent="general_chat_agent", message=reply)

    if request.file_id and not record:
        raise HTTPException(status_code=404, detail={"error": "FileNotFound", "message": "未找到上传文件，请重新上传。"})

    text_input = not request.file_id and route.intent in TEXT_INPUT_INTENTS
    resume_text = record.parsed_text if record else (request.message if text_input and route.intent != Intent.interview_audio_analysis else None)
    metadata = {
        "filename": record.filename if record else ("粘贴文本" if text_input else ""),
        "file_type": record.file_type if record else ("text" if text_input else ""),
        "file_record": record.__dict__ if record else None,
    }
    if text_input and route.intent == Intent.interview_audio_analysis:
        metadata["transcript_text"] = request.message

    agent_request = AgentRequest(
        message=request.message,
        file_id=request.file_id,
        filename=record.filename if record else ("粘贴文本" if text_input else None),
        resume_text=resume_text,
        session_id=request.session_id,
        api_config=request.api_config,
        metadata=metadata,
    )
    response = await agent_dispatcher.dispatch(route.intent, agent_request)
    return AssistantChatResponse(
        success=response.success,
        intent=route.intent.value,
        agent=response.agent,
        result=response.result,
        message=response.message,
    )


@router.post("/chat/stream")
async def assistant_chat_stream(request: AssistantChatRequest):
    record = file_parser_service.get_record(request.file_id) if request.file_id else None
    route = intent_router.route(request.message, has_file=bool(record or request.file_id))

    async def event_generator():
        if route.needs_clarification:
            yield _sse_event({"type": "result", "success": True, "intent": Intent.unknown.value, "message": route.message})
            return
        if route.intent == Intent.unknown:
            try:
                reply = await general_chat_service.chat(request.message, request.api_config)
                yield _sse_event({"type": "result", "success": True, "intent": "general_chat", "agent": "general_chat_agent", "message": reply})
            except Exception:
                yield _sse_event({"type": "result", "success": False, "intent": "general_chat", "message": "大模型对话暂时不可用，请检查后端 API 配置。"})
            return
        if request.file_id and not record:
            yield _sse_event({"type": "result", "success": False, "intent": route.intent.value, "message": "未找到上传文件，请重新上传。"})
            return

        text_input = not request.file_id and route.intent in TEXT_INPUT_INTENTS
        resume_text = record.parsed_text if record else (request.message if text_input and route.intent != Intent.interview_audio_analysis else None)
        metadata = {
            "filename": record.filename if record else ("粘贴文本" if text_input else ""),
            "file_type": record.file_type if record else ("text" if text_input else ""),
            "file_record": record.__dict__ if record else None,
        }
        if text_input and route.intent == Intent.interview_audio_analysis:
            metadata["transcript_text"] = request.message

        agent_request = AgentRequest(
            message=request.message,
            file_id=request.file_id,
            filename=record.filename if record else ("粘贴文本" if text_input else None),
            resume_text=resume_text,
            session_id=request.session_id,
            api_config=request.api_config,
            metadata=metadata,
        )
        if route.intent != Intent.resume_evaluation:
            response = await agent_dispatcher.dispatch(route.intent, agent_request)
            yield _sse_event({
                "type": "result",
                "success": response.success,
                "intent": route.intent.value,
                "agent": response.agent,
                "message": response.message,
                "result": response.result,
            })
            yield _sse_event({"type": "done"})
            return

        async for event in ResumeEvaluationAgent().stream(agent_request):
            event.setdefault("intent", route.intent.value)
            event.setdefault("agent", "resume_evaluation_agent")
            yield _sse_event(event)
        yield _sse_event({"type": "done"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
