import { API_BASE_URL } from "./resumeEvaluation";

export interface SalaryProfile {
  job_title: string;
  experience_level: string;
  years_experience: number;
  country: string;
  city?: string;
  company_size: string;
  industry: string;
  employment_type: string;
  remote_ratio: number;
  education_required: string;
  skills: string[];
  current_offer?: number | null;
  expected_salary?: number | null;
}

export interface SalaryExplainability {
  available: boolean;
  method: string;
  top_features: Array<{ feature: string; feature_raw: string; importance: number }>;
  narrative: string[];
}

export interface SalaryNegotiationReport {
  agent: "salary_negotiation_agent" | string;
  task_type: "salary_negotiation" | string;
  success: boolean;
  profile: SalaryProfile;
  prediction: {
    available: boolean;
    model_available: boolean;
    source: string;
    message: string;
    salary: string;
    salary_raw: number;
    salary_low: string;
    salary_high: string;
    salary_low_raw: number;
    salary_high_raw: number;
    confidence_interval: number[];
    offer_gap_percent?: number | null;
    skill_note: string[];
    explanation: SalaryExplainability;
  };
  trend: {
    available: boolean;
    message: string;
    months: string[];
    actual: Array<number | null>;
    predicted: Array<number | null>;
    type: string[];
    upper_bound: Array<number | null>;
    lower_bound: Array<number | null>;
    metrics: { rmse: number; mae: number; mape: number };
    forecast_summary: Array<{ month: string; salary: number }>;
  };
  benchmarks: {
    country_benchmarks: Record<string, number>;
    job_categories: Array<{ category: string; count: number; mean: number; median: number; q25: number; q75: number }>;
    top_countries: Array<{ country: string; salary: number }>;
  };
  explainability: SalaryExplainability;
  simulation: SalarySimulationResult;
  strategy: SalaryStrategy;
  metadata: Record<string, unknown>;
}

export interface SalarySimulationResult {
  success: boolean;
  rl_available: boolean;
  status: string;
  message: string;
  rounds: Array<{
    round: number;
    action: string;
    advice: string;
    candidate_offer: number;
    hr_offer: number;
    final_salary: number;
    done: boolean;
    hr_feedback?: string;
  }>;
  final_salary: number;
  market_salary: number;
  vs_market: number;
  hr_budget: number;
  result_text: string;
}

export interface SalaryStrategy {
  reasonable_range: string;
  target_salary: number;
  minimum_acceptable_salary: number;
  offer_decision: string;
  negotiation_strategy: string[];
  talking_scripts: string[];
  hr_pushback_responses: string[];
  risk_alerts: string[];
  final_report: string;
  used_deepseek: boolean;
  llm_error?: string;
}

async function parseResponse<T>(response: Response, fallback: string): Promise<T> {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail?.message || data.message || fallback);
  }
  return data;
}

export async function analyzeSalaryNegotiation(params: Partial<SalaryProfile> & { message?: string; file_id?: string }): Promise<SalaryNegotiationReport> {
  const response = await fetch(`${API_BASE_URL}/api/salary-negotiation/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: "帮我分析 offer 并生成谈薪策略", ...params }),
  });
  const data = await parseResponse<{ result: SalaryNegotiationReport }>(response, "薪资分析失败");
  return data.result;
}

export async function generateSalaryStrategy(params: {
  profile: SalaryProfile;
  prediction: SalaryNegotiationReport["prediction"];
  trend: SalaryNegotiationReport["trend"];
  simulation: SalarySimulationResult;
  message?: string;
}): Promise<SalaryStrategy> {
  const response = await fetch(`${API_BASE_URL}/api/salary-negotiation/generate-strategy`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  const data = await parseResponse<{ result: { strategy: SalaryStrategy } }>(response, "谈薪策略生成失败");
  return data.result.strategy;
}

export async function simulateSalaryNegotiation(params: { market_salary: number; exp_level: number; company_size: number }): Promise<SalarySimulationResult> {
  const response = await fetch(`${API_BASE_URL}/api/salary-negotiation/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  const data = await parseResponse<{ result: { simulation: SalarySimulationResult } }>(response, "谈判模拟失败");
  return data.result.simulation;
}

export async function exportSalaryNegotiationReport(report: SalaryNegotiationReport, format: "md" | "docx" | "pdf") {
  const response = await fetch(`${API_BASE_URL}/api/salary-negotiation/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report, format, filename: `薪资谈判报告.${format}` }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "薪资谈判报告导出失败");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `薪资谈判报告.${format}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
