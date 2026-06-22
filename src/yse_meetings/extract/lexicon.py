"""Lexicon classifier: a transparent, scalable, tunable baseline.

Why this exists alongside the LLM: a domain expert can read and tune the
term lists, it runs free over 10,000 meetings in seconds, it is fully
reproducible, and it gives an interpretable basis for the analysis. The LLM
adds nuance on ambiguous cases; the lexicon carries scale. We report both
and compare them on a held-out split.

The lexicon config is the topic definition. Swapping it (climate -> housing)
retargets the pipeline with no code change, which is the heart of Part II.

classify_text(text) returns (category, hazard, confidence) and can label any
excerpt, including 'unrelated', so it works both for corpus extraction and
for scoring the golden set.
"""

from __future__ import annotations

import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

import yaml

from yse_meetings import config
from yse_meetings.schema import CanonicalMeetingRecord, ExtractedAction

_LEXICON_PATH = config.REPO_ROOT / "configs" / "lexicon.climate.yaml"
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_MIN_LEN = 25
_VERSION = "lexicon:climate-v1"


@lru_cache(maxsize=1)
def _lexicon(path: str = str(_LEXICON_PATH)) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _hits(text: str, terms: Iterable[str]) -> list[str]:
    low = text.lower()
    return [t for t in terms if t in low]


def classify_text(text: str) -> tuple[str, Optional[str], float]:
    """Classify one excerpt. Returns (category, hazard, confidence).

    category is one of adaptation, mitigation, both, unrelated.
    """
    lex = _lexicon()
    low = (text or "").lower()

    adapt = _hits(low, lex["adaptation_strong"])
    mitig = _hits(low, lex["mitigation_strong"])
    generic = _hits(low, lex["climate_generic"])
    weak = _hits(low, lex["weak_context"])
    procedural = _hits(low, lex["procedural"])

    has_strong = bool(adapt or mitig)
    has_climate = has_strong or bool(generic)

    # Procedural motions with no real climate phrase are unrelated.
    if procedural and not has_climate:
        return "unrelated", "none", _conf(0, 0, 0, 0)
    # Weak terms (transit, bike) only count when climate context is present.
    if not has_climate and not weak:
        return "unrelated", "none", 0.5
    if not has_climate and weak:
        return "unrelated", "none", 0.45

    if adapt and mitig:
        category = "both"
    elif adapt:
        category = "adaptation"
    elif mitig:
        category = "mitigation"
    else:
        # only generic climate language, no concrete direction
        category = "both" if weak else "unrelated"

    hazard = _hazard(low, lex) if category in ("adaptation", "both") else "none"
    confidence = _conf(len(adapt), len(mitig), len(generic), len(weak))
    return category, hazard, confidence


def _hazard(low: str, lex: dict) -> str:
    for hazard, terms in lex["hazards"].items():
        if any(t in low for t in terms):
            return hazard
    return "other"


def _conf(n_adapt: int, n_mitig: int, n_generic: int, n_weak: int) -> float:
    """Heuristic confidence: more specific, more confident."""
    strong = n_adapt + n_mitig
    if strong >= 2:
        return 0.9
    if strong == 1:
        return 0.75
    if n_generic:
        return 0.6
    return 0.5


def extract_actions(records: Iterable[CanonicalMeetingRecord]) -> list[ExtractedAction]:
    """Emit one ExtractedAction per climate-relevant sentence."""
    results: list[ExtractedAction] = []
    now = datetime.utcnow()
    for rec in records:
        if not rec.transcript:
            continue
        for sentence in _SENT_SPLIT.split(rec.transcript):
            sentence = sentence.strip()
            if len(sentence) < _MIN_LEN:
                continue
            category, hazard, confidence = classify_text(sentence)
            if category == "unrelated":
                continue
            results.append(
                ExtractedAction(
                    canonical_id=rec.canonical_id,
                    action_text=sentence[:500],
                    action_category=category,  # type: ignore[arg-type]
                    hazard_type=hazard,  # type: ignore[arg-type]
                    confidence=confidence,
                    model_version=_VERSION,
                    extracted_at=now,
                )
            )
    return results
