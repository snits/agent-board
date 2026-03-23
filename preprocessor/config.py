# ABOUTME: Loads persistent configuration from an XDG-compliant TOML file.
# ABOUTME: Reads ~/.config/agent-board/config.toml for source and port settings.

import sys
import tomllib
from pathlib import Path

from preprocessor.paths import default_config_dir

CONFIG_FILENAME = "config.toml"

# Schema: key -> expected type
_SCHEMA = {
    "source": str,
    "port": int,
}


def load_config(config_dir: Path | None = None) -> dict:
    """Load configuration from config.toml in the given directory.

    Returns a dict with validated, type-checked values. Only keys defined
    in _SCHEMA are returned. Source paths have ~ expanded.

    Missing config file returns empty dict. Malformed TOML or type errors
    cause a clear error message and sys.exit(1).
    """
    if config_dir is None:
        config_dir = default_config_dir()
    config_dir = Path(config_dir)
    config_file = config_dir / CONFIG_FILENAME
    if not config_file.exists():
        return {}

    try:
        raw = tomllib.loads(config_file.read_text())
    except tomllib.TOMLDecodeError as e:
        print(f"Error: malformed config file {config_file}: {e}", file=sys.stderr)
        sys.exit(1)

    general = raw.get("general", {})
    result = {}

    for key, expected_type in _SCHEMA.items():
        if key not in general:
            continue
        value = general[key]
        if not isinstance(value, expected_type):
            print(
                f"Error: {config_file}: '{key}' must be {expected_type.__name__}, "
                f"got {type(value).__name__}",
                file=sys.stderr,
            )
            sys.exit(1)
        if key == "source":
            value = Path(value).expanduser()
        result[key] = value

    return result
