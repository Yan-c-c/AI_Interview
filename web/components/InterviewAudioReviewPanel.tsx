"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  Database,
  FileAudio,
  ListChecks,
  Loader2,
  Pencil,
  RefreshCcw,
  Save,
  SearchCheck,
  ShieldCheck,
  UserCheck,
  XCircle,
} from "lucide-react";
import {
  approveAudioReview,
  audioFileUrl,
  AudioEvidenceSource,
  AudioQAAnalysis,
  fetchInterviewAudioTask,
  InterviewAudioAnalysisReport,
  rejectAudioReview,
  TranscriptSegment,
  updateAudioReview,
} from "@/lib/api/interviewAudio";

type AudioReviewDraft = {
  question_id: string;
  question: string;
  standard_answer: string;
  knowledge_points: string[];
};

type QuestionReviewState = "pending" | "approved" | "rejected";

export function InterviewAudioReviewPanel({
  report,
  onUpdated,
  canManage = false,
}: {
  report: InterviewAudioAnalysisReport;
  onUpdated?: (report: InterviewAudioAnalysisReport) => void;
  canManage?: boolean;
}) {
  const [currentReport, setCurrentReport] = useState(report);
  const [drafts, setDrafts] = useState(() => createDrafts(report.qa_analysis || []));
  const [questionStates, setQuestionStates] = useState<Record<string, QuestionReviewState>>(() => createQuestionStates(report.qa_analysis || []));
  const [editing, setEditing] = useState<Record<string, { question?: boolean; answer?: boolean }>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const qaItems = currentReport.qa_analysis || [];
  const segments = currentReport.transcript.segments || [];
  const audioUrl = audioFileUrl(currentReport.metadata.audio_file_id);
  const hasTranscript = Boolean(currentReport.transcript.raw_text || segments.length);
  const hasQuestions = Boolean(qaItems.length);
  const taskStatus = currentReport.status || currentReport.review_status;
  const isProcessing = ["transcribing", "processing", "created", "pending_analysis"].includes(String(taskStatus));
  const isEmptyAnalysis = !isProcessing && !hasTranscript && !hasQuestions;

  useEffect(() => {
    setCurrentReport(report);
    setDrafts(createDrafts(report.qa_analysis || []));
    setQuestionStates(createQuestionStates(report.qa_analysis || []));
    setEditing({});
    setExpanded({});
  }, [report]);

  const updates = useMemo(
    () =>
      Object.values(drafts).map((item) => ({
        question_id: item.question_id,
        question: item.question,
        standard_answer: item.standard_answer,
        knowledge_points: item.knowledge_points,
      })),
    [drafts],
  );

  const progress = useMemo(() => {
    const total = qaItems.length;
    const approved = qaItems.filter((item) => questionStates[item.question_id] === "approved").length;
    const rejected = qaItems.filter((item) => questionStates[item.question_id] === "rejected").length;
    const pending = Math.max(total - approved - rejected, 0);
    const ingestable = qaItems.filter((item) => {
      const draft = drafts[item.question_id];
      return Boolean((draft?.question || item.question).trim() && (draft?.standard_answer || item.standard_answer).trim());
    }).length;
    return { total, approved, rejected, pending, ingestable };
  }, [drafts, qaItems, questionStates]);

  async function handleSave() {
    if (!canManage) {
      setStatus("录音题目入库由管理员在后台审核处理。");
      return;
    }
    if (!hasQuestions) {
      setStatus("当前还没有可编辑的题目，请等待转写和题目切分完成。");
      return;
    }
    setLoading(true);
    setStatus("");
    try {
      const response = await updateAudioReview(currentReport.task_id, updates);
      const next = response.task?.result as InterviewAudioAnalysisReport | undefined;
      if (next) {
        setCurrentReport(next);
        onUpdated?.(next);
      }
      setStatus("审核内容已保存。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "保存失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    if (!canManage) {
      setStatus("录音题目入库由管理员在后台审核处理。");
      return;
    }
    if (!hasQuestions) {
      setStatus("当前没有可入库的题目和标准答案，不能通过入库。");
      return;
    }
    setLoading(true);
    setStatus("");
    try {
      const response = await approveAudioReview(currentReport.task_id, updates);
      const next = response.task?.result as InterviewAudioAnalysisReport | undefined;
      if (next) {
        setCurrentReport(next);
        onUpdated?.(next);
      }
      setStatus("审核已通过，题目和标准答案已写入面试知识库。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "审核通过失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleReject() {
    if (!canManage) {
      setStatus("录音题目入库由管理员在后台审核处理。");
      return;
    }
    setLoading(true);
    setStatus("");
    try {
      const response = await rejectAudioReview(currentReport.task_id, "讲师判定暂不适合入库");
      const next = response.task?.result as InterviewAudioAnalysisReport | undefined;
      if (next) {
        setCurrentReport(next);
        onUpdated?.(next);
      }
      setStatus("已驳回当前录音分析结果。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "驳回失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleRefreshTask() {
    setLoading(true);
    setStatus("");
    try {
      const response = await fetchInterviewAudioTask(currentReport.task_id);
      const next = response.result;
      if (next) {
        setCurrentReport(next);
        setDrafts(createDrafts(next.qa_analysis || []));
        setQuestionStates(createQuestionStates(next.qa_analysis || []));
        onUpdated?.(next);
        const ready = Boolean(next.transcript.raw_text || next.qa_analysis?.length);
        setStatus(ready ? "已获取转写结果并完成分析。" : response.message || "百度仍在转写中，请稍后再次刷新。");
      } else {
        setStatus(response.message || "百度仍在转写中，请稍后再次刷新。");
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "刷新任务失败");
    } finally {
      setLoading(false);
    }
  }

  function seekToSegment(segment: TranscriptSegment) {
    const seconds = segmentStartSeconds(segment);
    if (audioRef.current && Number.isFinite(seconds)) {
      audioRef.current.currentTime = seconds;
      void audioRef.current.play().catch(() => undefined);
    }
  }

  function setQuestionState(questionId: string, next: QuestionReviewState) {
    setQuestionStates((state) => ({ ...state, [questionId]: next }));
  }

  function updateDraft(questionId: string, next: AudioReviewDraft) {
    setDrafts((state) => ({ ...state, [questionId]: next }));
  }

  function toggleExpanded(key: string) {
    setExpanded((state) => ({ ...state, [key]: !state[key] }));
  }

  return (
    <section className={`audio-review-workspace ${isProcessing ? "is-processing" : hasQuestions ? "is-complete" : "is-empty"}`}>
      <header className="audio-review-top">
        <div className="audio-top-title">
          <div className="kb-eyebrow"><FileAudio size={16} /> 面试录音分析 Agent</div>
          <div>
            <h2>{canManage ? "讲师快速审核工作台" : "面试录音分析结果"}</h2>
            <p>{canManage ? "围绕音频对照审核和题目答案入库两件事组织内容，审核通过后收录到面试知识库。" : "你可以查看转写、问答切分、评分和改进建议；题库入库由管理员在后台完成。"}</p>
          </div>
        </div>

        <div className="audio-task-strip">
          <StatusPill status={taskStatus} isProcessing={isProcessing} isEmpty={isEmptyAnalysis} />
          <span className="audio-file-chip"><FileAudio size={15} />{currentReport.metadata.audio_filename || "面试录音"}</span>
          <span className="audio-file-chip"><Clock3 size={15} />{hasTranscript ? "转写完成" : isProcessing ? "转写中" : "暂无转写"}</span>
          {currentReport.metadata.baidu_task_id && <span className="audio-file-chip muted">百度任务：{currentReport.metadata.baidu_task_id}</span>}
        </div>

        {canManage ? (
          <div className="audio-review-actions">
            <button type="button" className="outline-button" onClick={handleRefreshTask} disabled={loading}>
              {loading ? <Loader2 size={16} className="spin-icon" /> : <RefreshCcw size={16} />}刷新结果
            </button>
            <button type="button" className="outline-button" onClick={handleSave} disabled={loading || !hasQuestions}><Save size={16} />保存修改</button>
            <button type="button" className="outline-button danger" onClick={handleReject} disabled={loading}><XCircle size={16} />驳回</button>
            <button type="button" className="primary-button" onClick={handleApprove} disabled={loading || !hasQuestions}><CheckCircle2 size={16} />通过并入库</button>
          </div>
        ) : (
          <div className="audio-review-readonly-note">
            <UserCheck size={18} />
            <span>管理员审核通过后，真实题目和标准答案才会写入题库。</span>
          </div>
        )}

        <div className="audio-score-row">
          <ScoreCard label="总体评分" value={currentReport.summary.overall_score ?? undefined} pending={!hasQuestions} />
          <ScoreCard label="技术准确性" value={currentReport.summary.accuracy_score ?? undefined} pending={!hasQuestions} />
          <ScoreCard label="表达清晰度" value={currentReport.summary.expression_score ?? undefined} pending={!hasQuestions} />
          <ScoreCard label="项目理解深度" value={currentReport.summary.project_depth_score ?? undefined} pending={!hasQuestions} />
        </div>
      </header>

      {(isProcessing || isEmptyAnalysis || status) && (
        <div className={`audio-status-banner ${isProcessing ? "processing" : isEmptyAnalysis ? "warning" : ""}`}>
          {isProcessing ? <Loader2 size={20} className="spin-icon" /> : isEmptyAnalysis ? <AlertCircle size={20} /> : <CheckCircle2 size={20} />}
          <div>
            <strong>{status || (isProcessing ? "百度音频文件转写仍在处理中" : "当前没有可展示的转写内容")}</strong>
            <p>
              {status
                ? "请根据当前状态继续审核。"
                : isProcessing
                  ? "长音频转写不会立即返回完整文本。请等待百度任务完成后点击“刷新结果”，系统会继续进行话者识别、题目切分和答案评估。"
                  : "这通常是上一次在百度任务仍为 Running 时生成了空报告，或百度成功结果中没有可解析文本。请点击“刷新结果”重新拉取百度任务。"}
            </p>
          </div>
        </div>
      )}

      <div className="audio-review-center">
        <section className="audio-left-pane">
          <article className="audio-pane-card audio-player-card">
            <div className="audio-pane-head">
              <div>
                <h3>音频与原始转写区</h3>
                <p>点击时间轴片段可定位音频时间。</p>
              </div>
              <FileAudio size={20} />
            </div>
            {audioUrl ? <audio ref={audioRef} controls src={audioUrl} className="audio-player" /> : <div className="kb-empty">当前任务未关联本地音频文件。</div>}
          </article>

          <article className="audio-pane-card">
            <div className="audio-pane-head compact">
              <div>
                <h3>说话人映射</h3>
                <p>DeepSeek 基于话者分离判断角色。</p>
              </div>
              <UserCheck size={20} />
            </div>
            <SpeakerMapping mapping={currentReport.transcript.speaker_mapping} />
          </article>

          <article className="audio-pane-card transcript-card">
            <div className="audio-pane-head compact">
              <div>
                <h3>原始转写全文</h3>
                <p>默认摘要展示，展开后用于人工复核。</p>
              </div>
              <SearchCheck size={20} />
            </div>
            <CollapsibleText
              text={currentReport.transcript.raw_text || "转写完成后会在这里展示完整原文。"}
              expanded={Boolean(expanded.rawTranscript)}
              onToggle={() => toggleExpanded("rawTranscript")}
              limit={160}
            />
          </article>

          <article className="audio-pane-card timeline-card">
            <div className="audio-pane-head compact">
              <div>
                <h3>对话时间轴</h3>
                <p>按时间快速核对问题与回答。</p>
              </div>
              <Clock3 size={20} />
            </div>
            <div className="audio-timeline">
              {segments.map((segment) => (
                <button type="button" className={`audio-segment ${segment.role}`} key={segment.segment_id} onClick={() => seekToSegment(segment)}>
                  <span>{segment.start_time}</span>
                  <strong>{segment.role === "interviewer" ? "面试官" : "面试者"}</strong>
                  <p>{segment.text}</p>
                </button>
              ))}
              {!segments.length && <div className="kb-empty">转写完成后会按时间轴展示面试官和面试者对话。</div>}
            </div>
          </article>
        </section>

        <section className="audio-right-pane">
          <div className="audio-pane-head qa-sticky-head">
            <div>
              <h3>题目与答案审核区</h3>
              <p>{canManage ? "一题一卡，长文本折叠，证据来源收纳到抽屉。" : "展示系统识别出的题目、回答、参考答案和证据来源。"}</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <div className="audio-qa-list">
            {qaItems.map((item, index) => (
              <AudioQuestionCard
                key={item.question_id}
                index={index}
                item={item}
                draft={drafts[item.question_id]}
                state={questionStates[item.question_id] || "pending"}
                editing={editing[item.question_id] || {}}
                expanded={expanded}
                canManage={canManage}
                onToggleExpanded={toggleExpanded}
                onChange={(next) => updateDraft(item.question_id, next)}
                onEdit={(field) => setEditing((items) => ({ ...items, [item.question_id]: { ...items[item.question_id], [field]: !items[item.question_id]?.[field] } }))}
                onApprove={() => setQuestionState(item.question_id, "approved")}
                onReject={() => setQuestionState(item.question_id, "rejected")}
              />
            ))}
            {!qaItems.length && (
              <div className="audio-empty-state">
                <ListChecks size={28} />
                <strong>等待题目切分</strong>
                <p>转写完成后，这里会展示每道面试题、学生回答、AI 综合正确答案、评分和证据来源。</p>
              </div>
            )}
          </div>
        </section>
      </div>

      <footer className="audio-progress-panel">
        <div>
          <span>审核进度</span>
          <strong>{progress.approved}/{progress.total}</strong>
          <p>{canManage ? "已审核 / 总题数" : "管理员审核后更新"}</p>
        </div>
        <ProgressMetric label="待复核" value={progress.pending} />
        <ProgressMetric label="已驳回" value={progress.rejected} />
        <ProgressMetric label="可入库" value={progress.ingestable} />
        <div className="review-log-compact">
          <Database size={16} />
          <span>{(currentReport.review_logs || []).length ? `已有 ${currentReport.review_logs?.length} 条审核记录` : "暂无审核记录"}</span>
        </div>
        {canManage && (
          <button type="button" className="primary-button" onClick={handleApprove} disabled={loading || !hasQuestions}>
            <CheckCircle2 size={16} />最终提交入库
          </button>
        )}
      </footer>
    </section>
  );
}

function createDrafts(items: AudioQAAnalysis[]) {
  return Object.fromEntries(
    items.map((item) => [
      item.question_id,
      {
        question_id: item.question_id,
        question: item.question,
        standard_answer: item.standard_answer,
        knowledge_points: item.knowledge_points || [],
      },
    ]),
  );
}

function createQuestionStates(items: AudioQAAnalysis[]) {
  return Object.fromEntries(items.map((item) => [item.question_id, "pending" as QuestionReviewState]));
}

function ScoreCard({ label, value, pending = false }: { label: string; value?: number; pending?: boolean }) {
  return (
    <article className="audio-score-card">
      <span>{label}</span>
      {pending || value == null ? (
        <>
          <strong className="pending-score">待生成</strong>
          <p>等待转写</p>
        </>
      ) : (
        <>
          <strong>{value}</strong>
          <p>/100</p>
        </>
      )}
    </article>
  );
}

function StatusPill({ status, isProcessing, isEmpty }: { status?: string; isProcessing: boolean; isEmpty: boolean }) {
  const label = isProcessing ? "转写中" : isEmpty ? "待刷新" : status === "approved" ? "已入库" : "待审核";
  return <span className={`audio-status-pill ${isProcessing ? "processing" : isEmpty ? "warning" : "ready"}`}>{label}</span>;
}

function SpeakerMapping({ mapping }: { mapping: Record<string, string> }) {
  const entries = Object.entries(mapping || {});
  if (!entries.length) return <div className="kb-empty compact">等待话者识别结果。</div>;
  return (
    <div className="speaker-map-grid">
      {entries.map(([speaker, role]) => (
        <span key={speaker}>
          <strong>{speaker}</strong>
          {role === "interviewer" ? "面试官" : role === "candidate" ? "面试者" : role}
        </span>
      ))}
    </div>
  );
}

function AudioQuestionCard({
  index,
  item,
  draft,
  state,
  editing,
  expanded,
  canManage,
  onToggleExpanded,
  onChange,
  onEdit,
  onApprove,
  onReject,
}: {
  index: number;
  item: AudioQAAnalysis;
  draft?: AudioReviewDraft;
  state: QuestionReviewState;
  editing: { question?: boolean; answer?: boolean };
  expanded: Record<string, boolean>;
  canManage: boolean;
  onToggleExpanded: (key: string) => void;
  onChange: (draft: AudioReviewDraft) => void;
  onEdit: (field: "question" | "answer") => void;
  onApprove: () => void;
  onReject: () => void;
}) {
  const safeDraft = draft || {
    question_id: item.question_id,
    question: item.question,
    standard_answer: item.standard_answer,
    knowledge_points: item.knowledge_points || [],
  };
  const evidence = item.evidence_sources || [];
  const evidenceKey = `${item.question_id}-evidence`;
  const answerKey = `${item.question_id}-answer`;
  const standardKey = `${item.question_id}-standard`;

  return (
    <article className={`audio-question-card ${state}`}>
      <div className="audio-question-top">
        <div>
          <span className="question-index">第 {index + 1} 题</span>
          <strong>{item.accuracy_score ?? 0} 分 · {item.accuracy_level || "待评估"}</strong>
        </div>
        <span className={`question-review-pill ${state}`}>{state === "approved" ? "本题通过" : state === "rejected" ? "本题驳回" : "待复核"}</span>
      </div>

      <section className="question-field">
        <div className="field-title">
          <span>面试题</span>
          {canManage && <button type="button" onClick={() => onEdit("question")}><Pencil size={14} />{editing.question ? "完成编辑" : "编辑题目"}</button>}
        </div>
        {editing.question ? (
          <textarea value={safeDraft.question} onChange={(event) => onChange({ ...safeDraft, question: event.target.value })} />
        ) : (
          <CollapsibleText text={safeDraft.question || "未识别到面试题"} expanded={Boolean(expanded[`${item.question_id}-question`])} onToggle={() => onToggleExpanded(`${item.question_id}-question`)} limit={120} />
        )}
      </section>

      <section className="question-field">
        <div className="field-title">
          <span>学生回答</span>
        </div>
        <CollapsibleText text={item.candidate_answer || "未识别到回答"} expanded={Boolean(expanded[answerKey])} onToggle={() => onToggleExpanded(answerKey)} limit={150} />
      </section>

      <section className="question-field standard-answer">
        <div className="field-title">
          <span>AI 综合正确答案</span>
          {canManage && <button type="button" onClick={() => onEdit("answer")}><Pencil size={14} />{editing.answer ? "完成编辑" : "编辑答案"}</button>}
        </div>
        {editing.answer ? (
          <textarea value={safeDraft.standard_answer} onChange={(event) => onChange({ ...safeDraft, standard_answer: event.target.value })} />
        ) : (
          <CollapsibleText text={safeDraft.standard_answer || "等待生成标准答案"} expanded={Boolean(expanded[standardKey])} onToggle={() => onToggleExpanded(standardKey)} limit={180} />
        )}
      </section>

      <div className="source-tag-row">
        {evidence.length ? evidence.slice(0, 4).map((source, sourceIndex) => <EvidenceTag key={`${source.source_type}-${sourceIndex}`} source={source} />) : <EvidenceTag source={{ source_type: "deepseek_generated", title: "DeepSeek 兜底", summary: "未检索到外部证据。" }} />}
      </div>

      <details className="evidence-drawer" open={Boolean(expanded[evidenceKey])} onToggle={() => onToggleExpanded(evidenceKey)}>
        <summary>证据引用与反馈建议</summary>
        <div className="evidence-drawer-body">
          <div className="compact-evidence-list">
            {evidence.map((source, sourceIndex) => (
              <div key={`${source.source_type}-${sourceIndex}`}>
                <strong>{sourceLabel(source.source_type)}</strong>
                <span>{source.title || "未命名来源"}</span>
                <p>{source.summary || "暂无摘要"}</p>
              </div>
            ))}
            {!evidence.length && <div className="kb-empty compact">暂无外部证据，当前答案由 DeepSeek 兜底生成。</div>}
          </div>
          <div className="audio-feedback-compact">
            <p><strong>反馈：</strong>{item.feedback || "暂无反馈"}</p>
            <p><strong>建议：</strong>{item.improvement_suggestion || "暂无建议"}</p>
          </div>
        </div>
      </details>

      {canManage && (
        <div className="question-card-actions">
          <button type="button" className="outline-button compact" onClick={onApprove}><CheckCircle2 size={15} />通过本题</button>
          <button type="button" className="outline-button compact danger" onClick={onReject}><XCircle size={15} />驳回本题</button>
        </div>
      )}
    </article>
  );
}

function EvidenceTag({ source }: { source: AudioEvidenceSource }) {
  return <span className={`evidence-tag ${source.source_type}`}>{sourceLabel(source.source_type)}</span>;
}

function sourceLabel(sourceType?: string) {
  if (sourceType === "lightrag") return "LightRAG";
  if (sourceType === "baidu_ai_search") return "百度AI搜索";
  if (sourceType === "deepseek_generated") return "DeepSeek兜底";
  return sourceType || "未知来源";
}

function CollapsibleText({ text, expanded, onToggle, limit = 160 }: { text: string; expanded: boolean; onToggle: () => void; limit?: number }) {
  const content = text || "";
  const shouldCollapse = content.length > limit;
  const display = !shouldCollapse || expanded ? content : `${content.slice(0, limit)}...`;
  return (
    <div className="collapsible-copy">
      <p>{display}</p>
      {shouldCollapse && <button type="button" onClick={onToggle}>{expanded ? "收起详情" : "展开详情"}</button>}
    </div>
  );
}

function ProgressMetric({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>题</p>
    </div>
  );
}

function segmentStartSeconds(segment: TranscriptSegment) {
  const maybeMs = (segment as TranscriptSegment & { start_ms?: number }).start_ms;
  if (typeof maybeMs === "number") return maybeMs / 1000;
  const parts = String(segment.start_time || "0").split(":").map((item) => Number(item));
  if (parts.some((item) => Number.isNaN(item))) return 0;
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  return parts[0] || 0;
}
