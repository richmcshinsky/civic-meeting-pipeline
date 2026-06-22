"""Critical tests for extraction.

We test the response parser, which is deterministic, rather than the model
call, which is not. The parser is the part that has to be robust: it must
accept well-formed output, reject non-JSON, and drop malformed items without
failing the whole meeting.
"""

import pytest

from yse_meetings.extract.llm_extractor import parse_actions


def test_valid_output_parses_adaptation():
    raw = (
        '{"actions": [{"action_text": "build a sea wall along the marina",'
        ' "action_category": "adaptation", "hazard_type": "sea_level_rise",'
        ' "confidence": 0.88}]}'
    )
    actions = parse_actions(raw, canonical_id="abc123", version="ollama:llama3.1:8b")
    assert len(actions) == 1
    assert actions[0].action_category == "adaptation"
    assert actions[0].hazard_type == "sea_level_rise"
    assert actions[0].canonical_id == "abc123"
    assert 0.0 <= actions[0].confidence <= 1.0


def test_empty_actions_list_is_fine():
    actions = parse_actions('{"actions": []}', canonical_id="x", version="v")
    assert actions == []


def test_non_json_raises():
    with pytest.raises(ValueError):
        parse_actions("the model rambled instead of returning json", "x", "v")


def test_malformed_items_are_dropped():
    # Bad category, missing text, and out-of-range confidence handled.
    raw = (
        '{"actions": ['
        '{"action_text": "", "action_category": "adaptation", "confidence": 0.5},'
        '{"action_text": "ban gas hookups", "action_category": "not_a_category"},'
        '{"action_text": "fund transit", "action_category": "mitigation",'
        ' "hazard_type": "bogus", "confidence": 5}'
        ']}'
    )
    actions = parse_actions(raw, "x", "v")
    assert len(actions) == 1
    assert actions[0].action_category == "mitigation"
    assert actions[0].hazard_type is None  # invalid hazard coerced to None
    assert actions[0].confidence == 1.0  # clamped into range
