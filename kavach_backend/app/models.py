from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    channel: Literal["sms", "whatsapp"]
    message: str = Field(..., min_length=1, max_length=4000)
    sender: Optional[str] = Field(
        default=None,
        description="SMS sender ID / phone number. Ignored for WhatsApp paste-in checks.",
    )
    locale: str = Field(
        default="en",
        description="BCP-47-ish locale code, e.g. 'en', 'hi', 'bn', 'ta'. "
        "Falls back to English for any key missing in the requested locale.",
    )


class ReasonDetail(BaseModel):
    code: str
    message: str
    evidence: Optional[str] = None


class AnalysisResponse(BaseModel):
    channel: Literal["sms", "whatsapp"]
    locale: str
    risk_level: str
    risk_label: str
    score: int
    reasons: list[ReasonDetail]
    recommendation: str
    analysis_source: Literal["offline", "ai_enhanced"]
