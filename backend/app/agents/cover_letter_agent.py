from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.schemas.agent_schema import AgentRequest, AgentResponse
from app.services.cover_letter_service import cover_letter_service


class CoverLetterAgent(BaseAgent):
    name = "cover_letter_agent"
    task_type = "cover_letter_generation"

    async def run(self, request: AgentRequest) -> AgentResponse:
        report = await cover_letter_service.generate(request)
        return AgentResponse(
            success=True,
            agent=self.name,
            task_type=self.task_type,
            message="个性化求职信已生成。你可以继续补充公司、岗位或风格要求进行改写。",
            result=report,
        )
