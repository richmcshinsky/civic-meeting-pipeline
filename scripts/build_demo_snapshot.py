"""Copy the current processed outputs into data/demo for deployment.

data/processed is gitignored and regenerated locally by make all. Streamlit
Community Cloud cannot run the pipeline (no Ollama, no large downloads), so it
reads a committed snapshot in data/demo instead. Run this after make all,
make eval, and make eval-llm, then commit data/demo.

    uv run python scripts/build_demo_snapshot.py
"""

from __future__ import annotations

import shutil

from yse_meetings import config

DEMO_DIR = config.DATA_DIR / "demo"


def main() -> None:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    (DEMO_DIR / "analysis").mkdir(exist_ok=True)
    (DEMO_DIR / "eval_reports").mkdir(exist_ok=True)

    # Top-level processed tables.
    for name in ("meetings.parquet", "actions.parquet", "provenance.parquet",
                 "conflicts.parquet"):
        src = config.PROCESSED_DIR / name
        if src.exists():
            shutil.copy2(src, DEMO_DIR / name)
            print(f"copied {name}")
        else:
            print(f"missing {name} (run make all first)")

    # Analysis tables the app reads.
    analysis_src = config.PROCESSED_DIR / "analysis"
    if analysis_src.exists():
        for p in analysis_src.glob("*.parquet"):
            shutil.copy2(p, DEMO_DIR / "analysis" / p.name)
        print(f"copied {len(list(analysis_src.glob('*.parquet')))} analysis tables")
    else:
        print("missing analysis tables (run make analyze first)")

    # Per-method eval reports the app reads.
    for name in ("latest_lexicon.json", "latest_llm.json"):
        src = config.EVAL_REPORTS_DIR / name
        if src.exists():
            shutil.copy2(src, DEMO_DIR / "eval_reports" / name)
            print(f"copied eval_reports/{name}")
        else:
            print(f"missing eval_reports/{name} (run make eval / make eval-llm)")

    print(f"\ndemo snapshot ready in {DEMO_DIR}. Commit it for Streamlit Cloud.")


if __name__ == "__main__":
    main()
