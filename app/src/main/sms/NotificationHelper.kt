package com.kavach.sms

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat

/**
 * Responsibility 4: Generate a warning notification in the selected language.
 */
object NotificationHelper {

    private const val CHANNEL_ID = "kavach_sms_alerts"
    private const val CHANNEL_NAME = "Kavach SMS Protection"
    private const val CHANNEL_DESC = "Warnings for risky SMS messages"

    private val translations = mapOf(
        "en" to mapOf(
            "high_risk_title" to "⚠️ High-Risk SMS Detected!",
            "suspicious_title" to "⚠️ Suspicious SMS Detected",
            "safe_title" to "✅ SMS Checked - Safe",
            "high_risk_body" to "From %s: %s. Do NOT click links or share OTP/PIN.",
            "suspicious_body" to "From %s: %s. Be cautious, verify before acting.",
            "safe_body" to "SMS from %s looks safe.",
            "action_view" to "View Details"
        ),
        "hi" to mapOf(
            "high_risk_title" to "⚠️ खतरनाक SMS मिला!",
            "suspicious_title" to "⚠️ संदिग्ध SMS मिला",
            "safe_title" to "✅ SMS सुरक्षित है",
            "high_risk_body" to "%s से: %s। लिंक पर क्लिक न करें, OTP/PIN साझा न करें।",
            "suspicious_body" to "%s से: %s। सतर्क रहें, कार्रवाई से पहले जांच लें।",
            "safe_body" to "%s से SMS सुरक्षित लग रहा है।",
            "action_view" to "विवरण देखें"
        )
    )

    fun createNotificationChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = CHANNEL_DESC
                enableVibration(true)
            }
            val manager = context.getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    fun showWarning(context: Context, result: RiskResult) {
        createNotificationChannel(context)
        val prefs = context.getSharedPreferences("kavach_settings", Context.MODE_PRIVATE)
        val language = prefs.getString("language", "en") ?: "en"
        val langMap = translations[language] ?: translations["en"]!!

        val (titleKey, bodyKey) = when (result.level) {
            RiskLevel.HIGH_RISK -> "high_risk_title" to "high_risk_body"
            RiskLevel.SUSPICIOUS -> "suspicious_title" to "suspicious_body"
            RiskLevel.SAFE -> "safe_title" to "safe_body"
        }

        val title = langMap[titleKey] ?: "Kavach Alert"
        val reasonText = if (language == "hi") getHindiReason(result) else result.reasons.firstOrNull() ?: "Suspicious"
        val bodyTemplate = langMap[bodyKey] ?: "SMS from %s: %s"
        val body = if (result.level == RiskLevel.SAFE) {
            String.format(bodyTemplate, result.sms.sender)
        } else {
            String.format(bodyTemplate, result.sms.sender, reasonText)
        }

        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            putExtra("open_page", "sms")
            putExtra("risk_level", result.level.name)
        }

        val pendingIntent = PendingIntent.getActivity(
            context,
            result.sms.timestamp.toInt(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val builder = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .addAction(
                android.R.drawable.ic_menu_view,
                langMap["action_view"],
                pendingIntent
            )

        when (result.level) {
            RiskLevel.HIGH_RISK -> builder.setColor(0xFFD32F2F.toInt())
            RiskLevel.SUSPICIOUS -> builder.setColor(0xFFFF9800.toInt())
            RiskLevel.SAFE -> builder.setColor(0xFF4CAF50.toInt())
        }

        if (result.level != RiskLevel.SAFE) {
            try {
                with(NotificationManagerCompat.from(context)) {
                    notify(result.sms.timestamp.toInt(), builder.build())
                }
            } catch (e: SecurityException) {
                e.printStackTrace()
            }
        }

        saveResultToPrefs(context, result)
    }

    private fun saveResultToPrefs(context: Context, result: RiskResult) {
        val prefs = context.getSharedPreferences("kavach_sms_results", Context.MODE_PRIVATE)
        val json = """
            {
                "sender": "${result.sms.sender}",
                "body": "${result.sms.body.take(100).replace("\"", "'")}",
                "timestamp": ${result.sms.timestamp},
                "level": "${result.level.name}",
                "score": ${result.score},
                "reasons": "${result.reasons.joinToString(", ")}",
                "reasonCodes": "${result.reasonCodes.joinToString(",")}",
                "hasLink": ${result.hasLink}
            }
        """.trimIndent()
        prefs.edit().putString("latest_result", json).apply()
    }

    private fun getHindiReason(result: RiskResult): String {
        val code = result.reasonCodes.firstOrNull()
        return when (code) {
            RiskEngine.REASON_KYC_SCAM -> "फर्जी KYC अपडेट"
            RiskEngine.REASON_LOTTERY -> "लॉटरी का झांसा"
            RiskEngine.REASON_OTP_REQUEST -> "OTP/PIN मांग रहा है"
            RiskEngine.REASON_BANK_BLOCK -> "खाता ब्लॉक की धमकी"
            RiskEngine.REASON_LINK -> "खतरनाक लिंक"
            RiskEngine.REASON_URGENCY -> "जल्दबाजी में डाल रहा है"
            RiskEngine.REASON_UNKNOWN_SENDER -> "अनजान नंबर से लिंक"
            else -> result.reasons.firstOrNull() ?: "संदिग्ध"
        }
    }
}
