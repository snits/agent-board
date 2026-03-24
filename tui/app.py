# ABOUTME: Main Textual application for the Agent Board TUI.
# ABOUTME: Composes widgets, handles keybindings, and manages data loading.

import contextlib
import io
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer

from preprocessor.paths import default_archive_dir, default_data_dir, default_source_dir
from preprocessor.pipeline import run_preprocess
from tui.data import load_index, load_agent_types, load_session, load_messages
from tui.widgets.agent_bar import AgentBar
from tui.widgets.chat_view import ChatView
from tui.widgets.detail_pane import DetailPane
from tui.widgets.nav_tree import NavTree, SessionNode
from tui.widgets.search_bar import SearchBar


class AgentBoardApp(App):
    """Terminal viewer for Claude Code agent team transcripts."""

    TITLE = "Agent Board"

    CSS = """
    Screen {
        layout: vertical;
    }
    #chat-column {
        width: 3fr;
    }
    #chat-column > ChatView {
        width: 1fr;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("slash", "show_search", "Search", key_display="/", priority=True),
        Binding("f", "toggle_agent_filter", "Filter agents"),

        Binding("v", "toggle_detail", "Detail", show=False),
        Binding("tab", "switch_focus", "Switch panel", show=False),
        Binding("escape", "escape", "Back", show=False, priority=True),
        Binding("r", "refresh_data", "Refresh data"),
    ]

    def __init__(
        self,
        data_dir: Path | str | None = None,
        source_dir: Path | str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._data_dir = Path(data_dir) if data_dir is not None else default_data_dir()
        self._source_dir = Path(source_dir) if source_dir is not None else default_source_dir()
        self._agent_types = {}
        self._current_session_node: SessionNode | None = None
        self._search_query = ""
        self._agent_filter: set[str] = set()

    def compose(self) -> ComposeResult:
        index_data = load_index(self._data_dir)
        self._agent_types = load_agent_types(self._data_dir)

        yield AgentBar()
        with Horizontal():
            yield NavTree(index_data, id="nav-tree")
            with Vertical(id="chat-column"):
                yield ChatView(id="chat-view")
                yield DetailPane(agent_types=self._agent_types, id="detail-pane")
        yield SearchBar(id="search-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Set initial focus to the nav tree."""
        self.query_one("#nav-tree", NavTree).focus()

    @on(NavTree.SessionSelected)
    def on_session_selected(self, event: NavTree.SessionSelected) -> None:
        """Load and display the selected session's messages."""
        self._load_session_data(event.session_node)

    def _load_session_data(self, session_node: SessionNode) -> None:
        """Load session data and update all widgets."""
        self._current_session_node = session_node
        session_data = load_session(self._data_dir, session_node.session_id)
        messages = load_messages(self._data_dir, session_node.session_id)
        if not session_data or messages is None:
            return

        # 2-part breadcrumb
        session_label = session_node.start_time[:16].replace("T", " ")
        if not session_label:
            session_label = session_node.session_id[:8]
        breadcrumb = [session_node.project_display_name, session_label]

        self.query_one(AgentBar).update_meeting(
            session_data.get("agents", []),
            self._agent_types,
            breadcrumb,
        )
        self.query_one(ChatView).load_messages(
            {"messages": messages, "agents": session_data.get("agents", [])},
            self._agent_types,
        )

    def action_toggle_detail(self) -> None:
        """Toggle the detail pane."""
        chat = self.query_one(ChatView)
        if not chat._meeting_data:
            return
        pane = self.query_one(DetailPane)
        if pane.is_visible:
            pane.hide()
        else:
            pane.show()

    @on(ChatView.MessageFocused)
    def on_message_focused(self, event: ChatView.MessageFocused) -> None:
        """Route focused message to the detail pane."""
        self.query_one(DetailPane).update_message(event.message)

    def action_refresh_data(self) -> None:
        """Re-run the preprocessor and reload all data."""
        self.notify("Refreshing data...")
        self._run_refresh()

    @work(thread=True)
    def _run_refresh(self) -> None:
        """Run preprocessor in a background thread to avoid blocking the UI."""
        with contextlib.redirect_stdout(io.StringIO()):
            run_preprocess(self._source_dir, self._data_dir, archive_dir=default_archive_dir())
        self.call_from_thread(self._rebuild_after_refresh)

    def _rebuild_after_refresh(self) -> None:
        """Reload data from disk and rebuild the UI after preprocessing."""
        index_data = load_index(self._data_dir)
        self._agent_types = load_agent_types(self._data_dir)
        self._current_session_node = None
        self._search_query = ""
        self._agent_filter.clear()
        self.query_one(NavTree).reload(index_data)
        self.query_one(AgentBar).clear()
        self.query_one(ChatView).clear_meeting()
        self.query_one(DetailPane).hide()
        self.query_one(DetailPane).update_message(None)
        self.notify("Data refreshed")

    def action_show_search(self) -> None:
        """Show the search bar."""
        self.query_one(SearchBar).show()

    def action_escape(self) -> None:
        """Handle Escape — close pane, hide search, clear filters, or return focus."""
        pane = self.query_one(DetailPane)
        if pane.is_visible:
            pane.hide()
            self.query_one(ChatView).focus()
            return
        search = self.query_one(SearchBar)
        if search.has_class("-visible"):
            search.clear()
            return
        if self._search_query:
            search.clear()
            return
        if self._agent_filter:
            self._agent_filter.clear()
            self._apply_filters()
            return
        self.query_one("#nav-tree", NavTree).focus()

    def action_switch_focus(self) -> None:
        """Cycle focus: NavTree -> ChatView -> DetailPane (if visible) -> NavTree."""
        nav = self.query_one("#nav-tree", NavTree)
        chat = self.query_one("#chat-view", ChatView)
        pane = self.query_one("#detail-pane", DetailPane)
        if nav.has_focus_within:
            chat.focus()
        elif chat.has_focus_within:
            if pane.is_visible:
                pane.focus()
            else:
                nav.focus()
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

    @on(SearchBar.SearchChanged)
    def on_search_changed(self, event: SearchBar.SearchChanged) -> None:
        """Apply search filter to chat view."""
        self._search_query = event.query
        self._apply_filters()

    def _apply_filters(self) -> None:
        """Re-render chat view with current search and agent filters."""
        # Update filter indicator in agent bar
        if self._agent_filter:
            current = next(iter(self._agent_filter))
            type_list = sorted(self._agent_types.keys())
            position = type_list.index(current) + 1 if current in type_list else None
            total = len(type_list)
            self.query_one(AgentBar).set_filter(current, position=position, total=total)
        else:
            self.query_one(AgentBar).set_filter(None)

        chat = self.query_one(ChatView)
        if not chat._meeting_data:
            return
        chat.apply_filters(self._search_query, self._agent_filter)
