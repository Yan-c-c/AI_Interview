from __future__ import annotations

import asyncio
import logging
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.core.resume_experts import EXPERTS
from app.core.resume_reflector import ResumeReflectorAgent

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

    def __init__(self) -> None:
        builder = StateGraph(ResumeRoundTableState)
        builder.add_node("expert_roundtable", self._expert_roundtable_node)
        builder.add_node("reflector", self._reflector_node)
        builder.set_entry_point("expert_roundtable")
        builder.add_edge("expert_roundtable", "reflector")
        builder.add_edge("reflector", END)
        self.graph = builder.compile()

    async def ainvoke(self, state: ResumeRoundTableState) -> ResumeRoundTableState:
        return await self.graph.ainvoke(state)

    async def astream_events(self, state: ResumeRoundTableState):
        """Stream roundtable progress events while preserving the same expert workflow."""
        working_state: ResumeRoundTableState = dict(state)
        expert_outputs: dict[str, Any] = {}
        errors: list[str] = list(working_state.get("errors", []))

        yield {
            "type": "progress",
            "stage": "roundtable",
            "status": "running",
            "message": "多专家圆桌会议已启动，专家正在并行分析。",
        }

        async def run_expert(expert):
            try:
                result = await expert.analyze(
                    resume_text=working_state["resume_text"],
                    user_message=working_state.get("user_message", ""),
                    target_position=working_state.get("target_position", ""),
                    target_position_source=working_state.get("target_position_source", "system_inferred"),
                    tool_findings=working_state.get("tool_findings", {}),
                    api_config=working_state.get("api_config"),
                )
                return expert.key, expert.role, result, None
            except Exception as exc:
                logger.warning("%s failed: %s", expert.role, exc)
                return expert.key, expert.role, {"role": expert.role, "findings": [], "suggestions": [], "error": str(exc)}, str(exc)

        tasks = []
        for expert in EXPERTS:
            yield {
                "type": "expert_status",
                "stage": "roundtable",
                "expert": expert.key,
                "role": expert.role,
                "status": "running",
                "message": f"{expert.role}正在分析...",
            }
            tasks.append(asyncio.create_task(run_expert(expert)))

        pending = set(tasks)
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                key, role, result, error = task.result()
                expert_outputs[key] = result
                if error:
                    errors.append(f"{key}: {error}")
                    status = "error"
                    message = f"{role}暂时不可用。"
                else:
                    status = "done"
                    message = f"{role}已完成诊断。"
                yield {
                    "type": "expert_status",
                    "stage": "roundtable",
                    "expert": key,
                    "role": role,
                    "status": status,
                    "message": message,
                    "result": result,
                }

        working_state["expert_outputs"] = expert_outputs
        working_state["errors"] = errors
        working_state["llm_failed"] = len(errors) == len(EXPERTS)

        if working_state.get("llm_failed"):
            working_state["reflector_output"] = {}
            yield {
                "type": "progress",
                "stage": "roundtable",
                "status": "error",
                "message": "所有专家节点均不可用，未生成 AI 圆桌评估报告。",
            }
            yield {"type": "state", "stage": "roundtable", "state": working_state}
            return

        yield {
            "type": "expert_status",
            "stage": "reflector",
            "expert": "reflector",
            "role": "质量审核节点",
            "status": "running",
            "message": "Reflector 正在去重、反思并整合最终报告...",
        }
        try:
            reflector = ResumeReflectorAgent()
            output = await reflector.reflect(
                resume_text=working_state["resume_text"],
                user_message=working_state.get("user_message", ""),
                target_position=working_state.get("target_position", ""),
                target_position_source=working_state.get("target_position_source", "system_inferred"),
                tool_findings=working_state.get("tool_findings", {}),
                expert_outputs=working_state.get("expert_outputs", {}),
                filename=working_state.get("filename", ""),
                api_config=working_state.get("api_config"),
            )
            working_state["reflector_output"] = output
            yield {
                "type": "expert_status",
                "stage": "reflector",
                "expert": "reflector",
                "role": "质量审核节点",
                "status": "done",
                "message": "Reflector 已完成最终整合。",
                "result": output.get("roundtable", {}).get("reflector", {}),
            }
        except Exception as exc:
            logger.warning("Reflector failed: %s", exc)
            working_state["reflector_output"] = {}
            working_state["llm_failed"] = True
            working_state["errors"] = errors + [f"reflector: {exc}"]
            yield {
                "type": "expert_status",
                "stage": "reflector",
                "expert": "reflector",
                "role": "质量审核节点",
                "status": "error",
                "message": "Reflector 暂时不可用，未生成最终 AI 报告。",
            }

        yield {"type": "state", "stage": "roundtable", "state": working_state}

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

    async def _reflector_node(self, state: ResumeRoundTableState) -> dict[str, Any]:
        if state.get("llm_failed"):
            return {"reflector_output": {}, "llm_failed": True}
        try:
            reflector = ResumeReflectorAgent()
            output = await reflector.reflect(
                resume_text=state["resume_text"],
                user_message=state.get("user_message", ""),
                target_position=state.get("target_position", ""),
                target_position_source=state.get("target_position_source", "system_inferred"),
                tool_findings=state.get("tool_findings", {}),
                expert_outputs=state.get("expert_outputs", {}),
                filename=state.get("filename", ""),
                api_config=state.get("api_config"),
            )
            return {"reflector_output": output}
        except Exception as exc:
            logger.warning("Reflector failed: %s", exc)
            return {
                "reflector_output": {},
                "llm_failed": True,
                "errors": state.get("errors", []) + [f"reflector: {exc}"],
            }
