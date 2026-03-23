# ABOUTME: Tests for TOML config file loading.
# ABOUTME: Validates parsing, type checking, error handling, and tilde expansion.

import os
from pathlib import Path
from unittest.mock import patch

import pytest


def test_load_config_returns_empty_when_no_file(tmp_path):
    """Missing config file returns empty dict."""
    from preprocessor.config import load_config
    config = load_config(tmp_path / "nonexistent")
    assert config == {}


def test_load_config_parses_valid_toml(tmp_path):
    """Valid TOML with both keys is parsed correctly."""
    from preprocessor.config import load_config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        "[general]\nsource = \"/custom/source\"\nport = 9090\n"
    )
    config = load_config(config_dir)
    assert config["source"] == Path("/custom/source")
    assert config["port"] == 9090


def test_load_config_parses_source_only(tmp_path):
    """Config with only source key works."""
    from preprocessor.config import load_config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        "[general]\nsource = \"/my/projects\"\n"
    )
    config = load_config(config_dir)
    assert config["source"] == Path("/my/projects")
    assert "port" not in config


def test_load_config_parses_port_only(tmp_path):
    """Config with only port key works."""
    from preprocessor.config import load_config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text("[general]\nport = 3000\n")
    config = load_config(config_dir)
    assert config["port"] == 3000
    assert "source" not in config


def test_load_config_exits_on_malformed_toml(tmp_path, capsys):
    """Malformed TOML causes sys.exit with clear error message."""
    from preprocessor.config import load_config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text("not valid [[[toml")
    with pytest.raises(SystemExit) as exc_info:
        load_config(config_dir)
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert str(config_file) in captured.err


def test_load_config_exits_on_wrong_port_type(tmp_path, capsys):
    """Non-integer port causes sys.exit with clear error message."""
    from preprocessor.config import load_config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        '[general]\nport = "banana"\n'
    )
    with pytest.raises(SystemExit) as exc_info:
        load_config(config_dir)
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "port" in captured.err


def test_load_config_exits_on_wrong_source_type(tmp_path, capsys):
    """Non-string source causes sys.exit with clear error message."""
    from preprocessor.config import load_config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text("[general]\nsource = 42\n")
    with pytest.raises(SystemExit) as exc_info:
        load_config(config_dir)
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "source" in captured.err


def test_load_config_expands_tilde_in_source(tmp_path):
    """Tilde in source path is expanded to home directory."""
    from preprocessor.config import load_config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        '[general]\nsource = "~/my-projects"\n'
    )
    config = load_config(config_dir)
    assert config["source"] == Path.home() / "my-projects"


def test_load_config_empty_general_section(tmp_path):
    """Empty [general] section returns empty dict."""
    from preprocessor.config import load_config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text("[general]\n")
    config = load_config(config_dir)
    assert config == {}


def test_cli_precedence_config_overrides_default(tmp_path):
    """Config value is used when no CLI arg is provided."""
    from preprocessor.config import load_config
    from preprocessor.paths import default_source_dir
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        '[general]\nsource = "/from-config"\nport = 9999\n'
    )
    config = load_config(config_dir)
    # Simulate precedence: CLI None → config → default
    cli_source = None
    resolved_source = cli_source if cli_source is not None else config.get("source", default_source_dir())
    assert resolved_source == Path("/from-config")

    cli_port = None
    resolved_port = cli_port if cli_port is not None else config.get("port", 8080)
    assert resolved_port == 9999


def test_cli_precedence_cli_overrides_config(tmp_path):
    """CLI arg wins over config value."""
    from preprocessor.config import load_config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        '[general]\nsource = "/from-config"\nport = 9999\n'
    )
    config = load_config(config_dir)
    # Simulate CLI providing explicit values
    cli_source = Path("/from-cli")
    resolved_source = cli_source if cli_source is not None else config.get("source")
    assert resolved_source == Path("/from-cli")

    cli_port = 7070
    resolved_port = cli_port if cli_port is not None else config.get("port")
    assert resolved_port == 7070
