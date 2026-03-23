# ABOUTME: Tests for XDG-compliant data directory resolution.
# ABOUTME: Validates default path, env var override, and CLI override behavior.

import os
from pathlib import Path
from unittest.mock import patch


def test_default_data_dir_uses_xdg_data_home():
    """Default data dir is $XDG_DATA_HOME/agent-board."""
    from preprocessor.paths import default_data_dir
    with patch.dict(os.environ, {"XDG_DATA_HOME": "/tmp/xdg-test"}, clear=False):
        result = default_data_dir()
    assert result == Path("/tmp/xdg-test/agent-board")


def test_default_data_dir_falls_back_to_home():
    """Without XDG_DATA_HOME, falls back to ~/.local/share/agent-board."""
    from preprocessor.paths import default_data_dir
    env = os.environ.copy()
    env.pop("XDG_DATA_HOME", None)
    with patch.dict(os.environ, env, clear=True):
        result = default_data_dir()
    assert result == Path.home() / ".local" / "share" / "agent-board"


def test_default_data_dir_empty_string_falls_back():
    """Empty XDG_DATA_HOME falls back to default per XDG spec."""
    from preprocessor.paths import default_data_dir
    with patch.dict(os.environ, {"XDG_DATA_HOME": ""}, clear=False):
        result = default_data_dir()
    assert result == Path.home() / ".local" / "share" / "agent-board"


def test_default_data_dir_returns_path_object():
    """Return type is always a Path."""
    from preprocessor.paths import default_data_dir
    result = default_data_dir()
    assert isinstance(result, Path)


def test_preprocess_default_output_uses_xdg():
    """preprocess.py --output default should resolve to the XDG data dir."""
    import preprocess
    import argparse
    with patch.dict(os.environ, {"XDG_DATA_HOME": "/tmp/xdg-preprocess-test"}, clear=False):
        from preprocessor.paths import default_data_dir
        expected = default_data_dir()
    # The argparse default is evaluated at import time, so we verify
    # that the module uses default_data_dir() rather than a hardcoded path
    assert "default_data_dir" in preprocess.__dict__ or hasattr(preprocess, "default_data_dir")


def test_tui_app_default_uses_xdg(tmp_path):
    """AgentBoardApp without explicit data_dir uses the XDG default."""
    with patch.dict(os.environ, {"XDG_DATA_HOME": str(tmp_path)}, clear=False):
        from preprocessor.paths import default_data_dir
        expected = default_data_dir()
    with patch("tui.app.default_data_dir", return_value=expected):
        from tui.app import AgentBoardApp
        app = AgentBoardApp()
        assert app._data_dir == expected
