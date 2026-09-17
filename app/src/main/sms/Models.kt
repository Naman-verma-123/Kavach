package com.kavach.sms

// No conflict with existing files - new package com.kavach.sms
data class SmsMessage(
    val sender: String,
    val body: String,
    val timestamp: Long,
    val id: String = "${sender}_${timestamp}_${body.hashCode()}"
)

enum class RiskLevel {
    SAFE,
    SUSPICIOUS,
    HIGH_RISK
}

data class RiskResult(
    val level: RiskLevel,
    val score: Int,
    val reasons: List<String>,
    val reasonCodes: List<String>,
    val hasLink: Boolean,
    val hasUrgency: Boolean,
    val sms: SmsMessage
)

data class TrustedContact(
    val name: String,
    val phone: String,
    val consentGiven: Boolean
)
