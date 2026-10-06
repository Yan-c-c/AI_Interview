import { authHeaders } from "@/lib/auth";
import { API_BASE_URL } from "./resumeEvaluation";

export interface KnowledgeStatus {
  success: boolean;
  module: string;
  external_retrieval: {
    available: boolean;
    status: string;
    base_url?: string;
    error?: string;
  };
  local_index: {
    document_count: number;
    processed_document_count: number;
    chunk_count: number;
    input_dir?: string;
    working_dir?: string;
  };
  graph: {
    node_count: number;
    edge_count: number;
    popular_labels?: KnowledgeGraphLabel[];
  };
  config: {
    query_mode: string;
    top_k: number;
    chunk_top_k: number;
    summary_language: string;
  };
}

export interface KnowledgeDocument {
  id: string;
  filename: string;
  file_path: string;
  status: string;
  chunks_count: number;
  content_length: number;
  content_summary: string;
  created_at?: string;
  updated_at?: string;
}

export interface KnowledgeReference {
  reference_id: string;
  file_path: string;
  content: string[];
  score?: number;
}

export interface KnowledgeQueryResult {
  success: boolean;
  query: string;
  available: boolean;
  status: string;
  answer: string;
  references: KnowledgeReference[];
  source: "external_service" | "local_embedded_index" | string;
  error?: string;
}

export interface KnowledgeGraphLabel {
  label: string;
  degree: number;
  entity_type?: string;
  description?: string;
}

export interface KnowledgeGraphData {
  root?: string;
  nodes: Array<{
    id: string;
    label: string;
    entity_type?: string;
    description?: string;
    file_path?: string;
    root?: boolean;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    type?: string;
    description?: string;
  }>;
  metadata?: Record<string, unknown>;
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  Object.entries(authHeaders()).forEach(([key, value]) => headers.set(key, value));
  try {
    const response = await fetch(url, { ...init, headers, credentials: "include" });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail?.message || error.message || "知识库请求失败");
    }
    return response.json();
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error("知识库接口连接失败，请确认后端服务已启动，且浏览器当前地址在后端 CORS 允许范围内。");
    }
    throw error;
  }
}

export async function fetchKnowledgeStatus(): Promise<KnowledgeStatus> {
  return requestJson<KnowledgeStatus>(`${API_BASE_URL}/api/knowledge-base/status`);
}

export async function fetchKnowledgeDocuments(): Promise<{ success: boolean; documents: KnowledgeDocument[]; total: number }> {
  return requestJson(`${API_BASE_URL}/api/knowledge-base/documents`);
}

export async function uploadKnowledgeDocument(file: File): Promise<{ success: boolean; document: KnowledgeDocument }> {
  const body = new FormData();
  body.append("file", file);
  return requestJson(`${API_BASE_URL}/api/knowledge-base/documents/upload`, {
    method: "POST",
    body,
  });
}

export async function insertKnowledgeText(params: { title?: string; text: string }): Promise<{ success: boolean; document: KnowledgeDocument }> {
  return requestJson(`${API_BASE_URL}/api/knowledge-base/documents/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}

export async function deleteKnowledgeDocument(documentId: string): Promise<{ success: boolean; deleted: boolean; document_id: string }> {
  return requestJson(`${API_BASE_URL}/api/knowledge-base/documents/${encodeURIComponent(documentId)}`, {
    method: "DELETE",
  });
}

export async function queryKnowledgeBase(params: { query: string; mode?: string; top_k?: number }): Promise<KnowledgeQueryResult> {
  return requestJson(`${API_BASE_URL}/api/knowledge-base/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}

export async function fetchKnowledgeGraphLabels(params?: { q?: string; limit?: number }): Promise<{ success: boolean; labels: KnowledgeGraphLabel[] }> {
  const search = new URLSearchParams();
  if (params?.q) search.set("q", params.q);
  if (params?.limit) search.set("limit", String(params.limit));
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return requestJson(`${API_BASE_URL}/api/knowledge-base/graph/labels${suffix}`);
}

export async function fetchKnowledgeGraph(params?: { label?: string; max_depth?: number; max_nodes?: number }): Promise<{ success: boolean; graph: KnowledgeGraphData }> {
  const search = new URLSearchParams();
  if (params?.label) search.set("label", params.label);
  if (params?.max_depth) search.set("max_depth", String(params.max_depth));
  if (params?.max_nodes) search.set("max_nodes", String(params.max_nodes));
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return requestJson(`${API_BASE_URL}/api/knowledge-base/graph${suffix}`);
}
