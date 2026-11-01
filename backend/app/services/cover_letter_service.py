from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.json_utils import loads_json_response
from app.core.llms import get_llm_for_request
from app.schemas.agent_schema import AgentRequest

logger = logging.getLogger(__name__)


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        if "、" in value or "," in value:
            return [item.strip() for item in value.replace(",", "、").split("、") if item.strip()]
        return [value.strip()]
    return []


def _score(value: Any, fallback: int) -> int:
    try:
        return max(0, min(100, int(float(value))))
    except (TypeError, ValueError):
        return fallback


def _int_value(value: Any, fallback: int, minimum: int = 100, maximum: int = 2000) -> int:
    try:
        return max(minimum, min(maximum, int(float(value))))
    except (TypeError, ValueError):
        return fallback


class CoverLetterService:
    def __init__(self) -> None:
        self.history_dir = Path(__file__).resolve().parents[2] / "data" / "cover_letters"
        self.history_dir.mkdir(parents=True, exist_ok=True)

    async def generate(self, request: AgentRequest) -> dict[str, Any]:
        resume_text = (request.resume_text or "").strip()
        form = self._requirements_from_request(request)
        missing_fields = self._missing_fields(form, resume_text)
        used_deepseek = True
        llm_errors: list[str] = []

        try:
            payload = await self._call_generation_llm(request, resume_text, form, missing_fields)
        except Exception as exc:
            logger.warning("cover letter LLM generation failed: %s", exc)
            used_deepseek = False
            llm_errors.append(str(exc))
            payload = self._fallback_payload(form, resume_text, missing_fields)

        report = self._normalize_report(
            payload=payload,
            request=request,
            form=form,
            resume_text=resume_text,
            missing_fields=missing_fields,
            used_deepseek=used_deepseek,
            llm_errors=llm_errors,
        )
        self._save_history(report)
        return report

    async def rewrite(self, *, report: dict[str, Any], instruction: str, api_config: dict | None = None) -> dict[str, Any]:
        instruction = instruction.strip()
        if not instruction:
            raise ValueError("empty_instruction")
        used_deepseek = True
        llm_errors: list[str] = []
        try:
            llm = get_llm_for_request(api_config, channel="smart", temperature=0.35, max_tokens=3600)
            response = await llm.ainvoke(
                [
                    SystemMessage(content="你是求职信改写 Agent。根据用户要求改写已有求职信，保持事实不编造。只输出 JSON。"),
                    HumanMessage(
                        content=f"""用户修改要求：
{instruction}

已有求职信结果：
{json.dumps(report, ensure_ascii=False)[:12000]}

请输出 JSON，结构与原报告的 versions 字段一致，只需要返回：
{{
  "versions": {{
    "custom": {{"title": "", "body": ""}},
    "standard": {{"title": "", "body": ""}},
    "email_short": {{"title": "", "body": ""}},
    "technical": {{"title": "", "body": ""}},
    "campus_internship": {{"title": "", "body": ""}}
  }},
  "optimization_suggestions": ["后续可继续优化点"],
  "email": {{"subject": "", "body": ""}}
}}"""
                    ),
                ]
            )
            data = loads_json_response(str(response.content or ""))
            if not isinstance(data, dict):
                raise ValueError("rewrite response is not object")
        except Exception as exc:
            used_deepseek = False
            llm_errors.append(str(exc))
            data = self._fallback_rewrite(report, instruction)

        updated = dict(report)
        versions = dict(report.get("versions") or {})
        versions.update(self._normalize_versions(data.get("versions")))
        updated["versions"] = versions
        updated["optimization_suggestions"] = _string_list(data.get("optimization_suggestions"))[:8] or report.get("optimization_suggestions", [])
        if isinstance(data.get("email"), dict):
            updated["email"] = data["email"]
        updated["metadata"] = {
            **(report.get("metadata") or {}),
            "used_deepseek_rewrite": used_deepseek,
            "rewrite_instruction": instruction,
            "rewrite_errors": llm_errors,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._save_history(updated)
        return updated

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(self.history_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]:
            try:
                items.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        return items

    async def _call_generation_llm(
        self,
        request: AgentRequest,
        resume_text: str,
        form: dict[str, Any],
        missing_fields: list[str],
    ) -> dict[str, Any]:
        llm = get_llm_for_request(request.api_config, channel="smart", temperature=0.3, max_tokens=5200)
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content=(
                        "你是求职信生成 Agent。你必须结合简历/个人背景、目标公司、目标岗位和 JD 生成个性化求职信，"
                        "不能套模板，不能编造简历没有的经历。输出严格 JSON，不要 markdown。"
                    )
                ),
                HumanMessage(
                    content=f"""用户自然语言需求：
{request.message}

用户补充信息：
{json.dumps(form, ensure_ascii=False)}

缺失字段：
{missing_fields}

简历或个人背景：
{(resume_text or form.get("personal_background") or request.message)[:14000]}

请输出 JSON：
{{
  "resume_profile": {{
    "name": "",
    "education": "",
    "skills": [],
    "projects": [],
    "internships": [],
    "strongest_evidence": [],
    "job_fit_summary": ""
  }},
  "requirements": {{
    "target_company": "",
    "target_position": "",
    "jd_summary": "",
    "recipient": "",
    "purpose": "",
    "style": "",
    "focus_points": [],
    "word_count": 500
  }},
  "missing_fields": [],
  "needs_more_info": false,
  "versions": {{
    "standard": {{"title": "", "body": ""}},
    "email_short": {{"title": "", "body": ""}},
    "technical": {{"title": "", "body": ""}},
    "campus_internship": {{"title": "", "body": ""}}
  }},
  "highlight_points": [],
  "optimization_suggestions": [],
  "email": {{"subject": "", "body": ""}}
}}"""
                ),
            ]
        )
        data = loads_json_response(str(response.content or ""))
        if not isinstance(data, dict):
            raise ValueError("cover letter response is not object")
        return data

    def _requirements_from_request(self, request: AgentRequest) -> dict[str, Any]:
        metadata = request.metadata or {}
        return {
            "target_company": str(metadata.get("target_company") or "").strip(),
            "target_position": str(metadata.get("target_position") or "").strip(),
            "jd": str(metadata.get("jd") or metadata.get("job_description") or "").strip(),
            "recipient": str(metadata.get("recipient") or "HR").strip(),
            "purpose": str(metadata.get("purpose") or "求职申请").strip(),
            "style": str(metadata.get("style") or "正式专业").strip(),
            "focus_points": _string_list(metadata.get("focus_points") or metadata.get("highlights")),
            "word_count": _int_value(metadata.get("word_count"), 500),
            "personal_background": str(metadata.get("personal_background") or "").strip(),
        }

    def _missing_fields(self, form: dict[str, Any], resume_text: str) -> list[str]:
        missing: list[str] = []
        if not resume_text and not form.get("personal_background"):
            missing.append("简历或个人背景")
        if not form.get("target_company"):
            missing.append("目标公司")
        if not form.get("target_position"):
            missing.append("目标岗位")
        if not form.get("jd"):
            missing.append("招聘 JD")
        return missing

    def _normalize_report(
        self,
        *,
        payload: dict[str, Any],
        request: AgentRequest,
        form: dict[str, Any],
        resume_text: str,
        missing_fields: list[str],
        used_deepseek: bool,
        llm_errors: list[str],
    ) -> dict[str, Any]:
        history_id = str(uuid.uuid4())
        requirements = payload.get("requirements") if isinstance(payload.get("requirements"), dict) else {}
        normalized_requirements = {
            "target_company": str(requirements.get("target_company") or form.get("target_company") or "目标公司待补充").strip(),
            "target_position": str(requirements.get("target_position") or form.get("target_position") or "目标岗位待补充").strip(),
            "jd_summary": str(requirements.get("jd_summary") or form.get("jd") or "").strip()[:800],
            "recipient": str(requirements.get("recipient") or form.get("recipient") or "HR").strip(),
            "purpose": str(requirements.get("purpose") or form.get("purpose") or "求职申请").strip(),
            "style": str(requirements.get("style") or form.get("style") or "正式专业").strip(),
            "focus_points": _string_list(requirements.get("focus_points") or form.get("focus_points"))[:8],
            "word_count": _int_value(requirements.get("word_count") or form.get("word_count"), 500),
        }
        report = {
            "agent": "cover_letter_agent",
            "task_type": "cover_letter_generation",
            "success": True,
            "needs_more_info": bool(payload.get("needs_more_info")) or bool(missing_fields),
            "missing_fields": _string_list(payload.get("missing_fields")) or missing_fields,
            "resume_profile": self._normalize_profile(payload.get("resume_profile")),
            "requirements": normalized_requirements,
            "versions": self._normalize_versions(payload.get("versions")),
            "highlight_points": _string_list(payload.get("highlight_points"))[:8],
            "optimization_suggestions": _string_list(payload.get("optimization_suggestions"))[:8],
            "email": self._normalize_email(payload.get("email"), normalized_requirements),
            "metadata": {
                "history_id": history_id,
                "filename": request.filename or request.metadata.get("filename", ""),
                "parsed_char_count": len(resume_text),
                "used_deepseek": used_deepseek,
                "llm_errors": llm_errors,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "note": "" if resume_text else "未上传简历，当前结果主要基于用户输入背景生成；上传简历可获得更精准结果。",
            },
        }
        if not report["versions"].get("standard", {}).get("body"):
            report["versions"] = self._normalize_versions(self._fallback_payload(form, resume_text, missing_fields)["versions"])
        return report

    def _normalize_profile(self, value: Any) -> dict[str, Any]:
        profile = value if isinstance(value, dict) else {}
        return {
            "name": str(profile.get("name") or "").strip(),
            "education": str(profile.get("education") or "").strip(),
            "skills": _string_list(profile.get("skills"))[:16],
            "projects": _string_list(profile.get("projects"))[:8],
            "internships": _string_list(profile.get("internships"))[:6],
            "strongest_evidence": _string_list(profile.get("strongest_evidence"))[:8],
            "job_fit_summary": str(profile.get("job_fit_summary") or "").strip(),
        }

    def _normalize_versions(self, value: Any) -> dict[str, dict[str, str]]:
        raw = value if isinstance(value, dict) else {}
        labels = {
            "standard": "标准版求职信",
            "email_short": "邮件正文精简版",
            "technical": "技术岗位版求职信",
            "campus_internship": "校招/实习版求职信",
            "custom": "自定义改写版",
        }
        versions: dict[str, dict[str, str]] = {}
        for key, title in labels.items():
            item = raw.get(key) if isinstance(raw.get(key), dict) else {}
            body = str(item.get("body") or "").strip()
            versions[key] = {"title": str(item.get("title") or title).strip(), "body": body}
        return versions

    def _normalize_email(self, value: Any, requirements: dict[str, Any]) -> dict[str, str]:
        data = value if isinstance(value, dict) else {}
        company = requirements.get("target_company") or "贵公司"
        position = requirements.get("target_position") or "目标岗位"
        return {
            "subject": str(data.get("subject") or f"{position}求职申请 - 智能面试助手生成").strip(),
            "body": str(data.get("body") or f"您好，我想申请{company}{position}岗位，附件/正文为我的求职信，请查收。").strip(),
        }

    def _fallback_payload(self, form: dict[str, Any], resume_text: str, missing_fields: list[str]) -> dict[str, Any]:
        company = form.get("target_company") or "目标公司"
        position = form.get("target_position") or "目标岗位"
        body = (
            f"尊敬的{form.get('recipient') or 'HR'}：\n\n"
            f"您好！我希望申请{company}的{position}岗位。基于我的学习与项目经历，我希望在该岗位中发挥技术能力、"
            "问题分析能力和持续学习能力。后续建议补充更完整的简历、招聘 JD 与目标公司信息，以便生成更精准的个性化求职信。\n\n"
            "感谢您的阅读，期待获得进一步沟通机会。"
        )
        return {
            "resume_profile": {"skills": [], "projects": [], "strongest_evidence": [], "job_fit_summary": "信息不足，建议补充简历和 JD。"},
            "requirements": form,
            "missing_fields": missing_fields,
            "needs_more_info": bool(missing_fields),
            "versions": {
                "standard": {"title": f"{position}求职信", "body": body},
                "email_short": {"title": f"{position}申请邮件正文", "body": body},
                "technical": {"title": f"{position}技术岗位版求职信", "body": body},
                "campus_internship": {"title": f"{position}校招/实习版求职信", "body": body},
            },
            "highlight_points": ["建议补充项目经历、技术栈和量化成果"],
            "optimization_suggestions": ["补充目标公司和 JD 后重新生成", "加入 1-2 个与岗位最相关的项目证据"],
            "email": {"subject": f"{position}求职申请", "body": body},
        }

    def _fallback_rewrite(self, report: dict[str, Any], instruction: str) -> dict[str, Any]:
        standard = (report.get("versions") or {}).get("standard") or {}
        body = str(standard.get("body") or "")
        return {
            "versions": {
                "custom": {
                    "title": f"{standard.get('title') or '求职信'} - 改写版",
                    "body": f"{body}\n\n【改写要求记录】{instruction}",
                }
            },
            "optimization_suggestions": ["DeepSeek 改写暂时不可用，已保留修改要求，建议稍后重新生成。"],
        }

    def _save_history(self, report: dict[str, Any]) -> None:
        history_id = (report.get("metadata") or {}).get("history_id") or str(uuid.uuid4())
        (self.history_dir / f"{history_id}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


cover_letter_service = CoverLetterService()
