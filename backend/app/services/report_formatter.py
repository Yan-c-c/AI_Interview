from __future__ import annotations

from typing import Any


DIMENSION_DEFAULTS = {
    "basic_info": 0,
    "structure": 0,
    "content_quality": 0,
    "project_experience": 0,
    "skill_match": 0,
    "wording_risk": 0,
    "template_duplication": 0,
    "roundtable_quality": 0,
}


ROUNDTABLE_DEFAULTS = {
    "matching_analyst": {"role": "匹配分析师", "findings": [], "suggestions": []},
    "content_optimizer": {"role": "内容优化师", "findings": [], "suggestions": []},
    "hr_reviewer": {"role": "HR 审核官", "findings": [], "suggestions": []},
    "risk_template_reviewer": {"role": "风险与模板审查 Agent", "findings": [], "suggestions": []},
    "reflector": {"role": "质量审核节点", "final_judgement": "", "prioritized_actions": []},
}


def clamp_score(value: Any, default: int = 0) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return default


class ReportFormatter:
    def normalize_llm_report(
        self,
        *,
        report: dict[str, Any],
        tool_findings: dict[str, Any],
        expert_outputs: dict[str, Any],
        filename: str,
        parsed_char_count: int,
        llm_errors: list[str],
        resume_text: str = "",
    ) -> dict[str, Any]:
        normalized = dict(report or {})
        normalized["agent"] = "resume_evaluation_agent"
        normalized["task_type"] = "resume_evaluation"
        normalized["success"] = True

        summary = normalized.setdefault("summary", {})
        summary["overall_score"] = clamp_score(summary.get("overall_score"), 70)
        summary.setdefault("risk_level", "中")
        summary.setdefault("target_position", "未明确")
        summary.setdefault("target_position_source", "system_inferred")
        summary.setdefault("main_problems", [])
        summary.setdefault("main_suggestions", [])

        dimension_scores = dict(DIMENSION_DEFAULTS)
        dimension_scores.update(normalized.get("dimension_scores") or {})
        normalized["dimension_scores"] = {key: clamp_score(value, 70) for key, value in dimension_scores.items()}

        roundtable = dict(ROUNDTABLE_DEFAULTS)
        roundtable.update(normalized.get("roundtable") or {})
        for key, expert in expert_outputs.items():
            if key in roundtable and isinstance(expert, dict):
                roundtable[key] = {
                    "role": roundtable[key].get("role") or expert.get("role"),
                    "findings": expert.get("findings", roundtable[key].get("findings", [])),
                    "suggestions": expert.get("suggestions", roundtable[key].get("suggestions", [])),
                }
        normalized["roundtable"] = roundtable

        normalized.setdefault("tool_findings", tool_findings)
        normalized.setdefault("forbidden_words", [])
        normalized.setdefault(
            "template_duplication",
            {"risk_level": "中", "score": 70, "reasons": [], "ai_judgement": "", "suggestions": []},
        )
        normalized.setdefault("problems", [])
        normalized.setdefault("optimization_suggestions", [])
        normalized.setdefault(
            "resume_comparison",
            {
                "original_resume": "",
                "optimized_resume": "",
                "changes": [],
            },
        )
        resume_comparison = normalized["resume_comparison"]
        if isinstance(resume_comparison, dict):
            if not resume_comparison.get("original_resume"):
                resume_comparison["original_resume"] = resume_text
            resume_comparison.setdefault("optimized_resume", "")
            resume_comparison.setdefault("changes", [])
        normalized["metadata"] = {
            "filename": filename,
            "parsed_char_count": parsed_char_count,
            "used_llm_roundtable": True,
            "used_tool_clues": True,
            "used_forbidden_word_tool": True,
            "used_template_duplication_tool": True,
            "llm_errors": llm_errors,
        }
        return normalized


report_formatter = ReportFormatter()
