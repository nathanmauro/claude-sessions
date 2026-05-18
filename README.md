# claude-sessions

Browse, resume, and visualize your [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) sessions from three surfaces — terminal CLI, macOS menubar, and a local web dashboard — all backed by a shared SQLite index of `~/.claude/projects/*.jsonl`.

> **Status:** alpha (0.3.0). Mac-first. Linux/Windows untested for the menubar surface; CLI + dash should work cross-platform once a non-Ghostty launcher path is added.

## Why

Claude Code already records every session as JSONL under `~/.claude/projects/`, but the built-in `claude --resume` picker only shows the current directory and doesn't surface running processes or token usage. `claude-sessions` indexes that data once and serves it from whichever interface fits the moment:

| Surface | Best for | Command |
| --- | --- | --- |
| **CLI** | scripting, fzf piping, quick lookup | `claude-sessions ls`, `... open <sid>`, `... smart <sid>` |
| **Menubar** | always-on glance + one-click resume | `claude-sessions menu` |
| **Dash** | reviewing a day's work, search, token usage | `claude-sessions dash` |

## Install

```bash
# CLI only (no GUI deps)
pip install claude-sessions

# CLI + macOS menubar
pip install 'claude-sessions[menu]'

# CLI + web dashboard (FastAPI + React)
pip install 'claude-sessions[dash]'

# Everything
pip install 'claude-sessions[all]'
```

Or from source with [`uv`](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/nathanmauro/claude-sessions
cd claude-sessions
uv sync --all-extras
uv run claude-sessions ls
```

## Quick start

```bash
# Build a SQLite index of every session under ~/.claude/projects/
claude-sessions index

# List the 50 most-recent sessions
claude-sessions ls

# Smart-resume: focus the terminal if it's already running, else open a new Ghostty window
claude-sessions smart <session-id-prefix>

# Launch the macOS menubar (requires [menu] extra)
claude-sessions menu

# Launch the local dashboard at http://127.0.0.1:8765 (requires [dash] extra)
cd web && npm install && npm run build && cd ..
claude-sessions dash
```

## Surfaces

### CLI

```
claude-sessions ls                        # table of sessions, newest first
claude-sessions ls --json --limit 200     # machine-readable
claude-sessions running                   # active claude --resume processes
claude-sessions show <sid>                # session metadata (--short / --json)
claude-sessions pick                      # interactive fzf picker; prints chosen sid
claude-sessions open <sid> [--prompt X]   # open new terminal window/pane in the recorded cwd
claude-sessions focus <sid>               # bring the terminal running this session to front
claude-sessions smart <sid>               # focus if running, else open new
claude-sessions index                     # refresh the SQLite index
```

Session IDs accept unique prefixes. `pick` requires `fzf` on PATH (`brew install fzf`) and chains directly into a resume with `--exec smart`:

```bash
# Print the chosen sid:
claude-sessions pick

# Pick + smart-resume in one shot:
claude-sessions pick --exec smart
```

`open`, `focus`, `smart`, and `pick` all accept `--launcher {ghostty,tmux,zellij,generic}` (or set `CLAUDE_SESSIONS_LAUNCHER`) to override autodetection. Default behavior:

- inside zellij → new pane in the current zellij session
- inside tmux → new window in the current tmux session
- otherwise on macOS → new Ghostty window
- otherwise → fail loud with an install hint

### Menubar

A [rumps](https://github.com/jaredks/rumps) app that lives in your macOS menu bar. The title shows `CC<n>` where `<n>` is the count of running `claude --resume` processes. The menu groups items by *Running* and *Recent*, with recent sessions bucketed by project. Click any item to focus its terminal if alive, or open a fresh Ghostty window in the recorded cwd otherwise.

### Web dashboard

A React SPA served by FastAPI with SSE for live index updates. Routes:

- Per-day session list with token usage, task counts, and prompt previews
- Global search across session content (SQLite FTS5)
- Optional Notion todo overlay (set `NOTION_TOKEN` + `CLAUDE_SESSIONS_NOTION_DB_ID`)
- Open-finder / open-editor / start-new-session actions per project

The frontend lives in `web/`; build it once with `npm run build` before launching, or run `npm run dev` against a separate `claude-sessions dash` process during frontend development.

## Configuration

All config is environment variables, with sensible defaults:

| Variable | Default | Purpose |
| --- | --- | --- |
| `CLAUDE_PROJECTS_DIR` | `~/.claude/projects` | Where to read session JSONL from |
| `CLAUDE_SESSIONS_CACHE` | `~/.claude-sessions` | Cache dir for the SQLite index + caches |
| `CLAUDE_SESSIONS_HOST` | `127.0.0.1` | Dashboard bind host |
| `CLAUDE_SESSIONS_PORT` | `8765` | Dashboard port |
| `CLAUDE_SESSIONS_INDEX_INTERVAL` | `60` | Background indexer interval (seconds) |
| `CLAUDE_BIN` | auto-detect | Path to the `claude` binary used by `open` |
| `NOTION_TOKEN` | — | Optional; enables the Notion todos overlay |
| `CLAUDE_SESSIONS_NOTION_DB_ID` | — | Notion database ID to query (required for overlay) |
| `CLAUDE_SESSIONS_AUGGIE` | — | Path to the `auggie` binary if you use Augment |

## Development

```bash
uv sync --all-extras --extra dev
uv run pytest             # tests
uv run ruff check         # lint
cd web && npm install && npm run dev   # frontend dev server on :5173
```

The codebase is split into four packages under `claude_sessions/`:

```
core/    parser, SQLite indexer, models, event bus, config
cli/     argparse dispatcher
menu/    rumps app, Ghostty launcher, process detection
dash/    FastAPI server, Notion sync, subscription usage
web/     Vite + React + TanStack Query frontend
```

`core/` has zero third-party dependencies. `menu/` adds `rumps`. `dash/` adds `fastapi`, `uvicorn`, `pydantic`, `httpx`.

## History

This repo is a consolidation of two earlier projects:

- [`nathanmauro/claude-session-menu`](https://github.com/nathanmauro/claude-session-menu) — the menubar app
- [`nathanmauro/claude-dash`](https://github.com/nathanmauro/claude-dash) — the web dashboard

Both have been archived in favor of this unified repo. Their commit histories are preserved here.

## License

[MIT](LICENSE)
