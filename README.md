# agent-sessions

Browse, resume, and visualize your [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) sessions from three surfaces — terminal CLI, macOS menubar, and a local web dashboard — all backed by a shared SQLite index of `~/.claude/projects/*.jsonl`.

<p align="center">
  <img src="docs/screenshots/dashboard.png" alt="Dashboard — browse sessions, tasks, and token usage" width="820"><br>
  <em>Dashboard: browse sessions, tasks, and token usage in your browser.</em>
</p>

<table>
  <tr>
    <td width="50%" valign="top">
      <img src="docs/screenshots/menubar.png" alt="Menubar dropdown — running and recent sessions grouped by project" width="100%"><br>
      <em>Menubar: live count of running sessions, recents grouped by project.</em>
    </td>
    <td width="50%" valign="top">
      <img src="docs/screenshots/cli.png" alt="CLI — agent-sessions ls" width="100%"><br>
      <em>CLI: <code>agent-sessions ls</code> for scripting and quick lookup.</em>
    </td>
  </tr>
</table>


> **Status:** alpha (0.3.0). Mac-first. Linux/Windows untested for the menubar surface; CLI + dash should work cross-platform once a non-Ghostty launcher path is added.

## Migrating from `claude-sessions`

This project was renamed from `claude-sessions` to `agent-sessions`. Existing setups keep working:

- The legacy `claude-sessions` CLI command is still installed as a deprecated alias.
- Legacy `CLAUDE_SESSIONS_*` environment variables are still honored when the new `AGENT_SESSIONS_*` equivalents are not set.
- The cache dir is auto-migrated from `~/.claude-sessions/` to `~/.agent-sessions/` on first run.

New users and new docs should prefer `agent-sessions` and `AGENT_SESSIONS_*`.

## Why

Claude Code already records every session as JSONL under `~/.claude/projects/`, but the built-in `claude --resume` picker only shows the current directory and doesn't surface running processes or token usage. `agent-sessions` indexes that data once and serves it from whichever interface fits the moment:

| Surface | Best for | Command |
| --- | --- | --- |
| **CLI** | scripting, fzf piping, quick lookup | `agent-sessions ls`, `... open <sid>`, `... smart <sid>` |
| **Menubar** | always-on glance + one-click resume | `agent-sessions menu` |
| **Dash** | reviewing a day's work, search, token usage | `agent-sessions dash` |

## Install

```bash
# CLI only (no GUI deps)
pip install agent-sessions

# CLI + macOS menubar
pip install 'agent-sessions[menu]'

# CLI + web dashboard (FastAPI + React)
pip install 'agent-sessions[dash]'

# Everything
pip install 'agent-sessions[all]'
```

Or from source with [`uv`](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/nathanmauro/claude-sessions
cd claude-sessions
uv sync --all-extras
uv run agent-sessions ls
```

## Quick start

```bash
# Build a SQLite index of every session under ~/.claude/projects/
agent-sessions index

# List the 50 most-recent sessions
agent-sessions ls

# Smart-resume: focus the terminal if it's already running, else open a new Ghostty window
agent-sessions smart <session-id-prefix>

# Launch the macOS menubar (requires [menu] extra)
agent-sessions menu

# Launch the local dashboard at http://127.0.0.1:8765 (requires [dash] extra)
cd web && npm install && npm run build && cd ..
agent-sessions dash
```

## Surfaces

### CLI

```
agent-sessions ls                        # table of sessions, newest first
agent-sessions ls --json --limit 200     # machine-readable
agent-sessions running                   # active claude --resume processes
agent-sessions show <sid>                # session metadata (--short / --json)
agent-sessions pick                      # interactive fzf picker; prints chosen sid
agent-sessions open <sid> [--prompt X]   # open new terminal window/pane in the recorded cwd
agent-sessions focus <sid>               # bring the terminal running this session to front
agent-sessions smart <sid>               # focus if running, else open new
agent-sessions index                     # refresh the SQLite index
```

Session IDs accept unique prefixes. `pick` requires `fzf` on PATH (`brew install fzf`) and chains directly into a resume with `--exec smart`:

```bash
# Print the chosen sid:
agent-sessions pick

# Pick + smart-resume in one shot:
agent-sessions pick --exec smart
```

`open`, `focus`, `smart`, and `pick` all accept `--launcher {ghostty,tmux,zellij,generic}` (or set `AGENT_SESSIONS_LAUNCHER`) to override autodetection. Default behavior:

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
- Optional Notion todo overlay (set `NOTION_TOKEN` + `AGENT_SESSIONS_NOTION_DB_ID`)
- Open-finder / open-editor / start-new-session actions per project

The frontend lives in `web/`; build it once with `npm run build` before launching, or run `npm run dev` against a separate `agent-sessions dash` process during frontend development.

## Multiplexer integration

One-key picker from inside your terminal multiplexer.

### tmux (via TPM)

Add to `~/.tmux.conf`:

```tmux
set -g @plugin 'nathanmauro/claude-sessions'
set -g @agent_sessions_key 'C'   # optional; default is C
```

Then `prefix + I` to install. `prefix + C` opens an fzf popup — pick a session,
hit enter, and `smart` resumes it in a new tmux pane (or focuses the existing
one).

### zellij

Paste the snippet from [share/zellij/README.md](share/zellij/README.md) into
`~/.config/zellij/config.kdl` and reload (`Ctrl + Shift + L`). `Alt + p` opens
the picker in a transient pane.

Both bindings shell out to `agent-sessions pick --exec smart`, so
`agent-sessions` must be on `$PATH` (`pipx install agent-sessions` or
`uv tool install agent-sessions`).

## Configuration

All config is environment variables, with sensible defaults:

| Variable | Default | Purpose |
| --- | --- | --- |
| `CLAUDE_PROJECTS_DIR` | `~/.claude/projects` | Where to read session JSONL from |
| `AGENT_SESSIONS_CACHE` | `~/.agent-sessions` | Cache dir for the SQLite index + caches |
| `AGENT_SESSIONS_HOST` | `127.0.0.1` | Dashboard bind host |
| `AGENT_SESSIONS_PORT` | `8765` | Dashboard port |
| `AGENT_SESSIONS_INDEX_INTERVAL` | `60` | Background indexer interval (seconds) |
| `CLAUDE_BIN` | auto-detect | Path to the `claude` binary used by `open` |
| `NOTION_TOKEN` | — | Optional; enables the Notion todos overlay |
| `AGENT_SESSIONS_NOTION_DB_ID` | — | Notion database ID to query (required for overlay) |
| `AGENT_SESSIONS_AUGGIE` | — | Path to the `auggie` binary if you use Augment |

The legacy `CLAUDE_SESSIONS_*` names are still read as a fallback when the
`AGENT_SESSIONS_*` equivalent is unset (see "Migrating from `claude-sessions`"
above).

## Development

```bash
uv sync --all-extras --extra dev
uv run pytest             # tests
uv run ruff check         # lint
cd web && npm install && npm run dev   # frontend dev server on :5173
```

The codebase is split into four packages under `agent_sessions/`:

```
core/    parser, SQLite indexer, models, event bus, config
cli/     argparse dispatcher
menu/    rumps app, Ghostty launcher, process detection
dash/    FastAPI server, Notion sync, subscription usage
web/     Vite + React + TanStack Query frontend
```

`core/` has zero third-party dependencies. `menu/` adds `rumps`. `dash/` adds `fastapi`, `uvicorn`, `pydantic`, `httpx`.

## History

This repo is a consolidation of two related projects:

- [`nathanmauro/claude-session-menu`](https://github.com/nathanmauro/claude-session-menu) — the menubar app
- [`nathanmauro/claude-dash`](https://github.com/nathanmauro/claude-dash) — the web dashboard

Their commit histories are preserved here. The standalone `claude-dash` repo
remains usable directly for the dashboard while this repo provides the unified
CLI, menu bar, and dashboard package.

## License

[MIT](LICENSE)
