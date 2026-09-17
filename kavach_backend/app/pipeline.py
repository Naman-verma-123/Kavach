"""
Orchestrates one end-to-end analysis:

    extractor (offline, always runs)
        -> [optional] gemini_client (best-effort, never required)
        -> scorer
        -> i18n.Localizer

`analyze()` is the single function the API layer calls. It is
constructed so that removing network access or the Gemini API key
entirely still produces a complete, correctly-scored, correctly-worded
result -- that guarantee is exercised directly in
tests/test_pipeline.py::test_offline_fallback_when_ai_disabled.
"""

from __future__ import annotations

from app import gemini_client
from app.extractor import extract_signals
from app.i18n import Localizer
from app.models import AnalysisRequest, AnalysisResponse, ReasonDetail
from app.reason_codes import REASON_WEIGHTS, ReasonCode
from app.scorer import score_codes


class AnalysisPipeline:
    def __init__(self, localizer: Localizer | None = None, use_ai: bool = True):
        self.localizer = localizer or Localizer()
        # use_ai is a soft switch: even if True, gemini_client.classify()
        # independently no-ops when no API key is configured, so the
        # offline guarantee holds regardless of this flag's value.
        self.use_ai = use_ai

    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        offline_signals = extract_signals(request.message, request.sender)
        offline_codes = {s.code for s in offline_signals}
        evidence_by_code = {s.code: s.evidence for s in offline_signals if s.evidence}

        ai_codes: set[ReasonCode] = set()
        source = "offline"
        if self.use_ai:
            ai_result = gemini_client.classify(request.message)
            if ai_result:
                ai_codes = ai_result.codes
                source = "ai_enhanced"

        all_codes = (offline_codes | ai_codes) - {ReasonCode.NO_RISK_INDICATORS}
        if not all_codes:
            all_codes = {ReasonCode.NO_RISK_INDICATORS}

        result = score_codes(all_codes)

        ordered_codes = sorted(
            all_codes,
            key=lambda c: REASON_WEIGHTS.get(c, 0),
            reverse=True,
        )
        reasons = [
            ReasonDetail(
                code=code.value,
                message=self.localizer.reason_text(code, request.locale),
                evidence=evidence_by_code.get(code),
            )
            for code in ordered_codes
        ]

        return AnalysisResponse(
            channel=request.channel,
            locale=request.locale,
            risk_level=result.level.value,
            risk_label=self.localizer.level_label(result.level, request.locale),
            score=result.score,
            reasons=reasons,
            recommendation=self.localizer.recommendation(result.level, request.locale),
            analysis_source=source,
        )
