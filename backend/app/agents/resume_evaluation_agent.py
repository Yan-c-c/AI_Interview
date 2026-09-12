from __future__ import annotations

import logging
import re
from collections.abc import AsyncGenerator
from typing import Any

from app.agents.base_agent import BaseAgent
from app.schemas.agent_schema import AgentRequest, AgentResponse

logger = logging.getLogger(__name__)


class ResumeEvaluationAgent(BaseAgent):
    name = "resume_evaluation_agent"
    task_type = "resume_evaluation"



    def _infer_target_position(self, message: str, resume_text: str) -> tuple[str, str]:
        message_patterns = [
            r"看看我的简历能不能投\s*([^\n，,。；;]{2,30})",
            r"(?:想投|投递|应聘|求职)\s*([^\n，,。；;]{2,30})",
        ]
        resume_patterns = [
            r"(?:求职意向|目标岗位|应聘岗位|求职岗位|应聘职位|目标职位|求职方向|就业方向)\s*[:：]\s*([^\n，,。；;]{2,30})",
        ]
        for source_text, patterns in ((message, message_patterns), (resume_text[:1600], resume_patterns)):
            for pattern in patterns:
                match = re.search(pattern, source_text)
                if match:
                    position = self._clean_position(match.group(1))
                    if position and self._looks_like_position(position):
                        return position, "resume_explicit" if source_text != message else "resume_explicit"

        inferred = self._infer_by_skills(resume_text)
        return inferred, "system_inferred"

    def _clean_position(self, value: str) -> str:
        value = re.split(r"[，,。；;\n]", value.strip())[0]
        value = re.sub(r"^(求职意向|目标岗位|应聘岗位|求职岗位|应聘职位|目标职位|求职方向|就业方向)\s*[:：]?\s*", "", value).strip()
        value = re.sub(r"(帮我|看看|评估|简历|有没有|问题|风险).*", "", value).strip()
        return value[:30]

    def _looks_like_position(self, value: str) -> bool:
        if not value or len(value) < 2:
            return False
        invalid_fragments = [
            "综测",
            "排名",
            "成绩",
            "绩点",
            "专业前",
            "平均",
            "学院",
            "专业：",
            "出生",
            "邮箱",
            "手机",
            "电话",
            "籍贯",
            "政治面貌",
        ]
        if any(fragment in value for fragment in invalid_fragments):
            return False
        return True

    def _infer_by_skills(self, resume_text: str) -> str:
        text = resume_text.lower()
        candidates: list[tuple[str, int, list[str]]] = [
            ("Java 后端开发", 0, ["java", "spring", "spring boot", "mybatis", "mysql", "redis"]),
            ("前端开发", 0, ["react", "vue", "typescript", "javascript", "css", "next.js"]),
            ("Python 后端开发", 0, ["python", "django", "fastapi", "flask", "pytorch"]),
            ("数据分析", 0, ["sql", "tableau", "powerbi", "数据分析", "可视化"]),
            ("算法工程师", 0, ["机器学习", "深度学习", "transformer", "pytorch", "tensorflow"]),
            ("产品经理", 0, ["需求分析", "原型", "prd", "用户调研", "产品"]),
        ]
        scored = []
        for name, _score, keywords in candidates:
            scored.append((name, sum(1 for keyword in keywords if keyword in text)))
        best = max(scored, key=lambda item: item[1])
        return best[0] if best[1] >= 2 else "未明确"

