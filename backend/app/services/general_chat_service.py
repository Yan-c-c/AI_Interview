from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llms import get_llm_for_request


class GeneralChatService:
    async def chat(self, message: str, api_config: dict | None = None) -> str:
        text = (message or "").strip()
        if not text:
            return "你可以直接和我聊天，也可以上传简历后输入“帮我看看这份简历”触发简历评估，或输入“根据简历生成模拟面试”触发模拟面试。"

        llm = get_llm_for_request(api_config=api_config, channel="smart", temperature=0.4, max_tokens=1600)
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content=(
                        "你是智能面试助手。默认进行自然、简洁、有帮助的中文对话。"
                        "只有用户明确提出简历评估、简历优化、简历风险检测等需求时，才建议进入简历评估流程；"
                        "只有用户明确提出根据简历生成面试题、模拟面试、语音面试、练习题或题库检索时，才建议进入模拟面试流程。"
                        "只有用户明确提出求职信、自荐信、申请邮件时，才建议进入求职信生成流程；"
                        "只有用户明确提出邮件群发、批量发送求职邮件、给多个 HR 发邮件时，才建议进入邮件群发流程；"
                        "只有用户明确提出职业规划、转岗、学习路径或投递策略时，才建议进入职业规划流程。"
                        "不要编造用户简历内容。"
                    )
                ),
                HumanMessage(content=text),
            ]
        )
        return str(response.content or "").strip() or "我理解了。"


general_chat_service = GeneralChatService()
