# ABOUTME: Entry point for running the TUI via `python -m tui`.
# ABOUTME: Parses --data-dir argument and launches the Textual app.

import argparse
from pathlib import Path

from preprocessor.paths import default_data_dir
from tui.app import AgentBoardApp


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Board TUI viewer")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=default_data_dir(),
        help="Path to preprocessed data directory (default: ~/.local/share/agent-board/)",
    )
    args = parser.parse_args()
    AgentBoardApp(data_dir=args.data_dir).run()


if __name__ == "__main__":
    main()
