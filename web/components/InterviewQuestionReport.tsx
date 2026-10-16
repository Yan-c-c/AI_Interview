"use client";

import { useMemo, useState, type CSSProperties, type ReactNode } from "react";
import {
  Bot,
  Brain,
  BriefcaseBusiness,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  Download,
  Eye,
  FileSearch,
  Layers3,
  Mic,
  MicOff,
  Play,
  RotateCcw,
  Sparkles,
  UserRound,
  Volume2,
} from "lucide-react";
import {
  generateMockInterviewReport,
  InterviewQuestionReport as Report,
  MockInterviewQA,
  MockInterviewReport,
  MockInterviewScenario,
} from "@/lib/api/interviewQuestion";
import { API_BASE_URL } from "@/lib/api/resumeEvaluation";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";

const positions = ["Java 后端", "大模型", "数据分析", "前端", "测试开发"];
const difficulties: MockInterviewScenario["difficulty"][] = ["基础", "中等", "进阶"];
const modes: MockInterviewScenario["mode"][] = ["技术一面", "项目深挖", "HR 面", "压力面", "综合模拟"];
const questionCountOptions = [3, 5, 8, 10];

const sceneCategoryMap: Record<string, string[]> = {
  "技术一面": ["技术基础题", "技术进阶题", "项目深挖题"],
  "项目深挖": ["项目深挖题", "场景设计题", "技术进阶题"],
  "HR 面": ["项目深挖题", "场景设计题", "技术基础题"],
  "压力面": ["技术进阶题", "场景设计题", "项目深挖题"],
  "综合模拟": ["项目深挖题", "技术基础题", "技术进阶题", "场景设计题"],
};

function difficultyRank(value: string) {
  if (value === "easy") return 1;
  if (value === "medium") return 2;
  if (value === "hard") return 3;
  return 2;
}

function targetDifficulty(value: string) {
  if (value === "基础") return 1;
  if (value === "进阶") return 3;
  return 2;
}

function flattenQuestions(report: Report) {
  return report.questions?.length ? report.questions : Object.values(report.question_sets || {}).flat();
}

function pickQuestions(report: Report, scenario: MockInterviewScenario, count: number) {
  const nonFollowUpQuestions = flattenQuestions(report).filter((question) => question.category !== "追问题");
  const all = nonFollowUpQuestions.length ? nonFollowUpQuestions : flattenQuestions(report);
  const categories = sceneCategoryMap[scenario.mode] || sceneCategoryMap["综合模拟"];
  const target = targetDifficulty(scenario.difficulty);
  const sorted = [...all].sort((a, b) => {
    const categoryA = categories.includes(a.category) ? 0 : 1;
    const categoryB = categories.includes(b.category) ? 0 : 1;
    const difficultyA = Math.abs(difficultyRank(a.difficulty) - target);
    const difficultyB = Math.abs(difficultyRank(b.difficulty) - target);
    return categoryA - categoryB || difficultyA - difficultyB;
  });
  return sorted.slice(0, count);
}

function scoreLabel(score: number) {
  if (score >= 85) return "优秀";
  if (score >= 75) return "良好";
  if (score >= 60) return "待加强";
  return "需重点复盘";
}

function readableDifficulty(value: string) {
  if (value === "easy") return "基础";
  if (value === "medium") return "中等";
  if (value === "hard") return "进阶";
  return value || "中等";
}

export function InterviewQuestionReport({ report }: { report: Report }) {
  const inferredPosition = report.summary.target_position && report.summary.target_position !== "未明确"
    ? report.summary.target_position
    : "Java 后端";
  const [scenario, setScenario] = useState<MockInterviewScenario>({
    position: inferredPosition,
    difficulty: "中等",
    mode: "技术一面",
    answerMode: "voice",
  });
  const [questionCount, setQuestionCount] = useState(5);
  const [phase, setPhase] = useState<"setup" | "active" | "report">("setup");
  const [interviewStatus, setInterviewStatus] = useState<"idle" | "in_progress" | "completed">("idle");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [qaHistory, setQaHistory] = useState<MockInterviewQA[]>([]);
  const [answerError, setAnswerError] = useState("");
  const [voiceNotice, setVoiceNotice] = useState("");
  const [speaking, setSpeaking] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [previewExpanded, setPreviewExpanded] = useState(false);
  const [finalReport, setFinalReport] = useState<MockInterviewReport | null>(null);

  const selectedQuestions = useMemo(
    () => pickQuestions(report, scenario, questionCount),
    [report, scenario, questionCount],
  );
  const currentQuestion = selectedQuestions[currentIndex];
  const progressPercent = selectedQuestions.length ? Math.min(100, Math.round((qaHistory.length / selectedQuestions.length) * 100)) : 0;
  const isLastQuestion = currentIndex === selectedQuestions.length - 1;
  const visiblePreviewQuestions = previewExpanded ? selectedQuestions : selectedQuestions.slice(0, 3);
  const statusText = interviewStatus === "completed" ? "已完成" : phase === "active" ? "面试中" : "待开始";
  const currentStepText = phase === "setup"
    ? "等待开始"
    : phase === "active"
      ? `第 ${currentIndex + 1} / ${selectedQuestions.length} 题`
      : "评估报告已生成";
  const stepItems = [
    { index: "1", title: "简历解析", state: "已完成", Icon: FileSearch },
    { index: "2", title: "画像提取", state: "已完成", Icon: Brain },
    { index: "3", title: "个性化提问", state: "已完成", Icon: Layers3 },
    { index: "4", title: "模拟面试", state: statusText, Icon: Sparkles },
  ];

  const voice = useVoiceRecorder({
    onTranscript: (text) => {
      setAnswer((value) => `${value}${value ? " " : ""}${text}`);
    },
  });

  function updateScenario(update: Partial<MockInterviewScenario>) {
    setScenario((value) => ({ ...value, ...update }));
  }

  function startInterview() {
    voice.cancelRecording();
    setPhase("active");
    setInterviewStatus("in_progress");
    setCurrentIndex(0);
    setAnswer("");
    setQaHistory([]);
    setAnswerError("");
    setVoiceNotice("");
    setFinalReport(null);
  }

  async function playQuestionAudio() {
    const text = currentQuestion?.question;
    if (interviewStatus === "completed" || !text || speaking) return;
    setSpeaking(true);
    setVoiceNotice("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/interview-audio/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail?.message || error.message || "语音播放失败");
      }
      const blob = await response.blob();
      const audio = new Audio(URL.createObjectURL(blob));
      audio.onended = () => {
        URL.revokeObjectURL(audio.src);
        setSpeaking(false);
      };
      audio.onerror = () => {
        URL.revokeObjectURL(audio.src);
        setSpeaking(false);
        setVoiceNotice("音频播放失败，请直接阅读题目。");
      };
      await audio.play();
    } catch (event) {
      setSpeaking(false);
      setVoiceNotice(event instanceof Error ? event.message : "语音播放失败");
    }
  }

  function saveCurrentAnswer() {
    if (interviewStatus === "completed") return null;
    if (!currentQuestion) return null;
    const answerText = answer.trim();
    const record: MockInterviewQA = {
      question_id: currentQuestion.id,
      questionId: currentQuestion.id,
      question: currentQuestion.question,
      questionText: currentQuestion.question,
      category: currentQuestion.category,
      answer: answerText,
      answerText,
      empty: !answerText,
      index: currentIndex,
    };
    const nextRecords = [
      ...qaHistory.filter((item) => item.index !== currentIndex && item.question_id !== currentQuestion.id),
      record,
    ].sort((a, b) => (a.index ?? 0) - (b.index ?? 0));
    setQaHistory(nextRecords);
    setAnswerError("");
    return nextRecords;
  }

  function handleNextQuestion() {
    if (interviewStatus === "completed") return;
    voice.cancelRecording();
    const savedRecords = saveCurrentAnswer();
    if (!savedRecords || isLastQuestion) return;
    setVoiceNotice("");
    setAnswer("");
    setCurrentIndex((index) => index + 1);
  }

  async function handleSubmitInterview() {
    if (interviewStatus === "completed") return;
    voice.cancelRecording();
    const savedRecords = saveCurrentAnswer();
    if (!savedRecords || processing) return;
    setInterviewStatus("completed");
    setProcessing(true);
    try {
      const result = await generateMockInterviewReport({
        resume_profile: report.resume_profile,
        scenario,
        qa_history: savedRecords,
      });
      setFinalReport(result.report);
      setPhase("report");
    } catch (event) {
      setInterviewStatus("in_progress");
      setAnswerError(event instanceof Error ? event.message : "面试报告生成失败");
    } finally {
      setProcessing(false);
    }
  }

  return (
    <div className="mock-interview-workspace ios-agent-workbench">
      <header className="ios-agent-card ios-agent-hero">
        <div className="ios-agent-title">
          <div className="ios-agent-mark">
            <Bot size={22} />
          </div>
          <div>
            <div className="ios-eyebrow">
              <span>模拟面试 Agent</span>
              <span className={`ios-status-pill ${interviewStatus === "completed" ? "done" : phase === "active" ? "running" : ""}`}>
                {statusText}
              </span>
              <span className="ios-step-label">{currentStepText}</span>
            </div>
            <h2>简历驱动的模拟面试</h2>
            <p>AI 已根据简历完成画像抽取与个性化提问生成。选择场景后进入真实面试流程，回答会实时记录并用于最终评估。</p>
          </div>
        </div>
        <div className="ios-hero-meta">
          <strong>{selectedQuestions.length || report.summary.question_count}</strong>
          <span>本场题目</span>
        </div>
      </header>

      <section className="ios-stepper">
        {stepItems.map(({ index, title, state, Icon }, itemIndex) => {
          const active = itemIndex === 3 && phase === "setup";
          const done = itemIndex < 3 || phase !== "setup";
          return (
            <article className={`ios-step-card ${done ? "done" : ""} ${active ? "active" : ""}`} key={title}>
              <div className="ios-step-number">{index}</div>
              <Icon size={18} />
              <div>
                <strong>{title}</strong>
                <span>{state}</span>
              </div>
            </article>
          );
        })}
      </section>

      {phase === "setup" && (
        <section className="ios-task-grid">
          <div className="ios-agent-card ios-config-card">
            <div className="ios-section-head">
              <div>
                <h3>选择面试场景</h3>
                <p>岗位、难度和形式会影响题目排序、问题角度和最终报告维度。</p>
              </div>
            </div>

            <ConfigBlock label="岗位方向">
              <div className="ios-segment-grid five">
                {positions.map((item) => (
                  <button key={item} type="button" className={scenario.position === item ? "active" : ""} onClick={() => updateScenario({ position: item })}>
                    {item}
                  </button>
                ))}
              </div>
              <input value={scenario.position} onChange={(event) => updateScenario({ position: event.target.value })} placeholder="也可以手动输入目标岗位" />
            </ConfigBlock>

            <ConfigBlock label="难度">
              <div className="ios-segment-grid three">
                {difficulties.map((item) => (
                  <button key={item} type="button" className={scenario.difficulty === item ? "active" : ""} onClick={() => updateScenario({ difficulty: item })}>
                    {item}
                  </button>
                ))}
              </div>
            </ConfigBlock>

            <ConfigBlock label="面试形式">
              <div className="ios-segment-grid five">
                {modes.map((item) => (
                  <button key={item} type="button" className={scenario.mode === item ? "active" : ""} onClick={() => updateScenario({ mode: item })}>
                    {item}
                  </button>
                ))}
              </div>
            </ConfigBlock>

            <ConfigBlock label="回答方式">
              <div className="ios-segment-grid two">
                <button type="button" className={scenario.answerMode === "voice" ? "active" : ""} onClick={() => updateScenario({ answerMode: "voice" })}>
                  <Mic size={16} /> 语音 + 转写
                </button>
                <button type="button" className={scenario.answerMode === "text" ? "active" : ""} onClick={() => updateScenario({ answerMode: "text" })}>
                  <ClipboardList size={16} /> 文字输入
                </button>
              </div>
            </ConfigBlock>

            <ConfigBlock label="题目数量">
              <div className="ios-count-grid">
                {questionCountOptions.map((count) => (
                  <button key={count} type="button" className={questionCount === count ? "active" : ""} onClick={() => setQuestionCount(count)}>
                    {count} 题
                  </button>
                ))}
              </div>
            </ConfigBlock>

            <div className="ios-setup-actions">
              <button type="button" className="ios-secondary-button" onClick={() => setPreviewExpanded((value) => !value)}>
                <Eye size={18} /> {previewExpanded ? "收起题目" : "预览题目"}
              </button>
              <button type="button" className="ios-primary-button" disabled={!selectedQuestions.length} onClick={startInterview}>
                <Play size={18} /> 开始模拟面试
              </button>
            </div>
          </div>

          <aside className="ios-side-stack">
            <ResumeProfileCard report={report} />
            <QuestionPreviewList questions={visiblePreviewQuestions} total={selectedQuestions.length} expanded={previewExpanded} onToggle={() => setPreviewExpanded((value) => !value)} />
            <article className="ios-agent-card ios-tip-card">
              <Sparkles size={18} />
              <div>
                <strong>温馨提示</strong>
                <p>面试中支持语音输入，系统会记录每题回答；空答也会进入报告，便于复盘回答完整度。</p>
              </div>
            </article>
          </aside>
        </section>
      )}

      {phase === "active" && currentQuestion && (
        <section className="ios-task-grid active">
          <div className="ios-agent-card ios-interview-room">
            <article className="ios-question-card">
              <div className="ios-question-meta">
                <span>第 {currentIndex + 1} / {selectedQuestions.length} 题</span>
                <span>{currentQuestion.category}</span>
                <span>{readableDifficulty(currentQuestion.difficulty)}</span>
              </div>
              <div className="ios-question-body">
                <div className="ios-interviewer-avatar"><Bot size={26} /></div>
                <div>
                  <span className="ios-shiny-text">AI 面试官正在提问</span>
                  <h2>{currentQuestion.question}</h2>
                  <p>{currentQuestion.why_ask || "请结合你的简历项目和实际经历作答，尽量说明技术动作、取舍和结果。"}</p>
                </div>
              </div>
              {voiceNotice && <p className="voice-notice">{voiceNotice}</p>}
              <button type="button" className="ios-secondary-button compact" disabled={speaking} onClick={playQuestionAudio}>
                <Volume2 size={16} /> {speaking ? "播放中" : "朗读题目"}
              </button>
            </article>

            <section className="ios-answer-card">
              <div className="ios-section-head compact">
                <div>
                  <h3>你的回答</h3>
                  <p>{scenario.answerMode === "voice" ? "点击麦克风后说话，转写结果会进入文本框；也可以手动补充。" : "直接输入文字回答，点击下一题时自动保存。"}</p>
                </div>
              </div>
              <textarea value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder="在这里输入或补充你的回答..." />
              <div className="transcript-status ios-transcript-status">
                <span className={voice.isRecording ? "live" : ""}>
                  {voice.isRecording ? "录音中" : voice.isRecognizing ? "正在识别语音" : answer.trim() ? "已输入回答" : "当前为空答，切换题目时会记录为未作答"}
                </span>
                {voice.error && <span>{voice.error}</span>}
              </div>
              {answerError && <p className="answer-error">{answerError}</p>}
            </section>

            <section className="ios-record-section">
              <div className="ios-section-head compact">
                <div>
                  <h3>实时答题记录</h3>
                  <p>每次点击下一题或提交面试，都会按题号覆盖保存当前答案。</p>
                </div>
              </div>
              <div className="ios-record-list">
                {qaHistory.length === 0 ? (
                  <article className="ios-record-empty">还没有保存记录。</article>
                ) : qaHistory.map((item, index) => (
                  <article className="ios-record-card" style={{ animationDelay: `${index * 45}ms` }} key={`${item.question_id}-${item.index}`}>
                    <strong><UserRound size={15} /> Q{(item.index ?? index) + 1}: {item.question}</strong>
                    <p className={item.empty ? "empty-answer" : ""}>{item.answer || "未作答"}</p>
                  </article>
                ))}
              </div>
            </section>
          </div>

          <aside className="ios-side-stack">
            <article className="ios-agent-card ios-interview-state">
              <h3>当前回答状态</h3>
              <div className="ios-progress-ring" style={{ "--progress": `${progressPercent}%` } as CSSProperties}>
                <strong>{progressPercent}%</strong>
              </div>
              <div className="ios-state-list">
                <span><CheckCircle2 size={15} /> 已记录 {qaHistory.length} / {selectedQuestions.length} 题</span>
                <span><Sparkles size={15} /> 追问：未开启</span>
                <span><ClipboardList size={15} /> {isLastQuestion ? "最后一题，提交后生成报告" : "下一题只保存并切换"}</span>
              </div>
            </article>

            <article className="ios-agent-card ios-current-preview">
              <h3>本题参考方向</h3>
              <ul>
                {(currentQuestion.answer_points || []).slice(0, 4).map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
              </ul>
            </article>

            <div className="ios-control-dock">
              <button
                type="button"
                className={`ios-dock-button ${voice.isRecording ? "recording" : ""}`}
                onClick={voice.toggleRecording}
                disabled={!voice.isSupported || voice.isRecognizing || scenario.answerMode !== "voice" || interviewStatus === "completed"}
              >
                {voice.isRecording ? <MicOff size={19} /> : <Mic size={19} />}
                <span>{voice.isRecording ? "结束录音" : voice.isRecognizing ? "识别中" : "语音输入"}</span>
              </button>
              {!isLastQuestion ? (
                <button type="button" className="ios-dock-button primary" disabled={processing} onClick={handleNextQuestion}>
                  <ChevronRight size={19} />
                  <span>下一题</span>
                </button>
              ) : (
                <button type="button" className="ios-dock-button primary" disabled={processing} onClick={handleSubmitInterview}>
                  <CheckCircle2 size={19} />
                  <span>{processing ? "生成中" : "提交面试"}</span>
                </button>
              )}
            </div>
          </aside>
        </section>
      )}

      {phase === "report" && finalReport && (
        <section className="ios-agent-card ios-report-summary">
          <div className="ios-report-head">
            <div>
              <div className="ios-eyebrow">
                <CheckCircle2 size={18} />
                <span>面试评估报告</span>
                <span className="ios-status-pill done">已完成</span>
              </div>
              <h2>{scoreLabel(finalReport.overall_score)} · {finalReport.overall_score}/100</h2>
              <p>{finalReport.summary}</p>
            </div>
            <div className="ios-report-actions">
              <button type="button" className="ios-secondary-button" onClick={() => window.print()}>
                <Download size={16} /> 导出报告
              </button>
              <button type="button" className="ios-primary-button compact" onClick={startInterview}>
                <RotateCcw size={16} /> 重新模拟
              </button>
            </div>
          </div>

          <div className="ios-score-grid">
            <ScoreCard label="表达能力" score={finalReport.dimension_scores.expression} />
            <ScoreCard label="技术准确性" score={finalReport.dimension_scores.technical_accuracy} />
            <ScoreCard label="项目理解深度" score={finalReport.dimension_scores.project_depth} />
            <ScoreCard label="回答完整度" score={finalReport.dimension_scores.answer_completeness} />
          </div>

          <div className="ios-report-grid">
            <ReportList title="优点" items={finalReport.strengths} />
            <ReportList title="问题" items={finalReport.problems} />
            <ReportList title="优化建议" items={finalReport.suggestions} />
            <ReportList title="推荐复习方向" items={finalReport.review_directions} />
          </div>

          <section className="ios-next-practice">
            <strong>下一步练习</strong>
            <p>{finalReport.next_practice}</p>
          </section>
        </section>
      )}
    </div>
  );
}

function ConfigBlock({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="ios-config-block">
      <label>{label}</label>
      {children}
    </div>
  );
}

function ResumeProfileCard({ report }: { report: Report }) {
  const projects = report.resume_profile.projects || [];
  return (
    <article className="ios-agent-card ios-profile-card">
      <div className="ios-section-head compact">
        <div>
          <h3>简历画像</h3>
          <p>AI 从上传简历中提取的岗位、技能和项目关键词。</p>
        </div>
      </div>
      <div className="ios-profile-position">
        <BriefcaseBusiness size={16} />
        <strong>{report.resume_profile.target_position || report.summary.target_position || "未明确"}</strong>
      </div>
      <div className="ios-chip-cloud">
        {[...report.resume_profile.skills.slice(0, 8), ...report.resume_profile.keywords.slice(0, 4)].filter(Boolean).map((item) => (
          <span key={item}>{item}</span>
        ))}
      </div>
      {projects.length > 0 && (
        <div className="ios-profile-projects">
          <strong>项目关键词</strong>
          <p>{projects.slice(0, 2).map((item) => item.name).join(" / ")}</p>
        </div>
      )}
    </article>
  );
}

function QuestionPreviewList({
  questions,
  total,
  expanded,
  onToggle,
}: {
  questions: Report["questions"];
  total: number;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <article className="ios-agent-card ios-preview-card">
      <div className="ios-section-head compact">
        <div>
          <h3>本场面试预览</h3>
          <p>默认只展示 3 条摘要，避免提前变成题库浏览。</p>
        </div>
      </div>
      <ol className="ios-preview-list">
        {questions.map((question, index) => (
          <li style={{ animationDelay: `${index * 50}ms` }} key={question.id}>
            <span>{index + 1}</span>
            <p>{question.question}</p>
          </li>
        ))}
      </ol>
      {total > 3 && (
        <button type="button" className="ios-link-button" onClick={onToggle}>
          {expanded ? "收起题目" : `查看全部题目（${total}）`}
        </button>
      )}
    </article>
  );
}

function ScoreCard({ label, score }: { label: string; score: number }) {
  return (
    <article className="ios-score-card">
      <span>{label}</span>
      <strong>{score}</strong>
      <small>/100</small>
    </article>
  );
}

function ReportList({ title, items }: { title: string; items: string[] }) {
  return (
    <article className="ios-report-list-card">
      <h3>{title}</h3>
      <ul>
        {items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
      </ul>
    </article>
  );
}
