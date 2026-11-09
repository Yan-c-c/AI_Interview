"use client";

import { useMemo, useState } from "react";
import type { ComponentType, ReactNode } from "react";
import {
  Activity,
  BarChart3,
  Bot,
  BriefcaseBusiness,
  ChevronRight,
  Download,
  Gauge,
  LineChart,
  MessageSquareText,
  Play,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";
import {
  analyzeSalaryNegotiation,
  exportSalaryNegotiationReport,
  generateSalaryStrategy,
  SalaryNegotiationReport,
  simulateSalaryNegotiation,
} from "@/lib/api/salaryNegotiation";

type TabKey = "predict" | "trend" | "category" | "negotiate" | "advisor" | "explain";

const countryOptions = ["UNITED STATES", "CHINA", "SINGAPORE", "GERMANY", "UNITED KINGDOM", "CANADA", "SWITZERLAND", "INDIA"];
const skillOptions = ["Python", "SQL", "TensorFlow", "PyTorch", "Java", "MLOps", "NLP", "Deep Learning", "Spark", "Docker", "AWS", "Kubernetes"];

function money(value?: number | null) {
  if (!value) return "—";
  return `$${Math.round(value).toLocaleString()}`;
}

function expToNumber(exp: string) {
  return { EN: 0, MI: 1, SE: 2, EX: 3 }[exp as "EN" | "MI" | "SE" | "EX"] ?? 1;
}

function sizeToNumber(size: string) {
  return { S: 0, M: 1, L: 2 }[size as "S" | "M" | "L"] ?? 1;
}

export function SalaryNegotiationPanel({ report, fileId, onUpdated }: { report: SalaryNegotiationReport; fileId?: string; onUpdated: (report: SalaryNegotiationReport) => void }) {
  const [activeTab, setActiveTab] = useState<TabKey>("predict");
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [form, setForm] = useState({
    job_title: report.profile.job_title || "AI Engineer",
    experience_level: report.profile.experience_level || "MI",
    years_experience: report.profile.years_experience || 3,
    country: report.profile.country || "UNITED STATES",
    city: report.profile.city || "",
    company_size: report.profile.company_size || "M",
    industry: report.profile.industry || "Technology",
    employment_type: report.profile.employment_type || "FT",
    remote_ratio: report.profile.remote_ratio || 50,
    education_required: report.profile.education_required || "Bachelor",
    skills: report.profile.skills?.length ? report.profile.skills : ["Python", "SQL", "Machine Learning"],
    current_offer: report.profile.current_offer || 0,
    expected_salary: report.profile.expected_salary || 0,
  });

  const topFeatureTotal = useMemo(() => {
    const total = report.explainability?.top_features?.slice(0, 8).reduce((sum, item) => sum + item.importance, 0) || 1;
    return total || 1;
  }, [report.explainability?.top_features]);

  async function refreshAnalysis() {
    setLoading(true);
    setNotice("正在重新预测薪资区间并生成谈薪策略...");
    try {
      const next = await analyzeSalaryNegotiation({ ...form, file_id: fileId, current_offer: form.current_offer || undefined, expected_salary: form.expected_salary || undefined });
      onUpdated(next);
      setNotice("薪资预测和谈薪策略已更新。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "薪资分析失败");
    } finally {
      setLoading(false);
    }
  }

  async function rerunSimulation() {
    setLoading(true);
    setNotice("正在执行谈判模拟...");
    try {
      const simulation = await simulateSalaryNegotiation({
        market_salary: report.prediction.salary_raw,
        exp_level: expToNumber(form.experience_level),
        company_size: sizeToNumber(form.company_size),
      });
      onUpdated({ ...report, simulation, metadata: { ...report.metadata, used_rl_simulation: simulation.rl_available } });
      setActiveTab("negotiate");
      setNotice(simulation.message);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "谈判模拟失败");
    } finally {
      setLoading(false);
    }
  }

  async function rerunStrategy() {
    setLoading(true);
    setNotice("正在调用 DeepSeek 生成个性化谈薪话术...");
    try {
      const strategy = await generateSalaryStrategy({
        profile: report.profile,
        prediction: report.prediction,
        trend: report.trend,
        simulation: report.simulation,
        message: "请结合当前 offer 和预测区间，生成更适合面试沟通的谈薪策略。",
      });
      onUpdated({ ...report, strategy, metadata: { ...report.metadata, used_deepseek: strategy.used_deepseek } });
      setActiveTab("advisor");
      setNotice(strategy.used_deepseek ? "DeepSeek 谈薪策略已更新。" : "DeepSeek 暂不可用，已返回降级策略。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "谈薪策略生成失败");
    } finally {
      setLoading(false);
    }
  }

  function toggleSkill(skill: string) {
    setForm((current) => ({
      ...current,
      skills: current.skills.includes(skill) ? current.skills.filter((item) => item !== skill) : [...current.skills, skill],
    }));
  }

  return (
    <section className="salary-workbench">
      <header className="salary-hero">
        <div>
          <div className="salary-agent-kicker"><Bot size={18} /> 薪资谈判 Agent</div>
          <h2>薪资谈判工作台</h2>
          <p>融合 demo 的薪资预测、趋势分析、职位对比、谈判模拟和 SHAP 解释，再由 DeepSeek 生成个性化谈薪策略。</p>
          <div className="salary-status-row">
            <span className={report.prediction.model_available ? "ok" : "warn"}>{report.prediction.model_available ? "XGBoost 已启用" : "模型降级可用"}</span>
            <span className={report.simulation.rl_available ? "ok" : "warn"}>{report.simulation.rl_available ? "PPO 已启用" : "RL 暂不可用"}</span>
            <span className={report.strategy.used_deepseek ? "ok" : "warn"}>{report.strategy.used_deepseek ? "DeepSeek 已生成策略" : "DeepSeek 降级策略"}</span>
          </div>
        </div>
        <div className="salary-hero-actions">
          <button type="button" onClick={refreshAnalysis} disabled={loading}><RefreshCw size={16} />重新分析</button>
          <button type="button" onClick={() => exportSalaryNegotiationReport(report, "pdf")}><Download size={16} />导出报告</button>
        </div>
      </header>

      {notice && <div className="salary-notice"><Activity size={16} />{notice}</div>}

      <div className="salary-metric-grid">
        <MetricCard icon={Gauge} label="预测年薪" value={report.prediction.salary} sub={`${report.prediction.salary_low} - ${report.prediction.salary_high}`} />
        <MetricCard icon={Target} label="建议目标薪资" value={money(report.strategy.target_salary)} sub="DeepSeek 目标锚点" />
        <MetricCard icon={ShieldAlert} label="最低可接受" value={money(report.strategy.minimum_acceptable_salary)} sub="谈判底线建议" />
        <MetricCard icon={TrendingUp} label="趋势模型 MAPE" value={`${report.trend.metrics?.mape ?? 1.17}%`} sub="LSTM demo 指标" />
      </div>

      <div className="salary-shell">
        <aside className="salary-side-nav">
          {[
            ["predict", "薪资预测", BarChart3],
            ["trend", "趋势分析", LineChart],
            ["category", "职位分类", BriefcaseBusiness],
            ["negotiate", "谈判模拟", MessageSquareText],
            ["advisor", "AI 顾问", Sparkles],
            ["explain", "SHAP 解释", Gauge],
          ].map(([key, label, Icon]) => (
            <button type="button" className={activeTab === key ? "active" : ""} onClick={() => setActiveTab(key as TabKey)} key={key as string}>
              <Icon size={18} />
              <span>{label as string}</span>
              <ChevronRight size={14} />
            </button>
          ))}
        </aside>

        <div className="salary-panel">
          {activeTab === "predict" && (
            <div className="salary-grid-2">
              <article className="salary-card">
                <div className="salary-card-title">职位信息输入</div>
                <div className="salary-form-grid">
                  <Field label="岗位名称"><input value={form.job_title} onChange={(event) => setForm({ ...form, job_title: event.target.value })} /></Field>
                  <Field label="经验等级">
                    <select value={form.experience_level} onChange={(event) => setForm({ ...form, experience_level: event.target.value })}>
                      <option value="EN">入门级 EN</option>
                      <option value="MI">中级 MI</option>
                      <option value="SE">高级 SE</option>
                      <option value="EX">专家级 EX</option>
                    </select>
                  </Field>
                  <Field label="工作年限"><input type="number" value={form.years_experience} onChange={(event) => setForm({ ...form, years_experience: Number(event.target.value) })} /></Field>
                  <Field label="国家/地区">
                    <select value={form.country} onChange={(event) => setForm({ ...form, country: event.target.value })}>
                      {countryOptions.map((country) => <option value={country} key={country}>{country}</option>)}
                    </select>
                  </Field>
                  <Field label="公司规模">
                    <select value={form.company_size} onChange={(event) => setForm({ ...form, company_size: event.target.value })}>
                      <option value="S">小型 S</option>
                      <option value="M">中型 M</option>
                      <option value="L">大型 L</option>
                    </select>
                  </Field>
                  <Field label="远程比例"><input type="number" value={form.remote_ratio} onChange={(event) => setForm({ ...form, remote_ratio: Number(event.target.value) })} /></Field>
                  <Field label="当前 Offer"><input type="number" value={form.current_offer || ""} placeholder="可选" onChange={(event) => setForm({ ...form, current_offer: Number(event.target.value) })} /></Field>
                  <Field label="期望薪资"><input type="number" value={form.expected_salary || ""} placeholder="可选" onChange={(event) => setForm({ ...form, expected_salary: Number(event.target.value) })} /></Field>
                </div>
                <div className="salary-skill-cloud">
                  {skillOptions.map((skill) => (
                    <button type="button" className={form.skills.includes(skill) ? "selected" : ""} onClick={() => toggleSkill(skill)} key={skill}>{skill}</button>
                  ))}
                </div>
                <button type="button" className="salary-primary-btn" onClick={refreshAnalysis} disabled={loading}>
                  <Sparkles size={16} />运行薪资预测
                </button>
              </article>

              <article className="salary-card salary-result-card">
                <div className="salary-card-title">预测结果</div>
                <div className="salary-big-number">{report.prediction.salary}</div>
                <p className="salary-range">{report.prediction.salary_low} - {report.prediction.salary_high}</p>
                <div className="salary-band">
                  <span style={{ left: "8%" }}>{report.prediction.salary_low}</span>
                  <i />
                  <span style={{ right: "8%" }}>{report.prediction.salary_high}</span>
                </div>
                <p className="salary-note">{report.prediction.message}</p>
                <p className={report.prediction.skill_note?.[0] === "ok" ? "salary-note ok" : "salary-note warn"}>{report.prediction.skill_note?.[1]}</p>
              </article>
            </div>
          )}

          {activeTab === "trend" && (
            <article className="salary-card">
              <div className="salary-card-title">全球 AI 月均薪资趋势</div>
              <SalaryLineChart report={report} />
              <div className="salary-forecast-row">
                {report.trend.forecast_summary.map((item) => (
                  <div className="salary-forecast-card" key={item.month}>
                    <span>{item.month}</span>
                    <strong>{money(item.salary)}</strong>
                  </div>
                ))}
              </div>
            </article>
          )}

          {activeTab === "category" && (
            <article className="salary-card">
              <div className="salary-card-title">职位分类薪资对比</div>
              <div className="salary-bars">
                {report.benchmarks.job_categories.map((item) => (
                  <div className="salary-bar-row" key={item.category}>
                    <span>{item.category}</span>
                    <div><i style={{ width: `${Math.min(100, item.median / 1600)}%` }} /></div>
                    <strong>{money(item.median)}</strong>
                  </div>
                ))}
              </div>
            </article>
          )}

          {activeTab === "negotiate" && (
            <div className="salary-grid-2">
              <article className="salary-card">
                <div className="salary-card-title">PPO 谈判模拟</div>
                <p className="salary-note">{report.simulation.message}</p>
                <button type="button" className="salary-primary-btn" onClick={rerunSimulation} disabled={loading}><Play size={16} />重新模拟谈判</button>
                <div className="salary-market-box">
                  <span>市场基准 <strong>{money(report.simulation.market_salary)}</strong></span>
                  <span>HR 预算上限 <strong>{money(report.simulation.hr_budget)}</strong></span>
                  <span>模拟成交价 <strong>{money(report.simulation.final_salary)}</strong></span>
                </div>
              </article>
              <article className="salary-card">
                <div className="salary-card-title">谈判过程</div>
                <div className="salary-round-list">
                  {report.simulation.rounds.map((round) => (
                    <div className={round.done ? "done" : ""} key={round.round}>
                      <header><strong>第 {round.round} 轮</strong><span>{round.action}</span></header>
                      <p>你的出价 {money(round.candidate_offer)} · HR 出价 {money(round.hr_offer)}</p>
                      <em>{round.hr_feedback || round.advice}</em>
                    </div>
                  ))}
                </div>
              </article>
            </div>
          )}

          {activeTab === "advisor" && (
            <div className="salary-grid-2">
              <article className="salary-card salary-advice-card">
                <div className="salary-card-title">DeepSeek 谈薪建议</div>
                <p>{report.strategy.final_report}</p>
                <h4>是否建议接受 Offer</h4>
                <p>{report.strategy.offer_decision}</p>
                <button type="button" className="salary-primary-btn" onClick={rerunStrategy} disabled={loading}><Sparkles size={16} />重新生成话术</button>
              </article>
              <article className="salary-card">
                <div className="salary-card-title">谈薪话术与压价应对</div>
                <SectionList title="谈判策略" items={report.strategy.negotiation_strategy} />
                <SectionList title="可直接使用的话术" items={report.strategy.talking_scripts} />
                <SectionList title="HR 压价应对" items={report.strategy.hr_pushback_responses} />
              </article>
            </div>
          )}

          {activeTab === "explain" && (
            <div className="salary-grid-2">
              <article className="salary-card">
                <div className="salary-card-title">SHAP 特征贡献</div>
                <div className="salary-bars shap">
                  {report.explainability.top_features.slice(0, 8).map((item) => (
                    <div className="salary-bar-row" key={item.feature}>
                      <span>{item.feature}</span>
                      <div><i style={{ width: `${Math.max(8, (item.importance / topFeatureTotal) * 100)}%` }} /></div>
                      <strong>{Math.round(item.importance * 1000) / 10}%</strong>
                    </div>
                  ))}
                </div>
              </article>
              <article className="salary-card">
                <div className="salary-card-title">解释性结论</div>
                <SectionList title="为什么是这个区间" items={report.explainability.narrative} />
                <SectionList title="风险提醒" items={report.strategy.risk_alerts} />
              </article>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="salary-field"><span>{label}</span>{children}</label>;
}

function MetricCard({ icon: Icon, label, value, sub }: { icon: ComponentType<{ size?: number }>; label: string; value: string; sub: string }) {
  return (
    <article className="salary-metric-card">
      <Icon size={20} />
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{sub}</p>
    </article>
  );
}

function SectionList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="salary-section-list">
      <h4>{title}</h4>
      {(items?.length ? items : ["暂无"]).map((item, index) => <p key={`${title}-${index}`}>{item}</p>)}
    </div>
  );
}

function SalaryLineChart({ report }: { report: SalaryNegotiationReport }) {
  const values = report.trend.months.map((month, index) => ({
    month,
    value: report.trend.actual[index] ?? report.trend.predicted[index] ?? 0,
    type: report.trend.type[index],
  })).filter((item) => item.value);
  const min = Math.min(...values.map((item) => item.value));
  const max = Math.max(...values.map((item) => item.value));
  const points = values.map((item, index) => {
    const x = values.length <= 1 ? 0 : (index / (values.length - 1)) * 100;
    const y = 86 - ((item.value - min) / Math.max(1, max - min)) * 64;
    return `${x},${y}`;
  }).join(" ");
  return (
    <div className="salary-line-chart">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none">
        <polyline points={points} fill="none" stroke="#4361ee" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        <polyline points={`${points} 100,100 0,100`} fill="rgba(67,97,238,.08)" stroke="none" />
      </svg>
      <div className="salary-chart-axis">
        <span>{values[0]?.month}</span>
        <span>{values[Math.floor(values.length / 2)]?.month}</span>
        <span>{values[values.length - 1]?.month}</span>
      </div>
    </div>
  );
}
