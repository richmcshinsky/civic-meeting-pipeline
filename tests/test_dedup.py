"""Critical tests for entity resolution.

Three behaviors that matter: records link rather than collapse, the
higher-quality source becomes the primary, and a descriptive disagreement is
flagged to the conflict side table.
"""

from datetime import date

from yse_meetings.dedup.entity_resolution import resolve
from yse_meetings.schema import CanonicalMeetingRecord, make_canonical_id


def _record(source, source_id, quality, transcript, name="Seattle", state="WA"):
    fips = "5363000"
    d = date(2021, 5, 4)
    return CanonicalMeetingRecord(
        canonical_id=make_canonical_id(fips, d, "council_full"),
        jurisdiction_name=name,
        jurisdiction_fips=fips,
        state=state,
        meeting_date=d,
        meeting_type="council_full",
        transcript=transcript,
        transcript_quality=quality,
        source=source,
        source_url=f"https://example.org/{source_id}",
        source_record_id=source_id,
    )


def test_records_link_not_collapse():
    # Two records of the same meeting collapse to one primary, but both are
    # preserved as provenance links.
    a = _record("localview", "vid_part1", "full_text", "part one text")
    b = _record("localview", "vid_part2", "full_text", "part two text")
    primaries, links, conflicts = resolve([a, b])

    assert len(primaries) == 1
    assert len(links) == 2
    assert {link.source_record_id for link in links} == {"vid_part1", "vid_part2"}
    # Distinct part transcripts are merged, not dropped.
    assert "part one text" in primaries[0].transcript
    assert "part two text" in primaries[0].transcript


def test_higher_quality_source_wins_primary():
    weak = _record("localview", "meta_only", "metadata_only", None)
    strong = _record("meetingbank", "full", "full_text", "the real transcript")
    primaries, links, _ = resolve([weak, strong])

    assert len(primaries) == 1
    primary_links = [link for link in links if link.is_primary]
    assert len(primary_links) == 1
    assert primary_links[0].source_record_id == "full"


def test_field_disagreement_flags_conflict():
    a = _record("meetingbank", "a", "full_text", "text", name="Seattle")
    b = _record("localview", "b", "full_text", "text", name="Seattle City")
    _, _, conflicts = resolve([a, b])

    assert any(c.field == "jurisdiction_name" for c in conflicts)
    conflict = next(c for c in conflicts if c.field == "jurisdiction_name")
    assert {conflict.value_a, conflict.value_b} == {"Seattle", "Seattle City"}
