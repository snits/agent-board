# ABOUTME: Chat view widget for displaying grouped agent message streams.
# ABOUTME: Renders tool use summaries and supports agent grouping via a virtual-scroll widget pool.

from textual.events import Key, Resize
from textual.widget import Widget
from textual.widgets import Static


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
) -> list[tuple[str, str]]:
    """Convert filtered messages into a flat list of (markup, css_class) rows."""
    rows: list[tuple[str, str]] = []
    prev_agent = None

    for msg_idx, msg in enumerate(messages):
        agent_type = msg.get("agentType", "unknown")
        agent_id = msg.get("agentId", "")
        role = msg.get("role", "assistant")
        timestamp = msg.get("timestamp", "")[:16].replace("T", " ")

        type_info = agent_types.get(agent_type, {})
        color = type_info.get("color", "#888888")
        label = type_info.get("label", agent_type)

        alt = " msg-alt" if msg_idx % 2 == 1 else ""

        if agent_id != prev_agent:
            dim_open = "[dim]" if role == "user" else ""
            dim_close = "[/dim]" if role == "user" else ""
            header = f"{dim_open}[bold {color}]{label}[/] [dim]{timestamp}[/]{dim_close}"
            rows.append((header, f"msg-header{alt}"))
            prev_agent = agent_id

        content = msg.get("content", "")
        if content:
            first_line = content.split("\n", 1)[0]
            if len(first_line) > 120:
                first_line = first_line[:117] + "…"
            elif "\n" in content:
                first_line = first_line + "…"
            css_class = "msg-content msg-user" if role == "user" else "msg-content"
            rows.append((first_line, f"{css_class}{alt}"))

        for summary in msg.get("_tool_summaries", []):
            rows.append((f"[dim]{summary}[/]", f"tool-summary{alt}"))

    return rows


class ChatView(Widget):
    """Virtual-scroll chat view using a fixed widget pool."""

    DEFAULT_CSS = """
    ChatView {
        width: 3fr;
        min-width: 40;
        layout: vertical;
        overflow: hidden;
    }
    ChatView .msg-user {
        color: $text-muted;
    }
    ChatView .msg-alt {
        background: $surface-darken-1;
    }
    """

    can_focus = True

    EMPTY_STATE_HINT = "Select a session from the tree"
    EMPTY_FILTER_HINT = "No messages match current filters"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.message_count = 0
        self._all_messages: list[dict] = []
        self._filtered_messages: list[dict] = []
        self._rows: list[tuple[str, str]] = []
        self._pool: list[Static] = []
        self._scroll_offset = 0
        self._meeting_data = None
        self._agent_types = {}
        self._search_query = ""
        self._agent_filter: set[str] = set()

    def on_mount(self) -> None:
        """Build the widget pool sized to the viewport."""
        self._build_pool()
        if not self._meeting_data:
            self._show_empty_hint(self.EMPTY_STATE_HINT)

    def on_resize(self, event: Resize) -> None:
        """Rebuild pool when terminal is resized."""
        self._build_pool()
        if self._rows:
            self._refresh_pool()
        elif not self._meeting_data:
            self._show_empty_hint(self.EMPTY_STATE_HINT)

    def _build_pool(self) -> None:
        """Create or recreate the fixed pool of Static widgets."""
        self.remove_children()
        self._pool = []
        pool_size = self.size.height
        for _ in range(pool_size):
            widget = Static("")
            self.mount(widget)
            self._pool.append(widget)

    def clear_meeting(self) -> None:
        """Clear the current session and show the empty state."""
        self._meeting_data = None
        self._agent_types = {}
        self._all_messages = []
        self._filtered_messages = []
        self._rows = []
        self._scroll_offset = 0
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
        """Apply search and agent filters, then refresh the pool."""
        self._search_query = search_query
        self._agent_filter = agent_filter or set()
        self._apply_and_render()

    def _apply_and_render(self) -> None:
        """Filter messages, build rows, and refresh the pool."""
        messages = self._all_messages
        if self._agent_filter:
            messages = filter_by_agents(messages, self._agent_filter)
        if self._search_query:
            messages = [m for m in messages if matches_search(m, self._search_query)]
        self._filtered_messages = messages
        self.message_count = len(messages)
        self._rows = _build_rows(messages, self._agent_types)
        self._scroll_offset = 0
        if self.message_count == 0:
            hint = self.EMPTY_STATE_HINT if not self._all_messages else self.EMPTY_FILTER_HINT
            self._show_empty_hint(hint)
        else:
            self._refresh_pool()

    def _show_empty_hint(self, text: str) -> None:
        """Display a hint message using the pool."""
        self._rows = []
        for widget in self._pool:
            widget.update("")
            widget.set_classes("")
        if self._pool:
            mid = len(self._pool) // 3
            self._pool[mid].update(f"[dim]{text}[/]")

    def _refresh_pool(self) -> None:
        """Update pool widget content from rows at current scroll offset."""
        for i, widget in enumerate(self._pool):
            row_idx = self._scroll_offset + i
            if row_idx < len(self._rows):
                markup, css_class = self._rows[row_idx]
                widget.update(markup)
                widget.set_classes(css_class)
            else:
                widget.update("")
                widget.set_classes("")

    def _clamp_offset(self) -> None:
        """Ensure scroll offset stays within valid bounds."""
        max_offset = max(0, len(self._rows) - len(self._pool))
        self._scroll_offset = max(0, min(self._scroll_offset, max_offset))

    def on_key(self, event: Key) -> None:
        """Handle scroll keys."""
        if not self._rows:
            return
        pool_size = len(self._pool)
        if event.key == "down":
            self._scroll_offset += 1
        elif event.key == "up":
            self._scroll_offset -= 1
        elif event.key == "pagedown":
            self._scroll_offset += pool_size
        elif event.key == "pageup":
            self._scroll_offset -= pool_size
        elif event.key == "home":
            self._scroll_offset = 0
        elif event.key == "end":
            self._scroll_offset = max(0, len(self._rows) - len(self._pool))
        else:
            return
        event.prevent_default()
        self._clamp_offset()
        self._refresh_pool()

    def get_all_messages(self) -> list[dict]:
        """Return the current session's non-empty messages."""
        return list(self._all_messages)
