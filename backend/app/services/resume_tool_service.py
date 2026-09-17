from __future__ import annotations

import re
from typing import Any

from app.services.forbidden_words_service import ForbiddenWordsCheckTool
from app.services.template_duplication_service import TemplateSimilarityCheckTool


class BasicInfoCheckTool:
    name = "BasicInfoCheckTool"

    fields = {
        "name": ["姓名", "Name"],
        "phone": ["电话", "手机", "联系方式", "Tel"],
        "email": ["邮箱", "Email"],
        "target_position": ["求职意向", "目标岗位", "应聘岗位", "岗位"],
        "education": ["教育背景", "学历", "本科", "硕士", "博士", "大专"],
        "major": ["专业"],
        "skills": ["专业技能", "技能栈", "技能", "技术栈"],
        "projects": ["项目经历", "项目经验", "项目"],
        "work_or_internship": ["工作经历", "实习经历", "实习", "工作经验"],
        "honors": ["荣誉奖项", "证书", "奖项", "竞赛", "资格证"],
    }

    def run(self, resume_text: str) -> list[dict[str, Any]]:
        findings = []
        for key, keywords in self.fields.items():
            present = any(word.lower() in resume_text.lower() for word in keywords)
            if key == "name":
                first_lines = [line.strip() for line in resume_text.splitlines()[:5] if line.strip()]
                present = present or any(bool(re.fullmatch(r"[\u4e00-\u9fa5]{2,4}", line)) for line in first_lines)
            if key == "phone":
                present = present or bool(re.search(r"(?<!\d)(1[3-9]\d{9})(?!\d)", resume_text))
            if key == "email":
                present = present or bool(re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", resume_text))
            findings.append(
                {
                    "field": key,
                    "present": present,
                    "clue": "可能存在" if present else "未发现明显线索",
                    "tool_note": "基础信息工具只检查显性文本线索，最终完整性判断由 Agent 完成。",
                }
            )
        return findings


class StructureAnalysisTool:
    name = "StructureAnalysisTool"

    expected_order = ["基本信息", "求职意向", "教育背景", "专业技能", "项目经历", "实习经历", "工作经历", "荣誉奖项"]

    def run(self, resume_text: str) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
        text = "\n".join(lines)

        located = []
        for title in self.expected_order:
            idx = text.find(title)
            if idx >= 0:
                located.append({"title": title, "position": idx})

        missing_sections = [title for title in self.expected_order if title not in [item["title"] for item in located]]
        if missing_sections:
            findings.append({"type": "missing_section_clue", "items": missing_sections, "severity_hint": "medium"})

        ordered_titles = [item["title"] for item in sorted(located, key=lambda item: item["position"])]
        if ordered_titles and ordered_titles != [title for title in self.expected_order if title in ordered_titles]:
            findings.append({"type": "section_order_clue", "items": ordered_titles, "severity_hint": "low"})

        long_lines = [line for line in lines if len(line) > 120]
        if long_lines:
            findings.append(
                {
                    "type": "dense_content_clue",
                    "items": long_lines[:8],
                    "severity_hint": "medium",
                    "tool_note": "长段落可能影响可读性，但需由 Agent 判断是否为内容堆砌。",
                }
            )

        bullet_count = len([line for line in lines if line.startswith(("-", "•", "*", "·"))])
        if bullet_count < 4 and len(lines) > 20:
            findings.append({"type": "low_bullet_clue", "items": [f"条目化表达数量较少: {bullet_count}"], "severity_hint": "low"})

        if not findings:
            findings.append({"type": "structure_clue", "items": ["未发现明显结构异常线索"], "severity_hint": "low"})
        return findings


class ResumeToolService:
    """Runs local clue extraction tools for the LLM roundtable."""

    def __init__(self) -> None:
        self.basic_info_tool = BasicInfoCheckTool()
        self.structure_tool = StructureAnalysisTool()
        self.forbidden_words_tool = ForbiddenWordsCheckTool()
        self.template_tool = TemplateSimilarityCheckTool()

    def run_all(self, resume_text: str) -> dict[str, Any]:
        return {
            "basic_info_clues": self.basic_info_tool.run(resume_text),
            "structure_clues": self.structure_tool.run(resume_text),
            "forbidden_word_clues": self.forbidden_words_tool.run(resume_text),
            "template_duplication_clues": self.template_tool.run(resume_text),
        }


resume_tool_service = ResumeToolService()
