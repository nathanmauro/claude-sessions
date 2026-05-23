"""Backcompat helpers for the claude-sessions → agent-sessions rename."""
from __future__ import annotations

import os
import sys

_warned: set[str] = set()


def _env(new_name: str, old_name: str, default: str = "") -> str:
    """Read ``$new_name``; fall back to ``$old_name`` with a one-shot stderr warning.

    The deprecation warning fires at most once per ``old_name`` per process."""
    v = os.environ.get(new_name)
    if v is not None:
        return v
    v = os.environ.get(old_name)
    if v is not None:
        if old_name not in _warned:
            _warned.add(old_name)
            print(
                f"warning: ${old_name} is deprecated, use ${new_name}",
                file=sys.stderr,
            )
        return v
    return default
