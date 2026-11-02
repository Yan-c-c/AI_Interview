"use client";

import { useState } from "react";
import {
  ArrowRight,
  BookOpen,
  BriefcaseBusiness,
  CheckCircle2,
  Download,
  Gauge,
  Map,
  PenLine,
  Sparkles,
  Target,
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
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
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
  CareerPlanningReport,
  exportCareerPlan,
  rewriteCareerPlan,
} from "@/lib/api/careerPlanning";

function cleanText(text?: string) {
  return (text || "")
    .replace(/\\r\\n|\\n|\/n/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function brief(text?: string, length = 56) {
  const value = cleanText(text);
  return value.length > length ? `${value.slice(0, length)}...` : value;
}

function normalizeList(items?: string[], fallback = "暂无明确内容，建议补充简历或目标信息。") {
  const values = (items || []).map(cleanText).filter(Boolean);
  return values.length ? values : [fallback];
}

export function CareerPlanningPanel({
  report,
  onUpdated,
}: {
  report: CareerPlanningReport;
  onUpdated: (report: CareerPlanningReport) => void;
}) {
  const [instruction, setInstruction] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleRewrite() {
    if (!instruction.trim()) {
      setStatus("请先输入新的目标或调整要求。");
      return;
    }
    setBusy(true);
    setStatus("正在调用 DeepSeek 重新规划...");
    try {
      const updated = await rewriteCareerPlan(report, instruction);
      onUpdated(updated);
      setInstruction("");
      setStatus("职业规划已更新。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "职业规划调整失败");
    } finally {
      setBusy(false);
    }
  }

  async function handleExport(format: "md" | "docx" | "pdf") {
    setBusy(true);
    setStatus("");
    try {
      await exportCareerPlan(report, format);
      setStatus(`已导出 ${format.toUpperCase()}。`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "导出失败");
    } finally {
      setBusy(false);
    }
  }

  const recommendedPositions = normalizeList(report.career_profile.recommended_positions, "暂无推荐岗位方向");
  const nextActions = normalizeList(report.next_actions, "先补充目标方向、可投入时间和当前困惑。");

  return (
    <section className="flex min-h-0 flex-col gap-5">
      <Card>
        <CardHeader className="gap-4 md:grid-cols-[minmax(0,1fr)_auto]">
          <div className="flex min-w-0 items-start gap-4">
            <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-secondary text-primary">
              <Map className="size-6" />
            </div>
            <div className="flex min-w-0 flex-col gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">职业规划 Agent</Badge>
                <Badge variant="secondary">已生成</Badge>
                {report.metadata?.used_deepseek && <Badge variant="outline">DeepSeek 驱动</Badge>}
              </div>
              <CardTitle className="text-2xl md:text-3xl">个性化职业规划工作台</CardTitle>
              <CardDescription className="max-w-3xl text-base">
                先看目标与差距，再看学习路径和投递动作。长内容已收纳到分区中，避免信息堆叠。
              </CardDescription>
            </div>
          </div>
          <CardAction className="flex flex-wrap justify-end gap-2">
            <Button type="button" variant="outline" disabled={busy} onClick={() => void handleExport("md")}>
              <Download data-icon="inline-start" />
              Markdown
            </Button>
            <Button type="button" variant="outline" disabled={busy} onClick={() => void handleExport("docx")}>
              <Download data-icon="inline-start" />
              DOCX
            </Button>
            <Button type="button" disabled={busy} onClick={() => void handleExport("pdf")}>
              <Download data-icon="inline-start" />
              PDF
            </Button>
          </CardAction>
        </CardHeader>
      </Card>

      {report.needs_more_info && (
        <Alert>
          <Sparkles className="size-4" />
          <AlertDescription>
            建议补充：{report.missing_fields.join("、")}。未上传简历时也可使用，但上传简历会更精准。
          </AlertDescription>
        </Alert>
      )}

      {status && (
        <Alert>
          {busy ? <Spinner /> : <CheckCircle2 className="size-4" />}
          <AlertDescription>{status}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <SummaryCard
          icon={Target}
          label="目标方向"
          value={brief(report.career_profile.target_direction || report.matching_analysis.target_position || "待补充", 32)}
          detail={brief(report.career_profile.current_stage || "当前阶段待补充", 36)}
        />
        <SummaryCard
          icon={BookOpen}
          label="当前阶段"
          value={brief(report.career_profile.current_stage || "待补充", 26)}
          detail="用于决定学习周期和投递节奏"
        />
        <SummaryCard
          icon={Gauge}
          label="岗位匹配度"
          value={`${report.matching_analysis.match_score || 0}/100`}
          detail={brief(report.matching_analysis.target_position || "目标岗位待确认", 36)}
        />
        <SummaryCard
          icon={BriefcaseBusiness}
          label="推荐岗位"
          value={`${recommendedPositions.length} 个`}
          detail={brief(recommendedPositions.slice(0, 2).join("、"), 36)}
        />
        <SummaryCard
          icon={CheckCircle2}
          label="下一步行动"
          value={`${nextActions.length} 项`}
          detail={brief(nextActions[0], 36)}
        />
      </div>

      <div className="grid min-h-0 gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <main className="min-w-0">
          <Card>
            <CardHeader>
              <CardTitle>规划内容</CardTitle>
              <CardDescription>按任务分区查看，不再把所有内容挤在同一屏。</CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="overview" className="gap-5">
                <TabsList className="grid h-auto w-full grid-cols-2 md:grid-cols-4">
                  <TabsTrigger value="overview">总览</TabsTrigger>
                  <TabsTrigger value="gap">能力差距</TabsTrigger>
                  <TabsTrigger value="path">学习路径</TabsTrigger>
                  <TabsTrigger value="delivery">项目投递</TabsTrigger>
                </TabsList>

                <TabsContent value="overview">
                  <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                    <ListPanel title="当前优势" description="已经能支撑求职的部分" items={report.career_profile.current_strengths} icon={CheckCircle2} />
                    <ListPanel title="主要差距" description="需要优先补齐的短板" items={report.career_profile.main_gaps} icon={Gauge} />
                    <PlanPanel title="短期规划" items={report.career_plan.short_term} />
                    <PlanPanel title="中长期规划" items={[...normalizeList(report.career_plan.mid_term), ...normalizeList(report.career_plan.long_term)]} />
                  </div>
                </TabsContent>

                <TabsContent value="gap">
                  <div className="grid gap-4 lg:grid-cols-2">
                    <ListPanel title="已匹配技能" description="当前画像中已经具备的能力" items={report.matching_analysis.matched_skills} icon={CheckCircle2} />
                    <ListPanel title="待补齐技能" description="和目标岗位之间的能力缺口" items={report.matching_analysis.missing_skills} icon={Gauge} />
                    <ListPanel title="风险点" description="可能影响投递或面试转化的问题" items={report.matching_analysis.risk_points} icon={Sparkles} />
                    <ListPanel title="岗位判断" description="建议重点关注的匹配逻辑" items={[report.matching_analysis.target_position, `匹配度 ${report.matching_analysis.match_score || 0}/100`]} icon={Target} />
                  </div>
                </TabsContent>

                <TabsContent value="path">
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <TimelinePanel title="1 周" items={report.learning_path.one_week} />
                    <TimelinePanel title="1 个月" items={report.learning_path.one_month} />
                    <TimelinePanel title="3 个月" items={report.learning_path.three_months} />
                    <TimelinePanel title="6 个月" items={report.learning_path.six_months} />
                  </div>
                </TabsContent>

                <TabsContent value="delivery">
                  <div className="grid gap-4 lg:grid-cols-2">
                    <ListPanel title="项目补强" description="应该补什么项目、怎么写进简历" items={report.project_suggestions} icon={BriefcaseBusiness} />
                    <ListPanel title="投递策略" description="岗位关键词、投递顺序和面试准备" items={report.job_search_strategy} icon={Target} />
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </main>

        <aside className="flex min-w-0 flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="size-5 text-primary" />
                优先行动
              </CardTitle>
              <CardDescription>先做这些，避免规划停留在泛泛建议。</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="max-h-72">
                <ol className="flex flex-col gap-3">
                  {nextActions.slice(0, 8).map((item, index) => (
                    <li className="grid grid-cols-[auto_minmax(0,1fr)] gap-3 text-sm leading-6" key={`${item}-${index}`}>
                      <Badge variant="secondary">{index + 1}</Badge>
                      <span className="break-words">{item}</span>
                    </li>
                  ))}
                </ol>
              </ScrollArea>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Target className="size-5 text-primary" />
                推荐岗位方向
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {recommendedPositions.map((item) => (
                <Badge key={item} variant="secondary" className="max-w-full truncate">
                  {item}
                </Badge>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PenLine className="size-5 text-primary" />
                继续调整规划
              </CardTitle>
              <CardDescription>输入新的目标、时间约束或转向要求后重新规划。</CardDescription>
            </CardHeader>
            <CardContent>
              <FieldGroup>
                <Field>
                  <FieldLabel>调整要求</FieldLabel>
                  <Textarea
                    value={instruction}
                    onChange={(event) => setInstruction(event.target.value)}
                    placeholder="例如：我想转大模型方向，每天只能学 2 小时..."
                    className="min-h-28 resize-none"
                  />
                  <FieldDescription>系统会保留当前报告上下文，并基于新要求重新生成。</FieldDescription>
                </Field>
                <Button type="button" disabled={busy} onClick={() => void handleRewrite()}>
                  {busy ? <Spinner data-icon="inline-start" /> : <ArrowRight data-icon="inline-start" />}
                  重新规划
                </Button>
              </FieldGroup>
            </CardContent>
          </Card>
        </aside>
      </div>
    </section>
  );
}

function SummaryCard({ icon: Icon, label, value, detail }: { icon: LucideIcon; label: string; value: string; detail: string }) {
  return (
    <Card>
      <CardContent className="flex min-h-32 flex-col gap-3 p-4">
        <div className="flex items-center justify-between gap-3">
          <Badge variant="outline">{label}</Badge>
          <Icon className="size-5 text-primary" />
        </div>
        <strong className="break-words text-xl leading-snug">{value}</strong>
        <p className="break-words text-sm leading-6 text-muted-foreground">{detail}</p>
      </CardContent>
    </Card>
  );
}

function ListPanel({ title, description, items, icon: Icon }: { title: string; description: string; items?: string[]; icon: LucideIcon }) {
  const visible = normalizeList(items);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon className="size-5 text-primary" />
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {visible.length === 1 && visible[0].startsWith("暂无") ? (
          <Empty className="min-h-36">
            <EmptyMedia variant="icon">
              <BookOpen />
            </EmptyMedia>
            <EmptyHeader>
              <EmptyTitle>暂无明确内容</EmptyTitle>
              <EmptyDescription>补充简历或目标信息后会更精准。</EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : (
          <ScrollArea className="max-h-72 pr-3">
            <ul className="flex flex-col gap-3">
              {visible.map((item, index) => (
                <li className="grid grid-cols-[auto_minmax(0,1fr)] gap-3 text-sm leading-6" key={`${title}-${item}-${index}`}>
                  <Badge variant="secondary">{index + 1}</Badge>
                  <span className="break-words">{item}</span>
                </li>
              ))}
            </ul>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}

function PlanPanel({ title, items }: { title: string; items?: string[] }) {
  const visible = normalizeList(items, "暂无规划内容。");
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>按优先级执行即可，不需要一次铺开所有任务。</CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="max-h-64 pr-3">
          <ul className="flex flex-col gap-3">
            {visible.map((item, index) => (
              <li className="grid grid-cols-[auto_minmax(0,1fr)] gap-3 text-sm leading-6" key={`${title}-${item}-${index}`}>
                <CheckCircle2 className="mt-1 size-4 shrink-0 text-primary" />
                <span className="break-words">{item}</span>
              </li>
            ))}
          </ul>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function TimelinePanel({ title, items }: { title: string; items?: string[] }) {
  const visible = normalizeList(items, "待补充行动项。");
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Badge variant="secondary">{title}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-72 pr-3">
          <ul className="flex flex-col gap-3">
            {visible.map((item, index) => (
              <li className="grid grid-cols-[auto_minmax(0,1fr)] gap-3 text-sm leading-6" key={`${title}-${item}-${index}`}>
                <span className="mt-2 size-2 rounded-full bg-primary" />
                <span className="break-words">{item}</span>
                {index < visible.length - 1 && <Separator className="col-span-2" />}
              </li>
            ))}
          </ul>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
