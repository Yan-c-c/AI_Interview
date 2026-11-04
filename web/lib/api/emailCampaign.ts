import { API_BASE_URL } from "./resumeEvaluation";

export interface UploadResult {
  success: boolean;
  file_id: string;
  filename: string;
  file_type: string;
  parsed_text: string;
  parsed_char_count: number;
  is_audio?: boolean;
  file_sha256?: string;
}

export interface SmtpConfig {
  host: string;
  port: number;
  username: string;
  password: string;
  from_name: string;
  from_email: string;
  use_ssl: boolean;
  use_tls: boolean;
  save_config?: boolean;
}

export interface EmailRecipient {
  id?: string;
  name: string;
  email: string;
  company?: string;
  position?: string;
  note?: string;
}

export interface CampaignAttachment {
  file_id: string;
  filename: string;
  file_type?: string;
  size?: number;
  selected?: boolean;
}

export interface EmailCampaignReport {
  agent: "email_campaign_agent" | string;
  task_type: "email_campaign" | string;
  success: boolean;
  smtp_status: string;
  status?: string;
  task_id?: string;
  subject: string;
  content: string;
  recipients_count: number;
  attachments: CampaignAttachment[];
  recipients?: EmailRecipient[];
  send_summary: {
    total: number;
    success: number;
    failed: number;
    pending: number;
    sending?: number;
    skipped?: number;
  };
  send_results: Array<{
    recipient_id: string;
    name: string;
    email: string;
    company?: string;
    position?: string;
    status: "pending" | "sending" | "success" | "failed" | "skipped" | string;
    error?: string;
    subject?: string;
    content_preview?: string;
    sent_at?: string;
  }>;
  validation_warnings?: string[];
  message?: string;
  metadata?: Record<string, unknown>;
}

export const defaultSmtpConfig: SmtpConfig = {
  host: "",
  port: 465,
  username: "",
  password: "",
  from_name: "",
  from_email: "",
  use_ssl: true,
  use_tls: false,
};

async function parseResponse<T>(response: Response, fallback: string): Promise<T> {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail?.message || data.message || fallback);
  }
  return data;
}

export async function testEmailCampaignSmtp(smtp_config: SmtpConfig): Promise<{ success: boolean; result: Record<string, unknown>; message?: string }> {
  const response = await fetch(`${API_BASE_URL}/api/email-campaign/test-smtp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ smtp_config }),
  });
  return parseResponse(response, "SMTP 测试失败");
}

export async function generateCampaignContent(params: {
  message: string;
  file_id?: string;
  cover_letter?: string;
  target_company?: string;
  target_position?: string;
  purpose?: string;
  style?: string;
}): Promise<{ subject: string; content: string; variables: string[]; personalization_notes: string[]; attachments_advice: string[] }> {
  const response = await fetch(`${API_BASE_URL}/api/email-campaign/generate-content`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  const data = await parseResponse<{ result: { subject: string; content: string; variables: string[]; personalization_notes: string[]; attachments_advice: string[] } }>(response, "邮件内容生成失败");
  return data.result;
}

export async function polishCampaignContent(params: {
  subject: string;
  content: string;
  file_id?: string;
  cover_letter?: string;
  target_company?: string;
  target_position?: string;
  purpose?: string;
  style?: string;
}): Promise<{ subject: string; content: string; variables: string[]; personalization_notes: string[]; attachments_advice: string[] }> {
  const response = await fetch(`${API_BASE_URL}/api/email-campaign/polish-content`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  const data = await parseResponse<{ result: { subject: string; content: string; variables: string[]; personalization_notes: string[]; attachments_advice: string[] } }>(response, "邮件内容润色失败");
  return data.result;
}

export async function createEmailCampaign(params: {
  smtp_config: SmtpConfig;
  recipients: EmailRecipient[];
  subject: string;
  content: string;
  attachments: CampaignAttachment[];
  personalize: boolean;
  metadata?: Record<string, unknown>;
}): Promise<EmailCampaignReport> {
  const response = await fetch(`${API_BASE_URL}/api/email-campaign/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  const data = await parseResponse<{ result: EmailCampaignReport }>(response, "群发任务创建失败");
  return data.result;
}

export async function sendEmailCampaign(params: {
  task_id: string;
  smtp_config: SmtpConfig;
  confirm: boolean;
}): Promise<EmailCampaignReport> {
  const response = await fetch(`${API_BASE_URL}/api/email-campaign/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  const data = await parseResponse<{ result: EmailCampaignReport }>(response, "群发任务发送失败");
  return data.result;
}

export async function fetchEmailCampaign(taskId: string): Promise<EmailCampaignReport> {
  const response = await fetch(`${API_BASE_URL}/api/email-campaign/${taskId}`);
  const data = await parseResponse<{ result: EmailCampaignReport }>(response, "群发任务查询失败");
  return data.result;
}

export async function fetchEmailCampaignHistory(): Promise<EmailCampaignReport[]> {
  const response = await fetch(`${API_BASE_URL}/api/email-campaign/history`);
  const data = await parseResponse<{ items: EmailCampaignReport[] }>(response, "群发历史查询失败");
  return data.items || [];
}

export async function uploadCampaignAttachment(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: "POST",
    body: form,
  });
  return parseResponse<UploadResult>(response, "附件上传失败");
}
