# ABOUTME: Tests for writing processed session data to JSON output files.
# ABOUTME: Validates file structure, agent-types generation, and index creation.

import json
import shutil
from pathlib import Path
from preprocessor.writer import write_session, write_index, generate_agent_types


def test_generate_agent_types_known():
    """Known agent types get predefined colors."""
    types = generate_agent_types({"strategist", "engine-arch"})
    assert types["strategist"]["color"] == "#4A90D9"
    assert types["strategist"]["label"] == "Strategist"
    assert types["engine-arch"]["color"] == "#50C878"


def test_generate_agent_types_unknown():
    """Unknown agent types get a deterministic color."""
    types = generate_agent_types({"mystery-agent"})
    assert "mystery-agent" in types
    assert types["mystery-agent"]["color"].startswith("#")
    assert types["mystery-agent"]["label"] == "Mystery Agent"
    types2 = generate_agent_types({"mystery-agent"})
    assert types["mystery-agent"]["color"] == types2["mystery-agent"]["color"]


def test_write_session_creates_messages_file(tmp_path):
    """Writing a session creates a single messages.json with all messages."""
    session_info = {
        "id": "session-123",
        "messages": [
            {"uuid": "u1", "agentId": "a1", "role": "assistant", "content": "Hello",
             "toolUse": [], "timestamp": "2026-03-21T22:00:01Z", "teamName": "design-meeting"},
            {"uuid": "u2", "agentId": "a2", "role": "user", "content": "Hi",
             "toolUse": [], "timestamp": "2026-03-21T22:00:05Z", "teamName": "design-meeting"},
        ],
        "agentMeta": {"a1": {"agentType": "strategist"}, "a2": {"agentType": "general-purpose"}},
    }

    write_session(tmp_path, session_info)

    messages_file = tmp_path / "sessions" / "session-123" / "messages.json"
    meetings_dir = tmp_path / "sessions" / "session-123" / "meetings"
    assert messages_file.exists()
    assert not meetings_dir.exists()

    data = json.loads(messages_file.read_text())
    assert len(data) == 2
    assert data[0]["agentType"] == "strategist"
    assert data[1]["agentType"] == "general-purpose"


def test_write_session_creates_session_json_with_agents(tmp_path):
    """session.json includes agents roster at session level."""
    session_info = {
        "id": "session-123",
        "messages": [
            {"uuid": "u1", "agentId": "a1", "role": "assistant", "content": "Hello",
             "toolUse": [], "timestamp": "2026-03-21T22:00:01Z", "teamName": "design"},
            {"uuid": "u2", "agentId": "a1", "role": "assistant", "content": "More",
             "toolUse": [], "timestamp": "2026-03-21T22:00:05Z", "teamName": "design"},
        ],
        "agentMeta": {"a1": {"agentType": "strategist"}},
    }

    write_session(tmp_path, session_info)

    session_file = tmp_path / "sessions" / "session-123" / "session.json"
    session_data = json.loads(session_file.read_text())
    assert "meetings" not in session_data
    assert "agents" in session_data
    assert len(session_data["agents"]) == 1
    assert session_data["agents"][0]["type"] == "strategist"
    assert session_data["agents"][0]["messageCount"] == 2
    assert session_data["messageCount"] == 2


def test_write_session_cleans_stale_meetings_dir(tmp_path):
    """Re-running write_session removes old meetings/ directory."""
    session_dir = tmp_path / "sessions" / "session-123"
    meetings_dir = session_dir / "meetings"
    meetings_dir.mkdir(parents=True)
    (meetings_dir / "old-meeting.json").write_text("{}")

    session_info = {
        "id": "session-123",
        "messages": [],
        "agentMeta": {},
    }
    write_session(tmp_path, session_info)

    assert not meetings_dir.exists()


def test_write_index(tmp_path):
    """Index file contains project and session info without meetingCount."""
    projects = [
        {
            "slug": "-Users-test-project",
            "displayName": "test-project",
            "sessions": [
                {"id": "s1", "agentCount": 20, "startTime": "2026-03-21T22:00:00Z", "endTime": "2026-03-21T23:00:00Z"}
            ]
        }
    ]
    write_index(tmp_path, projects)

    index_file = tmp_path / "index.json"
    data = json.loads(index_file.read_text())
    assert len(data["projects"]) == 1
    assert "meetingCount" not in data["projects"][0]["sessions"][0]
