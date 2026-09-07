from __future__ import annotations

from fastapi import APIRouter

from app.agents.salary_negotiation_agent import SalaryNegotiationAgent
from app.schemas.agent_schema import AgentRequest

router = APIRouter(prefix="/api", tags=["预留 Agent"])


@router.post("/salary-negotiation/chat")
async def salary_negotiation_chat(request: AgentRequest) -> dict:
    return (await SalaryNegotiationAgent().run(request)).result
