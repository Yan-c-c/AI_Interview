export type RiskLevel = "低" | "中" | "高" | "未知" | string;

export interface ResumeEvaluationReport {
  agent: string;
  task_type: string;
  success: boolean;
  summary: {
    overall_score: number;
    risk_level: RiskLevel;
    target_position: string;
    target_position_source: string;
    main_problems: string[];
    main_suggestions: string[];
  };
  dimension_scores: Record<string, number>;
  tool_findings: Record<string, unknown>;
  roundtable: Record<string, {
    role: string;
    findings?: string[];
    suggestions?: string[];
    final_judgement?: string;
    prioritized_actions?: string[];
  }>;
  forbidden_words: Array<{
    word: string;
    risk_type: string;
    context: string;
    ai_judgement: string;
    suggestion: string;
  }>;
  template_duplication: {
    risk_level: RiskLevel;
    score: number;
    reasons: unknown[];
    ai_judgement: string;
    suggestions: string[];
  };
  problems: Array<{
    dimension: string;
    problem: string;
    evidence: string;
    suggestion: string;
    priority: "high" | "medium" | "low" | string;
  }>;
  optimization_suggestions: Array<{
    priority: "high" | "medium" | "low" | string;
    suggestion: string;
    example: string;
  }>;
  resume_comparison?: {
    original_resume: string;
    optimized_resume: string;
    changes: Array<{
      id: string;
      section: string;
      original_text: string;
      optimized_text: string;
      reason: string;
      risk_note?: string;
      priority: "high" | "medium" | "low" | string;
    }>;
  };
  metadata: {
    filename: string;
    parsed_char_count: number;
    used_llm_roundtable: boolean;
    used_tool_clues: boolean;
    used_forbidden_word_tool: boolean;
    used_template_duplication_tool: boolean;
    llm_errors?: string[];
  };
}

export const API_BASE_URL = resolveApiBaseUrl();

function resolveApiBaseUrl() {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined") {
    const host = window.location.hostname || "127.0.0.1";
    return `${window.location.protocol}//${host}:8000`;
  }
  return "http://127.0.0.1:8000";
}

export async function evaluateResume(params: {
  message: string;
  file_id?: string;
}): Promise<{ success: boolean; agent: string; result: ResumeEvaluationReport }> {
  const response = await fetch(`${API_BASE_URL}/api/resume/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "简历评估失败");
  }
  return response.json();
}

function reportFilename(report: ResumeEvaluationReport) {
  const source = report.metadata?.filename?.replace(/\.[^.]+$/, "") || "简历评估报告";
  return `${source}-简历评估报告.pdf`;
}

export async function downloadResumeReportPdf(report: ResumeEvaluationReport): Promise<void> {
  const filename = reportFilename(report);
  const response = await fetch(`${API_BASE_URL}/api/resume/report/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report, filename }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "PDF 导出失败");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function shareResumeReportByEmail(report: ResumeEvaluationReport, email: string): Promise<{ success: boolean; message: string; email: string }> {
  const response = await fetch(`${API_BASE_URL}/api/resume/report/share`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report, email, filename: reportFilename(report) }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "报告分享失败");
  }
  return response.json();
}
