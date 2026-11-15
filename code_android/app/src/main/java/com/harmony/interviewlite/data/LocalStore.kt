package com.harmony.interviewlite.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import org.json.JSONTokener

const val DefaultBaseUrl = GeneratedBackendBaseUrl

class LocalStore(context: Context) {
    private val prefs = context.getSharedPreferences(StoreName, Context.MODE_PRIVATE)

    fun getToken(): String = prefs.getString(KeyToken, "").orEmpty()

    fun saveToken(token: String) {
        prefs.edit().putString(KeyToken, token).apply()
    }

    fun getUser(): AuthUser? {
        val raw = prefs.getString(KeyUser, "").orEmpty()
        if (raw.isBlank()) return null
        return try {
            AuthUser.fromJson(JSONTokener(raw).nextValue() as JSONObject)
        } catch (_: Exception) {
            null
        }
    }

    fun saveUser(user: AuthUser) {
        prefs.edit().putString(KeyUser, user.toJson().toString()).apply()
    }

    fun clearSession() {
        prefs.edit()
            .remove(KeyToken)
            .remove(KeyUser)
            .apply()
    }

    fun getBaseUrl(): String = DefaultBaseUrl

    fun getAutoSaveHistory(): Boolean = prefs.getBoolean(KeyAutoSaveHistory, true)

    fun saveAutoSaveHistory(enabled: Boolean) {
        prefs.edit().putBoolean(KeyAutoSaveHistory, enabled).apply()
    }

    fun getHistory(): List<HistoryRecord> {
        val raw = prefs.getString(KeyHistory, "[]").orEmpty()
        return try {
            val array = JSONTokener(raw).nextValue() as JSONArray
            buildList {
                for (index in 0 until array.length()) {
                    val item = array.optJSONObject(index) ?: continue
                    add(HistoryRecord.fromJson(item))
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    fun saveHistory(records: List<HistoryRecord>) {
        val array = JSONArray()
        records.forEach { array.put(it.toJson()) }
        prefs.edit().putString(KeyHistory, array.toString()).apply()
    }

    companion object {
        private const val StoreName = "harmony_lite_store"
        private const val KeyToken = "auth_token"
        private const val KeyUser = "auth_user"
        private const val KeyHistory = "history_records"
        private const val KeyAutoSaveHistory = "auto_save_history"
    }
}
