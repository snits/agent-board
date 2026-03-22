# Agent Board

A web-based viewer for Claude Code agent team transcripts. Browse multi-agent conversations with a dark ops-center UI — see what your agent teams were doing, how they collaborated, and what tools they used.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Setup

```bash
# Clone and enter the project
git clone <repo-url>
cd agent-board

# Create a virtual environment and install dependencies
uv venv .venv
uv pip install pytest --python .venv/bin/python
```

## Usage

### Quick start

```bash
# Preprocess transcripts and start the server
.venv/bin/python serve.py
```

Then open http://localhost:8080 in your browser.

By default, Agent Board scans `~/.claude/projects/` for agent team sessions.

### CLI options

```
serve.py [--source PATH] [--output PATH] [--port PORT] [--skip-preprocess]

  --source PATH          Claude projects directory (default: ~/.claude/projects/)
  --output PATH          Preprocessed data output directory (default: ./data/)
  --port PORT            HTTP server port (default: 8080)
  --skip-preprocess      Skip preprocessing, serve existing data
```

### Preprocessing only

To regenerate the data without starting the server:

```bash
.venv/bin/python preprocess.py [--source PATH] [--output PATH]
```

## How it works

Agent Board has two parts:

1. **Preprocessor** (`preprocess.py`, `preprocessor/`) — Scans Claude Code's project storage, parses agent JSONL transcripts, groups messages into meetings by `promptId`, deduplicates broadcast messages, and writes per-meeting JSON files.

2. **Frontend** (`frontend/`, `serve.py`) — A vanilla HTML/CSS/JS viewer served by a Python HTTP server. Three-panel layout: sidebar navigation, chat message stream, and agent roster.

### Data flow

```
~/.claude/projects/
  └── {project}/
      └── {session}/
          └── subagents/
              ├── agent-{id}.jsonl      ← raw transcripts
              └── agent-{id}.meta.json  ← agent metadata

        ↓  preprocess.py

data/
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
  ├── tests/                 # pytest test suite
  └── data/                  # Generated output (gitignored)
```

## Running tests

```bash
.venv/bin/python -m pytest tests/ -v
```
