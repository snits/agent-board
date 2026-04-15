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


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
