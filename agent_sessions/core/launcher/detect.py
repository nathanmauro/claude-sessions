"""Pick a launcher backend based on environment or explicit user choice."""
from __future__ import annotations

import os
from pathlib import Path

from .._compat import _env
from .base import Launcher
from .generic import GenericLauncher
from .ghostty import GHOSTTY_APP, GhosttyLauncher
from .tmux import TmuxLauncher
from .zellij import ZellijLauncher

ENV_VAR = "AGENT_SESSIONS_LAUNCHER"
_LEGACY_ENV_VAR = "CLAUDE_SESSIONS_LAUNCHER"

# Eagerly probe at import so the deprecation warning fires once even for
# subcommands (e.g. ``ls``) that never reach the launcher selection path.
_env(ENV_VAR, _LEGACY_ENV_VAR)

_REGISTRY: dict[str, type[Launcher]] = {
    "ghostty": GhosttyLauncher,
    "tmux": TmuxLauncher,
    "zellij": ZellijLauncher,
    "generic": GenericLauncher,
}


def get_launcher(name: str) -> Launcher:
    """Instantiate a launcher by name. Raises ``ValueError`` on unknown name."""
    try:
        return _REGISTRY[name]()
    except KeyError:
        raise ValueError(
            f"unknown launcher: {name!r}; choices: {sorted(_REGISTRY)}"
        ) from None


def autodetect() -> Launcher:
    """Choose a launcher from the calling process's environment.

    Order: ``$AGENT_SESSIONS_LAUNCHER`` override (or legacy
    ``$CLAUDE_SESSIONS_LAUNCHER``) → ``$ZELLIJ`` → ``$TMUX`` →
    Ghostty.app present → :class:`GenericLauncher`.

    Use this from the CLI: when the user runs ``agent-sessions smart`` inside
    a multiplexer, they expect a new pane in *that* multiplexer, not a fresh
    external terminal."""
    forced = _env(ENV_VAR, _LEGACY_ENV_VAR)
    if forced:
        return get_launcher(forced)
    if os.environ.get("ZELLIJ"):
        return ZellijLauncher()
    if os.environ.get("TMUX"):
        return TmuxLauncher()
    if Path(GHOSTTY_APP).exists():
        return GhosttyLauncher()
    return GenericLauncher()


def gui_window() -> Launcher:
    """Always pick a GUI-window launcher; never a multiplexer pane.

    Use this from the dash server and the menubar app: the user is clicking a
    button or menu item — they expect a fresh terminal window, regardless of
    what multiplexer the server/app happens to be running inside.

    Honors the override env var only if it names a GUI launcher (``ghostty`` or
    ``generic``)."""
    forced = _env(ENV_VAR, _LEGACY_ENV_VAR)
    if forced in ("ghostty", "generic"):
        return get_launcher(forced)
    if Path(GHOSTTY_APP).exists():
        return GhosttyLauncher()
    return GenericLauncher()
