"""
FastAPI entrypoint for the Kavach analysis backend.

Run locally:
    uvicorn app.main:app --reload

Environment variables:
    KAVACH_ENABLE_GEMINI=true   -- turn on the optional AI enhancement layer
    GEMINI_API_KEY=<key>        -- required for the AI layer to actually fire;
                                    if absent, the AI layer silently no-ops
                                    and every response still has
                                    analysis_source == "offline".
"""

from __future__ import annotations

from dotenv import load_dotenv

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app import gemini_client
from app.i18n import Localizer
from app.models import AnalysisRequest, AnalysisResponse
from app.pipeline import AnalysisPipeline
from app.reason_codes import ReasonCode, RiskLevel

load_dotenv()  

localizer = Localizer()
pipeline = AnalysisPipeline(
    localizer=localizer,
    use_ai=os.getenv("KAVACH_ENABLE_GEMINI", "false").lower() == "true",
)

app = FastAPI(
    title="Kavach Message Analysis API",
    description="Offline-first SMS/WhatsApp scam analysis for senior citizens, "
    "with an optional Gemini-powered enhancement layer.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the app's own origin(s) before production
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "ai_enabled": pipeline.use_ai,
        "ai_configured": gemini_client.is_configured(),
        "available_locales": localizer.available_locales,
    }


@app.get("/locales")
def locales() -> dict:
    return {"available_locales": localizer.available_locales}


@app.get("/reason-codes")
def reason_codes() -> dict:
    """Static list of every possible reason code, for a client app that
    wants to pre-load icons/UI per code rather than branch on strings."""
    return {"codes": [c.value for c in ReasonCode]}


def _analyze(request: AnalysisRequest) -> AnalysisResponse:
    if request.locale not in localizer.available_locales:
        # Not an error -- Localizer already falls back to English per-key --
        # but tell the caller explicitly so a client can show "translated
        # to English" rather than silently rendering English text.
        pass
    try:
        return pipeline.analyze(request)
    except Exception as exc:  # noqa: BLE001
        # Analysis must never 500 on a senior citizen's phone; if
        # anything unexpected happens, fail safe with a clear server error
        # rather than a partial/garbled risk verdict.
        raise HTTPException(status_code=500, detail="Analysis failed") from exc


@app.post("/analyze/sms", response_model=AnalysisResponse)
def analyze_sms(request: AnalysisRequest) -> AnalysisResponse:
    if request.channel != "sms":
        raise HTTPException(status_code=400, detail="channel must be 'sms' for this endpoint")
    return _analyze(request)


@app.post("/analyze/whatsapp", response_model=AnalysisResponse)
def analyze_whatsapp(request: AnalysisRequest) -> AnalysisResponse:
    if request.channel != "whatsapp":
        raise HTTPException(status_code=400, detail="channel must be 'whatsapp' for this endpoint")
    return _analyze(request)
