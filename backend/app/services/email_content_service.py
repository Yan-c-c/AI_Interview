from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.json_utils import loads_json_response
from app.core.llms import get_llm_for_request
from app.schemas.email_campaign_schema import EmailCampaignContentRequest
from app.services.file_parser_service import file_parser_service

logger = logging.getLogger(__name__)


class EmailContentService:
    async def generate(self, request: EmailCampaignContentRequest) -> dict[str, Any]:
        resume_text = self._resume_text(request)
        try:
            payload = await self._call_llm(request=request, resume_text=resume_text, mode="generate")
            used_deepseek = True
            llm_errors: list[str] = []
        except Exception as exc:
            logger.warning("email campaign generation failed: %s", exc)
            payload = self._fallback_content(request, resume_text)
            used_deepseek = False
            llm_errors = [str(exc)]
        return self._normalize_payload(payload, used_deepseek=used_deepseek, llm_errors=llm_errors)

    async def polish(self, request: EmailCampaignContentRequest) -> dict[str, Any]:
        resume_text = self._resume_text(request)
        if not (request.subject.strip() or request.content.strip()):
            raise ValueError("empty_content")
        try:
            payload = await self._call_llm(request=request, resume_text=resume_text, mode="polish")
            used_deepseek = True
            llm_errors: list[str] = []
        except Exception as exc:
            logger.warning("email campaign polish failed: %s", exc)
            payload = self._fallback_polish(request)
            used_deepseek = False
            llm_errors = [str(exc)]
        return self._normalize_payload(payload, used_deepseek=used_deepseek, llm_errors=llm_errors)

    async def _call_llm(
        self,
        *,
        request: EmailCampaignContentRequest,
        resume_text: str,
        mode: str,
    ) -> dict[str, Any]:
        llm = get_llm_for_request(request.api_config, channel="smart", temperature=0.35, max_tokens=3200)
        system = (
            "你是智能面试助手中的邮件群发 Agent，负责生成或润色求职邮件。"
            "必须结合简历、求职信、目标公司/岗位、邮件用途和语气风格，生成可群发但带轻量个性化变量的邮件。"
            "允许使用变量 {{name}}、{{company}}、{{position}}，不要编造用户没有的经历。"
            "只输出 JSON，不要输出 markdown。"
        )
        instruction = "生成一封适合批量发送但可个性化渲染的求职邮件。" if mode == "generate" else "润色用户已有邮件，保留事实和核心诉求，增强礼貌、清晰度和求职匹配表达。"
        response = await llm.ainvoke(
            [
                SystemMessage(content=system),
                HumanMessage(
                    content=f"""{instruction}

用户自然语言需求：
{request.message}

目标公司：{request.target_company}
目标岗位：{request.target_position}
邮件用途：{request.purpose}
语气风格：{request.style}

已有邮件主题：
{request.subject}

已有邮件正文：
{request.content}

已有求职信内容：
{request.cover_letter[:5000]}

简历/个人背景：
{resume_text[:10000]}

请输出 JSON：
{{
  "subject": "",
  "content": "",
  "variables": ["{{{{name}}}}", "{{{{company}}}}", "{{{{position}}}}"],
  "personalization_notes": [],
  "attachments_advice": [],
  "preview": {{
    "sample_subject": "",
    "sample_content": ""
  }}
}}"""
                ),
            ]
        )
        data = loads_json_response(str(response.content or ""))
        if not isinstance(data, dict):
            raise ValueError("email content response is not object")
        return data

    def _resume_text(self, request: EmailCampaignContentRequest) -> str:
        if request.resume_text.strip():
            return request.resume_text.strip()
        if request.file_id:
            record = file_parser_service.get_record(request.file_id)
            if record:
                return record.parsed_text.strip()
        return ""

    def _normalize_payload(self, payload: dict[str, Any], *, used_deepseek: bool, llm_errors: list[str]) -> dict[str, Any]:
        subject = str(payload.get("subject") or "").strip() or "求职申请 - {{position}}"
        content = str(payload.get("content") or "").strip() or self._default_body()
        variables = payload.get("variables") if isinstance(payload.get("variables"), list) else ["{{name}}", "{{company}}", "{{position}}"]
        notes = payload.get("personalization_notes") if isinstance(payload.get("personalization_notes"), list) else []
        advice = payload.get("attachments_advice") if isinstance(payload.get("attachments_advice"), list) else []
        preview = payload.get("preview") if isinstance(payload.get("preview"), dict) else {}
        return {
            "agent": "email_campaign_agent",
            "task_type": "email_campaign",
            "success": True,
            "subject": subject,
            "content": content,
            "variables": [str(item) for item in variables],
            "personalization_notes": [str(item) for item in notes],
            "attachments_advice": [str(item) for item in advice],
            "preview": {
                "sample_subject": str(preview.get("sample_subject") or subject).strip(),
                "sample_content": str(preview.get("sample_content") or content).strip(),
            },
            "metadata": {
                "used_deepseek": used_deepseek,
                "llm_errors": llm_errors,
            },
        }

    def _fallback_content(self, request: EmailCampaignContentRequest, resume_text: str) -> dict[str, Any]:
        position = request.target_position.strip() or "{{position}}"
        company = request.target_company.strip() or "{{company}}"
        return {
            "subject": f"求职申请 - {position}",
            "content": (
                "您好，{{name}}：\n\n"
                f"我想应聘{company}的{position}岗位。结合我的项目经历和技术基础，我希望有机会进一步沟通岗位匹配情况。\n\n"
                "附件中包含我的简历，如方便，期待您的回复。谢谢。\n\n"
                "此致\n敬礼"
            ),
            "variables": ["{{name}}", "{{company}}", "{{position}}"],
            "personalization_notes": ["DeepSeek 暂不可用，当前为基础草稿；建议稍后使用 AI 重新生成。"],
            "attachments_advice": ["建议附加 PDF 简历。"],
        }

    def _fallback_polish(self, request: EmailCampaignContentRequest) -> dict[str, Any]:
        return {
            "subject": request.subject.strip() or "求职申请 - {{position}}",
            "content": request.content.strip() or self._default_body(),
            "variables": ["{{name}}", "{{company}}", "{{position}}"],
            "personalization_notes": ["AI 润色暂不可用，保留了原始内容。"],
            "attachments_advice": ["发送前请检查附件是否为最新版本。"],
        }

    def _default_body(self) -> str:
        return "您好，{{name}}：\n\n我想应聘贵公司 {{position}} 岗位，附件为我的简历，期待有机会进一步沟通。\n\n谢谢。"


email_content_service = EmailContentService()
