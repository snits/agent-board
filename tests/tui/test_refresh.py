# ABOUTME: Tests for the TUI refresh keybinding.
# ABOUTME: Verifies source_dir storage, NavTree reload, and rebuild behavior.

import json
from pathlib import Path
from unittest.mock import patch

from tui.app import AgentBoardApp
from tui.widgets.nav_tree import NavTree, SessionNode
from tui.widgets.chat_view import ChatView
from tui.widgets.agent_bar import AgentBar
from tui.widgets.detail_pane import DetailPane


async def test_refresh_binding_exists(data_dir):
    """The 'r' keybinding is registered as refresh_data."""
    app = AgentBoardApp(data_dir=data_dir)
    bindings = {b.key: b for b in app.BINDINGS}
    assert "r" in bindings
    assert bindings["r"].action == "refresh_data"


async def test_refresh_accepts_source_dir(data_dir):
    """AgentBoardApp accepts a source_dir parameter."""
    source = Path("/custom/source")
    app = AgentBoardApp(data_dir=data_dir, source_dir=source)
    assert app._source_dir == source


async def test_refresh_uses_default_source_dir(data_dir):
    """Without explicit source_dir, uses default_source_dir()."""
    from preprocessor.paths import default_source_dir
    app = AgentBoardApp(data_dir=data_dir)
    assert app._source_dir == default_source_dir()


async def test_nav_tree_reload_rebuilds_tree(data_dir, sample_index):
    """NavTree.reload() clears and repopulates from new index data."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        assert len(tree.root.children) == 2

        # Reload with only 1 project
        modified_index = {"projects": [sample_index["projects"][0]]}
        tree.reload(modified_index)
        await pilot.pause()
        assert len(tree.root.children) == 1


async def test_nav_tree_reload_creates_fresh_nodes(data_dir, sample_index):
    """After reload, session nodes are fresh instances."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)

        # Get reference to old session node
        old_session = tree.root.children[0].children[0]
        old_data = old_session.data

        # Reload and verify new session nodes are distinct objects
        tree.reload(sample_index)
        await pilot.pause()
        new_session = tree.root.children[0].children[0]
        assert new_session.data is not old_data
        assert isinstance(new_session.data, SessionNode)


async def test_rebuild_after_refresh_reloads_data(data_dir):
    """_rebuild_after_refresh reloads index and agent types from disk."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        assert "web-search-researcher" in app._agent_types

        # Write new agent types to disk
        new_types = {"new-agent": {"color": "#FF0000", "label": "New Agent"}}
        (data_dir / "agent-types.json").write_text(json.dumps(new_types))

        # Call rebuild directly
        app._rebuild_after_refresh()
        await pilot.pause()

        assert "new-agent" in app._agent_types
        assert "web-search-researcher" not in app._agent_types


async def test_rebuild_after_refresh_preserves_session(data_dir):
    """_rebuild_after_refresh re-selects the previous session if it still exists."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)

        # Load a session
        project_node = tree.root.children[0]
        session_node = project_node.children[0]
        tree.select_node(session_node)
        await pilot.pause()
        assert app._current_session_node is not None
        original_id = app._current_session_node.session_id

        app._rebuild_after_refresh()
        await pilot.pause()

        assert app._current_session_node is not None
        assert app._current_session_node.session_id == original_id


async def test_rebuild_after_refresh_rebuilds_nav_tree(data_dir, sample_index):
    """_rebuild_after_refresh rebuilds nav tree from fresh data."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        assert len(tree.root.children) == 2

        # Modify the index on disk
        modified_index = {"projects": [sample_index["projects"][0]]}
        (data_dir / "index.json").write_text(json.dumps(modified_index))

        app._rebuild_after_refresh()
        await pilot.pause()

        tree = app.query_one(NavTree)
        assert len(tree.root.children) == 1


async def test_rebuild_preserves_session_selection(data_dir):
    """After rebuild, the previously selected session is re-selected."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        chat = app.query_one(ChatView)

        # Select a session
        project_node = tree.root.children[0]
        session_node = project_node.children[0]
        tree.select_node(session_node)
        await pilot.pause()
        assert app._current_session_node is not None
        original_id = app._current_session_node.session_id

        # Rebuild (simulates refresh)
        app._rebuild_after_refresh()
        await pilot.pause()

        # Session should be re-selected
        assert app._current_session_node is not None
        assert app._current_session_node.session_id == original_id
        assert chat.message_count > 0


async def test_rebuild_preserves_detail_pane_visibility(data_dir):
    """After rebuild, the detail pane remains visible if it was open."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test(size=(80, 40)) as pilot:
        pane = app.query_one(DetailPane)
        tree = app.query_one(NavTree)

        # Select a session and open detail pane
        project_node = tree.root.children[0]
        session_node = project_node.children[0]
        tree.select_node(session_node)
        await pilot.pause()
        await pilot.press("v")
        await pilot.pause()
        assert pane.is_visible

        # Rebuild
        app._rebuild_after_refresh()
        await pilot.pause()

        # Detail pane should still be visible
        assert pane.is_visible


async def test_rebuild_handles_removed_session(data_dir, sample_index):
    """When the selected session is removed from index, rebuild shows empty state."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        chat = app.query_one(ChatView)

        # Select a session
        project_node = tree.root.children[0]
        session_node = project_node.children[0]
        tree.select_node(session_node)
        await pilot.pause()
        assert app._current_session_node is not None

        # Remove that session's project from the index
        modified_index = {"projects": [sample_index["projects"][1]]}
        (data_dir / "index.json").write_text(json.dumps(modified_index))

        # Rebuild — should handle missing session gracefully
        app._rebuild_after_refresh()
        await pilot.pause()

        # No session selected, chat empty
        assert app._current_session_node is None
        assert chat.message_count == 0
