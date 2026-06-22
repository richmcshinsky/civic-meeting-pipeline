"""LLM-assisted action extraction.

Given a meeting transcript, return ExtractedAction rows: adaptation,
mitigation, both, or unrelated, with an optional hazard tag and a confidence.

Design notes:
- Provider is abstracted (config.LLM_PROVIDER). Default is a free local model
  via Ollama, so the project runs with no API key. Anthropic or OpenAI are a
  config change behind the same seam.
- Structured output is requested as JSON and validated into ExtractedAction,
  so the model returns parseable fields, not prose.
- Parsing is a pure function (parse_actions) so it can be unit tested without
  a live model.
- The deployed demo reads precomputed actions from disk and never calls a
  model.

Simplification, documented honestly: each meeting is sent as a single
truncated transcript window rather than fully chunked. This keeps a local
model tractable on a laptop. Production would window the full transcript and
extract per window. The truncation length is config-controlled.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from yse_meetings import config
from yse_meetings.schema import CanonicalMeetingRecord, ExtractedAction

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "action_extraction.md"

_VALID_CATEGORIES = {"adaptation", "mitigation", "both", "unrelated"}
_VALID_HAZARDS = {
    "flood", "wildfire", "heat", "drought", "storm", "sea_level_rise", "other", "none",
}

def load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def model_version() -> str:
    return f"{config.LLM_PROVIDER}:{config.LLM_MODEL}"


def parse_actions(raw: str, canonical_id: str, version: str) -> list[ExtractedAction]:
    """Parse a model JSON response into ExtractedAction rows.

    Raises ValueError if the response is not valid JSON. Individual items that
    are malformed (missing text, invalid category) are skipped rather than
    failing the whole meeting.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"model did not return valid JSON: {exc}") from exc

    items = data.get("actions", []) if isinstance(data, dict) else []
    out: list[ExtractedAction] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = str(item.get("action_text", "")).strip()
        category = item.get("action_category")
        if not text or category not in _VALID_CATEGORIES:
            continue

        hazard = item.get("hazard_type")
        if hazard not in _VALID_HAZARDS:
            hazard = None

        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        out.append(
            ExtractedAction(
                canonical_id=canonical_id,
                action_text=text,
                action_category=category,  # type: ignore[arg-type]
                hazard_type=hazard,  # type: ignore[arg-type]
                confidence=confidence,
                model_version=version,
                extracted_at=datetime.utcnow(),
            )
        )
    return out


_CLASSIFY_INSTRUCTIONS = (
    "Classify the following municipal council excerpt for climate action. "
    "Return one JSON object: {\"action_category\": one of "
    "adaptation|mitigation|both|unrelated, \"hazard_type\": one of "
    "flood|wildfire|heat|drought|storm|sea_level_rise|other|none, "
    "\"confidence\": 0..1}. Nothing else.\n\nExcerpt:\n"
)


def classify_text(text: str) -> tuple[str, Optional[str], float]:
    """Classify a single excerpt with the LLM. Used by the eval harness.

    Mirrors the lexicon classify_text signature so both methods share the
    same eval. Returns ('unrelated', 'none', 0.0) on any failure.
    """
    try:
        raw = _complete(_CLASSIFY_INSTRUCTIONS + str(text)[: config.EXTRACT_MAX_CHARS])
        data = json.loads(raw)
        cat = data.get("action_category")
        if cat not in _VALID_CATEGORIES:
            return "unrelated", "none", 0.0
        hazard = data.get("hazard_type")
        if hazard not in _VALID_HAZARDS:
            hazard = "none"
        try:
            conf = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
        except (TypeError, ValueError):
            conf = 0.0
        return cat, hazard, conf
    except Exception:
        return "unrelated", "none", 0.0


def _complete(prompt: str) -> str:
    """Send a prompt to the configured provider and return the raw text."""
    provider = config.LLM_PROVIDER
    if provider == "ollama":
        return _complete_ollama(prompt)
    raise NotImplementedError(
        f"Provider '{provider}' is not wired. Default is 'ollama'. "
        "Anthropic and OpenAI slot in here behind the same function."
    )


def _complete_ollama(prompt: str) -> str:
    import requests

    resp = requests.post(
        config.OLLAMA_URL,
        json={
            "model": config.LLM_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0},
        },
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


def extract_actions(records: Iterable[CanonicalMeetingRecord]) -> list[ExtractedAction]:
    """Run extraction over records that have a transcript."""
    base_prompt = load_prompt()
    version = model_version()
    results: list[ExtractedAction] = []

    for rec in records:
        if not rec.transcript:
            continue
        excerpt = rec.transcript[: config.EXTRACT_MAX_CHARS]
        prompt = f"{base_prompt}\n\n## Transcript excerpt\n\n{excerpt}\n"
        try:
            raw = _complete(prompt)
            results.extend(parse_actions(raw, rec.canonical_id, version))
        except Exception as exc:  # one bad meeting should not stop the run
            print(f"skip {rec.canonical_id}: {exc}")
            continue
    return results
