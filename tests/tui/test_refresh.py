# ABOUTME: Tests for the TUI refresh keybinding.
# ABOUTME: Verifies source_dir storage, NavTree reload, and rebuild behavior.

import json
from pathlib import Path
from unittest.mock import patch

from tui.app import AgentBoardApp
from tui.widgets.nav_tree import NavTree
from tui.widgets.chat_view import ChatView
from tui.widgets.agent_bar import AgentBar


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


async def test_nav_tree_reload_resets_loaded_state(data_dir, sample_index):
    """After reload, session nodes are not marked as loaded."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)

        # Expand a session to mark it loaded
        project_node = tree.root.children[0]
        session_node = project_node.children[0]
        session_node.expand()
        await pilot.pause()
        assert session_node.data.loaded is True

        # Reload and verify fresh session nodes are not loaded
        tree.reload(sample_index)
        await pilot.pause()
        new_session = tree.root.children[0].children[0]
        assert new_session.data.loaded is False


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


async def test_rebuild_after_refresh_clears_meeting(data_dir):
    """_rebuild_after_refresh clears current meeting selection."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)

        # Load a meeting
        project_node = tree.root.children[0]
        session_node = project_node.children[0]
        session_node.expand()
        await pilot.pause()
        meeting_leaf = session_node.children[0]
        tree.select_node(meeting_leaf)
        await pilot.pause()
        assert app._current_meeting_node is not None

        app._rebuild_after_refresh()
        await pilot.pause()

        assert app._current_meeting_node is None


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
