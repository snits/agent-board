# ABOUTME: Integration tests for the TUI app.
# ABOUTME: Verifies widget composition, keybindings, and data flow.

import asyncio

import pytest
from tui.app import AgentBoardApp
from tui.widgets.nav_tree import NavTree, SessionNode
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
    """Test expanding a project node and selecting a session loads chat."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        chat = app.query_one(ChatView)
        bar = app.query_one(AgentBar)

        # Expand first project
        project_node = tree.root.children[0]
        project_node.expand()
        await pilot.pause()

        # Select the session node (leaf)
        session_node = project_node.children[0]
        tree.select_node(session_node)
        await pilot.pause()

        # Chat should have loaded messages
        assert chat.message_count > 0
        # Agent bar should have 2-part breadcrumb
        assert len(bar.breadcrumb_parts) == 2
        # Breadcrumb should use timestamp, not session ID hash
        session_part = bar.breadcrumb_parts[1]
        assert "2026-03-20" in session_part
        assert "sess-001" not in session_part


async def test_chat_view_visible_in_layout(data_dir):
    """ChatView must be positioned within the visible screen area."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test(size=(80, 24)) as pilot:
        tree = app.query_one(NavTree)
        chat = app.query_one(ChatView)
        # Both panels must be within the 80-column screen
        assert tree.region.x >= 0
        assert tree.region.x + tree.region.width <= 80
        assert chat.region.x >= 0
        assert chat.region.x + chat.region.width <= 80
        # Chat must not be pushed off-screen by the tree
        assert chat.region.x < 80, f"ChatView starts at x={chat.region.x}, off-screen"


async def test_tab_switches_focus_nav_to_chat(data_dir):
    """Tab moves focus from nav tree to chat view."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        nav = app.query_one(NavTree)
        chat = app.query_one(ChatView)
        nav.focus()
        await pilot.pause()
        assert nav.has_focus_within
        await pilot.press("tab")
        await pilot.pause()
        assert chat.has_focus_within


async def test_tab_switches_focus_chat_to_nav(data_dir):
    """Tab moves focus from chat view to nav tree."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        nav = app.query_one(NavTree)
        chat = app.query_one(ChatView)
        chat.focus()
        await pilot.pause()
        assert chat.has_focus_within
        await pilot.press("tab")
        await pilot.pause()
        assert nav.has_focus_within


async def test_tab_round_trip(data_dir):
    """Tab cycles nav -> chat -> nav without getting stuck."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        nav = app.query_one(NavTree)
        chat = app.query_one(ChatView)
        nav.focus()
        await pilot.pause()
        assert nav.has_focus_within

        await pilot.press("tab")
        await pilot.pause()
        assert chat.has_focus_within

        await pilot.press("tab")
        await pilot.pause()
        assert nav.has_focus_within


async def test_tab_from_search_bar_goes_to_nav(data_dir):
    """Tab from search bar sends focus to nav tree."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        nav = app.query_one(NavTree)
        search = app.query_one(SearchBar)
        # Show and focus search bar
        await pilot.press("slash")
        await pilot.pause()
        assert not nav.has_focus_within
        await pilot.press("tab")
        await pilot.pause()
        assert nav.has_focus_within


async def test_agent_filter_keybinding(data_dir):
    """Pressing 'f' cycles agent filter and updates AgentBar indicator."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        bar = app.query_one(AgentBar)

        # Load a session
        project_node = tree.root.children[0]
        session_node = project_node.children[0]
        tree.select_node(session_node)
        await pilot.pause()

        # No filter initially
        assert app._agent_filter == set()
        assert bar._filter_type is None

        # Press 'f' to activate first filter
        await pilot.press("f")
        await pilot.pause()
        assert len(app._agent_filter) == 1
        assert bar._filter_type is not None
        assert "Filter:" in str(bar._markup)

        first_filter = bar._filter_type

        # Press 'f' again to cycle to next filter
        await pilot.press("f")
        await pilot.pause()
        assert bar._filter_type is not None
        assert bar._filter_type != first_filter


async def test_escape_clears_agent_filter(data_dir):
    """Pressing Escape clears the active agent filter."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        bar = app.query_one(AgentBar)

        # Load a session
        project_node = tree.root.children[0]
        session_node = project_node.children[0]
        tree.select_node(session_node)
        await pilot.pause()

        # Activate a filter
        await pilot.press("f")
        await pilot.pause()
        assert len(app._agent_filter) == 1
        assert bar._filter_type is not None

        # Escape should clear the filter (search bar is not visible)
        await pilot.press("escape")
        await pilot.pause()
        assert app._agent_filter == set()
        assert bar._filter_type is None
        assert "Filter:" not in str(bar._markup)


async def test_search_enter_preserves_results(data_dir):
    """Enter dismisses search bar but chat view stays filtered."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        chat = app.query_one(ChatView)
        search = app.query_one(SearchBar)

        # Load a session
        project_node = tree.root.children[0]
        session_node = project_node.children[0]
        tree.select_node(session_node)
        await pilot.pause()
        full_count = chat.message_count

        # Search for something that matches a subset
        await pilot.press("slash")
        await pilot.pause()
        search.value = "Textual"
        await pilot.pause()
        await asyncio.sleep(0.5)
        await pilot.pause()
        filtered_count = chat.message_count
        assert filtered_count < full_count

        # Enter should dismiss search bar but keep results filtered
        await pilot.press("enter")
        await pilot.pause()
        assert not search.has_class("-visible")
        assert chat.message_count == filtered_count


async def test_escape_clears_dismissed_search(data_dir):
    """Escape clears a dismissed-but-active search filter."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        chat = app.query_one(ChatView)
        search = app.query_one(SearchBar)

        # Load a session
        project_node = tree.root.children[0]
        session_node = project_node.children[0]
        tree.select_node(session_node)
        await pilot.pause()
        full_count = chat.message_count

        # Search and dismiss with Enter
        await pilot.press("slash")
        await pilot.pause()
        search.value = "Textual"
        await pilot.pause()
        await asyncio.sleep(0.5)
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert not search.has_class("-visible")
        assert chat.message_count < full_count

        # Escape should clear the dismissed search and restore all results
        await pilot.press("escape")
        await pilot.pause()
        assert chat.message_count == full_count


async def test_filter_cycle_shows_position(data_dir):
    """Cycling filters with 'f' shows position indicator like [1/N]."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        bar = app.query_one(AgentBar)

        # Load a session
        project_node = tree.root.children[0]
        session_node = project_node.children[0]
        tree.select_node(session_node)
        await pilot.pause()

        # Press 'f' to activate first filter
        await pilot.press("f")
        await pilot.pause()
        markup = str(bar._markup)
        assert "[1/" in markup

        # Press 'f' again to cycle
        await pilot.press("f")
        await pilot.pause()
        markup = str(bar._markup)
        assert "[2/" in markup
