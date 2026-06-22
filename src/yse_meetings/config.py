"""Central paths and small runtime settings.

Flat module, no framework. Everything resolves relative to the repo root
so the pipeline behaves the same on a fresh clone.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
CROSSWALK_DIR = DATA_DIR / "crosswalks"
GOLDEN_DIR = DATA_DIR / "golden"

FIPS_CROSSWALK = CROSSWALK_DIR / "fips_crosswalk.csv"
GOLDEN_DATASET = GOLDEN_DIR / "golden_dataset.jsonl"
EVAL_REPORTS_DIR = PROCESSED_DIR / "eval_reports"

# Size of the development sample pulled per source. Kept small so the demo
# is reproducible on a laptop and on Streamlit Community Cloud free tier.
SAMPLE_SIZE = int(os.environ.get("YSE_SAMPLE_SIZE", "200"))

# Seed for reproducible sampling.
SAMPLE_SEED = int(os.environ.get("YSE_SAMPLE_SEED", "42"))

# LocalView years to pull. Comma separated. Default is one year that
# overlaps the MeetingBank window and keeps the download modest.
LOCALVIEW_YEARS = [
    y.strip() for y in os.environ.get("YSE_LOCALVIEW_YEARS", "2014").split(",") if y.strip()
]

# Extraction provider. Default is a local model via Ollama so the project
# runs free with no API key. Swap to "anthropic" or "openai" by setting
# YSE_LLM_PROVIDER and the matching key. The demo reads precomputed results,
# so it never needs a live key.
LLM_PROVIDER = os.environ.get("YSE_LLM_PROVIDER", "ollama")
LLM_MODEL = os.environ.get("YSE_LLM_MODEL", "llama3.1:8b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")

# Characters of transcript sent to the model per meeting, and an optional cap
# on how many meetings to process (useful for a quick local run).
EXTRACT_MAX_CHARS = int(os.environ.get("YSE_EXTRACT_MAX_CHARS", "6000"))
EXTRACT_LIMIT = int(os.environ.get("YSE_EXTRACT_LIMIT", "0"))  # 0 means no cap


def ensure_dirs() -> None:
    """Create the local data directories if they are missing."""
    for d in (RAW_DIR, INTERIM_DIR, PROCESSED_DIR, EVAL_REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
