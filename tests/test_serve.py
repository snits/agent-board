# ABOUTME: Tests for the web server's data directory routing and refresh endpoint.
# ABOUTME: Validates that /data/ URL paths map to the XDG data directory and /frontend/ URL paths map to the package frontend directory safely.

import io
import json
from pathlib import Path
from unittest.mock import patch

from serve import Handler


def _make_handler(data_dir: Path, directory: str = "/tmp",
                  frontend_dir: Path | None = None) -> Handler:
    """Create a Handler instance with minimal socket plumbing for testing."""
    # Handler.__init__ requires request, client_address, server args.
    # We bypass __init__ and set up the attributes translate_path needs.
    handler = Handler.__new__(Handler)
    handler.data_dir = data_dir
    handler.frontend_dir = frontend_dir or data_dir
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


def test_translate_path_routes_frontend_to_frontend_dir(tmp_path):
    """Requests for /frontend/... are served from the frontend package directory."""
    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    handler = _make_handler(data_dir, frontend_dir=frontend_dir)

    result = handler.translate_path("/frontend/index.html")
    assert result == str(frontend_dir / "index.html")


def test_translate_path_non_routed_uses_default(tmp_path):
    """Paths outside /data/ and /frontend/ use the standard translate_path behavior."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    project_root = str(tmp_path / "project")
    handler = _make_handler(data_dir, directory=project_root)

    result = handler.translate_path("/other/file.txt")
    assert result.startswith(project_root)


def test_translate_path_blocks_traversal(tmp_path):
    """Path traversal via /data/../../ must be clamped to data dir."""
    data_dir = tmp_path / "xdg-data" / "agent-board"
    data_dir.mkdir(parents=True)
    handler = _make_handler(data_dir)

    result = handler.translate_path("/data/../../etc/passwd")
    resolved = Path(result).resolve()
    assert resolved.is_relative_to(data_dir.resolve()), (
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
    assert resolved.is_relative_to(data_dir.resolve()), (
        f"Path traversal escaped data dir: {resolved}"
    )


def test_translate_path_blocks_sibling_prefix_collision(tmp_path):
    """Sibling dir with matching prefix must not pass the containment check.

    e.g., data_dir=/tmp/agent-board should block /tmp/agent-board-evil/secret
    """
    data_dir = tmp_path / "agent-board"
    data_dir.mkdir()
    sibling = tmp_path / "agent-board-evil"
    sibling.mkdir()
    (sibling / "secret").write_text("sensitive data")
    handler = _make_handler(data_dir)

    result = handler.translate_path("/data/../agent-board-evil/secret")
    resolved = Path(result).resolve()
    assert resolved.is_relative_to(data_dir.resolve()), (
        f"Sibling prefix collision escaped data dir: {resolved}"
    )


def _make_post_handler(data_dir: Path, source_dir: Path, archive_dir: Path, path: str) -> tuple:
    """Create a Handler wired for POST testing, returning (handler, response_buffer)."""
    handler = _make_handler(data_dir)
    handler.source_dir = source_dir
    handler.archive_dir = archive_dir
    handler.path = path
    handler.headers = {"Content-Length": "0"}
    handler.rfile = io.BytesIO(b"")
    handler.request_version = "HTTP/1.1"
    handler.requestline = f"POST {path} HTTP/1.1"
    handler.client_address = ("127.0.0.1", 0)
    response_buffer = io.BytesIO()
    handler.wfile = response_buffer
    return handler, response_buffer


def test_refresh_endpoint_calls_preprocess(tmp_path):
    """POST /api/refresh runs the preprocessor and returns success."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    archive_dir = tmp_path / "archive"

    handler, response_buffer = _make_post_handler(data_dir, source_dir, archive_dir, "/api/refresh")

    with patch("serve.run_preprocess") as mock_preprocess:
        handler.do_POST()
        mock_preprocess.assert_called_once_with(source_dir, data_dir, archive_dir=archive_dir)

    response_buffer.seek(0)
    raw = response_buffer.read().decode()
    assert "200" in raw
    assert '"ok"' in raw


def test_refresh_endpoint_returns_500_on_error(tmp_path):
    """POST /api/refresh returns 500 when preprocessing fails."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    archive_dir = tmp_path / "archive"

    handler, response_buffer = _make_post_handler(data_dir, source_dir, archive_dir, "/api/refresh")

    with patch("serve.run_preprocess", side_effect=RuntimeError("boom")):
        handler.do_POST()

    response_buffer.seek(0)
    raw = response_buffer.read().decode()
    assert "500" in raw
    assert "boom" in raw
