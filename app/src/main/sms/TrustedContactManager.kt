package com.kavach.sms

import android.content.Context
import android.content.SharedPreferences
import android.telephony.SmsManager
import android.util.Log

/**
 * Responsibility 5: Send a high-risk warning to the trusted contact.
 */
object TrustedContactManager {

    private const val PREFS_NAME = "kavach_trusted_contact"
    private const val KEY_NAME = "contact_name"
    private const val KEY_PHONE = "contact_phone"
    private const val KEY_CONSENT = "contact_consent"
    private const val KEY_LAST_ALERT_TIME = "last_alert_time"
    private const val ALERT_COOLDOWN_MS = 5 * 60 * 1000L

    private fun getPrefs(context: Context): SharedPreferences {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    }

    fun saveContact(context: Context, name: String, phone: String, consent: Boolean): Boolean {
        if (!isValidIndianMobile(phone)) return false
        if (name.trim().length < 2) return false
        if (!consent) return false
        getPrefs(context).edit()
            .putString(KEY_NAME, name.trim())
            .putString(KEY_PHONE, phone.trim())
            .putBoolean(KEY_CONSENT, consent)
            .apply()
        return true
    }

    fun getContact(context: Context): TrustedContact? {
        val prefs = getPrefs(context)
        val name = prefs.getString(KEY_NAME, null)
        val phone = prefs.getString(KEY_PHONE, null)
        val consent = prefs.getBoolean(KEY_CONSENT, false)
        if (name.isNullOrBlank() || phone.isNullOrBlank() || !consent) return null
        return TrustedContact(name, phone, consent)
    }

    fun hasValidContact(context: Context): Boolean = getContact(context) != null

    fun isValidIndianMobile(phone: String): Boolean {
        val clean = phone.trim().replace(" ", "").replace("-", "")
        return clean.matches(Regex("^[6-9]\\d{9}$"))
    }

    fun removeContact(context: Context) {
        getPrefs(context).edit().clear().apply()
    }

    fun sendHighRiskAlert(context: Context, result: RiskResult): Boolean {
        val contact = getContact(context) ?: run {
            Log.d("TrustedContact", "No trusted contact configured")
            return false
        }
        val prefs = getPrefs(context)
        val lastAlert = prefs.getLong(KEY_LAST_ALERT_TIME, 0)
        val now = System.currentTimeMillis()
        if ((now - lastAlert) < ALERT_COOLDOWN_MS) {
            Log.d("TrustedContact", "Alert cooldown active, skipping")
            return false
        }
        val language = context.getSharedPreferences("kavach_settings", Context.MODE_PRIVATE)
            .getString("language", "en") ?: "en"
        val message = buildAlertMessage(result, contact, language)
        return try {
            val smsManager = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
                context.getSystemService(SmsManager::class.java)
            } else {
                @Suppress("DEPRECATION")
                SmsManager.getDefault()
            }
            smsManager.sendTextMessage(contact.phone, null, message, null, null)
            prefs.edit().putLong(KEY_LAST_ALERT_TIME, now).apply()
            Log.d("TrustedContact", "High-risk alert sent to ${contact.phone}")
            true
        } catch (e: Exception) {
            Log.e("TrustedContact", "Failed to send alert", e)
            false
        }
    }

    private fun buildAlertMessage(result: RiskResult, contact: TrustedContact, language: String): String {
        val senderMasked = maskSender(result.sms.sender)
        val timeStr = java.text.SimpleDateFormat("dd MMM, hh:mm a", java.util.Locale.getDefault())
            .format(java.util.Date(result.sms.timestamp))
        return if (language == "hi") {
            """
            [कवच सुरक्षा अलर्ट]
            नमस्ते ${contact.name},
            
            ${senderMasked} से एक खतरनाक SMS मिला है ($timeStr)।
            जोखिम: ${getHindiReason(result)}
            
            कृपया तुरंत संपर्क करें। लिंक पर क्लिक न करें, OTP/PIN साझा न करें।
            - Kavach App
            """.trimIndent()
        } else {
            """
            [KAVACH SAFETY ALERT]
            Hi ${contact.name},
            
            High-risk SMS detected from $senderMasked at $timeStr.
            Risk: ${result.reasons.firstOrNull() ?: "Suspicious content"}
            
            Please check on them urgently. Advise NOT to click links or share OTP/PIN.
            - Kavach App
            """.trimIndent()
        }
    }

    private fun maskSender(sender: String): String {
        return when {
            sender.length <= 4 -> sender
            sender.all { it.isDigit() } && sender.length == 10 -> {
                "+91 ••••••${sender.takeLast(4)}"
            }
            else -> {
                if (sender.length > 6) {
                    sender.take(3) + "••••" + sender.takeLast(2)
                } else sender
            }
        }
    }

    private fun getHindiReason(result: RiskResult): String {
        val code = result.reasonCodes.firstOrNull()
        return when (code) {
            RiskEngine.REASON_KYC_SCAM -> "फर्जी KYC अपडेट का झांसा"
            RiskEngine.REASON_LOTTERY -> "लॉटरी/इनाम का झांसा"
            RiskEngine.REASON_OTP_REQUEST -> "OTP/PIN मांग रहा है"
            RiskEngine.REASON_BANK_BLOCK -> "खाता ब्लॉक होने की धमकी"
            RiskEngine.REASON_LINK -> "खतरनाक लिंक है"
            RiskEngine.REASON_URGENCY -> "जल्दबाजी में डाल रहा है"
            else -> "संदिग्ध मैसेज"
        }
    }
}
