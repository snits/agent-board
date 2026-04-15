# ABOUTME: Detail pane widget for showing full message content.
# ABOUTME: Scrollable panel that renders the complete text of a focused message.

from rich.markup import escape
from textual.containers import ScrollableContainer
from textual.widgets import Static


class DetailPane(ScrollableContainer):
    """Scrollable pane showing the full content of the focused message."""

    DEFAULT_CSS = """
    DetailPane {
        height: 2fr;
        border-top: solid $accent-darken-2;
        padding: 0 1;
    }
    DetailPane:focus-within {
        border-top: heavy $accent;
    }
    """

    def __init__(self, agent_types: dict | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._agent_types = agent_types or {}
        self._content = Static("")

    def compose(self):
        yield self._content

    def update_message(self, message: dict | None) -> None:
        """Render a message's full content, or clear if None."""
        if message is None:
            self._content.update("")
            return

        parts = []

        # Agent header
        agent_type = message.get("agentType", "unknown")
        timestamp = message.get("timestamp", "")[:16].replace("T", " ")
        type_info = self._agent_types.get(agent_type, {})
        color = type_info.get("color", "#888888")
        label = type_info.get("label", agent_type)
        parts.append(f"[bold {color}]{label}[/] [dim]{timestamp}[/]")
        parts.append("")

        # Full content
        content = message.get("content", "")
        if content:
            parts.append(escape(content))
            parts.append("")

        # Tool summaries
        for summary in message.get("_tool_summaries", []):
            parts.append(f"[dim]{escape(summary)}[/]")

        self._content.update("\n".join(parts))
        self.scroll_home(animate=False)
