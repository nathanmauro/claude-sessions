# agent-sessions — plan / next session handoff

Snapshot for resuming work in a fresh Claude Code session. Pair with the
project-level [`CLAUDE.md`](CLAUDE.md) (consolidation history + per-package
rules) and [`README.md`](README.md) (user-facing docs).

**Repo:** https://github.com/nathanmauro/claude-sessions  
**Branch:** `main`  
**Version:** 0.5.0  
**Tests:** 39 passing (`uv run pytest`)  
**Last touched:** 2026-05-18

---

## What's shipped

| Phase | What | PR |
| --- | --- | --- |
| 1 | Launcher refactor — `core/launcher/` package with 4 backends (Ghostty, tmux, zellij, generic) + `autodetect()` / `gui_window()` factories. CLI gains `--launcher` flag + `CLAUDE_SESSIONS_LAUNCHER` env var. Unifies menu+dash launchers (was inconsistent: menu→Ghostty, dash→Terminal.app). | [#1](https://github.com/nathanmauro/claude-sessions/pull/1) — `12c575b` |
| 2 | `claude-sessions show <sid>` (full / `--short` / `--json`) and `claude-sessions pick` (fzf-driven picker with `--exec smart\|open` chaining). | [#2](https://github.com/nathanmauro/claude-sessions/pull/2) — `93ce6a2` |

---

## Locked-in design decisions

Don't relitigate these in a new session unless something has actually changed:

- **Two launcher factories, not one.** `autodetect()` is for the CLI (honors `$ZELLIJ` → `$TMUX` → Ghostty.app, so "open" lands as a pane in the calling shell's multiplexer). `gui_window()` is for the menu and dash (always picks a GUI terminal — they're not running in the user's interactive shell).
- **`core/launcher/` has zero third-party deps.** Same rule as the rest of `core/`. Keep it that way.
- **`(ok: bool, msg: str)` tuples** are the return contract for all launcher methods. Avoid swapping to a dataclass — too much caller churn for no payoff.
- **`tuple[bool, str]` over exceptions** for launcher failures. Launchers never raise; they return `(False, <human message>)`.
- **`pick` requires fzf as a hard dep**, with an install hint on failure. Don't reimplement fzf in Python.
- **Dashboard stays.** Per user 2026-05-18: they want a web surface so they can search from a separate place from their terminal. Scope-tight it to the "search from elsewhere" story.
- **Rebase-merge, not squash.** Keeps `main` linear and preserves the prose commit message I write.
- **No Claude attribution on commits/PRs.** Per `~/.claude/CLAUDE.md` global rule. Always Nathan as sole author.
- **`menu/launcher.py` is gone.** All launcher code lives in `core/launcher/`. The `processes.py` (terminal-app discovery) still lives in `menu/` and is fine there.
- **Tmux focus is best-effort.** `TmuxLauncher.focus_pid()` searches `tmux list-panes -a` for a matching `pane_pid`. Works when the caller passed a shell pid; doesn't yet walk up from a claude pid through tmux. Deferred to a later improvement to `processes.py`.

---

## Next: Phase 3 — tmux + zellij plugin scripts

**Goal:** ship keybinding-driven plugins that wrap `claude-sessions pick --exec smart`. No new launcher code needed — Phase 1 + 2 already give us the API.

### Files to add

```
share/
  tmux/
    claude-sessions.tmux      # TPM-installable plugin (bash script)
  zellij/
    README.md                 # documented keybinding snippet (KDL)
    launch.sh                 # optional wrapper for the bind to call
```

### Tmux plugin design

- Single bash script registered with TPM via `set -g @plugin 'nathanmauro/claude-sessions'`.
- Reads optional tmux option `@claude_sessions_key` (default: `C` — i.e. `prefix + C`).
- Binds the key to: `display-popup -E -w 90% -h 80% 'claude-sessions pick --exec smart'`.
- README section showing how to install via TPM.

### Zellij approach

- Zellij plugins are WASM (Rust). Overkill for v1.
- Instead: ship a shell wrapper + a docs snippet telling users to add to `~/.config/zellij/config.kdl`:
  ```kdl
  keybinds {
    shared_except "locked" {
      bind "Alt p" { Run "claude-sessions" "pick" "--exec" "smart" {
        close_on_exit true
      }}
    }
  }
  ```
- README section in `share/zellij/README.md`.

### Acceptance

- [ ] tmux plugin file exists + documented in README install section
- [ ] zellij keybinding snippet in `share/zellij/README.md`
- [ ] Manual test: from inside tmux, `prefix + C` pops up fzf picker, enter resumes
- [ ] Manual test: from inside zellij, `Alt+p` does the same
- [ ] Top-level README has a "Multiplexer integration" section

No new Python code; therefore no new Python tests. Add a `tests/test_tmux_plugin.sh` if we want to lint the shell script with shellcheck, optional.

---

## Phase 4 — dash polish (smaller, parallelizable)

User explicitly wants the dashboard kept for "search from a separate place from terminal." Tighten it to that story.

- [ ] Make the global search box more prominent on first load (it's currently a per-day list with search hidden behind a click — verify by running `agent-sessions dash` and looking).
- [ ] README section: "Searching from elsewhere" with `agent-sessions dash --host 0.0.0.0` instructions + a warning that this exposes the API to the LAN.
- [ ] **Don't add auth** in this phase. If the user wants auth-protected dashboard access from anywhere, that's a separate, larger conversation (reverse-proxy + Tailscale serve, or a token-based middleware).
- [ ] Confirm the dash still works after the Phase 1 launcher refactor: `start_session` / `resume_session` now route through `core.launcher.gui_window()`. Manual smoke: click "Resume" on a session card.

Front-end source lives in `web/`; build with `npm run build`. The Python server returns a 503 if `web/dist/` is missing.

---

## Deferred (Phase 5+) — don't start without asking

These came up in planning and are explicitly out of scope until the user picks them up:

- **Textual TUI** as a dash-replacement candidate. User chose to keep the React dash, so deprioritize.
- **`agent-sessions search "<query>"`** — CLI exposure of the dash's FTS5 search. Nice but not urgent.
- **Tags / favorites** on sessions.
- **Notion sync of sessions** — push session metadata into Notion for cross-tool searchability.
- **Auto-archive / cleanup** of old session JSONL.
- **WASM zellij plugin** — only if a user actually asks for it.
- **`processes.py` tmux/zellij awareness** so `TmuxLauncher.focus_pid` can reliably find the pane owning a given claude pid (current implementation only works when caller passes a shell pid).

---

## Architecture cheat-sheet

```
claude_sessions/
  core/                    # zero third-party deps
    launcher/              # Phase 1 — pluggable backends
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
    main.py                # ls/running/show/pick/open/focus/smart/menu/dash/index
  menu/                    # macOS rumps app (requires [menu] extra)
    app.py
    processes.py           # detect running `claude --resume` + walk to terminal
  dash/                    # FastAPI server (requires [dash] extra)
    server.py
    launcher_extras.py     # thin wrappers around core.launcher.gui_window()
                           # + dash-only utilities (open_finder, open_editor, augment, github_url)
    notion.py
    subscription.py
web/                       # Vite + React + TanStack Query frontend; build to web/dist/
tests/                     # pytest; mocks subprocess for all launcher tests
  test_launcher.py         # 27 tests
  test_cli.py              # 12 tests
share/                     # ← add Phase 3 plugin files here
```

**Layering rule:** `core/` cannot import `menu/` or `dash/`. `menu/` can import `core/`. `dash/` can import `core/`. `cli/` imports anything but lazy-loads `menu/`/`dash/` so the bare-CLI install (`pip install claude-sessions`) works without rumps/fastapi.

---

## Validation commands

```bash
uv run pytest                              # all 39 tests
uv run ruff check claude_sessions tests    # lint (11 preexisting issues in unrelated files — ignore unless touching them)
uv run claude-sessions ls                  # smoke
uv run claude-sessions show <sid>          # smoke
uv run claude-sessions pick                # interactive — needs TTY
```

**Known ruff debt** (preexisting, not from any recent PR — fix only when touching the affected file):
- `claude_sessions/core/db.py` — unused `datetime` imports, `typing.Iterable/Iterator` → `collections.abc`
- `claude_sessions/core/models.py` — unused quoted-annotation
- `claude_sessions/core/sessions.py` — import sort, `typing.Iterator`, `dt.timezone.utc` → `dt.UTC`
- `claude_sessions/dash/server.py` — `asyncio.TimeoutError` → builtin `TimeoutError`, import sort
- `claude_sessions/menu/processes.py` — import sort

---

## Workflow conventions

- One PR per phase. Rebase-merge with `--delete-branch`.
- Commit message format: imperative title + 1-3 paragraph body. No `Co-Authored-By: Claude` ever (per global CLAUDE.md).
- Bump version per change: minor for additive features, patch for fixes, major if breaking.
- TaskCreate tasks during multi-step phases; mark complete as you go.
- Leave preexisting untracked files alone (`uv.lock`, `CLAUDE.md`) unless the user asks to commit them.

---

## Open questions / things to confirm with the user

- **Publish to PyPI?** Currently `0.5.0` exists only as a git tag. No release workflow. If publishing is desired, add `gh release` + `uv build` + `uv publish` to the validation step.
- **CI?** No `.github/workflows/`. A simple test+lint workflow would be cheap insurance.
- **Dashboard auth for LAN exposure** — only if the user actually wants to access the dash from off-host.
