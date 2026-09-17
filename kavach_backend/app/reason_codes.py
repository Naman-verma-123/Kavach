"""
Reason codes for Kavach message analysis.

Design principle: the analysis engine NEVER emits hard-coded English
sentences. It only emits a `ReasonCode` (plus optional raw evidence, e.g.
the exact substring that triggered the match). Turning a code into a
human sentence is entirely the job of `app.i18n.Localizer`, which looks
the code up in a locale file. This keeps analysis logic language-agnostic
and lets new languages be added by dropping in a JSON file -- no code
changes, no redeploys of the scoring logic.
"""

from __future__ import annotations

from enum import Enum


class ReasonCode(str, Enum):
    # --- Language / tone signals -------------------------------------
    URGENCY_LANGUAGE = "URGENCY_LANGUAGE"
    THREAT_OF_ACCOUNT_BLOCK = "THREAT_OF_ACCOUNT_BLOCK"

    # --- Impersonation --------------------------------------------------
    BANK_IMPERSONATION = "BANK_IMPERSONATION"
    GOVT_AUTHORITY_IMPERSONATION = "GOVT_AUTHORITY_IMPERSONATION"
    COURIER_LOGISTICS_IMPERSONATION = "COURIER_LOGISTICS_IMPERSONATION"
    UTILITY_IMPERSONATION = "UTILITY_IMPERSONATION"

    # --- Data / credential harvesting -----------------------------------
    OTP_OR_PIN_REQUEST = "OTP_OR_PIN_REQUEST"
    KYC_UPDATE_SCAM = "KYC_UPDATE_SCAM"

    # --- Link-based signals ----------------------------------------------
    SUSPICIOUS_SHORTENED_LINK = "SUSPICIOUS_SHORTENED_LINK"
    SUSPICIOUS_IP_LINK = "SUSPICIOUS_IP_LINK"
    SUSPICIOUS_DOMAIN_MISMATCH = "SUSPICIOUS_DOMAIN_MISMATCH"

    # --- Financial-gain / social-engineering scams -----------------------
    LOTTERY_OR_PRIZE_SCAM = "LOTTERY_OR_PRIZE_SCAM"
    JOB_OR_WORK_FROM_HOME_SCAM = "JOB_OR_WORK_FROM_HOME_SCAM"
    LOAN_OR_CREDIT_SCAM = "LOAN_OR_CREDIT_SCAM"
    INSURANCE_POLICY_SCAM = "INSURANCE_POLICY_SCAM"
    FAMILY_EMERGENCY_MONEY_REQUEST = "FAMILY_EMERGENCY_MONEY_REQUEST"
    REQUEST_FOR_PAYMENT_OR_UPI = "REQUEST_FOR_PAYMENT_OR_UPI"

    # --- Distribution pattern --------------------------------------------
    UNKNOWN_SENDER_MASS_MESSAGE = "UNKNOWN_SENDER_MASS_MESSAGE"

    # --- Positive / neutral -----------------------------------------------
    NO_RISK_INDICATORS = "NO_RISK_INDICATORS"

    # --- AI-only (only ever produced by the Gemini enhancement layer) ----
    AI_SEMANTIC_SCAM_PATTERN = "AI_SEMANTIC_SCAM_PATTERN"


class RiskLevel(str, Enum):
    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Base severity contribution of each reason code to the 0-100 risk score.
# Tuned so that a single weak signal stays LOW, and two-to-three strong
# signals firing together push into HIGH/CRITICAL. See scorer.py for how
# these combine (including the combo-bonus for classic scam "stacks").
REASON_WEIGHTS: dict[ReasonCode, int] = {
    ReasonCode.URGENCY_LANGUAGE: 12,
    ReasonCode.THREAT_OF_ACCOUNT_BLOCK: 18,
    ReasonCode.BANK_IMPERSONATION: 22,
    ReasonCode.GOVT_AUTHORITY_IMPERSONATION: 24,
    ReasonCode.COURIER_LOGISTICS_IMPERSONATION: 16,
    ReasonCode.UTILITY_IMPERSONATION: 16,
    ReasonCode.OTP_OR_PIN_REQUEST: 30,
    ReasonCode.KYC_UPDATE_SCAM: 20,
    ReasonCode.SUSPICIOUS_SHORTENED_LINK: 18,
    ReasonCode.SUSPICIOUS_IP_LINK: 22,
    ReasonCode.SUSPICIOUS_DOMAIN_MISMATCH: 20,
    ReasonCode.LOTTERY_OR_PRIZE_SCAM: 22,
    ReasonCode.JOB_OR_WORK_FROM_HOME_SCAM: 18,
    ReasonCode.LOAN_OR_CREDIT_SCAM: 16,
    ReasonCode.INSURANCE_POLICY_SCAM: 14,
    ReasonCode.FAMILY_EMERGENCY_MONEY_REQUEST: 20,
    ReasonCode.REQUEST_FOR_PAYMENT_OR_UPI: 18,
    ReasonCode.UNKNOWN_SENDER_MASS_MESSAGE: 8,
    ReasonCode.NO_RISK_INDICATORS: 0,
    ReasonCode.AI_SEMANTIC_SCAM_PATTERN: 20,
}

# Reason codes that, when they co-occur, represent a "classic scam stack"
# (e.g. urgency + impersonation + a link asking for action). Any pair
# drawn from two different groups below triggers a combo bonus in the
# scorer, because the combination is far more dangerous than either
# signal alone.
COMBO_GROUPS: list[set[ReasonCode]] = [
    {ReasonCode.URGENCY_LANGUAGE, ReasonCode.THREAT_OF_ACCOUNT_BLOCK},
    {
        ReasonCode.BANK_IMPERSONATION,
        ReasonCode.GOVT_AUTHORITY_IMPERSONATION,
        ReasonCode.COURIER_LOGISTICS_IMPERSONATION,
        ReasonCode.UTILITY_IMPERSONATION,
        ReasonCode.KYC_UPDATE_SCAM,
    },
    {
        ReasonCode.OTP_OR_PIN_REQUEST,
        ReasonCode.REQUEST_FOR_PAYMENT_OR_UPI,
        ReasonCode.SUSPICIOUS_SHORTENED_LINK,
        ReasonCode.SUSPICIOUS_IP_LINK,
        ReasonCode.SUSPICIOUS_DOMAIN_MISMATCH,
    },
]
COMBO_BONUS = 15

RISK_THRESHOLDS: list[tuple[int, RiskLevel]] = [
    (10, RiskLevel.SAFE),
    (30, RiskLevel.LOW),
    (55, RiskLevel.MEDIUM),
    (80, RiskLevel.HIGH),
    (101, RiskLevel.CRITICAL),
]


def level_for_score(score: int) -> RiskLevel:
    for ceiling, level in RISK_THRESHOLDS:
        if score < ceiling:
            return level
    return RiskLevel.CRITICAL
