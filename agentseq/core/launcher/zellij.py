"""Spawn claude sessions as new panes inside the calling zellij session."""
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from .base import claude_bin


class ZellijLauncher:
    """Open in a new zellij pane via ``zellij action new-pane``. No focus support."""

    name = "zellij"

    def open_new(
        self, cwd: str, session_id: str | None = None, extra: str = ""
    ) -> tuple[bool, str]:
        if not Path(cwd).exists():
            return False, f"cwd does not exist: {cwd}"
        bin_ = claude_bin()
        parts = [shlex.quote(bin_)]
        if session_id:
            parts.append("--resume")
            parts.append(shlex.quote(session_id))
        if extra.strip():
            parts.append(shlex.quote(extra.strip()))
        # Wrap in a login shell so PATH resolves and the pane stays around if
        # claude exits. `zellij action new-pane -- <argv>` runs <argv> directly.
        inner = f"cd {shlex.quote(cwd)} && exec {' '.join(parts)}"
        try:
            subprocess.run(
                ["zellij", "action", "new-pane", "--", "/bin/zsh", "-lc", inner],
                check=True,
                capture_output=True,
            )
            return True, "opened zellij pane"
        except subprocess.CalledProcessError as e:
            return False, e.stderr.decode("utf-8", errors="replace") or str(e)
        except FileNotFoundError:
            return False, "zellij binary not found in PATH"

    def focus_pid(self, pid: int) -> tuple[bool, str]:
        return False, "zellij has no per-pane focus-by-pid; pane will open afresh"

    def focus_app(self, app_name: str) -> tuple[bool, str]:
        return False, f"focus_app({app_name!r}) not meaningful inside zellij"
