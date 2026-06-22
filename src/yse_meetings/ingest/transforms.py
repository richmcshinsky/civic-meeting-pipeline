"""Reusable field transforms referenced by source configs.

A source's field_map declares, per canonical field, one transform spec. The
generic adapter applies these, so a new tabular source is a YAML file rather
than new code. Genuinely exotic parsing (composite ids) lives in a named
mapper instead; this module covers the common cases.

Spec forms (one key each):
  {copy: source_col}
  {const: value}
  {template: "https://...{col}"}
  {state_abbrev: source_col}            full state name -> 2-letter code
  {meeting_type_from_govt: source_col}  governing body -> meeting_type or None
  {parse_date: {column: c, format: iso|mmddyyyy}}
  {clean_text: {column: c, missing: "<sentinel>"}}
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Optional

STATE_ABBREV = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
    "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


def meeting_type_from_govt(value: Optional[str]) -> Optional[str]:
    """Map a LocalView governing-body label to our meeting_type, or None to
    drop bodies outside the agreed scope (councils, county, planning/zoning)."""
    if not value:
        return None
    g = value.upper()
    if "PLAN" in g or "ZON" in g:
        return "committee"
    if "COUNCIL" in g or "COMMISSION" in g or "COUNTY" in g or "BOARD OF SUPERVISORS" in g:
        return "council_full"
    return None


def parse_date(value: Any, fmt: str) -> Optional[date]:
    if value is None or value == "":
        return None
    text = str(value)
    if fmt == "mmddyyyy":
        if len(text) != 8 or not text.isdigit():
            return None
        try:
            return date(int(text[4:8]), int(text[0:2]), int(text[2:4]))
        except ValueError:
            return None
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def clean_text(value: Any, missing: str) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == missing.lower():
        return None
    return text


def apply_spec(spec: dict, row: dict) -> Any:
    """Apply a single field transform spec to a raw row."""
    if "copy" in spec:
        v = row.get(spec["copy"])
        return None if v is None else str(v).strip()
    if "const" in spec:
        return spec["const"]
    if "template" in spec:
        try:
            return spec["template"].format(**{k: (row.get(k) or "") for k in row})
        except Exception:
            return ""
    if "state_abbrev" in spec:
        return STATE_ABBREV.get(str(row.get(spec["state_abbrev"]) or "").strip(), "")
    if "meeting_type_from_govt" in spec:
        return meeting_type_from_govt(row.get(spec["meeting_type_from_govt"]))
    if "parse_date" in spec:
        p = spec["parse_date"]
        return parse_date(row.get(p["column"]), p.get("format", "iso"))
    if "clean_text" in spec:
        p = spec["clean_text"]
        return clean_text(row.get(p["column"]), p.get("missing", ""))
    raise ValueError(f"unknown transform spec: {spec}")


_PUNCT = re.compile(r"\s+")
