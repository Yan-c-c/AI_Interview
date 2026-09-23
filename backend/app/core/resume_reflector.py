from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core import llms
from app.core.json_utils import loads_json_response


class ResumeReflectorAgent:
    role = "质量审核节点"

    async def reflect(
        self,
        *,
        resume_text: str,
        user_message: str,
        target_position: str,
        target_position_source: str,
        tool_findings: dict[str, Any],
        expert_outputs: dict[str, Any],
        filename: str,
        api_config: dict[str, Any] | None,
    ) -> dict[str, Any]:
        llm = llms.get_llm_for_request(api_config, channel="reflector", temperature=0.1, max_tokens=10000)
        prompt = f"""你是智能面试助手的 Reflector / 质量审核 Agent。请对四位专家意见进行去重、反思和整合，生成最终结构化简历评估报告。

重要约束：
1. 最终结论、评分、风险等级和建议必须由你综合判断生成。
2. 本地工具线索只能作为证据线索，不得机械当成最终结论。
3. 对违禁词和模板化表达必须结合上下文给出 AI 判断。
4. 不要编造简历没有的经历、学历、公司或项目成果。
5. 输出必须是完整 JSON object，不要 markdown，不要解释。

【文件名】{filename}
【用户消息】{user_message}
【目标岗位】{target_position}
【目标岗位来源】{target_position_source}

【简历原文】
{resume_text[:18000]}

【本地工具线索】
{json.dumps(tool_findings, ensure_ascii=False, indent=2)[:12000]}

【多专家圆桌意见】
{json.dumps(expert_outputs, ensure_ascii=False, indent=2)[:18000]}

请严格输出以下结构，数组可为空但字段必须存在：
{{
  "agent": "resume_evaluation_agent",
  "task_type": "resume_evaluation",
  "success": true,
  "summary": {{
    "overall_score": 82,
    "risk_level": "低 | 中 | 高",
    "target_position": "{target_position}",
    "target_position_source": "resume_explicit | system_inferred",
    "main_problems": [],
    "main_suggestions": []
  }},
  "dimension_scores": {{
    "basic_info": 0,
    "structure": 0,
    "content_quality": 0,
    "project_experience": 0,
    "skill_match": 0,
    "wording_risk": 0,
    "template_duplication": 0,
    "roundtable_quality": 0
  }},
  "roundtable": {{
    "matching_analyst": {{"role": "匹配分析师", "findings": [], "suggestions": []}},
    "content_optimizer": {{"role": "内容优化师", "findings": [], "suggestions": []}},
    "hr_reviewer": {{"role": "HR 审核官", "findings": [], "suggestions": []}},
    "risk_template_reviewer": {{"role": "风险与模板审查 Agent", "findings": [], "suggestions": []}},
    "reflector": {{"role": "质量审核节点", "final_judgement": "", "prioritized_actions": []}}
  }},
  "forbidden_words": [
    {{
      "word": "",
      "risk_type": "",
      "context": "",
      "ai_judgement": "",
      "suggestion": ""
    }}
  ],
  "template_duplication": {{
    "risk_level": "低 | 中 | 高",
    "score": 0,
    "reasons": [],
    "ai_judgement": "",
    "suggestions": []
  }},
  "problems": [
    {{
      "dimension": "",
      "problem": "",
      "evidence": "",
      "suggestion": "",
      "priority": "high | medium | low"
    }}
  ],
  "optimization_suggestions": [
    {{
      "priority": "high | medium | low",
      "suggestion": "",
      "example": ""
    }}
  ],
  "resume_comparison": {{
    "original_resume": "保留简历原文，可做必要截断但不要改写",
    "optimized_resume": "基于专家建议生成一版可采纳的优化后简历 Markdown，不能编造事实",
    "changes": [
      {{
        "id": "change-1",
        "section": "项目经历",
        "original_text": "原文片段",
        "optimized_text": "优化后片段",
        "reason": "优化原因",
        "risk_note": "真实性或面试追问风险提示",
        "priority": "high | medium | low"
      }}
    ]
  }}
}}
"""
        response = await llm.ainvoke([SystemMessage(content="你只输出可解析 JSON。"), HumanMessage(content=prompt)])
        parsed = loads_json_response(response.content)
        if not isinstance(parsed, dict):
            raise ValueError("Reflector 输出不是 JSON object")
        return parsed
