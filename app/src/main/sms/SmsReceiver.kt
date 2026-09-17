package com.kavach.sms

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Telephony
import android.util.Log

/**
 * Responsibility 2: Detect newly received SMS automatically.
 * Responsibility 3: Pass SMS text to the risk engine.
 * Responsibility 4,5,6 handled after analysis.
 * Additive - new package, no existing file touched
 */
class SmsReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return

        if (!SmsPermissionManager.hasReceiveSmsPermission(context)) {
            Log.w("SmsReceiver", "RECEIVE_SMS permission not granted")
            return
        }

        try {
            val messages = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
                Telephony.Sms.Intents.getMessagesFromIntent(intent)
            } else {
                @Suppress("DEPRECATION")
                val pdus = intent.extras?.get("pdus") as? Array<*>
                @Suppress("DEPRECATION")
                val format = intent.extras?.getString("format")
                pdus?.mapNotNull { pdu ->
                    @Suppress("DEPRECATION")
                    android.telephony.SmsMessage.createFromPdu(pdu as ByteArray, format)
                }?.toTypedArray()
            }

            if (messages.isNullOrEmpty()) return

            val sender = messages[0].originatingAddress ?: "Unknown"
            val body = messages.joinToString("") { it.messageBody ?: "" }
            val timestamp = messages[0].timestampMillis

            val sms = SmsMessage(
                sender = sender,
                body = body,
                timestamp = timestamp
            )

            Log.d("SmsReceiver", "New SMS from $sender: ${body.take(50)}...")

            if (DuplicateAlertManager.isDuplicate(context, sms)) {
                Log.d("SmsReceiver", "Duplicate SMS detected, skipping: ${sms.id}")
                return
            }

            val riskResult = RiskEngine.analyze(sms)
            Log.d("SmsReceiver", "Risk analysis: ${riskResult.level} score=${riskResult.score} reasons=${riskResult.reasons}")

            DuplicateAlertManager.markAsProcessed(context, sms)

            NotificationHelper.showWarning(context, riskResult)

            if (riskResult.level == RiskLevel.HIGH_RISK) {
                val sent = TrustedContactManager.sendHighRiskAlert(context, riskResult)
                Log.d("SmsReceiver", "Trusted contact alert sent: $sent")
            }

            val broadcastIntent = Intent("com.kavach.SMS_ANALYZED").apply {
                putExtra("sender", riskResult.sms.sender)
                putExtra("body", riskResult.sms.body)
                putExtra("timestamp", riskResult.sms.timestamp)
                putExtra("level", riskResult.level.name)
                putExtra("score", riskResult.score)
                putExtra("reasons", riskResult.reasons.joinToString(","))
                putExtra("reasonCodes", riskResult.reasonCodes.joinToString(","))
                putExtra("hasLink", riskResult.hasLink)
            }
            context.sendBroadcast(broadcastIntent)

        } catch (e: Exception) {
            Log.e("SmsReceiver", "Error processing SMS", e)
        }
    }
}
