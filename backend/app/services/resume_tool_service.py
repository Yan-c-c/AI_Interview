from __future__ import annotations

import re
from typing import Any



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






