# ABOUTME: Chat view widget for displaying grouped agent message streams.
# ABOUTME: Renders markdown content, tool use summaries, and supports agent grouping.

import json

from textual.containers import VerticalScroll
from textual.widgets import Markdown, Static


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


def _format_tool_expanded(tool: dict) -> str:
    """Format a tool use block with full input detail."""
    name = tool.get("tool", "Unknown")
    tool_input = tool.get("input", {})
    input_str = json.dumps(tool_input, indent=2)
    return f"⚙ {name}\n```json\n{input_str}\n```"


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
        msg["_tool_expanded_text"] = [_format_tool_expanded(t) for t in tools]
        # Single search string: content + all tool names + all tool summaries
        parts = [msg.get("content", "")]
        for tool in tools:
            parts.append(tool.get("tool", ""))
            parts.append(tool.get("summary", ""))
        msg["_search_text"] = "\n".join(parts).lower()


class ChatView(VerticalScroll):
    """Scrollable chat message stream with grouped agent messages."""

    DEFAULT_CSS = """
    ChatView {
        width: 3fr;
        min-width: 40;
    }
    ChatView .msg-user {
        border-left: thick $accent-darken-2;
        padding-left: 1;
        color: $text-muted;
    }
    ChatView .empty-state {
        margin-top: 2;
        text-align: center;
        width: 100%;
    }
    """

    EMPTY_STATE_HINT = "Select a session from the tree"
    EMPTY_FILTER_HINT = "No messages match current filters"

    PAGE_SIZE = 100

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.message_count = 0
        self._all_messages: list[dict] = []
        self._filtered_messages: list[dict] = []
        self._rendered_count = 0
        self._meeting_data = None
        self._agent_types = {}
        self._tool_expanded = False
        self._search_query = ""
        self._agent_filter: set[str] = set()

    def clear_meeting(self) -> None:
        """Clear the current session and show the empty state."""
        self._meeting_data = None
        self._agent_types = {}
        self._all_messages = []
        self._filtered_messages = []
        self._rendered_count = 0
        self._search_query = ""
        self._agent_filter = set()
        self.message_count = 0
        self._show_empty_state(self.EMPTY_STATE_HINT)

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
        """Apply search and agent filters, then re-render first page."""
        self._search_query = search_query
        self._agent_filter = agent_filter or set()
        self._apply_and_render()

    def on_mount(self) -> None:
        """Show initial empty state on mount."""
        if not self._meeting_data:
            self._show_empty_state(self.EMPTY_STATE_HINT)

    def _show_empty_state(self, text: str) -> None:
        """Display a centered placeholder message."""
        self.remove_children()
        self.mount(Static(f"[dim]{text}[/]", classes="empty-state"))

    def _apply_and_render(self) -> None:
        """Filter messages and render the first page."""
        messages = self._all_messages
        if self._agent_filter:
            messages = filter_by_agents(messages, self._agent_filter)
        if self._search_query:
            messages = [m for m in messages if matches_search(m, self._search_query)]
        self._filtered_messages = messages
        self.message_count = len(messages)
        self.remove_children()
        self._rendered_count = 0
        if self.message_count == 0:
            hint = self.EMPTY_STATE_HINT if not self._all_messages else self.EMPTY_FILTER_HINT
            self._show_empty_state(hint)
            return
        self._render_page()

    def _render_page(self) -> None:
        """Mount the next PAGE_SIZE messages as widgets."""
        for indicator in self.query(".load-more"):
            indicator.remove()

        start = self._rendered_count
        end = min(start + self.PAGE_SIZE, len(self._filtered_messages))
        page = self._filtered_messages[start:end]

        prev_agent = None
        if start > 0 and start <= len(self._filtered_messages):
            prev_msg = self._filtered_messages[start - 1]
            prev_agent = prev_msg.get("agentId")

        for msg in page:
            agent_type = msg.get("agentType", "unknown")
            agent_id = msg.get("agentId", "")
            role = msg.get("role", "assistant")
            timestamp = msg.get("timestamp", "")[:16].replace("T", " ")

            type_info = self._agent_types.get(agent_type, {})
            color = type_info.get("color", "#888888")
            label = type_info.get("label", agent_type)

            if agent_id != prev_agent:
                dim_open = "[dim]" if role == "user" else ""
                dim_close = "[/dim]" if role == "user" else ""
                header = f"{dim_open}[bold {color}]{label}[/] [dim]{timestamp}[/]{dim_close}"
                self.mount(Static(header, classes="msg-header"))
                prev_agent = agent_id

            if msg.get("content"):
                content = msg["content"]
                css_class = "msg-content msg-user" if role == "user" else "msg-content"
                self.mount(Markdown(content, classes=css_class))

            tools = msg.get("toolUse", [])
            for idx, tool in enumerate(tools):
                if self._tool_expanded:
                    self.mount(Markdown(msg["_tool_expanded_text"][idx], classes="tool-detail"))
                else:
                    summary = msg["_tool_summaries"][idx]
                    self.mount(Static(f"[dim]{summary}[/]", classes="tool-summary"))

        self._rendered_count = end

        remaining = len(self._filtered_messages) - self._rendered_count
        if remaining > 0:
            self.mount(Static(
                f"[dim]── {remaining:,} more messages ──[/]",
                classes="load-more",
            ))

    def toggle_tool_detail(self) -> None:
        """Toggle between collapsed and expanded tool use display."""
        self._tool_expanded = not self._tool_expanded
        self._apply_and_render()

    def get_all_messages(self) -> list[dict]:
        """Return the current session's non-empty messages."""
        if not self._all_messages:
            return []
        return [m for m in self._all_messages if not m.get("_is_empty")]
