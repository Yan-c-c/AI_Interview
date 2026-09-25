"use client";

import {
  BriefcaseBusiness,
  ChevronDown,
  CheckCircle2,
  CircleAlert,
  Download,
  FileText,
  Mail,
  RefreshCcw,
  Share2,
  ShieldAlert,
  X,
} from "lucide-react";
import type { CSSProperties, ReactNode } from "react";
import { useMemo, useState } from "react";
import {
  downloadResumeReportPdf,
  ResumeEvaluationReport as Report,
  shareResumeReportByEmail,
} from "@/lib/api/resumeEvaluation";
import { ForbiddenWordsPanel } from "./ForbiddenWordsPanel";
import { ResumeComparisonPanel } from "./ResumeComparisonPanel";
import { RoundTablePanel } from "./RoundTablePanel";
import { TemplateDuplicationPanel } from "./TemplateDuplicationPanel";

const basicFieldLabels: Record<string, string> = {
  name: "姓名",
  phone: "联系方式",
  email: "邮箱",
  target_position: "求职岗位",
  education: "教育背景",
  major: "专业",
  skills: "技能栈",
  projects: "项目经历",
  work_or_internship: "实习 / 工作经历",
  honors: "荣誉奖项 / 证书",
};

function badgeClass(level: string) {
  if (level === "高") return "badge danger";
  if (level === "中") return "badge warn";
  return "badge";
}

type TabKey =
  | "overview"
  | "roundtable"
  | "problems"
  | "risk"
  | "comparison";

const reportTabs: Array<{ key: TabKey; label: string; title: string; description: string }> = [
  { key: "overview", label: "总览", title: "总览", description: "核心摘要、Reflector 结论、优先修复任务、专项检测和圆桌摘要。" },
  { key: "roundtable", label: "圆桌会议", title: "多专家圆桌会议", description: "匹配分析师、内容优化师、HR、风险模板审查与 Reflector 意见。" },
  { key: "problems", label: "问题详情", title: "问题详情", description: "基础信息、内容质量、项目经历的详细证据、建议和参考写法。" },
  { key: "risk", label: "风险检测", title: "风险与模板检测", description: "合并展示风险词、夸大表达、模板化表达和个性化改写建议。" },
  { key: "comparison", label: "优化对比", title: "简历原文 / 优化内容对比", description: "对比原文与优化稿，并逐条选择是否采纳。" },
];

type ClueRecord = Record<string, unknown>;

function asRecords(value: unknown): ClueRecord[] {
  return Array.isArray(value) ? value.filter((item): item is ClueRecord => !!item && typeof item === "object" && !Array.isArray(item)) : [];
}

function getBasicFieldLabel(field: unknown) {
  const key = String(field || "");
  return basicFieldLabels[key] || key || "字段";
}

function priorityText(priority: string) {
  if (priority === "high") return "高优先级";
  if (priority === "medium") return "中优先级";
  if (priority === "low") return "低优先级";
  return priority || "待处理";
}

function clueText(item: ClueRecord) {
  return String(item.clue || item.tool_note || (item.present ? "可能存在" : "未发现明显线索"));
}

function firstText(items: unknown, fallback: string) {
  return Array.isArray(items) && items.length > 0 ? String(items[0]) : fallback;
}

function expertEntries(report: Report) {
  return [
    ["matching_analyst", "匹配分析师"],
    ["content_optimizer", "内容优化师"],
    ["hr_reviewer", "HR 审核官"],
    ["risk_template_reviewer", "风险模板审查"],
    ["reflector", "Reflector"],
  ].map(([key, fallback]) => {
    const expert = report.roundtable[key] || { role: fallback, findings: [], suggestions: [] };
    return {
      key,
      role: expert.role || fallback,
      primary: firstText(expert.findings || expert.prioritized_actions, "暂无摘要"),
      secondary: firstText(expert.suggestions, ""),
    };
  });
}

function CollapsibleReportSection({
  title,
  description,
  collapsed,
  onToggle,
  children,
}: {
  title: string;
  description: string;
  collapsed: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  return (
    <section className={`report-section collapsible-section ${collapsed ? "collapsed" : ""}`}>
      <button type="button" className="collapsible-header" onClick={onToggle} aria-expanded={!collapsed}>
        <div>
          <h2>{title}</h2>
          {!collapsed && <p>{description}</p>}
        </div>
        <span className="section-toggle">
          <ChevronDown size={18} />
          {collapsed ? "展开" : "收起"}
        </span>
      </button>
      {!collapsed && <div className="collapsible-content">{children}</div>}
    </section>
  );
}

export function ResumeEvaluationReport({ report }: { report: Report }) {
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [collapsedTabs, setCollapsedTabs] = useState<Record<TabKey, boolean>>({} as Record<TabKey, boolean>);
  const [shareOpen, setShareOpen] = useState(false);
  const [shareEmail, setShareEmail] = useState("");
  const [shareStatus, setShareStatus] = useState("");
  const [sharing, setSharing] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const problemCount = report.problems?.length || report.summary.main_problems.length;
  const topProblems = (report.problems || []).slice(0, 3);
  const topSuggestions = (report.optimization_suggestions || []).slice(0, 3);
  const score = Number(report.summary.overall_score || 0);
  const currentTab = reportTabs.find((tab) => tab.key === activeTab) || reportTabs[0];
  const toolFindings = report.tool_findings || {};
  const basicInfoClues = asRecords(toolFindings.basic_info_clues);
  const structureClues = asRecords(toolFindings.structure_clues);
  const hasExplicitTarget = report.summary.target_position_source === "resume_explicit" && !!report.summary.target_position && report.summary.target_position !== "未明确";
  const targetText = hasExplicitTarget ? report.summary.target_position : "未明确";
  const reflector = report.roundtable.reflector || {};
  const prioritizedActions = (reflector.prioritized_actions || report.summary.main_suggestions || []).slice(0, 3);
  const experts = expertEntries(report);
  const matchingExpert = report.roundtable.matching_analyst;

  async function handleDownload() {
    try {
      setDownloading(true);
      await downloadResumeReportPdf(report);
    } catch (error) {
      setShareStatus(error instanceof Error ? error.message : "PDF 导出失败");
    } finally {
      setDownloading(false);
    }
  }

  async function handleShare() {
    try {
      setSharing(true);
      setShareStatus("");
      const result = await shareResumeReportByEmail(report, shareEmail);
      setShareStatus(result.message || "报告已发送。");
    } catch (error) {
      setShareStatus(error instanceof Error ? error.message : "报告分享失败");
    } finally {
      setSharing(false);
    }
  }

  const tabContent = useMemo(() => {
    if (activeTab === "overview") {
      return (
        <div className="overview-stack">
          <section className="overview-band">
            <div className="section-heading compact">
              <div>
                <h2>核心摘要</h2>
                <p>四个最重要的投递判断信号。</p>
              </div>
            </div>
            <div className="core-summary-grid">
              <article className="summary-card score-summary">
                <span className="card-label">总体评分</span>
                <div className="score-ring" style={{ "--score": `${score}%` } as CSSProperties}>
                  <strong>{score}</strong>
                  <span>/100</span>
                </div>
                <strong>{score >= 85 ? "优秀" : score >= 75 ? "良好" : "待优化"}</strong>
              </article>

              <article className="summary-card risk-summary">
                <span className="card-label">风险等级</span>
                <strong className="large-risk">{report.summary.risk_level}</strong>
                <p>{report.summary.risk_level === "高" ? "存在较明显风险" : report.summary.risk_level === "中" ? "存在一定风险" : "风险较低"}</p>
              </article>

              <article className="summary-card target-summary">
                <span className="card-label">目标岗位匹配</span>
                <div className="target-title">
                  <BriefcaseBusiness size={20} />
                  <strong>{targetText}</strong>
                </div>
                <p>匹配度：{report.dimension_scores.skill_match || 0}/100</p>
                <span className="badge">{hasExplicitTarget ? "简历明确" : "未明确"}</span>
              </article>

              <article className="summary-card problem-summary">
                <span className="card-label">关键问题</span>
                <strong className="problem-count">{problemCount}</strong>
                <p>项需要优先处理</p>
                <button type="button" className="link-button" onClick={() => setActiveTab("problems")}>查看问题详情</button>
              </article>
            </div>
          </section>

          <section className="reflector-summary-card">
            <div className="section-heading compact">
              <div>
                <h2>Reflector 最终结论</h2>
                <p>一句总评 + 三条优先修改顺序。</p>
              </div>
            </div>
            <p className="reflector-judgement">{reflector.final_judgement || "Reflector 已完成整合，建议优先处理高风险问题与影响投递判断的核心表达。"}</p>
            <ol className="priority-order-list">
              {prioritizedActions.length > 0 ? prioritizedActions.map((item, index) => (
                <li key={`${item}-${index}`}>{item}</li>
              )) : (
                <>
                  <li>先补齐基础信息和求职方向。</li>
                  <li>再补充项目职责、技术动作和量化结果。</li>
                  <li>最后处理风险词和模板化表达。</li>
                </>
              )}
            </ol>
          </section>

          <section className="overview-section-card">
            <div className="section-heading compact">
              <div>
                <h2>优先修复任务</h2>
                <p>每条任务包含问题、建议和示例入口。</p>
              </div>
            </div>
            <div className="priority-task-grid">
              {(topProblems.length ? topProblems : report.summary.main_problems.slice(0, 3).map((item) => ({
                dimension: "简历问题",
                problem: item,
                evidence: "",
                suggestion: "",
                priority: "high",
              }))).slice(0, 3).map((item, index) => {
                const suggestion = topSuggestions[index];
                return (
                  <article className="priority-task-card" key={`${item.problem}-${index}`}>
                    <span className={item.priority === "high" ? "badge danger" : "badge warn"}>{priorityText(item.priority)}</span>
                    <strong>{item.problem}</strong>
                    <p>{item.suggestion || suggestion?.suggestion || "建议补充具体证据、职责动作和结果数据。"}</p>
                    <button type="button" className="link-button" onClick={() => setActiveTab("problems")}>
                      查看示例
                    </button>
                  </article>
                );
              })}
            </div>
          </section>

          <section className="overview-section-card">
            <div className="section-heading compact">
              <div>
                <h2>专项检测</h2>
                <p>风险表达、模板化和结构完整性概览。</p>
              </div>
            </div>
            <div className="special-check-grid">
              <article className="special-check-card forbidden">
                <ShieldAlert size={22} />
                <div>
                  <strong>{report.forbidden_words?.length || 0} 个</strong>
                  <p>风险表达检测</p>
                  <button type="button" className="link-button" onClick={() => setActiveTab("risk")}>查看详情</button>
                </div>
              </article>
              <article className="special-check-card template">
                <FileText size={22} />
                <div>
                  <strong>{report.template_duplication?.risk_level || "未知"}</strong>
                  <p>模板化检测 · {report.template_duplication?.score || 0}/100</p>
                  <button type="button" className="link-button" onClick={() => setActiveTab("risk")}>查看详情</button>
                </div>
              </article>
              <article className="special-check-card structure">
                <CheckCircle2 size={22} />
                <div>
                  <strong>{report.dimension_scores.structure || 0}/100</strong>
                  <p>结构完整性 · {structureClues.length} 条线索</p>
                  <button type="button" className="link-button" onClick={() => setActiveTab("problems")}>查看详情</button>
                </div>
              </article>
            </div>
          </section>

          <section className="overview-section-card">
            <div className="section-heading compact">
              <div>
                <h2>多专家圆桌摘要</h2>
                <p>五位专家的核心判断。</p>
              </div>
            </div>
            <div className="roundtable-summary-grid">
              {experts.map((expert) => (
                <article className="roundtable-summary-card" key={expert.key}>
                  <strong>{expert.role}</strong>
                  <p>{expert.primary}</p>
                  {expert.secondary && <small>{expert.secondary}</small>}
                </article>
              ))}
            </div>
          </section>
        </div>
      );
    }

    if (activeTab === "problems") {
      const detailProblems = report.problems || [];
      return (
        <div className="problem-detail-stack">
          <section className="overview-section-card">
            <div className="section-heading compact">
              <div>
                <h2>基础信息完整性</h2>
                <p>字段名称已统一使用中文，技能匹配信息合并在这里展示。</p>
              </div>
            </div>
            <div className="basic-summary-grid">
              <article className="basic-summary-card target-summary compact-target">
                <span className="card-label">求职岗位线索</span>
                <div className="target-title">
                  <BriefcaseBusiness size={20} />
                  <strong>{targetText}</strong>
                </div>
                <p>{hasExplicitTarget ? "岗位来自简历明确字段。" : "建议在简历顶部补充“求职意向”，避免 HR 误判方向。"}</p>
              </article>
              <article className="basic-summary-card">
                <span className="card-label">技能与岗位支撑</span>
                <strong>{report.dimension_scores.skill_match || 0}/100</strong>
                <p>技能匹配信息仅作为专家判断岗位支撑度的参考，不再单独展示章节。</p>
                {(matchingExpert?.findings || []).length > 0 && <small>{matchingExpert.findings?.slice(0, 2).join("；")}</small>}
              </article>
            </div>

            <div className="tool-clue-grid">
              {basicInfoClues.length > 0 ? basicInfoClues.map((item, index) => (
                <article className={`tool-clue-card ${item.present ? "present" : "missing"}`} key={`${String(item.field)}-${index}`}>
                  <strong>{getBasicFieldLabel(item.field)}</strong>
                  <span>{item.present ? "已发现线索" : "未发现明显线索"}</span>
                  <p>{clueText(item)}</p>
                </article>
              )) : (
                <article className="empty-section-note">
                  <strong>暂无基础信息线索</strong>
                  <p>后端未返回基础信息工具线索，请重新评估或检查文件解析结果。</p>
                </article>
              )}
            </div>
          </section>

          <section className="overview-section-card analysis-section">
            <div className="section-heading compact">
              <div>
                <h2>内容质量与项目经历</h2>
                <p>统一用“问题、证据、建议、参考写法”说明，不再左右分栏。</p>
              </div>
            </div>
            <div className="analysis-card-list">
              {detailProblems.length > 0 ? detailProblems.slice(0, 10).map((item, index) => {
                const suggestion = report.optimization_suggestions[index];
                return (
                  <article className="analysis-advice-card" key={`${item.problem}-${index}`}>
                    <div className="analysis-card-header">
                      <span className={item.priority === "high" ? "badge danger" : "badge warn"}>{priorityText(item.priority)}</span>
                      <strong>{item.dimension}：{item.problem}</strong>
                    </div>
                    <div className="advice-grid">
                      <div className="advice-block">
                        <span>证据</span>
                        <p>{item.evidence || "报告未返回具体证据。"}</p>
                      </div>
                      <div className="advice-block">
                        <span>建议</span>
                        <p>{item.suggestion || suggestion?.suggestion || "建议补充具体职责、技术动作和结果数据。"}</p>
                      </div>
                      <div className="advice-block example-block">
                        <span>参考写法</span>
                        <p>{suggestion?.example || "将笼统描述改为：负责某模块，使用某技术解决某问题，最终带来某项可量化结果。"}</p>
                      </div>
                    </div>
                  </article>
                );
              }) : (
                <article className="empty-section-note">
                  <strong>暂无明确问题</strong>
                  <p>可以查看圆桌会议，确认专家是否给出了其他维度建议。</p>
                </article>
              )}
            </div>
          </section>
        </div>
      );
    }
    if (activeTab === "risk") {
      return (
        <div className="risk-template-grid">
          <ForbiddenWordsPanel report={report} embedded />
          <TemplateDuplicationPanel report={report} embedded />
        </div>
      );
    }
    if (activeTab === "roundtable") return <RoundTablePanel report={report} embedded />;
    if (activeTab === "comparison") return <ResumeComparisonPanel report={report} embedded />;

    return null;
  }, [
    activeTab,
    basicInfoClues,
    experts,
    hasExplicitTarget,
    matchingExpert,
    problemCount,
    prioritizedActions,
    report,
    reflector,
    score,
    structureClues,
    targetText,
    topProblems,
    topSuggestions,
  ]);

  return (
    <div className="report-workspace">
      {!report.metadata.used_llm_roundtable && (
        <section className="panel">
          <div className="section-title">
            <CircleAlert size={18} />
            <h2>AI 圆桌会议暂时不可用</h2>
          </div>
          <p className="small muted" style={{ marginTop: 8 }}>
            当前展示的是基础检测线索，建议配置或检查 DeepSeek / OpenAI 兼容 API 后重新生成完整评估。
          </p>
        </section>
      )}

      <div className="report-toolbar">
        <div>
          <div className="report-title-row">
            <h2>简历评估报告</h2>
            <span className="analysis-badge done">已完成</span>
          </div>
          <p>DeepSeek 多专家圆桌会议完成 · Reflector 已整合</p>
        </div>
        <div className="toolbar-actions">
          <button type="button" className="outline-button" disabled={downloading} onClick={handleDownload}>
            <Download size={16} />{downloading ? "导出中..." : "下载报告"}
          </button>
          <button type="button" className="outline-button" onClick={() => setShareOpen(true)}>
            <Share2 size={16} />分享报告
          </button>
          <button type="button" className="outline-button" onClick={() => window.location.reload()}>
            <RefreshCcw size={16} />重新评估
          </button>
        </div>
      </div>

      <div className="report-tabs">
        {reportTabs.map((tab) => (
          <button
            type="button"
            className={tab.key === activeTab ? "active" : ""}
            aria-selected={tab.key === activeTab}
            onClick={() => setActiveTab(tab.key)}
            key={tab.key}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <CollapsibleReportSection
        title={currentTab.title}
        description={currentTab.description}
        collapsed={!!collapsedTabs[activeTab]}
        onToggle={() => setCollapsedTabs((state) => ({ ...state, [activeTab]: !state[activeTab] }))}
      >
        {tabContent}
      </CollapsibleReportSection>

      {shareOpen && (
        <div className="share-modal-backdrop" role="presentation">
          <section className="share-modal" role="dialog" aria-modal="true" aria-labelledby="share-report-title">
            <button
              type="button"
              className="share-close-button"
              aria-label="关闭分享窗口"
              onClick={() => {
                setShareOpen(false);
                setShareStatus("");
              }}
            >
              <X size={18} />
            </button>
            <div className="share-modal-title">
              <Mail size={22} />
              <div>
                <h3 id="share-report-title">分享简历评估报告</h3>
                <p>输入邮箱后，系统会把当前报告 PDF 作为附件发送过去。</p>
              </div>
            </div>
            <label className="share-email-field">
              <span>收件邮箱</span>
              <input
                type="email"
                value={shareEmail}
                placeholder="user@example.com"
                onChange={(event) => setShareEmail(event.target.value)}
              />
            </label>
            {shareStatus && <p className="share-status">{shareStatus}</p>}
            <div className="share-modal-actions">
              <button type="button" className="outline-button" onClick={() => setShareOpen(false)}>取消</button>
              <button type="button" className="primary-button" disabled={sharing || !shareEmail.trim()} onClick={handleShare}>
                {sharing ? "发送中..." : "发送 PDF"}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
