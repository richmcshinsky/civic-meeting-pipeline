"""Jurisdiction resolution: map a free-text jurisdiction name to a FIPS code.

Strategy (Phase 3): exact match on (name, state) against the committed FIPS
crosswalk first, then a rapidfuzz fuzzy match constrained to the same state.
The state constraint keeps "Springfield" in Illinois from matching
"Springfield" in Missouri. rapidfuzz only, no heavier dedup library.
"""

from __future__ import annotations

from pathlib import Path

import rapidfuzz

from yse_meetings.config import FIPS_CROSSWALK


class JurisdictionResolver:
    def __init__(self, crosswalk_path: Path = FIPS_CROSSWALK) -> None:
        self.crosswalk_path = crosswalk_path
        # Loaded lazily in Phase 3.

    def resolve(self, name: str, state: str) -> str | None:
        """Return a FIPS code for (name, state), or None if no confident match."""
        raise NotImplementedError("Phase 3: jurisdiction resolution.")
