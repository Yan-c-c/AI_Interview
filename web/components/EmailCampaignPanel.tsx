"use client";

import { ChangeEvent, ReactNode, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ClipboardList,
  Eye,
  MailCheck,
  Paperclip,
  Plus,
  RefreshCw,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  Upload,
  UsersRound,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  Alert,
  AlertDescription,
  Badge,
  Button,
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Checkbox,
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
  Field,
  FieldContent,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldSet,
  Input,
  ScrollArea,
  Separator,
  Spinner,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Textarea,
} from "@/components/BasicUI";
import {
  CampaignAttachment,
  createEmailCampaign,
  defaultSmtpConfig,
  EmailCampaignReport,
  EmailRecipient,
  generateCampaignContent,
  polishCampaignContent,
  sendEmailCampaign,
  SmtpConfig,
  testEmailCampaignSmtp,
  uploadCampaignAttachment,
} from "@/lib/api/emailCampaign";
import { cn } from "@/lib/utils";

interface Props {
  report: EmailCampaignReport | null;
  fileId?: string;
  onUpdated?: (report: EmailCampaignReport) => void;
}

type StepValue = "smtp" | "recipients" | "content" | "preview";

const STEPS: Array<{ value: StepValue; label: string; icon: LucideIcon }> = [
  { value: "smtp", label: "SMTP 配置", icon: MailCheck },
  { value: "recipients", label: "收件人", icon: UsersRound },
  { value: "content", label: "邮件内容", icon: Sparkles },
  { value: "preview", label: "预览发送", icon: Send },
];

const EMAIL_RE = /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/;

function cleanGeneratedText(text?: string) {
  return (text || "")
    .replace(/\\r\\n|\\n|\/n/g, "\n")
    .replace(/\\t/g, "  ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function renderTemplate(template: string, recipient?: EmailRecipient) {
  const fallback = recipient || {
    name: "HR",
    company: "目标公司",
    position: "目标岗位",
    email: "",
  };
  return cleanGeneratedText(template)
    .replace(/\{\{\s*name\s*\}\}/gi, fallback.name || "您好")
    .replace(/\{\{\s*company\s*\}\}/gi, fallback.company || "贵公司")
    .replace(/\{\{\s*position\s*\}\}/gi, fallback.position || "相关岗位");
}

function parseRecipients(text: string): EmailRecipient[] {
  const chunks = text
    .split(/[\n;,，；]+/)
    .map((item) => item.trim())
    .filter(Boolean);
  return chunks.map((chunk) => {
    const email =
      chunk.match(/[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}/)?.[0] ||
      chunk;
    const name = chunk.replace(email, "").replace(/[<>()（）]/g, "").trim();
    return { id: crypto.randomUUID(), name, email, company: "", position: "", note: "" };
  });
}

export function EmailCampaignPanel({ report, fileId, onUpdated }: Props) {
  const [activeTab, setActiveTab] = useState<StepValue>("smtp");
  const [smtpConfig, setSmtpConfig] = useState<SmtpConfig>(defaultSmtpConfig);
  const [smtpStatus, setSmtpStatus] = useState<"idle" | "testing" | "success" | "failed">("idle");
  const [recipients, setRecipients] = useState<EmailRecipient[]>([]);
  const [batchText, setBatchText] = useState("");
  const [subject, setSubject] = useState(report?.subject || "");
  const [content, setContent] = useState(report?.content || "");
  const [targetCompany, setTargetCompany] = useState("");
  const [targetPosition, setTargetPosition] = useState("");
  const [purpose, setPurpose] = useState("投递简历");
  const [style, setStyle] = useState("自然真诚");
  const [personalize, setPersonalize] = useState(true);
  const [attachments, setAttachments] = useState<CampaignAttachment[]>(report?.attachments || []);
  const [task, setTask] = useState<EmailCampaignReport | null>(report?.task_id ? report : null);
  const [busy, setBusy] = useState("");
  const [toast, setToast] = useState(report?.message || "");

  const recipientStats = useMemo(() => {
    const seen = new Set<string>();
    let invalid = 0;
    let duplicate = 0;
    recipients.forEach((item) => {
      const email = item.email.trim().toLowerCase();
      if (!EMAIL_RE.test(email)) {
        invalid += 1;
        return;
      }
      if (seen.has(email)) duplicate += 1;
      seen.add(email);
    });
    return {
      total: recipients.length,
      valid: Math.max(0, recipients.length - invalid - duplicate),
      invalid,
      duplicate,
    };
  }, [recipients]);

  const previewRecipient = recipients.find((item) => EMAIL_RE.test(item.email)) || recipients[0];
  const previewSubject = renderTemplate(subject || "求职申请 - {{position}}", previewRecipient);
  const previewContent = renderTemplate(
    content || "您好，{{name}}：\n\n我想应聘 {{company}} 的 {{position}} 岗位，附件为我的简历。",
    previewRecipient
  );
  const selectedAttachments = attachments.filter((item) => item.selected !== false);
  const sendSummary = task?.send_summary || { total: 0, success: 0, failed: 0, pending: 0 };

  function updateRecipient(index: number, patch: Partial<EmailRecipient>) {
    setRecipients((items) => items.map((item, idx) => (idx === index ? { ...item, ...patch } : item)));
  }

  function addRecipient() {
    setRecipients((items) => [
      ...items,
      { id: crypto.randomUUID(), name: "", email: "", company: "", position: "", note: "" },
    ]);
    setActiveTab("recipients");
  }

  function removeRecipient(index: number) {
    setRecipients((items) => items.filter((_, idx) => idx !== index));
  }

  function importBatchRecipients() {
    const parsed = parseRecipients(batchText);
    if (!parsed.length) {
      setToast("请先粘贴邮箱或收件人信息。");
      return;
    }
    setRecipients((items) => [...items, ...parsed]);
    setBatchText("");
    setToast(`已添加 ${parsed.length} 个收件人，请检查公司和岗位字段。`);
  }

  async function handleTestSmtp() {
    setBusy("smtp");
    setSmtpStatus("testing");
    setToast("");
    try {
      const response = await testEmailCampaignSmtp(smtpConfig);
      setSmtpStatus(response.success ? "success" : "failed");
      setToast(response.message || (response.success ? "SMTP 配置可用。" : "SMTP 测试失败。"));
    } catch (error) {
      setSmtpStatus("failed");
      setToast(error instanceof Error ? error.message : "SMTP 测试失败");
    } finally {
      setBusy("");
    }
  }

  async function handleGenerateContent() {
    setBusy("generate");
    setToast("DeepSeek 正在结合简历、岗位和用途生成邮件内容...");
    try {
      const result = await generateCampaignContent({
        message: "生成一封可群发的求职邮件",
        file_id: fileId,
        target_company: targetCompany,
        target_position: targetPosition,
        purpose,
        style,
      });
      setSubject(cleanGeneratedText(result.subject));
      setContent(cleanGeneratedText(result.content));
      setToast("邮件主题和正文已生成。");
      setActiveTab("content");
    } catch (error) {
      setToast(error instanceof Error ? error.message : "邮件内容生成失败");
    } finally {
      setBusy("");
    }
  }

  async function handlePolishContent() {
    setBusy("polish");
    setToast("DeepSeek 正在润色邮件内容...");
    try {
      const result = await polishCampaignContent({
        subject,
        content,
        file_id: fileId,
        target_company: targetCompany,
        target_position: targetPosition,
        purpose,
        style,
      });
      setSubject(cleanGeneratedText(result.subject));
      setContent(cleanGeneratedText(result.content));
      setToast("邮件内容已润色。");
    } catch (error) {
      setToast(error instanceof Error ? error.message : "邮件内容润色失败");
    } finally {
      setBusy("");
    }
  }

  async function handleUploadAttachments(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    setBusy("upload");
    try {
      const uploaded = await Promise.all(files.map((item) => uploadCampaignAttachment(item)));
      setAttachments((items) => [
        ...items,
        ...uploaded.map((item) => ({
          file_id: item.file_id,
          filename: item.filename,
          file_type: item.file_type,
          selected: true,
        })),
      ]);
      setToast(`已上传 ${uploaded.length} 个附件。`);
    } catch (error) {
      setToast(error instanceof Error ? error.message : "附件上传失败");
    } finally {
      setBusy("");
      event.target.value = "";
    }
  }

  async function handleCreateTask() {
    if (recipientStats.valid <= 0) {
      setToast("请至少添加一个有效收件人。");
      setActiveTab("recipients");
      return;
    }
    if (!subject.trim() || !content.trim()) {
      setToast("请先填写或生成邮件主题和正文。");
      setActiveTab("content");
      return;
    }
    setBusy("create");
    try {
      const created = await createEmailCampaign({
        smtp_config: { ...smtpConfig, password: "" },
        recipients,
        subject,
        content,
        attachments,
        personalize,
        metadata: {
          source: "email_campaign_panel",
          target_company: targetCompany,
          target_position: targetPosition,
          purpose,
          style,
        },
      });
      setTask(created);
      onUpdated?.(created);
      setToast("群发任务已创建，请确认预览后发送。");
      setActiveTab("preview");
    } catch (error) {
      setToast(error instanceof Error ? error.message : "群发任务创建失败");
    } finally {
      setBusy("");
    }
  }

  async function handleSendTask() {
    if (!task?.task_id) {
      await handleCreateTask();
      return;
    }
    const confirmed = window.confirm(`确认向 ${task.recipients_count || recipients.length} 个收件人发送邮件？发送后会逐个记录状态。`);
    if (!confirmed) return;
    setBusy("send");
    try {
      const sent = await sendEmailCampaign({ task_id: task.task_id, smtp_config: smtpConfig, confirm: true });
      setTask(sent);
      onUpdated?.(sent);
      setToast("群发任务执行完成，可在发送记录中查看成功和失败原因。");
      setActiveTab("preview");
    } catch (error) {
      setToast(error instanceof Error ? error.message : "群发任务发送失败");
    } finally {
      setBusy("");
    }
  }

  return (
    <section className="flex min-h-0 flex-col gap-5 text-foreground">
      <Card className="rounded-[28px] border border-border/80 bg-card/90 shadow-[0_24px_70px_rgba(31,111,235,0.08)] backdrop-blur">
        <CardHeader className="items-start gap-4 p-6 md:grid-cols-[minmax(0,1fr)_auto]">
          <div className="flex min-w-0 items-start gap-4">
            <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <MailCheck className="size-6" />
            </div>
            <div className="flex min-w-0 flex-col gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge className="bg-primary/10 text-primary" variant="secondary">
                  邮件群发 Agent
                </Badge>
                <Badge
                  className={cn(
                    "border-transparent",
                    task?.status === "completed"
                      ? "bg-emerald-50 text-emerald-700"
                      : "bg-blue-50 text-blue-700"
                  )}
                  variant="secondary"
                >
                  {task?.status === "completed" ? "已完成" : "配置中"}
                </Badge>
              </div>
              <CardTitle className="text-3xl font-semibold tracking-tight md:text-4xl">
                AI 辅助求职邮件群发
              </CardTitle>
              <CardDescription className="max-w-3xl text-base leading-7">
                配置邮箱、维护收件人、生成或润色邮件内容，确认预览后再执行群发。
              </CardDescription>
            </div>
          </div>
          <CardAction className="flex flex-wrap justify-end gap-2">
            <Button type="button" variant="outline" size="lg" onClick={handleCreateTask} disabled={Boolean(busy)}>
              {busy === "create" ? <Spinner data-icon="inline-start" /> : <ClipboardList data-icon="inline-start" />}
              生成预览
            </Button>
            <Button type="button" size="lg" onClick={handleSendTask} disabled={Boolean(busy)}>
              {busy === "send" ? <Spinner data-icon="inline-start" /> : <Send data-icon="inline-start" />}
              开始群发
            </Button>
          </CardAction>
        </CardHeader>
        <CardContent className="px-6 pb-6">
          <div className="grid gap-3 md:grid-cols-4">
            <MetricCard label="有效收件人" value={`${recipientStats.valid} 个`} icon={UsersRound} />
            <MetricCard label="附件" value={`${selectedAttachments.length} 个`} icon={Paperclip} />
            <MetricCard label="成功发送" value={`${sendSummary.success || 0} 封`} icon={CheckCircle2} />
            <MetricCard label="失败" value={`${sendSummary.failed || 0} 封`} icon={AlertCircle} tone="danger" />
          </div>
        </CardContent>
      </Card>

      {toast && (
        <Alert className="rounded-2xl border-primary/20 bg-primary/5 text-primary">
          <AlertCircle className="size-4" />
          <AlertDescription className="text-primary">{toast}</AlertDescription>
        </Alert>
      )}

      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as StepValue)} className="gap-5">
        <TabsList className="grid h-auto w-full grid-cols-2 rounded-2xl border bg-card/80 p-1 shadow-sm md:grid-cols-4">
          {STEPS.map((step, index) => (
            <TabsTrigger
              key={step.value}
              value={step.value}
              className="h-12 rounded-xl data-active:bg-primary data-active:text-primary-foreground"
            >
              <step.icon data-icon="inline-start" />
              <span>{index + 1}. {step.label}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
          <main className="min-w-0">
            <TabsContent value="smtp">
              <CardPanel icon={MailCheck} title="SMTP 配置" description="使用你自己的邮箱 SMTP 发送，授权码只在当前请求中使用，不会明文展示。">
                <FieldSet>
                  <FieldGroup className="grid gap-4 md:grid-cols-2">
                    <FieldInput label="SMTP Host" value={smtpConfig.host} onChange={(value) => setSmtpConfig({ ...smtpConfig, host: value })} placeholder="smtp.163.com" />
                    <FieldInput label="SMTP Port" value={String(smtpConfig.port)} onChange={(value) => setSmtpConfig({ ...smtpConfig, port: Number(value) || 465 })} placeholder="465" />
                    <FieldInput label="邮箱账号" value={smtpConfig.username} onChange={(value) => setSmtpConfig({ ...smtpConfig, username: value })} placeholder="you@example.com" />
                    <FieldInput label="邮箱授权码 / 密码" type="password" value={smtpConfig.password} onChange={(value) => setSmtpConfig({ ...smtpConfig, password: value })} placeholder="不会明文展示" />
                    <FieldInput label="发件人名称" value={smtpConfig.from_name} onChange={(value) => setSmtpConfig({ ...smtpConfig, from_name: value })} placeholder="张同学" />
                    <FieldInput label="发件人邮箱" value={smtpConfig.from_email} onChange={(value) => setSmtpConfig({ ...smtpConfig, from_email: value })} placeholder="默认使用邮箱账号" />
                  </FieldGroup>
                  <FieldGroup className="grid gap-3 md:grid-cols-3">
                    <CheckField
                      id="campaign-ssl"
                      label="启用 SSL"
                      checked={smtpConfig.use_ssl}
                      onCheckedChange={(checked) => setSmtpConfig({ ...smtpConfig, use_ssl: checked, use_tls: checked ? false : smtpConfig.use_tls })}
                    />
                    <CheckField
                      id="campaign-tls"
                      label="启用 TLS"
                      checked={smtpConfig.use_tls}
                      onCheckedChange={(checked) => setSmtpConfig({ ...smtpConfig, use_tls: checked, use_ssl: checked ? false : smtpConfig.use_ssl })}
                    />
                    <CheckField
                      id="campaign-save-config"
                      label="保存为用户配置（预留）"
                      checked={Boolean(smtpConfig.save_config)}
                      onCheckedChange={(checked) => setSmtpConfig({ ...smtpConfig, save_config: checked })}
                    />
                  </FieldGroup>
                </FieldSet>
                <Separator />
                <div className="flex flex-wrap items-center gap-3">
                  <Button type="button" variant="outline" size="lg" onClick={handleTestSmtp} disabled={busy === "smtp"}>
                    {busy === "smtp" ? <Spinner data-icon="inline-start" /> : <RefreshCw data-icon="inline-start" />}
                    测试连接
                  </Button>
                  {smtpStatus !== "idle" && (
                    <Badge
                      className={cn(
                        smtpStatus === "success" && "bg-emerald-50 text-emerald-700",
                        smtpStatus === "testing" && "bg-blue-50 text-blue-700",
                        smtpStatus === "failed" && "bg-red-50 text-red-700"
                      )}
                      variant="secondary"
                    >
                      {smtpStatus === "success" ? "SMTP 可用" : smtpStatus === "testing" ? "测试中" : "测试失败"}
                    </Badge>
                  )}
                </div>
              </CardPanel>
            </TabsContent>

            <TabsContent value="recipients">
              <CardPanel icon={UsersRound} title="收件人管理" description="支持逐个添加和批量粘贴，发送前会校验邮箱格式和重复项。">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <Button type="button" variant="outline" size="lg" onClick={addRecipient}>
                    <Plus data-icon="inline-start" />
                    添加收件人
                  </Button>
                  <div className="flex flex-wrap gap-2 text-sm">
                    <Badge variant="secondary">有效 {recipientStats.valid}</Badge>
                    <Badge variant="outline">无效 {recipientStats.invalid}</Badge>
                    <Badge variant="outline">重复 {recipientStats.duplicate}</Badge>
                  </div>
                </div>
                <ScrollArea className="max-h-[420px] rounded-2xl border bg-background/70">
                  <div className="flex flex-col gap-3 p-3">
                    {recipients.length === 0 ? (
                      <Empty className="min-h-56 border border-dashed bg-card">
                        <EmptyMedia variant="icon">
                          <UsersRound />
                        </EmptyMedia>
                        <EmptyHeader>
                          <EmptyTitle>暂无收件人</EmptyTitle>
                          <EmptyDescription>点击添加收件人，或在下方批量粘贴邮箱。</EmptyDescription>
                        </EmptyHeader>
                      </Empty>
                    ) : (
                      recipients.map((item, index) => (
                        <Card key={item.id || index} size="sm" className="rounded-2xl bg-card shadow-none">
                          <CardContent className="grid gap-3 pt-1 md:grid-cols-[1fr_1.5fr_1fr_1fr_auto]">
                            <Input value={item.name} placeholder="姓名" onChange={(event) => updateRecipient(index, { name: event.target.value })} />
                            <Input
                              aria-invalid={Boolean(item.email && !EMAIL_RE.test(item.email))}
                              value={item.email}
                              placeholder="邮箱 *"
                              onChange={(event) => updateRecipient(index, { email: event.target.value })}
                            />
                            <Input value={item.company || ""} placeholder="公司" onChange={(event) => updateRecipient(index, { company: event.target.value })} />
                            <Input value={item.position || ""} placeholder="岗位" onChange={(event) => updateRecipient(index, { position: event.target.value })} />
                            <Button type="button" variant="destructive" size="icon" onClick={() => removeRecipient(index)} aria-label="删除收件人">
                              <Trash2 />
                            </Button>
                          </CardContent>
                        </Card>
                      ))
                    )}
                  </div>
                </ScrollArea>
                <Field>
                  <FieldLabel>批量粘贴</FieldLabel>
                  <Textarea
                    className="min-h-28 resize-none rounded-2xl"
                    value={batchText}
                    onChange={(event) => setBatchText(event.target.value)}
                    placeholder="批量粘贴邮箱，例如：王老师 wang@example.com；hr@example.com"
                  />
                  <FieldDescription>CSV / Excel 导入已预留，本阶段先支持粘贴导入。</FieldDescription>
                </Field>
                <Button type="button" variant="outline" size="lg" onClick={importBatchRecipients}>
                  <Upload data-icon="inline-start" />
                  导入粘贴内容
                </Button>
              </CardPanel>
            </TabsContent>

            <TabsContent value="content">
              <CardPanel icon={Sparkles} title="邮件内容" description="可手写，也可让 DeepSeek 结合简历、岗位和用途生成，再一键润色。">
                <FieldGroup className="grid gap-4 md:grid-cols-2">
                  <FieldInput label="目标公司" value={targetCompany} onChange={setTargetCompany} placeholder="可留空，群发时用变量" />
                  <FieldInput label="目标岗位" value={targetPosition} onChange={setTargetPosition} placeholder="Java 后端 / 大模型 / 实习生" />
                  <FieldInput label="邮件用途" value={purpose} onChange={setPurpose} placeholder="投递简历 / 内推联系 / 导师联系" />
                  <FieldInput label="语气风格" value={style} onChange={setStyle} placeholder="正式 / 自然 / 简洁 / 技术岗位风格" />
                </FieldGroup>
                <div className="flex flex-wrap gap-3">
                  <Button type="button" variant="outline" size="lg" onClick={handleGenerateContent} disabled={Boolean(busy)}>
                    {busy === "generate" ? <Spinner data-icon="inline-start" /> : <Sparkles data-icon="inline-start" />}
                    AI 生成
                  </Button>
                  <Button type="button" variant="outline" size="lg" onClick={handlePolishContent} disabled={Boolean(busy)}>
                    {busy === "polish" ? <Spinner data-icon="inline-start" /> : <Sparkles data-icon="inline-start" />}
                    AI 润色
                  </Button>
                </div>
                <Field>
                  <FieldLabel>邮件主题</FieldLabel>
                  <Input value={subject} onChange={(event) => setSubject(event.target.value)} placeholder="求职申请 - {{position}}" />
                </Field>
                <Field>
                  <FieldLabel>邮件正文</FieldLabel>
                  <Textarea
                    className="min-h-64 resize-y rounded-2xl leading-7"
                    value={content}
                    onChange={(event) => setContent(event.target.value)}
                    placeholder="您好，{{name}}：..."
                  />
                  <FieldDescription className="flex flex-wrap items-center gap-2">
                    支持变量：
                    <Badge variant="secondary">{"{{name}}"}</Badge>
                    <Badge variant="secondary">{"{{company}}"}</Badge>
                    <Badge variant="secondary">{"{{position}}"}</Badge>
                  </FieldDescription>
                </Field>
                <div className="flex flex-wrap items-center gap-3 rounded-2xl border bg-background/70 p-4">
                  <input
                    id="campaign-attachment-input"
                    type="file"
                    multiple
                    accept=".pdf,.docx,.doc,.txt,.md"
                    onChange={handleUploadAttachments}
                    hidden
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="lg"
                    onClick={() => document.getElementById("campaign-attachment-input")?.click()}
                    disabled={busy === "upload"}
                  >
                    {busy === "upload" ? <Spinner data-icon="inline-start" /> : <Upload data-icon="inline-start" />}
                    上传附件
                  </Button>
                  <CheckField
                    id="campaign-personalize"
                    label="启用个性化变量渲染"
                    checked={personalize}
                    onCheckedChange={setPersonalize}
                    compact
                  />
                </div>
              </CardPanel>
            </TabsContent>

            <TabsContent value="preview">
              <CardPanel icon={Eye} title="预览与发送" description="发送前确认发件人、收件人数量、正文预览和附件，避免误发。">
                <div className="grid gap-3 md:grid-cols-4">
                  <InfoTile label="发件人" value={smtpConfig.from_email || smtpConfig.username || "未配置"} />
                  <InfoTile label="预计发送" value={`${recipientStats.valid || task?.recipients_count || 0} 封`} />
                  <InfoTile label="附件" value={`${selectedAttachments.length} 个`} />
                  <InfoTile label="变量渲染" value={personalize ? "启用" : "关闭"} />
                </div>
                <Card className="rounded-3xl border-primary/15 bg-gradient-to-br from-blue-50/70 to-white shadow-none">
                  <CardHeader>
                    <CardTitle className="text-xl">{previewSubject}</CardTitle>
                    <CardDescription>使用第一位有效收件人渲染的预览内容。</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-2xl bg-white/70 p-4 text-sm leading-7 text-foreground shadow-inner">
                      {previewContent}
                    </pre>
                  </CardContent>
                </Card>
                {task?.send_results?.length ? (
                  <ScrollArea className="max-h-72 rounded-2xl border bg-background/70">
                    <div className="flex flex-col gap-2 p-3">
                      {task.send_results.map((item) => (
                        <div
                          className="grid gap-2 rounded-xl border bg-card p-3 text-sm md:grid-cols-[minmax(0,1fr)_96px_minmax(0,1fr)]"
                          key={item.recipient_id}
                        >
                          <span className="truncate">{item.email}</span>
                          <Badge className={cn(item.status === "success" && "bg-emerald-50 text-emerald-700", item.status === "failed" && "bg-red-50 text-red-700")} variant="secondary">
                            {item.status}
                          </Badge>
                          {item.error && <span className="truncate text-destructive">{item.error}</span>}
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                ) : (
                  <Empty className="border bg-background/60">
                    <EmptyMedia variant="icon">
                      <Send />
                    </EmptyMedia>
                    <EmptyHeader>
                      <EmptyTitle>暂无发送记录</EmptyTitle>
                      <EmptyDescription>创建预览并确认后，可以执行群发并查看逐封状态。</EmptyDescription>
                    </EmptyHeader>
                    <EmptyContent>
                      <Button type="button" onClick={handleCreateTask} disabled={Boolean(busy)}>
                        {busy === "create" ? <Spinner data-icon="inline-start" /> : <ClipboardList data-icon="inline-start" />}
                        生成预览
                      </Button>
                    </EmptyContent>
                  </Empty>
                )}
              </CardPanel>
            </TabsContent>
          </main>

          <aside className="flex min-w-0 flex-col gap-4">
            <Card className="rounded-[24px] bg-card/90 shadow-[0_18px_48px_rgba(31,111,235,0.06)]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ClipboardList className="size-5 text-primary" />
                  发送摘要
                </CardTitle>
                <CardDescription>确认任务前先核对数量和失败风险。</CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-3">
                <InfoTile label="收件人" value={`${recipientStats.valid || task?.recipients_count || 0}`} />
                <InfoTile label="成功" value={`${sendSummary.success || 0}`} />
                <InfoTile label="失败" value={`${sendSummary.failed || 0}`} />
                <InfoTile label="待发" value={`${sendSummary.pending || 0}`} />
              </CardContent>
            </Card>

            <Card className="rounded-[24px] bg-card/90 shadow-[0_18px_48px_rgba(31,111,235,0.06)]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Paperclip className="size-5 text-primary" />
                  附件列表
                </CardTitle>
                <CardDescription>选择随邮件发送的简历、求职信或补充材料。</CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="max-h-56">
                  <div className="flex flex-col gap-2">
                    {attachments.length === 0 ? (
                      <Empty className="min-h-40 border bg-background/60">
                        <EmptyMedia variant="icon">
                          <Paperclip />
                        </EmptyMedia>
                        <EmptyHeader>
                          <EmptyTitle>暂无附件</EmptyTitle>
                          <EmptyDescription>建议添加简历 PDF 或求职信 PDF。</EmptyDescription>
                        </EmptyHeader>
                      </Empty>
                    ) : (
                      attachments.map((item, index) => (
                        <div key={item.file_id} className="flex items-center gap-3 rounded-2xl border bg-background/70 p-3">
                          <Checkbox
                            checked={item.selected !== false}
                            onCheckedChange={(checked) =>
                              setAttachments((items) =>
                                items.map((attachment, idx) =>
                                  idx === index ? { ...attachment, selected: Boolean(checked) } : attachment
                                )
                              )
                            }
                          />
                          <span className="min-w-0 flex-1 truncate text-sm font-medium">{item.filename}</span>
                          <Button type="button" variant="ghost" size="icon-sm" onClick={() => setAttachments((items) => items.filter((_, idx) => idx !== index))}>
                            <Trash2 />
                          </Button>
                        </div>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>

            <Card className="rounded-[24px] bg-card/90 shadow-[0_18px_48px_rgba(31,111,235,0.06)]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ShieldCheck className="size-5 text-primary" />
                  发送前检查
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 text-sm text-muted-foreground">
                <CheckLine>建议先测试 SMTP 连接。</CheckLine>
                <CheckLine>收件人邮箱会在创建任务时校验并去重。</CheckLine>
                <CheckLine>授权码不会保存到群发记录。</CheckLine>
                <CheckLine>暂停发送、取消任务、CSV 导入已预留。</CheckLine>
              </CardContent>
            </Card>
          </aside>
        </div>
      </Tabs>
    </section>
  );
}

function CardPanel({ icon: Icon, title, description, children }: { icon: LucideIcon; title: string; description: string; children: ReactNode }) {
  return (
    <Card className="rounded-[28px] bg-card/95 shadow-[0_22px_60px_rgba(31,111,235,0.07)]">
      <CardHeader className="p-6">
        <CardTitle className="flex items-center gap-3 text-2xl">
          <span className="flex size-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <Icon className="size-5" />
          </span>
          {title}
        </CardTitle>
        <CardDescription className="text-base">{description}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5 px-6 pb-6">{children}</CardContent>
    </Card>
  );
}

function MetricCard({ label, value, icon: Icon, tone = "default" }: { label: string; value: string; icon: LucideIcon; tone?: "default" | "danger" }) {
  return (
    <Card className="rounded-2xl bg-background/75 py-3 shadow-none">
      <CardContent className="flex items-center gap-3 px-4">
        <div className={cn("flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary", tone === "danger" && "bg-red-50 text-red-600")}>
          <Icon className="size-5" />
        </div>
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">{label}</p>
          <strong className="text-xl font-semibold">{value}</strong>
        </div>
      </CardContent>
    </Card>
  );
}

function FieldInput({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <Field>
      <FieldLabel>{label}</FieldLabel>
      <Input type={type} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
    </Field>
  );
}

function CheckField({
  id,
  label,
  checked,
  onCheckedChange,
  compact = false,
}: {
  id: string;
  label: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  compact?: boolean;
}) {
  return (
    <Field orientation="horizontal" className={cn("rounded-2xl border bg-background/70 p-3", compact && "w-fit border-transparent bg-transparent p-0")}>
      <Checkbox id={id} checked={checked} onCheckedChange={(next) => onCheckedChange(Boolean(next))} />
      <FieldContent>
        <FieldLabel htmlFor={id}>{label}</FieldLabel>
      </FieldContent>
    </Field>
  );
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-2xl border bg-background/70 p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <strong className="mt-1 block truncate text-lg font-semibold">{value}</strong>
    </div>
  );
}

function CheckLine({ children }: { children: ReactNode }) {
  return (
    <div className="flex gap-2">
      <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" />
      <span>{children}</span>
    </div>
  );
}
