from __future__ import annotations

import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base_agent import BaseAgent
from app.core.json_utils import loads_json_response
from app.core.llms import get_llm_for_request
from app.schemas.agent_schema import AgentRequest, AgentResponse
from app.services.knowledge_base import LightRAGQueryResult, knowledge_base_service

logger = logging.getLogger(__name__)


QUESTION_CATEGORIES = [
    ("project_deep_dive", "项目深挖题"),
    ("technical_basics", "技术基础题"),
    ("technical_advanced", "技术进阶题"),
    ("scenario_design", "场景设计题"),
    ("follow_up", "追问题"),
]


class InterviewQuestionGenerationAgent(BaseAgent):
    name = "interview_question_generation_agent"
    task_type = "interview_question_generation"


    async def _extract_resume_profile(self, request: AgentRequest, resume_text: str) -> dict[str, Any]:
        llm = get_llm_for_request(request.api_config, channel="smart", temperature=0.15, max_tokens=2400)
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content=(
                        "你是简历画像抽取 Agent。只根据用户消息和简历原文抽取结构化画像，"
                        "不要编造简历中没有的经历。输出严格 JSON，不要 markdown。"
                    )
                ),
                HumanMessage(
                    content=f"""用户需求：
{request.message}

简历原文：
{resume_text[:12000]}

请输出 JSON：
{{
  "target_position": "岗位名称或未明确",
  "target_position_source": "resume_explicit | user_message | system_inferred | unknown",
  "skills": ["技能词"],
  "projects": [
    {{"name": "项目名", "description": "一句话摘要", "tech_stack": ["技术"], "keywords": ["关键词"]}}
  ],
  "internships": [
    {{"company": "公司或组织", "role": "角色", "keywords": ["关键词"]}}
  ],
  "education": "教育背景摘要",
  "keywords": ["用于检索题库的关键词"]
}}"""
                ),
            ]
        )
        data = loads_json_response(str(response.content or ""))
        if not isinstance(data, dict):
            raise ValueError("profile response is not object")
        return self._sanitize_profile(data)

    def _sanitize_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        target = str(profile.get("target_position") or "未明确").strip()[:40] or "未明确"
        source = str(profile.get("target_position_source") or "unknown")
        if source not in {"resume_explicit", "user_message", "system_inferred", "unknown"}:
            source = "unknown"
        return {
            "target_position": target,
            "target_position_source": source,
            "skills": self._string_list(profile.get("skills"))[:16],
            "projects": self._project_list(profile.get("projects"))[:6],
            "internships": self._internship_list(profile.get("internships"))[:5],
            "education": str(profile.get("education") or "").strip()[:300],
            "keywords": self._string_list(profile.get("keywords"))[:20],
        }

    def _fallback_profile(self, message: str, resume_text: str) -> dict[str, Any]:
        skills = self._extract_known_skills(resume_text)
        target = self._infer_target_position(message, resume_text, skills)
        projects = self._extract_projects(resume_text)
        return {
            "target_position": target[0],
            "target_position_source": target[1],
            "skills": skills[:16],
            "projects": projects[:5],
            "internships": [],
            "education": self._extract_education(resume_text),
            "keywords": list(dict.fromkeys([target[0], *skills, *[p["name"] for p in projects if p.get("name")]]))[:18],
        }

    def _build_retrieval_queries(self, profile: dict[str, Any], user_message: str) -> list[str]:
        target = profile.get("target_position") or "技术岗位"
        if target == "未明确":
            target = "技术岗位"
        skills = self._string_list(profile.get("skills"))[:8]
        project_keywords: list[str] = []
        for project in profile.get("projects") or []:
            if isinstance(project, dict):
                project_keywords.extend(self._string_list(project.get("keywords"))[:4])
                if project.get("name"):
                    project_keywords.append(str(project["name"]))
        keywords = list(dict.fromkeys([*skills, *project_keywords, *self._string_list(profile.get("keywords"))]))[:12]
        compact = " ".join([target, *keywords[:8], "面试"])
        queries = [
            compact,
            " ".join([target, *skills[:5], "技术基础 面试题"]),
            " ".join([target, *project_keywords[:5], "项目深挖 面试"]),
            " ".join([target, *skills[:4], "场景设计 系统设计 面试"]),
        ]
        if user_message:
            queries.append(f"{target} {user_message[:40]} 面试题")
        return [query.strip() for query in dict.fromkeys(queries) if len(query.strip()) >= 3][:4]

    async def _retrieve(self, queries: list[str]) -> list[LightRAGQueryResult]:
        if not queries:
            return []
        return await knowledge_base_service.retrieve_many(queries)










    def _string_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _project_list(self, value: Any) -> list[dict[str, Any]]:
        projects: list[dict[str, Any]] = []
        if not isinstance(value, list):
            return projects
        for item in value:
            if isinstance(item, dict):
                projects.append(
                    {
                        "name": str(item.get("name") or "未命名项目")[:80],
                        "description": str(item.get("description") or "")[:300],
                        "tech_stack": self._string_list(item.get("tech_stack"))[:10],
                        "keywords": self._string_list(item.get("keywords"))[:10],
                    }
                )
        return projects

    def _internship_list(self, value: Any) -> list[dict[str, Any]]:
        internships: list[dict[str, Any]] = []
        if not isinstance(value, list):
            return internships
        for item in value:
            if isinstance(item, dict):
                internships.append(
                    {
                        "company": str(item.get("company") or "")[:80],
                        "role": str(item.get("role") or "")[:80],
                        "keywords": self._string_list(item.get("keywords"))[:10],
                    }
                )
        return internships

    def _extract_known_skills(self, text: str) -> list[str]:
        candidates = [
            "Java", "Spring Boot", "Spring Cloud", "MyBatis", "MySQL", "Redis", "Kafka", "RabbitMQ",
            "Python", "FastAPI", "Django", "Flask", "PyTorch", "TensorFlow", "React", "Vue",
            "TypeScript", "JavaScript", "Node.js", "Docker", "Kubernetes", "Linux", "Nginx",
            "Elasticsearch", "MongoDB", "PostgreSQL", "Git", "机器学习", "深度学习", "大模型",
        ]
        lower = text.lower()
        found = [skill for skill in candidates if skill.lower() in lower or skill in text]
        return list(dict.fromkeys(found))

    def _infer_target_position(self, message: str, resume_text: str, skills: list[str]) -> tuple[str, str]:
        for text, source in ((message, "user_message"), (resume_text[:1800], "resume_explicit")):
            match = re.search(r"(?:求职意向|目标岗位|应聘岗位|求职岗位|应聘职位|目标职位|根据简历生成)\s*[:：]?\s*([^\n，,。；;]{2,30})", text)
            if match:
                value = match.group(1).strip()
                if "面试" not in value and "问题" not in value:
                    return value, source
        skill_text = " ".join(skills).lower()
        if any(token in skill_text for token in ["java", "spring", "mybatis"]):
            return "Java 后端开发", "system_inferred"
        if any(token in skill_text for token in ["react", "vue", "typescript", "javascript"]):
            return "前端开发", "system_inferred"
        if any(token in skill_text for token in ["pytorch", "tensorflow", "机器学习", "深度学习", "大模型"]):
            return "算法工程师", "system_inferred"
        if "python" in skill_text:
            return "Python 后端开发", "system_inferred"
        return "未明确", "unknown"

    def _extract_projects(self, resume_text: str) -> list[dict[str, Any]]:
        projects: list[dict[str, Any]] = []
        for line in resume_text.splitlines():
            stripped = line.strip()
            if not stripped or len(stripped) > 80:
                continue
            if "项目" in stripped and not stripped.startswith("#"):
                name = re.sub(r"^[#\-\s·•]+", "", stripped)
                projects.append({"name": name, "description": "", "tech_stack": [], "keywords": [name]})
        return projects[:5]

    def _extract_education(self, resume_text: str) -> str:
        match = re.search(r"(教育背景|教育经历|学历|本科|硕士|博士)[\s\S]{0,240}", resume_text)
        return match.group(0).strip()[:240] if match else ""

