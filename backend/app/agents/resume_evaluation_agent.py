from __future__ import annotations

import logging
import re
from collections.abc import AsyncGenerator
from typing import Any

from app.agents.base_agent import BaseAgent
from app.core.resume_roundtable_graph import ResumeRoundTableGraph
from app.schemas.agent_schema import AgentRequest, AgentResponse
from app.services.report_formatter import report_formatter
from app.services.resume_tool_service import resume_tool_service

logger = logging.getLogger(__name__)


class ResumeEvaluationAgent(BaseAgent):
    name = "resume_evaluation_agent"
    task_type = "resume_evaluation"

    async def run(self, request: AgentRequest) -> AgentResponse:
        final_response: AgentResponse | None = None
        async for event in self.stream(request):
            if event.get("type") == "result":
                final_response = AgentResponse(
                    success=event.get("success", True),
                    agent=self.name,
                    task_type=self.task_type,
                    message=event.get("message"),
                    result=event.get("result", {}),
                )
        return final_response or AgentResponse(
            success=False,
            agent=self.name,
            task_type=self.task_type,
            message="简历评估未生成结果。",
            result={"success": False, "error": "no_result"},
        )

    async def stream(self, request: AgentRequest) -> AsyncGenerator[dict[str, Any], None]:
        resume_text = (request.resume_text or "").strip()
        if not resume_text:
            yield {
                "type": "result",
                "success": False,
                "message": "未检测到可评估的简历文本，请先上传或粘贴简历。",
                "result": {"success": False, "error": "empty_resume_text"},
            }
            return

        target_position, source = self._infer_target_position(request.message, resume_text)
        filename = request.filename or request.metadata.get("filename", "")
        parsed_char_count = len(resume_text)
        yield {
            "type": "progress",
            "stage": "file",
            "status": "done",
            "message": "简历文件解析完成。",
            "filename": filename,
            "parsed_char_count": parsed_char_count,
        }

        yield {
            "type": "progress",
            "stage": "tools",
            "status": "running",
            "message": "正在提取基础信息、风险词、结构与模板化线索。",
        }
        tool_findings = resume_tool_service.run_all(resume_text)
        yield {
            "type": "progress",
            "stage": "tools",
            "status": "done",
            "message": "本地工具线索提取完成，线索将交给 AI 专家判断。",
            "tool_findings": tool_findings,
        }

        graph = ResumeRoundTableGraph()
        initial_state = {
            "resume_text": resume_text,
            "user_message": request.message,
            "target_position": target_position,
            "target_position_source": source,
            "tool_findings": tool_findings,
            "filename": filename,
            "api_config": request.api_config,
            "errors": [],
        }
        state: dict[str, Any] = {}
        async for event in graph.astream_events(initial_state):
            if event.get("type") == "state":
                state = event.get("state", {})
            else:
                yield event

        if state.get("llm_failed") or not state.get("reflector_output"):
            yield {
                "type": "result",
                "success": False,
                "message": "AI 多专家圆桌会议暂时不可用，未生成 AI 简历评估报告。请检查 backend/.env 中的 DeepSeek 配置后重试。",
                "result": self._llm_unavailable_result(
                    tool_findings=tool_findings,
                    filename=filename,
                    parsed_char_count=parsed_char_count,
                    target_position=target_position,
                    target_position_source=source,
                    errors=state.get("errors", []),
                ),
            }
            return
        else:
            yield {
                "type": "progress",
                "stage": "report",
                "status": "running",
                "message": "正在生成结构化评估报告与简历优化对比。",
            }
            report = report_formatter.normalize_llm_report(
                report=state.get("reflector_output", {}),
                tool_findings=tool_findings,
                expert_outputs=state.get("expert_outputs", {}),
                filename=filename,
                parsed_char_count=parsed_char_count,
                llm_errors=state.get("errors", []),
                resume_text=resume_text,
            )
            yield {
                "type": "result",
                "success": True,
                "message": "简历评估报告已生成。",
                "result": report,
            }

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

    def _llm_unavailable_result(
        self,
        *,
        tool_findings: dict[str, Any],
        filename: str,
        parsed_char_count: int,
        target_position: str,
        target_position_source: str,
        errors: list[str],
    ) -> dict[str, Any]:
        return {
            "agent": self.name,
            "task_type": self.task_type,
            "success": False,
            "report_status": "llm_unavailable",
            "message": "AI 多专家圆桌会议暂时不可用，当前没有生成 AI 评估结论。",
            "summary": {
                "overall_score": None,
                "risk_level": "未生成",
                "target_position": target_position or "未明确",
                "target_position_source": target_position_source,
                "main_problems": [],
                "main_suggestions": [],
            },
            "tool_findings": tool_findings,
            "roundtable": {},
            "metadata": {
                "filename": filename,
                "parsed_char_count": parsed_char_count,
                "used_llm_roundtable": False,
                "used_tool_clues": True,
                "used_forbidden_word_tool": True,
                "used_template_duplication_tool": True,
                "llm_errors": errors,
            },
        }
