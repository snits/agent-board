# ABOUTME: Search bar widget for the TUI frontend.
# ABOUTME: Provides a hideable search input that posts query change messages.

from textual.message import Message
from textual.widgets import Input


class SearchBar(Input):
    """Search input that posts search queries as messages."""

    DEFAULT_CSS = """
    SearchBar {
        dock: bottom;
        display: none;
        height: 1;
        border: none;
        padding: 0 1;
    }
    SearchBar.-visible {
        display: block;
    }
    """

    class SearchChanged(Message):
        """Posted when the search query changes."""

        def __init__(self, query: str) -> None:
            super().__init__()
            self.query = query

    def __init__(self, **kwargs) -> None:
        super().__init__(placeholder="Search messages...", **kwargs)

    def show(self) -> None:
        """Show the search bar and focus it."""
        self.add_class("-visible")
        self.focus()

    def dismiss(self) -> None:
        """Hide the search bar but keep the current query active."""
        self.remove_class("-visible")

    def clear(self) -> None:
        """Hide the search bar and clear the query."""
        self.remove_class("-visible")
        self.value = ""
        self.post_message(self.SearchChanged(""))

    def on_input_changed(self, event: Input.Changed) -> None:
        """Forward input changes as search queries."""
        self.post_message(self.SearchChanged(self.value))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Dismiss on Enter — keep the filter active."""
        self.dismiss()
