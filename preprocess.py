# ABOUTME: CLI entry point for the agent board preprocessor.
# ABOUTME: Thin wrapper that delegates to preprocessor.pipeline.

import argparse
from pathlib import Path

from preprocessor.config import load_config
from preprocessor.paths import default_archive_dir, default_data_dir, default_source_dir
from preprocessor.pipeline import run_preprocess


def main():
    parser = argparse.ArgumentParser(description="Preprocess Claude Code agent teams transcripts")
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Source directory to scan (default: ~/.claude/projects/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory (default: ~/.local/share/agent-board/)",
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=None,
        help="Conversation archive directory (default: auto-detect)",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Disable archive scanning",
    )
    args = parser.parse_args()
    config = load_config()
    args.source = args.source if args.source is not None else config.get("source", default_source_dir())
    args.output = args.output if args.output is not None else default_data_dir()
    if args.no_archive:
        archive_dir = None
    else:
        archive_dir = args.archive if args.archive is not None else default_archive_dir()
    run_preprocess(args.source, args.output, archive_dir=archive_dir)


if __name__ == "__main__":
    main()
