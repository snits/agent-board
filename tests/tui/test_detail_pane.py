# ABOUTME: Tests for the detail pane widget.
# ABOUTME: Verifies full message rendering and toggle behavior.

import pytest
from textual.app import App, ComposeResult

from tui.widgets.detail_pane import DetailPane


AGENT_TYPES = {
    "web-search-researcher": {"color": "#DCBEFF", "label": "Researcher"},
    "general-purpose": {"color": "#FFFAC8", "label": "General"},
}


class DetailPaneApp(App):
    """Minimal app for testing DetailPane."""

    def compose(self) -> ComposeResult:
        yield DetailPane(agent_types=AGENT_TYPES)


async def test_detail_pane_starts_hidden():
    """DetailPane is hidden by default."""
    app = DetailPaneApp()
    async with app.run_test(size=(80, 24)) as pilot:
        pane = app.query_one(DetailPane)
        assert not pane.has_class("-visible")


async def test_detail_pane_show_hide():
    """Toggle visibility with show/hide methods."""
    app = DetailPaneApp()
    async with app.run_test(size=(80, 24)) as pilot:
        pane = app.query_one(DetailPane)
        assert not pane.has_class("-visible")
        pane.show()
        await pilot.pause()
        assert pane.has_class("-visible")
        pane.hide()
        await pilot.pause()
        assert not pane.has_class("-visible")


async def test_detail_pane_renders_message():
    """Updating with a message renders its full content."""
    app = DetailPaneApp()
    async with app.run_test(size=(80, 24)) as pilot:
        pane = app.query_one(DetailPane)
        pane.show()
        await pilot.pause()
        msg = {
            "agentType": "general-purpose",
            "timestamp": "2026-03-20T10:00:00.000Z",
            "content": "Line one\nLine two\nLine three",
            "_tool_summaries": ["⚙ Read → /app.py"],
        }
        pane.update_message(msg)
        await pilot.pause()
        content = str(pane._content.content)
        assert "Line one" in content
        assert "Line two" in content
        assert "Read" in content


async def test_detail_pane_clears_on_none():
    """Updating with None clears the pane."""
    app = DetailPaneApp()
    async with app.run_test(size=(80, 24)) as pilot:
        pane = app.query_one(DetailPane)
        pane.show()
        await pilot.pause()
        msg = {"agentType": "general-purpose", "timestamp": "2026-03-20T10:00:00.000Z",
               "content": "Hello", "_tool_summaries": []}
        pane.update_message(msg)
        await pilot.pause()
        pane.update_message(None)
        await pilot.pause()
        content = str(pane._content.content)
        assert content.strip() == ""
