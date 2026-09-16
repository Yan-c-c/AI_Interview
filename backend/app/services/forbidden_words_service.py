from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ForbiddenTerm:
    word: str
    risk_type: str


FORBIDDEN_TERMS = [
    ForbiddenTerm("精通", "过度绝对化"),
    ForbiddenTerm("完全掌握", "过度绝对化"),
    ForbiddenTerm("顶级", "过度绝对化"),
    ForbiddenTerm("最强", "过度绝对化"),
    ForbiddenTerm("无敌", "过度绝对化"),
    ForbiddenTerm("百分百", "过度绝对化"),
    ForbiddenTerm("熟悉各种", "低可信表达"),
    ForbiddenTerm("参与多个", "低可信表达"),
    ForbiddenTerm("负责相关", "低可信表达"),
    ForbiddenTerm("做过一些", "低可信表达"),
    ForbiddenTerm("了解一点", "低可信表达"),
    ForbiddenTerm("吃苦耐劳", "空泛套话"),
    ForbiddenTerm("认真负责", "空泛套话"),
    ForbiddenTerm("积极向上", "空泛套话"),
    ForbiddenTerm("沟通能力强", "空泛套话"),
    ForbiddenTerm("学习能力强", "空泛套话"),
    ForbiddenTerm("独立完成大型系统", "容易被质疑的表达"),
    ForbiddenTerm("全栈精通", "容易被质疑的表达"),
    ForbiddenTerm("核心负责人", "容易被质疑的表达"),
    ForbiddenTerm("深度参与", "容易被质疑的表达"),
]


class ForbiddenWordsCheckTool:
    name = "ForbiddenWordsCheckTool"

    def run(self, resume_text: str) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        compact = resume_text.replace("\r", "")
        for term in FORBIDDEN_TERMS:
            start = 0
            while True:
                idx = compact.find(term.word, start)
                if idx == -1:
                    break
                context_start = max(0, idx - 30)
                context_end = min(len(compact), idx + len(term.word) + 45)
                findings.append(
                    {
                        "word": term.word,
                        "risk_type": term.risk_type,
                        "context": compact[context_start:context_end].replace("\n", " ").strip(),
                        "tool_note": "本地工具仅标记命中线索，实际风险等级需由风险与模板审查 Agent 结合上下文判断。",
                    }
                )
                start = idx + len(term.word)
        return findings[:80]
