"""Hazard exposure enrichment: join jurisdictions to FEMA NRI county risk.

This is what lets us ask the climate-adaptation question that matters: do
places with higher exposure to a hazard take more adaptation action against
that hazard? We attach each meeting's county-level NRI risk scores.

County resolution, in order:
1. MeetingBank cities: a small hardcoded place-FIPS to county-FIPS map.
2. County-type jurisdictions (name contains County or Parish): matched to NRI
   by county name + state.
3. An optional committed place_to_county.csv (place_fips,county_fips) for
   full place coverage.
Unresolved jurisdictions get null exposure and are reported as a coverage gap.
We never guess.
"""

from __future__ import annotations

import re
from functools import lru_cache

import pandas as pd

from yse_meetings import config

NRI_SLIM = config.CROSSWALK_DIR / "nri_county_slim.csv"
PLACE_TO_COUNTY = config.CROSSWALK_DIR / "place_to_county.csv"

HAZARD_COLUMNS = {
    "flood": "IFLD_RISKS",
    "sea_level_rise": "CFLD_RISKS",
    "wildfire": "WFIR_RISKS",
    "heat": "HWAV_RISKS",
    "drought": "DRGT_RISKS",
    "storm": "HRCN_RISKS",
}

# MeetingBank place FIPS -> county FIPS (STCOFIPS).
MEETINGBANK_COUNTY = {
    "5363000": "53033",  # Seattle -> King County
    "53033": "53033",    # King County
    "0820000": "08031",  # Denver -> Denver County
    "2507000": "25025",  # Boston -> Suffolk County
    "0643000": "06037",  # Long Beach -> Los Angeles County
    "0600562": "06001",  # Alameda -> Alameda County
}

_COUNTY_SUFFIX = re.compile(r"\s+(county|parish|borough)$", re.I)


@lru_cache(maxsize=1)
def _nri() -> pd.DataFrame:
    df = pd.read_csv(NRI_SLIM, dtype={"STCOFIPS": str})
    df["STCOFIPS"] = df["STCOFIPS"].str.zfill(5)
    df["_county_key"] = df["COUNTY"].str.upper().str.strip() + "|" + df["STATEABBRV"].str.upper()
    return df


@lru_cache(maxsize=1)
def _place_to_county() -> dict[str, str]:
    if not PLACE_TO_COUNTY.exists():
        return {}
    df = pd.read_csv(PLACE_TO_COUNTY, dtype=str)
    return dict(zip(df["place_fips"].str.strip(), df["county_fips"].str.zfill(5)))


def resolve_county(fips: str, name: str, state: str) -> str | None:
    fips = str(fips).strip()
    if fips in MEETINGBANK_COUNTY:
        return MEETINGBANK_COUNTY[fips]
    if fips in _place_to_county():
        return _place_to_county()[fips]
    if _COUNTY_SUFFIX.search(name or ""):
        county = _COUNTY_SUFFIX.sub("", name).upper().strip()
        key = f"{county}|{str(state).upper()}"
        match = _nri()[_nri()["_county_key"] == key]
        if not match.empty:
            return match.iloc[0]["STCOFIPS"]
    return None


def enrich(meetings: pd.DataFrame) -> pd.DataFrame:
    """Return meetings with county_fips and per-hazard NRI risk scores attached."""
    nri = _nri().set_index("STCOFIPS")
    rows = []
    for _, m in meetings.iterrows():
        county = resolve_county(m["jurisdiction_fips"], m["jurisdiction_name"], m["state"])
        row = {"canonical_id": m["canonical_id"], "county_fips": county}
        if county is not None and county in nri.index:
            n = nri.loc[county]
            row["county_name"] = n["COUNTY"]
            row["overall_risk"] = n["RISK_SCORE"]
            for hazard, col in HAZARD_COLUMNS.items():
                row[f"risk_{hazard}"] = n.get(col)
        rows.append(row)
    return pd.DataFrame(rows)


def available() -> bool:
    return NRI_SLIM.exists()
