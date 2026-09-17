from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any


COMMON_TEMPLATE_PHRASES = [
    "本人性格开朗",
    "吃苦耐劳",
    "认真负责",
    "具有良好的沟通能力",
    "具有较强的学习能力",
    "能够快速适应环境",
    "具备团队合作精神",
    "熟悉各种办公软件",
    "负责相关模块开发",
    "参与多个项目开发",
    "完成领导交代的其他任务",
    "有较强的抗压能力",
    "工作积极主动",
    "对互联网行业充满热情",
    "熟练掌握相关技术",
]

COMMON_SECTION_TITLES = [
    "基本信息",
    "教育背景",
    "专业技能",
    "项目经历",
    "工作经历",
    "实习经历",
    "校园经历",
    "自我评价",
    "荣誉奖项",
    "证书",
]


class TemplateSimilarityCheckTool:
    name = "TemplateSimilarityCheckTool"

    def run(self, resume_text: str) -> dict[str, Any]:
        text = re.sub(r"\s+", " ", resume_text)
        lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
        phrase_hits = []

        for phrase in COMMON_TEMPLATE_PHRASES:
            if phrase in text:
                phrase_hits.append(
                    {
                        "phrase": phrase,
                        "context": self._context(text, phrase),
                        "tool_note": "模板句式命中仅作为线索，需由 Agent 判断是否真的低区分度。",
                    }
                )

        title_hits = []
        for line in lines[:120]:
            normalized = re.sub(r"[:：#\-\s]", "", line)
            for title in COMMON_SECTION_TITLES:
                ratio = SequenceMatcher(None, normalized, title).ratio()
                if ratio >= 0.75:
                    title_hits.append({"title": line, "matched_template_title": title, "similarity": round(ratio, 2)})
                    break

        self_eval_lines = [line for line in lines if any(p in line for p in ["本人", "性格", "沟通", "学习能力", "团队"])]
        project_generic_lines = [
            line
            for line in lines
            if any(p in line for p in ["负责", "参与", "完成", "实现"])
            and not re.search(r"\d+|%|ms|QPS|万|千|用户|接口|模块|性能", line, flags=re.I)
        ]

        token_count = max(1, len(text))
        phrase_chars = sum(len(hit["phrase"]) for hit in phrase_hits)
        generic_ratio = min(1.0, (phrase_chars + sum(len(line) for line in project_generic_lines[:20])) / token_count)
        score = max(0, min(100, round(100 - generic_ratio * 100)))

        if score < 60:
            risk_level = "高"
        elif score < 78:
            risk_level = "中"
        else:
            risk_level = "低"

        return {
            "template_phrase_hits": phrase_hits[:60],
            "section_title_similarity": title_hits[:30],
            "self_evaluation_template_clues": self_eval_lines[:20],
            "project_description_generic_clues": project_generic_lines[:30],
            "common_phrase_ratio": round(generic_ratio, 3),
            "tool_score": score,
            "tool_risk_level": risk_level,
            "tool_note": "该分数是本地模板化线索分，不是最终模板查重结论。",
        }

    def _context(self, text: str, phrase: str) -> str:
        idx = text.find(phrase)
        if idx == -1:
            return phrase
        return text[max(0, idx - 30) : min(len(text), idx + len(phrase) + 45)].strip()
