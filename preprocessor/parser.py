# ABOUTME: Parses individual JSONL records from claude's transcript format.
# ABOUTME: Extracts text content, tool-use blocks, and teammate-message metadata.

import re


def parse_content(content: str | list) -> tuple[str, list[dict]]:
    """Extract text and tool-use blocks from a message's content field."""
    if isinstance(content, str):
        return content, []

    text_parts = []
    tools = []

    for block in content:
        block_type = block.get("type", "")
        if block_type == "text":
            text_parts.append(block["text"])
        elif block_type == "tool_use":
            tool_name = block["name"]
            tool_input = block.get("input", {})
            tools.append({
                "tool": tool_name,
                "input": tool_input,
                "summary": _tool_summary(tool_name, tool_input),
            })

    return "\n\n".join(text_parts), tools


def parse_teammate_message(text: str) -> dict | None:
    """Parse <teammate-message> XML from a user message."""
    match = re.search(
        r'<teammate-message\s+([^>]+)>\s*(.*?)\s*</teammate-message>',
        text,
        re.DOTALL,
    )
    if not match:
        return None

    attrs_str = match.group(1)
    content = match.group(2).strip()

    sender = _extract_attr(attrs_str, "teammate_id")
    summary = _extract_attr(attrs_str, "summary")

    return {
        "sender": sender or "unknown",
        "content": content,
        "summary": summary,
    }


def parse_record(record: dict) -> dict | None:
    """Parse a raw JSONL record into a normalized message dict.
    Returns None for records that should be skipped."""
    record_type = record.get("type")
    if record_type not in ("user", "assistant"):
        return None

    message = record.get("message", {})
    content_raw = message.get("content", "")
    text, tools = parse_content(content_raw)

    result = {
        "uuid": record.get("uuid"),
        "parentUuid": record.get("parentUuid"),
        "agentId": record.get("agentId"),
        "role": message.get("role", record_type),
        "content": text,
        "toolUse": tools,
        "timestamp": record.get("timestamp"),
        "promptId": record.get("promptId"),
    }

    if record_type == "user" and isinstance(content_raw, str):
        teammate = parse_teammate_message(content_raw)
        if teammate:
            result["sender"] = teammate["sender"]
            result["content"] = teammate["content"]
            if teammate.get("summary"):
                result["summary"] = teammate["summary"]

    return result


def _tool_summary(tool_name: str, tool_input: dict) -> str:
    """Generate a one-line summary for a tool-use block."""
    if tool_name == "Read" and "file_path" in tool_input:
        return f"Read: {tool_input['file_path']}"
    if tool_name == "Bash" and "command" in tool_input:
        cmd = tool_input["command"]
        return f"Bash: {cmd[:80]}{'...' if len(cmd) > 80 else ''}"
    if tool_name == "Write" and "file_path" in tool_input:
        return f"Write: {tool_input['file_path']}"
    if tool_name == "Edit" and "file_path" in tool_input:
        return f"Edit: {tool_input['file_path']}"
    if tool_name == "Grep" and "pattern" in tool_input:
        return f"Grep: {tool_input['pattern']}"
    if tool_name == "Glob" and "pattern" in tool_input:
        return f"Glob: {tool_input['pattern']}"
    if tool_name == "SendMessage" and "to" in tool_input:
        return f"SendMessage to {tool_input['to']}"
    return tool_name


def _extract_attr(attrs_str: str, name: str) -> str | None:
    """Extract a named attribute value from an XML-like attribute string."""
    match = re.search(rf'{name}="([^"]*)"', attrs_str)
    return match.group(1) if match else None
