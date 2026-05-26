"""Pluggable session source registry.

A `SessionSource` adapts an external transcript store (Claude Code's JSONL
projects dir, Augment's session JSON, etc.) to a uniform protocol so the
indexer and list path can iterate them generically. Wave 1A only ships the
Claude source; Wave 2 adds Augment.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..models import Session


@runtime_checkable
class SessionSource(Protocol):
    name: str

    def is_available(self) -> bool: ...
    def iter_session_files(self) -> Iterator[Path]: ...
    def parse(self, path: Path) -> Session | None: ...


from .claude import ClaudeSource  # noqa: E402

_REGISTRY: list[SessionSource] = [ClaudeSource()]


def get_sources() -> list[SessionSource]:
    """Return registered sources whose on-disk store is currently available."""
    return [s for s in _REGISTRY if s.is_available()]


__all__ = ["SessionSource", "ClaudeSource", "get_sources"]
