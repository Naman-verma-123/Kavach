# Kavach — Message Analysis Backend

Offline-first SMS / WhatsApp scam analysis engine for the Kavach senior-
citizen safety app, built to match the architecture in the pitch deck
(`Python • FastAPI` backend, `Rules • Gemini API` scam intelligence).

## Design principles

1. **Offline always works.** The rule-based extractor (`app/extractor.py`)
   and scorer (`app/scorer.py`) use only the Python standard library.
   No network call, API key, or external service is ever required for a
   message to be analyzed and scored correctly. This is enforced by
   `tests/test_pipeline.py::test_offline_fallback_when_ai_disabled` and
   `::test_offline_fallback_survives_gemini_network_failure`.
2. **Reason codes, not sentences.** Detection logic never produces
   English (or any language's) text. It only ever produces a
   `ReasonCode` enum value (`app/reason_codes.py`), e.g.
   `BANK_IMPERSONATION`, `OTP_OR_PIN_REQUEST`. Turning a code into a
   sentence a senior citizen can read is the *only* job of
   `app/i18n.py` + `app/locales/*.json`.
3. **Gemini is a pure add-on.** `app/gemini_client.py` optionally asks
   Gemini to return *additional reason codes* (still from the same
   closed vocabulary — never free text) for scam patterns that don't
   match any keyword/link rule. If it's disabled, misconfigured, slow,
   or errors, the pipeline silently continues with the offline result.
   This also means a malicious SMS can't "prompt-inject" arbitrary text
   onto a user's screen — Gemini's output is validated against the enum
   before it's used for anything.
4. **Multilingual by construction.** Adding a language is "drop in
   `app/locales/<code>.json`" — no code change. Seven languages ship
   today: English, Hindi, Bengali, Marathi, Gujarati, Tamil, Telugu.
   Any locale requested that isn't shipped falls back to English; any
   *key* missing from a shipped locale also falls back to English
   per-key, so a partial translation never shows blank text. (These
   translations are DSA-project-grade — please have a native speaker
   review the copy before shipping to real users.)

## Project layout

```
app/
  reason_codes.py   # ReasonCode enum, RiskLevel enum, severity weights, combo rules
  patterns.py        # keyword/regex pattern banks (EN + Hindi + Hinglish)
  extractor.py        # message -> list[Signal] (offline, stdlib only)
  scorer.py            # set[ReasonCode] -> score (0-100) + RiskLevel
  i18n.py               # ReasonCode/RiskLevel -> localized text
  locales/*.json         # one file per language
  gemini_client.py        # optional AI enhancement, fails safe
  pipeline.py               # orchestrates extractor -> [AI] -> scorer -> i18n
  models.py                  # pydantic request/response schemas
  main.py                      # FastAPI app + routes
tests/                          # pytest suite (offline, no network needed)
```

## Running it

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- `POST /analyze/sms` — body: `{"channel": "sms", "sender": "VM-SBIBNK", "message": "...", "locale": "hi"}`
- `POST /analyze/whatsapp` — body: `{"channel": "whatsapp", "message": "...", "locale": "ta"}`
- `GET /health` — reports whether the AI layer is enabled/configured and which locales are available
- `GET /reason-codes` — the full static list of codes, for a client to pre-map to icons
- `GET /locales` — available locale codes

Example response:

```json
{
  "channel": "sms",
  "locale": "hi",
  "risk_level": "CRITICAL",
  "risk_label": "खतरनाक",
  "score": 88,
  "reasons": [
    {"code": "OTP_OR_PIN_REQUEST", "message": "यह मैसेज आपसे ओटीपी...", "evidence": "share otp"},
    {"code": "BANK_IMPERSONATION", "message": "यह मैसेज आपके बैंक...", "evidence": "sbi"},
    {"code": "SUSPICIOUS_SHORTENED_LINK", "message": "...", "evidence": "http://bit.ly/..."}
  ],
  "recommendation": "यह मैसेज खतरनाक है। क्लिक न करें...",
  "analysis_source": "offline"
}
```

## Turning on the Gemini enhancement layer

```bash
export KAVACH_ENABLE_GEMINI=true
export GEMINI_API_KEY=your-key-here
```

Without `GEMINI_API_KEY` set, `KAVACH_ENABLE_GEMINI=true` is a no-op —
`gemini_client.is_configured()` returns `False` and every response still
reports `"analysis_source": "offline"`.

## Tests

```bash
pytest -q
```

All tests run fully offline (the Gemini-path tests monkeypatch the
network call to simulate both "no key" and "key present but the call
fails").

## Extending

- **New scam pattern:** add a `ReasonCode`, a weight in `REASON_WEIGHTS`,
  keywords in `patterns.py`, and one line per locale file. Nothing else
  changes.
- **New language:** copy `app/locales/en.json`, translate every value
  (keys must stay identical), save as `app/locales/<code>.json`. It's
  picked up automatically — no restart-time config needed beyond the
  process restart itself.
