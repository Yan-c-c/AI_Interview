package com.harmony.interviewlite.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import org.json.JSONTokener
import java.net.HttpURLConnection
import java.net.URL

class ApiException(message: String) : Exception(message)

object ApiClient {
    suspend fun login(baseUrl: String, email: String, password: String): AuthSession {
        val data = requestJson(
            baseUrl = baseUrl,
            path = "/api/admin/auth/login",
            method = "POST",
            token = null,
            body = JSONObject()
                .put("email", email)
                .put("password", password)
        )
        return AuthSession(
            token = data.optString("token"),
            user = AuthUser.fromJson(data.getJSONObject("user"))
        )
    }

    suspend fun register(baseUrl: String, name: String, email: String, password: String): AuthSession {
        val data = requestJson(
            baseUrl = baseUrl,
            path = "/api/admin/auth/register",
            method = "POST",
            token = null,
            body = JSONObject()
                .put("name", name)
                .put("email", email)
                .put("password", password)
        )
        return AuthSession(
            token = data.optString("token"),
            user = AuthUser.fromJson(data.getJSONObject("user"))
        )
    }

    suspend fun me(baseUrl: String, token: String): AuthUser {
        val data = requestJson(
            baseUrl = baseUrl,
            path = "/api/admin/auth/me",
            method = "GET",
            token = token,
            body = null
        )
        return AuthUser.fromJson(data.getJSONObject("user"))
    }

    suspend fun chat(baseUrl: String, token: String, message: String, sessionId: String): AssistantPayload {
        val data = requestJson(
            baseUrl = baseUrl,
            path = "/api/assistant/chat",
            method = "POST",
            token = token,
            body = JSONObject()
                .put("message", message)
                .put("session_id", sessionId)
        )
        val result = if (data.has("result") && !data.isNull("result")) data.opt("result") else null
        val rawJson = prettyJson(data)
        val messageText = data.optNullableString("message")
        val displayText = renderAssistantText(messageText.orEmpty(), result, rawJson)
        return AssistantPayload(
            success = data.optBoolean("success", false),
            intent = data.optString("intent", "unknown"),
            agent = data.optNullableString("agent"),
            message = messageText,
            displayText = displayText,
            rawJson = rawJson
        )
    }

    private suspend fun requestJson(
        baseUrl: String,
        path: String,
        method: String,
        token: String?,
        body: JSONObject?
    ): JSONObject {
        val text = requestText(baseUrl, path, method, token, body)
        val parsed = try {
            JSONTokener(text).nextValue()
        } catch (_: Exception) {
            throw ApiException("后端响应不是有效 JSON")
        }
        return parsed as? JSONObject ?: throw ApiException("后端响应格式无效")
    }

    private suspend fun requestText(
        baseUrl: String,
        path: String,
        method: String,
        token: String?,
        body: JSONObject?
    ): String = withContext(Dispatchers.IO) {
        val connection = (URL(joinUrl(baseUrl, path)).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 15_000
            readTimeout = 120_000
            setRequestProperty("Accept", "application/json")
            if (!token.isNullOrBlank()) {
                setRequestProperty("Authorization", "Bearer $token")
            }
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
            }
        }

        try {
            if (body != null) {
                connection.outputStream.use { stream ->
                    stream.write(body.toString().toByteArray(Charsets.UTF_8))
                }
            }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            if (status !in 200..299) {
                throw ApiException(extractErrorMessage(text, status))
            }
            text
        } finally {
            connection.disconnect()
        }
    }

    private fun joinUrl(baseUrl: String, path: String): String {
        val cleanBase = baseUrl.trimEnd('/')
        val cleanPath = if (path.startsWith("/")) path else "/$path"
        return cleanBase + cleanPath
    }

    private fun extractErrorMessage(raw: String, status: Int): String {
        return try {
            val data = JSONTokener(raw).nextValue() as? JSONObject
            val detail = data?.opt("detail")
            when {
                detail is JSONObject && !detail.optString("message").isNullOrBlank() -> detail.optString("message")
                detail is JSONObject && !detail.optString("error").isNullOrBlank() -> detail.optString("error")
                detail is String && detail.isNotBlank() -> detail
                data != null && data.optString("message").isNotBlank() -> data.optString("message")
                else -> "请求失败：HTTP $status"
            }
        } catch (_: Exception) {
            "请求失败：HTTP $status"
        }
    }

    private fun renderAssistantText(message: String, result: Any?, rawJson: String): String {
        val sections = mutableListOf<String>()
        if (message.isNotBlank()) {
            sections += message
        }
        if (result is JSONObject) {
            val knownSections = listOf(
                "summary" to "摘要",
                "versions" to "生成版本",
                "email" to "邮件正文",
                "questions" to "面试题",
                "strategy" to "谈薪策略",
                "career_plan" to "职业计划",
                "qa_analysis" to "逐题分析"
            )
            knownSections.forEach { (key, label) ->
                if (result.has(key) && !result.isNull(key)) {
                    sections += "$label\n${prettyJson(result.opt(key))}"
                }
            }
        }
        if (sections.isEmpty()) {
            sections += rawJson
        }
        return sections.joinToString("\n\n")
    }

    fun prettyJson(value: Any?): String {
        return try {
            when (value) {
                is JSONObject -> value.toString(2)
                is JSONArray -> value.toString(2)
                null -> ""
                else -> value.toString()
            }
        } catch (_: Exception) {
            value?.toString().orEmpty()
        }
    }
}
