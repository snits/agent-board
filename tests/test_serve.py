# ABOUTME: Tests for the web server's data directory routing.
# ABOUTME: Validates that /data/ URL paths map to the XDG data directory safely.

import io
from pathlib import Path

from serve import Handler


def _make_handler(data_dir: Path, directory: str = "/tmp") -> Handler:
    """Create a Handler instance with minimal socket plumbing for testing."""
    # Handler.__init__ requires request, client_address, server args.
    # We bypass __init__ and set up the attributes translate_path needs.
    handler = Handler.__new__(Handler)
    handler.data_dir = data_dir
    # SimpleHTTPRequestHandler.translate_path needs self.directory
    handler.directory = directory
    return handler


def test_translate_path_routes_data_to_xdg_dir(tmp_path):
    """Requests for /data/... are served from the configured data directory."""
    data_dir = tmp_path / "xdg-data" / "agent-board"
    data_dir.mkdir(parents=True)
    handler = _make_handler(data_dir)

    result = handler.translate_path("/data/index.json")
    assert result == str(data_dir / "index.json")


def test_translate_path_routes_data_subdir(tmp_path):
    """Nested /data/ paths are routed correctly."""
    data_dir = tmp_path / "xdg-data" / "agent-board"
    data_dir.mkdir(parents=True)
    handler = _make_handler(data_dir)

    result = handler.translate_path("/data/sessions/abc/session.json")
    assert result == str(data_dir / "sessions" / "abc" / "session.json")


def test_translate_path_non_data_uses_default(tmp_path):
    """Non-/data/ paths use the standard translate_path behavior."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    project_root = str(tmp_path / "project")
    handler = _make_handler(data_dir, directory=project_root)

    result = handler.translate_path("/frontend/index.html")
    # Should delegate to SimpleHTTPRequestHandler which joins with self.directory
    assert result.startswith(project_root)
    assert "frontend" in result


def test_translate_path_blocks_traversal(tmp_path):
    """Path traversal via /data/../../ must be clamped to data dir."""
    data_dir = tmp_path / "xdg-data" / "agent-board"
    data_dir.mkdir(parents=True)
    handler = _make_handler(data_dir)

    result = handler.translate_path("/data/../../etc/passwd")
    resolved = Path(result).resolve()
    assert str(resolved).startswith(str(data_dir.resolve())), (
        f"Path traversal escaped data dir: {resolved}"
    )


def test_translate_path_blocks_encoded_traversal(tmp_path):
    """Percent-encoded traversal via /data/..%2F..%2F must be clamped."""
    data_dir = tmp_path / "xdg-data" / "agent-board"
    data_dir.mkdir(parents=True)
    handler = _make_handler(data_dir)

    # SimpleHTTPRequestHandler.translate_path decodes percent-encoding,
    # but our override receives the raw path. Test both forms.
    result = handler.translate_path("/data/../../../etc/passwd")
    resolved = Path(result).resolve()
    assert str(resolved).startswith(str(data_dir.resolve())), (
        f"Path traversal escaped data dir: {resolved}"
    )
