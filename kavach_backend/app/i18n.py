"""
Turns ReasonCode / RiskLevel into human-readable text, in whichever
language the client asked for. This is the ONLY place in the codebase
that is allowed to contain user-facing sentences -- detection and
scoring never do.

Adding a new language = dropping a new locales/<code>.json file with the
same three top-level keys ("reasons", "recommendations", "levels"). No
Python changes required. Any key missing from a locale silently falls
back to English, so a partially-translated locale still degrades
gracefully instead of crashing or showing blank text.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.reason_codes import ReasonCode, RiskLevel

LOCALES_DIR = Path(__file__).parent / "locales"
DEFAULT_LOCALE = "en"


class Localizer:
    def __init__(self, locales_dir: Path = LOCALES_DIR):
        self._locales_dir = locales_dir
        self._cache: dict[str, dict] = {}
        self.available_locales: list[str] = sorted(
            p.stem for p in locales_dir.glob("*.json")
        )
        # Fail fast if the mandatory English fallback file is missing --
        # everything else in this class assumes it exists.
        if DEFAULT_LOCALE not in self.available_locales:
            raise RuntimeError(
                f"Missing mandatory fallback locale file: "
                f"{locales_dir / (DEFAULT_LOCALE + '.json')}"
            )

    def _load(self, locale: str) -> dict:
        if locale not in self._cache:
            path = self._locales_dir / f"{locale}.json"
            if not path.exists():
                self._cache[locale] = {}
            else:
                self._cache[locale] = json.loads(path.read_text(encoding="utf-8"))
        return self._cache[locale]

    def _resolve_locale(self, locale: str) -> str:
        locale = (locale or DEFAULT_LOCALE).lower().split("-")[0]
        return locale if locale in self.available_locales else DEFAULT_LOCALE

    def _lookup(self, locale: str, section: str, key: str) -> str:
        requested = self._resolve_locale(locale)
        data = self._load(requested)
        value = data.get(section, {}).get(key)
        if value:
            return value
        # Per-key fallback to English so a partially-translated locale
        # never shows a blank string.
        fallback = self._load(DEFAULT_LOCALE)
        return fallback.get(section, {}).get(key, key)

    def reason_text(self, code: ReasonCode | str, locale: str) -> str:
        key = code.value if isinstance(code, ReasonCode) else code
        return self._lookup(locale, "reasons", key)

    def recommendation(self, level: RiskLevel | str, locale: str) -> str:
        key = level.value if isinstance(level, RiskLevel) else level
        return self._lookup(locale, "recommendations", key)

    def level_label(self, level: RiskLevel | str, locale: str) -> str:
        key = level.value if isinstance(level, RiskLevel) else level
        return self._lookup(locale, "levels", key)
