"""Fallback launcher: fails loud with an actionable hint."""
from __future__ import annotations

_HINT = (
    "no launcher available for this environment. "
    "Set AGENT_SESSIONS_LAUNCHER (or legacy CLAUDE_SESSIONS_LAUNCHER) to one of: ghostty, tmux, zellij. "
    "Or open a terminal manually and run: claude --resume <session-id>"
)


class GenericLauncher:
    """No-op backend for unrecognized environments. Returns failure + hint."""

    name = "generic"

    def open_new(
        self, cwd: str, session_id: str | None = None, extra: str = ""
    ) -> tuple[bool, str]:
        return False, _HINT

    def focus_pid(self, pid: int) -> tuple[bool, str]:
        return False, "focus not supported by generic launcher"

    def focus_app(self, app_name: str) -> tuple[bool, str]:
        return False, "focus not supported by generic launcher"
