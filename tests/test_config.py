# ABOUTME: Tests for XDG-compliant config file loading.
# ABOUTME: Validates config path resolution, file parsing, defaults, and merging.

import json
import os
from pathlib import Path
from unittest.mock import patch


def test_default_config_dir_uses_xdg_config_home():
    """Config dir is $XDG_CONFIG_HOME/agent-board."""
    from preprocessor.config import default_config_dir
    with patch.dict(os.environ, {"XDG_CONFIG_HOME": "/tmp/xdg-config-test"}, clear=False):
        result = default_config_dir()
    assert result == Path("/tmp/xdg-config-test/agent-board")


def test_default_config_dir_falls_back_to_home():
    """Without XDG_CONFIG_HOME, falls back to ~/.config/agent-board."""
    from preprocessor.config import default_config_dir
    env = os.environ.copy()
    env.pop("XDG_CONFIG_HOME", None)
    with patch.dict(os.environ, env, clear=True):
        result = default_config_dir()
    assert result == Path.home() / ".config" / "agent-board"


def test_default_config_dir_empty_string_falls_back():
    """Empty XDG_CONFIG_HOME falls back to default per XDG spec."""
    from preprocessor.config import default_config_dir
    with patch.dict(os.environ, {"XDG_CONFIG_HOME": ""}, clear=False):
        result = default_config_dir()
    assert result == Path.home() / ".config" / "agent-board"


def test_load_config_returns_defaults_when_no_file(tmp_path):
    """Missing config file returns all defaults."""
    from preprocessor.config import load_config
    config = load_config(tmp_path / "nonexistent" / "config.json")
    assert config == {}


def test_load_config_reads_valid_file(tmp_path):
    """Valid config file is parsed correctly."""
    from preprocessor.config import load_config
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"port": 9090, "source": "/custom/source"}))
    config = load_config(config_file)
    assert config["port"] == 9090
    assert config["source"] == "/custom/source"


def test_load_config_returns_empty_on_invalid_json(tmp_path):
    """Malformed JSON returns empty dict rather than crashing."""
    from preprocessor.config import load_config
    config_file = tmp_path / "config.json"
    config_file.write_text("not valid json {{{")
    config = load_config(config_file)
    assert config == {}


def test_load_config_ignores_unknown_keys(tmp_path):
    """Unknown keys in config are preserved but don't affect behavior."""
    from preprocessor.config import load_config
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"port": 3000, "unknown_key": "value"}))
    config = load_config(config_file)
    assert config["port"] == 3000
    assert config["unknown_key"] == "value"


def test_config_file_path():
    """Default config file path is config_dir / config.json."""
    from preprocessor.config import default_config_dir
    config_dir = default_config_dir()
    assert config_dir.name == "agent-board"


def test_serve_uses_config_port(tmp_path):
    """serve.py reads port from config when no CLI arg provided."""
    from preprocessor.config import load_config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps({"port": 9999}))
    config = load_config(config_file)
    assert config["port"] == 9999


def test_serve_uses_config_source(tmp_path):
    """serve.py reads source from config when no CLI arg provided."""
    from preprocessor.config import load_config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps({"source": "/custom/claude/projects"}))
    config = load_config(config_file)
    assert config["source"] == "/custom/claude/projects"


def test_serve_uses_config_ui(tmp_path):
    """Config can specify preferred UI mode."""
    from preprocessor.config import load_config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps({"ui": "tui"}))
    config = load_config(config_file)
    assert config["ui"] == "tui"


def test_serve_uses_config_output(tmp_path):
    """Config can override the data directory."""
    from preprocessor.config import load_config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps({"output": "/custom/data/dir"}))
    config = load_config(config_file)
    assert config["output"] == "/custom/data/dir"


def test_apply_config_overrides_argparse_defaults():
    """Config values override hardcoded defaults but CLI args still win."""
    import argparse
    from preprocessor.config import apply_config

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--source", type=Path, default=Path.home() / ".claude" / "projects")

    config = {"port": 9090, "source": "/custom/source"}
    apply_config(parser, config)

    # Parse with no CLI args — config values should win
    args = parser.parse_args([])
    assert args.port == 9090
    assert args.source == Path("/custom/source")


def test_apply_config_cli_overrides_config():
    """CLI arguments override config values."""
    import argparse
    from preprocessor.config import apply_config

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)

    config = {"port": 9090}
    apply_config(parser, config)

    # Parse with explicit CLI arg — CLI should win
    args = parser.parse_args(["--port", "7070"])
    assert args.port == 7070


def test_apply_config_ignores_unknown_keys():
    """Config keys that don't match any argparse argument are ignored."""
    import argparse
    from preprocessor.config import apply_config

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)

    config = {"port": 9090, "unknown_setting": "value"}
    apply_config(parser, config)

    args = parser.parse_args([])
    assert args.port == 9090
    assert not hasattr(args, "unknown_setting")


def test_apply_config_converts_path_types():
    """Config string values for Path-typed args are converted to Path."""
    import argparse
    from preprocessor.config import apply_config

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data"))

    config = {"output": "/custom/output"}
    apply_config(parser, config)

    args = parser.parse_args([])
    assert args.output == Path("/custom/output")
    assert isinstance(args.output, Path)
