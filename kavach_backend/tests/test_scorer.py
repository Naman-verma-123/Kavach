from app.reason_codes import ReasonCode, RiskLevel
from app.scorer import score_codes


def test_no_risk_indicators_scores_zero_and_safe():
    result = score_codes({ReasonCode.NO_RISK_INDICATORS})
    assert result.score == 0
    assert result.level == RiskLevel.SAFE


def test_single_weak_signal_stays_low():
    result = score_codes({ReasonCode.UNKNOWN_SENDER_MASS_MESSAGE})
    assert result.level in (RiskLevel.SAFE, RiskLevel.LOW)


def test_classic_scam_stack_reaches_high_or_critical():
    result = score_codes(
        {
            ReasonCode.URGENCY_LANGUAGE,
            ReasonCode.THREAT_OF_ACCOUNT_BLOCK,
            ReasonCode.BANK_IMPERSONATION,
            ReasonCode.KYC_UPDATE_SCAM,
            ReasonCode.OTP_OR_PIN_REQUEST,
            ReasonCode.SUSPICIOUS_SHORTENED_LINK,
        }
    )
    assert result.level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    assert result.combo_bonus_applied is True


def test_score_never_exceeds_100():
    everything = {c for c in ReasonCode if c != ReasonCode.NO_RISK_INDICATORS}
    result = score_codes(everything)
    assert 0 <= result.score <= 100


def test_empty_set_is_safe():
    result = score_codes(set())
    assert result.score == 0
    assert result.level == RiskLevel.SAFE
