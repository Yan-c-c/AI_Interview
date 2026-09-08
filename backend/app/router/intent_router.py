from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.agent_schema import Intent


@dataclass
class IntentRouteResult:
    intent: Intent
    confidence: float
    needs_clarification: bool = False
    message: str | None = None


class IntentRouter:
    resume_patterns = [
        r"^(帮我)?(看看|评估|分析|优化|检查).{0,10}(这份|我的)?简历",
        r"^(这份|我的)?简历.*(看看|评估|分析|问题|优化|检查|风险|违禁词|模板|查重)",
        r"^看看我的简历能不能投",
        r"^求职材料",
        r"^帮我看看这份简历",
        r"^帮我优化一下简历",
    ]
    interview_question_patterns = [
        r"面试题",
        r"模拟面试",
        r"语音面试",
        r"面试练习题",
        r"生成.*(问题|题目|练习题)",
        r"(根据|基于).{0,8}简历.{0,12}(生成|出|准备|设计).{0,8}(面试题|问题|题目|练习题)",
        r"(帮我)?(出|生成|准备|设计).{0,12}(面试题|问题|题目|练习题)",
        r"(根据|基于).{0,8}简历.{0,12}问.{0,8}(问题|题目)",
        r"根据简历.*提问",
        r"题库",
    ]
    audio_patterns = [r"录音分析", r"分析.*录音", r"面试录音", r"音频分析", r"分析.*音频", r"面试对话分析", r"转写.*面试", r"面试.*转写"]
    cover_letter_patterns = [
        r"求职信",
        r"cover letter",
        r"自荐信",
        r"申请信",
        r"申请邮件",
        r"内推信",
        r"导师申请",
        r"邮件正文",
        r"(帮我|给我)?(写|生成|改写).{0,12}(求职信|自荐信|申请信|申请邮件|内推信)",
    ]
    email_campaign_patterns = [
        r"邮件群发",
        r"群发.*邮件",
        r"批量.*邮件",
        r"批量发送.*(求职信|求职邮件|邮件)",
        r"群发.*(求职信|求职邮件)",
        r"给这些.{0,8}(hr|HR|招聘).{0,8}发邮件",
        r"给.*(hr|HR|招聘).{0,12}(发|发送).{0,6}邮件",
        r"email campaign",
    ]
    salary_patterns = [
        r"薪资",
        r"谈薪",
        r"offer",
        r"加薪",
        r"合理薪资",
        r"薪资预测",
        r"谈判",
        r"hr.*(压价|还价|报价)",
        r"(模拟|生成).{0,8}(薪资|谈薪).{0,8}(谈判|话术)",
    ]
    career_patterns = [
        r"职业规划",
        r"发展路径",
        r"职业方向",
        r"职业建议",
        r"未来规划",
        r"转行",
        r"转岗",
        r"学习路线",
        r"学习路径",
        r"投递策略",
        r"岗位方向",
        r"求职规划",
        r"(帮我|给我)?(规划|分析).{0,12}(职业|岗位|求职|发展)",
    ]

    def route(self, message: str, has_file: bool = False) -> IntentRouteResult:
        normalized = (message or "").strip().lower()
        if self._matches(normalized, self.resume_patterns):
            return IntentRouteResult(Intent.resume_evaluation, 0.95)
        if self._matches(normalized, self.interview_question_patterns):
            return IntentRouteResult(Intent.interview_question_generation, 0.9)
        if self._matches(normalized, self.audio_patterns):
            return IntentRouteResult(Intent.interview_audio_analysis, 0.9)
        if self._matches(normalized, self.email_campaign_patterns):
            return IntentRouteResult(Intent.email_campaign, 0.9)
        if self._matches(normalized, self.cover_letter_patterns):
            return IntentRouteResult(Intent.cover_letter_generation, 0.9)
        if self._matches(normalized, self.salary_patterns):
            return IntentRouteResult(Intent.salary_negotiation, 0.85)
        if self._matches(normalized, self.career_patterns):
            return IntentRouteResult(Intent.career_planning, 0.85)

        if has_file and not normalized:
            return IntentRouteResult(
                Intent.unknown,
                0.2,
                needs_clarification=True,
                message="我已收到你的文件，请问你是希望进行简历评估、根据简历进行模拟面试、分析面试录音、生成求职信，还是做职业规划？",
            )
        if has_file and normalized in {"看看", "帮我看看", "处理一下", "分析一下"}:
            return IntentRouteResult(
                Intent.unknown,
                0.35,
                needs_clarification=True,
                message="我已收到你的文件，请问你是希望进行简历评估、根据简历进行模拟面试、分析面试录音、生成求职信，还是做职业规划？",
            )

        return IntentRouteResult(Intent.unknown, 0.1, message="暂时无法识别你的需求，请说明想进行简历评估、模拟面试、录音分析、求职信生成或职业规划。")

    def _matches(self, text: str, patterns: list[str]) -> bool:
        return any(re.search(pattern, text, flags=re.I) for pattern in patterns)


intent_router = IntentRouter()
