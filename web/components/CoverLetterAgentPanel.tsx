"use client";

import { useMemo, useState } from "react";
import {
  BriefcaseBusiness,
  CheckCircle2,
  Download,
  FileText,
  Mail,
  PenLine,
  Send,
  Sparkles,
} from "lucide-react";
import {
  CoverLetterReport,
  exportCoverLetter,
  rewriteCoverLetter,
  sendCoverLetterEmail,
} from "@/lib/api/coverLetter";

const versionLabels: Record<string, string> = {
  standard: "标准版",
  email_short: "邮件精简版",
  technical: "技术岗位版",
  campus_internship: "校招/实习版",
  custom: "自定义版",
};

function cleanGeneratedText(text?: string) {
  return (text || "")
    .replace(/\\r\\n|\\n|\/n/g, "\n")
    .replace(/\\t/g, "  ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function CoverLetterAgentPanel({ report, fileId, onUpdated }: { report: CoverLetterReport; fileId?: string; onUpdated: (report: CoverLetterReport) => void }) {
  const availableVersions = Object.keys(report.versions || {}).filter((key) => report.versions[key]?.body);
  const [activeVersion, setActiveVersion] = useState(availableVersions[0] || "standard");
  const [rewriteInstruction, setRewriteInstruction] = useState("");
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const current = report.versions?.[activeVersion] || report.versions?.standard;
  const missingText = report.missing_fields?.length ? report.missing_fields.join("、") : "信息完整";

  const profileTags = useMemo(
    () => [...(report.resume_profile.skills || []), ...(report.resume_profile.strongest_evidence || [])].slice(0, 10),
    [report],
  );

  async function handleRewrite() {
    if (!rewriteInstruction.trim()) {
      setStatus("请先输入改写要求。");
      return;
    }
    setBusy(true);
    setStatus("正在调用 DeepSeek 改写求职信...");
    try {
      const updated = await rewriteCoverLetter(report, rewriteInstruction);
      onUpdated(updated);
      setActiveVersion(updated.versions.custom?.body ? "custom" : activeVersion);
      setRewriteInstruction("");
      setStatus("求职信已改写。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "求职信改写失败");
    } finally {
      setBusy(false);
    }
  }

  async function handleExport(format: "md" | "docx" | "pdf") {
    setBusy(true);
    setStatus("");
    try {
      await exportCoverLetter(report, format, activeVersion);
      setStatus(`已导出 ${format.toUpperCase()}。`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "导出失败");
    } finally {
      setBusy(false);
    }
  }

  async function handleSend(saveDraft = false) {
    if (!email.trim()) {
      setStatus("请先输入收件人邮箱。");
      return;
    }
    setBusy(true);
    setStatus(saveDraft ? "正在保存邮件草稿..." : "正在发送邮件...");
    try {
      const result = await sendCoverLetterEmail({
        report,
        to_email: email,
        subject: report.email.subject,
        body: report.email.body,
        version: activeVersion,
        attach_cover_letter: true,
        attach_resume_file: Boolean(fileId),
        resume_file_id: fileId,
        save_draft: saveDraft,
      });
      setStatus(result.message);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "邮件处理失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="agent-workspace letter-workspace">
      <header className="agent-hero-card">
        <div className="agent-title-block">
          <div className="agent-icon"><Mail size={22} /></div>
          <div>
            <div className="agent-kicker">
              <span>求职信生成 Agent</span>
              <span className="soft-pill done">已生成</span>
            </div>
            <h2>个性化求职信工作台</h2>
          </div>
        </div>
        <div className="agent-action-row letter-export-grid">
          <button type="button" className="outline-button" disabled={busy} onClick={() => void handleExport("md")}><Download size={16} />Markdown</button>
          <button type="button" className="outline-button" disabled={busy} onClick={() => void handleExport("docx")}><Download size={16} />DOCX</button>
          <button type="button" className="outline-button" disabled={busy} onClick={() => void handleExport("pdf")}><Download size={16} />PDF</button>
        </div>
      </header>

      {report.needs_more_info && (
        <div className="agent-notice">
          <Sparkles size={18} />
          <span>建议补充：{missingText}。当前结果可用，但补充后会更贴合目标岗位。</span>
        </div>
      )}

      <article className="agent-main-card letter-mail-card">
        <div>
          <h3><Send size={18} /> 邮件发送</h3>
          <p className="muted-text">{cleanGeneratedText(report.email.subject) || "系统会根据求职信自动生成邮件主题。"}</p>
        </div>
        <div className="letter-mail-form">
          <input className="soft-input" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="收件人邮箱" />
          <button type="button" className="outline-button" disabled={busy} onClick={() => void handleSend(true)}>保存草稿</button>
          <button type="button" className="primary-button" disabled={busy} onClick={() => void handleSend(false)}>发送</button>
        </div>
      </article>

      <div className="letter-layout">
        <main className="agent-main-card letter-preview-card">
          <nav className="soft-tabs">
            {availableVersions.map((key) => (
              <button key={key} type="button" className={activeVersion === key ? "active" : ""} onClick={() => setActiveVersion(key)}>
                {versionLabels[key] || key}
              </button>
            ))}
          </nav>
          <article className="letter-paper">
            <h3>{current?.title || "求职信"}</h3>
            <pre>{cleanGeneratedText(current?.body) || "暂无正文"}</pre>
          </article>
          <div className="rewrite-bar">
            <PenLine size={18} />
            <input value={rewriteInstruction} onChange={(event) => setRewriteInstruction(event.target.value)} placeholder="例如：更正式一点，突出科研经历，缩短到 300 字..." />
            <button type="button" className="primary-button" disabled={busy} onClick={() => void handleRewrite()}>改写</button>
          </div>
        </main>

        <aside className="agent-side-stack">
          <article className="agent-side-card">
            <h3><BriefcaseBusiness size={18} /> 目标信息</h3>
            <dl className="compact-dl">
              <div><dt>公司</dt><dd>{report.requirements.target_company}</dd></div>
              <div><dt>岗位</dt><dd>{report.requirements.target_position}</dd></div>
              <div><dt>用途</dt><dd>{report.requirements.purpose}</dd></div>
              <div><dt>风格</dt><dd>{report.requirements.style}</dd></div>
            </dl>
          </article>

          <article className="agent-side-card">
            <h3><FileText size={18} /> 简历画像</h3>
            <p>{report.resume_profile.job_fit_summary || report.metadata.note || "上传简历可获得更精准画像。"}</p>
            <div className="tag-cloud">
              {profileTags.length ? profileTags.map((item) => <span key={item}>{item}</span>) : <span>待补充简历信息</span>}
            </div>
          </article>

          <article className="agent-side-card">
            <h3><CheckCircle2 size={18} /> 突出亮点</h3>
            <ul className="soft-list">
              {(report.highlight_points || []).slice(0, 5).map((item) => <li key={item}>{item}</li>)}
            </ul>
          </article>

        </aside>
      </div>

      {status && <div className="agent-toast">{status}</div>}
    </section>
  );
}
