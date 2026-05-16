"""Open new Ghostty windows or focus existing Ghostty/Terminal sessions."""
from __future__ import annotations

import datetime as dt
import os
import shlex
import subprocess
from pathlib import Path

GHOSTTY_APP = "/Applications/Ghostty.app"
LOG_PATH = Path.home() / "Library" / "Logs" / "claude-sessions.log"


def log_failure(context: str, msg: str) -> None:
    """Append a failure line to ~/Library/Logs/claude-sessions.log. Swallows
    OSError so a logging failure can't crash the menu."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"{dt.datetime.now().isoformat()}\t{context}\t{msg}\n")
    except OSError:
        pass


def _resolve_claude_bin() -> str:
    """Return absolute path to the claude binary. Search CLAUDE_BIN env first, then
    common install locations, then a login-shell PATH lookup."""
    env_bin = os.environ.get("CLAUDE_BIN")
    if env_bin and Path(env_bin).exists():
        return env_bin
    candidates = [
        Path.home() / ".claude" / "local" / "claude",
        Path("/opt/homebrew/bin/claude"),
        Path("/usr/local/bin/claude"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    # Fall back to a login shell PATH lookup
    try:
        out = subprocess.run(
            ["/bin/zsh", "-lc", "command -v claude"],
            capture_output=True,
            text=True,
            check=True,
        )
        path = out.stdout.strip()
        if path:
            return path
    except subprocess.CalledProcessError:
        pass
    return "claude"


CLAUDE_BIN = None  # lazy


def claude_bin() -> str:
    global CLAUDE_BIN
    if CLAUDE_BIN is None:
        CLAUDE_BIN = _resolve_claude_bin()
    return CLAUDE_BIN


def _ghostty_open_window(cwd: str, command: str) -> tuple[bool, str]:
    """Open a new Ghostty window running `command` with working dir `cwd`.

    Uses `open -na Ghostty.app --args -e <shell> -lc '<cmd>'` so the shell
    inherits the login environment (PATH for `claude`, etc.) and stays open
    after the command exits via `exec $SHELL`.
    """
    inner = f"cd {shlex.quote(cwd)} && exec {command}"
    # `-e` makes Ghostty run the argv that follows as a single command. We
    # invoke a login shell so PATH resolves and so the user sees a normal
    # prompt if claude exits.
    args = [
        "open",
        "-na",
        GHOSTTY_APP,
        "--args",
        "-e",
        "/bin/zsh",
        "-lc",
        inner,
    ]
    try:
        subprocess.run(args, check=True, capture_output=True)
        return True, "opened"
    except subprocess.CalledProcessError as e:
        return False, e.stderr.decode("utf-8", errors="replace") or str(e)


def open_new(cwd: str, session_id: str | None = None, extra: str = "") -> tuple[bool, str]:
    if not Path(cwd).exists():
        return False, f"cwd does not exist: {cwd}"
    bin_ = claude_bin()
    parts = [shlex.quote(bin_)]
    if session_id:
        parts.append(f"--resume {shlex.quote(session_id)}")
    if extra.strip():
        parts.append(shlex.quote(extra.strip()))
    return _ghostty_open_window(cwd, " ".join(parts))


def focus_app(app_name: str) -> tuple[bool, str]:
    """Bring the terminal app frontmost. Tab-level focus is not yet supported."""
    script = f'tell application "{app_name}" to activate'
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        return True, f"activated {app_name}"
    except subprocess.CalledProcessError as e:
        return False, e.stderr.decode("utf-8", errors="replace") or str(e)


def focus_pid(pid: int) -> tuple[bool, str]:
    """Activate the process with the given unix pid (i.e., its owning .app)."""
    script = (
        'tell application "System Events" to '
        f"set frontmost of (first process whose unix id is {pid}) to true"
    )
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        return True, f"focused pid {pid}"
    except subprocess.CalledProcessError as e:
        return False, e.stderr.decode("utf-8", errors="replace") or str(e)
