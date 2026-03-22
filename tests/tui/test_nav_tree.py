# ABOUTME: Tests for the navigation tree widget.
# ABOUTME: Verifies project/session/meeting hierarchy and lazy loading.

import pytest
from textual.app import App, ComposeResult

from tui.widgets.nav_tree import NavTree, ProjectNode, SessionNode, MeetingNode


class NavTreeApp(App):
    """Minimal app for testing NavTree."""

    def __init__(self, index_data: dict):
        super().__init__()
        self.index_data = index_data
        self.selected_meeting = None

    def compose(self) -> ComposeResult:
        yield NavTree(self.index_data)

    def on_nav_tree_meeting_selected(self, event: NavTree.MeetingSelected) -> None:
        self.selected_meeting = event.meeting_node


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
        # Sessions should be added as children of the project
        assert len(project_node.children) == 1
        session_data = project_node.children[0].data
        assert isinstance(session_data, SessionNode)
        assert session_data.session_id == "sess-001"


async def test_session_node_starts_unexpanded(sample_index):
    app = NavTreeApp(sample_index)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        session_node = tree.root.children[0].children[0]
        # Session should not be expanded (meetings loaded lazily)
        assert not session_node.is_expanded
        assert len(session_node.children) == 0
