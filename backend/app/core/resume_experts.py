from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core import llms
from app.core.json_utils import loads_json_response

logger = logging.getLogger(__name__)


@dataclass
class ResumeExpertAgent:
    key: str
    role: str
    system_prompt: str
    task_prompt: str
    channel: str

    async def analyze(
        self,
        *,
        resume_text: str,
        user_message: str,
        target_position: str,
        target_position_source: str,
        tool_findings: dict[str, Any],
        api_config: dict[str, Any] | None,
    ) -> dict[str, Any]:
        llm = llms.get_llm_for_request(api_config, channel=self.channel)
        prompt = self.task_prompt.format(
            resume_text=resume_text[:18000],
            user_message=user_message or "",
            target_position=target_position or "未明确",
            target_position_source=target_position_source,
            tool_findings=json.dumps(tool_findings, ensure_ascii=False, indent=2)[:12000],
        )
        response = await llm.ainvoke([SystemMessage(content=self.system_prompt), HumanMessage(content=prompt)])
        parsed = loads_json_response(response.content)
        if not isinstance(parsed, dict):
            raise ValueError(f"{self.role} 输出不是 JSON object")
        parsed.setdefault("role", self.role)
        parsed.setdefault("findings", [])
        parsed.setdefault("suggestions", [])
        return parsed


MATCHING_ANALYST = ResumeExpertAgent(
    key="matching_analyst",
    role="匹配分析师",
    channel="matching_analyst",
    system_prompt="你是智能面试助手中的简历匹配分析师。你只基于简历原文、用户需求和工具线索判断，不编造经历。",
    task_prompt="""请分析候选人简历与目标岗位的匹配度。

【用户消息】
{user_message}

【目标岗位】{target_position}
【目标岗位来源】{target_position_source}

【简历原文】
{resume_text}

【本地工具线索】
{tool_findings}

请重点判断：
1. 技能、项目、经历是否支撑求职方向。
2. 如果目标岗位是系统推测，请说明推测依据和不确定性。
3. 哪些技能或经历是强匹配、弱匹配、缺失项。
4. 给出可执行的补强建议。

只输出 JSON，不要 markdown：
{{
  "role": "匹配分析师",
  "target_position": "",
  "target_position_source": "resume_explicit | system_inferred",
  "match_score": 0,
  "findings": ["发现1"],
  "skill_match": {{"strong": [], "weak": [], "missing": []}},
  "evidence": ["证据1"],
  "suggestions": ["建议1"]
}}
""",
)


CONTENT_OPTIMIZER = ResumeExpertAgent(
    key="content_optimizer",
    role="内容优化师",
    channel="content_optimizer",
    system_prompt="你是简历内容优化师，擅长判断表达是否具体、量化、有逻辑，并给出保守真实的改写示例。",
    task_prompt="""请从内容质量角度诊断这份简历。

【用户消息】
{user_message}

【目标岗位】{target_position}
【简历原文】
{resume_text}

【本地工具线索】
{tool_findings}

请重点检查：
1. 是否有量化成果。
2. 是否体现个人贡献、技术难点、解决方案和项目结果。
3. 是否存在空泛描述、内容堆砌或逻辑断裂。
4. 项目经历是否适合作为面试重点项目。

只输出 JSON，不要 markdown：
{{
  "role": "内容优化师",
  "content_quality_score": 0,
  "project_experience_score": 0,
  "findings": ["发现1"],
  "project_findings": ["项目经历问题1"],
  "rewrite_examples": [{{"before": "原表达", "after": "优化示例", "reason": "原因"}}],
  "suggestions": ["建议1"]
}}
""",
)


HR_REVIEWER = ResumeExpertAgent(
    key="hr_reviewer",
    role="HR 审核官",
    channel="hr_reviewer",
    system_prompt="你是资深 HR 审核官，从初筛、可信度、亮点、质疑点和通过率角度评估简历。",
    task_prompt="""请从 HR 初筛角度审查这份简历。

【用户消息】
{user_message}

【目标岗位】{target_position}
【简历原文】
{resume_text}

【本地工具线索】
{tool_findings}

请判断：
1. 基础信息和结构是否支持快速筛选。
2. 哪些亮点会提高通过率。
3. 哪些表达会引发可信度质疑。
4. 是否存在低区分度、泛泛而谈或不匹配岗位的内容。

只输出 JSON，不要 markdown：
{{
  "role": "HR 审核官",
  "first_screen_pass_rate": 0,
  "credibility_score": 0,
  "findings": ["发现1"],
  "highlights": ["亮点1"],
  "concerns": ["疑虑1"],
  "suggestions": ["建议1"]
}}
""",
)


RISK_TEMPLATE_REVIEWER = ResumeExpertAgent(
    key="risk_template_reviewer",
    role="风险与模板审查 Agent",
    channel="risk_template_reviewer",
    system_prompt="你是风险与模板审查 Agent。工具命中不是结论，你必须结合上下文判断风险、模板化程度和具体改写方向。",
    task_prompt="""请结合本地工具线索和简历上下文，审查违禁词、风险词和模板化表达。

【用户消息】
{user_message}

【目标岗位】{target_position}
【简历原文】
{resume_text}

【本地工具线索】
{tool_findings}

要求：
1. 对每个风险词判断其在当前上下文是否真的夸大、空泛或易被质疑。
2. 模板化检测不能只复述占比，要说明哪些表达低区分度、为什么低区分度。
3. 给出贴合简历内容的个性化改写建议。

只输出 JSON，不要 markdown：
{{
  "role": "风险与模板审查 Agent",
  "wording_risk_score": 0,
  "template_duplication_score": 0,
  "findings": ["发现1"],
  "forbidden_words": [
    {{
      "word": "精通",
      "risk_type": "过度绝对化",
      "context": "上下文",
      "ai_judgement": "AI判断",
      "suggestion": "修改建议"
    }}
  ],
  "template_duplication": {{
    "risk_level": "低 | 中 | 高",
    "score": 0,
    "reasons": [],
    "ai_judgement": "",
    "suggestions": []
  }},
  "suggestions": ["建议1"]
}}
""",
)


EXPERTS = [MATCHING_ANALYST, CONTENT_OPTIMIZER, HR_REVIEWER, RISK_TEMPLATE_REVIEWER]
