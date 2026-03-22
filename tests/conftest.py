# ABOUTME: Shared pytest fixtures for preprocessor tests.
# ABOUTME: Provides sample JSONL records and temporary directory helpers.

import json
import os
import pytest
from pathlib import Path


@pytest.fixture
def tmp_output(tmp_path):
    """Temporary directory for preprocessor output."""
    return tmp_path / "output"


@pytest.fixture
def sample_user_record():
    """A user-type agent record with a teammate-message and promptId."""
    return {
        "parentUuid": None,
        "isSidechain": True,
        "promptId": "prompt-aaa",
        "agentId": "agent-001",
        "type": "user",
        "message": {
            "role": "user",
            "content": '<teammate-message teammate_id="team-lead" summary="Design meeting: strategist">\nYou are in a design meeting.\n</teammate-message>'
        },
        "uuid": "uuid-001",
        "timestamp": "2026-03-21T22:10:10.000Z",
        "sessionId": "session-aaa",
        "userType": "external",
        "entrypoint": "cli",
        "cwd": "/some/path",
        "version": "2.1.81"
    }


@pytest.fixture
def sample_assistant_text_record():
    """An assistant record with text content (no promptId — must inherit via parentUuid)."""
    return {
        "parentUuid": "uuid-001",
        "isSidechain": True,
        "agentId": "agent-001",
        "message": {
            "model": "claude-opus-4-6",
            "id": "msg_001",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Here is my analysis of the design."}],
            "stop_reason": None,
            "usage": {"input_tokens": 100, "output_tokens": 50}
        },
        "requestId": "req_001",
        "type": "assistant",
        "uuid": "uuid-002",
        "timestamp": "2026-03-21T22:10:15.000Z",
        "sessionId": "session-aaa"
    }


@pytest.fixture
def sample_assistant_tooluse_record():
    """An assistant record with tool_use content."""
    return {
        "parentUuid": "uuid-002",
        "isSidechain": True,
        "agentId": "agent-001",
        "message": {
            "model": "claude-opus-4-6",
            "id": "msg_001",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_001",
                    "name": "Read",
                    "input": {"file_path": "/path/to/file.md"},
                    "caller": {"type": "direct"}
                }
            ],
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 100, "output_tokens": 80}
        },
        "requestId": "req_001",
        "type": "assistant",
        "uuid": "uuid-003",
        "timestamp": "2026-03-21T22:10:16.000Z",
        "sessionId": "session-aaa"
    }


@pytest.fixture
def sample_assistant_mixed_record():
    """An assistant record with both text and tool_use content blocks."""
    return {
        "parentUuid": "uuid-001",
        "isSidechain": True,
        "agentId": "agent-001",
        "message": {
            "model": "claude-opus-4-6",
            "id": "msg_002",
            "type": "message",
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Let me read that file."},
                {
                    "type": "tool_use",
                    "id": "toolu_002",
                    "name": "Read",
                    "input": {"file_path": "/path/to/file.md"},
                    "caller": {"type": "direct"}
                }
            ],
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 100, "output_tokens": 80}
        },
        "requestId": "req_002",
        "type": "assistant",
        "uuid": "uuid-004",
        "timestamp": "2026-03-21T22:10:17.000Z",
        "sessionId": "session-aaa"
    }


@pytest.fixture
def sample_progress_record():
    """A progress record (should be skipped)."""
    return {
        "parentUuid": "uuid-002",
        "isSidechain": True,
        "promptId": None,
        "type": "progress",
        "uuid": "uuid-005",
        "timestamp": "2026-03-21T22:10:15.500Z",
        "sessionId": "session-aaa"
    }


@pytest.fixture
def sample_meta_json():
    """Agent metadata."""
    return {"agentType": "strategist"}


@pytest.fixture
def sample_meta_json_with_desc():
    """Agent metadata with description."""
    return {"agentType": "game-design-reviewer", "description": "Review design doc: find flaws"}


@pytest.fixture
def sample_main_conversation_records():
    """Records from the main conversation JSONL that contain teamName."""
    return [
        {
            "parentUuid": "main-uuid-001",
            "isSidechain": False,
            "teamName": "design-meeting",
            "promptId": "prompt-aaa",
            "type": "user",
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]},
            "uuid": "main-uuid-002",
            "timestamp": "2026-03-21T22:09:47.000Z",
            "sessionId": "session-aaa"
        },
        {
            "parentUuid": "main-uuid-010",
            "isSidechain": False,
            "teamName": "galaxy-map-meeting",
            "promptId": "prompt-bbb",
            "type": "assistant",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "Spawning agents..."}]},
            "uuid": "main-uuid-011",
            "timestamp": "2026-03-21T23:00:00.000Z",
            "sessionId": "session-aaa"
        }
    ]


def write_jsonl(path, records):
    """Helper to write a list of dicts as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


def write_json(path, data):
    """Helper to write a dict as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)
