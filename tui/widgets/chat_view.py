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
    query_lower = query.lower()
    if query_lower in msg.get("content", "").lower():
        return True
    for tool in msg.get("toolUse", []):
        if query_lower in tool.get("summary", "").lower():
            return True
        if query_lower in tool.get("tool", "").lower():
            return True
    return False


def filter_by_agents(messages: list[dict], agent_types: set[str]) -> list[dict]:
    """Filter messages to only those from the specified agent types."""
    if not agent_types:
        return messages
    return [m for m in messages if m.get("agentType") in agent_types]


class ChatView(VerticalScroll):
    """Scrollable chat message stream with grouped agent messages."""

    DEFAULT_CSS = """
    ChatView {
        width: 3fr;
        min-width: 40;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.message_count = 0
        self._meeting_data = None
        self._agent_types = {}
        self._tool_expanded = False
        self._search_query = ""
        self._agent_filter: set[str] = set()

    def load_meeting(self, meeting_data: dict, agent_types: dict) -> None:
        """Load and render a meeting's messages."""
        self._meeting_data = meeting_data
        self._agent_types = agent_types
        self._search_query = ""
        self._agent_filter = set()
        self._render_messages()

    def apply_filters(self, search_query: str = "", agent_filter: set[str] | None = None) -> None:
        """Apply search and agent filters, then re-render."""
        self._search_query = search_query
        self._agent_filter = agent_filter or set()
        self._render_messages()

    def _render_messages(self) -> None:
        """Build message widgets from meeting data."""
        self.remove_children()
        self.message_count = 0

        if not self._meeting_data:
            return

        messages = [m for m in self._meeting_data.get("messages", []) if not is_empty_message(m)]

        # Apply agent filter
        if self._agent_filter:
            messages = filter_by_agents(messages, self._agent_filter)

        # Apply search filter
        if self._search_query:
            messages = [m for m in messages if matches_search(m, self._search_query)]

        self.message_count = len(messages)

        prev_agent = None
        for msg in messages:
            agent_type = msg.get("agentType", "unknown")
            agent_id = msg.get("agentId", "")
            role = msg.get("role", "assistant")
            timestamp = msg.get("timestamp", "")[:16].replace("T", " ")

            type_info = self._agent_types.get(agent_type, {})
            color = type_info.get("color", "#888888")
            label = type_info.get("label", agent_type)

            # Group header — only show when agent changes
            if agent_id != prev_agent:
                dim_open = "[dim]" if role == "user" else ""
                dim_close = "[/dim]" if role == "user" else ""
                header = f"{dim_open}[bold {color}]{label}[/] [dim]{timestamp}[/]{dim_close}"
                self.mount(Static(header, classes="msg-header"))
                prev_agent = agent_id

            # Message content
            if msg.get("content"):
                content = msg["content"]
                css_class = "msg-content msg-user" if role == "user" else "msg-content"
                self.mount(Markdown(content, classes=css_class))

            # Tool use
            for tool in msg.get("toolUse", []):
                if self._tool_expanded:
                    self.mount(Markdown(_format_tool_expanded(tool), classes="tool-detail"))
                else:
                    summary = format_tool_summary(tool)
                    self.mount(Static(f"[dim]{summary}[/]", classes="tool-summary"))

    def toggle_tool_detail(self) -> None:
        """Toggle between collapsed and expanded tool use display."""
        self._tool_expanded = not self._tool_expanded
        self._render_messages()

    def get_all_messages(self) -> list[dict]:
        """Return the current meeting's non-empty messages."""
        if not self._meeting_data:
            return []
        return [m for m in self._meeting_data.get("messages", []) if not is_empty_message(m)]
