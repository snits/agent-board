# ABOUTME: Tests for the web server's data directory routing.
# ABOUTME: Validates that /data/ URL paths map to the XDG data directory.

from pathlib import Path
from unittest.mock import patch, MagicMock

from serve import Handler


def test_translate_path_routes_data_to_xdg_dir(tmp_path):
    """Requests for /data/... are served from the configured data directory."""
    Handler.data_dir = tmp_path / "xdg-data" / "agent-board"

    handler = MagicMock(spec=Handler)
    handler.data_dir = Handler.data_dir

    result = Handler.translate_path(handler, "/data/index.json")
    assert result == str(tmp_path / "xdg-data" / "agent-board" / "index.json")


def test_translate_path_routes_data_subdir(tmp_path):
    """Nested /data/ paths are routed correctly."""
    Handler.data_dir = tmp_path / "xdg-data" / "agent-board"

    handler = MagicMock(spec=Handler)
    handler.data_dir = Handler.data_dir

    result = Handler.translate_path(handler, "/data/sessions/abc/session.json")
    expected = str(tmp_path / "xdg-data" / "agent-board" / "sessions" / "abc" / "session.json")
    assert result == expected


def test_translate_path_non_data_uses_default(tmp_path):
    """Non-/data/ paths use the default translate_path behavior."""
    Handler.data_dir = tmp_path

    handler = MagicMock(spec=Handler)
    handler.data_dir = Handler.data_dir

    # Call the real translate_path; it should delegate to super for non-/data/ paths
    with patch.object(
        Handler.__bases__[0], "translate_path", return_value="/project/frontend/index.html"
    ) as mock_super:
        result = Handler.translate_path(handler, "/frontend/index.html")
    mock_super.assert_called_once_with("/frontend/index.html")
    assert result == "/project/frontend/index.html"
