# ABOUTME: Resolves XDG-compliant paths for agent-board storage and config.
# ABOUTME: Provides default directories for data, config, and source following XDG spec.

import os
from pathlib import Path

APP_NAME = "agent-board"


def default_data_dir() -> Path:
    """Return the XDG-compliant data directory for agent-board.

    Uses $XDG_DATA_HOME/agent-board if set, otherwise ~/.local/share/agent-board.
    """
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def default_config_dir() -> Path:
    """Return the XDG-compliant config directory for agent-board.

    Uses $XDG_CONFIG_HOME/agent-board if set, otherwise ~/.config/agent-board.
    """
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / APP_NAME
    return Path.home() / ".config" / APP_NAME


def default_source_dir() -> Path:
    """Return the default Claude projects directory."""
    return Path.home() / ".claude" / "projects"
