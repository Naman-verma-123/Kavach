package com.kavach.sms

import java.util.regex.Pattern

/**
 * Responsibility 3: Pass SMS text to the risk engine.
 * Additive module - new package
 */
object RiskEngine {

    private val URL_PATTERN = Pattern.compile(
        "(https?://|www\\.|bit\\.ly|tinyurl|t\\.me|goo\\.gl|rebrand\\.ly|cutt\\.ly|is\\.gd|shorturl|\\b[a-z0-9-]+\\.(com|in|net|org|xyz|top|click|link|info)/\\S*)",
        Pattern.CASE_INSENSITIVE
    )

    private val HIGH_RISK_KEYWORDS = listOf(
        "kyc blocked", "kyc suspended", "kyc update immediately", "account blocked", "account suspended",
        "lottery won", "you have won", "prize", "congratulations you won",
        "urgent", "immediately", "within 24 hours", "last warning", "final notice",
        "click here", "verify now", "update now",
        "bank account blocked", "pan blocked", "aadhaar blocked",
        "electricity bill", "electricity connection will be cut",
        "job offer", "earn daily", "work from home earn",
        "share otp", "share pin", "share cvv", "share password",
        "customs", "parcel held", "delivery failed",
        "income tax refund", "refund"
    )

    private val SUSPICIOUS_KEYWORDS = listOf(
        "offer", "discount", "free", "click", "link", "update", "verify",
        "limited time", "act now", "dear customer", "dear user"
    )

    const val REASON_LINK = "contains_link"
    const val REASON_URGENCY = "urgency_language"
    const val REASON_KYC_SCAM = "kyc_scam"
    const val REASON_LOTTERY = "lottery_scam"
    const val REASON_OTP_REQUEST = "otp_request"
    const val REASON_BANK_BLOCK = "bank_block_scam"
    const val REASON_UNKNOWN_SENDER = "unknown_sender"
    const val REASON_SUSPICIOUS_PROMO = "suspicious_promo"

    fun analyze(sms: SmsMessage): RiskResult {
        val bodyLower = sms.body.lowercase()
        var score = 0
        val reasons = mutableListOf<String>()
        val reasonCodes = mutableListOf<String>()

        val hasLink = URL_PATTERN.matcher(sms.body).find()
        val hasUrgency = bodyLower.contains("urgent") || bodyLower.contains("immediately") ||
                bodyLower.contains("तुरंत") || bodyLower.contains("अभी")

        if (hasLink) {
            score += 40
            reasons.add("Contains suspicious link")
            reasonCodes.add(REASON_LINK)
        }

        for (keyword in HIGH_RISK_KEYWORDS) {
            if (bodyLower.contains(keyword)) {
                score += 30
                when {
                    keyword.contains("kyc") -> {
                        reasons.add("Fake KYC update scam pattern")
                        reasonCodes.add(REASON_KYC_SCAM)
                    }
                    keyword.contains("lottery") || keyword.contains("won") || keyword.contains("prize") -> {
                        reasons.add("Lottery/Prize fraud pattern")
                        reasonCodes.add(REASON_LOTTERY)
                    }
                    keyword.contains("otp") || keyword.contains("pin") || keyword.contains("cvv") -> {
                        reasons.add("Asking to share OTP/PIN/CVV")
                        reasonCodes.add(REASON_OTP_REQUEST)
                    }
                    keyword.contains("blocked") || keyword.contains("suspended") -> {
                        reasons.add("Fake account blocked threat")
                        reasonCodes.add(REASON_BANK_BLOCK)
                    }
                    else -> {
                        if (!reasonCodes.contains(REASON_URGENCY) && hasUrgency) {
                            reasons.add("Creates false urgency")
                            reasonCodes.add(REASON_URGENCY)
                        }
                    }
                }
                break
            }
        }

        if (hasUrgency && !reasonCodes.contains(REASON_URGENCY)) {
            score += 15
            reasons.add("Creates false urgency")
            reasonCodes.add(REASON_URGENCY)
        }

        var promoCount = 0
        for (kw in SUSPICIOUS_KEYWORDS) {
            if (bodyLower.contains(kw)) promoCount++
        }
        if (promoCount >= 2) {
            score += 10
            if (!reasonCodes.contains(REASON_SUSPICIOUS_PROMO)) {
                reasons.add("Suspicious promotional language")
                reasonCodes.add(REASON_SUSPICIOUS_PROMO)
            }
        }

        if (sms.sender.length == 10 && sms.sender.all { it.isDigit() } && hasLink) {
            score += 20
            reasons.add("Unknown mobile number with link")
            reasonCodes.add(REASON_UNKNOWN_SENDER)
        }

        val level = when {
            score >= 50 -> RiskLevel.HIGH_RISK
            score >= 20 -> RiskLevel.SUSPICIOUS
            else -> RiskLevel.SAFE
        }

        if (level == RiskLevel.SAFE) {
            reasons.clear()
            reasonCodes.clear()
            reasons.add("No risky patterns detected")
        }

        return RiskResult(
            level = level,
            score = score,
            reasons = reasons.distinct(),
            reasonCodes = reasonCodes.distinct(),
            hasLink = hasLink,
            hasUrgency = hasUrgency,
            sms = sms
        )
    }

    fun analyzeText(sender: String, body: String, timestamp: Long = System.currentTimeMillis()): RiskResult {
        return analyze(SmsMessage(sender, body, timestamp))
    }
}
