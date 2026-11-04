from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.schemas.agent_schema import AgentRequest, AgentResponse
from app.services.email_campaign_service import email_campaign_service


class EmailCampaignAgent(BaseAgent):
    name = "email_campaign_agent"
    task_type = "email_campaign"

    async def run(self, request: AgentRequest) -> AgentResponse:
        result = email_campaign_service.preview_workspace(
            filename=request.filename or "",
            parsed_char_count=len(request.resume_text or ""),
        )
        return AgentResponse(
            success=True,
            agent=self.name,
            task_type=self.task_type,
            message="邮件群发 Agent 已打开。请在工作台中配置 SMTP、添加收件人、生成或填写邮件内容，并在预览确认后发送。",
            result=result,
        )
