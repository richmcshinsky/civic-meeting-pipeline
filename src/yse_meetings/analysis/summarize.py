"""Analysis layer: the answers to Rodriguez's actual question.

Produces summary tables for how municipal climate action varies by region,
hazard type, hazard exposure, and time. Everything is normalized by meeting
count where it matters, so we report intensity (actions per meeting), not raw
counts that just reflect where we happen to have data. Coverage tables make
the representativeness limits explicit.

Inputs are the deduped meetings and the extracted actions. Exposure is added
when the FEMA NRI join is available (see enrich.hazard_exposure).
"""

from __future__ import annotations

import pandas as pd

from yse_meetings.analysis import regions

CLIMATE = ["adaptation", "mitigation", "both"]


def _meetings_enriched(meetings: pd.DataFrame) -> pd.DataFrame:
    m = meetings.copy()
    m["region"] = m["state"].map(regions.region)
    m["year"] = pd.to_datetime(m["meeting_date"], errors="coerce").dt.year
    return m


def _actions_enriched(meetings: pd.DataFrame, actions: pd.DataFrame) -> pd.DataFrame:
    cols = ["canonical_id", "state", "meeting_date", "source",
            "jurisdiction_name", "jurisdiction_fips"]
    df = actions.merge(meetings[cols], on="canonical_id", how="left")
    df["region"] = df["state"].map(regions.region)
    df["year"] = pd.to_datetime(df["meeting_date"], errors="coerce").dt.year
    return df


def _intensity(table: pd.DataFrame) -> pd.DataFrame:
    for c in CLIMATE:
        if c not in table:
            table[c] = 0
    table["climate_actions"] = table[CLIMATE].sum(axis=1)
    table["actions_per_meeting"] = (
        table["climate_actions"] / table["meetings"].replace(0, pd.NA)
    ).round(3)
    return table


def by_region(meetings: pd.DataFrame, actions: pd.DataFrame) -> pd.DataFrame:
    m = _meetings_enriched(meetings)
    a = _actions_enriched(meetings, actions)
    base = m.groupby("region").agg(
        meetings=("canonical_id", "nunique"),
        jurisdictions=("jurisdiction_fips", "nunique"),
    )
    cat = a.pivot_table(index="region", columns="action_category",
                        values="canonical_id", aggfunc="count", fill_value=0)
    return _intensity(base.join(cat, how="left").fillna(0)).reset_index()


def by_state(meetings: pd.DataFrame, actions: pd.DataFrame) -> pd.DataFrame:
    m = _meetings_enriched(meetings)
    a = _actions_enriched(meetings, actions)
    base = m.groupby("state").agg(
        meetings=("canonical_id", "nunique"),
        region=("region", "first"),
    )
    cat = a.pivot_table(index="state", columns="action_category",
                        values="canonical_id", aggfunc="count", fill_value=0)
    return _intensity(base.join(cat, how="left").fillna(0)).reset_index()


def by_time(meetings: pd.DataFrame, actions: pd.DataFrame) -> pd.DataFrame:
    m = _meetings_enriched(meetings)
    a = _actions_enriched(meetings, actions)
    base = m.groupby("year").agg(meetings=("canonical_id", "nunique"))
    cat = a.pivot_table(index="year", columns="action_category",
                        values="canonical_id", aggfunc="count", fill_value=0)
    out = _intensity(base.join(cat, how="left").fillna(0)).reset_index()
    return out.dropna(subset=["year"])


def by_hazard(meetings: pd.DataFrame, actions: pd.DataFrame) -> pd.DataFrame:
    a = _actions_enriched(meetings, actions)
    haz = a[a["action_category"].isin(["adaptation", "both"])]
    return (
        haz.groupby("hazard_type").size().reset_index(name="actions")
        .sort_values("actions", ascending=False)
    )


def hazard_by_region(meetings: pd.DataFrame, actions: pd.DataFrame) -> pd.DataFrame:
    a = _actions_enriched(meetings, actions)
    haz = a[a["action_category"].isin(["adaptation", "both"])]
    return (
        haz.groupby(["region", "hazard_type"]).size().reset_index(name="actions")
        .sort_values(["region", "actions"], ascending=[True, False])
    )


def coverage(meetings: pd.DataFrame) -> pd.DataFrame:
    m = _meetings_enriched(meetings)
    m["has_transcript"] = m["transcript"].notna()
    return m.groupby(["region", "source"]).agg(
        meetings=("canonical_id", "nunique"),
        jurisdictions=("jurisdiction_fips", "nunique"),
        pct_with_transcript=("has_transcript", lambda s: round(100 * s.mean(), 1)),
    ).reset_index()


HAZARDS_FOR_EXPOSURE = ["flood", "heat", "wildfire", "drought"]


def exposure_tables(
    meetings: pd.DataFrame, actions: pd.DataFrame, exposure_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-jurisdiction risk vs adaptation-action counts, and the alignment.

    Answers: do higher-exposure places take more matching adaptation? Returns
    (per_jurisdiction, alignment). Alignment reports a correlation per hazard
    with the n it is based on, so small samples are read with caution.
    """
    a = _actions_enriched(meetings, actions)
    haz = a[a["action_category"].isin(["adaptation", "both"])].merge(
        exposure_df[["canonical_id", "county_fips"]], on="canonical_id", how="left"
    )
    mc = meetings.merge(exposure_df, on="canonical_id", how="left")
    mc = mc[mc["county_fips"].notna()]
    if mc.empty:
        return pd.DataFrame(), pd.DataFrame()

    agg = {"county_name": ("county_name", "first"),
           "meetings": ("canonical_id", "nunique")}
    for h in HAZARDS_FOR_EXPOSURE:
        agg[f"risk_{h}"] = (f"risk_{h}", "first")
    base = mc.groupby("county_fips").agg(**agg)

    for h in HAZARDS_FOR_EXPOSURE:
        cnt = haz[haz["hazard_type"] == h].groupby("county_fips").size().rename(f"act_{h}")
        base = base.join(cnt)
    base = base.fillna({f"act_{h}": 0 for h in HAZARDS_FOR_EXPOSURE}).reset_index()

    rows = []
    for h in HAZARDS_FOR_EXPOSURE:
        sub = base[[f"risk_{h}", f"act_{h}"]].dropna()
        corr = None
        if len(sub) >= 5 and sub[f"risk_{h}"].std() > 0 and sub[f"act_{h}"].std() > 0:
            corr = round(float(sub[f"risk_{h}"].corr(sub[f"act_{h}"])), 3)
        rows.append({
            "hazard": h,
            "n_jurisdictions": int(base[f"risk_{h}"].notna().sum()),
            "total_actions": int(base[f"act_{h}"].sum()),
            "pearson_r_risk_vs_action": corr,
        })
    return base, pd.DataFrame(rows)


def build_all(
    meetings: pd.DataFrame,
    actions: pd.DataFrame,
    exposure_df: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    tables = {
        "by_region": by_region(meetings, actions),
        "by_state": by_state(meetings, actions),
        "by_time": by_time(meetings, actions),
        "by_hazard": by_hazard(meetings, actions),
        "hazard_by_region": hazard_by_region(meetings, actions),
        "coverage": coverage(meetings),
    }
    if exposure_df is not None and not exposure_df.empty:
        per_juris, alignment = exposure_tables(meetings, actions, exposure_df)
        tables["exposure_jurisdictions"] = per_juris
        tables["exposure_alignment"] = alignment
    return tables
