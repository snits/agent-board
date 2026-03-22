# ABOUTME: Tests for writing processed meeting data to JSON output files.
# ABOUTME: Validates file structure, agent-types generation, and index creation.

import json
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


def test_write_session_creates_meeting_files(tmp_path):
    """Writing a session creates per-meeting JSON files."""
    session_info = {
        "id": "session-123",
        "meetings": {
            "prompt-A": {
                "id": "prompt-A",
                "teamName": "design-meeting",
                "startTime": "2026-03-21T22:00:00Z",
                "endTime": "2026-03-21T22:15:00Z",
                "agentIds": ["a1"],
                "messages": [
                    {"uuid": "u1", "agentId": "a1", "agentType": "strategist", "role": "assistant", "content": "Hello", "toolUse": [], "timestamp": "2026-03-21T22:00:01Z"}
                ],
            }
        },
        "agentMeta": {"a1": {"agentType": "strategist"}},
    }

    write_session(tmp_path, session_info)

    meeting_file = tmp_path / "sessions" / "session-123" / "meetings" / "prompt-A.json"
    assert meeting_file.exists()
    data = json.loads(meeting_file.read_text())
    assert data["teamName"] == "design-meeting"
    assert len(data["messages"]) == 1

    session_file = tmp_path / "sessions" / "session-123" / "session.json"
    session_data = json.loads(session_file.read_text())
    assert "meetings" in session_data
    assert len(session_data["meetings"]) == 1
    assert session_data["meetings"][0]["id"] == "prompt-A"
    assert session_data["meetings"][0]["teamName"] == "design-meeting"
    assert session_data["meetings"][0]["agentCount"] == 1
    assert session_data["meetings"][0]["messageCount"] == 1


def test_write_index(tmp_path):
    """Index file contains project and session info."""
    projects = [
        {
            "slug": "-Users-test-project",
            "displayName": "test-project",
            "sessions": [
                {"id": "s1", "meetingCount": 5, "agentCount": 20, "startTime": "2026-03-21T22:00:00Z", "endTime": "2026-03-21T23:00:00Z"}
            ]
        }
    ]
    write_index(tmp_path, projects)

    index_file = tmp_path / "index.json"
    assert index_file.exists()
    data = json.loads(index_file.read_text())
    assert len(data["projects"]) == 1
    assert data["projects"][0]["sessions"][0]["meetingCount"] == 5
