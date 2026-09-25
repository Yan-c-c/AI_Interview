"use client";

import type { CSSProperties } from "react";
import {
  Bot,
  Check,
  Circle,
  ClipboardCheck,
  FileSearch,
  ShieldAlert,
  Sparkles,
  UserCheck,
  UsersRound,
} from "lucide-react";
import { EvaluationStreamEvent } from "@/lib/api/assistant";

export type ExpertKey =
  | "matching_analyst"
  | "content_optimizer"
  | "hr_reviewer"
  | "risk_template_reviewer"
  | "reflector";

export type StepStatus = "pending" | "running" | "done" | "error";
export type ProgressStepKey = "file" | "tools" | "roundtable" | "reflector" | "report";
export type ProgressSteps = Record<ProgressStepKey, StepStatus>;

export interface ExpertState {
  key: ExpertKey;
  role: string;
  subtitle: string;
  status: StepStatus;
  message: string;
  findings: string[];
  accent: "blue" | "green" | "orange" | "red" | "purple";
}

const iconMap = {
  matching_analyst: FileSearch,
  content_optimizer: Sparkles,
  hr_reviewer: UserCheck,
  risk_template_reviewer: ShieldAlert,
  reflector: ClipboardCheck,
};

const steps = [
  { key: "file", label: "解析简历文件" },
  { key: "tools", label: "提取初步线索" },
  { key: "roundtable", label: "多专家圆桌会议" },
  { key: "reflector", label: "Reflector 质量审核" },
  { key: "report", label: "生成评估报告" },
] satisfies Array<{ key: ProgressStepKey; label: string }>;

export const sidebarStepLabels: Record<ProgressStepKey, string> = {
  file: "解析简历文件",
  tools: "提取初步线索（工具检测）",
  roundtable: "启动圆桌会议（多专家协作）",
  reflector: "Reflector 质量审核",
  report: "生成评估报告",
};

export function createInitialProgressSteps(): ProgressSteps {
  return {
    file: "pending",
    tools: "pending",
    roundtable: "pending",
    reflector: "pending",
    report: "pending",
  };
}

export function updateProgressSteps(current: ProgressSteps, event: EvaluationStreamEvent): ProgressSteps {
  const next = { ...current };

  if (event.type === "progress") {
    if (event.stage === "file") next.file = event.status === "error" ? "error" : "done";
    if (event.stage === "tools") next.tools = event.status === "done" ? "done" : event.status === "error" ? "error" : "running";
    if (event.stage === "roundtable") next.roundtable = event.status === "done" ? "done" : event.status === "error" ? "error" : "running";
    if (event.stage === "report") {
      next.file = "done";
      next.tools = "done";
      next.roundtable = "done";
      next.reflector = "done";
      next.report = event.status === "done" ? "done" : event.status === "error" ? "error" : "running";
    }
  }

  if (event.type === "expert_status") {
    if (event.stage === "roundtable") {
      next.file = next.file === "pending" ? "done" : next.file;
      next.tools = next.tools === "pending" ? "done" : next.tools;
      if (next.roundtable !== "done") next.roundtable = event.status === "error" ? "running" : "running";
    }
    if (event.stage === "reflector") {
      next.file = "done";
      next.tools = "done";
      next.roundtable = "done";
      next.reflector = event.status === "done" ? "done" : event.status === "error" ? "error" : "running";
    }
  }

  if (event.type === "result") {
    if (event.success) {
      return {
        file: "done",
        tools: "done",
        roundtable: "done",
        reflector: "done",
        report: "done",
      };
    }
    next.report = "error";
  }

  return next;
}

export function progressFromSteps(stepStatuses: ProgressSteps): number {
  const order: ProgressStepKey[] = ["file", "tools", "roundtable", "reflector", "report"];
  const doneCount = order.filter((key) => stepStatuses[key] === "done").length;
  const runningCount = order.some((key) => stepStatuses[key] === "running") ? 0.5 : 0;
  return Math.min(100, Math.round((doneCount + runningCount) * 20));
}

function statusLabel(status: ExpertState["status"]) {
  if (status === "done") return "已完成";
  if (status === "running") return "思考中";
  if (status === "error") return "不可用";
  return "等待中";
}

export function createInitialExperts(): Record<ExpertKey, ExpertState> {
  return {
    matching_analyst: {
      key: "matching_analyst",
      role: "匹配分析师",
      subtitle: "岗位匹配度专家",
      status: "pending",
      message: "等待分析技能、项目与岗位相关性。",
      findings: [],
      accent: "blue",
    },
    content_optimizer: {
      key: "content_optimizer",
      role: "内容优化师",
      subtitle: "内容表达优化专家",
      status: "pending",
      message: "等待分析表达质量、量化程度和逻辑结构。",
      findings: [],
      accent: "green",
    },
    hr_reviewer: {
      key: "hr_reviewer",
      role: "HR 审核官",
      subtitle: "HR 初筛专家",
      status: "pending",
      message: "等待从初筛视角判断可信度与通过率。",
      findings: [],
      accent: "orange",
    },
    risk_template_reviewer: {
      key: "risk_template_reviewer",
      role: "风险与模板审查",
      subtitle: "风险及模板审查专家",
      status: "pending",
      message: "等待审查风险词、模板化表达和低区分度内容。",
      findings: [],
      accent: "red",
    },
    reflector: {
      key: "reflector",
      role: "Reflector 审核",
      subtitle: "质量审核专家",
      status: "pending",
      message: "等待整合专家意见并形成最终建议。",
      findings: [],
      accent: "purple",
    },
  };
}

export function updateExpertState(
  experts: Record<ExpertKey, ExpertState>,
  event: EvaluationStreamEvent,
): Record<ExpertKey, ExpertState> {
  if (event.type !== "expert_status" || !event.expert || !(event.expert in experts)) return experts;
  const key = event.expert as ExpertKey;
  const result = event.result as {
    findings?: string[];
    suggestions?: string[];
    final_judgement?: string;
    prioritized_actions?: string[];
  } | undefined;
  const findings =
    result?.findings?.slice(0, 4)
    || result?.prioritized_actions?.slice(0, 4)
    || (result?.final_judgement ? [result.final_judgement] : undefined)
    || result?.suggestions?.slice(0, 4)
    || experts[key].findings;
  return {
    ...experts,
    [key]: {
      ...experts[key],
      status: (event.status as ExpertState["status"]) || experts[key].status,
      message: event.message || experts[key].message,
      findings,
    },
  };
}

export function EvaluationProgress({
  experts,
  events,
  stepStatuses,
  onAbort,
}: {
  experts: Record<ExpertKey, ExpertState>;
  events: EvaluationStreamEvent[];
  stepStatuses: ProgressSteps;
  onAbort?: () => void;
}) {
  const progress = progressFromSteps(stepStatuses);

  return (
    <div className="meeting-view">
      <div className="meeting-header">
        <div>
          <div className="eyebrow-row">
            <UsersRound size={18} />
            <span>圆桌会议进行中</span>
          </div>
          <h2>简历评估 - 多专家协同诊断</h2>
          <p>5 位专家正在从不同维度分析你的简历，完成后生成结构化报告与优化对比。</p>
        </div>
        <div className="meeting-actions">
          <span className="analysis-badge">分析中</span>
          {onAbort && (
            <button type="button" className="outline-button danger-text" onClick={onAbort}>
              终止当前结果
            </button>
          )}
        </div>
      </div>

      <div className="stage-stepper">
        {steps.map((step) => {
          const status = stepStatuses[step.key];
          return (
            <div className={`stage-step ${status}`} key={step.key}>
              <div className="stage-dot">{status === "done" ? <Check size={16} /> : <Circle size={12} />}</div>
              <span>{step.label}</span>
            </div>
          );
        })}
      </div>

      <div className="expert-meeting-grid">
        {Object.values(experts).map((expert) => {
          const Icon = iconMap[expert.key];
          return (
            <article className={`meeting-card ${expert.accent}`} key={expert.key}>
              <div className="meeting-card-head">
                <div className="expert-avatar">
                  <Icon size={22} />
                </div>
                <div>
                  <h3>{expert.role}</h3>
                  <p>{expert.subtitle}</p>
                </div>
                <span className={`status-pill ${expert.status}`}>{statusLabel(expert.status)}</span>
              </div>
              <div className="expert-message">{expert.message}</div>
              <div className="expert-findings">
                <strong>已发现要点</strong>
                {expert.findings.length > 0 ? (
                  <ul>
                    {expert.findings.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                ) : expert.status === "running" ? (
                  <p>专家正在输入中...</p>
                ) : expert.status === "done" ? (
                  <p>该专家已完成诊断，等待 Reflector 汇总。</p>
                ) : expert.status === "error" ? (
                  <p>该专家节点暂时不可用。</p>
                ) : (
                  <p>等待进入分析队列。</p>
                )}
              </div>
              {expert.status === "running" && (
                <div className="typing-row">
                  <span>专家正在输入中</span>
                  <i />
                  <i />
                  <i />
                </div>
              )}
              {expert.status === "done" && <div className="typing-row done"><span>专家已完成诊断</span></div>}
              {expert.status === "error" && <div className="typing-row error"><span>专家暂时不可用</span></div>}
            </article>
          );
        })}
      </div>

      <div className="meeting-bottom-grid">
        <section className="meeting-panel">
          <h3>当前会议要点</h3>
          <ul className="meeting-log">
            {events.slice(-6).map((event, index) => (
              <li key={`${event.stage}-${index}`}>
                <Bot size={14} />
                <span>{event.message || `${event.stage || "系统"} 状态更新`}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="meeting-panel progress-panel">
          <h3>会议进度</h3>
          <div className="progress-ring" style={{ "--progress": `${progress}%` } as CSSProperties}>
            <span>{progress}%</span>
          </div>
          <ol>
            {steps.map((step) => (
              <li className={stepStatuses[step.key]} key={step.key}>{step.label}</li>
            ))}
          </ol>
        </section>
        <section className="meeting-panel control-panel">
          <h3>会议控制</h3>
          <button type="button" className="outline-button">查看初步线索</button>
          <button type="button" className="outline-button">暂停会议（稍后继续）</button>
          <button type="button" className="outline-button danger-text" onClick={onAbort}>终止并生成当前结果</button>
        </section>
      </div>
    </div>
  );
}
