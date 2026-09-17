import os

import pytest

from app.i18n import Localizer
from app.models import AnalysisRequest
from app.pipeline import AnalysisPipeline

SCAM_SMS = (
    "Dear customer, your SBI account will be blocked. Update your KYC now: "
    "http://bit.ly/sbi-kyc-update. Share OTP to verify immediately."
)
SAFE_SMS = "Hi beta, are you free for lunch on Sunday?"


@pytest.fixture()
def pipeline():
    return AnalysisPipeline(localizer=Localizer(), use_ai=True)


def test_offline_fallback_when_ai_disabled(monkeypatch, pipeline):
    """The core guarantee: with no GEMINI_API_KEY set, use_ai=True must
    still produce a complete, correctly-scored result purely from the
    offline extractor -- analysis_source must say 'offline'."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    request = AnalysisRequest(channel="sms", message=SCAM_SMS, sender="VM-SBIBNK", locale="en")
    result = pipeline.analyze(request)
    assert result.analysis_source == "offline"
    assert result.risk_level in ("HIGH", "CRITICAL")
    assert result.score > 0
    assert len(result.reasons) > 0


def test_offline_fallback_survives_gemini_network_failure(monkeypatch, pipeline):
    """Even with an API key configured, if the Gemini call itself raises,
    the pipeline must still return a complete offline result instead of
    propagating the error to the caller."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")

    from app import gemini_client

    def boom(_message):
        raise RuntimeError("simulated network failure")

    monkeypatch.setattr(gemini_client, "_call_gemini", boom)

    request = AnalysisRequest(channel="sms", message=SCAM_SMS, locale="en")
    result = pipeline.analyze(request)
    assert result.analysis_source == "offline"
    assert result.score > 0


def test_safe_message_is_low_score_and_gives_a_recommendation(pipeline):
    request = AnalysisRequest(channel="whatsapp", message=SAFE_SMS, locale="en")
    result = pipeline.analyze(request)
    assert result.risk_level == "SAFE"
    assert result.recommendation  # never empty


def test_reason_text_is_never_the_raw_code(pipeline):
    request = AnalysisRequest(channel="sms", message=SCAM_SMS, locale="en")
    result = pipeline.analyze(request)
    for reason in result.reasons:
        assert reason.message != reason.code
        assert len(reason.message) > 5


@pytest.mark.parametrize("locale", ["en", "hi", "bn", "mr", "gu", "ta", "te"])
def test_every_supported_locale_produces_localized_text(pipeline, locale):
    request = AnalysisRequest(channel="sms", message=SCAM_SMS, sender="VM-BANK", locale=locale)
    result = pipeline.analyze(request)
    assert result.locale == locale
    assert result.recommendation
    assert result.risk_label
    for reason in result.reasons:
        assert reason.message


def test_unknown_locale_falls_back_to_english_text(pipeline):
    request = AnalysisRequest(channel="sms", message=SAFE_SMS, locale="xx")
    result = pipeline.analyze(request)
    en_result = pipeline.analyze(AnalysisRequest(channel="sms", message=SAFE_SMS, locale="en"))
    assert result.recommendation == en_result.recommendation
