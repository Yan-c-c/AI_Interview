import { API_BASE_URL } from "./resumeEvaluation";

export interface CareerPlanningReport {
  agent: "career_planning_agent" | string;
  task_type: "career_planning" | string;
  success: boolean;
  needs_more_info: boolean;
  missing_fields: string[];
  career_profile: {
    current_stage: string;
    target_direction: string;
    recommended_positions: string[];
    current_strengths: string[];
    main_gaps: string[];
  };
  matching_analysis: {
    target_position: string;
    match_score: number;
    matched_skills: string[];
    missing_skills: string[];
    risk_points: string[];
  };
  career_plan: {
    short_term: string[];
    mid_term: string[];
    long_term: string[];
  };
  learning_path: {
    one_week: string[];
    one_month: string[];
    three_months: string[];
    six_months: string[];
  };
  project_suggestions: string[];
  job_search_strategy: string[];
  next_actions: string[];
  metadata: {
    history_id: string;
    filename: string;
    parsed_char_count: number;
    used_deepseek: boolean;
    note?: string;
    llm_errors?: string[];
  };
}

export async function generateCareerPlan(params: {
  message: string;
  file_id?: string;
  current_identity?: string;
  target_direction?: string;
  current_stage?: string;
  expected_city?: string;
  expected_industry?: string;
  expected_salary?: string;
  available_time?: string;
  confusion?: string;
  personal_background?: string;
}): Promise<{ success: boolean; agent: string; result: CareerPlanningReport; message?: string }> {
  const response = await fetch(`${API_BASE_URL}/api/career-planning/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "职业规划生成失败");
  }
  return response.json();
}

export async function rewriteCareerPlan(report: CareerPlanningReport, instruction: string): Promise<CareerPlanningReport> {
  const response = await fetch(`${API_BASE_URL}/api/career-planning/rewrite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report, instruction }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "职业规划调整失败");
  }
  const data = await response.json();
  return data.result;
}

export async function exportCareerPlan(report: CareerPlanningReport, format: "md" | "docx" | "pdf") {
  const response = await fetch(`${API_BASE_URL}/api/career-planning/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report, format, filename: `职业规划报告.${format}` }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "职业规划导出失败");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `职业规划报告.${format}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
