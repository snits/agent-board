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

    def _populate_from_index(self, index_data: dict) -> None:
        """Build the project -> session tree from index data."""
        for project in index_data.get("projects", []):
            project_data = ProjectNode(
                slug=project["slug"],
                display_name=project["displayName"],
            )
            project_node = self.root.add(project["displayName"], data=project_data)

            for session in project.get("sessions", []):
                start = session["startTime"][:16].replace("T", " ")
                label = f"{start} ({session['agentCount']} agents)"
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
