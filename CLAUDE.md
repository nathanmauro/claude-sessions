# agent-sessions — session handoff

This repo was originally consolidated from two now-superseded repos:
- `nathanmauro/claude-session-menu` (the rumps menubar app)
- `nathanmauro/claude-dash` (the FastAPI + React dashboard)

Both histories are preserved here via `git subtree`. The public repo is live at
https://github.com/nathanmauro/claude-sessions (the GitHub slug is unchanged
even though the project/package was renamed to `agent-sessions`).

## State as of 2026-05-23

- Repo published to GitHub as `nathanmauro/claude-sessions` (slug unchanged).
- Project renamed from `claude-sessions` to `agent-sessions`. The legacy
  `claude-sessions` CLI command stays installed as a deprecated alias.
- Layout: `agent_sessions/{core,cli,menu,dash}/` + `web/` (Vite/React frontend).
- Single primary CLI entrypoint `agent-sessions` with subcommands: `ls`,
  `running`, `open`, `focus`, `smart`, `menu`, `dash`, `index`. `claude-sessions`
  is kept as a backward-compatible alias.
- Packaging: PEP 621 extras — `[menu]` adds rumps, `[dash]` adds FastAPI stack,
  `[all]` is both, `[dev]` adds pytest/ruff.
- De-personalized: hardcoded Notion DB UUID and Mac-specific auggie path
  replaced with `AGENT_SESSIONS_NOTION_DB_ID` / `AGENT_SESSIONS_AUGGIE` env
  vars. The legacy `CLAUDE_SESSIONS_NOTION_DB_ID` / `CLAUDE_SESSIONS_AUGGIE`
  names still work as a fallback.
- Cache dir renames: `~/.claude-dash` → `~/.claude-sessions` → `~/.agent-sessions`
  (auto-migrated on first run from either older location).

## Deferred (per user choice "Push public, but don't archive yet")

1. **Polish**: screenshots of the menubar + dashboard into `docs/screenshots/`, slot into README hero.

## Prior session transcript

Full conversation log: `/Users/nathan/.claude/projects/-Users-nathan-Developer-proj-claude-session-menu/f4aa1e39-836b-4a18-a14b-cdbcd3f43a5f.jsonl`

## Project-specific notes for future Claude sessions

- `core/` has zero third-party deps — keep it that way. `menu/` may import rumps; `dash/` may import fastapi/httpx/etc. `core/` must not import either.
- `core/parser.py` is the deep parser (writes SQLite rows with token counts + task counts); `core/sessions.py` is the DB-first reader with JSONL fallback. They both exist intentionally — don't try to collapse them.
- The web build (`web/dist/`) is gitignored. The dash server returns a helpful 503 if it's missing, telling the user to run `npm install && npm run build` in `web/`.
- Frontend dev: `cd web && npm run dev` (Vite on :5173) against a running `agent-sessions dash` (FastAPI on :8765).
