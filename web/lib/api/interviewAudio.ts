import { authHeaders } from "@/lib/auth";
import { API_BASE_URL } from "./resumeEvaluation";

export interface TranscriptSegment {
  segment_id: string;
  speaker: string;
  role?: "interviewer" | "candidate" | string;
  text: string;
  start_time: string;
  end_time: string;
}

export interface AudioEvidenceSource {
  source_type: "lightrag" | "baidu_ai_search" | "deepseek_generated" | string;
  title: string;
  url?: string;
  summary: string;
}

export interface AudioQAAnalysis {
  question_id: string;
  question: string;
  candidate_answer: string;
  standard_answer: string;
  accuracy_score: number;
  accuracy_level: string;
  correct_points: string[];
  missing_points: string[];
  wrong_points: string[];
  knowledge_points?: string[];
  evidence_sources: AudioEvidenceSource[];
  feedback: string;
  improvement_suggestion: string;
}

export interface InterviewAudioAnalysisReport {
  agent: "interview_audio_analysis_agent" | string;
  task_type: "interview_audio_analysis" | string;
  success: boolean;
  status?: "transcribing" | "completed" | "failed" | string;
  message?: string;
  raw_baidu_result?: Record<string, unknown>;
  task_id: string;
  summary: {
    overall_score: number | null;
    accuracy_score: number | null;
    expression_score: number | null;
    project_depth_score: number | null;
    completeness_score?: number | null;
    logic_score?: number | null;
    strengths?: string[];
    main_problems: string[];
    main_suggestions: string[];
    next_steps?: string[];
    review_focus?: string[];
    question_scores?: Array<{ question_id: string; score: number }>;
  };
  transcript: {
    raw_text: string;
    speaker_mapping: Record<string, string>;
    segments: TranscriptSegment[];
  };
  qa_pairs?: unknown[];
  qa_analysis: AudioQAAnalysis[];
  review_status: string;
  review_logs?: Array<Record<string, unknown>>;
  metadata: {
    audio_filename: string;
    audio_file_id?: string;
    audio_url?: string;
    baidu_task_id?: string;
    used_baidu_asr: boolean;
    used_speaker_diarization: boolean;
    used_lightrag: boolean;
    used_baidu_ai_search: boolean;
    used_deepseek: boolean;
    knowledge_base_document_id?: string;
    knowledge_base_track_id?: string;
  };
}

export async function analyzeInterviewAudio(params: {
  message: string;
  file_id?: string;
  audio_url?: string;
}): Promise<InterviewAudioAnalysisReport> {
  const response = await fetch(`${API_BASE_URL}/api/interview-audio/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "面试录音分析失败");
  }
  const data = await response.json();
  if (!data.success) {
    throw new Error(data.message || "面试录音分析失败");
  }
  return data as InterviewAudioAnalysisReport;
}

export async function fetchInterviewAudioTask(taskId: string): Promise<{ success: boolean; task: Record<string, unknown>; result?: InterviewAudioAnalysisReport; message?: string }> {
  const response = await fetch(`${API_BASE_URL}/api/interview-audio/${taskId}`, { credentials: "include" });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "查询录音分析任务失败");
  }
  return response.json();
}

export async function approveAudioReview(taskId: string, updates: Array<{ question_id: string; question?: string; standard_answer?: string; knowledge_points?: string[] }>) {
  const response = await fetch(`${API_BASE_URL}/api/audio-review/${taskId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify({ reviewer: "讲师", updates }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "审核通过失败");
  }
  return response.json();
}

export async function rejectAudioReview(taskId: string, reason: string) {
  const response = await fetch(`${API_BASE_URL}/api/audio-review/${taskId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify({ reviewer: "讲师", reason }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "审核驳回失败");
  }
  return response.json();
}

export async function updateAudioReview(taskId: string, updates: Array<{ question_id: string; question?: string; standard_answer?: string; knowledge_points?: string[] }>) {
  const response = await fetch(`${API_BASE_URL}/api/audio-review/${taskId}/update`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify({ reviewer: "讲师", updates }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "审核内容更新失败");
  }
  return response.json();
}

export function audioFileUrl(fileId?: string) {
  return fileId ? `${API_BASE_URL}/api/interview-audio/audio/${fileId}` : "";
}
