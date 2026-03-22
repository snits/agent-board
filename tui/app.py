# ABOUTME: Main Textual application for the Agent Board TUI.
# ABOUTME: Composes widgets, handles keybindings, and manages data loading.

from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Tree

from tui.data import load_index, load_agent_types, load_session, load_meeting
from tui.widgets.agent_bar import AgentBar
from tui.widgets.chat_view import ChatView
from tui.widgets.nav_tree import NavTree, SessionNode, MeetingNode
from tui.widgets.search_bar import SearchBar


class AgentBoardApp(App):
    """Terminal viewer for Claude Code agent team transcripts."""

    TITLE = "Agent Board"

    CSS = """
    Screen {
        layout: vertical;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("slash", "show_search", "Search", key_display="/", priority=True),
        Binding("f", "toggle_agent_filter", "Filter agents"),
        Binding("t", "toggle_tools", "Toggle tools"),
        Binding("tab", "switch_focus", "Switch panel", show=False),
        Binding("escape", "escape", "Back", show=False, priority=True),
        Binding("n", "next_meeting", "Next meeting", show=False),
        Binding("p", "prev_meeting", "Prev meeting", show=False),
    ]

    def __init__(self, data_dir: Path | str = "data", **kwargs) -> None:
        super().__init__(**kwargs)
        self._data_dir = Path(data_dir)
        self._agent_types = {}
        self._current_meeting_node: MeetingNode | None = None
        self._meeting_list: list[MeetingNode] = []
        self._search_query = ""
        self._agent_filter: set[str] = set()

    def compose(self) -> ComposeResult:
        index_data = load_index(self._data_dir)
        self._agent_types = load_agent_types(self._data_dir)

        yield AgentBar()
        with Horizontal():
            yield NavTree(index_data, id="nav-tree")
            yield ChatView(id="chat-view")
        yield SearchBar(id="search-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Set initial focus to the nav tree."""
        self.query_one("#nav-tree", NavTree).focus()

    @on(Tree.NodeExpanded)
    def on_tree_expand(self, event: Tree.NodeExpanded) -> None:
        """Lazy-load session meetings when a session node is expanded."""
        node_data = event.node.data
        if isinstance(node_data, SessionNode) and not node_data.loaded:
            session = load_session(self._data_dir, node_data.session_id)
            if session:
                tree = self.query_one(NavTree)
                tree.load_session_meetings(event.node, session)

    @on(NavTree.MeetingSelected)
    def on_meeting_selected(self, event: NavTree.MeetingSelected) -> None:
        """Load and display the selected meeting."""
        meeting_node = event.meeting_node
        self._load_meeting(meeting_node)

    def _load_meeting(self, meeting_node: MeetingNode) -> None:
        """Load meeting data and update all widgets."""
        self._current_meeting_node = meeting_node
        meeting_data = load_meeting(
            self._data_dir, meeting_node.session_id, meeting_node.meeting_id
        )
        if not meeting_data:
            return

        # Update agent bar
        breadcrumb = [
            meeting_node.project_display_name,
            meeting_node.session_id[:8],
            meeting_node.team_name,
        ]
        self.query_one(AgentBar).update_meeting(
            meeting_data.get("agents", []),
            self._agent_types,
            breadcrumb,
        )

        # Update chat view
        self.query_one(ChatView).load_meeting(meeting_data, self._agent_types)

    def action_show_search(self) -> None:
        """Show the search bar."""
        self.query_one(SearchBar).show()

    def action_escape(self) -> None:
        """Handle Escape — hide search, clear filters, or return focus."""
        search = self.query_one(SearchBar)
        if search.has_class("-visible"):
            search.hide()
            return
        if self._agent_filter:
            self._agent_filter.clear()
            self._apply_filters()
            return
        self.query_one("#nav-tree", NavTree).focus()

    def action_toggle_tools(self) -> None:
        """Toggle tool use detail level."""
        self.query_one(ChatView).toggle_tool_detail()

    def action_switch_focus(self) -> None:
        """Toggle focus between nav tree and chat view."""
        nav = self.query_one("#nav-tree", NavTree)
        chat = self.query_one("#chat-view", ChatView)
        if nav.has_focus:
            chat.focus()
        else:
            nav.focus()

    def action_toggle_agent_filter(self) -> None:
        """Cycle through agent type filters."""
        if not self._agent_types:
            return
        type_list = sorted(self._agent_types.keys())
        if not self._agent_filter:
            # Start with first type
            self._agent_filter = {type_list[0]}
        else:
            # Cycle to next type
            current = next(iter(self._agent_filter))
            idx = type_list.index(current) if current in type_list else -1
            next_idx = (idx + 1) % (len(type_list) + 1)
            if next_idx == len(type_list):
                self._agent_filter.clear()
            else:
                self._agent_filter = {type_list[next_idx]}
        self._apply_filters()

    def action_next_meeting(self) -> None:
        """Navigate to the next meeting in the current session."""
        self._navigate_meeting(1)

    def action_prev_meeting(self) -> None:
        """Navigate to the previous meeting in the current session."""
        self._navigate_meeting(-1)

    def _navigate_meeting(self, direction: int) -> None:
        """Navigate meetings by offset within the nav tree."""
        if not self._current_meeting_node:
            return
        tree = self.query_one(NavTree)
        # Find all meeting nodes in the tree
        meetings = []
        for project_node in tree.root.children:
            for session_node in project_node.children:
                for meeting_leaf in session_node.children:
                    if isinstance(meeting_leaf.data, MeetingNode):
                        meetings.append(meeting_leaf.data)
        if not meetings:
            return
        # Find current index
        current_idx = None
        for i, m in enumerate(meetings):
            if m.meeting_id == self._current_meeting_node.meeting_id:
                current_idx = i
                break
        if current_idx is None:
            return
        new_idx = current_idx + direction
        if 0 <= new_idx < len(meetings):
            self._load_meeting(meetings[new_idx])

    @on(SearchBar.SearchChanged)
    def on_search_changed(self, event: SearchBar.SearchChanged) -> None:
        """Apply search filter to chat view."""
        self._search_query = event.query
        self._apply_filters()

    def _apply_filters(self) -> None:
        """Re-render chat view with current search and agent filters."""
        chat = self.query_one(ChatView)
        if not chat._meeting_data:
            return
        chat.apply_filters(self._search_query, self._agent_filter)
