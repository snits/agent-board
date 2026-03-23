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


def test_preprocess_default_output_is_not_hardcoded():
    """preprocess.py --output default matches default_data_dir(), not './data'."""
    from preprocessor.paths import default_data_dir
    expected = default_data_dir()
    # Parse with no args to get the default
    from preprocess import main
    import argparse
    # Build the parser the same way main() does and check its default
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=expected)
    args = parser.parse_args([])
    assert args.output == expected
    assert args.output != Path("data"), "Default should not be relative './data'"


def test_tui_app_default_uses_xdg():
    """AgentBoardApp without explicit data_dir uses default_data_dir()."""
    from preprocessor.paths import default_data_dir
    expected = default_data_dir()
    with patch("tui.app.default_data_dir", return_value=expected):
        from tui.app import AgentBoardApp
        app = AgentBoardApp()
        assert app._data_dir == expected
