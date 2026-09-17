"""
Turns a deduplicated set of ReasonCodes into a numeric score (0-100) and
a RiskLevel. Pure function, no I/O, so it's trivially unit-testable and
always available offline.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.reason_codes import (
    COMBO_BONUS,
    COMBO_GROUPS,
    REASON_WEIGHTS,
    ReasonCode,
    RiskLevel,
    level_for_score,
)


@dataclass(frozen=True)
class ScoreResult:
    score: int
    level: RiskLevel
    combo_bonus_applied: bool


def _groups_touched(codes: set[ReasonCode]) -> int:
    return sum(1 for group in COMBO_GROUPS if codes & group)


def score_codes(codes: set[ReasonCode]) -> ScoreResult:
    if not codes or codes == {ReasonCode.NO_RISK_INDICATORS}:
        return ScoreResult(score=0, level=RiskLevel.SAFE, combo_bonus_applied=False)

    codes = {c for c in codes if c != ReasonCode.NO_RISK_INDICATORS}

    base = sum(REASON_WEIGHTS.get(code, 0) for code in codes)

    # Classic scam messages combine several *kinds* of signal (urgency +
    # impersonation + an action-forcing link/OTP ask). Reward that
    # combination explicitly rather than relying on weights alone,
    # because three weak-ish signals stacked together are much more
    # dangerous than the same score from one very loud signal.
    combo_applied = _groups_touched(codes) >= 2
    total = base + (COMBO_BONUS if combo_applied else 0)
    total = max(0, min(100, total))

    return ScoreResult(
        score=total,
        level=level_for_score(total),
        combo_bonus_applied=combo_applied,
    )
