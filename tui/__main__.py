# ABOUTME: Entry point for running the TUI via `python -m tui`.
# ABOUTME: Parses --data-dir argument and launches the Textual app.

import argparse
from pathlib import Path

from preprocessor.paths import default_data_dir, default_source_dir
from tui.app import AgentBoardApp


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Board TUI viewer")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Path to preprocessed data directory (default: ~/.local/share/agent-board/)",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Source directory to scan on refresh (default: ~/.claude/projects/)",
    )
    args = parser.parse_args()
    data_dir = args.data_dir if args.data_dir is not None else default_data_dir()
    source_dir = args.source if args.source is not None else default_source_dir()
    AgentBoardApp(data_dir=data_dir, source_dir=source_dir).run()


if __name__ == "__main__":
    main()
