from fastapi import APIRouter, HTTPException
from app.schemas.assistant_schema import AssistantChatRequest, AssistantChatResponse
from app.services.general_chat_service import general_chat_service
router = APIRouter(prefix="/api/assistant", tags=["统一助手"])

@router.post("/chat", response_model=AssistantChatResponse)
async def assistant_chat(request: AssistantChatRequest) -> AssistantChatResponse:
    try:
        reply = await general_chat_service.chat(request.message, request.api_config)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": "LLMChatFailed", "message": "大模型对话暂时不可用，请检查后端 API 配置。"}) from exc
    return AssistantChatResponse(success=True, intent="general_chat", agent="general_chat_agent", message=reply)
