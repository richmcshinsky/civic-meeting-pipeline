"""Config-driven ingestion engine.

A source is a YAML file under configs/sources/. The engine reads it, calls the
named loader to fetch raw rows, and the named mapper to turn them into
canonical records. A new tabular source needs only a config (loader +
field_map via the generic_tabular mapper); sources with composite identifiers,
like MeetingBank, use a small named mapper as a documented escape hatch.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import yaml

from yse_meetings import config
from yse_meetings.ingest.loaders import LOADERS
from yse_meetings.ingest.transforms import apply_spec
from yse_meetings.schema import CanonicalMeetingRecord, make_canonical_id

SOURCES_DIR = config.REPO_ROOT / "configs" / "sources"

# MeetingBank covers six councils, keyed by a token matched against the uid.
# Used only by the meetingbank_segments mapper.
_MEETINGBANK_JURIS: dict[str, dict] = {
    "alameda": {"fips": "0600562", "state": "CA", "name": "Alameda"},
    "boston": {"fips": "2507000", "state": "MA", "name": "Boston"},
    "denver": {"fips": "0820000", "state": "CO", "name": "Denver"},
    "longbeach": {"fips": "0643000", "state": "CA", "name": "Long Beach"},
    "kingcounty": {"fips": "53033", "state": "WA", "name": "King County"},
    "seattle": {"fips": "5363000", "state": "WA", "name": "Seattle"},
}


def _parse_meetingbank_uid(uid: str):
    """Parse 'DenverCityCouncil_05012017_17-0161' into jurisdiction, date,
    meeting_type, and the meeting-level uid. Returns None if it does not parse."""
    from datetime import date

    parts = uid.split("_")
    if len(parts) < 2:
        return None
    body, datestr = parts[0], parts[1]
    juris = next((m for t, m in _MEETINGBANK_JURIS.items() if t in body.lower()), None)
    if juris is None:
        return None
    if len(datestr) != 8 or not datestr.isdigit():
        return None
    try:
        mdate = date(int(datestr[4:8]), int(datestr[0:2]), int(datestr[2:4]))
    except ValueError:
        return None
    body_l = body.lower()
    mtype = ("committee" if "committee" in body_l
             else "special" if "special" in body_l
             else "workshop" if "workshop" in body_l
             else "council_full")
    return juris, mdate, mtype, f"{body}_{datestr}"


def load_config(name: str) -> dict:
    cfg = yaml.safe_load((SOURCES_DIR / f"{name}.yaml").read_text(encoding="utf-8"))
    cfg["name"] = name
    return cfg


def _build_record(row: dict, cfg: dict) -> CanonicalMeetingRecord | None:
    vals = {field: apply_spec(spec, row) for field, spec in cfg["field_map"].items()}
    fips = vals.get("jurisdiction_fips")
    mtype = vals.get("meeting_type")
    mdate = vals.get("meeting_date")
    if not fips or mtype is None or mdate is None:
        return None
    transcript = vals.get("transcript")
    return CanonicalMeetingRecord(
        canonical_id=make_canonical_id(str(fips), mdate, mtype),
        jurisdiction_name=vals.get("jurisdiction_name") or "",
        jurisdiction_fips=str(fips),
        state=vals.get("state") or "",
        meeting_date=mdate,
        meeting_type=mtype,
        transcript=transcript,
        transcript_quality="full_text" if transcript else "metadata_only",
        source=cfg["name"],
        source_url=vals.get("source_url") or "",
        source_record_id=str(vals.get("source_record_id") or ""),
    )


def _group_preserving_sample(df, group_keys: list[str], size: int, seed: int):
    df = df.copy()
    df["_key"] = df[group_keys].astype(str).agg("|".join, axis=1)
    sizes = df.groupby("_key").size()
    dup_keys = list(sizes[sizes > 1].index)
    import pandas as pd

    chosen = (
        pd.Series(dup_keys).sample(n=min(len(dup_keys), 40), random_state=seed)
        if dup_keys else pd.Series([], dtype=object)
    )
    dup_rows = df[df["_key"].isin(set(chosen))]
    singles = df[df["_key"].isin(set(sizes[sizes == 1].index))]
    remaining = max(size - len(dup_rows), 0)
    if len(singles) > remaining:
        singles = singles.sample(n=remaining, random_state=seed)
    return pd.concat([dup_rows, singles], ignore_index=True).drop(columns=["_key"])


def map_generic_tabular(raw, cfg: dict, raw_dir: Path) -> Iterator[CanonicalMeetingRecord]:
    """Row-wise mapping of a dataframe via the config field_map. Used for any
    standard tabular source, so adding one is pure configuration."""
    df = raw
    mt_spec = cfg["field_map"]["meeting_type"]
    in_scope = df.apply(lambda r: apply_spec(mt_spec, r.to_dict()) is not None, axis=1)
    df = df[in_scope].copy()

    s = cfg.get("sample", {})
    if s.get("strategy") == "group_preserving":
        df = _group_preserving_sample(df, s["group_keys"], s.get("size", 200),
                                      config.SAMPLE_SEED)
    elif s.get("size"):
        df = df.head(s["size"])

    for row in df.to_dict("records"):
        rec = _build_record(row, cfg)
        if rec is not None:
            yield rec


def map_meetingbank(raw, cfg: dict, raw_dir: Path) -> Iterator[CanonicalMeetingRecord]:
    """Escape-hatch mapper: MeetingBank rows are agenda segments with a
    composite uid, so we parse the uid and group segments into meetings."""
    meetings: dict = {}
    order: list = []
    for row in raw:
        parsed = _parse_meetingbank_uid(str(row.get("uid", "")))
        if parsed is None:
            continue
        juris, mdate, mtype, muid = parsed
        key = (juris["fips"], mdate, mtype)
        if key not in meetings:
            meetings[key] = {"j": juris, "d": mdate, "t": mtype, "uid": muid, "seg": []}
            order.append(key)
        if row.get("transcript"):
            meetings[key]["seg"].append(row["transcript"])

    for key in order:
        m = meetings[key]
        transcript = "\n\n".join(m["seg"]) if m["seg"] else None
        yield CanonicalMeetingRecord(
            canonical_id=make_canonical_id(m["j"]["fips"], m["d"], m["t"]),
            jurisdiction_name=m["j"]["name"],
            jurisdiction_fips=m["j"]["fips"],
            state=m["j"]["state"],
            meeting_date=m["d"],
            meeting_type=m["t"],
            transcript=transcript,
            transcript_quality="full_text" if transcript else "metadata_only",
            source=cfg["name"],
            source_url=cfg.get("source_url", ""),
            source_record_id=m["uid"],
        )


MAPPERS = {
    "generic_tabular": map_generic_tabular,
    "meetingbank_segments": map_meetingbank,
}


def run_source(name: str, raw_dir: Path) -> Iterator[CanonicalMeetingRecord]:
    cfg = load_config(name)
    loader_cfg = {**cfg["loader"], "name": name}
    raw = LOADERS[cfg["loader"]["type"]](loader_cfg, raw_dir)
    yield from MAPPERS[cfg["mapper"]["type"]](raw, cfg, raw_dir)


def available_sources() -> list[str]:
    return sorted(p.stem for p in SOURCES_DIR.glob("*.yaml"))
