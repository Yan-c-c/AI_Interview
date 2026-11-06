from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.email_campaign_schema import (
    EmailCampaignContentRequest,
    EmailCampaignCreateRequest,
    EmailCampaignResponse,
    EmailCampaignSendRequest,
    EmailCampaignTestSMTPRequest,
)
from app.services.email_campaign_service import email_campaign_service
from app.services.email_content_service import email_content_service

router = APIRouter(prefix="/api/email-campaign", tags=["邮件群发 Agent"])


ERROR_MESSAGES = {
    "smtp_not_configured": "请填写 SMTP Host、发件邮箱和账号信息。",
    "smtp_invalid_port": "SMTP 端口格式不正确。",
    "smtp_auth_failed": "SMTP 认证失败，请检查邮箱账号和授权码。",
    "smtp_connection_failed": "SMTP 连接失败，请检查 Host、端口和 SSL/TLS。",
    "empty_recipients": "请至少添加一个有效收件人。",
    "empty_email_content": "请先填写或生成邮件主题和正文。",
    "send_not_confirmed": "发送前需要勾选确认，避免误发。",
    "attachment_not_found": "附件不存在或已失效，请重新上传。",
    "attachment_too_large": "单个附件超过 20MB，请压缩或移除后重试。",
}


@router.post("/test-smtp", response_model=EmailCampaignResponse)
async def test_smtp(request: EmailCampaignTestSMTPRequest) -> EmailCampaignResponse:
    try:
        result = email_campaign_service.test_smtp(request.smtp_config.model_dump())
    except Exception as exc:
        key = str(exc)
        return EmailCampaignResponse(
            success=False,
            result={"success": False, "smtp_status": "failed", "error": key},
            message=ERROR_MESSAGES.get(key, "SMTP 测试失败，请检查配置。"),
        )
    return EmailCampaignResponse(success=True, result=result, message="SMTP 配置可用。")


@router.post("/generate-content", response_model=EmailCampaignResponse)
async def generate_content(request: EmailCampaignContentRequest) -> EmailCampaignResponse:
    result = await email_content_service.generate(request)
    return EmailCampaignResponse(success=True, result=result, message="邮件内容已生成。")


@router.post("/polish-content", response_model=EmailCampaignResponse)
async def polish_content(request: EmailCampaignContentRequest) -> EmailCampaignResponse:
    try:
        result = await email_content_service.polish(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "EmptyContent", "message": "请先填写邮件主题或正文后再润色。"}) from exc
    return EmailCampaignResponse(success=True, result=result, message="邮件内容已润色。")


@router.post("/create", response_model=EmailCampaignResponse)
async def create_campaign(request: EmailCampaignCreateRequest) -> EmailCampaignResponse:
    try:
        result = email_campaign_service.create_task(request)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        key = str(exc)
        raise HTTPException(status_code=400, detail={"error": key, "message": ERROR_MESSAGES.get(key, "群发任务创建失败。")}) from exc
    return EmailCampaignResponse(success=True, result=result, message="群发任务已创建，请预览确认后发送。")


@router.post("/send", response_model=EmailCampaignResponse)
async def send_campaign(request: EmailCampaignSendRequest) -> EmailCampaignResponse:
    try:
        result = email_campaign_service.send_task(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"error": "TaskNotFound", "message": "未找到群发任务。"}) from exc
    except (ValueError, RuntimeError) as exc:
        key = str(exc)
        raise HTTPException(status_code=400, detail={"error": key, "message": ERROR_MESSAGES.get(key, "群发任务发送失败。")}) from exc
    return EmailCampaignResponse(success=True, result=result, message="群发任务执行完成。")


@router.get("/history")
async def campaign_history(limit: int = 30) -> dict:
    return {"success": True, "items": email_campaign_service.history(limit=limit)}


@router.get("/{task_id}")
async def campaign_detail(task_id: str) -> dict:
    task = email_campaign_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail={"error": "TaskNotFound", "message": "未找到群发任务。"})
    return {"success": True, "result": task}
