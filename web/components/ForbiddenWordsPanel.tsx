import { AlertTriangle } from "lucide-react";
import { ResumeEvaluationReport } from "@/lib/api/resumeEvaluation";

export function ForbiddenWordsPanel({ report, embedded = false }: { report: ResumeEvaluationReport; embedded?: boolean }) {
  const items = report.forbidden_words || [];
  const content = (
    <>
      {!embedded && (
      <div className="section-title">
        <AlertTriangle size={18} />
        <h2>违禁词 / 风险词</h2>
      </div>
      )}
      <div className="table-like" style={{ marginTop: 12 }}>
        {items.length === 0 ? (
          <p className="small muted">未发现需要展示的风险词结论。</p>
        ) : (
          items.map((item, index) => (
            <div className="risk-row" key={`${item.word}-${index}`}>
              <strong>{item.word}</strong>
              <span className="badge warn">{item.risk_type}</span>
              <div>
                <p className="small">{item.context}</p>
                <p className="small muted">{item.ai_judgement}</p>
                <p className="small">{item.suggestion}</p>
              </div>
            </div>
          ))
        )}
      </div>
    </>
  );

  if (embedded) return content;

  return (
    <section className="panel">
      {content}
    </section>
  );
}
