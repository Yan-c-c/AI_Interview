from __future__ import annotations

from app.agents.career_planning_agent import CareerPlanningAgent
from app.agents.cover_letter_agent import CoverLetterAgent
from app.agents.email_campaign_agent import EmailCampaignAgent
from app.agents.interview_audio_agent import InterviewAudioAnalysisAgent
from app.agents.interview_question_agent import InterviewQuestionGenerationAgent
from app.agents.resume_evaluation_agent import ResumeEvaluationAgent
from app.agents.salary_negotiation_agent import SalaryNegotiationAgent
from app.schemas.agent_schema import AgentRequest, AgentResponse, Intent


class AgentDispatcher:
    def __init__(self) -> None:
        self._agents = {
            Intent.resume_evaluation: ResumeEvaluationAgent(),
            Intent.interview_audio_analysis: InterviewAudioAnalysisAgent(),
            Intent.interview_question_generation: InterviewQuestionGenerationAgent(),
            Intent.cover_letter_generation: CoverLetterAgent(),
            Intent.email_campaign: EmailCampaignAgent(),
            Intent.salary_negotiation: SalaryNegotiationAgent(),
            Intent.career_planning: CareerPlanningAgent(),
        }

    async def dispatch(self, intent: Intent, request: AgentRequest) -> AgentResponse:
        agent = self._agents.get(intent)
        if not agent:
            return AgentResponse(
                success=False,
                agent="unknown",
                task_type=Intent.unknown.value,
                message="无法识别可调度的 Agent。",
                result={"success": False, "error": "unknown_intent"},
            )
        return await agent.run(request)


agent_dispatcher = AgentDispatcher()
