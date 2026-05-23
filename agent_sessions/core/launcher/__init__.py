"""Pluggable launchers: open new claude sessions in the user's terminal,
multiplexer, or fallback. Shared by the CLI, the menubar app, and the
dashboard server.

Use :func:`autodetect` from the CLI (honors ``$ZELLIJ`` / ``$TMUX`` so
"open" lands as a pane in the calling shell's multiplexer) and
:func:`gui_window` from the dash and menubar (always picks a GUI terminal,
since their callers aren't a user shell)."""
from __future__ import annotations

from .base import Launcher, claude_bin, log_failure
from .detect import autodetect, get_launcher, gui_window
from .generic import GenericLauncher
from .ghostty import GhosttyLauncher
from .tmux import TmuxLauncher
from .zellij import ZellijLauncher

__all__ = [
    "GenericLauncher",
    "GhosttyLauncher",
    "Launcher",
    "TmuxLauncher",
    "ZellijLauncher",
    "autodetect",
    "claude_bin",
    "get_launcher",
    "gui_window",
    "log_failure",
]
