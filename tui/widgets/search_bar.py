# ABOUTME: Search bar widget for the TUI frontend.
# ABOUTME: Provides a hideable search input that posts query change messages.

from textual.message import Message
from textual.timer import Timer
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
        background: $boost;
    }
    SearchBar.-visible {
        display: block;
    }
    """

    DEBOUNCE_SECONDS = 0.3

    class SearchChanged(Message):
        """Posted when the search query changes."""

        def __init__(self, query: str) -> None:
            super().__init__()
            self.query = query

    def __init__(self, **kwargs) -> None:
        super().__init__(placeholder="Search messages… (Esc to close)", **kwargs)
        self._debounce_timer: Timer | None = None

    def _cancel_debounce(self) -> None:
        """Cancel any pending debounce timer."""
        if self._debounce_timer is not None:
            self._debounce_timer.stop()
            self._debounce_timer = None

    def _fire_search(self) -> None:
        """Post the current value as a SearchChanged message."""
        self._debounce_timer = None
        self.post_message(self.SearchChanged(self.value))

    def show(self) -> None:
        """Show the search bar and focus it."""
        self.add_class("-visible")
        self.call_after_refresh(self.focus)

    def dismiss(self) -> None:
        """Hide the search bar but keep the current query active."""
        self.remove_class("-visible")

    def clear(self) -> None:
        """Hide the search bar and clear the query."""
        self._cancel_debounce()
        self.remove_class("-visible")
        self.value = ""
        self.post_message(self.SearchChanged(""))

    def on_input_changed(self, event: Input.Changed) -> None:
        """Debounce input changes before posting search queries."""
        self._cancel_debounce()
        self._debounce_timer = self.set_timer(
            self.DEBOUNCE_SECONDS, self._fire_search
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Dismiss on Enter — fire immediately and keep the filter active."""
        self._cancel_debounce()
        self.post_message(self.SearchChanged(self.value))
        self.dismiss()
