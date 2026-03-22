# ABOUTME: Shared test fixtures for TUI tests.
# ABOUTME: Provides sample JSON data matching the preprocessor output format.

import json
from pathlib import Path

import pytest


@pytest.fixture
def sample_index():
    """Matches the structure of data/index.json."""
    return {
        "projects": [
            {
                "slug": "-Users-test-project-alpha",
                "displayName": "project/alpha",
                "sessions": [
                    {
                        "id": "sess-001",
                        "startTime": "2026-03-20T10:00:00.000Z",
                        "endTime": "2026-03-20T11:00:00.000Z",
                        "meetingCount": 2,
                        "agentCount": 3,
                    }
                ],
            },
            {
                "slug": "-Users-test-project-beta",
                "displayName": "project/beta",
                "sessions": [
                    {
                        "id": "sess-002",
                        "startTime": "2026-03-21T14:00:00.000Z",
                        "endTime": "2026-03-21T15:00:00.000Z",
                        "meetingCount": 1,
                        "agentCount": 2,
                    }
                ],
            },
        ]
    }


@pytest.fixture
def sample_agent_types():
    """Matches the structure of data/agent-types.json."""
    return {
        "web-search-researcher": {
            "color": "#DCBEFF",
            "label": "Web Search Researcher",
        },
        "general-purpose": {
            "color": "#FFFAC8",
            "label": "General Purpose",
        },
        "code-reviewer": {
            "color": "#ADB8FF",
            "label": "Code Reviewer",
        },
    }


@pytest.fixture
def sample_session():
    """Matches the structure of data/sessions/{id}/session.json."""
    return {
        "id": "sess-001",
        "startTime": "2026-03-20T10:00:00.000Z",
        "endTime": "2026-03-20T11:00:00.000Z",
        "meetingCount": 2,
        "agentCount": 3,
        "meetings": [
            {
                "id": "mtg-001",
                "teamName": "Research Team",
                "startTime": "2026-03-20T10:00:00.000Z",
                "endTime": "2026-03-20T10:30:00.000Z",
                "agentCount": 2,
                "messageCount": 5,
            },
            {
                "id": "mtg-002",
                "teamName": "Review Team",
                "startTime": "2026-03-20T10:30:00.000Z",
                "endTime": "2026-03-20T11:00:00.000Z",
                "agentCount": 1,
                "messageCount": 3,
            },
        ],
    }


@pytest.fixture
def sample_meeting():
    """Matches the structure of data/sessions/{sid}/meetings/{mid}.json."""
    return {
        "id": "mtg-001",
        "teamName": "Research Team",
        "startTime": "2026-03-20T10:00:00.000Z",
        "endTime": "2026-03-20T10:30:00.000Z",
        "agents": [
            {
                "agentId": "agent-aaa",
                "type": "web-search-researcher",
                "messageCount": 3,
            },
            {
                "agentId": "agent-bbb",
                "type": "general-purpose",
                "messageCount": 2,
            },
        ],
        "messages": [
            {
                "uuid": "msg-001",
                "parentUuid": None,
                "agentId": "agent-aaa",
                "role": "user",
                "content": "Research the Textual TUI framework.",
                "toolUse": [],
                "timestamp": "2026-03-20T10:00:00.000Z",
                "promptId": "mtg-001",
                "agentType": "web-search-researcher",
            },
            {
                "uuid": "msg-002",
                "parentUuid": "msg-001",
                "agentId": "agent-aaa",
                "role": "assistant",
                "content": "I'll look into the Textual framework documentation.",
                "toolUse": [
                    {
                        "tool": "WebFetch",
                        "input": {"url": "https://textual.textualize.io/"},
                        "summary": "WebFetch → textual.textualize.io",
                    }
                ],
                "timestamp": "2026-03-20T10:01:00.000Z",
                "promptId": "mtg-001",
                "agentType": "web-search-researcher",
            },
            {
                "uuid": "msg-003",
                "parentUuid": "msg-002",
                "agentId": "agent-aaa",
                "role": "assistant",
                "content": "Here's what I found:\n\n## Textual Overview\n\n- Modern TUI framework\n- Built on **Rich**\n- Supports CSS styling\n\n```python\nfrom textual.app import App\n```",
                "toolUse": [],
                "timestamp": "2026-03-20T10:02:00.000Z",
                "promptId": "mtg-001",
                "agentType": "web-search-researcher",
            },
            {
                "uuid": "msg-004",
                "parentUuid": None,
                "agentId": "agent-bbb",
                "role": "user",
                "content": "Summarize the research findings.",
                "toolUse": [],
                "timestamp": "2026-03-20T10:03:00.000Z",
                "promptId": "mtg-001",
                "agentType": "general-purpose",
            },
            {
                "uuid": "msg-005",
                "parentUuid": "msg-004",
                "agentId": "agent-bbb",
                "role": "assistant",
                "content": "Based on the research, Textual is the recommended choice.",
                "toolUse": [
                    {
                        "tool": "Read",
                        "input": {"file_path": "/tmp/notes.md"},
                        "summary": "Read → /tmp/notes.md",
                    }
                ],
                "timestamp": "2026-03-20T10:04:00.000Z",
                "promptId": "mtg-001",
                "agentType": "general-purpose",
            },
        ],
    }


@pytest.fixture
def sample_empty_meeting():
    """A meeting with messages that should be filtered out."""
    return {
        "id": "mtg-empty",
        "teamName": "Empty Test",
        "startTime": "2026-03-20T10:00:00.000Z",
        "endTime": "2026-03-20T10:05:00.000Z",
        "agents": [{"agentId": "agent-aaa", "type": "general-purpose", "messageCount": 1}],
        "messages": [
            {
                "uuid": "msg-e1",
                "parentUuid": None,
                "agentId": "agent-aaa",
                "role": "assistant",
                "content": "",
                "toolUse": [],
                "timestamp": "2026-03-20T10:00:00.000Z",
                "promptId": "mtg-empty",
                "agentType": "general-purpose",
            },
            {
                "uuid": "msg-e2",
                "parentUuid": None,
                "agentId": "agent-aaa",
                "role": "assistant",
                "content": "This message has content.",
                "toolUse": [],
                "timestamp": "2026-03-20T10:01:00.000Z",
                "promptId": "mtg-empty",
                "agentType": "general-purpose",
            },
        ],
    }


@pytest.fixture
def data_dir(tmp_path, sample_index, sample_agent_types, sample_session, sample_meeting):
    """Create a complete data directory matching the preprocessor output structure."""
    # Write index.json
    (tmp_path / "index.json").write_text(json.dumps(sample_index))

    # Write agent-types.json
    (tmp_path / "agent-types.json").write_text(json.dumps(sample_agent_types))

    # Write session and meeting files
    session_dir = tmp_path / "sessions" / "sess-001"
    meetings_dir = session_dir / "meetings"
    meetings_dir.mkdir(parents=True)

    (session_dir / "session.json").write_text(json.dumps(sample_session))
    (meetings_dir / "mtg-001.json").write_text(json.dumps(sample_meeting))

    return tmp_path
