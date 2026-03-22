# ABOUTME: Integration tests for the TUI app.
# ABOUTME: Verifies widget composition, keybindings, and data flow.

import pytest
from tui.app import AgentBoardApp
from tui.widgets.nav_tree import NavTree
from tui.widgets.chat_view import ChatView
from tui.widgets.agent_bar import AgentBar
from tui.widgets.search_bar import SearchBar


async def test_app_composes_all_widgets(data_dir):
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        assert app.query_one(NavTree) is not None
        assert app.query_one(ChatView) is not None
        assert app.query_one(AgentBar) is not None
        assert app.query_one(SearchBar) is not None


async def test_app_populates_nav_tree(data_dir):
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        # Should have 2 projects from our fixture data
        assert len(tree.root.children) == 2


async def test_quit_keybinding(data_dir):
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        await pilot.press("q")
        # App should exit (run_test context will end)


async def test_search_keybinding_shows_search_bar(data_dir):
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        search = app.query_one(SearchBar)
        assert not search.has_class("-visible")
        await pilot.press("slash")
        await pilot.pause()
        assert search.has_class("-visible")


async def test_escape_hides_search_bar(data_dir):
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        await pilot.press("slash")
        await pilot.pause()
        search = app.query_one(SearchBar)
        assert search.has_class("-visible")
        await pilot.press("escape")
        await pilot.pause()
        assert not search.has_class("-visible")


async def test_full_flow_expand_and_select(data_dir, sample_session):
    """Test expanding a session node loads meetings, selecting one loads chat."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        chat = app.query_one(ChatView)
        bar = app.query_one(AgentBar)

        # Expand first project
        project_node = tree.root.children[0]
        session_node = project_node.children[0]

        # Simulate expanding the session node
        session_node.expand()
        await pilot.pause()

        # Session should now have meeting children
        assert len(session_node.children) == 2

        # Select the first meeting
        meeting_leaf = session_node.children[0]
        tree.select_node(meeting_leaf)
        await pilot.pause()

        # Chat should have loaded messages
        assert chat.message_count > 0
        # Agent bar should have breadcrumb
        assert len(bar.breadcrumb_parts) == 3


async def test_tool_toggle(data_dir, sample_session):
    """Test that 't' toggles tool use detail."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        chat = app.query_one(ChatView)
        assert chat._tool_expanded is False
        await pilot.press("t")
        await pilot.pause()
        assert chat._tool_expanded is True
        await pilot.press("t")
        await pilot.pause()
        assert chat._tool_expanded is False
