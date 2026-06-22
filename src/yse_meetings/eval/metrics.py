"""Evaluation harness. This is the methods section in code form.

We evaluate a classifier directly on the hand-labeled golden excerpts: for
each labeled action_text we run the method under test and compare its
prediction to the human label. This is method-agnostic (lexicon or LLM use
the same harness) and avoids fragile joins on generated text.

What it reports:
- Precision, recall, F1 per action_category against the golden set.
- Per hazard_type accuracy, exploratory, with support counts.
- Confidence calibration: predictions binned by confidence with empirical
  accuracy per bin.
- Human-vs-model agreement (Cohen's kappa). This is agreement between the
  annotator's labels and the method, not inter-annotator agreement.

Reports are written as JSON to data/processed/eval_reports/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

# A classifier takes an excerpt and returns (category, hazard, confidence).
Classifier = Callable[[str], tuple[str, Optional[str], float]]

CATEGORIES = ["adaptation", "mitigation", "both", "unrelated"]
_BINS = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.01)]


def load_golden(golden_path: Path) -> dict[str, dict]:
    """Map action_text to the golden label record."""
    golden: dict[str, dict] = {}
    if not golden_path.exists():
        return golden
    for line in golden_path.open(encoding="utf-8"):
        line = line.strip()
        if line:
            row = json.loads(line)
            golden[row["action_text"]] = row
    return golden


def evaluate(classify_fn: Classifier, golden_path: Path, method: str = "") -> dict:
    """Run classify_fn on every golden excerpt and score it."""
    from sklearn.metrics import cohen_kappa_score, precision_recall_fscore_support

    golden = load_golden(golden_path)
    if not golden:
        return {"method": method, "golden_items": 0,
                "note": "Golden set is empty. Label with make label."}

    y_true, y_pred, conf, haz_true, haz_pred = [], [], [], [], []
    for text, gold in golden.items():
        cat, haz, c = classify_fn(text)
        y_true.append(gold["action_category"])
        y_pred.append(cat)
        conf.append(float(c))
        haz_true.append(gold.get("hazard_type") or "none")
        haz_pred.append(haz or "none")

    n = len(y_true)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=CATEGORIES, zero_division=0
    )
    report: dict = {
        "method": method,
        "golden_items": n,
        "per_category": {
            cat: {
                "precision": round(float(precision[i]), 3),
                "recall": round(float(recall[i]), 3),
                "f1": round(float(f1[i]), 3),
                "support": int(support[i]),
            }
            for i, cat in enumerate(CATEGORIES)
        },
        "macro_f1": round(float(sum(f1) / len(f1)), 3),
        "accuracy": round(sum(int(a == b) for a, b in zip(y_true, y_pred)) / n, 3),
        "human_vs_model_cohen_kappa": round(float(cohen_kappa_score(y_true, y_pred)), 3),
        "kappa_note": (
            "Agreement between annotator labels and the method, not "
            "inter-annotator agreement."
        ),
    }

    calibration = []
    for low, high in _BINS:
        idx = [i for i, c in enumerate(conf) if low <= c < high]
        if idx:
            acc = sum(int(y_true[i] == y_pred[i]) for i in idx) / len(idx)
            calibration.append({
                "bin": f"{low:.1f}-{min(high, 1.0):.1f}",
                "n": len(idx),
                "empirical_accuracy": round(acc, 3),
            })
    report["confidence_calibration"] = calibration

    haz_counts: dict[str, list[int]] = {}
    for ht, hp, yt in zip(haz_true, haz_pred, y_true):
        if yt != "adaptation":
            continue
        bucket = haz_counts.setdefault(ht, [0, 0])
        bucket[1] += 1
        if ht == hp:
            bucket[0] += 1
    report["hazard_accuracy_exploratory"] = {
        ht: {"correct": c, "support": s, "accuracy": round(c / s, 3)}
        for ht, (c, s) in haz_counts.items()
    }
    report["hazard_note"] = "Exploratory only; small per-class support."
    return report
