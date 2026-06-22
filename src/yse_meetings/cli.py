"""Command line entry point. Thin dispatcher behind the Makefile targets.

Usage: python -m yse_meetings.cli {ingest,dedup,extract,eval}
"""

from __future__ import annotations

import argparse
import json

from yse_meetings import config
from yse_meetings.ingest.engine import available_sources, run_source


def cmd_ingest(args: argparse.Namespace) -> None:
    config.ensure_dirs()
    sources = args.sources or available_sources()
    total = 0
    out_path = config.INTERIM_DIR / "canonical.jsonl"
    with out_path.open("w", encoding="utf-8") as out:
        for name in sources:
            kept = 0
            for rec in run_source(name, config.RAW_DIR):
                out.write(rec.model_dump_json() + "\n")
                kept += 1
            print(f"{name}: wrote {kept} canonical records")
            total += kept
    print(f"ingest complete: {total} records -> {out_path}")


def cmd_dedup(args: argparse.Namespace) -> None:
    import collections

    import pandas as pd

    from yse_meetings.dedup.entity_resolution import resolve
    from yse_meetings.schema import CanonicalMeetingRecord

    config.ensure_dirs()
    in_path = config.INTERIM_DIR / "canonical.jsonl"
    records = [
        CanonicalMeetingRecord.model_validate_json(line)
        for line in in_path.open(encoding="utf-8")
    ]

    primaries, links, conflicts = resolve(records)

    # Overlap statistics, by canonical_id.
    by_id_sources = collections.defaultdict(set)
    by_id_count = collections.Counter()
    for link in links:
        by_id_sources[link.canonical_id].add(link.source)
        by_id_count[link.canonical_id] += 1
    multi_record = sum(1 for n in by_id_count.values() if n > 1)
    cross_source = sum(1 for s in by_id_sources.values() if len(s) > 1)

    meetings_path = config.PROCESSED_DIR / "meetings.parquet"
    provenance_path = config.PROCESSED_DIR / "provenance.parquet"
    conflicts_path = config.PROCESSED_DIR / "conflicts.parquet"

    pd.DataFrame([m.model_dump() for m in primaries]).to_parquet(meetings_path, index=False)
    pd.DataFrame([link.model_dump() for link in links]).to_parquet(provenance_path, index=False)
    pd.DataFrame(
        [c.model_dump() for c in conflicts]
        or [{"canonical_id": None, "field": None, "source_a": None,
             "value_a": None, "source_b": None, "value_b": None,
             "resolved_value": None, "note": None}]
    ).to_parquet(conflicts_path, index=False)

    print(f"input records:        {len(records)}")
    print(f"canonical meetings:   {len(primaries)}")
    print(f"linked (>1 record):   {multi_record}")
    print(f"cross-source linked:  {cross_source}")
    print(f"conflicts flagged:    {len(conflicts)}")
    print(f"wrote {meetings_path.name}, {provenance_path.name}, {conflicts_path.name}")


def cmd_extract(args: argparse.Namespace) -> None:
    import collections
    import math

    import pandas as pd

    from yse_meetings.schema import CanonicalMeetingRecord

    config.ensure_dirs()
    df = pd.read_parquet(config.PROCESSED_DIR / "meetings.parquet")
    if config.EXTRACT_LIMIT:
        df = df.head(config.EXTRACT_LIMIT)

    def _clean(row: dict) -> dict:
        # parquet reads a null transcript back as NaN (float); restore None.
        return {
            k: (None if isinstance(v, float) and math.isnan(v) else v)
            for k, v in row.items()
        }

    records = [CanonicalMeetingRecord(**_clean(row)) for row in df.to_dict("records")]

    if args.method == "llm":
        from yse_meetings.extract.llm_extractor import extract_actions
        out_name = "actions_llm.parquet"
    else:
        from yse_meetings.extract.lexicon import extract_actions
        out_name = "actions.parquet"

    actions = extract_actions(records)
    out_path = config.PROCESSED_DIR / out_name
    pd.DataFrame([a.model_dump() for a in actions]).to_parquet(out_path, index=False)

    by_cat = collections.Counter(a.action_category for a in actions)
    print(f"method:              {args.method}")
    print(f"meetings processed:  {len(records)}")
    print(f"actions extracted:   {len(actions)}")
    print(f"by category:         {dict(by_cat)}")
    print(f"wrote {out_path.name}")


def cmd_analyze(args: argparse.Namespace) -> None:
    import pandas as pd

    from yse_meetings.analysis.summarize import build_all

    config.ensure_dirs()
    out_dir = config.PROCESSED_DIR / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    meetings = pd.read_parquet(config.PROCESSED_DIR / "meetings.parquet")
    actions = pd.read_parquet(config.PROCESSED_DIR / "actions.parquet")

    from yse_meetings.enrich import hazard_exposure
    exposure_df = None
    if hazard_exposure.available():
        exposure_df = hazard_exposure.enrich(meetings)
        exposure_df.to_parquet(config.PROCESSED_DIR / "exposure.parquet", index=False)
        resolved = exposure_df["county_fips"].notna().sum()
        print(f"hazard exposure: resolved {resolved}/{len(exposure_df)} meetings to a county")
    else:
        print("hazard exposure: NRI slim file not found, skipping exposure "
              "(run scripts/build_nri_slim.py)")

    tables = build_all(meetings, actions, exposure_df)
    for name, table in tables.items():
        table.to_parquet(out_dir / f"{name}.parquet", index=False)

    print("\n=== actions per meeting by region ===")
    print(tables["by_region"][["region", "meetings", "jurisdictions",
                                "climate_actions", "actions_per_meeting"]].to_string(index=False))
    print("\n=== adaptation actions by hazard type ===")
    print(tables["by_hazard"].to_string(index=False))
    if "exposure_alignment" in tables:
        print("\n=== hazard exposure vs adaptation action (alignment) ===")
        print(tables["exposure_alignment"].to_string(index=False))
    print(f"\nwrote {len(tables)} analysis tables to {out_dir}")


def cmd_eval(args: argparse.Namespace) -> None:
    import datetime as _dt
    import json

    from yse_meetings.eval.metrics import evaluate

    config.ensure_dirs()

    if args.method == "llm":
        from yse_meetings.extract.llm_extractor import classify_text
    else:
        from yse_meetings.extract.lexicon import classify_text

    report = evaluate(classify_text, config.GOLDEN_DATASET, method=args.method)

    stamp = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = config.EVAL_REPORTS_DIR / f"eval_{args.method}_{stamp}.json"
    latest_path = config.EVAL_REPORTS_DIR / "latest.json"
    method_path = config.EVAL_REPORTS_DIR / f"latest_{args.method}.json"
    for path in (out_path, latest_path, method_path):
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"wrote {out_path.name}, latest.json, {method_path.name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="yse_meetings")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="pull and normalize source samples")
    p_ingest.add_argument("--sources", nargs="*", choices=available_sources(), default=None)
    p_ingest.set_defaults(func=cmd_ingest)

    sub.add_parser("dedup", help="link records and flag conflicts").set_defaults(func=cmd_dedup)
    p_extract = sub.add_parser("extract", help="extract actions (lexicon or llm)")
    p_extract.add_argument("--method", choices=["lexicon", "llm"], default="lexicon")
    p_extract.set_defaults(func=cmd_extract)
    sub.add_parser("analyze", help="build region/hazard/time summaries").set_defaults(func=cmd_analyze)
    p_eval = sub.add_parser("eval", help="score a method against the golden set")
    p_eval.add_argument("--method", choices=["lexicon", "llm"], default="lexicon")
    p_eval.set_defaults(func=cmd_eval)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
