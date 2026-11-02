from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.schemas.agent_schema import AgentRequest, AgentResponse
from app.services.career_planning_service import career_planning_service


class CareerPlanningAgent(BaseAgent):
    name = "career_planning_agent"
    task_type = "career_planning"

    async def run(self, request: AgentRequest) -> AgentResponse:
        report = await career_planning_service.generate(request)
        return AgentResponse(
            success=True,
            agent=self.name,
            task_type=self.task_type,
            message="个性化职业规划已生成。你可以继续追问或补充目标方向后重新规划。",
            result=report,
        )
