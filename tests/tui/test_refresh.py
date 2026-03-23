# ABOUTME: Tests for the TUI refresh keybinding.
# ABOUTME: Verifies that pressing R re-runs preprocessing and reloads data.

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from tui.app import AgentBoardApp
from tui.widgets.nav_tree import NavTree
from tui.widgets.chat_view import ChatView
from tui.widgets.agent_bar import AgentBar


async def test_refresh_binding_exists(data_dir):
    """The 'R' keybinding is registered."""
    app = AgentBoardApp(data_dir=data_dir)
    bindings = {b.key: b for b in app.BINDINGS}
    assert "R" in bindings


async def test_refresh_reruns_preprocessor(data_dir):
    """Pressing R calls run_preprocess with source and data dirs."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        with patch("tui.app.run_preprocess") as mock_preprocess:
            await pilot.press("R")
            await pilot.pause()
            mock_preprocess.assert_called_once_with(
                app._source_dir, app._data_dir
            )


async def test_refresh_reloads_nav_tree(data_dir, sample_index):
    """After refresh, the nav tree is rebuilt from reloaded data."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        assert len(tree.root.children) == 2

        # Modify the index to have 1 project instead of 2
        modified_index = {"projects": [sample_index["projects"][0]]}
        (data_dir / "index.json").write_text(json.dumps(modified_index))

        with patch("tui.app.run_preprocess"):
            await pilot.press("R")
            await pilot.pause()

        tree = app.query_one(NavTree)
        assert len(tree.root.children) == 1


async def test_refresh_reloads_agent_types(data_dir):
    """After refresh, agent types are reloaded."""
    app = AgentBoardApp(data_dir=data_dir)
    async with app.run_test() as pilot:
        assert "web-search-researcher" in app._agent_types

        # Write new agent types
        new_types = {"new-agent": {"color": "#FF0000", "label": "New Agent"}}
        (data_dir / "agent-types.json").write_text(json.dumps(new_types))

        with patch("tui.app.run_preprocess"):
            await pilot.press("R")
            await pilot.pause()

        assert "new-agent" in app._agent_types
        assert "web-search-researcher" not in app._agent_types


async def test_refresh_clears_current_meeting(data_dir):
    """After refresh, current meeting selection is cleared."""
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

        with patch("tui.app.run_preprocess"):
            await pilot.press("R")
            await pilot.pause()

        assert app._current_meeting_node is None


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
