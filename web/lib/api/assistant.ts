import { API_BASE_URL, ResumeEvaluationReport } from "./resumeEvaluation";
import { CareerPlanningReport } from "./careerPlanning";
import { CoverLetterReport } from "./coverLetter";
import { EmailCampaignReport } from "./emailCampaign";
import { InterviewAudioAnalysisReport } from "./interviewAudio";
import { InterviewQuestionReport } from "./interviewQuestion";
import { SalaryNegotiationReport } from "./salaryNegotiation";

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

export interface AssistantChatResult {
  success: boolean;
  intent: string;
  agent?: string;
  result?: ResumeEvaluationReport | InterviewQuestionReport | InterviewAudioAnalysisReport | CoverLetterReport | CareerPlanningReport | EmailCampaignReport | SalaryNegotiationReport;
  message?: string;
}

export interface EvaluationStreamEvent {
  type: "progress" | "expert_status" | "result" | "done" | string;
  intent?: string;
  agent?: string;
  stage?: string;
  expert?: string;
  role?: string;
  status?: "pending" | "running" | "done" | "error" | string;
  message?: string;
  success?: boolean;
  result?: ResumeEvaluationReport;
  tool_findings?: Record<string, unknown>;
}

export async function uploadResumeFile(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "文件上传失败");
  }
  return response.json();
}

export async function chatWithAssistant(params: {
  message: string;
  file_id?: string;
  session_id?: string;
}): Promise<AssistantChatResult> {
  const response = await fetch(`${API_BASE_URL}/api/assistant/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "助手请求失败");
  }
  return response.json();
}

export async function streamAssistantEvaluation(
  params: {
    message: string;
    file_id?: string;
    session_id?: string;
  },
  onEvent: (event: EvaluationStreamEvent) => void,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/assistant/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!response.ok || !response.body) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "助手请求失败");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";
    for (const chunk of chunks) {
      const line = chunk.split("\n").find((item) => item.startsWith("data:"));
      if (!line) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      onEvent(JSON.parse(payload) as EvaluationStreamEvent);
    }
  }
}
