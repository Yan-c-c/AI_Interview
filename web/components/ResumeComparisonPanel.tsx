"use client";

import { useMemo, useState } from "react";
import { Check, FileText, RotateCcw } from "lucide-react";
import { ResumeEvaluationReport } from "@/lib/api/resumeEvaluation";

export function ResumeComparisonPanel({ report, embedded = false }: { report: ResumeEvaluationReport; embedded?: boolean }) {
  const changes = report.resume_comparison?.changes || [];
  const [accepted, setAccepted] = useState<Record<string, boolean>>({});

  const acceptedCount = useMemo(() => Object.values(accepted).filter(Boolean).length, [accepted]);

  if (!report.resume_comparison) {
    return null;
  }

  const content = (
    <>
      <div className="section-heading">
        <div>
          {!embedded && <h2>简历原文 / 优化内容对比</h2>}
          <p>逐条审核 AI 修改建议，选择是否采纳。本阶段采纳状态保存在当前页面，用于后续接入导出。</p>
        </div>
        <span className="analysis-badge done">已采纳 {acceptedCount}/{changes.length}</span>
      </div>

      <div className="compare-grid">
        <article className="resume-paper">
          <div className="paper-title">
            <FileText size={16} />
            <strong>简历原文</strong>
          </div>
          <pre>{report.resume_comparison.original_resume || "暂无原文"}</pre>
        </article>
        <article className="resume-paper optimized">
          <div className="paper-title">
            <FileText size={16} />
            <strong>优化后内容</strong>
          </div>
          <pre>{report.resume_comparison.optimized_resume || "等待 AI 生成优化稿"}</pre>
        </article>
      </div>

      <div className="change-list">
        {changes.length === 0 ? (
          <p className="small muted">本次报告未返回逐条改写建议。</p>
        ) : (
          changes.map((change, index) => {
            const id = change.id || `change-${index}`;
            const isAccepted = accepted[id];
            return (
              <article className={`change-card ${isAccepted ? "accepted" : ""}`} key={id}>
                <div className="change-head">
                  <div>
                    <span className="change-section">{change.section}</span>
                    <strong>{change.reason}</strong>
                  </div>
                  <button
                    type="button"
                    className={isAccepted ? "outline-button" : "primary-button small-button"}
                    onClick={() => setAccepted((state) => ({ ...state, [id]: !state[id] }))}
                  >
                    {isAccepted ? <RotateCcw size={14} /> : <Check size={14} />}
                    {isAccepted ? "撤销采纳" : "采纳修改"}
                  </button>
                </div>
                <div className="change-diff">
                  <div>
                    <span>原文</span>
                    <p>{change.original_text}</p>
                  </div>
                  <div>
                    <span>优化后</span>
                    <p>{change.optimized_text}</p>
                  </div>
                </div>
                {change.risk_note && <p className="risk-note">{change.risk_note}</p>}
              </article>
            );
          })
        )}
      </div>
    </>
  );

  if (embedded) return content;

  return (
    <section className="report-section comparison-section">
      {content}
    </section>
  );
}
