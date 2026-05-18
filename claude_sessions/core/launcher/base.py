"""Launcher protocol + shared helpers (claude binary resolution, failure log)."""
from __future__ import annotations

import datetime as dt
import os
import subprocess
from pathlib import Path
from typing import Protocol

from ..config import CACHE_DIR

LOG_PATH = CACHE_DIR / "logs" / "launcher.log"


class Launcher(Protocol):
    """Anything that can spawn a claude session and (best-effort) focus it."""

    name: str

    def open_new(
        self, cwd: str, session_id: str | None = None, extra: str = ""
    ) -> tuple[bool, str]:
        """Spawn ``claude [--resume <sid>] [<extra>]`` in ``cwd``. Returns
        ``(ok, message)``. The message is human-readable; ``open_new`` should
        never raise."""
        ...

    def focus_pid(self, pid: int) -> tuple[bool, str]:
        """Bring the terminal/pane that owns ``pid`` to the foreground. Backends
        that can't do this should return ``(False, <reason>)``."""
        ...

    def focus_app(self, app_name: str) -> tuple[bool, str]:
        """Bring the named terminal app to the foreground. Same contract as
        :meth:`focus_pid`."""
        ...


def log_failure(context: str, msg: str) -> None:
    """Append a failure line to the launcher log. Never raises."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"{dt.datetime.now().isoformat()}\t{context}\t{msg}\n")
    except OSError:
        pass


_CLAUDE_BIN: str | None = None


def claude_bin() -> str:
    """Resolve the ``claude`` binary path. Cached after first call. Honors the
    ``CLAUDE_BIN`` env var, then well-known install locations, then a login-shell
    PATH lookup."""
    global _CLAUDE_BIN
    if _CLAUDE_BIN is not None:
        return _CLAUDE_BIN
    env_bin = os.environ.get("CLAUDE_BIN")
    if env_bin and Path(env_bin).exists():
        _CLAUDE_BIN = env_bin
        return _CLAUDE_BIN
    for c in (
        Path.home() / ".claude" / "local" / "claude",
        Path("/opt/homebrew/bin/claude"),
        Path("/usr/local/bin/claude"),
    ):
        if c.exists():
            _CLAUDE_BIN = str(c)
            return _CLAUDE_BIN
    try:
        out = subprocess.run(
            ["/bin/zsh", "-lc", "command -v claude"],
            capture_output=True,
            text=True,
            check=True,
        )
        path = out.stdout.strip()
        if path:
            _CLAUDE_BIN = path
            return _CLAUDE_BIN
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    _CLAUDE_BIN = "claude"
    return _CLAUDE_BIN
