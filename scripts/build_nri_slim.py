"""Slim the FEMA NRI county table to the columns we use.

The full NRI county CSV is ~24 MB with 465 columns. We only need the county
key, identity, population, overall risk, and the per-hazard risk scores that
map to our hazard tags. This writes a small, committable crosswalk.

Place the downloaded NRI county CSV at data/crosswalks/NRI_Table_Counties.csv
(unzip the FEMA download), then run:

    uv run python scripts/build_nri_slim.py
"""

from __future__ import annotations

import pandas as pd

from yse_meetings import config

SRC = config.CROSSWALK_DIR / "NRI_Table_Counties.csv"
OUT = config.CROSSWALK_DIR / "nri_county_slim.csv"

# NRI per-hazard risk-score columns mapped to our hazard tags.
HAZARD_COLUMNS = {
    "flood": "IFLD_RISKS",          # inland / riverine flooding
    "sea_level_rise": "CFLD_RISKS",  # coastal flooding (proxy)
    "wildfire": "WFIR_RISKS",
    "heat": "HWAV_RISKS",            # heat wave
    "drought": "DRGT_RISKS",
    "storm": "HRCN_RISKS",           # hurricane (proxy)
}

KEEP = ["STCOFIPS", "STATEABBRV", "COUNTY", "POPULATION", "RISK_SCORE"] + list(
    HAZARD_COLUMNS.values()
)


def main() -> None:
    if not SRC.exists():
        raise SystemExit(
            f"Missing {SRC}. Download the FEMA NRI county CSV (unzip the FEMA "
            "download) into data/crosswalks/ and rerun."
        )
    df = pd.read_csv(SRC, usecols=lambda c: c in KEEP, low_memory=False)
    df["STCOFIPS"] = df["STCOFIPS"].astype(str).str.zfill(5)
    df.to_csv(OUT, index=False)
    print(f"wrote {OUT} with {len(df)} counties and columns {list(df.columns)}")


if __name__ == "__main__":
    main()
