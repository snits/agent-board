# ABOUTME: Tests for the navigation tree widget.
# ABOUTME: Verifies project/session hierarchy and session selection events.

import pytest
from textual.app import App, ComposeResult

from tui.widgets.nav_tree import NavTree, ProjectNode, SessionNode


class NavTreeApp(App):
    """Minimal app for testing NavTree."""

    def __init__(self, index_data: dict):
        super().__init__()
        self.index_data = index_data
        self.selected_session = None

    def compose(self) -> ComposeResult:
        yield NavTree(self.index_data)

    def on_nav_tree_session_selected(self, event: NavTree.SessionSelected) -> None:
        self.selected_session = event.session_node


async def test_tree_populates_projects(sample_index):
    app = NavTreeApp(sample_index)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        # Root should have 2 project nodes
        assert len(tree.root.children) == 2
        assert tree.root.children[0].data.display_name == "project/alpha"
        assert tree.root.children[1].data.display_name == "project/beta"


async def test_project_node_has_session_children(sample_index):
    app = NavTreeApp(sample_index)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        project_node = tree.root.children[0]
        # Sessions should be added as leaf children of the project
        assert len(project_node.children) == 1
        session_data = project_node.children[0].data
        assert isinstance(session_data, SessionNode)
        assert session_data.session_id == "sess-001"


async def test_session_nodes_are_leaves(sample_index):
    """Session nodes should be leaf nodes, not expandable parents."""
    app = NavTreeApp(sample_index)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        session_node = tree.root.children[0].children[0]
        assert len(session_node.children) == 0
        assert session_node.allow_expand is False
