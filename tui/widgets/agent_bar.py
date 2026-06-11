# ABOUTME: Header bar widget showing agent roster and breadcrumb navigation.
# ABOUTME: Displays colored agent dots with message counts and current location path.

from rich.text import Text
from textual.widgets import Static


class AgentBar(Static):
    """Header bar showing agent roster and breadcrumb."""

    DEFAULT_CSS = """
    AgentBar {
        dock: top;
        height: 1;
        background: $surface;
        color: $text;
        padding: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__("")
        self.agents: list[dict] = []
        self.agent_types: dict = {}
        self.breadcrumb_parts: list[str] = []
        self._filter_type: str | None = None
        self._filter_position: int | None = None
        self._filter_total: int | None = None
        self._search_query: str = ""
        self._bar_text: Text = Text()

    def update_meeting(
        self,
        agents: list[dict],
        agent_types: dict,
        breadcrumb_parts: list[str],
    ) -> None:
        """Update the bar with a new meeting's agent roster and breadcrumb."""
        self.agents = agents
        self.agent_types = agent_types
        self.breadcrumb_parts = breadcrumb_parts
        self._refresh_content()

    def set_filter(
        self,
        agent_type: str | None,
        position: int | None = None,
        total: int | None = None,
    ) -> None:
        """Set or clear the active agent filter indicator."""
        self._filter_type = agent_type
        self._filter_position = position
        self._filter_total = total
        self._refresh_content()

    def set_search(self, query: str) -> None:
        """Set or clear the active search query indicator."""
        self._search_query = query
        self._refresh_content()

    def clear(self) -> None:
        """Clear the bar."""
        self.agents = []
        self.agent_types = {}
        self.breadcrumb_parts = []
        self._filter_type = None
        self._filter_position = None
        self._filter_total = None
        self._search_query = ""
        self._refresh_content()

    def _refresh_content(self) -> None:
        """Rebuild the displayed bar text.

        The bar is assembled as a Rich Text with explicit styles — agent
        labels, search queries, and breadcrumbs are never parsed as markup,
        so bracket- or backslash-heavy names render literally.
        """
        if not self.agents and not self.breadcrumb_parts and not self._filter_type and not self._search_query:
            self._bar_text = Text()
            self.update("")
            return

        parts = []
        for agent in self.agents:
            agent_type = agent["type"]
            count = agent["messageCount"]
            type_info = self.agent_types.get(agent_type, {})
            color = type_info.get("color", "#888888")
            label = type_info.get("label", agent_type)
            parts.append(Text.assemble(("●", color), f" {label}: {count}"))

        roster = Text("  ").join(parts)
        breadcrumb = " › ".join(self.breadcrumb_parts)

        # Build filter indicator
        filter_text = None
        if self._filter_type:
            type_info = self.agent_types.get(self._filter_type, {})
            filter_label = type_info.get("label", self._filter_type)
            pos_info = ""
            if self._filter_position is not None and self._filter_total is not None:
                pos_info = f" [{self._filter_position}/{self._filter_total}]"
            filter_text = Text(f"Filter: {filter_label}{pos_info}")
            filter_text.stylize("bold yellow")

        # Build search indicator
        search_text = None
        if self._search_query:
            search_text = Text(f"Search: {self._search_query}")
            search_text.stylize("bold cyan")

        sections = []
        if parts:
            sections.append(roster)
        if filter_text is not None:
            sections.append(filter_text)
        if search_text is not None:
            sections.append(search_text)
        if breadcrumb:
            breadcrumb_text = Text(breadcrumb)
            breadcrumb_text.stylize("dim")
            sections.append(breadcrumb_text)

        self._bar_text = Text.assemble("  ", ("│", "dim"), "  ").join(sections)
        self.update(self._bar_text)
