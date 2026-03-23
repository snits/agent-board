# ABOUTME: Integration tests for the full preprocessing pipeline.
# ABOUTME: Creates a realistic directory structure and validates end-to-end output.

import json
from pathlib import Path
from conftest import write_jsonl, write_json


def test_full_pipeline(tmp_path):
    """End-to-end: source directory → preprocessed output."""
    from preprocessor.pipeline import run_preprocess

    # Create source structure
    project_dir = tmp_path / "source" / "-Users-test-myproject"
    session_id = "aabbccdd-eeff-0011-2233-445566778899"
    subagents_dir = project_dir / session_id / "subagents"
    subagents_dir.mkdir(parents=True)

    # Main conversation with teamName mapping
    write_jsonl(project_dir / f"{session_id}.jsonl", [
        {
            "type": "assistant",
            "teamName": "design-meeting",
            "promptId": "prompt-111",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "spawning"}]},
            "uuid": "main-u1",
            "parentUuid": None,
            "timestamp": "2026-03-21T22:00:00Z",
            "sessionId": session_id,
        }
    ])

    # Agent meta
    write_json(subagents_dir / "agent-a1.meta.json", {"agentType": "strategist"})
    write_json(subagents_dir / "agent-a2.meta.json", {"agentType": "engine-arch"})

    # Agent transcripts
    write_jsonl(subagents_dir / "agent-a1.jsonl", [
        {
            "type": "user",
            "promptId": "prompt-111",
            "agentId": "a1",
            "message": {"role": "user", "content": '<teammate-message teammate_id="team-lead" summary="task">\nDo the analysis.\n</teammate-message>'},
            "uuid": "a1-u1",
            "parentUuid": None,
            "isSidechain": True,
            "timestamp": "2026-03-21T22:00:01Z",
            "sessionId": session_id,
        },
        {
            "type": "assistant",
            "agentId": "a1",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "Here is my analysis."}]},
            "uuid": "a1-u2",
            "parentUuid": "a1-u1",
            "isSidechain": True,
            "timestamp": "2026-03-21T22:00:10Z",
            "sessionId": session_id,
        },
    ])

    write_jsonl(subagents_dir / "agent-a2.jsonl", [
        {
            "type": "user",
            "promptId": "prompt-111",
            "agentId": "a2",
            "message": {"role": "user", "content": '<teammate-message teammate_id="team-lead" summary="task">\nReview the engine.\n</teammate-message>'},
            "uuid": "a2-u1",
            "parentUuid": None,
            "isSidechain": True,
            "timestamp": "2026-03-21T22:00:02Z",
            "sessionId": session_id,
        },
    ])

    # Run pipeline
    output_dir = tmp_path / "output"
    run_preprocess(tmp_path / "source", output_dir)

    # Verify index
    index = json.loads((output_dir / "index.json").read_text())
    assert len(index["projects"]) == 1
    assert index["projects"][0]["sessions"][0]["id"] == session_id

    # Verify messages.json (replaces per-meeting files)
    messages_file = output_dir / "sessions" / session_id / "messages.json"
    assert messages_file.exists()
    messages = json.loads(messages_file.read_text())
    assert len(messages) == 4  # 1 from main, 2 from a1, 1 from a2
    assert messages[0]["timestamp"] < messages[-1]["timestamp"]
    assert messages[0]["teamName"] == "design-meeting"

    # Verify no meetings/ directory
    assert not (output_dir / "sessions" / session_id / "meetings").exists()

    assert "meetingCount" not in index["projects"][0]["sessions"][0]

    # Verify agent types
    types = json.loads((output_dir / "agent-types.json").read_text())
    assert "strategist" in types
    assert "engine-arch" in types


def test_pipeline_excludes_empty_sessions(tmp_path):
    """Sessions with no messages should be excluded from index.json."""
    from preprocessor.pipeline import run_preprocess

    project_dir = tmp_path / "source" / "-Users-test-myproject"

    # Session with messages
    session_with = "aaaa1111-bbbb-cccc-dddd-eeeeeeeeeeee"
    subagents_dir = project_dir / session_with / "subagents"
    subagents_dir.mkdir(parents=True)
    write_jsonl(project_dir / f"{session_with}.jsonl", [
        {
            "type": "assistant",
            "teamName": "meeting",
            "promptId": "prompt-111",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "hello"}]},
            "uuid": "u1",
            "parentUuid": None,
            "timestamp": "2026-03-21T22:00:00Z",
            "sessionId": session_with,
        }
    ])
    write_json(subagents_dir / "agent-a1.meta.json", {"agentType": "general"})
    write_jsonl(subagents_dir / "agent-a1.jsonl", [
        {
            "type": "user",
            "promptId": "prompt-111",
            "agentId": "a1",
            "message": {"role": "user", "content": "Do stuff"},
            "uuid": "a1-u1",
            "parentUuid": None,
            "isSidechain": True,
            "timestamp": "2026-03-21T22:00:01Z",
            "sessionId": session_with,
        },
    ])

    # Empty session — no agent transcripts, no messages
    session_empty = "ffff2222-gggg-hhhh-iiii-jjjjjjjjjjjj"
    empty_subagents = project_dir / session_empty / "subagents"
    empty_subagents.mkdir(parents=True)
    write_jsonl(project_dir / f"{session_empty}.jsonl", [])

    output_dir = tmp_path / "output"
    run_preprocess(tmp_path / "source", output_dir)

    index = json.loads((output_dir / "index.json").read_text())
    sessions = index["projects"][0]["sessions"]
    session_ids = [s["id"] for s in sessions]

    # Empty session should be excluded from index
    assert session_with in session_ids
    assert session_empty not in session_ids


def test_pipeline_processes_archive_sessions(tmp_path):
    """Pipeline handles archive-style sessions with agentJsonls instead of subagentsDir."""
    from preprocessor.pipeline import run_preprocess

    # Create native source (empty — no projects)
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Create archive with a session
    archive_dir = tmp_path / "archive"
    project_dir = archive_dir / "-Users-test-myproject"
    project_dir.mkdir(parents=True)

    session_id = "aabbccdd-eeff-0011-2233-445566778899"

    # Main conversation
    write_jsonl(project_dir / f"{session_id}.jsonl", [
        {
            "type": "assistant",
            "teamName": "design-meeting",
            "promptId": "prompt-111",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "spawning"}]},
            "uuid": "main-u1",
            "parentUuid": None,
            "timestamp": "2026-03-21T22:00:00Z",
            "sessionId": session_id,
        }
    ])

    # Agent files (flat, at project root — no subagents dir, no meta.json)
    write_jsonl(project_dir / "agent-a1.jsonl", [
        {
            "type": "user",
            "promptId": "prompt-111",
            "agentId": "a1",
            "message": {"role": "user", "content": '<teammate-message teammate_id="team-lead" summary="task">\nDo the analysis.\n</teammate-message>'},
            "uuid": "a1-u1",
            "parentUuid": None,
            "isSidechain": True,
            "timestamp": "2026-03-21T22:00:01Z",
            "sessionId": session_id,
        },
        {
            "type": "assistant",
            "agentId": "a1",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "Here is my analysis."}]},
            "uuid": "a1-u2",
            "parentUuid": "a1-u1",
            "isSidechain": True,
            "timestamp": "2026-03-21T22:00:10Z",
            "sessionId": session_id,
        },
    ])

    output_dir = tmp_path / "output"
    run_preprocess(source_dir, output_dir, archive_dir=archive_dir)

    # Verify index includes archive session
    index = json.loads((output_dir / "index.json").read_text())
    assert len(index["projects"]) == 1
    assert index["projects"][0]["sessions"][0]["id"] == session_id

    # Verify messages were parsed
    messages = json.loads(
        (output_dir / "sessions" / session_id / "messages.json").read_text()
    )
    assert len(messages) == 3  # 1 from main, 2 from a1
    assert messages[0]["teamName"] == "design-meeting"


def test_pipeline_processes_main_only_session(tmp_path):
    """A session with only a main JSONL (no agents) produces messages from main conversation."""
    from preprocessor.pipeline import run_preprocess

    source_dir = tmp_path / "source"
    source_dir.mkdir()

    archive_dir = tmp_path / "archive"
    project_dir = archive_dir / "-Users-test-solo"
    project_dir.mkdir(parents=True)

    session_id = "cccccccc-dddd-eeee-ffff-000000000000"

    # Main conversation only — no agent files
    write_jsonl(project_dir / f"{session_id}.jsonl", [
        {
            "type": "user",
            "message": {"role": "user", "content": "Hello from main"},
            "uuid": "main-u1",
            "parentUuid": None,
            "timestamp": "2026-03-21T10:00:00Z",
            "sessionId": session_id,
        },
        {
            "type": "assistant",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "Hi back"}]},
            "uuid": "main-u2",
            "parentUuid": "main-u1",
            "timestamp": "2026-03-21T10:00:05Z",
            "sessionId": session_id,
        },
    ])

    output_dir = tmp_path / "output"
    run_preprocess(source_dir, output_dir, archive_dir=archive_dir)

    index = json.loads((output_dir / "index.json").read_text())
    assert len(index["projects"]) == 1
    session_ids = [s["id"] for s in index["projects"][0]["sessions"]]
    assert session_id in session_ids

    messages = json.loads(
        (output_dir / "sessions" / session_id / "messages.json").read_text()
    )
    assert len(messages) == 2
    assert all(m["teamName"] == "Main Conversation" for m in messages)


def test_pipeline_main_jsonl_included_with_agents(tmp_path):
    """An agent session also includes main JSONL records alongside agent records."""
    from preprocessor.pipeline import run_preprocess

    source_dir = tmp_path / "source"
    source_dir.mkdir()

    archive_dir = tmp_path / "archive"
    project_dir = archive_dir / "-Users-test-myproject"
    project_dir.mkdir(parents=True)

    session_id = "aabbccdd-eeff-0011-2233-445566778899"

    # Main conversation with a real promptId + teamName
    write_jsonl(project_dir / f"{session_id}.jsonl", [
        {
            "type": "assistant",
            "teamName": "design-meeting",
            "promptId": "prompt-111",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "spawning"}]},
            "uuid": "main-u1",
            "parentUuid": None,
            "timestamp": "2026-03-21T22:00:00Z",
            "sessionId": session_id,
        }
    ])

    # Agent file
    write_jsonl(project_dir / "agent-a1.jsonl", [
        {
            "type": "user",
            "promptId": "prompt-111",
            "agentId": "a1",
            "message": {"role": "user", "content": '<teammate-message teammate_id="team-lead" summary="task">\nDo the analysis.\n</teammate-message>'},
            "uuid": "a1-u1",
            "parentUuid": None,
            "isSidechain": True,
            "timestamp": "2026-03-21T22:00:01Z",
            "sessionId": session_id,
        },
    ])

    output_dir = tmp_path / "output"
    run_preprocess(source_dir, output_dir, archive_dir=archive_dir)

    messages = json.loads(
        (output_dir / "sessions" / session_id / "messages.json").read_text()
    )
    # Should include both the main conversation record and the agent record
    assert len(messages) == 2
    contents = [m.get("content") or m.get("text") for m in messages]
    assert any("spawning" in str(c) for c in contents)


def test_pipeline_merges_native_and_archive(tmp_path):
    """Pipeline merges sessions from both native and archive sources."""
    from preprocessor.pipeline import run_preprocess

    slug = "-Users-test-myproject"
    native_sid = "11111111-aaaa-bbbb-cccc-dddddddddddd"
    archive_sid = "22222222-aaaa-bbbb-cccc-dddddddddddd"

    # Native source
    source_dir = tmp_path / "source"
    native_project = source_dir / slug
    native_sub = native_project / native_sid / "subagents"
    native_sub.mkdir(parents=True)
    write_jsonl(native_project / f"{native_sid}.jsonl", [
        {
            "type": "assistant", "teamName": "m1", "promptId": "p1",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "native"}]},
            "uuid": "nu1", "parentUuid": None,
            "timestamp": "2026-03-21T22:00:00Z", "sessionId": native_sid,
        }
    ])
    write_json(native_sub / "agent-a1.meta.json", {"agentType": "general"})
    write_jsonl(native_sub / "agent-a1.jsonl", [
        {
            "type": "user", "promptId": "p1", "agentId": "a1",
            "message": {"role": "user", "content": "native agent"},
            "uuid": "na1", "parentUuid": None, "isSidechain": True,
            "timestamp": "2026-03-21T22:00:01Z", "sessionId": native_sid,
        },
    ])

    # Archive source
    archive_dir = tmp_path / "archive"
    archive_project = archive_dir / slug
    archive_project.mkdir(parents=True)
    write_jsonl(archive_project / f"{archive_sid}.jsonl", [
        {
            "type": "assistant", "teamName": "m2", "promptId": "p2",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "archive"}]},
            "uuid": "au1", "parentUuid": None,
            "timestamp": "2026-03-20T10:00:00Z", "sessionId": archive_sid,
        }
    ])
    write_jsonl(archive_project / "agent-a2.jsonl", [
        {
            "type": "user", "promptId": "p2", "agentId": "a2",
            "message": {"role": "user", "content": "archive agent"},
            "uuid": "aa1", "parentUuid": None, "isSidechain": True,
            "timestamp": "2026-03-20T10:00:01Z", "sessionId": archive_sid,
        },
    ])

    output_dir = tmp_path / "output"
    run_preprocess(source_dir, output_dir, archive_dir=archive_dir)

    index = json.loads((output_dir / "index.json").read_text())
    assert len(index["projects"]) == 1
    session_ids = [s["id"] for s in index["projects"][0]["sessions"]]
    assert native_sid in session_ids
    assert archive_sid in session_ids
