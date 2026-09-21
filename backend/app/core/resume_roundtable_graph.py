from __future__ import annotations

import asyncio
import logging
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.core.resume_experts import EXPERTS

logger = logging.getLogger(__name__)


class ResumeRoundTableState(TypedDict, total=False):
    resume_text: str
    user_message: str
    target_position: str
    target_position_source: str
    tool_findings: dict[str, Any]
    filename: str
    api_config: dict[str, Any] | None
    expert_outputs: dict[str, Any]
    reflector_output: dict[str, Any]
    llm_failed: bool
    errors: list[str]


class ResumeRoundTableGraph:
    """LangGraph workflow for the resume multi-expert roundtable."""




    async def _expert_roundtable_node(self, state: ResumeRoundTableState) -> dict[str, Any]:
        async def run_expert(expert):
            try:
                result = await expert.analyze(
                    resume_text=state["resume_text"],
                    user_message=state.get("user_message", ""),
                    target_position=state.get("target_position", ""),
                    target_position_source=state.get("target_position_source", "system_inferred"),
                    tool_findings=state.get("tool_findings", {}),
                    api_config=state.get("api_config"),
                )
                return expert.key, result, None
            except Exception as exc:
                logger.warning("%s failed: %s", expert.role, exc)
                return expert.key, {"role": expert.role, "findings": [], "suggestions": [], "error": str(exc)}, str(exc)

        results = await asyncio.gather(*(run_expert(expert) for expert in EXPERTS))
        expert_outputs = {key: result for key, result, _error in results}
        errors = [f"{key}: {error}" for key, _result, error in results if error]
        return {
            "expert_outputs": expert_outputs,
            "errors": state.get("errors", []) + errors,
            "llm_failed": len(errors) == len(EXPERTS),
        }

