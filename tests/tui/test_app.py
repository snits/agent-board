# ABOUTME: Integration tests for the TUI app.
# ABOUTME: Verifies widget composition, keybindings, and data flow.

import pytest
from tui.app import AgentBoardApp
from tui.widgets.nav_tree import NavTree, MeetingNode
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


async def test_agent_filter_keybinding(data_dir):
    """Pressing 'f' cycles agent filter and updates AgentBar indicator."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        bar = app.query_one(AgentBar)

        # Load a meeting so agent types are available
        project_node = tree.root.children[0]
        session_node = project_node.children[0]
        session_node.expand()
        await pilot.pause()
        meeting_leaf = session_node.children[0]
        tree.select_node(meeting_leaf)
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

        # Load a meeting
        project_node = tree.root.children[0]
        session_node = project_node.children[0]
        session_node.expand()
        await pilot.pause()
        meeting_leaf = session_node.children[0]
        tree.select_node(meeting_leaf)
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


async def test_next_meeting_syncs_tree(data_dir_two_meetings):
    """Pressing 'n' navigates to next meeting and syncs the tree cursor."""
    app = AgentBoardApp(data_dir=data_dir_two_meetings)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)

        # Expand project and session to load meetings
        project_node = tree.root.children[0]
        project_node.expand()
        await pilot.pause()
        session_node = project_node.children[0]
        session_node.expand()
        await pilot.pause()
        assert len(session_node.children) == 2

        # Select first meeting
        meeting1 = session_node.children[0]
        tree.select_node(meeting1)
        await pilot.pause()
        assert app._current_meeting_node.meeting_id == "mtg-001"

        # Press 'n' to go to next meeting
        await pilot.press("n")
        await pilot.pause()

        # Chat should show second meeting
        assert app._current_meeting_node.meeting_id == "mtg-002"
        # Tree cursor should also point to second meeting
        assert tree.cursor_node is not None
        assert isinstance(tree.cursor_node.data, MeetingNode)
        assert tree.cursor_node.data.meeting_id == "mtg-002"


async def test_prev_meeting_syncs_tree(data_dir_two_meetings):
    """Pressing 'p' navigates to previous meeting and syncs the tree cursor."""
    app = AgentBoardApp(data_dir=data_dir_two_meetings)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)

        # Expand project and session to load meetings
        project_node = tree.root.children[0]
        project_node.expand()
        await pilot.pause()
        session_node = project_node.children[0]
        session_node.expand()
        await pilot.pause()

        # Select second meeting
        meeting2 = session_node.children[1]
        tree.select_node(meeting2)
        await pilot.pause()
        assert app._current_meeting_node.meeting_id == "mtg-002"

        # Press 'p' to go to previous meeting
        await pilot.press("p")
        await pilot.pause()

        assert app._current_meeting_node.meeting_id == "mtg-001"
        assert tree.cursor_node.data.meeting_id == "mtg-001"


async def test_next_meeting_at_end_stays_put(data_dir_two_meetings):
    """Pressing 'n' on the last meeting does not change the view."""
    app = AgentBoardApp(data_dir=data_dir_two_meetings)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)

        # Expand and select the last meeting
        project_node = tree.root.children[0]
        project_node.expand()
        await pilot.pause()
        session_node = project_node.children[0]
        session_node.expand()
        await pilot.pause()

        meeting2 = session_node.children[1]
        tree.select_node(meeting2)
        await pilot.pause()
        assert app._current_meeting_node.meeting_id == "mtg-002"

        # Press 'n' — should stay on the last meeting
        await pilot.press("n")
        await pilot.pause()
        assert app._current_meeting_node.meeting_id == "mtg-002"
        assert tree.cursor_node.data.meeting_id == "mtg-002"


async def test_prev_meeting_at_start_stays_put(data_dir_two_meetings):
    """Pressing 'p' on the first meeting does not change the view."""
    app = AgentBoardApp(data_dir=data_dir_two_meetings)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)

        # Expand and select the first meeting
        project_node = tree.root.children[0]
        project_node.expand()
        await pilot.pause()
        session_node = project_node.children[0]
        session_node.expand()
        await pilot.pause()

        meeting1 = session_node.children[0]
        tree.select_node(meeting1)
        await pilot.pause()
        assert app._current_meeting_node.meeting_id == "mtg-001"

        # Press 'p' — should stay on the first meeting
        await pilot.press("p")
        await pilot.pause()
        assert app._current_meeting_node.meeting_id == "mtg-001"
        assert tree.cursor_node.data.meeting_id == "mtg-001"


async def test_np_bindings_visible_in_footer(data_dir):
    """The n/p keybindings should be visible in the footer."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        # Check that n and p bindings have show=True (default)
        bindings = {b.key: b for b in app.BINDINGS}
        assert bindings["n"].show is True
        assert bindings["p"].show is True


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
