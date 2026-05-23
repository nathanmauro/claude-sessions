"""Spawn / focus claude sessions as windows inside the calling tmux session."""
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from .base import claude_bin


class TmuxLauncher:
    """Open in a new tmux window; focus a pane by walking ``tmux list-panes -a``."""

    name = "tmux"

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
        cmd = " ".join(parts)
        try:
            subprocess.run(
                ["tmux", "new-window", "-c", cwd, cmd],
                check=True,
                capture_output=True,
            )
            return True, "opened tmux window"
        except subprocess.CalledProcessError as e:
            return False, e.stderr.decode("utf-8", errors="replace") or str(e)
        except FileNotFoundError:
            return False, "tmux binary not found in PATH"

    def focus_pid(self, pid: int) -> tuple[bool, str]:
        # Best effort: tmux only knows pane_pid (the shell), so this matches when
        # the caller passed a shell pid. Walking from a claude pid up to its
        # owning pane pid would need processes.py awareness of tmux — deferred.
        try:
            out = subprocess.run(
                [
                    "tmux",
                    "list-panes",
                    "-a",
                    "-F",
                    "#{pane_pid} #{session_name}:#{window_index}.#{pane_index}",
                ],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr or str(e)
        except FileNotFoundError:
            return False, "tmux binary not found in PATH"
        for line in out.splitlines():
            parts = line.split(None, 1)
            if len(parts) < 2:
                continue
            try:
                pane_pid = int(parts[0])
            except ValueError:
                continue
            if pane_pid == pid:
                target = parts[1]
                try:
                    subprocess.run(
                        ["tmux", "select-window", "-t", target],
                        check=True,
                        capture_output=True,
                    )
                    return True, f"selected tmux {target}"
                except subprocess.CalledProcessError as e:
                    return False, e.stderr.decode("utf-8", errors="replace") or str(e)
        return False, f"no tmux pane found owning pid {pid}"

    def focus_app(self, app_name: str) -> tuple[bool, str]:
        return False, f"focus_app({app_name!r}) not meaningful inside tmux"
