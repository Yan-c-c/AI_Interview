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

    async def run(self, request: AgentRequest) -> AgentResponse:
        resume_text = (request.resume_text or "").strip()
        if not resume_text:
            return AgentResponse(
                success=False,
                agent=self.name,
                task_type=self.task_type,
                message="未检测到可生成面试题的简历文本，请先上传简历。",
                result={
                    "success": False,
                    "agent": self.name,
                    "task_type": self.task_type,
                    "error": "empty_resume_text",
                },
            )

        errors: list[str] = []
        used_llm_profile = True
        used_llm_generation = True

        try:
            profile = await self._extract_resume_profile(request, resume_text)
        except Exception as exc:
            logger.warning("LLM resume profile extraction failed: %s", exc)
            errors.append(f"profile_llm_failed: {exc}")
            used_llm_profile = False
            profile = self._fallback_profile(request.message, resume_text)

        retrieval_queries = self._build_retrieval_queries(profile, request.message)
        profile["retrieval_queries"] = retrieval_queries
        retrieval_results = await self._retrieve(retrieval_queries)
        has_lightrag_hit = any(result.has_content for result in retrieval_results)

        try:
            report = await self._generate_question_report(
                request=request,
                resume_text=resume_text,
                profile=profile,
                retrieval_results=retrieval_results,
                has_lightrag_hit=has_lightrag_hit,
            )
        except Exception as exc:
            logger.warning("LLM interview question generation failed: %s", exc)
            errors.append(f"question_llm_failed: {exc}")
            used_llm_generation = False
            report = self._fallback_question_report(
                resume_text=resume_text,
                profile=profile,
                retrieval_results=retrieval_results,
                has_lightrag_hit=has_lightrag_hit,
            )

        normalized = self._normalize_report(
            report=report,
            request=request,
            profile=profile,
            retrieval_results=retrieval_results,
            has_lightrag_hit=has_lightrag_hit,
            used_llm_profile=used_llm_profile,
            used_llm_generation=used_llm_generation,
            errors=errors,
            parsed_char_count=len(resume_text),
        )
        return AgentResponse(
            success=True,
            agent=self.name,
            task_type=self.task_type,
            message="个性化面试练习题已生成。",
            result=normalized,
        )

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

    async def _generate_question_report(
        self,
        *,
        request: AgentRequest,
        resume_text: str,
        profile: dict[str, Any],
        retrieval_results: list[LightRAGQueryResult],
        has_lightrag_hit: bool,
    ) -> dict[str, Any]:
        llm = get_llm_for_request(request.api_config, channel="smart", temperature=0.25, max_tokens=5200)
        retrieval_context = self._format_retrieval_context(retrieval_results)
        source_rule = (
            "面试知识库已检索到题库/面试宝典内容。只有题目明显由检索内容支撑时，source_type 才能写 lightrag，并填写 source_refs。"
            if has_lightrag_hit
            else "面试知识库没有检索到可用内容。所有题目的 source_type 必须写 system_generated，source_refs 必须为空数组，不要伪造题库来源。"
        )
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content=(
                        "你是面试题生成 Agent。你要结合学生简历画像、简历原文和面试知识库检索结果，"
                        "生成个性化面试练习题。题目必须贴合简历项目和技能，避免泛泛而谈。"
                    )
                ),
                HumanMessage(
                    content=f"""生成要求：
1. 生成 15 道题，覆盖项目深挖题、技术基础题、技术进阶题、场景设计题、追问题。
2. 每题给出为什么问、回答要点、可能追问、关联简历证据。
3. {source_rule}
4. 难度使用 easy / medium / hard。
5. 输出严格 JSON，不要 markdown，不要额外解释。

用户需求：
{request.message}

简历画像：
{profile}

面试知识库检索结果：
{retrieval_context}

简历原文：
{resume_text[:12000]}

输出 JSON：
{{
  "summary": {{
    "target_position": "",
    "target_position_source": "",
    "question_count": 15,
    "difficulty_mix": {{"easy": 0, "medium": 0, "hard": 0}},
    "source_note": ""
  }},
  "question_sets": {{
    "project_deep_dive": [],
    "technical_basics": [],
    "technical_advanced": [],
    "scenario_design": [],
    "follow_up": []
  }},
  "practice_plan": ["练习建议1", "练习建议2", "练习建议3"]
}}

每个 question_sets 数组元素结构：
{{
  "id": "Q1",
  "category": "项目深挖题",
  "difficulty": "medium",
  "question": "问题内容",
  "why_ask": "面试官为什么问",
  "answer_points": ["回答要点"],
  "follow_ups": ["可能追问"],
  "source_type": "lightrag | system_generated",
  "source_refs": ["引用文件或 reference_id"],
  "related_resume_evidence": "简历中的依据"
}}"""
                ),
            ]
        )
        data = loads_json_response(str(response.content or ""))
        if not isinstance(data, dict):
            raise ValueError("question response is not object")
        return data

    def _normalize_report(
        self,
        *,
        report: dict[str, Any],
        request: AgentRequest,
        profile: dict[str, Any],
        retrieval_results: list[LightRAGQueryResult],
        has_lightrag_hit: bool,
        used_llm_profile: bool,
        used_llm_generation: bool,
        errors: list[str],
        parsed_char_count: int,
    ) -> dict[str, Any]:
        question_sets = self._normalize_question_sets(report.get("question_sets"), has_lightrag_hit)
        questions = [question for key, _label in QUESTION_CATEGORIES for question in question_sets[key]]
        difficulty_mix = {"easy": 0, "medium": 0, "hard": 0}
        for question in questions:
            difficulty = question.get("difficulty") if question.get("difficulty") in difficulty_mix else "medium"
            question["difficulty"] = difficulty
            difficulty_mix[difficulty] += 1

        retrieval_status = self._retrieval_status(retrieval_results, has_lightrag_hit)
        sources = self._source_list(retrieval_results)
        source_note = (
            "题目已结合面试知识库检索到的真实题库/面试宝典内容；部分个性化题目由系统基于简历生成。"
            if has_lightrag_hit
            else "面试知识库未返回可用题库内容，本次题目基于简历由系统生成，未标记为真实题库来源。"
        )
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        normalized_source_note = str(summary.get("source_note") or source_note).replace("LightRAG", "面试知识库")
        return {
            "agent": self.name,
            "task_type": self.task_type,
            "success": True,
            "summary": {
                "target_position": summary.get("target_position") or profile.get("target_position") or "未明确",
                "target_position_source": summary.get("target_position_source") or profile.get("target_position_source") or "unknown",
                "question_count": len(questions),
                "difficulty_mix": difficulty_mix,
                "used_lightrag": has_lightrag_hit,
                "source_note": normalized_source_note,
            },
            "resume_profile": profile,
            "retrieval": {
                "used_lightrag": has_lightrag_hit,
                "status": retrieval_status,
                "queries": [result.query for result in retrieval_results],
                "sources": sources,
                "errors": [result.error for result in retrieval_results if result.error],
            },
            "question_sets": question_sets,
            "questions": questions,
            "practice_plan": self._string_list(report.get("practice_plan"))[:6] or self._default_practice_plan(),
            "metadata": {
                "filename": request.filename or request.metadata.get("filename", ""),
                "parsed_char_count": parsed_char_count,
                "used_llm_profile": used_llm_profile,
                "used_llm_generation": used_llm_generation,
                "used_lightrag": has_lightrag_hit,
                "lightrag_base_url": knowledge_base_service.client.base_url,
                "llm_errors": errors,
            },
        }

    def _normalize_question_sets(self, value: Any, has_lightrag_hit: bool) -> dict[str, list[dict[str, Any]]]:
        sets: dict[str, list[dict[str, Any]]] = {key: [] for key, _label in QUESTION_CATEGORIES}
        if isinstance(value, dict):
            for key, label in QUESTION_CATEGORIES:
                raw_items = value.get(key) or []
                if isinstance(raw_items, list):
                    for item in raw_items:
                        if isinstance(item, dict):
                            sets[key].append(self._normalize_question(item, label, has_lightrag_hit))
        if sum(len(items) for items in sets.values()) == 0:
            fallback = self._fallback_questions({}, has_lightrag_hit)
            for question in fallback:
                key = next((k for k, label in QUESTION_CATEGORIES if question["category"] == label), "technical_basics")
                sets[key].append(question)
        counter = 1
        for key, _label in QUESTION_CATEGORIES:
            for question in sets[key]:
                question["id"] = f"Q{counter}"
                counter += 1
        return sets

    def _normalize_question(self, item: dict[str, Any], fallback_category: str, has_lightrag_hit: bool) -> dict[str, Any]:
        source_type = str(item.get("source_type") or "system_generated")
        if source_type != "lightrag" or not has_lightrag_hit:
            source_type = "system_generated"
            refs: list[str] = []
        else:
            refs = self._string_list(item.get("source_refs"))[:4]
        return {
            "id": str(item.get("id") or ""),
            "category": str(item.get("category") or fallback_category),
            "difficulty": str(item.get("difficulty") or "medium"),
            "question": str(item.get("question") or item.get("content") or "请介绍一个与你简历相关的项目。").strip(),
            "why_ask": str(item.get("why_ask") or "考察简历经历与岗位能力的匹配度。").strip(),
            "answer_points": self._string_list(item.get("answer_points"))[:6],
            "follow_ups": self._string_list(item.get("follow_ups"))[:5],
            "source_type": source_type,
            "source_refs": refs,
            "related_resume_evidence": str(item.get("related_resume_evidence") or "").strip(),
        }

    def _fallback_question_report(
        self,
        *,
        resume_text: str,
        profile: dict[str, Any],
        retrieval_results: list[LightRAGQueryResult],
        has_lightrag_hit: bool,
    ) -> dict[str, Any]:
        questions = self._fallback_questions(profile, has_lightrag_hit)
        question_sets: dict[str, list[dict[str, Any]]] = {key: [] for key, _label in QUESTION_CATEGORIES}
        for question in questions:
            key = next((k for k, label in QUESTION_CATEGORIES if question["category"] == label), "technical_basics")
            question_sets[key].append(question)
        return {
            "summary": {
                "target_position": profile.get("target_position") or "未明确",
                "target_position_source": profile.get("target_position_source") or "unknown",
                "question_count": len(questions),
                "source_note": "LLM 题目生成不可用，当前为系统兜底生成题目。",
            },
            "question_sets": question_sets,
            "practice_plan": self._default_practice_plan(),
        }

    def _fallback_questions(self, profile: dict[str, Any], has_lightrag_hit: bool) -> list[dict[str, Any]]:
        skills = self._string_list(profile.get("skills")) or ["核心技术栈"]
        projects = profile.get("projects") if isinstance(profile.get("projects"), list) else []
        project_name = "你简历中最重要的项目"
        if projects and isinstance(projects[0], dict) and projects[0].get("name"):
            project_name = str(projects[0]["name"])
        source_type = "system_generated"
        source_refs: list[str] = []
        base = [
            ("项目深挖题", "medium", f"请介绍 {project_name} 的业务背景、你的职责、核心技术难点和最终结果。"),
            ("项目深挖题", "hard", f"{project_name} 中如果核心接口响应变慢，你会如何定位瓶颈并优化？"),
            ("项目深挖题", "medium", f"你在 {project_name} 中做过最能体现个人贡献的技术决策是什么？为什么这样做？"),
            ("技术基础题", "easy", f"请解释 {skills[0]} 的核心原理，以及你在项目中如何使用它。"),
            ("技术基础题", "easy", "请说明数据库索引的适用场景、失效场景和排查方式。"),
            ("技术基础题", "medium", "请说明缓存与数据库一致性常见方案，并结合你的项目说明取舍。"),
            ("技术进阶题", "hard", "如果系统并发量突然提升 10 倍，你会从哪些层面改造架构？"),
            ("技术进阶题", "hard", "请设计一套线上故障排查流程，说明日志、指标、链路追踪分别怎么用。"),
            ("技术进阶题", "medium", f"围绕 {skills[0]}，你遇到过哪些边界问题或坑？如何解决？"),
            ("场景设计题", "hard", "请设计一个支持权限控制、审计日志和高并发访问的后台系统。"),
            ("场景设计题", "medium", "如果项目需要接入第三方接口且对方不稳定，你会如何保证业务可用性？"),
            ("场景设计题", "medium", "如果简历项目需要上线到生产环境，你会设计哪些监控和告警？"),
            ("追问题", "medium", "你刚才提到的技术难点，有没有可量化的指标证明优化有效？"),
            ("追问题", "medium", "这个项目中哪些部分是你独立完成的，哪些是团队协作完成的？"),
            ("追问题", "hard", "如果让你重新做一次这个项目，你会保留什么、重构什么？"),
        ]
        return [
            {
                "id": f"Q{index}",
                "category": category,
                "difficulty": difficulty,
                "question": question,
                "why_ask": "考察候选人是否能把简历经历讲清楚，并证明真实参与和技术理解。",
                "answer_points": ["背景与目标", "个人职责", "关键技术动作", "结果或指标", "复盘与改进"],
                "follow_ups": ["请给出具体数据。", "这个方案有什么缺点？", "如果规模扩大你会怎么改？"],
                "source_type": source_type,
                "source_refs": source_refs,
                "related_resume_evidence": project_name,
            }
            for index, (category, difficulty, question) in enumerate(base, start=1)
        ]




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

    def _default_practice_plan(self) -> list[str]:
        return [
            "先准备 2 分钟项目讲解，覆盖背景、职责、技术难点、结果和复盘。",
            "按技术栈逐项复习基础原理，再补充项目中的真实使用细节。",
            "对每个项目准备 2 个量化指标和 1 个可追问的技术细节。",
        ]
