"""State to Census region and division crosswalk.

Used to roll jurisdictions up to regions for the "varies by region" analysis.
Census regions are the standard the geospatial faculty will expect; divisions
are provided for a finer cut. No download needed, this is a fixed mapping.
"""

from __future__ import annotations

# state abbrev -> (region, division)
_STATE: dict[str, tuple[str, str]] = {
    "CT": ("Northeast", "New England"), "ME": ("Northeast", "New England"),
    "MA": ("Northeast", "New England"), "NH": ("Northeast", "New England"),
    "RI": ("Northeast", "New England"), "VT": ("Northeast", "New England"),
    "NJ": ("Northeast", "Middle Atlantic"), "NY": ("Northeast", "Middle Atlantic"),
    "PA": ("Northeast", "Middle Atlantic"),
    "IL": ("Midwest", "East North Central"), "IN": ("Midwest", "East North Central"),
    "MI": ("Midwest", "East North Central"), "OH": ("Midwest", "East North Central"),
    "WI": ("Midwest", "East North Central"),
    "IA": ("Midwest", "West North Central"), "KS": ("Midwest", "West North Central"),
    "MN": ("Midwest", "West North Central"), "MO": ("Midwest", "West North Central"),
    "NE": ("Midwest", "West North Central"), "ND": ("Midwest", "West North Central"),
    "SD": ("Midwest", "West North Central"),
    "DE": ("South", "South Atlantic"), "DC": ("South", "South Atlantic"),
    "FL": ("South", "South Atlantic"), "GA": ("South", "South Atlantic"),
    "MD": ("South", "South Atlantic"), "NC": ("South", "South Atlantic"),
    "SC": ("South", "South Atlantic"), "VA": ("South", "South Atlantic"),
    "WV": ("South", "South Atlantic"),
    "AL": ("South", "East South Central"), "KY": ("South", "East South Central"),
    "MS": ("South", "East South Central"), "TN": ("South", "East South Central"),
    "AR": ("South", "West South Central"), "LA": ("South", "West South Central"),
    "OK": ("South", "West South Central"), "TX": ("South", "West South Central"),
    "AZ": ("West", "Mountain"), "CO": ("West", "Mountain"), "ID": ("West", "Mountain"),
    "MT": ("West", "Mountain"), "NV": ("West", "Mountain"), "NM": ("West", "Mountain"),
    "UT": ("West", "Mountain"), "WY": ("West", "Mountain"),
    "AK": ("West", "Pacific"), "CA": ("West", "Pacific"), "HI": ("West", "Pacific"),
    "OR": ("West", "Pacific"), "WA": ("West", "Pacific"),
}


def region(state_abbrev: str) -> str:
    return _STATE.get((state_abbrev or "").upper(), ("Unknown", "Unknown"))[0]


def division(state_abbrev: str) -> str:
    return _STATE.get((state_abbrev or "").upper(), ("Unknown", "Unknown"))[1]
