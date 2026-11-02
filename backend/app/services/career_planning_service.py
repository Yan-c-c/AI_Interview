from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.json_utils import loads_json_response
from app.core.llms import get_llm_for_request
from app.schemas.agent_schema import AgentRequest

logger = logging.getLogger(__name__)


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.replace(",", "、").split("、") if item.strip()]
    return []


def _score(value: Any, fallback: int = 70) -> int:
    try:
        return max(0, min(100, int(float(value))))
    except (TypeError, ValueError):
        return fallback


class CareerPlanningService:
    def __init__(self) -> None:
        self.history_dir = Path(__file__).resolve().parents[2] / "data" / "career_plans"
        self.history_dir.mkdir(parents=True, exist_ok=True)

    async def generate(self, request: AgentRequest) -> dict[str, Any]:
        resume_text = (request.resume_text or "").strip()
        form = self._form_from_request(request)
        missing_fields = self._missing_fields(form, resume_text)
        used_deepseek = True
        llm_errors: list[str] = []

        try:
            payload = await self._call_generation_llm(request, resume_text, form, missing_fields)
        except Exception as exc:
            logger.warning("career planning LLM generation failed: %s", exc)
            used_deepseek = False
            llm_errors.append(str(exc))
            payload = self._fallback_payload(form, resume_text, missing_fields)

        report = self._normalize_report(
            payload=payload,
            request=request,
            form=form,
            resume_text=resume_text,
            missing_fields=missing_fields,
            used_deepseek=used_deepseek,
            llm_errors=llm_errors,
        )
        self._save_history(report)
        return report

    async def rewrite(self, *, report: dict[str, Any], instruction: str, api_config: dict | None = None) -> dict[str, Any]:
        instruction = instruction.strip()
        if not instruction:
            raise ValueError("empty_instruction")
        used_deepseek = True
        llm_errors: list[str] = []
        try:
            llm = get_llm_for_request(api_config, channel="smart", temperature=0.25, max_tokens=4800)
            response = await llm.ainvoke(
                [
                    SystemMessage(content="你是职业规划改写 Agent。根据用户新目标或补充要求重写规划，保持结构化输出。只输出 JSON。"),
                    HumanMessage(
                        content=f"""用户补充要求：
{instruction}

已有职业规划：
{json.dumps(report, ensure_ascii=False)[:14000]}

请输出完整 JSON，结构必须包含：
career_profile, matching_analysis, career_plan, learning_path, project_suggestions, job_search_strategy, next_actions。"""
                    ),
                ]
            )
            data = loads_json_response(str(response.content or ""))
            if not isinstance(data, dict):
                raise ValueError("rewrite response is not object")
        except Exception as exc:
            used_deepseek = False
            llm_errors.append(str(exc))
            data = self._fallback_rewrite(report, instruction)

        updated = self._normalize_report(
            payload={**report, **data},
            request=AgentRequest(message=instruction, api_config=api_config, metadata=report.get("metadata") or {}),
            form={},
            resume_text="",
            missing_fields=[],
            used_deepseek=used_deepseek,
            llm_errors=llm_errors,
        )
        updated["metadata"] = {
            **(report.get("metadata") or {}),
            **updated.get("metadata", {}),
            "used_deepseek_rewrite": used_deepseek,
            "rewrite_instruction": instruction,
            "rewrite_errors": llm_errors,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._save_history(updated)
        return updated

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(self.history_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]:
            try:
                items.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        return items

    async def _call_generation_llm(
        self,
        request: AgentRequest,
        resume_text: str,
        form: dict[str, Any],
        missing_fields: list[str],
    ) -> dict[str, Any]:
        llm = get_llm_for_request(request.api_config, channel="smart", temperature=0.25, max_tokens=5600)
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content=(
                        "你是职业规划 Agent。你需要结合简历/个人背景、目标方向和偏好，生成可执行的职业规划。"
                        "不要泛泛鸡汤，要输出短期、中期、长期计划、学习路径、项目补强和投递策略。只输出 JSON。"
                    )
                ),
                HumanMessage(
                    content=f"""用户自然语言需求：
{request.message}

用户补充信息：
{json.dumps(form, ensure_ascii=False)}

缺失字段：
{missing_fields}

简历或个人背景：
{(resume_text or form.get("personal_background") or request.message)[:14000]}

请输出 JSON：
{{
  "career_profile": {{
    "current_stage": "",
    "target_direction": "",
    "recommended_positions": [],
    "current_strengths": [],
    "main_gaps": []
  }},
  "matching_analysis": {{
    "target_position": "",
    "match_score": 0,
    "matched_skills": [],
    "missing_skills": [],
    "risk_points": []
  }},
  "career_plan": {{
    "short_term": [],
    "mid_term": [],
    "long_term": []
  }},
  "learning_path": {{
    "one_week": [],
    "one_month": [],
    "three_months": [],
    "six_months": []
  }},
  "project_suggestions": [],
  "job_search_strategy": [],
  "next_actions": [],
  "needs_more_info": false,
  "missing_fields": []
}}"""
                ),
            ]
        )
        data = loads_json_response(str(response.content or ""))
        if not isinstance(data, dict):
            raise ValueError("career planning response is not object")
        return data

    def _form_from_request(self, request: AgentRequest) -> dict[str, Any]:
        metadata = request.metadata or {}
        return {
            "current_identity": str(metadata.get("current_identity") or "").strip(),
            "target_direction": str(metadata.get("target_direction") or "").strip(),
            "current_stage": str(metadata.get("current_stage") or "").strip(),
            "expected_city": str(metadata.get("expected_city") or "").strip(),
            "expected_industry": str(metadata.get("expected_industry") or "").strip(),
            "expected_salary": str(metadata.get("expected_salary") or "").strip(),
            "available_time": str(metadata.get("available_time") or "").strip(),
            "confusion": str(metadata.get("confusion") or "").strip(),
            "personal_background": str(metadata.get("personal_background") or "").strip(),
        }

    def _missing_fields(self, form: dict[str, Any], resume_text: str) -> list[str]:
        missing: list[str] = []
        if not resume_text and not form.get("personal_background"):
            missing.append("简历或个人背景")
        if not form.get("current_identity"):
            missing.append("当前身份")
        if not form.get("target_direction"):
            missing.append("目标方向")
        if not form.get("current_stage"):
            missing.append("当前阶段")
        if not form.get("available_time"):
            missing.append("可投入学习时间")
        return missing

    def _normalize_report(
        self,
        *,
        payload: dict[str, Any],
        request: AgentRequest,
        form: dict[str, Any],
        resume_text: str,
        missing_fields: list[str],
        used_deepseek: bool,
        llm_errors: list[str],
    ) -> dict[str, Any]:
        history_id = str((request.metadata or {}).get("history_id") or uuid.uuid4())
        profile = payload.get("career_profile") if isinstance(payload.get("career_profile"), dict) else {}
        matching = payload.get("matching_analysis") if isinstance(payload.get("matching_analysis"), dict) else {}
        plan = payload.get("career_plan") if isinstance(payload.get("career_plan"), dict) else {}
        learning = payload.get("learning_path") if isinstance(payload.get("learning_path"), dict) else {}
        return {
            "agent": "career_planning_agent",
            "task_type": "career_planning",
            "success": True,
            "needs_more_info": bool(payload.get("needs_more_info")) or bool(missing_fields),
            "missing_fields": _list(payload.get("missing_fields")) or missing_fields,
            "career_profile": {
                "current_stage": str(profile.get("current_stage") or form.get("current_stage") or "待补充").strip(),
                "target_direction": str(profile.get("target_direction") or form.get("target_direction") or "待补充").strip(),
                "recommended_positions": _list(profile.get("recommended_positions"))[:8],
                "current_strengths": _list(profile.get("current_strengths"))[:8],
                "main_gaps": _list(profile.get("main_gaps"))[:8],
            },
            "matching_analysis": {
                "target_position": str(matching.get("target_position") or form.get("target_direction") or "目标岗位待补充").strip(),
                "match_score": _score(matching.get("match_score"), 65),
                "matched_skills": _list(matching.get("matched_skills"))[:12],
                "missing_skills": _list(matching.get("missing_skills"))[:12],
                "risk_points": _list(matching.get("risk_points"))[:8],
            },
            "career_plan": {
                "short_term": _list(plan.get("short_term"))[:8],
                "mid_term": _list(plan.get("mid_term"))[:8],
                "long_term": _list(plan.get("long_term"))[:8],
            },
            "learning_path": {
                "one_week": _list(learning.get("one_week"))[:8],
                "one_month": _list(learning.get("one_month"))[:8],
                "three_months": _list(learning.get("three_months"))[:8],
                "six_months": _list(learning.get("six_months"))[:8],
            },
            "project_suggestions": _list(payload.get("project_suggestions"))[:10],
            "job_search_strategy": _list(payload.get("job_search_strategy"))[:10],
            "next_actions": _list(payload.get("next_actions"))[:10],
            "metadata": {
                "history_id": history_id,
                "filename": request.filename or (request.metadata or {}).get("filename", ""),
                "parsed_char_count": len(resume_text),
                "used_deepseek": used_deepseek,
                "llm_errors": llm_errors,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "note": "" if resume_text else "未上传简历，当前规划主要基于用户输入背景生成；上传简历可获得更精准结果。",
            },
        }

    def _fallback_payload(self, form: dict[str, Any], resume_text: str, missing_fields: list[str]) -> dict[str, Any]:
        target = form.get("target_direction") or "目标方向待补充"
        return {
            "needs_more_info": bool(missing_fields),
            "missing_fields": missing_fields,
            "career_profile": {
                "current_stage": form.get("current_stage") or "待补充",
                "target_direction": target,
                "recommended_positions": [target],
                "current_strengths": ["具备进一步规划的基础信息"],
                "main_gaps": ["目标方向、项目经历或学习时间仍需补充"],
            },
            "matching_analysis": {
                "target_position": target,
                "match_score": 60,
                "matched_skills": [],
                "missing_skills": ["请补充目标岗位核心技能后进一步分析"],
                "risk_points": ["信息不足会影响规划精度"],
            },
            "career_plan": {
                "short_term": ["补齐目标岗位信息，整理简历项目和技能清单"],
                "mid_term": ["围绕目标方向完成一个可写入简历的项目"],
                "long_term": ["形成稳定投递方向，并根据面试反馈迭代能力栈"],
            },
            "learning_path": {
                "one_week": ["明确目标岗位 JD，列出高频技能关键词"],
                "one_month": ["补齐 2-3 个关键技术点并完成小项目"],
                "three_months": ["完成项目复盘、简历优化和模拟面试训练"],
                "six_months": ["形成投递节奏，持续复盘面试反馈"],
            },
            "project_suggestions": ["选择与目标岗位强相关的项目，突出技术难点、个人贡献和量化结果"],
            "job_search_strategy": ["优先投递与现有技能最接近的岗位，再尝试进阶方向"],
            "next_actions": ["补充简历或个人背景", "补充目标方向、城市、行业和可投入学习时间"],
        }

    def _fallback_rewrite(self, report: dict[str, Any], instruction: str) -> dict[str, Any]:
        updated = dict(report)
        next_actions = _list(updated.get("next_actions"))
        next_actions.insert(0, f"已记录新的规划要求：{instruction}")
        updated["next_actions"] = next_actions[:10]
        return updated

    def _save_history(self, report: dict[str, Any]) -> None:
        history_id = (report.get("metadata") or {}).get("history_id") or str(uuid.uuid4())
        (self.history_dir / f"{history_id}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


career_planning_service = CareerPlanningService()
