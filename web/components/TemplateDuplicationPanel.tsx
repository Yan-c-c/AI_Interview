import { CopyCheck } from "lucide-react";
import { ResumeEvaluationReport } from "@/lib/api/resumeEvaluation";

export function TemplateDuplicationPanel({ report, embedded = false }: { report: ResumeEvaluationReport; embedded?: boolean }) {
  const template = report.template_duplication;
  const content = (
    <>
      {!embedded && (
      <div className="section-title">
        <CopyCheck size={18} />
        <h2>模板查重 / 模板化表达</h2>
      </div>
      )}
      <div className="score-row">
        <span>模板重复风险</span>
        <span className="badge warn">{template.risk_level}</span>
      </div>
      <div className="score-row">
        <span>模板重复评分</span>
        <strong>{template.score}</strong>
      </div>
      <p className="small muted" style={{ marginTop: 10 }}>{template.ai_judgement}</p>
      {template.suggestions?.length > 0 && (
        <ul className="list">
          {template.suggestions.map((item, index) => <li key={index}>{item}</li>)}
        </ul>
      )}
    </>
  );

  if (embedded) return content;

  return (
    <section className="panel">
      {content}
    </section>
  );
}
