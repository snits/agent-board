# ABOUTME: Discovers projects and sessions in claude's storage and conversation archives.
# ABOUTME: Supports both native nested layout and flat archive layout.

import json
import os
import re
from collections import defaultdict
from pathlib import Path


def derive_display_name(slug: str) -> str:
    """Convert a project slug to a human-readable display name.

    Slugs encode a full path with '-' replacing '/'. Since '-' also
    appears within directory names, we resolve the ambiguity by checking
    the filesystem.
    """
    resolved = _resolve_slug_to_path(slug)

    if resolved is not None:
        # Try to derive relative to user's home directory
        try:
            home = Path.home()
            return str(resolved.relative_to(home))
        except ValueError:
            pass

        # Not under home — find "Users/<username>" in path components and
        # return everything after as a slash-joined display name.
        parts = resolved.parts
        for i, part in enumerate(parts):
            if part == "Users" and i + 2 < len(parts):
                return "/".join(parts[i + 2:])

        return str(resolved)

    # Fallback: clean up the slug manually without filesystem access
    path_str = slug.lstrip("-")
    parts = path_str.split("-")
    try:
        users_idx = parts.index("Users")
        remaining = parts[users_idx + 2:]
    except ValueError:
        remaining = parts

    return "-".join(remaining) if remaining else slug


def _resolve_slug_to_path(slug: str) -> Path | None:
    """Resolve a project slug to a real filesystem path.

    Slugs are built by replacing all '/' with '-' in the original path.
    Since '-' also appears in directory names, we walk the filesystem
    greedily, matching each real directory name against the slug prefix.
    """
    path_str = slug.lstrip("-")
    return _match_path_components(Path("/"), path_str)


def _match_path_components(current: Path, remaining: str) -> Path | None:
    """Recursively match remaining slug characters to filesystem entries under current."""
    if not remaining:
        return current

    try:
        entries = list(current.iterdir())
    except (PermissionError, NotADirectoryError, OSError):
        return None

    # Sort longest names first so we greedily prefer longer directory matches
    for entry in sorted(entries, key=lambda e: len(e.name), reverse=True):
        name = entry.name
        if remaining == name:
            return entry
        if remaining.startswith(name + "-"):
            result = _match_path_components(entry, remaining[len(name) + 1:])
            if result is not None:
                return result

    return None


def scan_projects(source_dir: Path) -> list[dict]:
    """Scan a source directory for projects containing agent teams sessions."""
    source_dir = Path(source_dir)
    if not source_dir.is_dir():
        return []

    projects = []

    for entry in sorted(source_dir.iterdir()):
        if not entry.is_dir():
            continue

        sessions = _find_sessions(entry)
        if not sessions:
            continue

        projects.append({
            "slug": entry.name,
            "displayName": derive_display_name(entry.name),
            "sessions": sessions,
        })

    return projects


def _find_sessions(project_dir: Path) -> list[dict]:
    """Find sessions with subagents in a project directory."""
    sessions = []

    for entry in sorted(project_dir.iterdir()):
        if not entry.is_dir():
            continue
        if not _looks_like_uuid(entry.name):
            continue
        subagents_dir = entry / "subagents"
        if not subagents_dir.is_dir():
            continue
        main_jsonl = project_dir / f"{entry.name}.jsonl"

        sessions.append({
            "id": entry.name,
            "dir": str(entry),
            "subagentsDir": str(subagents_dir),
            "mainJsonl": str(main_jsonl) if main_jsonl.exists() else None,
        })

    return sessions


def scan_archive(archive_dir: Path) -> list[dict]:
    """Scan a flat conversation archive for projects and sessions.

    Archive layout is flat: project-slug/UUID.jsonl and project-slug/agent-*.jsonl
    with no nested subagents/ directories or meta.json files.
    """
    archive_dir = Path(archive_dir)
    if not archive_dir.is_dir():
        return []

    projects = []

    for entry in sorted(archive_dir.iterdir()):
        if not entry.is_dir():
            continue

        sessions = _find_archive_sessions(entry)
        if not sessions:
            continue

        projects.append({
            "slug": entry.name,
            "displayName": derive_display_name(entry.name),
            "sessions": sessions,
        })

    return projects


def _find_archive_sessions(project_dir: Path) -> list[dict]:
    """Find sessions in a flat archive project directory.

    Groups agent-*.jsonl files to sessions by reading the sessionId
    from each agent file's first record.
    """
    # Find session JSONL files (UUID.jsonl, not agent-*.jsonl)
    session_ids = set()
    for f in project_dir.iterdir():
        if f.suffix == ".jsonl" and _looks_like_uuid(f.stem) and not f.stem.startswith("agent-"):
            session_ids.add(f.stem)

    if not session_ids:
        return []

    # Group agent files by sessionId
    agents_by_session = defaultdict(list)
    for f in sorted(project_dir.glob("agent-*.jsonl")):
        session_id = _read_session_id(f)
        if session_id and session_id in session_ids:
            agents_by_session[session_id].append(str(f))

    sessions = []
    for sid in sorted(session_ids):
        main_jsonl = project_dir / f"{sid}.jsonl"
        sessions.append({
            "id": sid,
            "dir": str(project_dir),
            "subagentsDir": None,
            "agentJsonls": agents_by_session.get(sid, []),
            "mainJsonl": str(main_jsonl) if main_jsonl.exists() else None,
        })

    return sessions


def _read_session_id(jsonl_path: Path) -> str | None:
    """Read the sessionId from the first record of a JSONL file."""
    try:
        with open(jsonl_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                return record.get("sessionId")
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _looks_like_uuid(name: str) -> bool:
    """Check if a string looks like a UUID."""
    return bool(re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-', name))
