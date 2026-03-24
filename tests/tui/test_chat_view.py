# ABOUTME: Tests for the chat view message stream widget.
# ABOUTME: Verifies message grouping, rendering, and empty message filtering.

import pytest
from textual.app import App, ComposeResult

from tui.widgets.chat_view import (
    ChatView, is_empty_message, format_tool_summary, matches_search,
    filter_by_agents, _precompute_messages, _build_rows,
)


class ChatViewApp(App):
    """Minimal app for testing ChatView."""

    def compose(self) -> ComposeResult:
        yield ChatView()


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
        # Should have rendered message groups (5 messages, but grouped)
        assert chat.message_count > 0


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


async def test_chat_view_user_messages_have_class(sample_messages, sample_agent_types):
    """User messages get the msg-user CSS class for visual distinction."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": sample_messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        user_widgets = [w for w in chat._pool if w.has_class("msg-user")]
        assert len(user_widgets) > 0
        non_user_content = [w for w in chat._pool
                           if w.has_class("msg-content") and not w.has_class("msg-user")]
        assert len(non_user_content) > 0


async def test_chat_view_empty_state_on_launch():
    """Chat view shows placeholder when no session is loaded."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        await pilot.pause()
        pool_texts = [str(w.content) for w in chat._pool]
        assert any("Select a session" in t for t in pool_texts)


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
        pool_texts = [str(w.content) for w in chat._pool]
        assert any("No messages match" in t for t in pool_texts)


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
    assert rows[0][1] == "msg-header"
    assert "General" in rows[0][0]
    assert rows[1][1] == "msg-content"
    assert rows[2][1] == "msg-header"
    assert "Researcher" in rows[2][0]
    assert rows[3][1] == "msg-content"


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


async def test_chat_view_pool_size_matches_height():
    """Widget pool size equals the ChatView height."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        await pilot.pause()
        assert len(chat._pool) == chat.size.height


async def test_chat_view_refresh_pool_updates_content(sample_messages, sample_agent_types):
    """Loading messages updates pool widget content."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": sample_messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        first_content = str(chat._pool[0].content)
        assert first_content != ""


async def test_chat_view_scroll_down(sample_agent_types):
    """Down arrow increments scroll offset when content exceeds viewport."""
    # Enough messages so rows > pool height (24), enabling scrolling
    messages = []
    for i in range(50):
        messages.append({
            "uuid": f"msg-{i:04d}", "parentUuid": None, "agentId": "agent-aaa",
            "role": "assistant", "content": f"Message {i}", "toolUse": [],
            "timestamp": f"2026-03-20T10:00:{i:02d}.000Z", "promptId": "mtg-001",
            "agentType": "web-search-researcher", "teamName": "Test",
        })
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        chat.focus()
        await pilot.pause()
        assert chat._scroll_offset == 0
        await pilot.press("down")
        await pilot.pause()
        assert chat._scroll_offset == 1


async def test_chat_view_scroll_clamps_at_top(sample_agent_types):
    """Up arrow at top stays at offset 0."""
    messages = []
    for i in range(50):
        messages.append({
            "uuid": f"msg-{i:04d}", "parentUuid": None, "agentId": "agent-aaa",
            "role": "assistant", "content": f"Message {i}", "toolUse": [],
            "timestamp": f"2026-03-20T10:00:{i:02d}.000Z", "promptId": "mtg-001",
            "agentType": "web-search-researcher", "teamName": "Test",
        })
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        chat.focus()
        await pilot.pause()
        assert chat._scroll_offset == 0
        await pilot.press("up")
        await pilot.pause()
        assert chat._scroll_offset == 0


async def test_chat_view_scroll_clamps_at_bottom(sample_agent_types):
    """Scroll offset clamps so last row is visible."""
    messages = []
    for i in range(10):
        messages.append({
            "uuid": f"msg-{i:04d}", "parentUuid": None, "agentId": "agent-aaa",
            "role": "assistant", "content": f"Message {i}", "toolUse": [],
            "timestamp": f"2026-03-20T10:00:{i:02d}.000Z", "promptId": "mtg-001",
            "agentType": "web-search-researcher", "teamName": "Test",
        })
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        chat.focus()
        await pilot.pause()
        await pilot.press("end")
        await pilot.pause()
        max_offset = max(0, len(chat._rows) - len(chat._pool))
        assert chat._scroll_offset == max_offset


async def test_chat_view_page_down(sample_agent_types):
    """Page down advances by pool size."""
    messages = []
    for i in range(100):
        messages.append({
            "uuid": f"msg-{i:04d}", "parentUuid": None, "agentId": "agent-aaa",
            "role": "assistant", "content": f"Message {i}", "toolUse": [],
            "timestamp": f"2026-03-20T10:{i // 60:02d}:{i % 60:02d}.000Z",
            "promptId": "mtg-001", "agentType": "web-search-researcher",
            "teamName": "Test",
        })
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        chat.focus()
        await pilot.pause()
        pool_size = len(chat._pool)
        await pilot.press("pagedown")
        await pilot.pause()
        assert chat._scroll_offset == pool_size


async def test_chat_view_empty_state_via_pool():
    """Empty state renders hint text through the pool."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        await pilot.pause()
        assert len(chat._pool) > 0
        pool_texts = [str(w.content) for w in chat._pool]
        assert any("Select a session" in t for t in pool_texts)


async def test_chat_view_resize_rebuilds_pool():
    """Resize rebuilds the pool to match new height."""
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        await pilot.pause()
        old_pool_size = len(chat._pool)
        assert old_pool_size > 0
        await pilot.resize_terminal(80, 40)
        await pilot.pause()
        new_pool_size = len(chat._pool)
        assert new_pool_size != old_pool_size
        assert new_pool_size > 0


async def test_chat_view_filter_resets_scroll(sample_agent_types):
    """Applying a filter resets scroll offset to 0."""
    messages = []
    for i in range(100):
        messages.append({
            "uuid": f"msg-{i:04d}", "parentUuid": None, "agentId": "agent-aaa",
            "role": "assistant", "content": f"Message {i}", "toolUse": [],
            "timestamp": f"2026-03-20T10:{i // 60:02d}:{i % 60:02d}.000Z",
            "promptId": "mtg-001", "agentType": "web-search-researcher",
            "teamName": "Test",
        })
    app = ChatViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        chat.focus()
        await pilot.pause()
        await pilot.press("pagedown")
        await pilot.pause()
        assert chat._scroll_offset > 0
        chat.apply_filters(search_query="Message 5")
        await pilot.pause()
        assert chat._scroll_offset == 0
