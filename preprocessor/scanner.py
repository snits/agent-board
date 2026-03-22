# ABOUTME: Discovers projects and sessions in claude's internal storage.
# ABOUTME: Scans ~/.claude/projects/ for sessions that contain agent teams data.

import os
import re
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


def _looks_like_uuid(name: str) -> bool:
    """Check if a string looks like a UUID."""
    return bool(re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-', name))
