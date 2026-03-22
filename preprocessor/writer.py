# ABOUTME: Writes processed meeting data to the output JSON file structure.
# ABOUTME: Generates index.json, agent-types.json, and per-meeting JSON files.

import hashlib
import json
from pathlib import Path

KNOWN_COLORS = {
    "strategist": ("#4A90D9", "Strategist"),
    "engine-arch": ("#50C878", "Engine Architect"),
    "sim-designer": ("#E8A838", "Simulation Designer"),
    "social-designer": ("#C77DBA", "Social Designer"),
    "ux-expert": ("#E85D75", "UX Expert"),
    "world-gen": ("#6BC5D2", "World Generation"),
    "cultural-mythology-engine": ("#D4A574", "Cultural Mythology"),
    "game-design-reviewer": ("#8B8BCD", "Design Reviewer"),
    "game-balance-analyst": ("#7CB97C", "Balance Analyst"),
    "game-performance-analyst": ("#CD8B8B", "Performance Analyst"),
    "strategy-guide-writer": ("#B8A960", "Strategy Guide Writer"),
    "crawford-research": ("#A0A0A0", "Crawford Research"),
    "prompt-cleanup": ("#808080", "Prompt Cleanup"),
    "team-lead": ("#FFFFFF", "Team Lead"),
}

FALLBACK_PALETTE = [
    "#E6194B", "#3CB44B", "#FFE119", "#4363D8", "#F58231",
    "#911EB4", "#42D4F4", "#F032E6", "#BFEF45", "#FABED4",
    "#469990", "#DCBEFF", "#9A6324", "#FFFAC8", "#800000",
    "#AAFFC3", "#808000", "#FFD8B1", "#000075", "#A9A9A9",
]


def _label_from_slug(slug: str) -> str:
    """Convert a kebab-case slug to a Title Case label."""
    return " ".join(word.capitalize() for word in slug.split("-"))


def _color_for_type(agent_type: str) -> str:
    """Deterministic color for an unknown agent type."""
    h = int(hashlib.md5(agent_type.encode()).hexdigest(), 16)
    return FALLBACK_PALETTE[h % len(FALLBACK_PALETTE)]


def generate_agent_types(type_names: set[str]) -> dict:
    """Generate an agent-types registry with colors and labels."""
    result = {}
    for name in sorted(type_names):
        if name in KNOWN_COLORS:
            color, label = KNOWN_COLORS[name]
        else:
            color = _color_for_type(name)
            label = _label_from_slug(name)
        result[name] = {"color": color, "label": label}
    return result


def write_session(output_dir: Path, session_info: dict) -> None:
    """Write a session's meetings to the output directory."""
    output_dir = Path(output_dir)
    session_dir = output_dir / "sessions" / session_info["id"]
    meetings_dir = session_dir / "meetings"
    meetings_dir.mkdir(parents=True, exist_ok=True)

    agent_meta = session_info.get("agentMeta", {})

    for prompt_id, meeting in session_info["meetings"].items():
        agents_in_meeting = {}
        for msg in meeting["messages"]:
            aid = msg.get("agentId")
            if aid and aid in agent_meta:
                msg["agentType"] = agent_meta[aid].get("agentType", "unknown")
                agents_in_meeting.setdefault(aid, {
                    "agentId": aid,
                    "type": msg["agentType"],
                    "messageCount": 0,
                })
                agents_in_meeting[aid]["messageCount"] += 1

        meeting_data = {
            "id": prompt_id,
            "teamName": meeting["teamName"],
            "startTime": meeting.get("startTime"),
            "endTime": meeting.get("endTime"),
            "agents": list(agents_in_meeting.values()),
            "messages": meeting["messages"],
        }

        meeting_file = meetings_dir / f"{prompt_id}.json"
        meeting_file.write_text(json.dumps(meeting_data, indent=2))

    all_timestamps = []
    for meeting in session_info["meetings"].values():
        if meeting.get("startTime"):
            all_timestamps.append(meeting["startTime"])
        if meeting.get("endTime"):
            all_timestamps.append(meeting["endTime"])
    all_timestamps.sort()

    session_meta = {
        "id": session_info["id"],
        "startTime": all_timestamps[0] if all_timestamps else None,
        "endTime": all_timestamps[-1] if all_timestamps else None,
        "meetingCount": len(session_info["meetings"]),
        "agentCount": len(agent_meta),
    }
    (session_dir / "session.json").write_text(json.dumps(session_meta, indent=2))


def write_index(output_dir: Path, projects: list[dict]) -> None:
    """Write the master index.json."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "index.json"
    index_path.write_text(json.dumps({"projects": projects}, indent=2))


def write_agent_types(output_dir: Path, type_names: set[str]) -> None:
    """Write agent-types.json."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    types = generate_agent_types(type_names)
    (output_dir / "agent-types.json").write_text(json.dumps(types, indent=2))
