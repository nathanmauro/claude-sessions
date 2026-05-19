# claude-sessions — session handoff

This repo was just consolidated from two now-superseded repos:
- `nathanmauro/claude-session-menu` (the rumps menubar app)
- `nathanmauro/claude-dash` (the FastAPI + React dashboard)

Both histories are preserved here via `git subtree`. The new public repo is live at https://github.com/nathanmauro/claude-sessions.

## State as of 2026-05-18

- Repo pushed public to GitHub as `nathanmauro/claude-sessions`.
- Layout: `claude_sessions/{core,cli,menu,dash}/` + `web/` (Vite/React frontend).
- Single CLI entrypoint `claude-sessions` with subcommands: `ls`, `running`, `open`, `focus`, `smart`, `menu`, `dash`, `index`.
- Packaging: PEP 621 extras — `[menu]` adds rumps, `[dash]` adds FastAPI stack, `[all]` is both, `[dev]` adds pytest/ruff.
- De-personalized: hardcoded Notion DB UUID and Mac-specific auggie path replaced with `CLAUDE_SESSIONS_NOTION_DB_ID` and `CLAUDE_SESSIONS_AUGGIE` env vars.
- Cache dir renamed `~/.claude-dash` → `~/.claude-sessions`.

## Deferred (per user choice "Push public, but don't archive yet")

1. **Archive the two source repos** when user is ready:
   - Append "Moved to nathanmauro/claude-sessions" to each README first.
   - Then `gh repo archive nathanmauro/claude-session-menu` and `gh repo archive nathanmauro/claude-dash`.
2. **Fast-forward `claude-dash` main** — the playwright e2e commit landed on `add-playwright-e2e` branch. User chose "Merge to main first (no PR) then archive". Harness blocked the push from this session; user runs manually:
   ```bash
   git -C ~/Developer/proj/claude-dash checkout main \
     && git merge --ff-only add-playwright-e2e \
     && git push origin main
   ```
3. **Polish**: screenshots of the menubar + dashboard into `docs/screenshots/`, slot into README hero.

## Prior session transcript

Full conversation log: `/Users/nathan/.claude/projects/-Users-nathan-Developer-proj-claude-session-menu/f4aa1e39-836b-4a18-a14b-cdbcd3f43a5f.jsonl`

## Project-specific notes for future Claude sessions

- `core/` has zero third-party deps — keep it that way. `menu/` may import rumps; `dash/` may import fastapi/httpx/etc. `core/` must not import either.
- `core/parser.py` is the deep parser (writes SQLite rows with token counts + task counts); `core/sessions.py` is the DB-first reader with JSONL fallback. They both exist intentionally — don't try to collapse them.
- The web build (`web/dist/`) is gitignored. The dash server returns a helpful 503 if it's missing, telling the user to run `npm install && npm run build` in `web/`.
- Frontend dev: `cd web && npm run dev` (Vite on :5173) against a running `claude-sessions dash` (FastAPI on :8765).
