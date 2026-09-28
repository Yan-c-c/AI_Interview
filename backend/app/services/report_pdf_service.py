from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    if isinstance(value, (list, tuple)):
        return "；".join(_text(item) for item in value if _text(item))
    if isinstance(value, dict):
        return "；".join(f"{key}: {_text(item)}" for key, item in value.items())
    return str(value).strip() or fallback


def _items(value: Any, limit: int = 8) -> list[Any]:
    if not isinstance(value, list):
        return []
    return value[:limit]


def _priority_text(priority: str) -> str:
    if priority == "high":
        return "高"
    if priority == "medium":
        return "中"
    if priority == "low":
        return "低"
    return priority or "待定"


class ResumeReportPdfService:
    def __init__(self) -> None:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        styles = getSampleStyleSheet()
        self.title = ParagraphStyle(
            "ResumeTitle",
            parent=styles["Title"],
            fontName="STSong-Light",
            fontSize=20,
            leading=28,
            textColor=colors.HexColor("#17223b"),
            spaceAfter=8,
        )
        self.h2 = ParagraphStyle(
            "ResumeH2",
            parent=styles["Heading2"],
            fontName="STSong-Light",
            fontSize=14,
            leading=20,
            textColor=colors.HexColor("#1f6feb"),
            spaceBefore=12,
            spaceAfter=8,
        )
        self.body = ParagraphStyle(
            "ResumeBody",
            parent=styles["BodyText"],
            fontName="STSong-Light",
            fontSize=10.5,
            leading=16,
            textColor=colors.HexColor("#26364f"),
            wordWrap="CJK",
        )
        self.small = ParagraphStyle(
            "ResumeSmall",
            parent=self.body,
            fontSize=9,
            leading=14,
            textColor=colors.HexColor("#5f6f89"),
        )

    def render(self, report: dict[str, Any]) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=16 * mm,
            rightMargin=16 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
            title="简历评估报告",
        )
        story: list[Any] = []
        summary = report.get("summary") or {}
        dimension_scores = report.get("dimension_scores") or {}
        roundtable = report.get("roundtable") or {}
        reflector = roundtable.get("reflector") or {}

        story.append(Paragraph("简历评估报告", self.title))
        story.append(Paragraph("DeepSeek 多专家圆桌会议完成 · Reflector 已整合", self.small))
        story.append(Spacer(1, 8))

        summary_rows = [
            ["总体评分", f"{summary.get('overall_score', 0)}/100"],
            ["风险等级", _text(summary.get("risk_level"), "未知")],
            ["目标岗位", _text(summary.get("target_position"), "未明确")],
            ["技能匹配", f"{dimension_scores.get('skill_match', 0)}/100"],
            ["关键问题", str(len(report.get("problems") or summary.get("main_problems") or []))],
        ]
        story.append(self._table(summary_rows, widths=[36 * mm, 120 * mm]))

        story.append(Paragraph("Reflector 最终结论", self.h2))
        story.append(Paragraph(_text(reflector.get("final_judgement"), "暂无最终结论。"), self.body))
        for index, action in enumerate(_items(reflector.get("prioritized_actions"), 3), start=1):
            story.append(Paragraph(f"{index}. {_text(action)}", self.body))

        story.append(Paragraph("优先修复任务", self.h2))
        problems = _items(report.get("problems"), 6)
        suggestions = _items(report.get("optimization_suggestions"), 6)
        if problems:
            for index, problem in enumerate(problems, start=1):
                suggestion = suggestions[index - 1] if index - 1 < len(suggestions) else {}
                story.append(Paragraph(f"{index}. [{_priority_text(_text(problem.get('priority')))}] {_text(problem.get('problem'))}", self.body))
                story.append(Paragraph(f"证据：{_text(problem.get('evidence'), '未提供')}", self.small))
                story.append(Paragraph(f"建议：{_text(problem.get('suggestion') or suggestion.get('suggestion'), '补充具体职责、技术动作和结果数据。')}", self.small))
                if suggestion.get("example"):
                    story.append(Paragraph(f"示例：{_text(suggestion.get('example'))}", self.small))
                story.append(Spacer(1, 5))
        else:
            story.append(Paragraph("暂无明确问题。", self.body))

        story.append(Paragraph("专项检测", self.h2))
        story.append(Paragraph(f"风险表达命中：{len(report.get('forbidden_words') or [])} 个", self.body))
        for item in _items(report.get("forbidden_words"), 5):
            story.append(Paragraph(f"- {_text(item.get('word'))}（{_text(item.get('risk_type'))}）：{_text(item.get('suggestion'))}", self.small))
        template = report.get("template_duplication") or {}
        story.append(Paragraph(f"模板化风险：{_text(template.get('risk_level'), '未知')}，评分 {template.get('score', 0)}/100", self.body))
        for item in _items(template.get("suggestions"), 5):
            story.append(Paragraph(f"- {_text(item)}", self.small))

        story.append(Paragraph("多专家圆桌摘要", self.h2))
        expert_keys = ["matching_analyst", "content_optimizer", "hr_reviewer", "risk_template_reviewer", "reflector"]
        for key in expert_keys:
            expert = roundtable.get(key) or {}
            story.append(Paragraph(_text(expert.get("role"), key), self.body))
            for finding in _items(expert.get("findings") or expert.get("prioritized_actions"), 3):
                story.append(Paragraph(f"- {_text(finding)}", self.small))

        doc.build(story)
        return buffer.getvalue()

    def _table(self, rows: list[list[str]], widths: list[float]) -> Table:
        table = Table(
            [[Paragraph(_text(cell), self.body) for cell in row] for row in rows],
            colWidths=widths,
            hAlign="LEFT",
        )
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f2f6ff")),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1f6feb")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dbe4f0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        return table


resume_report_pdf_service = ResumeReportPdfService()
