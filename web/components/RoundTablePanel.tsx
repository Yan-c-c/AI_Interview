import { UsersRound } from "lucide-react";
import { ResumeEvaluationReport } from "@/lib/api/resumeEvaluation";

const order = [
  "matching_analyst",
  "content_optimizer",
  "hr_reviewer",
  "risk_template_reviewer",
  "reflector",
];

export function RoundTablePanel({ report, embedded = false }: { report: ResumeEvaluationReport; embedded?: boolean }) {
  const content = (
    <>
      {!embedded && (
      <div className="section-title">
        <UsersRound size={18} />
        <h2>多专家圆桌会议</h2>
      </div>
      )}
      <div className="expert-grid" style={{ marginTop: 12 }}>
        {order.map((key) => {
          const expert = report.roundtable[key];
          if (!expert) return null;
          return (
            <article className="expert-card" key={key}>
              <h3>{expert.role}</h3>
              {expert.final_judgement && <p className="small muted" style={{ marginTop: 8 }}>{expert.final_judgement}</p>}
              {expert.findings && expert.findings.length > 0 && (
                <ul className="list">
                  {expert.findings.slice(0, 5).map((item, index) => <li key={index}>{item}</li>)}
                </ul>
              )}
              {expert.suggestions && expert.suggestions.length > 0 && (
                <p className="small muted" style={{ marginTop: 8 }}>{expert.suggestions.slice(0, 2).join("；")}</p>
              )}
              {expert.prioritized_actions && expert.prioritized_actions.length > 0 && (
                <ul className="list">
                  {expert.prioritized_actions.slice(0, 5).map((item, index) => <li key={index}>{item}</li>)}
                </ul>
              )}
            </article>
          );
        })}
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
