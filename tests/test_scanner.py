# ABOUTME: Tests for project/session scanning in claude's storage directory.
# ABOUTME: Validates discovery of projects, sessions with subagents, and display name derivation.

import json
from pathlib import Path
from tests.conftest import write_jsonl, write_json
from preprocessor.scanner import scan_projects, derive_display_name


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
    project_dir = tmp_path / "-Users-jsnitsel-test-project"
    project_dir.mkdir()

    session_id = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
    session_dir = project_dir / session_id / "subagents"
    session_dir.mkdir(parents=True)
    write_jsonl(project_dir / f"{session_id}.jsonl", [{"type": "user", "message": {"role": "user", "content": "hi"}, "uuid": "u1", "timestamp": "2026-03-21T22:00:00Z", "sessionId": session_id}])

    write_jsonl(project_dir / "dddd-eeee.jsonl", [{"type": "user"}])

    (project_dir / "memory").mkdir()

    projects = scan_projects(tmp_path)
    assert len(projects) == 1
    assert projects[0]["slug"] == "-Users-jsnitsel-test-project"
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
