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


async def test_tree_handles_null_start_time():
    """Sessions with null startTime should not crash the tree."""
    index_data = {
        "projects": [
            {
                "slug": "-test-project",
                "displayName": "test/project",
                "sessions": [
                    {
                        "id": "sess-null",
                        "startTime": None,
                        "endTime": None,
                        "agentCount": 0,
                    },
                    {
                        "id": "sess-ok",
                        "startTime": "2026-03-20T10:00:00.000Z",
                        "endTime": "2026-03-20T11:00:00.000Z",
                        "agentCount": 2,
                    },
                ],
            }
        ]
    }
    app = NavTreeApp(index_data)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        project_node = tree.root.children[0]
        # Both sessions should render without crashing
        assert len(project_node.children) == 2
        # Dated session sorts first (most recent first), null sorts last
        ok_session = project_node.children[0]
        assert "2026-03-20" in str(ok_session.label)
        # Null-timestamp session should show a fallback label
        null_session = project_node.children[1]
        assert "—" in str(null_session.label)


async def test_sessions_sorted_most_recent_first():
    """Sessions should be sorted by startTime descending (most recent first)."""
    index_data = {
        "projects": [
            {
                "slug": "-test-sort",
                "displayName": "test/sort",
                "sessions": [
                    {
                        "id": "sess-old",
                        "startTime": "2026-01-01T10:00:00.000Z",
                        "endTime": "2026-01-01T11:00:00.000Z",
                        "agentCount": 0,
                    },
                    {
                        "id": "sess-new",
                        "startTime": "2026-03-20T10:00:00.000Z",
                        "endTime": "2026-03-20T11:00:00.000Z",
                        "agentCount": 0,
                    },
                    {
                        "id": "sess-mid",
                        "startTime": "2026-02-15T10:00:00.000Z",
                        "endTime": "2026-02-15T11:00:00.000Z",
                        "agentCount": 0,
                    },
                ],
            }
        ]
    }
    app = NavTreeApp(index_data)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        project_node = tree.root.children[0]
        assert project_node.children[0].data.session_id == "sess-new"
        assert project_node.children[1].data.session_id == "sess-mid"
        assert project_node.children[2].data.session_id == "sess-old"


async def test_sessions_with_null_start_time_sort_last():
    """Sessions with null startTime should sort after sessions with a startTime."""
    index_data = {
        "projects": [
            {
                "slug": "-test-null-sort",
                "displayName": "test/nullsort",
                "sessions": [
                    {
                        "id": "sess-null",
                        "startTime": None,
                        "endTime": None,
                        "agentCount": 0,
                    },
                    {
                        "id": "sess-dated",
                        "startTime": "2026-03-20T10:00:00.000Z",
                        "endTime": "2026-03-20T11:00:00.000Z",
                        "agentCount": 0,
                    },
                ],
            }
        ]
    }
    app = NavTreeApp(index_data)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        project_node = tree.root.children[0]
        assert project_node.children[0].data.session_id == "sess-dated"
        assert project_node.children[1].data.session_id == "sess-null"


async def test_project_label_includes_session_count(sample_index):
    """Project node labels should include the session count in parentheses."""
    app = NavTreeApp(sample_index)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        project_node = tree.root.children[0]
        # sample_index has 1 session for project/alpha
        assert "project/alpha" in str(project_node.label)
        assert "(1)" in str(project_node.label)


async def test_session_label_multi_agent():
    """Sessions with 2+ agents should show '{start} · {n} agents'."""
    index_data = {
        "projects": [
            {
                "slug": "-test-labels",
                "displayName": "test/labels",
                "sessions": [
                    {
                        "id": "sess-multi",
                        "startTime": "2026-03-20T10:00:00.000Z",
                        "endTime": "2026-03-20T11:00:00.000Z",
                        "agentCount": 3,
                    },
                ],
            }
        ]
    }
    app = NavTreeApp(index_data)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        session_node = tree.root.children[0].children[0]
        label = str(session_node.label)
        assert "2026-03-20 10:00" in label
        assert "· 3 agents" in label
        assert "(" not in label


async def test_session_label_single_agent():
    """Sessions with agentCount == 1 should show '{start} · 1 agent'."""
    index_data = {
        "projects": [
            {
                "slug": "-test-single-agent",
                "displayName": "test/single",
                "sessions": [
                    {
                        "id": "sess-one",
                        "startTime": "2026-03-20T10:00:00.000Z",
                        "endTime": "2026-03-20T11:00:00.000Z",
                        "agentCount": 1,
                    },
                ],
            }
        ]
    }
    app = NavTreeApp(index_data)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        session_node = tree.root.children[0].children[0]
        label = str(session_node.label)
        assert "2026-03-20 10:00" in label
        assert "· 1 agent" in label
        assert "agents" not in label


async def test_session_label_no_agent():
    """Sessions with agentCount == 0 should show just the date, no agent qualifier."""
    index_data = {
        "projects": [
            {
                "slug": "-test-no-agent",
                "displayName": "test/noagent",
                "sessions": [
                    {
                        "id": "sess-zero",
                        "startTime": "2026-03-20T10:00:00.000Z",
                        "endTime": "2026-03-20T11:00:00.000Z",
                        "agentCount": 0,
                    },
                ],
            }
        ]
    }
    app = NavTreeApp(index_data)
    async with app.run_test() as pilot:
        tree = app.query_one(NavTree)
        session_node = tree.root.children[0].children[0]
        label = str(session_node.label)
        assert "2026-03-20 10:00" in label
        assert "agent" not in label
        assert "·" not in label
