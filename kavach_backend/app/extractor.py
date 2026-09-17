"""
Offline, dependency-free signal extraction.

This is the layer that MUST always work -- no network call, no API key,
no external service. It is pure text/regex analysis in Python's standard
library plus the pattern banks in patterns.py. Gemini (pipeline.py) can
optionally *add* signals on top of this, but this module alone is the
guaranteed offline fallback the app promises.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.patterns import (
    BRAND_TO_OFFICIAL_DOMAINS,
    IP_HOST_REGEX,
    KEYWORD_BANKS,
    KNOWN_SHORTENERS,
    URL_REGEX,
    normalize,
)
from app.reason_codes import ReasonCode


@dataclass(frozen=True)
class Signal:
    code: ReasonCode
    evidence: str  # short raw snippet that triggered the match (for debugging/UI, not for display copy)


def _match_keyword_banks(normalized_text: str, raw_text: str) -> list[Signal]:
    lowered = normalized_text.lower()
    signals: list[Signal] = []
    for code, keywords in KEYWORD_BANKS.items():
        for kw in keywords:
            haystack = raw_text if _is_devanagari(kw) else lowered
            if kw in haystack:
                signals.append(Signal(code=code, evidence=kw))
                break  # one hit per reason code is enough signal-wise
    return signals


def _is_devanagari(s: str) -> bool:
    return any("\u0900" <= ch <= "\u097F" for ch in s)


def _extract_link_signals(raw_text: str) -> list[Signal]:
    signals: list[Signal] = []
    urls = URL_REGEX.findall(raw_text)
    if not urls:
        return signals

    lowered = raw_text.lower()

    for url in urls:
        candidate = url if url.startswith("http") else f"http://{url}"
        try:
            parsed = urlparse(candidate)
            host = (parsed.netloc or "").lower()
        except ValueError:
            host = ""

        if IP_HOST_REGEX.match(candidate):
            signals.append(Signal(code=ReasonCode.SUSPICIOUS_IP_LINK, evidence=url))

        if any(host == s or host.endswith("." + s) for s in KNOWN_SHORTENERS):
            signals.append(Signal(code=ReasonCode.SUSPICIOUS_SHORTENED_LINK, evidence=url))

        for brand, official_domains in BRAND_TO_OFFICIAL_DOMAINS.items():
            if brand in lowered:
                is_official = any(
                    host == d or host.endswith("." + d) for d in official_domains
                )
                if not is_official:
                    signals.append(
                        Signal(code=ReasonCode.SUSPICIOUS_DOMAIN_MISMATCH, evidence=url)
                    )
                break

    return signals


def _extract_mass_sender_signal(sender: str | None) -> list[Signal]:
    """A short alphanumeric sender ID (e.g. 'VM-SBIBNK', 'AX-KYCUPD') that
    doesn't look like a normal 10-digit mobile number is common for bulk
    SMS gateways -- legitimate AND fraudulent alike, so this is a weak,
    low-weight signal only ever used to nudge the score, never alone."""
    if not sender:
        return []
    cleaned = sender.strip()
    looks_like_phone = cleaned.isdigit() and len(cleaned) >= 10
    if not looks_like_phone and len(cleaned) <= 16:
        return [Signal(code=ReasonCode.UNKNOWN_SENDER_MASS_MESSAGE, evidence=cleaned)]
    return []


def extract_signals(message: str, sender: str | None = None) -> list[Signal]:
    """Return every offline signal found in `message` (and optionally the
    SMS `sender` ID). Guaranteed to return a non-empty list -- if nothing
    else fires, NO_RISK_INDICATORS is returned so downstream code never
    has to special-case "empty"."""
    if not message or not message.strip():
        return [Signal(code=ReasonCode.NO_RISK_INDICATORS, evidence="")]

    raw_text = message
    normalized_text = normalize(message)

    signals: list[Signal] = []
    signals.extend(_match_keyword_banks(normalized_text, raw_text))
    signals.extend(_extract_link_signals(raw_text))
    signals.extend(_extract_mass_sender_signal(sender))

    if not signals:
        signals.append(Signal(code=ReasonCode.NO_RISK_INDICATORS, evidence=""))

    return signals
