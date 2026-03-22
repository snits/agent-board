# ABOUTME: Tests for search and agent filtering functionality.
# ABOUTME: Verifies text search matching and agent type filtering.

import pytest

from tui.widgets.search_bar import SearchBar
from tui.widgets.chat_view import matches_search, filter_by_agents


def test_matches_search_in_content():
    msg = {"content": "Hello world", "toolUse": []}
    assert matches_search(msg, "hello") is True


def test_matches_search_case_insensitive():
    msg = {"content": "Textual Framework", "toolUse": []}
    assert matches_search(msg, "textual") is True


def test_matches_search_in_tool_summary():
    msg = {"content": "", "toolUse": [{"tool": "Read", "input": {}, "summary": "Read → app.py"}]}
    assert matches_search(msg, "app.py") is True


def test_matches_search_no_match():
    msg = {"content": "Hello world", "toolUse": []}
    assert matches_search(msg, "nonexistent") is False


def test_matches_search_empty_query():
    msg = {"content": "Hello world", "toolUse": []}
    assert matches_search(msg, "") is True


def test_filter_by_agents_include():
    messages = [
        {"agentType": "researcher", "content": "a", "toolUse": []},
        {"agentType": "general", "content": "b", "toolUse": []},
        {"agentType": "researcher", "content": "c", "toolUse": []},
    ]
    result = filter_by_agents(messages, {"researcher"})
    assert len(result) == 2
    assert all(m["agentType"] == "researcher" for m in result)


def test_filter_by_agents_empty_filter_returns_all():
    messages = [
        {"agentType": "researcher", "content": "a", "toolUse": []},
        {"agentType": "general", "content": "b", "toolUse": []},
    ]
    result = filter_by_agents(messages, set())
    assert len(result) == 2
