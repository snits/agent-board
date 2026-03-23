# ABOUTME: Tests for XDG-compliant path resolution (data, config, source).
# ABOUTME: Validates default paths, env var overrides, and fallback behavior.

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


def test_default_config_dir_uses_xdg_config_home():
    """Config dir is $XDG_CONFIG_HOME/agent-board."""
    from preprocessor.paths import default_config_dir
    with patch.dict(os.environ, {"XDG_CONFIG_HOME": "/tmp/xdg-config-test"}, clear=False):
        result = default_config_dir()
    assert result == Path("/tmp/xdg-config-test/agent-board")


def test_default_config_dir_falls_back_to_home():
    """Without XDG_CONFIG_HOME, falls back to ~/.config/agent-board."""
    from preprocessor.paths import default_config_dir
    env = os.environ.copy()
    env.pop("XDG_CONFIG_HOME", None)
    with patch.dict(os.environ, env, clear=True):
        result = default_config_dir()
    assert result == Path.home() / ".config" / "agent-board"


def test_default_config_dir_empty_string_falls_back():
    """Empty XDG_CONFIG_HOME falls back to default per XDG spec."""
    from preprocessor.paths import default_config_dir
    with patch.dict(os.environ, {"XDG_CONFIG_HOME": ""}, clear=False):
        result = default_config_dir()
    assert result == Path.home() / ".config" / "agent-board"


def test_default_source_dir():
    """Source dir defaults to ~/.claude/projects."""
    from preprocessor.paths import default_source_dir
    result = default_source_dir()
    assert result == Path.home() / ".claude" / "projects"
    assert isinstance(result, Path)


def test_preprocess_default_source_uses_default_source_dir():
    """preprocess.py resolves --source to default_source_dir() when omitted."""
    from preprocessor.paths import default_source_dir
    from unittest.mock import patch as mock_patch
    import preprocess
    # Call main() with no args, intercepting run_preprocess to capture source_dir
    captured = {}
    def fake_run(source_dir, output_dir):
        captured["source"] = source_dir
    with mock_patch.object(preprocess, "run_preprocess", fake_run), \
         mock_patch("sys.argv", ["preprocess"]), \
         mock_patch.object(preprocess, "load_config", return_value={}):
        preprocess.main()
    assert captured["source"] == default_source_dir()


def test_tui_app_default_uses_xdg():
    """AgentBoardApp without explicit data_dir uses default_data_dir()."""
    from preprocessor.paths import default_data_dir
    expected = default_data_dir()
    with patch("tui.app.default_data_dir", return_value=expected):
        from tui.app import AgentBoardApp
        app = AgentBoardApp()
        assert app._data_dir == expected
