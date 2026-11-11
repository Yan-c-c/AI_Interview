import { authHeaders, AuthUser } from "@/lib/auth";
import { API_BASE_URL } from "./resumeEvaluation";
import type { InterviewAudioAnalysisReport } from "./interviewAudio";

export interface AdminMetric {
  label: string;
  value: number | string;
  hint: string;
  tone: string;
}

export interface UserAnalytics {
  total: number;
  active: number;
  disabled: number;
  admins: number;
  regular_users: number;
  new_7d: number;
  by_role: Record<string, number>;
  by_status: Record<string, number>;
}

export interface AdminOverview {
  success: boolean;
  metrics: AdminMetric[];
  users: UserAnalytics;
  question_bank: {
    documents: number;
    chunks: number;
    graph_nodes: number;
    graph_edges: number;
    external_status: string;
    external_available: boolean;
    recent_documents: Array<Record<string, unknown>>;
  };
  audio_reviews: {
    total_tasks: number;
    completed_tasks: number;
    approved: number;
    rejected: number;
    failed: number;
    pending_review: number;
    logs: number;
  };
  agent_counts: Array<{ key: string; label: string; runs: number }>;
}

export interface AgentMonitor {
  key: string;
  name: string;
  runs: number;
  status: "online" | "attention" | string;
  success_rate: number | null;
  note: string;
}

export interface AudioReviewTask {
  task_id: string;
  status: string;
  review_status: string;
  audio_filename?: string;
  created_at?: string;
  updated_at?: string;
  error?: string | null;
  qa_count: number;
  overall_score?: number | null;
  has_result: boolean;
  result?: InterviewAudioAnalysisReport | null;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 10000);
  const headers = new Headers(init?.headers);
  if (!(init?.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  Object.entries(authHeaders()).forEach(([key, value]) => headers.set(key, value));
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
      signal: controller.signal,
      credentials: "include",
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail?.message || error.message || "后台管理请求失败");
    }
    return response.json();
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("后台接口响应超时，请确认后端服务已启动。");
    }
    if (error instanceof TypeError) {
      throw new Error("后台接口连接失败，请确认后端服务已启动，且浏览器当前地址在后端 CORS 允许范围内。");
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function login(params: { email: string; password: string }): Promise<{ success: boolean; user: AuthUser; token: string }> {
  return requestJson("/api/admin/auth/login", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function register(params: { name: string; email: string; password: string }): Promise<{ success: boolean; user: AuthUser; token: string }> {
  return requestJson("/api/admin/auth/register", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function fetchMe(): Promise<{ success: boolean; user: AuthUser }> {
  return requestJson("/api/admin/auth/me");
}

export async function fetchAdminOverview(): Promise<AdminOverview> {
  return requestJson("/api/admin/overview");
}

export async function fetchAdminUsers(): Promise<{ success: boolean; users: AuthUser[]; analytics: UserAnalytics; total: number }> {
  return requestJson("/api/admin/users");
}

export async function createAdminUser(params: { name: string; email: string; password: string; role: "user" | "admin" }): Promise<{ success: boolean; user: AuthUser }> {
  return requestJson("/api/admin/users", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function updateAdminUser(userId: string, params: Partial<Pick<AuthUser, "name" | "role" | "status">>): Promise<{ success: boolean; user: AuthUser }> {
  return requestJson(`/api/admin/users/${encodeURIComponent(userId)}`, {
    method: "PATCH",
    body: JSON.stringify(params),
  });
}

export async function deleteAdminUser(userId: string): Promise<{ success: boolean; deleted: boolean; user_id: string }> {
  return requestJson(`/api/admin/users/${encodeURIComponent(userId)}`, {
    method: "DELETE",
  });
}

export async function fetchAgentMonitoring(): Promise<{ success: boolean; agents: AgentMonitor[]; recent_events: Array<Record<string, unknown>> }> {
  return requestJson("/api/admin/agent-monitoring");
}

export async function fetchAudioReviewTasks(): Promise<{ success: boolean; tasks: AudioReviewTask[]; total: number; summary: AdminOverview["audio_reviews"] }> {
  return requestJson("/api/admin/audio-reviews");
}
