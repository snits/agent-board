# Agent Board

## PROJECT SCALE CONTEXT

- **Users:** Single developer (Jerry), personal tool
- **Type:** Local web viewer for Claude Code transcripts
- **Codebase:** Small (~1500 lines Python + ~1300 lines HTML/CSS/JS)
- **Complexity:** Simple — no build tools, no frameworks, no database
- **Process:** Pragmatic — no CI/CD, no formal review process
- **Default approach:** Keep it simple, ship fast, fix issues as found in browser

## Architecture

- **Backend:** Python preprocessor (scanner → parser → grouper → writer) with no dependencies beyond stdlib
- **Frontend:** Vanilla HTML/CSS/JS, CDN dependencies (marked.js, DOMPurify)
- **Serving:** Python stdlib HTTP server, serves from project root
- **Data:** Preprocessed JSON files in `~/.local/share/agent-board/` (XDG-compliant, overridable via `$XDG_DATA_HOME` or `--output`)

## Conventions

- All Python/JS files start with 2-line `ABOUTME:` comments
- Tests use pytest with no external dependencies
- Agent counts use unique types, not instance IDs
- Broadcast messages are deduplicated by UUID across agent JSONL files
- Empty tool-result plumbing messages are filtered from rendering
