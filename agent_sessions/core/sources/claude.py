"""Claude Code JSONL source — wraps the existing parser behind SessionSource."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from ..config import PROJECTS_DIR
from ..models import Session
from ..parser import parse_session


class ClaudeSource:
    name = "claude"

    def __init__(self, projects_dir: Path | None = None) -> None:
        self.projects_dir = projects_dir if projects_dir is not None else PROJECTS_DIR

    def is_available(self) -> bool:
        return self.projects_dir.exists()

    def iter_session_files(self) -> Iterator[Path]:
        if not self.projects_dir.exists():
            return iter(())
        return self.projects_dir.rglob("*.jsonl")

    def parse(self, path: Path) -> Session | None:
        sess = parse_session(path)
        if sess is not None:
            sess.source = self.name
        return sess
