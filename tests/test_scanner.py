# ABOUTME: Tests for project/session scanning in claude's storage directory.
# ABOUTME: Validates discovery of projects, sessions with subagents, and display name derivation.

import json
from pathlib import Path
from conftest import write_jsonl, write_json
from preprocessor.scanner import scan_projects, scan_archive, derive_display_name


def test_derive_display_name(tmp_path):
    """Project slug resolved via filesystem to human-readable path."""
    real_path = tmp_path / "Users" / "testuser" / "desert-island" / "phoenix"
    real_path.mkdir(parents=True)
    slug = "-" + str(tmp_path / "Users" / "testuser" / "desert-island" / "phoenix").replace("/", "-")
    result = derive_display_name(slug)
    assert result == "desert-island/phoenix"


def test_derive_display_name_fallback():
    """Unresolvable slug falls back to cleaned-up slug."""
    result = derive_display_name("-Users-nobody-nonexistent-path")
    assert isinstance(result, str)
    assert len(result) > 0


def test_scan_projects_finds_sessions_with_subagents(tmp_path):
    """Only sessions with subagents/ directories are discovered."""
    project_dir = tmp_path / "-Users-testuser-test-project"
    project_dir.mkdir()

    session_id = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
    session_dir = project_dir / session_id / "subagents"
    session_dir.mkdir(parents=True)
    write_jsonl(project_dir / f"{session_id}.jsonl", [{"type": "user", "message": {"role": "user", "content": "hi"}, "uuid": "u1", "timestamp": "2026-03-21T22:00:00Z", "sessionId": session_id}])

    write_jsonl(project_dir / "dddd-eeee.jsonl", [{"type": "user"}])

    (project_dir / "memory").mkdir()

    projects = scan_projects(tmp_path)
    assert len(projects) == 1
    assert projects[0]["slug"] == "-Users-testuser-test-project"
    assert len(projects[0]["sessions"]) == 1
    assert projects[0]["sessions"][0]["id"] == session_id


def test_scan_projects_empty_dir(tmp_path):
    """Empty source directory returns empty list."""
    projects = scan_projects(tmp_path)
    assert projects == []


def test_scan_projects_skips_non_project_dirs(tmp_path):
    """Non-project entries (files, non-slug dirs) are skipped."""
    (tmp_path / "some-file.txt").write_text("not a project")
    projects = scan_projects(tmp_path)
    assert projects == []


# --- Archive scanning tests ---


def _make_archive_project(tmp_path, slug, sessions):
    """Helper: create an archive-style flat project directory.

    sessions is a list of dicts with 'id' and 'agents' (list of agent dicts).
    Each agent dict has 'agentId' and optionally 'records' (list of JSONL records).
    """
    project_dir = tmp_path / slug
    project_dir.mkdir(parents=True, exist_ok=True)

    for session in sessions:
        sid = session["id"]
        # Main conversation JSONL
        main_records = session.get("main_records", [
            {
                "type": "assistant",
                "teamName": "meeting",
                "promptId": "prompt-111",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "hello"}]},
                "uuid": f"main-{sid[:8]}",
                "parentUuid": None,
                "timestamp": "2026-03-21T22:00:00Z",
                "sessionId": sid,
            }
        ])
        write_jsonl(project_dir / f"{sid}.jsonl", main_records)

        # Agent JSONL files (flat, at project root)
        for agent in session.get("agents", []):
            aid = agent["agentId"]
            records = agent.get("records", [
                {
                    "type": "user",
                    "promptId": "prompt-111",
                    "agentId": aid,
                    "message": {"role": "user", "content": "Do stuff"},
                    "uuid": f"{aid}-u1",
                    "parentUuid": None,
                    "isSidechain": True,
                    "timestamp": "2026-03-21T22:00:01Z",
                    "sessionId": sid,
                },
            ])
            write_jsonl(project_dir / f"agent-{aid}.jsonl", records)


def test_scan_archive_finds_sessions(tmp_path):
    """Archive scanner discovers sessions from flat UUID.jsonl files."""
    sid = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
    _make_archive_project(tmp_path, "-Users-test-myproject", [
        {"id": sid, "agents": [{"agentId": "a1"}, {"agentId": "a2"}]},
    ])

    projects = scan_archive(tmp_path)
    assert len(projects) == 1
    assert len(projects[0]["sessions"]) == 1

    session = projects[0]["sessions"][0]
    assert session["id"] == sid
    assert session["mainJsonl"] is not None
    assert len(session["agentJsonls"]) == 2


def test_scan_archive_groups_agents_by_session(tmp_path):
    """Agent files are grouped to the correct session by sessionId."""
    sid1 = "11111111-aaaa-bbbb-cccc-dddddddddddd"
    sid2 = "22222222-aaaa-bbbb-cccc-dddddddddddd"
    _make_archive_project(tmp_path, "-Users-test-project", [
        {"id": sid1, "agents": [{"agentId": "a1"}, {"agentId": "a2"}]},
        {"id": sid2, "agents": [{"agentId": "a3"}]},
    ])

    projects = scan_archive(tmp_path)
    sessions = {s["id"]: s for s in projects[0]["sessions"]}

    assert len(sessions[sid1]["agentJsonls"]) == 2
    assert len(sessions[sid2]["agentJsonls"]) == 1


def test_scan_archive_handles_session_with_no_agents(tmp_path):
    """Sessions with only a main JSONL and no agent files are still discovered."""
    sid = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
    _make_archive_project(tmp_path, "-Users-test-project", [
        {"id": sid, "agents": []},
    ])

    projects = scan_archive(tmp_path)
    session = projects[0]["sessions"][0]
    assert session["agentJsonls"] == []


def test_scan_archive_ignores_summary_files(tmp_path):
    """Summary .txt files in the archive are ignored."""
    sid = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
    _make_archive_project(tmp_path, "-Users-test-project", [
        {"id": sid, "agents": [{"agentId": "a1"}]},
    ])
    # Add a summary file that should be ignored
    (tmp_path / "-Users-test-project" / f"{sid}-summary.txt").write_text("AI summary")

    projects = scan_archive(tmp_path)
    assert len(projects[0]["sessions"]) == 1


def test_scan_archive_empty_dir(tmp_path):
    """Empty archive directory returns empty list."""
    projects = scan_archive(tmp_path)
    assert projects == []


def test_scan_archive_nonexistent_dir():
    """Nonexistent archive directory returns empty list."""
    projects = scan_archive(Path("/nonexistent/path"))
    assert projects == []
