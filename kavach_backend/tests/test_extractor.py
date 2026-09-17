from app.extractor import extract_signals
from app.reason_codes import ReasonCode


def codes(message, sender=None):
    return {s.code for s in extract_signals(message, sender)}


def test_classic_kyc_bank_scam_triggers_multiple_signals():
    msg = "Dear customer, your SBI account will be blocked. Update your KYC now: http://bit.ly/sbi-kyc"
    found = codes(msg, sender="VM-SBIBNK")
    assert ReasonCode.THREAT_OF_ACCOUNT_BLOCK in found
    assert ReasonCode.BANK_IMPERSONATION in found
    assert ReasonCode.KYC_UPDATE_SCAM in found
    assert ReasonCode.SUSPICIOUS_SHORTENED_LINK in found


def test_hindi_otp_request_is_detected():
    msg = "आपका बैंक खाता बंद हो जाएगा। कृपया ओटीपी शेयर करें।"
    found = codes(msg)
    assert ReasonCode.THREAT_OF_ACCOUNT_BLOCK in found
    assert ReasonCode.OTP_OR_PIN_REQUEST in found


def test_safe_message_returns_no_risk_indicators():
    msg = "Hi beta, are you free for lunch on Sunday?"
    found = codes(msg)
    assert found == {ReasonCode.NO_RISK_INDICATORS}


def test_empty_message_returns_no_risk_indicators():
    assert codes("") == {ReasonCode.NO_RISK_INDICATORS}
    assert codes("   ") == {ReasonCode.NO_RISK_INDICATORS}


def test_ip_address_link_detected():
    msg = "Verify here http://192.168.10.5/verify to avoid suspension"
    assert ReasonCode.SUSPICIOUS_IP_LINK in codes(msg)


def test_domain_mismatch_when_brand_named_but_link_is_foreign():
    msg = "SBI KYC pending, click https://sbi-kyc-verify.xyz/login to update immediately"
    found = codes(msg)
    assert ReasonCode.SUSPICIOUS_DOMAIN_MISMATCH in found


def test_no_mismatch_when_link_is_actually_official():
    msg = "Your SBI statement is ready at https://www.onlinesbi.sbi/statements"
    found = codes(msg)
    assert ReasonCode.SUSPICIOUS_DOMAIN_MISMATCH not in found


def test_lottery_scam_detected():
    msg = "Congratulations! You have won a lucky draw cash prize of Rs 50,00,000!"
    assert ReasonCode.LOTTERY_OR_PRIZE_SCAM in codes(msg)


def test_family_emergency_scam_detected():
    msg = "Hi papa, this is my new number, I lost my wallet, please send money urgently"
    assert ReasonCode.FAMILY_EMERGENCY_MONEY_REQUEST in codes(msg)


def test_normal_10_digit_sender_is_not_flagged_as_mass_message():
    msg = "Hi beta, are you free for lunch on Sunday?"
    found = codes(msg, sender="9876543210")
    assert ReasonCode.UNKNOWN_SENDER_MASS_MESSAGE not in found


def test_short_bulk_sender_id_is_flagged():
    msg = "Hi beta, are you free for lunch on Sunday?"
    found = codes(msg, sender="VM-ALERTS")
    assert ReasonCode.UNKNOWN_SENDER_MASS_MESSAGE in found
