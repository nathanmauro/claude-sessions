# agent-sessions for zellij

One-keystroke session picker for [zellij](https://zellij.dev/). Press `Alt + p`
to open an fzf picker in a transient pane; choose a session and `smart`
resumes it (focus the existing zellij pane if it's running, else open a new
one).

## Install

Paste this into `~/.config/zellij/config.kdl` (or merge into your existing
`keybinds` block):

```kdl
keybinds {
  shared_except "locked" {
    bind "Alt p" {
      Run "agent-sessions" "pick" "--exec" "smart" {
        close_on_exit true
      }
    }
  }
}
```

Reload with `Ctrl + Shift + L` (zellij's "Detach and reload" — picks up
config changes without restarting your session).

## Requirements

- `agent-sessions` on `$PATH` — `pipx install agent-sessions` or
  `uv tool install agent-sessions`
- `fzf` on `$PATH` — `brew install fzf`

`Run` opens the command directly in a transient pane (no shell wrapper
needed) and `close_on_exit true` makes the pane vanish after the resume
completes. The chosen session opens as a new zellij pane in the same
session because the picker's resume path detects `$ZELLIJ` and routes
through `core.launcher.ZellijLauncher`.

## Rebinding

`Alt + p` collides with nothing in zellij's default keymap, but if you
prefer a different chord, swap `"Alt p"` for any other zellij key spec
(`"Ctrl o"`, `"Alt s"`, etc.). See
[zellij keybindings docs](https://zellij.dev/documentation/keybindings.html).
