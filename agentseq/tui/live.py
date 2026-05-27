"""Poll live Claude agents via ``claude agents --json``."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from ..core.launcher.base import claude_bin


@dataclass
class LiveAgent:
    pid: int
    cwd: str
    kind: str
    started_at: int
    session_id: str
    name: str = ""
    status: str = ""


def fetch_live_agents() -> list[LiveAgent]:
    try:
        result = subprocess.run(
            [claude_bin(), "agents", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        return [
            LiveAgent(
                pid=a["pid"],
                cwd=a.get("cwd", ""),
                kind=a.get("kind", ""),
                started_at=a.get("startedAt", 0),
                session_id=a.get("sessionId", ""),
                name=a.get("name", ""),
                status=a.get("status", ""),
            )
            for a in data
        ]
    except Exception:
        return []
