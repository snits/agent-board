# ABOUTME: Tests for the TUI data loading layer.
# ABOUTME: Verifies JSON file reading from the preprocessor output directory.

from tui.data import load_index, load_agent_types, load_session, load_meeting


def test_load_index(data_dir, sample_index):
    result = load_index(data_dir)
    assert result == sample_index
    assert len(result["projects"]) == 2


def test_load_agent_types(data_dir, sample_agent_types):
    result = load_agent_types(data_dir)
    assert result == sample_agent_types
    assert "web-search-researcher" in result


def test_load_session(data_dir, sample_session):
    result = load_session(data_dir, "sess-001")
    assert result == sample_session
    assert len(result["meetings"]) == 2


def test_load_meeting(data_dir, sample_meeting):
    result = load_meeting(data_dir, "sess-001", "mtg-001")
    assert result == sample_meeting
    assert len(result["messages"]) == 5


def test_load_index_missing_file(tmp_path):
    result = load_index(tmp_path)
    assert result == {"projects": []}


def test_load_agent_types_missing_file(tmp_path):
    result = load_agent_types(tmp_path)
    assert result == {}


def test_load_session_missing_file(tmp_path):
    result = load_session(tmp_path, "nonexistent")
    assert result is None


def test_load_meeting_missing_file(tmp_path):
    result = load_meeting(tmp_path, "sess-001", "nonexistent")
    assert result is None
