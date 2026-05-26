"""Detect running `claude --resume <session_id>` processes and trace to Ghostty."""
from __future__ import annotations

import re
import subprocess
from dataclasses import asdict, dataclass

RESUME_RE = re.compile(r"(?:^|\s)claude\b.*?--resume[=\s]+([a-f0-9-]{36})")
GHOSTTY_BIN = "/Applications/Ghostty.app/Contents/MacOS/ghostty"


@dataclass
class RunningSession:
    session_id: str
    pid: int
    argv: str
    terminal_pid: int | None
    terminal_app: str | None
    pid_chain: list[int]

    def to_dict(self) -> dict:
        return asdict(self)


def _ps_axwwo() -> list[tuple[int, int, str]]:
    """Return [(pid, ppid, full_command), ...]."""
    out = subprocess.run(
        ["ps", "-axww", "-o", "pid=,ppid=,command="],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    rows: list[tuple[int, int, str]] = []
    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
        except ValueError:
            continue
        rows.append((pid, ppid, parts[2]))
    return rows


def _proc_info(pid: int) -> tuple[int, str] | None:
    """(ppid, command) for pid, or None."""
    try:
        out = subprocess.run(
            ["ps", "-o", "ppid=,command=", "-p", str(pid)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return None
    if not out:
        return None
    parts = out.split(None, 1)
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), parts[1]
    except ValueError:
        return None


def _walk_to_terminal(start_pid: int, max_depth: int = 16) -> tuple[list[int], int | None, str | None]:
    """Walk parent chain looking for a known terminal emulator. Returns (chain, terminal_pid, terminal_app)."""
    chain: list[int] = []
    pid = start_pid
    for _ in range(max_depth):
        info = _proc_info(pid)
        if info is None:
            break
        ppid, cmd = info
        chain.append(pid)
        # Identify terminal at this level
        app = _identify_terminal(cmd)
        if app:
            return chain, pid, app
        if ppid <= 1 or ppid == pid:
            break
        pid = ppid
    return chain, None, None


_TERMINAL_MARKERS = {
    "Ghostty": "Ghostty",
    "iTerm": "iTerm",
    "Terminal.app": "Terminal",
    "Alacritty": "Alacritty",
    "WezTerm": "WezTerm",
    "kitty": "kitty",
    "Warp.app": "Warp",
}


def _identify_terminal(cmd: str) -> str | None:
    for marker, name in _TERMINAL_MARKERS.items():
        if marker in cmd:
            return name
    return None


def list_running() -> list[RunningSession]:
    """Find all claude --resume <id> processes."""
    rows = _ps_axwwo()
    out: list[RunningSession] = []
    seen: set[str] = set()
    for pid, _ppid, cmd in rows:
        m = RESUME_RE.search(cmd)
        if not m:
            continue
        sid = m.group(1)
        # Skip the inner claude-helper variants (one entry per session is enough)
        if sid in seen:
            continue
        seen.add(sid)
        chain, term_pid, term_app = _walk_to_terminal(pid)
        out.append(
            RunningSession(
                session_id=sid,
                pid=pid,
                argv=cmd,
                terminal_pid=term_pid,
                terminal_app=term_app,
                pid_chain=chain,
            )
        )
    return out


def find_running(session_id: str) -> RunningSession | None:
    for r in list_running():
        if r.session_id == session_id:
            return r
    return None
