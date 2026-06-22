"""Tests for the canonical schema and id construction."""

from datetime import date

from yse_meetings.schema import (
    CanonicalMeetingRecord,
    ExtractedAction,
    make_canonical_id,
)


def test_canonical_id_is_deterministic():
    a = make_canonical_id("0820000", date(2021, 5, 3), "council_full")
    b = make_canonical_id("0820000", date(2021, 5, 3), "council_full")
    assert a == b


def test_canonical_id_differs_on_inputs():
    a = make_canonical_id("0820000", date(2021, 5, 3), "council_full")
    b = make_canonical_id("0820000", date(2021, 5, 3), "committee")
    assert a != b


def test_record_round_trips():
    rec = CanonicalMeetingRecord(
        canonical_id=make_canonical_id("5363000", date(2020, 1, 6), "council_full"),
        jurisdiction_name="Seattle",
        jurisdiction_fips="5363000",
        state="WA",
        meeting_date=date(2020, 1, 6),
        meeting_type="council_full",
        transcript="example transcript text",
        transcript_quality="full_text",
        source="meetingbank",
        source_url="https://meetingbank.github.io/",
        source_record_id="seattle_2020_01_06",
    )
    assert rec.transcript_quality == "full_text"


def test_extracted_action_confidence_bounds():
    action = ExtractedAction(
        canonical_id="abc123",
        action_text="adopt a heat action plan",
        action_category="adaptation",
        hazard_type="heat",
        confidence=0.82,
        model_version="v0.1",
    )
    assert 0.0 <= action.confidence <= 1.0
