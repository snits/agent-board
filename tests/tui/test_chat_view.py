# ABOUTME: Tests for the chat view message stream widget.
# ABOUTME: Verifies message grouping, rendering, and empty message filtering.

import pytest
from textual.app import App, ComposeResult
from textual.widgets import OptionList

from tui.widgets.chat_view import (
    ChatView, is_empty_message, format_tool_summary, matches_search,
    filter_by_agents, _precompute_messages, _build_rows,
)


class ChatViewApp(App):
    """Minimal app for testing ChatView."""

    def compose(self) -> ComposeResult:
        yield ChatView()


def _option_list(chat: ChatView) -> OptionList:
    return chat.query_one("#chat-options", OptionList)


def _make_messages(count: int) -> list[dict]:
    """Generate `count` assistant messages under a single agent id."""
    return [
        {
            "uuid": f"msg-{i:04d}", "parentUuid": None, "agentId": "agent-aaa",
            "role": "assistant", "content": f"Message {i}", "toolUse": [],
            "timestamp": f"2026-03-20T10:{i // 60:02d}:{i % 60:02d}.000Z",
            "promptId": "mtg-001", "agentType": "web-search-researcher",
            "teamName": "Test",
        }
        for i in range(count)
    ]


def test_is_empty_message_empty():
    msg = {"content": "", "toolUse": []}
    assert is_empty_message(msg) is True


def test_is_empty_message_with_content():
    msg = {"content": "Hello", "toolUse": []}
    assert is_empty_message(msg) is False


def test_is_empty_message_with_tools():
    msg = {"content": "", "toolUse": [{"tool": "Read", "input": {}, "summary": "Read"}]}
    assert is_empty_message(msg) is False


def test_format_tool_summary_with_file_path():
    tool = {"tool": "Read", "input": {"file_path": "/src/app.py"}, "summary": "Read → /src/app.py"}
    assert format_tool_summary(tool) == "⚙ Read → /src/app.py"


def test_format_tool_summary_with_command():
    tool = {"tool": "Bash", "input": {"command": "npm test"}, "summary": "Bash"}
    assert format_tool_summary(tool) == "⚙ Bash → npm test"


def test_format_tool_summary_fallback():
    tool = {"tool": "WebFetch", "input": {"url": "https://example.com"}, "summary": "WebFetch → example.com"}
    assert format_tool_summary(tool) == "⚙ WebFetch → example.com"


def test_format_tool_summary_no_summary():
    tool = {"tool": "Unknown", "input": {"data": "value"}, "summary": ""}
    assert format_tool_summary(tool) == "⚙ Unknown"


async def test_chat_view_loads_messages(sample_messages, sample_agent_types):
    app = ChatViewApp()
    async with app.run_test() as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": sample_messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        assert chat.message_count > 0
        assert _option_list(chat).option_count > 0


async def test_chat_view_filters_empty_messages(sample_empty_messages, sample_agent_types):
    app = ChatViewApp()
    async with app.run_test() as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages(
            {"messages": sample_empty_messages, "agents": []},
            {"general-purpose": {"color": "#FFFAC8", "label": "General Purpose"}},
        )
        await pilot.pause()
        # Only 1 message should render (the one with content)
        assert chat.message_count == 1


async def test_chat_view_apply_search_filter(sample_messages, sample_agent_types):
    app = ChatViewApp()
    async with app.run_test() as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": sample_messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        original_count = chat.message_count
        chat.apply_filters(search_query="Textual")
        await pilot.pause()
        assert chat.message_count < original_count
        assert chat.message_count > 0


async def test_chat_view_user_messages_rendered(sample_messages, sample_agent_types):
    """User messages have their content rendered with dim styling."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": sample_messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        prompts = [opt.prompt for opt in _option_list(chat).options]
        # At least one option's Rich Text carries a dim style span (from a user-role content line).
        # Prompts are wrapped via Text.from_markup so styling is in spans, not literal "[dim]".
        has_dim = any(
            any("dim" in str(span.style) for span in getattr(p, "spans", []))
            for p in prompts
        )
        assert has_dim


async def test_chat_view_empty_state_on_launch():
    """Chat view shows the placeholder hint when no session is loaded."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        await pilot.pause()
        ol = _option_list(chat)
        assert ol.option_count == 1
        hint_option = ol.get_option_at_index(0)
        assert hint_option.disabled
        assert ChatView.EMPTY_STATE_HINT in str(hint_option.prompt)
        assert chat.message_count == 0


def test_precompute_sets_is_empty():
    """Pre-computation annotates empty messages."""
    msgs = [
        {"content": "", "toolUse": []},
        {"content": "hello", "toolUse": []},
    ]
    _precompute_messages(msgs)
    assert msgs[0]["_is_empty"] is True
    assert msgs[1]["_is_empty"] is False


def test_precompute_sets_tool_summaries():
    """Pre-computation caches formatted tool summaries."""
    msgs = [
        {
            "content": "",
            "toolUse": [
                {"tool": "Read", "input": {"file_path": "/app.py"}, "summary": "Read → /app.py"},
            ],
        },
    ]
    _precompute_messages(msgs)
    assert len(msgs[0]["_tool_summaries"]) == 1
    assert "Read" in msgs[0]["_tool_summaries"][0]


def test_precompute_sets_search_text():
    """Pre-computation builds a single lowercase search string."""
    msgs = [
        {
            "content": "Hello World",
            "toolUse": [
                {"tool": "Read", "input": {}, "summary": "Read → app.py"},
            ],
        },
    ]
    _precompute_messages(msgs)
    assert "hello world" in msgs[0]["_search_text"]
    assert "read" in msgs[0]["_search_text"]
    assert "app.py" in msgs[0]["_search_text"]


def test_matches_search_uses_precomputed():
    """matches_search works with pre-computed _search_text."""
    msgs = [{"content": "Hello World", "toolUse": []}]
    _precompute_messages(msgs)
    assert matches_search(msgs[0], "hello") is True
    assert matches_search(msgs[0], "nonexistent") is False


async def test_chat_view_empty_state_on_filter(sample_messages, sample_agent_types):
    """Chat view shows 'no results' when filters produce zero matches."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": sample_messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        assert chat.message_count > 0
        chat.apply_filters(search_query="zzz_no_match_zzz")
        await pilot.pause()
        assert chat.message_count == 0
        ol = _option_list(chat)
        assert ol.option_count == 1
        hint_option = ol.get_option_at_index(0)
        assert hint_option.disabled
        assert ChatView.EMPTY_FILTER_HINT in str(hint_option.prompt)


def test_build_rows_header_on_agent_change():
    """Headers are inserted when agentId changes."""
    msgs = [
        {"agentId": "a1", "agentType": "general-purpose", "role": "assistant",
         "content": "Hello", "toolUse": [], "timestamp": "2026-03-20T10:00:00.000Z",
         "_is_empty": False, "_tool_summaries": [], "_search_text": "hello"},
        {"agentId": "a2", "agentType": "web-search-researcher", "role": "assistant",
         "content": "World", "toolUse": [], "timestamp": "2026-03-20T10:01:00.000Z",
         "_is_empty": False, "_tool_summaries": [], "_search_text": "world"},
    ]
    agent_types = {
        "general-purpose": {"color": "#FFFAC8", "label": "General"},
        "web-search-researcher": {"color": "#DCBEFF", "label": "Researcher"},
    }
    rows = _build_rows(msgs, agent_types)
    assert len(rows) == 4
    assert "msg-header" in rows[0][1]
    assert "General" in rows[0][0]
    assert "msg-content" in rows[1][1]
    assert "msg-header" in rows[2][1]
    assert "Researcher" in rows[2][0]
    assert "msg-content" in rows[3][1]


def test_build_rows_no_header_same_agent():
    """No header when consecutive messages share the same agentId."""
    msgs = [
        {"agentId": "a1", "agentType": "general-purpose", "role": "assistant",
         "content": "First", "toolUse": [], "timestamp": "2026-03-20T10:00:00.000Z",
         "_is_empty": False, "_tool_summaries": [], "_search_text": "first"},
        {"agentId": "a1", "agentType": "general-purpose", "role": "assistant",
         "content": "Second", "toolUse": [], "timestamp": "2026-03-20T10:01:00.000Z",
         "_is_empty": False, "_tool_summaries": [], "_search_text": "second"},
    ]
    agent_types = {"general-purpose": {"color": "#FFFAC8", "label": "General"}}
    rows = _build_rows(msgs, agent_types)
    assert len(rows) == 3
    headers = [r for r in rows if r[1] == "msg-header"]
    assert len(headers) == 1


def test_build_rows_tool_rows():
    """Tool uses produce separate tool-summary rows."""
    msgs = [
        {"agentId": "a1", "agentType": "general-purpose", "role": "assistant",
         "content": "Working", "toolUse": [{"tool": "Read"}, {"tool": "Write"}],
         "timestamp": "2026-03-20T10:00:00.000Z",
         "_is_empty": False,
         "_tool_summaries": ["⚙ Read → /app.py", "⚙ Write → /out.py"],
         "_search_text": "working"},
    ]
    agent_types = {"general-purpose": {"color": "#FFFAC8", "label": "General"}}
    rows = _build_rows(msgs, agent_types)
    assert len(rows) == 4
    tool_rows = [r for r in rows if r[1] == "tool-summary"]
    assert len(tool_rows) == 2
    assert "Read" in tool_rows[0][0]
    assert "Write" in tool_rows[1][0]


def test_build_rows_user_message_class():
    """User messages get the msg-user class."""
    msgs = [
        {"agentId": "a1", "agentType": "general-purpose", "role": "user",
         "content": "Question", "toolUse": [], "timestamp": "2026-03-20T10:00:00.000Z",
         "_is_empty": False, "_tool_summaries": [], "_search_text": "question"},
    ]
    agent_types = {"general-purpose": {"color": "#FFFAC8", "label": "General"}}
    rows = _build_rows(msgs, agent_types)
    content_rows = [r for r in rows if "msg-content" in r[1]]
    assert len(content_rows) == 1
    assert "msg-user" in content_rows[0][1]


def test_build_rows_truncates_long_content():
    """Long content is truncated to a single line."""
    msgs = [
        {"agentId": "a1", "agentType": "general-purpose", "role": "assistant",
         "content": "Line one\nLine two\nLine three",
         "toolUse": [], "timestamp": "2026-03-20T10:00:00.000Z",
         "_is_empty": False, "_tool_summaries": [], "_search_text": "line"},
    ]
    agent_types = {"general-purpose": {"color": "#FFFAC8", "label": "General"}}
    rows = _build_rows(msgs, agent_types)
    content_rows = [r for r in rows if "msg-content" in r[1]]
    assert len(content_rows) == 1
    assert "\n" not in content_rows[0][0]
    assert "…" in content_rows[0][0]


def test_build_rows_empty_list():
    """Empty message list produces empty row list."""
    rows = _build_rows([], {})
    assert rows == []


async def test_chat_view_refresh_updates_option_list(sample_messages, sample_agent_types):
    """Loading messages populates the OptionList with options."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": sample_messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        ol = _option_list(chat)
        assert ol.option_count > 0
        first_prompt = str(ol.get_option_at_index(0).prompt)
        assert first_prompt != ""


async def test_chat_view_scroll_down(sample_agent_types):
    """Down arrow advances the OptionList highlight by one."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": _make_messages(50), "agents": []}, sample_agent_types)
        await pilot.pause()
        chat.focus()
        await pilot.pause()
        ol = _option_list(chat)
        assert ol.highlighted == 0
        await pilot.press("down")
        await pilot.pause()
        assert ol.highlighted == 1


async def test_chat_view_scroll_clamps_at_top(sample_agent_types):
    """Up at the first option keeps the highlight at 0."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": _make_messages(50), "agents": []}, sample_agent_types)
        await pilot.pause()
        chat.focus()
        await pilot.pause()
        ol = _option_list(chat)
        assert ol.highlighted == 0
        await pilot.press("up")
        await pilot.pause()
        assert ol.highlighted == 0


async def test_chat_view_scroll_clamps_at_bottom(sample_agent_types):
    """End key moves highlight to the last option."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": _make_messages(10), "agents": []}, sample_agent_types)
        await pilot.pause()
        chat.focus()
        await pilot.pause()
        await pilot.press("end")
        await pilot.pause()
        ol = _option_list(chat)
        assert ol.highlighted == ol.option_count - 1


async def test_chat_view_page_down_advances_highlight(sample_agent_types):
    """Page down moves the highlight forward."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": _make_messages(100), "agents": []}, sample_agent_types)
        await pilot.pause()
        chat.focus()
        await pilot.pause()
        ol = _option_list(chat)
        start = ol.highlighted
        await pilot.press("pagedown")
        await pilot.pause()
        assert ol.highlighted > start


async def test_chat_view_filter_resets_highlight(sample_agent_types):
    """Applying a filter resets the highlight to 0."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": _make_messages(100), "agents": []}, sample_agent_types)
        await pilot.pause()
        chat.focus()
        await pilot.pause()
        await pilot.press("pagedown")
        await pilot.pause()
        ol = _option_list(chat)
        assert ol.highlighted > 0
        chat.apply_filters(search_query="Message 5")
        await pilot.pause()
        assert ol.highlighted == 0


def test_build_rows_includes_msg_index():
    """Each row carries the index of its source message."""
    msgs = [
        {"agentId": "a1", "agentType": "general-purpose", "role": "assistant",
         "content": "First", "toolUse": [{"tool": "Read"}],
         "timestamp": "2026-03-20T10:00:00.000Z",
         "_is_empty": False, "_tool_summaries": ["⚙ Read → /app.py"],
         "_search_text": "first"},
        {"agentId": "a2", "agentType": "general-purpose", "role": "assistant",
         "content": "Second", "toolUse": [],
         "timestamp": "2026-03-20T10:01:00.000Z",
         "_is_empty": False, "_tool_summaries": [], "_search_text": "second"},
    ]
    agent_types = {"general-purpose": {"color": "#FFFAC8", "label": "General"}}
    rows = _build_rows(msgs, agent_types)
    assert all(len(r) == 3 for r in rows)
    assert rows[0][2] == 0  # header
    assert rows[1][2] == 0  # content
    assert rows[2][2] == 0  # tool
    assert rows[3][2] == 1  # header
    assert rows[4][2] == 1  # content


async def test_chat_view_highlight_starts_at_zero(sample_agent_types):
    """Highlight starts at option 0 after loading messages."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": _make_messages(50), "agents": []}, sample_agent_types)
        await pilot.pause()
        assert _option_list(chat).highlighted == 0


async def test_chat_view_highlight_moves_down(sample_agent_types):
    """Down arrow advances the highlight by one."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": _make_messages(50), "agents": []}, sample_agent_types)
        await pilot.pause()
        chat.focus()
        await pilot.pause()
        await pilot.press("down")
        await pilot.pause()
        assert _option_list(chat).highlighted == 1


async def test_chat_view_highlight_clamps_at_top(sample_agent_types):
    """Up at highlight 0 stays at 0 (single message)."""
    messages = [
        {"uuid": "msg-0", "parentUuid": None, "agentId": "agent-aaa",
         "role": "assistant", "content": "Hello", "toolUse": [],
         "timestamp": "2026-03-20T10:00:00.000Z", "promptId": "mtg-001",
         "agentType": "web-search-researcher", "teamName": "Test"},
    ]
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        chat.focus()
        await pilot.pause()
        await pilot.press("up")
        await pilot.pause()
        assert _option_list(chat).highlighted == 0


async def test_chat_view_focus_delegates_to_option_list(sample_agent_types):
    """chat.focus() puts focus on the inner OptionList."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": _make_messages(10), "agents": []}, sample_agent_types)
        await pilot.pause()
        chat.focus()
        await pilot.pause()
        assert _option_list(chat).has_focus


async def test_chat_view_end_key_highlights_visible_last_option(sample_agent_types):
    """Regression: in a small viewport, pressing End highlights the last option
    AND scrolls it into view. The previous fixed-pool implementation could leave
    the cursor rendered off-screen when the pool was sized before layout settled.
    """
    # Enough messages to exceed any reasonable viewport
    messages = _make_messages(200)
    app = ChatViewApp()
    # Deliberately small terminal — stresses the previous pool's viewport math
    async with app.run_test(size=(80, 16)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        chat.focus()
        await pilot.pause()
        await pilot.press("end")
        await pilot.pause()
        ol = _option_list(chat)
        last_index = ol.option_count - 1
        assert ol.highlighted == last_index
        # The highlighted option must be inside the OptionList's visible scroll region.
        # OptionList subclasses ScrollView, so scroll_y is the top of the visible region
        # and size.height is its span.
        scroll_y = ol.scroll_y
        visible_top = scroll_y
        visible_bottom = scroll_y + ol.size.height
        # virtual_size.height equals the total rendered height of all options
        # Use the per-line y of the highlighted option: approximate via scroll_offset check.
        # A sufficient condition: scroll_y is positioned so that last option's y is visible.
        # virtual_size.height - scroll_y should be <= ol.size.height (i.e. we scrolled to bottom)
        assert scroll_y + ol.size.height >= ol.virtual_size.height - 1
        assert visible_top >= 0
        assert visible_bottom > visible_top


async def test_chat_view_message_focused_event_fires(sample_agent_types):
    """Moving highlight to a different source message posts MessageFocused."""
    received: list[dict] = []

    class CapturingApp(App):
        def compose(self) -> ComposeResult:
            yield ChatView()

        def on_chat_view_message_focused(self, event: ChatView.MessageFocused) -> None:
            received.append(event.message)

    # Messages with distinct agent ids so each row maps to a new source message
    messages = [
        {"uuid": f"msg-{i}", "parentUuid": None, "agentId": f"agent-{i}",
         "role": "assistant", "content": f"Content {i}", "toolUse": [],
         "timestamp": "2026-03-20T10:00:00.000Z", "promptId": "mtg-001",
         "agentType": "web-search-researcher", "teamName": "Test"}
        for i in range(5)
    ]
    app = CapturingApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        chat.focus()
        await pilot.pause()
        received.clear()
        # Each source message here produces two rows (header + content), so the
        # highlight must cross two positions to hit a different msg_idx.
        await pilot.press("down")
        await pilot.press("down")
        await pilot.pause()
        assert len(received) >= 1
        assert received[0]["content"] == "Content 1"


async def test_chat_view_clear_meeting_resets_to_empty(sample_messages, sample_agent_types):
    """clear_meeting drops all options and returns to the empty hint."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": sample_messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        assert _option_list(chat).option_count > 0
        chat.clear_meeting()
        await pilot.pause()
        assert chat.message_count == 0
        ol = _option_list(chat)
        assert ol.option_count == 1
        hint_option = ol.get_option_at_index(0)
        assert hint_option.disabled
        assert ChatView.EMPTY_STATE_HINT in str(hint_option.prompt)


async def test_chat_view_get_all_messages_returns_non_empty(sample_empty_messages):
    """get_all_messages exposes the current session's non-empty messages."""
    app = ChatViewApp()
    async with app.run_test() as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages(
            {"messages": sample_empty_messages, "agents": []},
            {"general-purpose": {"color": "#FFFAC8", "label": "General"}},
        )
        await pilot.pause()
        messages = chat.get_all_messages()
        assert len(messages) == 1
        assert messages[0]["content"] == "This message has content."
