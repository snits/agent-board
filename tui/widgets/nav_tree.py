# ABOUTME: Navigation tree widget for project/session/meeting hierarchy.
# ABOUTME: Supports lazy loading of sessions and posts meeting selection events.

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
    meeting_count: int
    agent_count: int
    loaded: bool = False


@dataclass
class MeetingNode:
    """Data for a meeting tree node."""
    meeting_id: str
    session_id: str
    project_slug: str
    project_display_name: str
    team_name: str
    message_count: int


class NavTree(Tree):
    """Project/session/meeting navigation tree."""

    DEFAULT_CSS = """
    NavTree {
        width: 1fr;
        min-width: 20;
        border-right: solid $surface-lighten-2;
        padding: 0;
    }
    """

    class MeetingSelected(Message):
        """Posted when a meeting node is selected."""

        def __init__(self, meeting_node: MeetingNode) -> None:
            super().__init__()
            self.meeting_node = meeting_node

    def __init__(self, index_data: dict, **kwargs) -> None:
        super().__init__("Projects", **kwargs)
        self.show_root = False
        self._populate_from_index(index_data)

    def _populate_from_index(self, index_data: dict) -> None:
        """Build the project → session tree from index data."""
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
                    meeting_count=session["meetingCount"],
                    agent_count=session["agentCount"],
                )
                project_node.add(label, data=session_data)

    def load_session_meetings(self, node, session_data: dict) -> None:
        """Populate a session node with its meetings from loaded session data."""
        if not session_data:
            return
        session_node_data = node.data
        if session_node_data.loaded:
            return
        session_node_data.loaded = True

        for meeting in session_data.get("meetings", []):
            label = f"{meeting['teamName']} ({meeting['messageCount']} msgs)"
            meeting_data = MeetingNode(
                meeting_id=meeting["id"],
                session_id=session_node_data.session_id,
                project_slug=session_node_data.project_slug,
                project_display_name=session_node_data.project_display_name,
                team_name=meeting["teamName"],
                message_count=meeting["messageCount"],
            )
            node.add_leaf(label, data=meeting_data)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle node selection — post MeetingSelected for meeting nodes."""
        if isinstance(event.node.data, MeetingNode):
            self.post_message(self.MeetingSelected(event.node.data))
