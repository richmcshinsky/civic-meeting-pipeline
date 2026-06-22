"""Entity resolution and conflict detection.

Records sharing a canonical_id describe the same meeting. We link them and
pick a primary by source quality (full_text > summary > metadata_only), but
we never discard the linked records and we never silently merge conflicting
fields. Every input record produces a ProvenanceLink, so a merged output row
always traces back to its sources. Disagreements on descriptive fields go to
a ConflictRecord side table for manual review.

This is where the real overlap shows up: the same public meeting is often
captured by several videos in LocalView, and those collapse to one canonical
meeting here with their transcripts merged in order.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from yse_meetings.schema import (
    QUALITY_RANK,
    CanonicalMeetingRecord,
    ConflictRecord,
    ProvenanceLink,
)

# Descriptive fields that can legitimately differ between records of the same
# meeting (different spellings, different source conventions). The key fields
# (fips, date, type) are baked into canonical_id and cannot differ by design.
_CONFLICT_FIELDS = ("jurisdiction_name", "state")


def resolve(
    records: Iterable[CanonicalMeetingRecord],
) -> tuple[list[CanonicalMeetingRecord], list[ProvenanceLink], list[ConflictRecord]]:
    """Group by canonical_id, choose a primary, link the rest, flag conflicts.

    Returns (primary_records, provenance_links, conflicts).
    """
    groups: dict[str, list[CanonicalMeetingRecord]] = defaultdict(list)
    for rec in records:
        groups[rec.canonical_id].append(rec)

    primaries: list[CanonicalMeetingRecord] = []
    links: list[ProvenanceLink] = []
    conflicts: list[ConflictRecord] = []

    for canonical_id, members in groups.items():
        ranked = sorted(
            members,
            key=lambda r: (QUALITY_RANK[r.transcript_quality], len(r.transcript or "")),
            reverse=True,
        )
        primary = ranked[0]

        # Merge distinct transcripts in ranked order. Distinct so a true
        # duplicate is not repeated, while genuine multi-part videos are kept.
        seen: set[str] = set()
        parts: list[str] = []
        for r in ranked:
            text = (r.transcript or "").strip()
            if text and text not in seen:
                seen.add(text)
                parts.append(text)
        merged_transcript = "\n\n".join(parts) if parts else None

        merged = primary.model_copy(update={"transcript": merged_transcript})
        primaries.append(merged)

        for r in members:
            links.append(
                ProvenanceLink(
                    canonical_id=canonical_id,
                    source=r.source,
                    source_record_id=r.source_record_id,
                    source_url=r.source_url,
                    transcript_quality=r.transcript_quality,
                    is_primary=(r is primary),
                )
            )

        for field in _CONFLICT_FIELDS:
            primary_value = getattr(primary, field)
            for r in members:
                value = getattr(r, field)
                if value != primary_value:
                    conflicts.append(
                        ConflictRecord(
                            canonical_id=canonical_id,
                            field=field,
                            source_a=primary.source,
                            value_a=primary_value,
                            source_b=r.source,
                            value_b=value,
                        )
                    )

    return primaries, links, conflicts
