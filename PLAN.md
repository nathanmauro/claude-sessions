# agentseq — plan / next session handoff

Snapshot for resuming work in a fresh Claude Code session. Pair with the
project-level [`CLAUDE.md`](CLAUDE.md) (consolidation history + per-package
rules) and [`README.md`](README.md) (user-facing docs).

**Repo:** https://github.com/nathanmauro/claude-sessions
**Branch:** `main`
**Version:** 0.7.0
**Tests:** 78 passing (`uv run pytest`)
**Lint:** clean (`uv run ruff check agentseq/ tests/`)
**Last touched:** 2026-05-27

---

## What's shipped

| Phase | What | PR |
| --- | --- | --- |
| 1 | Launcher refactor — `core/launcher/` package with 4 backends (Ghostty, tmux, zellij, generic) + `autodetect()` / `gui_window()` factories. | [#1](https://github.com/nathanmauro/claude-sessions/pull/1) |
| 2 | `show` + `pick` CLI commands (fzf-driven picker with `--exec smart\|open` chaining). | [#2](https://github.com/nathanmauro/claude-sessions/pull/2) |
| 3 | tmux TPM plugin (`prefix + C`) + zellij keybinding snippet (`Alt + p`). README "Multiplexer integration" section. | [#3](https://github.com/nathanmauro/claude-sessions/pull/3) |
| — | Rename `claude-sessions` → `agent-sessions` → `agentseq`. Legacy aliases preserved. Cache dir auto-migrated. | [#6](https://github.com/nathanmauro/claude-sessions/pull/6), [#8](https://github.com/nathanmauro/claude-sessions/pull/8) |
| — | Deterministic screenshots (VHS tapes) for dashboard, CLI, and menubar. | `99a80ab` |
| 4 | Textual TUI — live agent monitor, session browser with FTS, detail screen (transcript + tasks), combine workspace, jobs queue placeholder. SVG screenshot, README badges + full TUI docs. All ruff lint debt cleared. v0.7.0. | [#9](https://github.com/nathanmauro/claude-sessions/pull/9) |

---

## Locked-in design decisions

Don't relitigate unless something has actually changed:

- **Two launcher factories, not one.** `autodetect()` is for the CLI (honors `$ZELLIJ` → `$TMUX` → Ghostty.app). `gui_window()` is for the menu and dash (always picks a GUI terminal).
- **`core/` has zero third-party deps.** `tui/` may import textual; `menu/` may import rumps; `dash/` may import fastapi/httpx/etc. `core/` must not import any of them.
- **`(ok: bool, msg: str)` tuples** are the return contract for all launcher methods. No exceptions, no dataclass.
- **`pick` requires fzf as a hard dep**, with an install hint on failure.
- **Dashboard stays** alongside the TUI. Different use cases — dash is for browser-based search from elsewhere; TUI is for terminal-native monitoring.
- **Squash-merge PRs.** Keeps `main` linear with one clean commit per feature.
- **No Claude attribution on commits/PRs.** Per global `~/.claude/CLAUDE.md`. Nathan as sole author.
- **Tmux focus is best-effort.** Searches `tmux list-panes -a` for a matching `pane_pid`. Doesn't yet walk up from a claude pid.

---

## Next up — pick any of these

### TUI: wire up Combine workspace actions

The Combine tab collects multi-selected sessions but the action buttons are placeholders ("coming soon"). Wire up:

- [ ] **Export** (`e`) — concatenate selected session transcripts to a markdown file
- [ ] **Skill draft** (`k`) — extract patterns from selected sessions into a skill skeleton
- [ ] **Handoff summary** (`h`) — generate a context summary from selected sessions

These are the TUI's differentiating feature over the other surfaces.

### TUI: test coverage

No tests exist for the TUI yet. Add:

- [ ] Smoke test: app mounts, all 4 tabs render, agents table accepts data
- [ ] Detail screen: loads a session, shows transcript, toggles raw JSON
- [ ] Search: exercises FTS path and substring fallback

Use Textual's `run_test()` / pilot API — no real terminal needed.

### Dash polish

- [ ] Make global search more prominent on first load (currently buried behind per-day list)
- [ ] Smoke test the dashboard post-rename (`agentseq dash`)
- [ ] README section: "Searching from elsewhere" with `--host 0.0.0.0` + LAN warning
- [ ] No auth in this phase

### CLI search command

- [ ] `agentseq search "<query>"` — CLI exposure of the SQLite FTS5 search
- [ ] Output: session ID, title, snippet, date (tabular + `--json`)

### CI pipeline

- [ ] `.github/workflows/test.yml` — pytest + ruff on push/PR
- [ ] Badge in README

---

## Deferred — don't start without asking

- **PyPI publishing** — no release workflow yet. Add `gh release` + `uv build` + `uv publish` when ready.
- **Tags / favorites** on sessions.
- **Notion sync** — push session metadata into Notion for cross-tool searchability.
- **Auto-archive / cleanup** of old session JSONL.
- **WASM zellij plugin** — only if someone actually asks.
- **`processes.py` tmux/zellij awareness** — walk from claude pid up to owning pane.
- **Dashboard auth** for LAN/Tailscale exposure.

---

## Architecture

```
agentseq/
  core/                    # zero third-party deps
    launcher/              # pluggable backends
      base.py              # Launcher Protocol, claude_bin(), log_failure()
      detect.py            # autodetect() / gui_window() / get_launcher()
      ghostty.py           # macOS via `open -na Ghostty.app`
      tmux.py              # `tmux new-window`, best-effort focus
      zellij.py            # `zellij action new-pane`
      generic.py           # fail-loud with install hint
    sessions.py            # DB-first reader + JSONL fallback
    parser.py              # deep parser, writes SQLite rows
    db.py                  # SQLite index (FTS5 search)
    config.py              # env-var configuration
    indexer.py             # background indexer
    events.py              # SSE event bus
    models.py
  cli/                     # argparse dispatcher; no GUI deps
    main.py                # ls/running/show/pick/open/focus/smart/tui/menu/dash/index
  tui/                     # Textual terminal UI (requires [tui] extra)
    app.py                 # AgentSeqApp — 4-tab TabbedContent
    live.py                # poll `claude agents --json` for live agents
    agentseq.tcss          # stylesheet
    screens/
      agents.py            # live agent monitor (auto-refresh 3s)
      browser.py           # session list + FTS search
      combine.py           # multi-select workspace
      detail.py            # transcript + tasks + raw JSON toggle
      jobs.py              # export/generation queue (placeholder)
  menu/                    # macOS rumps app (requires [menu] extra)
    app.py
    processes.py           # detect running `claude --resume` + walk to terminal
  dash/                    # FastAPI server (requires [dash] extra)
    server.py
    launcher_extras.py     # gui_window() wrappers + dash utilities
    notion.py
    subscription.py
web/                       # Vite + React + TanStack Query frontend
tests/
  test_launcher.py         # 27 tests
  test_cli.py              # 12+ tests
  test_compat.py           # backcompat helpers
  test_parser.py           # JSONL parser
share/
  tmux/claude-sessions.tmux
  zellij/README.md
```

**Layering rule:** `core/` cannot import `tui/`, `menu/`, or `dash/`. `cli/` lazy-loads extras so `pip install agentseq` (bare) works without textual/rumps/fastapi.

---

## Validation commands

```bash
uv run pytest -x -q                    # 78 tests
uv run ruff check agentseq/ tests/     # lint (zero warnings)
uv run agentseq ls                     # smoke
uv run agentseq tui                    # TUI smoke (needs TTY)
uv run agentseq pick                   # fzf picker (needs TTY)
```

---

## Workflow conventions

- One PR per feature. Squash-merge with `--delete-branch`.
- Commit message: imperative title + body. No Claude attribution.
- Bump version: minor for features, patch for fixes.
- **Keep PLAN.md current** — update shipped table + next-up section in every PR that changes scope.
