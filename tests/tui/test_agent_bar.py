# ABOUTME: Tests for the agent bar header widget.
# ABOUTME: Verifies agent roster display and breadcrumb rendering.

import pytest
from textual.app import App, ComposeResult

from tui.widgets.agent_bar import AgentBar


class AgentBarApp(App):
    """Minimal app for testing AgentBar."""

    def compose(self) -> ComposeResult:
        yield AgentBar()


async def test_agent_bar_renders_empty():
    app = AgentBarApp()
    async with app.run_test() as pilot:
        bar = app.query_one(AgentBar)
        assert bar is not None


async def test_agent_bar_update_meeting(sample_agent_types):
    app = AgentBarApp()
    async with app.run_test() as pilot:
        bar = app.query_one(AgentBar)
        agents = [
            {"agentId": "a1", "type": "web-search-researcher", "messageCount": 42},
            {"agentId": "a2", "type": "general-purpose", "messageCount": 18},
        ]
        breadcrumb = ["project/alpha", "sess-001", "Research Team"]
        bar.update_meeting(agents, sample_agent_types, breadcrumb)
        await pilot.pause()
        # Verify the content was updated (check internal state)
        assert bar.breadcrumb_parts == breadcrumb
        assert len(bar.agents) == 2


async def test_agent_bar_clear():
    app = AgentBarApp()
    async with app.run_test() as pilot:
        bar = app.query_one(AgentBar)
        bar.update_meeting(
            [{"agentId": "a1", "type": "test", "messageCount": 1}],
            {"test": {"color": "#ff0000", "label": "Test"}},
            ["project", "session", "meeting"],
        )
        await pilot.pause()
        bar.clear()
        await pilot.pause()
        assert bar.breadcrumb_parts == []
        assert bar.agents == []
