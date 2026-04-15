# Agent Board

A viewer for Claude Code agent team transcripts. Browse multi-agent conversations — see what your agent teams were doing, how they collaborated, and what tools they used. Available as a web UI or terminal UI (TUI).

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Setup

```bash
# Clone and enter the project
git clone <repo-url>
cd agent-board

# Create a virtual environment and install
uv venv .venv
uv pip install -e ".[dev]" --python .venv/bin/python
```

## Usage

### Web UI

```bash
# Preprocess transcripts and start the web server
.venv/bin/python serve.py
```

Then open http://localhost:8080 in your browser.

### Terminal UI (TUI)

```bash
# Preprocess and launch the terminal viewer
.venv/bin/python serve.py --tui

# Or run the TUI standalone against already-preprocessed data
.venv/bin/python -m tui [--data-dir PATH] [--source PATH]
```

The TUI reads preprocessed data from `~/.local/share/agent-board/` by default; override with `--data-dir`. The `--source` flag sets the Claude projects directory used when refreshing live.

**TUI keybindings:** `q` quit, `/` search, `f` filter by agent, `v` toggle detail pane, `Tab` switch panel, `r` refresh data, `Esc` back

By default, Agent Board scans `~/.claude/projects/` for agent team sessions.

### CLI options

```
serve.py [--source PATH] [--output PATH] [--port PORT] [--skip-preprocess] [--tui]

  --source PATH          Claude projects directory (default: ~/.claude/projects/)
  --output PATH          Preprocessed data output directory (default: ~/.local/share/agent-board/)
  --port PORT            HTTP server port (default: 8080)
  --skip-preprocess      Skip preprocessing, serve existing data
  --tui                  Launch terminal UI instead of web server
```

### Preprocessing only

To regenerate the data without starting the server:

```bash
.venv/bin/python preprocess.py [--source PATH] [--output PATH]
```

## How it works

Agent Board has two parts:

1. **Preprocessor** (`preprocess.py`, `preprocessor/`) — Scans Claude Code's project storage, parses agent JSONL transcripts, groups messages into meetings by `promptId`, deduplicates broadcast messages, and writes per-meeting JSON files.

2. **Web Frontend** (`frontend/`, `serve.py`) — A vanilla HTML/CSS/JS viewer served by a Python HTTP server. Three-panel layout: sidebar navigation, chat message stream, and agent roster.

3. **Terminal UI** (`tui/`) — A Textual-based TUI with keyboard-driven navigation. Two-panel layout: project/session/meeting tree (left) and chat message stream (right), with agent roster header bar and search.

### Data flow

```
~/.claude/projects/
  └── {project}/
      └── {session}/
          └── subagents/
              ├── agent-{id}.jsonl      ← raw transcripts
              └── agent-{id}.meta.json  ← agent metadata

        ↓  preprocess.py

~/.local/share/agent-board/        (override with --output)
  ├── index.json                  ← project/session tree
  ├── agent-types.json            ← agent type → color/label
  └── sessions/{id}/
      ├── session.json            ← session metadata + meeting list
      └── meetings/{id}.json      ← messages, agents, timestamps
```

## Project structure

```
agent-board/
  ├── preprocess.py          # CLI entry point for preprocessing
  ├── serve.py               # Preprocess + HTTP server
  ├── preprocessor/
  │   ├── scanner.py         # Discovers projects and sessions
  │   ├── parser.py          # Parses JSONL records
  │   ├── grouper.py         # Groups messages into meetings
  │   └── writer.py          # Writes output JSON files
  ├── frontend/
  │   ├── index.html         # Three-panel layout
  │   ├── style.css          # Dark theme
  │   └── app.js             # Application logic
  ├── tui/
  │   ├── app.py             # Textual app composition and keybindings
  │   ├── data.py            # JSON data loading layer
  │   ├── __main__.py        # Entry point for python -m tui
  │   └── widgets/           # Nav tree, chat view, agent bar, search bar
  └── tests/                 # pytest test suite
```

Generated output is written to `~/.local/share/agent-board/` by default (XDG-compliant, override with `--output`).

## Running tests

```bash
.venv/bin/python -m pytest tests/ -v
```
