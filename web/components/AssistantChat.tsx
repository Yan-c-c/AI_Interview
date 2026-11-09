"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Brain,
  Bot,
  ChevronDown,
  CheckCircle2,
  Clock3,
  ClipboardList,
  LogOut,
  Mail,
  MailCheck,
  MailPlus,
  Map,
  BadgeDollarSign,
  MessageSquareText,
  FileAudio,
  FileText,
  FileSearch,
  HelpCircle,
  History,
  Layers3,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  UserRound,
  UsersRound,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  chatWithAssistant,
  EvaluationStreamEvent,
  streamAssistantEvaluation,
  UploadResult,
} from "@/lib/api/assistant";
import type { AuthUser } from "@/lib/auth";
import { CareerPlanningReport as CareerReport } from "@/lib/api/careerPlanning";
import { CoverLetterReport as LetterReport } from "@/lib/api/coverLetter";
import { EmailCampaignReport as CampaignReport } from "@/lib/api/emailCampaign";
import { InterviewAudioAnalysisReport as AudioReport } from "@/lib/api/interviewAudio";
import { InterviewQuestionReport as QuestionReport } from "@/lib/api/interviewQuestion";
import { ResumeEvaluationReport as Report } from "@/lib/api/resumeEvaluation";
import { SalaryNegotiationReport as SalaryReport } from "@/lib/api/salaryNegotiation";
import { FileUploader } from "./FileUploader";
import {
  createInitialExperts,
  createInitialProgressSteps,
  EvaluationProgress,
  ExpertKey,
  ExpertState,
  ProgressSteps,
  updateExpertState,
  updateProgressSteps,
} from "./EvaluationProgress";
import { InterviewQuestionReport } from "./InterviewQuestionReport";
import { InterviewAudioReviewPanel } from "./InterviewAudioReviewPanel";
import { CareerPlanningPanel } from "./CareerPlanningPanel";
import { CoverLetterAgentPanel } from "./CoverLetterAgentPanel";
import { EmailCampaignPanel } from "./EmailCampaignPanel";
import { ResumeEvaluationReport } from "./ResumeEvaluationReport";
import { SalaryNegotiationPanel } from "./SalaryNegotiationPanel";

type ViewMode = "empty" | "interview_loading" | "audio_loading" | "letter_loading" | "career_loading" | "campaign_loading" | "salary_loading" | "meeting" | "report" | "questions" | "audio_review" | "cover_letter" | "career_planning" | "email_campaign" | "salary_negotiation" | "error";
type ChatMessage = { id: string; role: "user" | "assistant"; content: string; time: string };

function nowTime() {
  return new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

function createCampaignDraft(): CampaignReport {
  return {
    agent: "email_campaign_agent",
    task_type: "email_campaign",
    success: true,
    smtp_status: "unconfigured",
    status: "draft",
    subject: "",
    content: "",
    recipients_count: 0,
    attachments: [],
    send_summary: { total: 0, success: 0, failed: 0, pending: 0 },
    send_results: [],
    message: "邮件群发工作台已准备好。",
    metadata: {},
  };
}

function isResumeEvaluationRequest(text: string) {
  const normalized = text.trim().toLowerCase();
  if (!normalized) return false;
  return [
    /^(帮我)?(看看|评估|分析|优化|检查).{0,10}(这份|我的)?简历/,
    /^(这份|我的)?简历.{0,12}(有什么问题|评估|分析|优化|检查|风险|违禁词|模板|查重)/,
    /^看看我的简历能不能投/,
    /^帮我看看这份简历/,
    /^帮我优化一下简历/,
  ].some((pattern) => pattern.test(normalized));
}

function isInterviewQuestionRequest(text: string) {
  const normalized = text.trim().toLowerCase();
  if (!normalized) return false;
  return [
    /面试题/,
    /模拟面试/,
    /语音面试/,
    /面试练习题/,
    /(根据|基于).{0,8}简历.{0,12}(生成|出|准备|设计).{0,8}(面试题|问题|题目|练习题)/,
    /(帮我)?(出|生成|准备|设计).{0,12}(面试题|问题|题目|练习题)/,
    /(根据|基于).{0,8}简历.{0,12}问.{0,8}(问题|题目)/,
    /根据简历.{0,8}提问/,
    /题库/,
  ].some((pattern) => pattern.test(normalized));
}

function isInterviewAudioAnalysisRequest(text: string) {
  const normalized = text.trim().toLowerCase();
  if (!normalized) return false;
  return [
    /面试录音/,
    /录音分析/,
    /分析.*录音/,
    /音频分析/,
    /分析.*音频/,
    /面试对话分析/,
    /转写.*面试/,
  ].some((pattern) => pattern.test(normalized));
}

function isCoverLetterRequest(text: string) {
  const normalized = text.trim().toLowerCase();
  if (!normalized) return false;
  return [
    /求职信/,
    /cover letter/,
    /自荐信/,
    /申请信/,
    /申请邮件/,
    /内推信/,
    /导师申请/,
    /邮件正文/,
    /(写|生成|改写).{0,12}(求职信|自荐信|申请信|申请邮件|内推信)/,
  ].some((pattern) => pattern.test(normalized));
}

function isEmailCampaignRequest(text: string) {
  const normalized = text.trim().toLowerCase();
  if (!normalized) return false;
  return [
    /邮件群发/,
    /群发.*邮件/,
    /批量.*邮件/,
    /批量发送.*(求职信|求职邮件|邮件)/,
    /群发.*(求职信|求职邮件)/,
    /给这些.{0,8}(hr|招聘).{0,8}发邮件/i,
    /给.*(hr|招聘).{0,12}(发|发送).{0,6}邮件/i,
    /email campaign/,
  ].some((pattern) => pattern.test(normalized));
}

function isCareerPlanningRequest(text: string) {
  const normalized = text.trim().toLowerCase();
  if (!normalized) return false;
  return [
    /职业规划/,
    /发展路径/,
    /职业方向/,
    /职业建议/,
    /未来规划/,
    /转行/,
    /转岗/,
    /学习路线/,
    /学习路径/,
    /投递策略/,
    /岗位方向/,
    /求职规划/,
    /(规划|分析).{0,12}(职业|岗位|求职|发展)/,
  ].some((pattern) => pattern.test(normalized));
}

function isSalaryNegotiationRequest(text: string) {
  const normalized = text.trim().toLowerCase();
  if (!normalized) return false;
  return [
    /薪资/,
    /谈薪/,
    /offer/,
    /加薪/,
    /合理薪资/,
    /薪资预测/,
    /薪资谈判/,
    /hr.{0,8}(压价|报价|还价)/i,
    /(模拟|生成).{0,8}(薪资|谈薪).{0,8}(谈判|话术)/,
  ].some((pattern) => pattern.test(normalized));
}

export function AssistantChat({ currentUser, onSignOut }: { currentUser?: AuthUser; onSignOut?: () => void }) {
  const [message, setMessage] = useState("");
const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "你好，我是智能面试助手。你可以直接提问；上传简历后可以评估简历、生成模拟面试、写求职信、做职业规划、群发求职邮件或做薪资谈判分析，上传录音后可以做面试录音分析。",
      time: "现在",
    },
  ]);
  const [file, setFile] = useState<UploadResult | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [questionReport, setQuestionReport] = useState<QuestionReport | null>(null);
  const [audioReport, setAudioReport] = useState<AudioReport | null>(null);
  const [letterReport, setLetterReport] = useState<LetterReport | null>(null);
  const [careerReport, setCareerReport] = useState<CareerReport | null>(null);
  const [campaignReport, setCampaignReport] = useState<CampaignReport | null>(null);
  const [salaryReport, setSalaryReport] = useState<SalaryReport | null>(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [events, setEvents] = useState<EvaluationStreamEvent[]>([]);
  const [experts, setExperts] = useState<Record<ExpertKey, ExpertState>>(createInitialExperts());
  const [stepStatuses, setStepStatuses] = useState<ProgressSteps>(createInitialProgressSteps());
  const [viewMode, setViewMode] = useState<ViewMode>("empty");

  const currentConversationTitle = useMemo(() => {
    if (file) return `${file.filename}`;
    return "智能面试助手对话";
  }, [file]);

  async function handleSend() {
    if (loading) return;
    const content = message.trim();
    if (!content && !file) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: content || "我已上传简历文件",
      time: nowTime(),
    };
    setChatMessages((items) => [...items, userMessage]);
    setMessage("");

    if (!content && file) {
      const text = file.is_audio
        ? "我已收到你的面试录音。你可以发送“请分析这段面试录音”开始转写、问答切分和讲师审核流程。"
        : "我已收到你的简历文件。你可以继续提问，也可以发送“帮我看看这份简历”开始评估，发送“根据简历生成模拟面试”，或让我生成求职信、职业规划、群发求职邮件、薪资谈判策略。";
      setChatMessages((items) => [...items, { id: crypto.randomUUID(), role: "assistant", content: text, time: nowTime() }]);
      return;
    }

    const shouldEvaluateResume = isResumeEvaluationRequest(content);
    const shouldAnalyzeAudio = !shouldEvaluateResume && isInterviewAudioAnalysisRequest(content);
    const shouldGenerateQuestions = !shouldEvaluateResume && !shouldAnalyzeAudio && isInterviewQuestionRequest(content);
    const shouldEmailCampaign = !shouldEvaluateResume && !shouldAnalyzeAudio && !shouldGenerateQuestions && isEmailCampaignRequest(content);
    const shouldGenerateLetter = !shouldEvaluateResume && !shouldAnalyzeAudio && !shouldGenerateQuestions && !shouldEmailCampaign && isCoverLetterRequest(content);
    const shouldNegotiateSalary = !shouldEvaluateResume && !shouldAnalyzeAudio && !shouldGenerateQuestions && !shouldEmailCampaign && !shouldGenerateLetter && isSalaryNegotiationRequest(content);
    const shouldPlanCareer = !shouldEvaluateResume && !shouldAnalyzeAudio && !shouldGenerateQuestions && !shouldEmailCampaign && !shouldGenerateLetter && !shouldNegotiateSalary && isCareerPlanningRequest(content);
    if (!shouldEvaluateResume && !shouldGenerateQuestions && !shouldAnalyzeAudio && !shouldEmailCampaign && !shouldGenerateLetter && !shouldNegotiateSalary && !shouldPlanCareer) {
      setStatus("");
      setLoading(true);
      try {
        const response = await chatWithAssistant({ message: content });
        setChatMessages((items) => [
          ...items,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: response.message || "我理解了。",
            time: nowTime(),
          },
        ]);
        setViewMode("empty");
      } catch (error) {
        const text = error instanceof Error ? error.message : "大模型对话失败";
        setStatus(text);
        setChatMessages((items) => [...items, { id: crypto.randomUUID(), role: "assistant", content: text, time: nowTime() }]);
      } finally {
        setLoading(false);
      }
      return;
    }

    if (shouldAnalyzeAudio) {
      if (!file) {
        const text = "我识别到你想分析面试录音，请先上传音频文件，然后再发送分析请求。";
        setStatus(text);
        setChatMessages((items) => [...items, { id: crypto.randomUUID(), role: "assistant", content: text, time: nowTime() }]);
        return;
      }
      if (!file.is_audio) {
        const text = "当前上传的是简历文件。面试录音分析需要上传 mp3、wav、m4a 等音频文件。";
        setStatus(text);
        setChatMessages((items) => [...items, { id: crypto.randomUUID(), role: "assistant", content: text, time: nowTime() }]);
        return;
      }
      setReport(null);
      setQuestionReport(null);
      setAudioReport(null);
      setLetterReport(null);
      setCareerReport(null);
      setCampaignReport(null);
      setSalaryReport(null);
      setStatus("正在提交百度音频文件转写任务，并准备面试录音分析...");
      setLoading(true);
      setViewMode("audio_loading");
      setChatMessages((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "我已识别到面试录音分析需求，正在进行音频文件转写、话者识别、题目切分和答案评估。",
          time: nowTime(),
        },
      ]);
      try {
        const response = await chatWithAssistant({ message: content, file_id: file.file_id });
        const result = response.result as AudioReport | undefined;
        if (response.success && result?.task_type === "interview_audio_analysis") {
          setAudioReport(result);
          setViewMode("audio_review");
          const isTranscribing = result.status === "transcribing" || result.review_status === "transcribing";
          setStatus(response.message || (isTranscribing ? "百度音频文件转写仍在处理中。" : "面试录音分析已完成。"));
          setChatMessages((items) => [
            ...items,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content: isTranscribing
                ? "百度音频文件转写任务已提交。长音频需要等待一段时间，右侧可以点击“刷新结果”继续获取转写和分析结果。"
                : "面试录音分析已完成，右侧已进入讲师快速审核界面。",
              time: nowTime(),
            },
          ]);
        } else {
          const text = response.message || "面试录音分析未完成，请检查百度音频文件转写配置。";
          setStatus(text);
          setViewMode("error");
        }
      } catch (error) {
        const text = error instanceof Error ? error.message : "面试录音分析失败";
        setStatus(text);
        setViewMode("error");
        setChatMessages((items) => [...items, { id: crypto.randomUUID(), role: "assistant", content: text, time: nowTime() }]);
      } finally {
        setLoading(false);
      }
      return;
    }

    if (shouldGenerateQuestions) {
      if (!file) {
        const text = "我识别到你想根据简历进行模拟面试，请先上传简历文件，然后再发送生成请求。";
        setStatus(text);
        setChatMessages((items) => [...items, { id: crypto.randomUUID(), role: "assistant", content: text, time: nowTime() }]);
        return;
      }

      setReport(null);
      setQuestionReport(null);
      setLetterReport(null);
      setCareerReport(null);
      setCampaignReport(null);
      setSalaryReport(null);
      setStatus("正在提取简历画像、检索面试知识库并准备模拟面试...");
      setLoading(true);
      setViewMode("interview_loading");
      setChatMessages((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "我已识别到模拟面试需求，正在基于简历画像检索题库并准备个性化面试流程。",
          time: nowTime(),
        },
      ]);

      try {
        const response = await chatWithAssistant({ message: content, file_id: file.file_id });
        const result = response.result as QuestionReport | undefined;
        if (response.success && result?.task_type === "interview_question_generation") {
          setQuestionReport(result);
          setViewMode("questions");
          setStatus(response.message || "模拟面试已准备好。");
          setChatMessages((items) => [
            ...items,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content: "模拟面试已准备好，你可以在右侧选择岗位、难度、面试形式，然后开始语音或文字面试。",
              time: nowTime(),
            },
          ]);
        } else {
          const text = response.message || "模拟面试准备失败，请稍后重试。";
          setStatus(text);
          setViewMode("error");
        }
      } catch (error) {
        const text = error instanceof Error ? error.message : "模拟面试准备失败";
        setStatus(text);
        setViewMode("error");
        setChatMessages((items) => [...items, { id: crypto.randomUUID(), role: "assistant", content: text, time: nowTime() }]);
      } finally {
        setLoading(false);
      }
      return;
    }

    if (shouldEmailCampaign) {
      setReport(null);
      setQuestionReport(null);
      setAudioReport(null);
      setLetterReport(null);
      setCareerReport(null);
      setCampaignReport(null);
      setCampaignReport(null);
      setSalaryReport(null);
      setStatus("正在打开邮件群发 Agent 工作台...");
      setLoading(true);
      setViewMode("campaign_loading");
      setChatMessages((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "我已识别到邮件群发需求，正在准备 SMTP 配置、收件人管理、AI 邮件生成和发送预览工作台。",
          time: nowTime(),
        },
      ]);
      try {
        const response = await chatWithAssistant({ message: content, file_id: file?.is_audio ? undefined : file?.file_id });
        const result = response.result as CampaignReport | undefined;
        if (response.success && result?.task_type === "email_campaign") {
          setCampaignReport(result);
          setViewMode("email_campaign");
          setStatus(response.message || "邮件群发工作台已准备好。");
          setChatMessages((items) => [
            ...items,
            { id: crypto.randomUUID(), role: "assistant", content: "邮件群发工作台已打开。请在右侧配置 SMTP、添加 HR 收件人、生成邮件内容并预览确认后发送。", time: nowTime() },
          ]);
        } else {
          const text = response.message || "邮件群发 Agent 打开失败，请稍后重试。";
          setStatus(text);
          setViewMode("error");
        }
      } catch (error) {
        const text = error instanceof Error ? error.message : "邮件群发 Agent 打开失败";
        setStatus(text);
        setViewMode("error");
        setChatMessages((items) => [...items, { id: crypto.randomUUID(), role: "assistant", content: text, time: nowTime() }]);
      } finally {
        setLoading(false);
      }
      return;
    }

    if (shouldGenerateLetter) {
      setReport(null);
      setQuestionReport(null);
      setAudioReport(null);
      setLetterReport(null);
      setCareerReport(null);
      setCampaignReport(null);
      setSalaryReport(null);
      setStatus("正在读取简历/背景并调用 DeepSeek 生成求职信...");
      setLoading(true);
      setViewMode("letter_loading");
      setChatMessages((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: file
            ? "我已识别到求职信生成需求，正在结合简历和你的补充信息生成多版本求职信。"
            : "我已识别到求职信生成需求。未上传简历时也可以先生成草稿，但上传简历会更精准。",
          time: nowTime(),
        },
      ]);
      try {
        const response = await chatWithAssistant({ message: content, file_id: file?.is_audio ? undefined : file?.file_id });
        const result = response.result as LetterReport | undefined;
        if (response.success && result?.task_type === "cover_letter_generation") {
          setLetterReport(result);
          setViewMode("cover_letter");
          setStatus(response.message || "求职信已生成。");
          setChatMessages((items) => [
            ...items,
            { id: crypto.randomUUID(), role: "assistant", content: "求职信已生成，你可以在右侧切换版本、继续改写、导出或发送邮件。", time: nowTime() },
          ]);
        } else {
          const text = response.message || "求职信生成失败，请稍后重试。";
          setStatus(text);
          setViewMode("error");
        }
      } catch (error) {
        const text = error instanceof Error ? error.message : "求职信生成失败";
        setStatus(text);
        setViewMode("error");
        setChatMessages((items) => [...items, { id: crypto.randomUUID(), role: "assistant", content: text, time: nowTime() }]);
      } finally {
        setLoading(false);
      }
      return;
    }

    if (shouldNegotiateSalary) {
      setReport(null);
      setQuestionReport(null);
      setAudioReport(null);
      setLetterReport(null);
      setCareerReport(null);
      setCampaignReport(null);
      setSalaryReport(null);
      setStatus("正在融合薪资 demo 数据、预测区间和 DeepSeek 谈薪策略...");
      setLoading(true);
      setViewMode("salary_loading");
      setChatMessages((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: file && !file.is_audio
            ? "我已识别到薪资谈判需求，正在结合简历、岗位信息、薪资 demo 数据和 DeepSeek 生成谈薪策略。"
            : "我已识别到薪资谈判需求。未上传简历也可以先做薪资预测和谈薪模拟，上传简历后会更精准。",
          time: nowTime(),
        },
      ]);
      try {
        const response = await chatWithAssistant({ message: content, file_id: file?.is_audio ? undefined : file?.file_id });
        const result = response.result as SalaryReport | undefined;
        if (response.success && result?.task_type === "salary_negotiation") {
          setSalaryReport(result);
          setViewMode("salary_negotiation");
          setStatus(response.message || "薪资谈判工作台已生成。");
          setChatMessages((items) => [
            ...items,
            { id: crypto.randomUUID(), role: "assistant", content: "薪资谈判工作台已打开，你可以在右侧查看预测区间、趋势、职位对比、谈判模拟和 DeepSeek 话术。", time: nowTime() },
          ]);
        } else {
          const text = response.message || "薪资谈判 Agent 打开失败，请稍后重试。";
          setStatus(text);
          setViewMode("error");
        }
      } catch (error) {
        const text = error instanceof Error ? error.message : "薪资谈判 Agent 打开失败";
        setStatus(text);
        setViewMode("error");
        setChatMessages((items) => [...items, { id: crypto.randomUUID(), role: "assistant", content: text, time: nowTime() }]);
      } finally {
        setLoading(false);
      }
      return;
    }

    if (shouldPlanCareer) {
      setReport(null);
      setQuestionReport(null);
      setAudioReport(null);
      setLetterReport(null);
      setCareerReport(null);
      setSalaryReport(null);
      setStatus("正在提取简历画像并调用 DeepSeek 生成职业规划...");
      setLoading(true);
      setViewMode("career_loading");
      setChatMessages((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: file
            ? "我已识别到职业规划需求，正在结合简历、目标方向和求职阶段分析能力差距。"
            : "我已识别到职业规划需求。你可以不上传简历直接使用，但上传简历会获得更精准结果。",
          time: nowTime(),
        },
      ]);
      try {
        const response = await chatWithAssistant({ message: content, file_id: file?.is_audio ? undefined : file?.file_id });
        const result = response.result as CareerReport | undefined;
        if (response.success && result?.task_type === "career_planning") {
          setCareerReport(result);
          setViewMode("career_planning");
          setStatus(response.message || "职业规划已生成。");
          setChatMessages((items) => [
            ...items,
            { id: crypto.randomUUID(), role: "assistant", content: "职业规划已生成，你可以在右侧查看能力差距、学习路径、项目补强和投递策略。", time: nowTime() },
          ]);
        } else {
          const text = response.message || "职业规划生成失败，请稍后重试。";
          setStatus(text);
          setViewMode("error");
        }
      } catch (error) {
        const text = error instanceof Error ? error.message : "职业规划生成失败";
        setStatus(text);
        setViewMode("error");
        setChatMessages((items) => [...items, { id: crypto.randomUUID(), role: "assistant", content: text, time: nowTime() }]);
      } finally {
        setLoading(false);
      }
      return;
    }

    if (!file) {
      const text = "我识别到你想进行简历评估，请先上传简历文件，然后再发送评估请求。";
      setStatus(text);
      setChatMessages((items) => [...items, { id: crypto.randomUUID(), role: "assistant", content: text, time: nowTime() }]);
      return;
    }

    setReport(null);
    setQuestionReport(null);
    setAudioReport(null);
    setLetterReport(null);
    setCareerReport(null);
    setCampaignReport(null);
    setCampaignReport(null);
    setSalaryReport(null);
    setStatus("");
    setEvents([]);
    setExperts(createInitialExperts());
    setStepStatuses({ ...createInitialProgressSteps(), file: "running" });
    setViewMode("meeting");
    setLoading(true);
    setChatMessages((items) => [
      ...items,
      {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "我已识别到简历评估需求，正在启动多专家圆桌会议，请稍等。",
        time: nowTime(),
      },
    ]);

    try {
      await streamAssistantEvaluation(
        {
          message: content,
          file_id: file?.file_id,
        },
        (event) => {
          if (event.type === "done") return;
          setEvents((items) => [...items, event]);
          setExperts((state) => updateExpertState(state, event));
          setStepStatuses((state) => updateProgressSteps(state, event));

          if (event.type === "result") {
            if (event.success && event.result?.metadata?.used_llm_roundtable) {
              setReport(event.result);
              setStepStatuses({
                file: "done",
                tools: "done",
                roundtable: "done",
                reflector: "done",
                report: "done",
              });
              setViewMode("report");
              setStatus(event.message || "简历评估报告已生成。");
              setChatMessages((items) => [
                ...items,
                {
                  id: crypto.randomUUID(),
                  role: "assistant",
                  content: "简历评估报告已生成，你可以在右侧查看完整结果。",
                  time: nowTime(),
                },
              ]);
            } else {
              setViewMode("error");
              setStatus(event.message || "AI 圆桌会议未生成报告，请检查后端 DeepSeek 配置。");
            }
          }
        },
      );
    } catch (error) {
      setViewMode("error");
      setStatus(error instanceof Error ? error.message : "请求失败");
    } finally {
      setLoading(false);
    }
  }

  function resetConversation() {
    setReport(null);
    setQuestionReport(null);
    setAudioReport(null);
    setLetterReport(null);
    setCareerReport(null);
    setCampaignReport(null);
    setSalaryReport(null);
    setChatMessages([
      {
        id: "welcome",
        role: "assistant",
        content: "你好，我是智能面试助手。你可以直接提问；上传简历后可以评估简历、生成模拟面试、写求职信、做职业规划、群发求职邮件或做薪资谈判分析，上传录音后可以做面试录音分析。",
        time: "现在",
      },
    ]);
    setEvents([]);
    setExperts(createInitialExperts());
    setStepStatuses(createInitialProgressSteps());
    setViewMode("empty");
    setStatus("");
  }

  return (
    <main className="product-shell">
      <header className="topbar">
        <div className="product-brand">
          <div className="brand-icon">
            <Bot size={28} />
          </div>
          <h1>智能面试助手</h1>
          <span>AI</span>
        </div>
        <nav className="top-actions">
          <button type="button" className={viewMode === "cover_letter" ? "active" : ""} onClick={() => setViewMode(letterReport ? "cover_letter" : "empty")}>
            <Mail size={16} />求职信
          </button>
          <button
            type="button"
            className={viewMode === "email_campaign" ? "active" : ""}
            onClick={() => {
              setCampaignReport((current) => current || createCampaignDraft());
              setViewMode("email_campaign");
            }}
          >
            <MailPlus size={16} />邮件群发
          </button>
          <button type="button" className={viewMode === "career_planning" ? "active" : ""} onClick={() => setViewMode(careerReport ? "career_planning" : "empty")}>
            <Map size={16} />职业规划
          </button>
          <button type="button" className={viewMode === "salary_negotiation" ? "active" : ""} onClick={() => setViewMode(salaryReport ? "salary_negotiation" : "empty")}>
            <BadgeDollarSign size={16} />薪资谈判
          </button>
          <button type="button"><History size={16} />历史会话</button>
          <button type="button"><HelpCircle size={16} />使用指南</button>
          {currentUser?.role === "admin" && (
            <button type="button" onClick={() => { window.location.href = "/admin"; }}>
              <ShieldCheck size={16} />后台管理
            </button>
          )}
          {onSignOut && (
            <button type="button" onClick={onSignOut}>
              <LogOut size={16} />退出
            </button>
          )}
          <div className="user-chip">
            <div className="user-avatar"><UserRound size={18} /></div>
            <strong>{currentUser?.name || "用户"}</strong>
            <ChevronDown size={14} />
          </div>
        </nav>
      </header>

      <div className="app-board">
        <aside className="conversation-rail">
          <div className="rail-tabs">
            <button type="button" onClick={resetConversation}>新建会话</button>
            <button type="button" className="active">当前会话</button>
          </div>

          <div className="chat-thread">
            {chatMessages.map((item) => (
              item.role === "user" ? (
                <div className="bubble user-bubble" key={item.id}>
                  <p>{item.content}</p>
                  <time>{item.time}</time>
                </div>
              ) : (
                <div className="assistant-row" key={item.id}>
                  <div className="mini-bot"><Bot size={16} /></div>
                  <div className="bubble assistant-bubble">
                    <p>{item.content}</p>
                    <time>{item.time}</time>
                  </div>
                </div>
              )
            ))}
            {file && (
              <div className="file-card-chat">
                <div className="pdf-icon"><FileText size={20} /></div>
              <div>
                <strong>{file.filename}</strong>
                  <p>{file.is_audio ? file.file_type.toUpperCase() : `${(file.parsed_char_count / 1000).toFixed(1)} K chars`}</p>
              </div>
                <span>✓</span>
              </div>
            )}
          </div>

          <div className="composer">
            <FileUploader
              file={file}
              loading={uploading}
              onLoadingChange={setUploading}
              onUploaded={(uploaded) => {
                setFile(uploaded);
                setStatus(`已收到${uploaded.is_audio ? "录音" : "简历"}：${uploaded.filename}`);
              }}
              onError={setStatus}
            />
            <div className="composer-input-row">
              <textarea
                value={message}
                placeholder="输入你的问题..."
                onChange={(event) => setMessage(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void handleSend();
                  }
                }}
              />
              <div className="composer-actions">
                <button type="button" className="send-button" disabled={loading || uploading} onClick={handleSend} aria-label="发送">
                  <Send size={18} />
                </button>
              </div>
            </div>
          </div>

          <p className="ai-note">内容由 AI 生成，仅供参考，请结合实际情况判断。</p>
        </aside>

        <section className="main-workspace">
          {viewMode === "meeting" && (
            <EvaluationProgress
              experts={experts}
              events={events}
              stepStatuses={stepStatuses}
              onAbort={() => {
                setViewMode("error");
                setStatus("已停止当前可视化等待。");
              }}
            />
          )}

          {viewMode === "report" && report && <ResumeEvaluationReport report={report} />}

          {viewMode === "questions" && questionReport && <InterviewQuestionReport report={questionReport} />}

          {viewMode === "audio_review" && audioReport && (
            <InterviewAudioReviewPanel report={audioReport} onUpdated={setAudioReport} canManage={currentUser?.role === "admin"} />
          )}

          {viewMode === "cover_letter" && letterReport && (
            <CoverLetterAgentPanel report={letterReport} fileId={file?.file_id} onUpdated={setLetterReport} />
          )}

          {viewMode === "career_planning" && careerReport && (
            <CareerPlanningPanel report={careerReport} onUpdated={setCareerReport} />
          )}

          {viewMode === "email_campaign" && (
            <EmailCampaignPanel report={campaignReport} fileId={file?.is_audio ? undefined : file?.file_id} onUpdated={setCampaignReport} />
          )}

          {viewMode === "salary_negotiation" && salaryReport && (
            <SalaryNegotiationPanel report={salaryReport} fileId={file?.is_audio ? undefined : file?.file_id} onUpdated={setSalaryReport} />
          )}

          {viewMode === "interview_loading" && file && (
            <InterviewGenerationMotion filename={file.filename} parsedCharCount={file.parsed_char_count} />
          )}

          {viewMode === "audio_loading" && file && (
            <InterviewAudioMotion filename={file.filename} />
          )}

          {viewMode === "letter_loading" && (
            <AgentDocumentMotion title="正在生成个性化求职信" subtitle="DeepSeek 正在结合简历画像、目标岗位、求职信风格和重点亮点生成多版本内容。" icon="letter" />
          )}

          {viewMode === "career_loading" && (
            <AgentDocumentMotion title="正在生成职业规划方案" subtitle="DeepSeek 正在分析当前能力、目标岗位差距、学习路径、项目补强和投递策略。" icon="career" />
          )}

          {viewMode === "campaign_loading" && (
            <AgentDocumentMotion title="正在打开邮件群发工作台" subtitle="系统正在准备 SMTP 配置、收件人校验、AI 邮件生成、附件和发送预览流程。" icon="campaign" />
          )}

          {viewMode === "salary_loading" && (
            <AgentDocumentMotion title="正在生成薪资谈判方案" subtitle="系统正在读取薪资 demo 数据、预测合理区间、分析趋势、模拟谈判并生成 DeepSeek 话术。" icon="salary" />
          )}

          {viewMode === "error" && (
            <div className="empty-report error-state">
              <Trash2 size={34} />
              <h2>未生成 AI 评估报告</h2>
              <p>{status || "请检查 backend/.env 中的 DeepSeek 配置后重新评估。"}</p>
              <button type="button" className="primary-button" onClick={handleSend}>重新评估</button>
            </div>
          )}

          {viewMode === "empty" && (
            file ? (
              file.is_audio ? <AudioReadyMotion filename={file.filename} /> : <ResumeReadyMotion filename={file.filename} parsedCharCount={file.parsed_char_count} />
            ) : (
              <div className="empty-report">
                <Clock3 size={42} />
                <h2>智能面试助手</h2>
                <p>普通问题会直接进入大模型对话；明确提出简历评估、模拟面试、求职信或职业规划时，系统会调度对应 Agent。</p>
                <div className="empty-hint">
                  <strong>当前会话</strong>
                  <span>{currentConversationTitle}</span>
                </div>
              </div>
            )
          )}
        </section>
      </div>
    </main>
  );
}

function ResumeReadyMotion({ filename, parsedCharCount }: { filename: string; parsedCharCount: number }) {
  return (
    <section className="interview-motion-screen ready">
      <div className="motion-orbit" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div className="motion-copy">
        <div className="motion-badge"><CheckCircle2 size={16} /> 简历已接收</div>
        <h2>等待你的下一步指令</h2>
        <p>你可以发送“根据简历生成模拟面试”，右侧会动态展示简历解析、画像提取、题库检索和个性化提问生成过程。</p>
      </div>
      <div className="motion-document-card">
        <div className="motion-doc-icon"><FileText size={26} /></div>
        <div>
          <strong>{filename}</strong>
          <span>{parsedCharCount} 字 · 已完成解析</span>
        </div>
        <div className="motion-scan-line" />
      </div>
    </section>
  );
}

type MotionStep = {
  title: string;
  state?: string;
  icon: LucideIcon;
};

function useLinearMotionProgress(stepCount: number) {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    setActiveStep(0);
    const timers = Array.from({ length: Math.max(0, stepCount - 1) }, (_, index) =>
      window.setTimeout(() => setActiveStep(index + 1), 1600 * (index + 1))
    );
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [stepCount]);

  return activeStep;
}

function MotionFlowSteps({ steps, activeStep, showDescriptions = true }: { steps: MotionStep[]; activeStep: number; showDescriptions?: boolean }) {
  return (
    <div className="motion-flow-grid">
      {steps.map((step, index) => {
        const Icon = step.icon;
        const stateClass = index < activeStep ? "is-complete" : index === activeStep ? "is-active" : "is-pending";
        return (
          <article className={`motion-flow-card ${stateClass}`} key={step.title}>
            <div className="motion-step-index">{index + 1}</div>
            <Icon size={24} />
            <div>
              <strong>{step.title}</strong>
              {showDescriptions && step.state && <span>{step.state}</span>}
            </div>
          </article>
        );
      })}
    </div>
  );
}

function CurrentMotionStep({ steps, activeStep }: { steps: MotionStep[]; activeStep: number }) {
  const current = steps[activeStep] || steps[steps.length - 1];
  return (
    <div className="motion-current-step">
      <CheckCircle2 size={16} />
      <span>当前步骤：{current.title}</span>
      {current.state && <em>{current.state}</em>}
    </div>
  );
}

function InterviewGenerationMotion({ filename, parsedCharCount }: { filename: string; parsedCharCount: number }) {
  const steps = [
    { title: "简历解析", state: "读取正文、项目和技能模块", icon: FileSearch },
    { title: "画像提取", state: "提取岗位、技能栈和项目关键词", icon: Brain },
    { title: "题库参考", state: "参考真实面试题库和面试宝典", icon: Layers3 },
    { title: "个性化提问", state: "组合项目深挖、技术基础和场景题", icon: Sparkles },
    { title: "面试准备", state: "准备语音 / 文字模拟面试工作台", icon: CheckCircle2 },
  ];
  const activeStep = useLinearMotionProgress(steps.length);

  return (
    <section className="interview-motion-screen generating">
      <div className="motion-copy">
        <div className="motion-badge running"><Sparkles size={16} /> 模拟面试生成中</div>
        <h2>正在把简历转成一场个性化面试</h2>
        <p>系统正在完成“简历解析 → 画像提取 → 参考真实题库和面试宝典 → 个性化提问 → 准备面试工作台”。生成完成后，会自动切回模拟面试配置界面。</p>
        <CurrentMotionStep steps={steps} activeStep={activeStep} />
      </div>

      <MotionFlowSteps steps={steps} activeStep={activeStep} />

      <div className="motion-lab-grid">
        <article className="motion-document-card active">
          <div className="motion-doc-icon"><FileText size={26} /></div>
          <div>
            <strong>{filename}</strong>
            <span>{parsedCharCount} 字 · 正在生成简历画像</span>
          </div>
          <div className="motion-scan-line" />
        </article>

        <article className="motion-preview-skeleton">
          <div className="skeleton-title" />
          <div className="skeleton-line wide" />
          <div className="skeleton-line" />
          <div className="skeleton-chip-row">
            <span />
            <span />
            <span />
          </div>
        </article>

        <article className="motion-question-stack">
          {[0, 1, 2].map((item) => (
            <div className="motion-question-row" style={{ animationDelay: `${item * 220}ms` }} key={item}>
              <span>{item + 1}</span>
              <div>
                <i />
                <i />
              </div>
            </div>
          ))}
        </article>
      </div>
    </section>
  );
}

function AudioReadyMotion({ filename }: { filename: string }) {
  return (
    <section className="interview-motion-screen ready audio-ready">
      <div className="motion-orbit" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div className="motion-copy">
        <div className="motion-badge"><FileAudio size={16} /> 录音已接收</div>
        <h2>等待启动面试录音分析</h2>
        <p>发送“请分析这段面试录音”后，系统会使用百度音频文件转写接口、DeepSeek 话者识别、知识库检索和讲师快速审核流程。</p>
      </div>
      <div className="motion-document-card">
        <div className="motion-doc-icon"><FileAudio size={26} /></div>
        <div>
          <strong>{filename}</strong>
          <span>音频文件 · 等待转写</span>
        </div>
        <div className="motion-scan-line" />
      </div>
    </section>
  );
}

function InterviewAudioMotion({ filename }: { filename: string }) {
  const steps = [
    { title: "提交转写任务", state: "调用百度音频文件转写 API，pid=8953 开启话者分离", icon: FileAudio },
    { title: "识别说话人", state: "DeepSeek 判断面试官与面试者角色", icon: Brain },
    { title: "切分问答", state: "提取面试题、追问和候选人回答", icon: FileSearch },
    { title: "检索正确答案", state: "优先参考面试知识库，再补充百度 AI 搜索", icon: Layers3 },
    { title: "生成审核页", state: "整理评分、证据来源和入库审核记录", icon: CheckCircle2 },
  ];
  const activeStep = useLinearMotionProgress(steps.length);

  return (
    <section className="interview-motion-screen generating audio-generating">
      <div className="motion-copy">
        <div className="motion-badge running"><Sparkles size={16} /> 面试录音分析中</div>
        <h2>正在把录音转成可审核的面试问答</h2>
        <p>系统正在完成“音频转写 → 话者识别 → 问答切分 → 正确答案检索 → 回答准确性评估 → 快速审核页”。</p>
        <CurrentMotionStep steps={steps} activeStep={activeStep} />
      </div>
      <MotionFlowSteps steps={steps} activeStep={activeStep} />
      <div className="motion-lab-grid">
        <article className="motion-document-card active">
          <div className="motion-doc-icon"><FileAudio size={26} /></div>
          <div>
            <strong>{filename}</strong>
            <span>正在等待百度转写结果</span>
          </div>
          <div className="motion-scan-line" />
        </article>
        <article className="motion-preview-skeleton">
          <div className="skeleton-title" />
          <div className="skeleton-line wide" />
          <div className="skeleton-line" />
          <div className="skeleton-chip-row"><span /><span /><span /></div>
        </article>
        <article className="motion-question-stack">
          {[0, 1, 2].map((item) => (
            <div className="motion-question-row" style={{ animationDelay: `${item * 220}ms` }} key={item}>
              <span>{item + 1}</span>
              <div><i /><i /></div>
            </div>
          ))}
        </article>
      </div>
    </section>
  );
}

function AgentDocumentMotion({ title, subtitle, icon }: { title: string; subtitle: string; icon: "letter" | "career" | "campaign" | "salary" }) {
  const Icon = icon === "letter" ? Mail : icon === "campaign" ? MailPlus : icon === "salary" ? BadgeDollarSign : Map;
  const steps = icon === "letter"
    ? [
      { title: "读取简历画像", icon: FileSearch },
      { title: "识别岗位诉求", icon: Brain },
      { title: "生成多版本求职信", icon: Sparkles },
      { title: "准备导出与邮件", icon: Mail },
    ]
    : icon === "campaign"
      ? [
        { title: "准备 SMTP 配置", icon: MailCheck },
        { title: "校验收件人列表", icon: UsersRound },
        { title: "生成求职邮件", icon: Sparkles },
        { title: "整理预览与发送记录", icon: ClipboardList },
      ]
      : icon === "salary"
        ? [
          { title: "读取薪资 demo 数据", icon: FileSearch },
          { title: "预测合理薪资区间", icon: BadgeDollarSign },
          { title: "模拟谈薪博弈", icon: MessageSquareText },
          { title: "生成谈薪话术", icon: Sparkles },
        ]
      : [
        { title: "抽取能力画像", icon: FileSearch },
        { title: "分析岗位差距", icon: Brain },
        { title: "规划学习路径", icon: Map },
        { title: "整理行动清单", icon: CheckCircle2 },
      ];
  const activeStep = useLinearMotionProgress(steps.length);
  return (
    <section className="interview-motion-screen generating agent-document-motion">
      <div className="motion-copy">
        <div className="motion-badge running"><Icon size={16} /> Agent 处理中</div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
        <CurrentMotionStep steps={steps} activeStep={activeStep} />
      </div>
      <MotionFlowSteps steps={steps} activeStep={activeStep} showDescriptions={false} />
      <div className="motion-lab-grid">
        <article className="motion-preview-skeleton">
          <div className="skeleton-title" />
          <div className="skeleton-line wide" />
          <div className="skeleton-line" />
          <div className="skeleton-chip-row"><span /><span /><span /></div>
        </article>
        <article className="motion-question-stack">
          {[0, 1, 2].map((item) => (
            <div className="motion-question-row" style={{ animationDelay: `${item * 180}ms` }} key={item}>
              <span>{item + 1}</span>
              <div><i /><i /></div>
            </div>
          ))}
        </article>
      </div>
    </section>
  );
}
