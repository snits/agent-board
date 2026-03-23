# ABOUTME: Loads persistent configuration from XDG-compliant config directory.
# ABOUTME: Reads ~/.config/agent-board/config.json for default settings.

import argparse
import json
import os
from pathlib import Path

APP_NAME = "agent-board"
CONFIG_FILENAME = "config.json"


def default_config_dir() -> Path:
    """Return the XDG-compliant config directory for agent-board.

    Uses $XDG_CONFIG_HOME/agent-board if set, otherwise ~/.config/agent-board.
    """
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / APP_NAME
    return Path.home() / ".config" / APP_NAME


def load_config(config_path: Path | None = None) -> dict:
    """Load configuration from a JSON file.

    Returns an empty dict if the file doesn't exist or contains invalid JSON.
    """
    if config_path is None:
        config_path = default_config_dir() / CONFIG_FILENAME
    config_path = Path(config_path)
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def apply_config(parser: argparse.ArgumentParser, config: dict) -> None:
    """Override argparse defaults with values from the config dict.

    Only config keys that match a registered argparse argument are applied.
    Values are converted through the argument's type function if one is set.
    """
    # Build a map of dest -> action for all registered arguments
    actions = {action.dest: action for action in parser._actions}
    new_defaults = {}
    for key, value in config.items():
        # Convert config key from kebab-case or snake_case to argparse dest
        dest = key.replace("-", "_")
        if dest in actions:
            action = actions[dest]
            if action.type and not isinstance(value, action.type):
                value = action.type(value)
            new_defaults[dest] = value
    if new_defaults:
        parser.set_defaults(**new_defaults)
