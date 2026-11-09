from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.schemas.agent_schema import AgentRequest, AgentResponse
from app.services.salary_negotiation_service import salary_negotiation_service


class SalaryNegotiationAgent(BaseAgent):
    name = "salary_negotiation_agent"
    task_type = "salary_negotiation"

    async def run(self, request: AgentRequest) -> AgentResponse:
        report = await salary_negotiation_service.analyze(request)
        return AgentResponse(
            success=True,
            agent=self.name,
            task_type=self.task_type,
            message="薪资谈判工作台已生成。你可以继续调整岗位、offer、地区和技能后重新分析。",
            result=report,
        )
