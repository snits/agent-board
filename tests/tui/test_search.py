# ABOUTME: Tests for search and agent filtering functionality.
# ABOUTME: Verifies text search matching, agent type filtering, and search bar widget behavior.

import asyncio

import pytest
from textual.app import App, ComposeResult

from tui.widgets.search_bar import SearchBar
from tui.widgets.chat_view import matches_search, filter_by_agents, _precompute_messages


class SearchBarApp(App):
    """Minimal app for testing SearchBar."""

    def compose(self) -> ComposeResult:
        yield SearchBar()


def test_matches_search_in_content():
    msg = {"content": "Hello world", "toolUse": []}
    _precompute_messages([msg])
    assert matches_search(msg, "hello") is True


def test_matches_search_case_insensitive():
    msg = {"content": "Textual Framework", "toolUse": []}
    _precompute_messages([msg])
    assert matches_search(msg, "textual") is True


def test_matches_search_in_tool_summary():
    msg = {"content": "", "toolUse": [{"tool": "Read", "input": {}, "summary": "Read → app.py"}]}
    _precompute_messages([msg])
    assert matches_search(msg, "app.py") is True


def test_matches_search_no_match():
    msg = {"content": "Hello world", "toolUse": []}
    _precompute_messages([msg])
    assert matches_search(msg, "nonexistent") is False


def test_matches_search_empty_query():
    msg = {"content": "Hello world", "toolUse": []}
    _precompute_messages([msg])
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


async def test_search_bar_starts_hidden():
    app = SearchBarApp()
    async with app.run_test() as pilot:
        bar = app.query_one(SearchBar)
        assert not bar.has_class("-visible")


async def test_search_bar_show():
    app = SearchBarApp()
    async with app.run_test() as pilot:
        bar = app.query_one(SearchBar)
        bar.show()
        await pilot.pause()
        assert bar.has_class("-visible")


async def test_search_bar_hide_clears_value():
    app = SearchBarApp()
    async with app.run_test() as pilot:
        bar = app.query_one(SearchBar)
        bar.show()
        await pilot.pause()
        bar.value = "test query"
        bar.clear()
        await pilot.pause()
        assert not bar.has_class("-visible")
        assert bar.value == ""


async def test_search_bar_dismiss_keeps_query():
    """Enter dismisses search bar but preserves the query."""
    app = SearchBarApp()
    async with app.run_test() as pilot:
        bar = app.query_one(SearchBar)
        bar.show()
        await pilot.pause()
        bar.value = "test query"
        bar.dismiss()
        await pilot.pause()
        assert not bar.has_class("-visible")
        assert bar.value == "test query"


async def test_search_bar_enter_dismisses_not_clears():
    """Pressing Enter hides bar but keeps the query value."""
    app = SearchBarApp()
    async with app.run_test() as pilot:
        bar = app.query_one(SearchBar)
        bar.show()
        await pilot.pause()
        bar.value = "test query"
        await pilot.press("enter")
        await pilot.pause()
        assert not bar.has_class("-visible")
        assert bar.value == "test query"


async def test_search_bar_debounces_input():
    """Rapid typing only fires SearchChanged once after a pause."""
    received = []

    class CapturingApp(App):
        def compose(self) -> ComposeResult:
            yield SearchBar()

        def on_search_bar_search_changed(self, event: SearchBar.SearchChanged) -> None:
            received.append(event.query)

    app = CapturingApp()
    async with app.run_test() as pilot:
        bar = app.query_one(SearchBar)
        bar.show()
        await pilot.pause()
        # Type rapidly
        bar.value = "h"
        await pilot.pause()
        bar.value = "he"
        await pilot.pause()
        bar.value = "hel"
        await pilot.pause()
        # Wait for debounce to fire (300ms + buffer)
        await asyncio.sleep(0.5)
        await pilot.pause()
        # Should have received only the final value, not intermediate ones
        assert received[-1] == "hel"
        # Should NOT have received all 3 intermediate values
        assert len([q for q in received if q in ("h", "he", "hel")]) < 3


async def test_search_bar_clear_fires_immediately():
    """clear() posts SearchChanged immediately, not after debounce delay."""
    received = []

    class CapturingApp(App):
        def compose(self) -> ComposeResult:
            yield SearchBar()

        def on_search_bar_search_changed(self, event: SearchBar.SearchChanged) -> None:
            received.append(event.query)

    app = CapturingApp()
    async with app.run_test() as pilot:
        bar = app.query_one(SearchBar)
        bar.show()
        await pilot.pause()
        bar.value = "test"
        await asyncio.sleep(0.5)
        await pilot.pause()
        received.clear()
        bar.clear()
        await pilot.pause()
        # Should have received empty string immediately
        assert "" in received


async def test_search_bar_submit_fires_immediately():
    """Pressing Enter posts current value immediately."""
    received = []

    class CapturingApp(App):
        def compose(self) -> ComposeResult:
            yield SearchBar()

        def on_search_bar_search_changed(self, event: SearchBar.SearchChanged) -> None:
            received.append(event.query)

    app = CapturingApp()
    async with app.run_test() as pilot:
        bar = app.query_one(SearchBar)
        bar.show()
        await pilot.pause()
        bar.value = "query"
        await pilot.pause()
        received.clear()
        # Submit immediately fires
        await pilot.press("enter")
        await pilot.pause()
        assert "query" in received
