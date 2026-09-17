import os

from fastapi.testclient import TestClient

os.environ.setdefault("KAVACH_ENABLE_GEMINI", "false")

from app.main import app  # noqa: E402  (env var must be set before import)

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "en" in body["available_locales"]


def test_reason_codes_endpoint_lists_codes():
    resp = client.get("/reason-codes")
    assert resp.status_code == 200
    assert "URGENCY_LANGUAGE" in resp.json()["codes"]


def test_analyze_sms_high_risk():
    payload = {
        "channel": "sms",
        "sender": "VM-SBIBNK",
        "message": "Your SBI account will be blocked. Update KYC now: http://bit.ly/kyc. Share OTP.",
        "locale": "hi",
    }
    resp = client.post("/analyze/sms", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk_level"] in ("HIGH", "CRITICAL")
    assert body["analysis_source"] == "offline"
    assert body["locale"] == "hi"
    assert len(body["reasons"]) > 0


def test_analyze_whatsapp_safe_message():
    payload = {
        "channel": "whatsapp",
        "message": "Hi beta, are you free for lunch on Sunday?",
        "locale": "en",
    }
    resp = client.post("/analyze/whatsapp", json=payload)
    assert resp.status_code == 200
    assert resp.json()["risk_level"] == "SAFE"


def test_channel_mismatch_is_rejected():
    payload = {"channel": "whatsapp", "message": "hello"}
    resp = client.post("/analyze/sms", json=payload)
    assert resp.status_code == 400
