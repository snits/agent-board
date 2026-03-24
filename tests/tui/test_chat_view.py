# ABOUTME: Tests for the chat view message stream widget.
# ABOUTME: Verifies message grouping, rendering, and empty message filtering.

import pytest
from textual.app import App, ComposeResult

from tui.widgets.chat_view import (
    ChatView, is_empty_message, format_tool_summary, matches_search,
    filter_by_agents, _precompute_messages,
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


async def test_chat_view_toggle_tool_detail(sample_messages, sample_agent_types):
    app = ChatViewApp()
    async with app.run_test() as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": sample_messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        assert chat._tool_expanded is False
        chat.toggle_tool_detail()
        await pilot.pause()
        assert chat._tool_expanded is True


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
    async with app.run_test() as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": sample_messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        user_msgs = chat.query(".msg-user")
        assert len(user_msgs) > 0
        # Verify assistant messages don't have the class
        all_content = chat.query(".msg-content")
        assistant_msgs = [w for w in all_content if not w.has_class("msg-user")]
        assert len(assistant_msgs) > 0


async def test_chat_view_empty_state_on_launch():
    """Chat view shows placeholder when no session is loaded."""
    app = ChatViewApp()
    async with app.run_test() as pilot:
        chat = app.query_one(ChatView)
        await pilot.pause()
        # Should have a placeholder widget
        placeholders = chat.query(".empty-state")
        assert len(placeholders) == 1
        assert "Select a session" in str(placeholders.first().content)


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
    assert len(msgs[0]["_tool_expanded_text"]) == 1


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
    async with app.run_test() as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": sample_messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        assert chat.message_count > 0
        # Apply a search that matches nothing
        chat.apply_filters(search_query="zzz_no_match_zzz")
        await pilot.pause()
        assert chat.message_count == 0
        placeholders = chat.query(".empty-state")
        assert len(placeholders) == 1
        assert "No messages match" in str(placeholders.first().content)


async def test_chat_view_paginates_large_sessions(sample_agent_types):
    """Only PAGE_SIZE messages are mounted initially for large sessions."""
    messages = []
    for i in range(250):
        messages.append({
            "uuid": f"msg-{i:04d}",
            "parentUuid": None,
            "agentId": "agent-aaa",
            "role": "assistant",
            "content": f"Message number {i}",
            "toolUse": [],
            "timestamp": f"2026-03-20T10:{i // 60:02d}:{i % 60:02d}.000Z",
            "promptId": "mtg-001",
            "agentType": "web-search-researcher",
            "teamName": "Test",
        })
    app = ChatViewApp()
    async with app.run_test() as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        assert chat.message_count == 250
        assert chat._rendered_count == chat.PAGE_SIZE


async def test_chat_view_small_session_no_indicator(sample_messages, sample_agent_types):
    """Sessions smaller than PAGE_SIZE don't show a load-more indicator."""
    app = ChatViewApp()
    async with app.run_test() as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": sample_messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        indicators = chat.query(".load-more")
        assert len(indicators) == 0


async def test_chat_view_large_session_shows_indicator(sample_agent_types):
    """Sessions larger than PAGE_SIZE show a load-more indicator."""
    messages = []
    for i in range(150):
        messages.append({
            "uuid": f"msg-{i:04d}",
            "parentUuid": None,
            "agentId": "agent-aaa",
            "role": "assistant",
            "content": f"Message number {i}",
            "toolUse": [],
            "timestamp": f"2026-03-20T10:{i // 60:02d}:{i % 60:02d}.000Z",
            "promptId": "mtg-001",
            "agentType": "web-search-researcher",
            "teamName": "Test",
        })
    app = ChatViewApp()
    async with app.run_test() as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        indicators = chat.query(".load-more")
        assert len(indicators) == 1


async def test_chat_view_filter_resets_pagination(sample_agent_types):
    """Applying a filter resets to the first page."""
    messages = []
    for i in range(200):
        agent_type = "web-search-researcher" if i % 2 == 0 else "general-purpose"
        messages.append({
            "uuid": f"msg-{i:04d}",
            "parentUuid": None,
            "agentId": f"agent-{agent_type[:3]}",
            "role": "assistant",
            "content": f"Message number {i}",
            "toolUse": [],
            "timestamp": f"2026-03-20T10:{i // 60:02d}:{i % 60:02d}.000Z",
            "promptId": "mtg-001",
            "agentType": agent_type,
            "teamName": "Test",
        })
    app = ChatViewApp()
    async with app.run_test() as pilot:
        chat = app.query_one(ChatView)
        chat.load_messages({"messages": messages, "agents": []}, sample_agent_types)
        await pilot.pause()
        assert chat._rendered_count == chat.PAGE_SIZE
        chat.apply_filters(agent_filter={"web-search-researcher"})
        await pilot.pause()
        assert chat.message_count == 100
        assert chat._rendered_count == chat.PAGE_SIZE
