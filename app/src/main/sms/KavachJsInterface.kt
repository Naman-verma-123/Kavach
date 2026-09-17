package com.kavach.sms

import android.app.Activity
import android.content.Context
import android.content.SharedPreferences
import android.webkit.JavascriptInterface
import org.json.JSONObject

/**
 * Bridge between WebView JS and Native Android
 * Additive - new file, does not replace existing
 */
class KavachJsInterface(private val activity: Activity) {

    private val context: Context get() = activity
    private val settingsPrefs: SharedPreferences
        get() = context.getSharedPreferences("kavach_settings", Context.MODE_PRIVATE)

    @JavascriptInterface
    fun requestSmsPermission() {
        activity.runOnUiThread {
            SmsPermissionManager.requestPermissions(activity)
        }
    }

    @JavascriptInterface
    fun checkSmsPermission(): String {
        return SmsPermissionManager.getPermissionStatus(context)
    }

    @JavascriptInterface
    fun getDetailedPermissionStatus(): String {
        val map = SmsPermissionManager.getDetailedStatus(context)
        return JSONObject(map as Map<*, *>).toString()
    }

    @JavascriptInterface
    fun getLanguage(): String {
        return settingsPrefs.getString("language", "en") ?: "en"
    }

    @JavascriptInterface
    fun setLanguage(lang: String) {
        settingsPrefs.edit().putString("language", lang).apply()
    }

    @JavascriptInterface
    fun getLatestResult(): String {
        val prefs = context.getSharedPreferences("kavach_sms_results", Context.MODE_PRIVATE)
        return prefs.getString("latest_result", "{}") ?: "{}"
    }

    @JavascriptInterface
    fun getTrustedContact(): String {
        val contact = TrustedContactManager.getContact(context)
        return if (contact != null) {
            JSONObject().apply {
                put("name", contact.name)
                put("phone", contact.phone)
                put("hasContact", true)
            }.toString()
        } else {
            JSONObject().apply {
                put("hasContact", false)
            }.toString()
        }
    }

    @JavascriptInterface
    fun saveTrustedContact(name: String, phone: String, consent: Boolean): String {
        val success = TrustedContactManager.saveContact(context, name, phone, consent)
        return JSONObject().apply {
            put("success", success)
            put("message", if (success) "saved" else "invalid")
        }.toString()
    }

    @JavascriptInterface
    fun removeTrustedContact() {
        TrustedContactManager.removeContact(context)
    }

    @JavascriptInterface
    fun analyzeText(sender: String, body: String): String {
        val result = RiskEngine.analyzeText(sender, body)
        return JSONObject().apply {
            put("sender", result.sms.sender)
            put("level", result.level.name)
            put("score", result.score)
            put("reasons", result.reasons.joinToString(","))
            put("reasonCodes", result.reasonCodes.joinToString(","))
            put("hasLink", result.hasLink)
            put("hasUrgency", result.hasUrgency)
        }.toString()
    }

    @JavascriptInterface
    fun isDuplicateCheck(sender: String, body: String): Boolean {
        val sms = SmsMessage(sender, body, System.currentTimeMillis())
        return DuplicateAlertManager.isDuplicate(context, sms)
    }

    @JavascriptInterface
    fun log(message: String) {
        android.util.Log.d("KavachJS", message)
    }
}
