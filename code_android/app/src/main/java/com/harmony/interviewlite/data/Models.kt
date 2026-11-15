package com.harmony.interviewlite.data

import org.json.JSONObject
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.UUID

data class AuthUser(
    val id: String,
    val name: String,
    val email: String,
    val role: String,
    val status: String,
    val createdAt: String? = null,
    val updatedAt: String? = null,
    val lastLoginAt: String? = null
) {
    fun toJson(): JSONObject = JSONObject()
        .put("id", id)
        .put("name", name)
        .put("email", email)
        .put("role", role)
        .put("status", status)
        .put("created_at", createdAt)
        .put("updated_at", updatedAt)
        .put("last_login_at", lastLoginAt)

    companion object {
        fun fromJson(json: JSONObject): AuthUser = AuthUser(
            id = json.optString("id"),
            name = json.optString("name"),
            email = json.optString("email"),
            role = json.optString("role", "user"),
            status = json.optString("status", "active"),
            createdAt = json.optNullableString("created_at"),
            updatedAt = json.optNullableString("updated_at"),
            lastLoginAt = json.optNullableString("last_login_at")
        )
    }
}

data class AuthSession(
    val token: String,
    val user: AuthUser
)

enum class ChatRole {
    User,
    Assistant
}

data class ChatMessage(
    val id: String = UUID.randomUUID().toString(),
    val role: ChatRole,
    val text: String,
    val createdAt: String = nowText()
)

data class HistoryRecord(
    val id: String = UUID.randomUUID().toString(),
    val title: String,
    val intent: String,
    val agent: String?,
    val userMessage: String,
    val assistantMessage: String,
    val resultText: String,
    val rawJson: String,
    val createdAt: String = nowText()
) {
    val preview: String
        get() {
            val source = (resultText.ifBlank { assistantMessage }).replace('\n', ' ')
            return if (source.length <= 96) source else source.take(96) + "..."
        }

    fun toJson(): JSONObject = JSONObject()
        .put("id", id)
        .put("title", title)
        .put("intent", intent)
        .put("agent", agent)
        .put("userMessage", userMessage)
        .put("assistantMessage", assistantMessage)
        .put("resultText", resultText)
        .put("rawJson", rawJson)
        .put("createdAt", createdAt)

    companion object {
        fun fromJson(json: JSONObject): HistoryRecord = HistoryRecord(
            id = json.optString("id", UUID.randomUUID().toString()),
            title = json.optString("title", "智能助手记录"),
            intent = json.optString("intent", "unknown"),
            agent = json.optNullableString("agent"),
            userMessage = json.optString("userMessage"),
            assistantMessage = json.optString("assistantMessage"),
            resultText = json.optString("resultText"),
            rawJson = json.optString("rawJson"),
            createdAt = json.optString("createdAt", nowText())
        )
    }
}

data class AssistantPayload(
    val success: Boolean,
    val intent: String,
    val agent: String?,
    val message: String?,
    val displayText: String,
    val rawJson: String
)

data class AgentShortcut(
    val key: String,
    val title: String,
    val subtitle: String,
    val iconText: String,
    val colorHex: String,
    val prompt: String
)

val AgentShortcuts = listOf(
    AgentShortcut(
        key = "resume",
        title = "简历评估",
        subtitle = "粘贴简历文本，生成优化建议",
        iconText = "简",
        colorHex = "#2563EB",
        prompt = """
            请帮我评估这份简历，指出岗位匹配度、主要风险、可量化优化建议和改写方向。

            目标岗位：

            简历文本：
        """.trimIndent()
    ),
    AgentShortcut(
        key = "interview",
        title = "模拟面试",
        subtitle = "岗位、技能、项目驱动问答",
        iconText = "面",
        colorHex = "#0F766E",
        prompt = """
            请基于以下岗位、技能栈和项目经历生成个性化面试题，并开始文字模拟面试。

            目标岗位：
            技能栈：
            项目经历：
            希望面试难度：
        """.trimIndent()
    ),
    AgentShortcut(
        key = "cover",
        title = "求职信",
        subtitle = "公司、岗位、JD 生成正文",
        iconText = "信",
        colorHex = "#4F46E5",
        prompt = """
            请生成一封个性化求职信，包含正式版和邮件精简版。

            目标公司：
            目标岗位：
            招聘 JD：
            个人背景：
            希望风格：
        """.trimIndent()
    ),
    AgentShortcut(
        key = "career",
        title = "职业规划",
        subtitle = "背景、目标、困惑形成路径",
        iconText = "规",
        colorHex = "#15803D",
        prompt = """
            请为我生成职业规划，包含能力画像、目标岗位匹配、学习路径、项目补强和投递策略。

            当前背景：
            目标方向：
            当前困惑：
            可投入时间：
            期望城市/行业：
        """.trimIndent()
    ),
    AgentShortcut(
        key = "salary",
        title = "谈薪助手",
        subtitle = "Offer、城市、经验谈判策略",
        iconText = "薪",
        colorHex = "#C2410C",
        prompt = """
            请作为谈薪助手，根据以下信息生成薪资判断、谈判策略和 HR 话术。

            岗位：
            城市：
            工作年限：
            技能栈：
            当前 Offer：
            期望薪资：
            其他约束：
        """.trimIndent()
    ),
    AgentShortcut(
        key = "email",
        title = "邮件润色",
        subtitle = "只生成或润色邮件正文",
        iconText = "邮",
        colorHex = "#BE185D",
        prompt = """
            请帮我生成或润色求职邮件正文，只输出邮件主题、正文和可替换版本，不要执行发送。

            目标公司：
            目标岗位：
            收件人：
            原邮件/想表达的内容：
            个人背景：
            希望语气：
        """.trimIndent()
    )
)

fun nowText(): String = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"))

fun JSONObject.optNullableString(name: String): String? =
    if (has(name) && !isNull(name)) optString(name) else null

fun intentLabel(intent: String): String = when (intent) {
    "resume_evaluation" -> "简历"
    "interview_question_generation" -> "面试"
    "interview_audio_analysis" -> "对话分析"
    "cover_letter_generation" -> "求职信"
    "career_planning" -> "规划"
    "salary_negotiation" -> "谈薪"
    "general_chat" -> "对话"
    else -> "记录"
}

fun titleForIntent(intent: String, userMessage: String): String {
    val firstLine = userMessage
        .lineSequence()
        .firstOrNull { it.trim().length > 6 }
        ?.trim()
    if (!firstLine.isNullOrBlank()) {
        return if (firstLine.length <= 28) firstLine else firstLine.take(28) + "..."
    }
    return when (intent) {
        "resume_evaluation" -> "简历评估报告"
        "interview_question_generation" -> "模拟面试题"
        "interview_audio_analysis" -> "面试对话分析"
        "cover_letter_generation" -> "求职信生成"
        "career_planning" -> "职业规划"
        "salary_negotiation" -> "谈薪策略"
        "general_chat" -> "智能助手对话"
        else -> "智能助手记录"
    }
}
