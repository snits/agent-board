# ABOUTME: Header bar widget showing agent roster and breadcrumb navigation.
# ABOUTME: Displays colored agent dots with message counts and current location path.

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
        self._markup: str = ""

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

    def set_filter(self, agent_type: str | None) -> None:
        """Set or clear the active agent filter indicator."""
        self._filter_type = agent_type
        self._refresh_content()

    def clear(self) -> None:
        """Clear the bar."""
        self.agents = []
        self.agent_types = {}
        self.breadcrumb_parts = []
        self._filter_type = None
        self._refresh_content()

    def _refresh_content(self) -> None:
        """Rebuild the displayed markup."""
        if not self.agents and not self.breadcrumb_parts and not self._filter_type:
            self._markup = ""
            self.update("")
            return

        parts = []
        for agent in self.agents:
            agent_type = agent["type"]
            count = agent["messageCount"]
            type_info = self.agent_types.get(agent_type, {})
            color = type_info.get("color", "#888888")
            label = type_info.get("label", agent_type)
            parts.append(f"[{color}]●[/] {label}: {count}")

        roster = "  ".join(parts)
        breadcrumb = " › ".join(self.breadcrumb_parts)

        # Build filter indicator
        filter_text = ""
        if self._filter_type:
            type_info = self.agent_types.get(self._filter_type, {})
            filter_label = type_info.get("label", self._filter_type)
            filter_text = f"[bold yellow]Filter: {filter_label}[/]"

        sections = []
        if roster:
            sections.append(roster)
        if filter_text:
            sections.append(filter_text)
        if breadcrumb:
            sections.append(f"[dim]{breadcrumb}[/]")

        self._markup = "  [dim]│[/]  ".join(sections)
        self.update(self._markup)
