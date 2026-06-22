"""Canonical data models shared across all sources.

Every source adapter normalizes its records into CanonicalMeetingRecord.
The extraction stage produces ExtractedAction rows keyed back to the
canonical record. ConflictRecord is the side table we use when two
sources disagree about the same meeting. We link records, we do not
silently collapse them, so every output row traces back to source data.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

MeetingType = Literal[
    "council_full",
    "committee",
    "special",
    "workshop",
    "executive",
    "other",
]

TranscriptQuality = Literal["full_text", "summary", "metadata_only"]

Source = Literal["meetingbank", "localview"]

ActionCategory = Literal["adaptation", "mitigation", "both", "unrelated"]

HazardType = Literal[
    "flood",
    "wildfire",
    "heat",
    "drought",
    "storm",
    "sea_level_rise",
    "other",
    "none",
]

# Source quality ranking used by entity resolution. Higher wins when two
# records describe the same meeting. Kept here so ingest, dedup, and the
# app all read the same ordering.
QUALITY_RANK: dict[str, int] = {
    "full_text": 3,
    "summary": 2,
    "metadata_only": 1,
}


def make_canonical_id(jurisdiction_fips: str, meeting_date: date, meeting_type: str) -> str:
    """Deterministic id for a meeting.

    The key is (jurisdiction_fips, meeting_date, meeting_type). Two records
    from different sources that share this key are treated as the same
    real-world meeting and linked.
    """
    raw = f"{jurisdiction_fips}|{meeting_date.isoformat()}|{meeting_type}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


class CanonicalMeetingRecord(BaseModel):
    """One meeting, normalized into a single shape across sources."""

    canonical_id: str
    jurisdiction_name: str
    jurisdiction_fips: str  # 7-digit place FIPS preferred, 5-digit county fallback
    state: str  # 2-letter postal code
    meeting_date: date
    meeting_type: MeetingType
    transcript: Optional[str] = None
    transcript_quality: TranscriptQuality
    source: Source
    source_url: str
    source_record_id: str
    ingested_at: datetime = Field(default_factory=datetime.utcnow)


class ExtractedAction(BaseModel):
    """One climate action extracted from a meeting transcript."""

    canonical_id: str
    action_text: str  # verbatim excerpt from the transcript
    action_category: ActionCategory
    hazard_type: Optional[HazardType] = None
    confidence: float = Field(ge=0.0, le=1.0)
    model_version: str
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


class ProvenanceLink(BaseModel):
    """One source record that contributed to a canonical meeting.

    Dedup links records, it does not delete them. Every input record gets a
    ProvenanceLink so any merged output row traces back to all of its sources.
    """

    canonical_id: str
    source: Source
    source_record_id: str
    source_url: str
    transcript_quality: TranscriptQuality
    is_primary: bool


class ConflictRecord(BaseModel):
    """A flagged disagreement between two source records sharing a canonical_id.

    We keep these in a side table for manual review rather than guessing.
    field is the attribute that disagreed, for example jurisdiction_name or
    meeting_type.
    """

    canonical_id: str
    field: str
    source_a: Source
    value_a: str
    source_b: Source
    value_b: str
    resolved_value: Optional[str] = None
    note: Optional[str] = None
