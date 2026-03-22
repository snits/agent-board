# ABOUTME: Tests for JSONL record parsing — content extraction, tool-use separation, teammate XML.
# ABOUTME: Validates both string and array content formats from claude's transcript data.

import pytest
from preprocessor.parser import parse_content, parse_teammate_message, parse_record


def test_parse_content_string():
    """String content (user messages) returns text as-is, no tool use."""
    text, tools = parse_content("Hello, this is a message.")
    assert text == "Hello, this is a message."
    assert tools == []


def test_parse_content_text_blocks():
    """Array with text blocks joins text, no tool use."""
    content = [
        {"type": "text", "text": "First part."},
        {"type": "text", "text": "Second part."}
    ]
    text, tools = parse_content(content)
    assert text == "First part.\n\nSecond part."
    assert tools == []


def test_parse_content_tool_use_only():
    """Array with only tool_use blocks returns empty text."""
    content = [
        {
            "type": "tool_use",
            "id": "toolu_001",
            "name": "Read",
            "input": {"file_path": "/path/to/file.md"}
        }
    ]
    text, tools = parse_content(content)
    assert text == ""
    assert len(tools) == 1
    assert tools[0]["tool"] == "Read"
    assert tools[0]["input"] == {"file_path": "/path/to/file.md"}
    assert tools[0]["summary"] == "Read: /path/to/file.md"


def test_parse_content_mixed():
    """Array with text + tool_use separates them."""
    content = [
        {"type": "text", "text": "Let me read that file."},
        {
            "type": "tool_use",
            "id": "toolu_002",
            "name": "Bash",
            "input": {"command": "ls -la"}
        }
    ]
    text, tools = parse_content(content)
    assert text == "Let me read that file."
    assert len(tools) == 1
    assert tools[0]["tool"] == "Bash"


def test_parse_content_tool_result_in_user_message():
    """Array with tool_result blocks (user records) are skipped."""
    content = [
        {"type": "tool_result", "tool_use_id": "t1", "content": "some result"}
    ]
    text, tools = parse_content(content)
    assert text == ""
    assert tools == []


def test_parse_teammate_message_basic():
    """Extracts sender and content from teammate-message XML."""
    text = '<teammate-message teammate_id="strategist" color="blue">\nHello team!\n</teammate-message>'
    result = parse_teammate_message(text)
    assert result is not None
    assert result["sender"] == "strategist"
    assert "Hello team!" in result["content"]


def test_parse_teammate_message_team_lead():
    """team-lead sender is handled."""
    text = '<teammate-message teammate_id="team-lead" summary="task info">\nDo the thing.\n</teammate-message>'
    result = parse_teammate_message(text)
    assert result["sender"] == "team-lead"
    assert "Do the thing." in result["content"]


def test_parse_teammate_message_not_present():
    """Returns None for plain text without teammate-message XML."""
    result = parse_teammate_message("Just a normal message.")
    assert result is None


def test_parse_teammate_message_with_summary():
    """Extracts summary attribute if present."""
    text = '<teammate-message teammate_id="engine-arch" summary="Review findings">\nContent here.\n</teammate-message>'
    result = parse_teammate_message(text)
    assert result["summary"] == "Review findings"


def test_parse_record_assistant_text(sample_assistant_text_record):
    """Parses an assistant text record into a normalized message."""
    result = parse_record(sample_assistant_text_record)
    assert result is not None
    assert result["role"] == "assistant"
    assert result["agentId"] == "agent-001"
    assert result["content"] == "Here is my analysis of the design."
    assert result["toolUse"] == []
    assert result["timestamp"] == "2026-03-21T22:10:15.000Z"
    assert result["uuid"] == "uuid-002"
    assert result["parentUuid"] == "uuid-001"


def test_parse_record_user_teammate(sample_user_record):
    """Parses a user record with teammate-message."""
    result = parse_record(sample_user_record)
    assert result is not None
    assert result["role"] == "user"
    assert result["sender"] == "team-lead"
    assert result["promptId"] == "prompt-aaa"


def test_parse_record_progress_skipped(sample_progress_record):
    """Progress records return None (skipped)."""
    result = parse_record(sample_progress_record)
    assert result is None


def test_parse_record_tool_use(sample_assistant_tooluse_record):
    """Parses tool_use content into toolUse array."""
    result = parse_record(sample_assistant_tooluse_record)
    assert result is not None
    assert result["content"] == ""
    assert len(result["toolUse"]) == 1
    assert result["toolUse"][0]["tool"] == "Read"
