# ABOUTME: Tests for the chat view message stream widget.
# ABOUTME: Verifies message grouping, rendering, and empty message filtering.

import pytest
from textual.app import App, ComposeResult

from tui.widgets.chat_view import (
    ChatView, is_empty_message, format_tool_summary, matches_search, filter_by_agents,
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
