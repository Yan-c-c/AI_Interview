package com.harmony.interviewlite

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.harmony.interviewlite.data.AgentShortcut
import com.harmony.interviewlite.data.ApiClient
import com.harmony.interviewlite.data.AssistantPayload
import com.harmony.interviewlite.data.AuthUser
import com.harmony.interviewlite.data.ChatMessage
import com.harmony.interviewlite.data.ChatRole
import com.harmony.interviewlite.data.DefaultBaseUrl
import com.harmony.interviewlite.data.HistoryRecord
import com.harmony.interviewlite.data.LocalStore
import com.harmony.interviewlite.data.titleForIntent
import kotlinx.coroutines.launch
import java.util.UUID

class HarmonyViewModel(application: Application) : AndroidViewModel(application) {
    private val store = LocalStore(application)

    var isReady by mutableStateOf(false)
        private set
    var currentTab by mutableStateOf(0)
        private set
    var authMode by mutableStateOf(0)
        private set
    var isLoading by mutableStateOf(false)
        private set
    var user by mutableStateOf<AuthUser?>(null)
        private set
    var token by mutableStateOf("")
        private set
    var baseUrl by mutableStateOf(DefaultBaseUrl)
        private set
    var autoSaveHistory by mutableStateOf(true)
        private set
    var authError by mutableStateOf<String?>(null)
        private set
    var statusMessage by mutableStateOf("")
        private set
    var draft by mutableStateOf("")
        private set
    var sessionId by mutableStateOf(UUID.randomUUID().toString())
        private set
    var isSending by mutableStateOf(false)
        private set
    var selectedHistory by mutableStateOf<HistoryRecord?>(null)
        private set

    val messages = mutableStateListOf<ChatMessage>()
    val history = mutableStateListOf<HistoryRecord>()

    val isAuthenticated: Boolean
        get() = user != null && token.isNotBlank()

    init {
        resetConversation()
        viewModelScope.launch { bootstrap() }
    }

    fun switchTab(index: Int) {
        currentTab = index
    }

    fun switchAuthMode(index: Int) {
        authMode = index
        authError = null
    }

    fun updateDraft(value: String) {
        draft = value
    }

    fun openShortcut(shortcut: AgentShortcut) {
        draft = shortcut.prompt
        currentTab = 1
    }

    fun selectHistory(record: HistoryRecord?) {
        selectedHistory = record
    }

    fun toggleAutoSaveHistory(enabled: Boolean) {
        autoSaveHistory = enabled
        store.saveAutoSaveHistory(enabled)
    }

    fun login(email: String, password: String) {
        if (email.isBlank() || password.isBlank()) {
            authError = "请输入邮箱和密码。"
            return
        }
        viewModelScope.launch {
            isLoading = true
            authError = null
            runCatching { ApiClient.login(baseUrl, email.trim(), password) }
                .onSuccess { session ->
                    token = session.token
                    user = session.user
                    store.saveToken(session.token)
                    store.saveUser(session.user)
                    currentTab = 0
                    statusMessage = "登录有效"
                }
                .onFailure { authError = it.message ?: "登录失败。" }
            isLoading = false
        }
    }

    fun register(name: String, email: String, password: String) {
        if (name.isBlank() || email.isBlank() || password.isBlank()) {
            authError = "请输入姓名、邮箱和密码。"
            return
        }
        viewModelScope.launch {
            isLoading = true
            authError = null
            runCatching { ApiClient.register(baseUrl, name.trim(), email.trim(), password) }
                .onSuccess { session ->
                    token = session.token
                    user = session.user
                    store.saveToken(session.token)
                    store.saveUser(session.user)
                    currentTab = 0
                    statusMessage = "登录有效"
                }
                .onFailure { authError = it.message ?: "注册失败。" }
            isLoading = false
        }
    }

    fun validateToken(showResult: Boolean = true) {
        viewModelScope.launch {
            if (token.isBlank()) {
                statusMessage = "未保存 Token"
                return@launch
            }
            isLoading = true
            runCatching { ApiClient.me(baseUrl, token) }
                .onSuccess { freshUser ->
                    user = freshUser
                    store.saveUser(freshUser)
                    if (showResult) statusMessage = "登录有效"
                }
                .onFailure {
                    store.clearSession()
                    token = ""
                    user = null
                    if (showResult) statusMessage = "登录已失效，请重新登录"
                }
            isLoading = false
        }
    }

    fun logout() {
        store.clearSession()
        token = ""
        user = null
        currentTab = 0
        authError = null
        statusMessage = ""
        resetConversation()
    }

    fun resetConversation() {
        sessionId = UUID.randomUUID().toString()
        messages.clear()
        messages += ChatMessage(
            role = ChatRole.Assistant,
            text = "把简历、项目、岗位、面试回答或 Offer 信息贴进来，我会调用后端 Agent 处理。"
        )
        draft = ""
    }

    fun sendChat() {
        val text = draft.trim()
        if (text.isBlank() || isSending) return
        viewModelScope.launch {
            draft = ""
            isSending = true
            messages += ChatMessage(role = ChatRole.User, text = text)
            runCatching { ApiClient.chat(baseUrl, token, text, sessionId) }
                .onSuccess { payload ->
                    val reply = payload.displayText.ifBlank { payload.message ?: "已完成。" }
                    messages += ChatMessage(role = ChatRole.Assistant, text = reply)
                    if (autoSaveHistory) {
                        addHistory(payload = payload, userMessage = text)
                    }
                }
                .onFailure { error ->
                    messages += ChatMessage(
                        role = ChatRole.Assistant,
                        text = "请求失败：${error.message ?: "网络请求异常"}"
                    )
                }
            isSending = false
        }
    }

    fun deleteHistory(record: HistoryRecord) {
        history.removeAll { it.id == record.id }
        store.saveHistory(history)
        if (selectedHistory?.id == record.id) {
            selectedHistory = null
        }
    }

    fun clearHistory() {
        history.clear()
        selectedHistory = null
        store.saveHistory(history)
    }

    private suspend fun bootstrap() {
        baseUrl = store.getBaseUrl()
        autoSaveHistory = store.getAutoSaveHistory()
        history.clear()
        history.addAll(store.getHistory())
        token = store.getToken()
        user = store.getUser()
        if (token.isNotBlank()) {
            runCatching { ApiClient.me(baseUrl, token) }
                .onSuccess { freshUser ->
                    user = freshUser
                    store.saveUser(freshUser)
                    statusMessage = "登录有效"
                }
                .onFailure {
                    store.clearSession()
                    token = ""
                    user = null
                    statusMessage = "登录已失效，请重新登录"
                }
        }
        isReady = true
    }

    private fun addHistory(payload: AssistantPayload, userMessage: String) {
        val record = HistoryRecord(
            title = titleForIntent(payload.intent, userMessage),
            intent = payload.intent,
            agent = payload.agent,
            userMessage = userMessage,
            assistantMessage = payload.message.orEmpty(),
            resultText = payload.displayText,
            rawJson = payload.rawJson
        )
        history.add(0, record)
        store.saveHistory(history)
    }
}
