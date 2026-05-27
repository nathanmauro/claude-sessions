"""Open new Ghostty.app windows and focus existing terminal apps on macOS."""
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from .base import claude_bin

GHOSTTY_APP = "/Applications/Ghostty.app"


class GhosttyLauncher:
    """Spawn ``claude`` in a fresh Ghostty window; focus via AppleScript."""

    name = "ghostty"

    def open_new(
        self, cwd: str, session_id: str | None = None, extra: str = ""
    ) -> tuple[bool, str]:
        if not Path(cwd).exists():
            return False, f"cwd does not exist: {cwd}"
        bin_ = claude_bin()
        parts = [shlex.quote(bin_)]
        if session_id:
            parts.append(f"--resume {shlex.quote(session_id)}")
        if extra.strip():
            parts.append(shlex.quote(extra.strip()))
        command = " ".join(parts)
        # Run a login shell so PATH resolves and the prompt stays after claude exits.
        inner = f"cd {shlex.quote(cwd)} && exec {command}"
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
            return True, "opened Ghostty window"
        except subprocess.CalledProcessError as e:
            return False, e.stderr.decode("utf-8", errors="replace") or str(e)
        except FileNotFoundError:
            return False, "`open` not found (macOS only)"

    def focus_app(self, app_name: str) -> tuple[bool, str]:
        script = f'tell application "{app_name}" to activate'
        try:
            subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
            return True, f"activated {app_name}"
        except subprocess.CalledProcessError as e:
            return False, e.stderr.decode("utf-8", errors="replace") or str(e)
        except FileNotFoundError:
            return False, "osascript not available (macOS only)"

    def focus_pid(self, pid: int) -> tuple[bool, str]:
        script = (
            'tell application "System Events" to '
            f"set frontmost of (first process whose unix id is {pid}) to true"
        )
        try:
            subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
            return True, f"focused pid {pid}"
        except subprocess.CalledProcessError as e:
            return False, e.stderr.decode("utf-8", errors="replace") or str(e)
        except FileNotFoundError:
            return False, "osascript not available (macOS only)"
