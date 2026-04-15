# ABOUTME: Chat view widget for displaying grouped agent message streams.
# ABOUTME: Wraps Textual's OptionList to render headers, content lines, and tool summaries.

from rich.markup import escape
from rich.text import Text
from textual.app import ComposeResult
from textual.css.query import NoMatches
from textual.message import Message
from textual.widget import Widget
from textual.widgets import OptionList
from textual.widgets.option_list import Option


def _single_line(markup: str) -> Text:
    """Render markup as a Rich Text forced onto a single terminal line.

    OptionList scroll math tracks options by index but renders per terminal
    line, so any option whose content wraps across multiple lines causes the
    highlight to drift from the scroll offset. Ellipsizing excess content
    keeps every option exactly one line tall.
    """
    text = Text.from_markup(markup, overflow="ellipsis")
    text.no_wrap = True
    return text


def is_empty_message(msg: dict) -> bool:
    """Check if a message has no content and no tool use."""
    return not msg.get("content") and not msg.get("toolUse")


def format_tool_summary(tool: dict) -> str:
    """Format a tool use block as a one-line summary."""
    name = tool.get("tool", "Unknown")
    summary = tool.get("summary", "")
    tool_input = tool.get("input", {})

    # Use the pre-computed summary if it contains useful detail
    if summary and summary != name:
        return f"⚙ {summary}"

    # Fall back to extracting key info from input
    if "file_path" in tool_input:
        return f"⚙ {name} → {tool_input['file_path']}"
    if "command" in tool_input:
        cmd = tool_input["command"]
        if len(cmd) > 60:
            cmd = cmd[:57] + "..."
        return f"⚙ {name} → {cmd}"
    if "url" in tool_input:
        return f"⚙ {name} → {tool_input['url']}"
    if "pattern" in tool_input:
        return f"⚙ {name} → {tool_input['pattern']}"

    return f"⚙ {name}"


def matches_search(msg: dict, query: str) -> bool:
    """Check if a message matches a search query (case-insensitive)."""
    if not query:
        return True
    return query.lower() in msg.get("_search_text", msg.get("content", "").lower())


def filter_by_agents(messages: list[dict], agent_types: set[str]) -> list[dict]:
    """Filter messages to only those from the specified agent types."""
    if not agent_types:
        return messages
    return [m for m in messages if m.get("agentType") in agent_types]


def _precompute_messages(messages: list[dict]) -> None:
    """Annotate messages with cached formatting for render and search."""
    for msg in messages:
        msg["_is_empty"] = not msg.get("content") and not msg.get("toolUse")
        tools = msg.get("toolUse", [])
        msg["_tool_summaries"] = [format_tool_summary(t) for t in tools]
        # Single search string: content + all tool names + all tool summaries
        parts = [msg.get("content", "")]
        for tool in tools:
            parts.append(tool.get("tool", ""))
            parts.append(tool.get("summary", ""))
        msg["_search_text"] = "\n".join(parts).lower()


def _build_rows(
    messages: list[dict], agent_types: dict
) -> list[tuple[str, int]]:
    """Convert filtered messages into a flat list of (markup, msg_index) rows."""
    rows: list[tuple[str, int]] = []
    prev_agent = None

    for msg_idx, msg in enumerate(messages):
        agent_type = msg.get("agentType", "unknown")
        agent_id = msg.get("agentId", "")
        role = msg.get("role", "assistant")
        timestamp = msg.get("timestamp", "")[:16].replace("T", " ")

        type_info = agent_types.get(agent_type, {})
        color = type_info.get("color", "#888888")
        label = type_info.get("label", agent_type)

        if agent_id != prev_agent:
            dim_open = "[dim]" if role == "user" else ""
            dim_close = "[/dim]" if role == "user" else ""
            header = f"{dim_open}[bold {color}]{label}[/] [dim]{timestamp}[/]{dim_close}"
            rows.append((header, msg_idx))
            prev_agent = agent_id

        content = msg.get("content", "")
        if content:
            first_line = content.split("\n", 1)[0]
            if len(first_line) > 120:
                first_line = first_line[:117] + "…"
            elif "\n" in content:
                first_line = first_line + "…"
            escaped = escape(first_line)
            if role == "user":
                rows.append((f"[dim]{escaped}[/dim]", msg_idx))
            else:
                rows.append((escaped, msg_idx))

        for summary in msg.get("_tool_summaries", []):
            rows.append((f"[dim]{escape(summary)}[/]", msg_idx))

    return rows


class _ChatOptionList(OptionList):
    """OptionList variant that clamps at both ends instead of wrapping."""

    def action_cursor_up(self) -> None:
        if self.highlighted is None or self.highlighted <= 0:
            return
        self.highlighted -= 1

    def action_cursor_down(self) -> None:
        if self.highlighted is None:
            if self.option_count:
                self.highlighted = 0
            return
        if self.highlighted >= self.option_count - 1:
            return
        self.highlighted += 1


class ChatView(Widget):
    """Chat view rendering grouped agent messages via an OptionList."""

    DEFAULT_CSS = """
    ChatView {
        width: 3fr;
        height: 3fr;
        min-width: 40;
        layout: vertical;
        overflow: hidden;
    }
    ChatView > OptionList {
        height: 1fr;
        border: none;
        padding: 0;
        background: $surface;
    }
    ChatView > OptionList:focus {
        border: none;
    }
    ChatView > OptionList > .option-list--option-highlighted {
        background: $accent-darken-1;
    }
    """

    can_focus = True

    def allow_focus(self) -> bool:
        """ChatView delegates focus to its inner OptionList.

        ``can_focus = True`` is kept at the class level as a documented contract,
        but Textual's focus cycling should land on the OptionList directly — it is
        the widget that actually consumes keyboard input. Returning False here
        keeps ChatView out of the tab-focus chain while ``chat.focus()`` still
        routes focus to the inner list (so ``chat.has_focus_within`` becomes True).
        """
        return False

    class MessageFocused(Message):
        """Posted when cursor moves to a different message."""
        def __init__(self, message: dict) -> None:
            super().__init__()
            self.message = message

    EMPTY_STATE_HINT = "Select a session from the tree"
    EMPTY_FILTER_HINT = "No messages match current filters"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.message_count = 0
        self._all_messages: list[dict] = []
        self._filtered_messages: list[dict] = []
        self._row_msg_idx: list[int] = []
        self._last_focused_msg_idx = -1
        self._meeting_data = None
        self._agent_types = {}
        self._search_query = ""
        self._agent_filter: set[str] = set()

    def compose(self) -> ComposeResult:
        yield _ChatOptionList(id="chat-options")

    def on_mount(self) -> None:
        """Start in the empty state until a session is loaded."""
        self._show_empty_hint(self.EMPTY_STATE_HINT)

    def focus(self, scroll_visible: bool = True):
        """Delegate focus to the inner OptionList so keyboard navigation works."""
        option_list = self._option_list
        if option_list is not None:
            option_list.focus(scroll_visible=scroll_visible)
        return self

    @property
    def _option_list(self) -> OptionList | None:
        try:
            return self.query_one("#chat-options", OptionList)
        except NoMatches:
            return None

    def clear_meeting(self) -> None:
        """Clear the current session and show the empty state."""
        self._meeting_data = None
        self._agent_types = {}
        self._all_messages = []
        self._filtered_messages = []
        self._row_msg_idx = []
        self._last_focused_msg_idx = -1
        self._search_query = ""
        self._agent_filter = set()
        self.message_count = 0
        self._show_empty_hint(self.EMPTY_STATE_HINT)

    def load_messages(self, meeting_data: dict, agent_types: dict) -> None:
        """Load and render a session's messages."""
        self._meeting_data = meeting_data
        self._agent_types = agent_types
        self._search_query = ""
        self._agent_filter = set()
        raw = meeting_data.get("messages", [])
        _precompute_messages(raw)
        self._all_messages = [m for m in raw if not m.get("_is_empty")]
        self._apply_and_render()

    def apply_filters(self, search_query: str = "", agent_filter: set[str] | None = None) -> None:
        """Apply search and agent filters, then refresh the option list."""
        self._search_query = search_query
        self._agent_filter = agent_filter or set()
        self._apply_and_render()

    def _apply_and_render(self) -> None:
        """Filter messages, build rows, and repopulate the option list."""
        messages = self._all_messages
        if self._agent_filter:
            messages = filter_by_agents(messages, self._agent_filter)
        if self._search_query:
            messages = [m for m in messages if matches_search(m, self._search_query)]
        self._filtered_messages = messages
        self.message_count = len(messages)
        rows = _build_rows(messages, self._agent_types)
        self._last_focused_msg_idx = -1

        if self.message_count == 0:
            self._row_msg_idx = []
            hint = self.EMPTY_STATE_HINT if not self._all_messages else self.EMPTY_FILTER_HINT
            self._show_empty_hint(hint)
            return

        self._row_msg_idx = [r[1] for r in rows]
        option_list = self._option_list
        if option_list is None:
            return
        options = [
            Option(_single_line(markup), id=str(i))
            for i, (markup, _idx) in enumerate(rows)
        ]
        option_list.clear_options()
        option_list.add_options(options)
        if options:
            option_list.highlighted = 0

    def _show_empty_hint(self, text: str) -> None:
        """Populate the option list with a single disabled hint option."""
        self._row_msg_idx = []
        option_list = self._option_list
        if option_list is None:
            return
        option_list.clear_options()
        option_list.add_option(Option(_single_line(f"[dim]{text}[/]"), disabled=True))

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        """Post MessageFocused when the highlighted option maps to a new source message."""
        event.stop()
        idx = event.option_index
        if idx is None or idx < 0 or idx >= len(self._row_msg_idx):
            return
        msg_idx = self._row_msg_idx[idx]
        if msg_idx == self._last_focused_msg_idx:
            return
        self._last_focused_msg_idx = msg_idx
        if 0 <= msg_idx < len(self._filtered_messages):
            self.post_message(self.MessageFocused(self._filtered_messages[msg_idx]))

    def get_all_messages(self) -> list[dict]:
        """Return the current session's non-empty messages."""
        return list(self._all_messages)
