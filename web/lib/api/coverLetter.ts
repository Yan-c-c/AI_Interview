import { API_BASE_URL } from "./resumeEvaluation";

export interface CoverLetterVersion {
  title: string;
  body: string;
}

export interface CoverLetterReport {
  agent: "cover_letter_agent" | string;
  task_type: "cover_letter_generation" | string;
  success: boolean;
  needs_more_info: boolean;
  missing_fields: string[];
  resume_profile: {
    name?: string;
    education?: string;
    skills: string[];
    projects: string[];
    internships: string[];
    strongest_evidence: string[];
    job_fit_summary: string;
  };
  requirements: {
    target_company: string;
    target_position: string;
    jd_summary: string;
    recipient: string;
    purpose: string;
    style: string;
    focus_points: string[];
    word_count: number;
  };
  versions: Record<string, CoverLetterVersion>;
  highlight_points: string[];
  optimization_suggestions: string[];
  email: {
    subject: string;
    body: string;
  };
  metadata: {
    history_id: string;
    filename: string;
    parsed_char_count: number;
    used_deepseek: boolean;
    note?: string;
    llm_errors?: string[];
  };
}

export async function generateCoverLetter(params: {
  message: string;
  file_id?: string;
  target_company?: string;
  target_position?: string;
  jd?: string;
  recipient?: string;
  purpose?: string;
  style?: string;
  focus_points?: string[];
  word_count?: number;
  personal_background?: string;
}): Promise<{ success: boolean; agent: string; result: CoverLetterReport; message?: string }> {
  const response = await fetch(`${API_BASE_URL}/api/cover-letter/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "求职信生成失败");
  }
  return response.json();
}

export async function rewriteCoverLetter(report: CoverLetterReport, instruction: string): Promise<CoverLetterReport> {
  const response = await fetch(`${API_BASE_URL}/api/cover-letter/rewrite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report, instruction }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "求职信改写失败");
  }
  const data = await response.json();
  return data.result;
}

export async function exportCoverLetter(report: CoverLetterReport, format: "md" | "docx" | "pdf", version = "standard") {
  const response = await fetch(`${API_BASE_URL}/api/cover-letter/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report, format, version, filename: `求职信.${format}` }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "求职信导出失败");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `求职信.${format}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function sendCoverLetterEmail(params: {
  report: CoverLetterReport;
  to_email: string;
  subject?: string;
  body?: string;
  version?: string;
  attach_cover_letter?: boolean;
  attach_resume_file?: boolean;
  resume_file_id?: string;
  save_draft?: boolean;
}): Promise<{ success: boolean; status: string; message: string; email?: string }> {
  const response = await fetch(`${API_BASE_URL}/api/cover-letter/send-email`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "邮件处理失败");
  }
  return response.json();
}
