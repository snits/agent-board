# ABOUTME: Detail pane widget for showing full message content.
# ABOUTME: Scrollable panel that renders the complete text of a focused message.

from rich.text import Text
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
        """Render a message's full content, or clear if None.

        Content is assembled as a Rich Text with explicit styles — it is never
        parsed as markup, so bracket- or backslash-heavy content renders
        literally.
        """
        if message is None:
            self._content.update("")
            return

        parts: list[Text] = []

        # Agent header
        agent_type = message.get("agentType", "unknown")
        timestamp = message.get("timestamp", "")[:16].replace("T", " ")
        type_info = self._agent_types.get(agent_type, {})
        color = type_info.get("color", "#888888")
        label = type_info.get("label", agent_type)
        parts.append(Text.assemble((label, f"bold {color}"), " ", (timestamp, "dim")))
        parts.append(Text(""))

        # Full content
        content = message.get("content", "")
        if content:
            parts.append(Text(content))
            parts.append(Text(""))

        # Tool summaries
        for summary in message.get("_tool_summaries", []):
            summary_text = Text(summary)
            summary_text.stylize("dim")
            parts.append(summary_text)

        self._content.update(Text("\n").join(parts))
        self.scroll_home(animate=False)
