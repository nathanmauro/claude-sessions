# agentseq — session handoff

This repo was originally consolidated from two now-superseded repos:
- `nathanmauro/claude-session-menu` (the rumps menubar app)
- `nathanmauro/claude-dash` (the FastAPI + React dashboard)

Both histories are preserved here via `git subtree`. The public repo is live at
https://github.com/nathanmauro/claude-sessions (the GitHub slug is unchanged
even though the project/package was renamed to `agentseq`).

## State as of 2026-05-27

- Repo published to GitHub as `nathanmauro/claude-sessions` (slug unchanged).
- Project renamed from `claude-sessions` → `agent-sessions` → `agentseq`.
  The legacy `agent-sessions` and `claude-sessions` CLI commands stay installed
  as deprecated aliases.
- Layout: `agentseq/{core,cli,tui,menu,dash}/` + `web/` (Vite/React frontend).
- Single primary CLI entrypoint `agentseq` with subcommands: `ls`,
  `running`, `open`, `focus`, `smart`, `tui`, `menu`, `dash`, `index`.
- Packaging: PEP 621 extras — `[tui]` adds textual, `[menu]` adds rumps,
  `[dash]` adds FastAPI stack, `[all]` is everything, `[dev]` adds pytest/ruff.
- De-personalized: hardcoded Notion DB UUID and Mac-specific auggie path
  replaced with `AGENTSEQ_NOTION_DB_ID` / `AGENTSEQ_AUGGIE` env vars.
  The legacy `AGENT_SESSIONS_*` and `CLAUDE_SESSIONS_*` names still work
  as fallbacks.
- Cache dir renames: `~/.claude-dash` → `~/.claude-sessions` → `~/.agent-sessions` → `~/.agentseq`
  (auto-migrated on first run from older locations).
- Textual TUI added (v0.7.0): live agent monitoring, session browser with FTS,
  detail screen with transcript + tasks, combine workspace for multi-session ops.

## Prior session transcript

Full conversation log: `/Users/nathan/.claude/projects/-Users-nathan-Developer-proj-claude-session-menu/f4aa1e39-836b-4a18-a14b-cdbcd3f43a5f.jsonl`

## Project-specific notes for future Claude sessions

- `core/` has zero third-party deps — keep it that way. `tui/` may import textual; `menu/` may import rumps; `dash/` may import fastapi/httpx/etc. `core/` must not import any of them.
- `core/parser.py` is the deep parser (writes SQLite rows with token counts + task counts); `core/sessions.py` is the DB-first reader with JSONL fallback. They both exist intentionally — don't try to collapse them.
- The web build (`web/dist/`) is gitignored. The dash server returns a helpful 503 if it's missing, telling the user to run `npm install && npm run build` in `web/`.
- Frontend dev: `cd web && npm run dev` (Vite on :5173) against a running `agentseq dash` (FastAPI on :8765).
