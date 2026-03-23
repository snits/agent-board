# ABOUTME: Tests for flattening parsed records into a sorted message list.
# ABOUTME: Validates promptId inheritance via parentUuid chains.

import pytest
from preprocessor.grouper import flatten_messages, resolve_prompt_id


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


def test_flatten_messages_basic():
    """Returns flat sorted list with teamName on each message."""
    records = [
        {"uuid": "u1", "promptId": "prompt-A", "parentUuid": None, "timestamp": "2026-03-21T22:00:00Z", "agentId": "a1", "role": "user", "content": "Hi", "toolUse": []},
        {"uuid": "u2", "promptId": None, "parentUuid": "u1", "timestamp": "2026-03-21T22:00:05Z", "agentId": "a1", "role": "assistant", "content": "Hello", "toolUse": []},
        {"uuid": "u3", "promptId": "prompt-B", "parentUuid": None, "timestamp": "2026-03-21T22:01:00Z", "agentId": "a2", "role": "user", "content": "Meeting 2", "toolUse": []},
    ]
    team_names = {"prompt-A": "design-meeting"}

    result = flatten_messages(records, team_names)
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]["content"] == "Hi"
    assert result[1]["content"] == "Hello"
    assert result[2]["content"] == "Meeting 2"
    assert result[0]["teamName"] == "design-meeting"
    assert result[1]["teamName"] == "design-meeting"
    assert result[2]["teamName"] == "Unnamed Meeting"


def test_flatten_messages_sorted_by_timestamp():
    """Messages are sorted chronologically regardless of input order."""
    records = [
        {"uuid": "u2", "promptId": None, "parentUuid": "u1", "timestamp": "2026-03-21T22:00:10Z", "agentId": "a1", "role": "assistant", "content": "Second", "toolUse": []},
        {"uuid": "u1", "promptId": "prompt-A", "parentUuid": None, "timestamp": "2026-03-21T22:00:01Z", "agentId": "a1", "role": "user", "content": "First", "toolUse": []},
    ]
    result = flatten_messages(records, {})
    assert result[0]["content"] == "First"
    assert result[1]["content"] == "Second"


def test_flatten_messages_labels_orphans_as_main_conversation():
    """Records with no resolvable promptId get 'Main Conversation' teamName."""
    records = [
        {"uuid": "u1", "promptId": None, "parentUuid": None, "timestamp": "2026-03-21T22:00:00Z", "agentId": "a1", "role": "user", "content": "Orphan", "toolUse": []},
        {"uuid": "u2", "promptId": "prompt-A", "parentUuid": None, "timestamp": "2026-03-21T22:00:01Z", "agentId": "a1", "role": "user", "content": "Has prompt", "toolUse": []},
    ]
    result = flatten_messages(records, {})
    assert len(result) == 2
    orphan = next(r for r in result if r["content"] == "Orphan")
    assert orphan["teamName"] == "Main Conversation"


def test_flatten_messages_handles_none_timestamps():
    """Records with timestamp=None should sort without crashing."""
    records = [
        {"uuid": "u1", "promptId": "prompt-A", "parentUuid": None, "timestamp": None, "agentId": "a1", "role": "user", "content": "No timestamp", "toolUse": []},
        {"uuid": "u2", "promptId": "prompt-A", "parentUuid": None, "timestamp": "2026-03-21T22:00:00Z", "agentId": "a1", "role": "assistant", "content": "Has timestamp", "toolUse": []},
    ]
    result = flatten_messages(records, {})
    assert len(result) == 2
    # Record with None timestamp should sort before the timestamped one
    assert result[0]["content"] == "No timestamp"
    assert result[1]["content"] == "Has timestamp"
