package com.kavach.sms

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONArray
import org.json.JSONObject
import java.security.MessageDigest

/**
 * Responsibility 6: Prevent duplicate alerts.
 */
object DuplicateAlertManager {

    private const val PREFS_NAME = "kavach_duplicate_prefs"
    private const val KEY_HASHES = "processed_sms_hashes"
    private const val MAX_STORED = 50
    private const val DUPLICATE_WINDOW_MS = 10 * 60 * 1000L

    private fun getPrefs(context: Context): SharedPreferences {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    }

    private fun sha256(input: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val hash = digest.digest(input.toByteArray())
        return hash.joinToString("") { "%02x".format(it) }
    }

    fun generateHash(sms: SmsMessage): String {
        val normalizedBody = sms.body.trim().lowercase().replace("\\s+".toRegex(), " ")
        return sha256("${sms.sender}_${normalizedBody}")
    }

    fun isDuplicate(context: Context, sms: SmsMessage): Boolean {
        val hash = generateHash(sms)
        val prefs = getPrefs(context)
        val jsonStr = prefs.getString(KEY_HASHES, "[]") ?: "[]"
        try {
            val arr = JSONArray(jsonStr)
            val now = System.currentTimeMillis()
            for (i in 0 until arr.length()) {
                val obj = arr.getJSONObject(i)
                val storedHash = obj.getString("hash")
                val storedTime = obj.getLong("timestamp")
                if (storedHash == hash && (now - storedTime) < DUPLICATE_WINDOW_MS) {
                    return true
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return false
    }

    fun markAsProcessed(context: Context, sms: SmsMessage) {
        val hash = generateHash(sms)
        val prefs = getPrefs(context)
        val jsonStr = prefs.getString(KEY_HASHES, "[]") ?: "[]"
        try {
            val arr = JSONArray(jsonStr)
            val newArr = JSONArray()
            val now = System.currentTimeMillis()
            val validEntries = mutableListOf<JSONObject>()
            for (i in 0 until arr.length()) {
                val obj = arr.getJSONObject(i)
                val storedTime = obj.getLong("timestamp")
                if ((now - storedTime) < DUPLICATE_WINDOW_MS * 2) {
                    validEntries.add(obj)
                }
            }
            val newObj = JSONObject().apply {
                put("hash", hash)
                put("timestamp", now)
                put("sender", sms.sender)
            }
            validEntries.add(newObj)
            val toKeep = validEntries.takeLast(MAX_STORED)
            for (obj in toKeep) {
                newArr.put(obj)
            }
            prefs.edit().putString(KEY_HASHES, newArr.toString()).apply()
        } catch (e: Exception) {
            e.printStackTrace()
            val newArr = JSONArray().apply {
                put(JSONObject().apply {
                    put("hash", hash)
                    put("timestamp", System.currentTimeMillis())
                    put("sender", sms.sender)
                })
            }
            prefs.edit().putString(KEY_HASHES, newArr.toString()).apply()
        }
    }

    fun clearAll(context: Context) {
        getPrefs(context).edit().remove(KEY_HASHES).apply()
    }
}
