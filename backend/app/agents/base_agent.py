from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.agent_schema import AgentRequest, AgentResponse


class BaseAgent(ABC):
    name: str
    task_type: str

    @abstractmethod
    async def run(self, request: AgentRequest) -> AgentResponse:
        raise NotImplementedError


class TodoAgent(BaseAgent):
    def __init__(self, name: str, task_type: str):
        self.name = name
        self.task_type = task_type

    async def run(self, request: AgentRequest) -> AgentResponse:
        return AgentResponse(
            success=False,
            agent=self.name,
            task_type=self.task_type,
            status="todo",
            message="该功能框架已预留，业务逻辑待后续实现。",
            result={
                "success": False,
                "status": "todo",
                "message": "该功能框架已预留，业务逻辑待后续实现。",
            },
        )
