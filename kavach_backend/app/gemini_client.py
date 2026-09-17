"""
Optional AI enhancement layer using the Gemini API.

Hard rules this module must satisfy:
1. It is ALWAYS optional. If disabled, unconfigured, unreachable, slow,
   or it returns garbage, the rest of the system must keep working
   exactly as if this module didn't exist (see pipeline.py).
2. It NEVER becomes the source of user-facing text. Gemini is asked to
   return *only* reason codes drawn from our closed vocabulary
   (ReasonCode), never free-form sentences. This keeps "explain the
   risk" fully controlled by app/locales/*.json and fully translatable,
   and stops a prompt-injected SMS from putting arbitrary text in front
   of a senior citizen.
3. It fails fast and quietly: short timeout, one retry at most, broad
   exception handling, structured logging instead of raising.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

from app.reason_codes import ReasonCode

logger = logging.getLogger("kavach.gemini")

GEMINI_MODEL = os.getenv("KAVACH_GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
REQUEST_TIMEOUT_SECONDS = 4.0

# Only these codes may ever be returned by the AI layer. Anything else
# in the model's response is discarded during validation.
_AI_ALLOWED_CODES = {c.value for c in ReasonCode} - {
    ReasonCode.NO_RISK_INDICATORS.value,
}

_SYSTEM_INSTRUCTION = (
    "You are a scam-message classifier for Indian senior citizens. "
    "Given an SMS or WhatsApp message, respond with ONLY a compact JSON "
    "object of the shape {\"codes\": [\"CODE_A\", \"CODE_B\"]} using codes "
    "from this exact allowed list, with no extra text, no explanation, "
    "and no markdown fences: " + ", ".join(sorted(_AI_ALLOWED_CODES))
)


@dataclass(frozen=True)
class AiResult:
    codes: set[ReasonCode]
    raw_model: str


def is_configured() -> bool:
    return bool(os.getenv(GEMINI_API_KEY_ENV))


def classify(message: str) -> AiResult | None:
    """Ask Gemini for extra reason codes it can infer from the message's
    meaning (things a keyword list can't catch, e.g. a cleverly-worded
    scam with no trigger words). Returns None on ANY failure -- caller
    must treat None exactly like "AI unavailable" and continue with the
    offline result alone."""
    if not is_configured():
        return None

    try:
        return _call_gemini(message)
    except Exception as exc:  # noqa: BLE001 - intentionally broad: never let AI break the request
        logger.warning("Gemini classification failed, falling back to offline only: %s", exc)
        return None


def _call_gemini(message: str) -> AiResult | None:
    # Imported lazily so the dependency is only required when Gemini is
    # actually enabled -- keeps the offline path free of extra installs.
    import httpx

    api_key = os.environ[GEMINI_API_KEY_ENV]
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={api_key}"
    )
    payload = {
        "system_instruction": {"parts": [{"text": _SYSTEM_INSTRUCTION}]},
        "contents": [{"parts": [{"text": message}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
        },
    }

    with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    text = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "")
    )
    if not text:
        return None

    parsed = json.loads(text)
    raw_codes = parsed.get("codes", [])
    if not isinstance(raw_codes, list):
        return None

    valid_codes = {
        ReasonCode(code) for code in raw_codes if code in _AI_ALLOWED_CODES
    }
    if not valid_codes:
        return None

    # Tag every AI-only finding with AI_SEMANTIC_SCAM_PATTERN so the UI
    # can show "our AI also noticed..." even when the specific code it
    # returned already has its own offline reason text.
    valid_codes.add(ReasonCode.AI_SEMANTIC_SCAM_PATTERN)
    return AiResult(codes=valid_codes, raw_model=GEMINI_MODEL)
