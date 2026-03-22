# ABOUTME: Data loading layer for the TUI frontend.
# ABOUTME: Reads preprocessed JSON files from the data directory.

import json
from pathlib import Path


def load_index(data_dir: Path) -> dict:
    """Load the project/session index."""
    path = Path(data_dir) / "index.json"
    if not path.exists():
        return {"projects": []}
    return json.loads(path.read_text())


def load_agent_types(data_dir: Path) -> dict:
    """Load the agent type registry (colors and labels)."""
    path = Path(data_dir) / "agent-types.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def load_session(data_dir: Path, session_id: str) -> dict | None:
    """Load session metadata including meeting summaries."""
    path = Path(data_dir) / "sessions" / session_id / "session.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def load_meeting(data_dir: Path, session_id: str, meeting_id: str) -> dict | None:
    """Load a meeting's full message history."""
    path = Path(data_dir) / "sessions" / session_id / "meetings" / f"{meeting_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())
