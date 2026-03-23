# ABOUTME: Navigation tree widget for project/session hierarchy.
# ABOUTME: Supports session selection events for message loading.

from dataclasses import dataclass

from textual.message import Message
from textual.widgets import Tree


@dataclass
class ProjectNode:
    """Data for a project tree node."""
    slug: str
    display_name: str


@dataclass
class SessionNode:
    """Data for a session tree node."""
    session_id: str
    project_slug: str
    project_display_name: str
    agent_count: int
    start_time: str = ""


class NavTree(Tree):
    """Project/session navigation tree."""

    DEFAULT_CSS = """
    NavTree {
        width: 1fr;
        min-width: 20;
        border-right: solid $surface-lighten-2;
        padding: 0;
    }
    """

    class SessionSelected(Message):
        """Posted when a session node is selected."""

        def __init__(self, session_node: SessionNode) -> None:
            super().__init__()
            self.session_node = session_node

    def __init__(self, index_data: dict, **kwargs) -> None:
        super().__init__("Projects", **kwargs)
        self.show_root = False
        self._populate_from_index(index_data)

    def _session_label(self, start: str, agent_count: int) -> str:
        """Format a session node label based on start time and agent count."""
        if agent_count >= 2:
            return f"{start} · {agent_count} agents"
        if agent_count == 1:
            return f"{start} · 1 agent"
        return start

    def _populate_from_index(self, index_data: dict) -> None:
        """Build the project -> session tree from index data."""
        for project in index_data.get("projects", []):
            sessions = project.get("sessions", [])
            project_data = ProjectNode(
                slug=project["slug"],
                display_name=project["displayName"],
            )
            project_label = f"{project['displayName']} ({len(sessions)})"
            project_node = self.root.add(project_label, data=project_data)

            sorted_sessions = sorted(
                sessions,
                key=lambda s: s.get("startTime") or "",
                reverse=True,
            )

            for session in sorted_sessions:
                raw_start = session.get("startTime")
                start = raw_start[:16].replace("T", " ") if raw_start else "—"
                label = self._session_label(start, session["agentCount"])
                session_data = SessionNode(
                    session_id=session["id"],
                    project_slug=project["slug"],
                    project_display_name=project["displayName"],
                    agent_count=session["agentCount"],
                    start_time=session.get("startTime", ""),
                )
                project_node.add_leaf(label, data=session_data)

    def reload(self, index_data: dict) -> None:
        """Clear and rebuild the tree from fresh index data."""
        self.clear()
        self._populate_from_index(index_data)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle node selection — post SessionSelected for session nodes."""
        if isinstance(event.node.data, SessionNode):
            self.post_message(self.SessionSelected(event.node.data))
