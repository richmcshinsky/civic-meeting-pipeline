"""Labeling helper.

Pulls candidate actions from the extracted set and lets you hand-label them
quickly at the command line, writing to the golden set. The golden set is the
anchor for the eval harness, so this is where the methods credibility starts.

Usage:
    uv run python -m yse_meetings.label --n 80

For each candidate it shows the model's guess. Press Enter to accept it, or
type a correction. Labels append to data/golden/golden_dataset.jsonl. Items
already labeled (matched on action_text) are skipped so you can resume.
"""

from __future__ import annotations

import argparse
import json
import os

from yse_meetings import config

_CAT = {"a": "adaptation", "m": "mitigation", "b": "both", "u": "unrelated"}
_HAZ = {
    "f": "flood", "w": "wildfire", "h": "heat", "d": "drought",
    "s": "storm", "l": "sea_level_rise", "o": "other", "n": "none",
}


def _already_labeled() -> set[str]:
    path = config.GOLDEN_DATASET
    if not path.exists():
        return set()
    seen = set()
    for line in path.open(encoding="utf-8"):
        line = line.strip()
        if line:
            seen.add(json.loads(line).get("action_text", ""))
    return seen


def main() -> None:
    import pandas as pd

    parser = argparse.ArgumentParser(prog="yse_meetings.label")
    parser.add_argument("--n", type=int, default=80, help="how many to label")
    args = parser.parse_args()

    actions_path = config.PROCESSED_DIR / "actions.parquet"
    df = pd.read_parquet(actions_path)

    # Stratify across model categories so the golden set is balanced.
    per = max(args.n // 4, 1)
    frames = []
    for cat in ("adaptation", "mitigation", "both", "unrelated"):
        sub = df[df["action_category"] == cat]
        if len(sub):
            frames.append(sub.sample(n=min(per, len(sub)), random_state=config.SAMPLE_SEED))
    candidates = pd.concat(frames).to_dict("records") if frames else []

    seen = _already_labeled()
    config.GOLDEN_DATASET.parent.mkdir(parents=True, exist_ok=True)

    print("Categories: a=adaptation m=mitigation b=both u=unrelated")
    print("Hazards:    f=flood w=wildfire h=heat d=drought s=storm l=sea_level_rise o=other n=none")
    print("Enter to accept the model guess shown in [brackets]. Ctrl-C to stop.\n")

    written = 0
    with config.GOLDEN_DATASET.open("a", encoding="utf-8") as out:
        for item in candidates:
            text = item["action_text"]
            if text in seen:
                continue
            print("-" * 70)
            print(f"meeting: {item['canonical_id']}  model conf: {item.get('confidence')}")
            print(f"ACTION: {text}")

            guess_cat = item["action_category"]
            raw = input(f"category [{guess_cat}]: ").strip().lower()
            category = _CAT.get(raw, guess_cat)

            guess_haz = item.get("hazard_type") or "none"
            raw = input(f"hazard [{guess_haz}]: ").strip().lower()
            hazard = _HAZ.get(raw, guess_haz)

            out.write(json.dumps({
                "canonical_id": item["canonical_id"],
                "action_text": text,
                "action_category": category,
                "hazard_type": hazard,
                "label_source": os.environ.get("YSE_LABELER", "richard_mcshinsky"),
            }) + "\n")
            out.flush()
            seen.add(text)
            written += 1

    print(f"\nwrote {written} labels to {config.GOLDEN_DATASET}")


if __name__ == "__main__":
    main()
