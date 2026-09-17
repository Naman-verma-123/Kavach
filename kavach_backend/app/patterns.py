"""
Keyword and regex pattern banks for the offline rule-based extractor.

Every list mixes English, Hindi (Devanagari) and common Romanized-Hindi
("Hinglish") phrasing, because senior citizens in India receive scam
SMS/WhatsApp text in all three registers. Matching is substring-based on
a normalized (lower-cased, whitespace-collapsed) copy of the message, so
Devanagari terms are matched on the original text and Latin-script terms
on the lower-cased text.

This file intentionally holds ONLY detection data, not scoring or output
text -- keeping "what looks suspicious" separate from "how risky is it"
(scorer.py) and "how do we say it" (locales/*.json).
"""

from __future__ import annotations

import re

from app.reason_codes import ReasonCode

# ---------------------------------------------------------------------------
# URL handling
# ---------------------------------------------------------------------------

URL_REGEX = re.compile(r"(https?://[^\s]+|www\.[^\s]+)", re.IGNORECASE)

IP_HOST_REGEX = re.compile(
    r"https?://(\d{1,3}\.){3}\d{1,3}(:\d+)?(/|$)", re.IGNORECASE
)

KNOWN_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "cutt.ly", "rebrand.ly", "is.gd",
    "shorturl.at", "tiny.cc", "rb.gy", "bitly.com", "ow.ly", "buff.ly",
    "shorte.st", "soo.gd", "clck.ru", "lnkd.in",
}

# Domains that are the genuine, official domains for common entities
# referenced in Indian scam SMS. If a message *mentions* one of these
# brands/authorities by name but the URL in the message does NOT contain
# any of its allow-listed domains, that's a strong mismatch signal.
BRAND_TO_OFFICIAL_DOMAINS = {
    "sbi": {"sbi.co.in", "onlinesbi.sbi", "sbibank.co.in"},
    "state bank": {"sbi.co.in", "onlinesbi.sbi"},
    "icici": {"icicibank.com"},
    "hdfc": {"hdfcbank.com"},
    "axis": {"axisbank.com"},
    "pnb": {"pnbindia.in", "netpnb.com"},
    "kotak": {"kotak.com"},
    "post office": {"indiapost.gov.in"},
    "india post": {"indiapost.gov.in"},
    "income tax": {"incometax.gov.in"},
    "uidai": {"uidai.gov.in"},
    "aadhaar": {"uidai.gov.in"},
    "epfo": {"epfindia.gov.in"},
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


# ---------------------------------------------------------------------------
# Keyword banks: ReasonCode -> list of (pattern, is_lowercase_keyword)
# All Latin-script keywords are stored lowercase and matched against the
# lower-cased text. Devanagari keywords are matched against the raw text.
# ---------------------------------------------------------------------------

KEYWORD_BANKS: dict[ReasonCode, list[str]] = {
    ReasonCode.URGENCY_LANGUAGE: [
        "urgent", "immediately", "act now", "within 24 hours",
        "within 2 hours", "last warning", "final notice", "expire today",
        "right now", "hurry", "time is running out",
        "turant", "abhi karein", "jaldi karein", "aakhri chance",
        "तुरंत", "अभी करें", "जल्दी करें", "आखिरी मौका", "आखिरी चेतावनी",
    ],
    ReasonCode.THREAT_OF_ACCOUNT_BLOCK: [
        "account will be blocked", "account has been blocked",
        "account suspended", "will be deactivated", "card will be blocked",
        "sim will be blocked", "number will be blocked", "will be closed",
        "khaata band", "account band ho jayega", "sim band",
        "खाता बंद", "खाता ब्लॉक", "बंद हो जाएगा", "सिम बंद",
    ],
    ReasonCode.BANK_IMPERSONATION: [
        "bank account", "kyc update", "debit card", "credit card blocked",
        "net banking", "sbi", "icici", "hdfc", "axis bank", "pnb",
        "kotak mahindra", "rbi", "bank customer care",
        "बैंक खाता", "बैंक", "एसबीआई", "आईसीआईसीआई", "एचडीएफसी",
        "केवाईसी",
    ],
    ReasonCode.GOVT_AUTHORITY_IMPERSONATION: [
        "income tax department", "digital arrest", "cbi", "customs department",
        "trai", "narcotics department", "police verification", "court notice",
        "aadhaar suspended", "uidai", "epfo", "your parcel contains illegal",
        "cyber crime cell", "arrest warrant",
        "डिजिटल अरेस्ट", "आधार सस्पेंड", "साइबर क्राइम", "गिरफ्तारी वारंट",
        "कस्टम विभाग", "आयकर विभाग",
    ],
    ReasonCode.COURIER_LOGISTICS_IMPERSONATION: [
        "your parcel", "your courier", "fedex", "bluedart", "delhivery",
        "package is held", "customs clearance fee", "delivery failed",
        "shipment on hold", "parcel is stuck",
        "आपका पार्सल", "कोरियर", "डिलीवरी फेल",
    ],
    ReasonCode.UTILITY_IMPERSONATION: [
        "electricity bill", "power will be disconnected",
        "electricity connection will be cut", "gas connection",
        "बिजली बिल", "बिजली कनेक्शन काट दिया जाएगा", "बिजली कट",
    ],
    ReasonCode.OTP_OR_PIN_REQUEST: [
        "share the otp", "share your otp", "otp is", "tell me the otp",
        "send otp", "share your pin", "upi pin", "atm pin", "cvv number",
        "share the cvv", "one time password",
        "ओटीपी शेयर करें", "ओटीपी बताएं", "यूपीआई पिन", "एटीएम पिन",
    ],
    ReasonCode.KYC_UPDATE_SCAM: [
        "kyc update", "update your kyc", "kyc verification pending",
        "kyc will expire", "complete your kyc", "re-kyc",
        "केवाईसी अपडेट करें", "केवाईसी पेंडिंग",
    ],
    ReasonCode.LOTTERY_OR_PRIZE_SCAM: [
        "you have won", "lucky draw", "lottery winner", "claim your prize",
        "cash prize", "kbc lottery", "you are selected for a gift",
        "congratulations you have been selected",
        "आपने जीता", "लॉटरी", "लकी ड्रा", "इनाम जीता",
    ],
    ReasonCode.JOB_OR_WORK_FROM_HOME_SCAM: [
        "work from home", "earn daily", "part time job offer",
        "data entry job", "earn per day", "join telegram for job",
        "no investment job", "earn rs", "daily payment job",
        "घर बैठे कमाएं", "पार्ट टाइम जॉब",
    ],
    ReasonCode.LOAN_OR_CREDIT_SCAM: [
        "instant loan approved", "loan pre-approved", "get instant loan",
        "loan without documents", "credit limit increased instantly",
        "लोन मंजूर", "इंस्टेंट लोन",
    ],
    ReasonCode.INSURANCE_POLICY_SCAM: [
        "policy maturity", "insurance bonus pending", "lic policy",
        "policy will lapse", "insurance refund",
        "पॉलिसी मैच्योरिटी", "बीमा बोनस",
    ],
    ReasonCode.FAMILY_EMERGENCY_MONEY_REQUEST: [
        "i am in hospital", "send money urgently", "i lost my wallet",
        "stuck at airport", "need money right now", "this is my new number",
        "i am in trouble send money", "mera number change ho gaya",
        "अस्पताल में हूं", "पैसे भेज दो", "नंबर बदल गया",
    ],
    ReasonCode.REQUEST_FOR_PAYMENT_OR_UPI: [
        "pay via upi", "scan this qr", "send payment to this upi id",
        "pay processing fee", "pay a small fee to unlock",
        "यूपीआई पर पेमेंट करें", "क्यूआर कोड स्कैन करें",
    ],
}
