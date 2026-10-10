import { API_BASE_URL } from "./resumeEvaluation";

export interface InterviewQuestionItem {
  id: string;
  category: string;
  difficulty: "easy" | "medium" | "hard" | string;
  question: string;
  why_ask: string;
  answer_points: string[];
  follow_ups: string[];
  source_type: "lightrag" | "system_generated" | string;
  source_refs: string[];
  related_resume_evidence: string;
}

export interface InterviewQuestionReport {
  agent: "interview_question_generation_agent" | string;
  task_type: "interview_question_generation" | string;
  success: boolean;
  summary: {
    target_position: string;
    target_position_source: string;
    question_count: number;
    difficulty_mix: Record<string, number>;
    used_lightrag: boolean;
    source_note: string;
  };
  resume_profile: {
    target_position: string;
    target_position_source: string;
    skills: string[];
    projects: Array<{
      name: string;
      description?: string;
      tech_stack?: string[];
      keywords?: string[];
    }>;
    internships: Array<{
      company: string;
      role: string;
      keywords?: string[];
    }>;
    education?: string;
    keywords: string[];
    retrieval_queries: string[];
  };
  retrieval: {
    used_lightrag: boolean;
    status: string;
    queries: string[];
    sources: Array<{
      reference_id: string;
      title: string;
      source: string;
      snippet: string;
    }>;
    errors: string[];
  };
  question_sets: Record<string, InterviewQuestionItem[]>;
  questions: InterviewQuestionItem[];
  practice_plan: string[];
  metadata: {
    filename: string;
    parsed_char_count: number;
    used_llm_profile: boolean;
    used_llm_generation: boolean;
    used_lightrag: boolean;
    lightrag_base_url: string;
    llm_errors?: string[];
  };
}

export interface MockInterviewScenario {
  position: string;
  difficulty: "基础" | "中等" | "进阶" | string;
  mode: "技术一面" | "项目深挖" | "HR 面" | "压力面" | "综合模拟" | string;
  answerMode: "text" | "voice";
}

export interface MockInterviewQA {
  question_id: string;
  questionId?: string;
  question: string;
  questionText?: string;
  category: string;
  answer: string;
  answerText?: string;
  index?: number;
  empty?: boolean;
  feedback?: string;
  follow_up?: string;
}

export interface MockInterviewReport {
  overall_score: number;
  dimension_scores: {
    expression: number;
    technical_accuracy: number;
    project_depth: number;
    answer_completeness: number;
  };
  summary: string;
  strengths: string[];
  problems: string[];
  suggestions: string[];
  review_directions: string[];
  next_practice: string;
}

export async function generateInterviewQuestions(params: {
  message: string;
  file_id?: string;
}): Promise<{ success: boolean; agent: string; result: InterviewQuestionReport; message?: string }> {
  const response = await fetch(`${API_BASE_URL}/api/interview-question/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "面试题生成失败");
  }
  return response.json();
}

export async function generateInterviewFollowUp(params: {
  question: string;
  answer: string;
  resume_profile: InterviewQuestionReport["resume_profile"];
  scenario: MockInterviewScenario;
  interview_status?: "idle" | "in_progress" | "completed";
}): Promise<{ success: boolean; feedback: string; follow_up: string; answer_status: string; fallback?: boolean }> {
  if (params.interview_status === "completed") {
    return { success: false, feedback: "", follow_up: "", answer_status: "completed" };
  }
  const response = await fetch(`${API_BASE_URL}/api/interview-question/follow-up`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "追问生成失败");
  }
  return response.json();
}

export async function generateMockInterviewReport(params: {
  resume_profile: InterviewQuestionReport["resume_profile"];
  scenario: MockInterviewScenario;
  qa_history: MockInterviewQA[];
}): Promise<{ success: boolean; report: MockInterviewReport; fallback?: boolean }> {
  const response = await fetch(`${API_BASE_URL}/api/interview-question/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || error.message || "面试报告生成失败");
  }
  return response.json();
}
