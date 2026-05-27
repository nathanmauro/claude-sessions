"""Backcompat helpers for the claude-sessions → agent-sessions → agentseq rename."""
from __future__ import annotations

import os
import sys

_warned: set[str] = set()


def _env(new_name: str, *old_names: str, default: str = "") -> str:
    """Read ``$new_name``; fall back through ``old_names`` with a one-shot stderr warning."""
    v = os.environ.get(new_name)
    if v is not None:
        return v
    for old in old_names:
        v = os.environ.get(old)
        if v is not None:
            if old not in _warned:
                _warned.add(old)
                print(
                    f"warning: ${old} is deprecated, use ${new_name}",
                    file=sys.stderr,
                )
            return v
    return default
