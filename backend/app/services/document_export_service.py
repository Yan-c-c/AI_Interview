from __future__ import annotations

import re
from io import BytesIO
from typing import Any

from docx import Document
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    if isinstance(value, list):
        return "\n".join(f"- {_text(item)}" for item in value if _text(item))
    if isinstance(value, dict):
        return "\n".join(f"- {key}: {_text(item)}" for key, item in value.items() if _text(item))
    return str(value).strip() or fallback


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def safe_export_filename(filename: str | None, suffix: str) -> str:
    raw = (filename or f"智能面试助手导出.{suffix}").strip()
    raw = raw.replace("\r", "").replace("\n", "")
    raw = re.sub(r"[\\/:*?\"<>|]+", "-", raw)
    if not raw.lower().endswith(f".{suffix.lower()}"):
        raw = f"{raw}.{suffix}"
    return raw[:120]


class DocumentExportService:
    def __init__(self) -> None:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        styles = getSampleStyleSheet()
        self.title = ParagraphStyle(
            "DocTitle",
            parent=styles["Title"],
            fontName="STSong-Light",
            fontSize=20,
            leading=28,
            textColor=colors.HexColor("#17223b"),
            spaceAfter=8,
        )
        self.h2 = ParagraphStyle(
            "DocH2",
            parent=styles["Heading2"],
            fontName="STSong-Light",
            fontSize=13.5,
            leading=20,
            textColor=colors.HexColor("#1f6feb"),
            spaceBefore=10,
            spaceAfter=6,
        )
        self.body = ParagraphStyle(
            "DocBody",
            parent=styles["BodyText"],
            fontName="STSong-Light",
            fontSize=10.5,
            leading=16,
            textColor=colors.HexColor("#26364f"),
            wordWrap="CJK",
        )

    def cover_letter_markdown(self, report: dict[str, Any], version_key: str = "standard") -> str:
        requirements = report.get("requirements") or {}
        versions = report.get("versions") or {}
        version = versions.get(version_key) or versions.get("standard") or {}
        title = _text(version.get("title"), "个性化求职信")
        body = _text(version.get("body"), "暂无求职信正文。")
        highlights = _list(report.get("highlight_points"))
        suggestions = _list(report.get("optimization_suggestions"))
        return "\n\n".join(
            [
                f"# {title}",
                f"目标公司：{_text(requirements.get('target_company'), '待补充')}",
                f"目标岗位：{_text(requirements.get('target_position'), '待补充')}",
                f"求职信用途：{_text(requirements.get('purpose'), '求职申请')}",
                f"生成风格：{_text(requirements.get('style'), '正式专业')}",
                "## 正文",
                body,
                "## 突出亮点",
                _text(highlights, "暂无"),
                "## 可优化建议",
                _text(suggestions, "暂无"),
            ]
        )

    def career_plan_markdown(self, report: dict[str, Any]) -> str:
        profile = report.get("career_profile") or {}
        matching = report.get("matching_analysis") or {}
        plan = report.get("career_plan") or {}
        learning = report.get("learning_path") or {}
        return "\n\n".join(
            [
                "# 职业规划报告",
                f"当前阶段：{_text(profile.get('current_stage'), '待补充')}",
                f"目标方向：{_text(profile.get('target_direction'), '待补充')}",
                f"目标岗位匹配度：{matching.get('match_score', 0)}/100",
                "## 当前优势",
                _text(profile.get("current_strengths"), "暂无"),
                "## 主要差距",
                _text(profile.get("main_gaps"), "暂无"),
                "## 短期规划",
                _text(plan.get("short_term"), "暂无"),
                "## 中期规划",
                _text(plan.get("mid_term"), "暂无"),
                "## 长期规划",
                _text(plan.get("long_term"), "暂无"),
                "## 学习路径",
                f"### 1 周\n{_text(learning.get('one_week'), '暂无')}",
                f"### 1 个月\n{_text(learning.get('one_month'), '暂无')}",
                f"### 3 个月\n{_text(learning.get('three_months'), '暂无')}",
                f"### 6 个月\n{_text(learning.get('six_months'), '暂无')}",
                "## 项目补强建议",
                _text(report.get("project_suggestions"), "暂无"),
                "## 投递策略",
                _text(report.get("job_search_strategy"), "暂无"),
                "## 下一步行动",
                _text(report.get("next_actions"), "暂无"),
            ]
        )

    def markdown_bytes(self, markdown: str) -> bytes:
        return markdown.encode("utf-8")

    def docx_bytes(self, markdown: str) -> bytes:
        document = Document()
        for raw_line in markdown.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("# "):
                document.add_heading(line[2:].strip(), level=1)
            elif line.startswith("## "):
                document.add_heading(line[3:].strip(), level=2)
            elif line.startswith("### "):
                document.add_heading(line[4:].strip(), level=3)
            elif line.startswith("- "):
                document.add_paragraph(line[2:].strip(), style="List Bullet")
            else:
                document.add_paragraph(line)
        buffer = BytesIO()
        document.save(buffer)
        return buffer.getvalue()

    def pdf_bytes(self, title: str, markdown: str) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=16 * mm,
            rightMargin=16 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
            title=title,
        )
        story: list[Any] = []
        for raw_line in markdown.splitlines():
            line = raw_line.strip()
            if not line:
                story.append(Spacer(1, 5))
                continue
            if line.startswith("# "):
                story.append(Paragraph(line[2:].strip(), self.title))
            elif line.startswith("## "):
                story.append(Paragraph(line[3:].strip(), self.h2))
            elif line.startswith("### "):
                story.append(Paragraph(line[4:].strip(), self.h2))
            else:
                story.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), self.body))
        doc.build(story)
        return buffer.getvalue()


document_export_service = DocumentExportService()
