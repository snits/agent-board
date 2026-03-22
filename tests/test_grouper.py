# ABOUTME: Tests for grouping parsed records into meetings by promptId.
# ABOUTME: Validates promptId inheritance via parentUuid chains.

import pytest
from preprocessor.grouper import group_into_meetings, resolve_prompt_id


def test_resolve_prompt_id_direct():
    """Record with promptId returns it directly."""
    records_by_uuid = {
        "uuid-1": {"uuid": "uuid-1", "promptId": "prompt-A", "parentUuid": None}
    }
    assert resolve_prompt_id(records_by_uuid["uuid-1"], records_by_uuid) == "prompt-A"


def test_resolve_prompt_id_inherited():
    """Record without promptId inherits from parent."""
    records_by_uuid = {
        "uuid-1": {"uuid": "uuid-1", "promptId": "prompt-A", "parentUuid": None},
        "uuid-2": {"uuid": "uuid-2", "promptId": None, "parentUuid": "uuid-1"},
    }
    assert resolve_prompt_id(records_by_uuid["uuid-2"], records_by_uuid) == "prompt-A"


def test_resolve_prompt_id_chain():
    """Walks multiple levels of parentUuid."""
    records_by_uuid = {
        "uuid-1": {"uuid": "uuid-1", "promptId": "prompt-A", "parentUuid": None},
        "uuid-2": {"uuid": "uuid-2", "promptId": None, "parentUuid": "uuid-1"},
        "uuid-3": {"uuid": "uuid-3", "promptId": None, "parentUuid": "uuid-2"},
    }
    assert resolve_prompt_id(records_by_uuid["uuid-3"], records_by_uuid) == "prompt-A"


def test_resolve_prompt_id_orphan():
    """Record with no resolvable promptId returns None."""
    records_by_uuid = {
        "uuid-1": {"uuid": "uuid-1", "promptId": None, "parentUuid": None},
    }
    assert resolve_prompt_id(records_by_uuid["uuid-1"], records_by_uuid) is None


def test_group_into_meetings_basic():
    """Groups records by promptId into meetings."""
    records = [
        {"uuid": "u1", "promptId": "prompt-A", "parentUuid": None, "timestamp": "2026-03-21T22:00:00Z", "agentId": "a1", "role": "user", "content": "Hi", "toolUse": []},
        {"uuid": "u2", "promptId": None, "parentUuid": "u1", "timestamp": "2026-03-21T22:00:05Z", "agentId": "a1", "role": "assistant", "content": "Hello", "toolUse": []},
        {"uuid": "u3", "promptId": "prompt-B", "parentUuid": None, "timestamp": "2026-03-21T22:01:00Z", "agentId": "a2", "role": "user", "content": "Meeting 2", "toolUse": []},
    ]
    team_names = {"prompt-A": "design-meeting"}

    meetings = group_into_meetings(records, team_names)
    assert "prompt-A" in meetings
    assert "prompt-B" in meetings
    assert meetings["prompt-A"]["teamName"] == "design-meeting"
    assert meetings["prompt-B"]["teamName"] == "Unnamed Meeting"
    assert len(meetings["prompt-A"]["messages"]) == 2
    assert len(meetings["prompt-B"]["messages"]) == 1


def test_group_into_meetings_sorted_by_timestamp():
    """Messages within a meeting are sorted chronologically."""
    records = [
        {"uuid": "u2", "promptId": None, "parentUuid": "u1", "timestamp": "2026-03-21T22:00:10Z", "agentId": "a1", "role": "assistant", "content": "Second", "toolUse": []},
        {"uuid": "u1", "promptId": "prompt-A", "parentUuid": None, "timestamp": "2026-03-21T22:00:01Z", "agentId": "a1", "role": "user", "content": "First", "toolUse": []},
    ]
    meetings = group_into_meetings(records, {})
    msgs = meetings["prompt-A"]["messages"]
    assert msgs[0]["content"] == "First"
    assert msgs[1]["content"] == "Second"
