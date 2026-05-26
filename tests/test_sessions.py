"""Tests for session enumeration and SQLite cache freshness."""
from __future__ import annotations

import json
import os
from pathlib import Path

from agent_sessions.core import db, sessions
from agent_sessions.core.sources import ClaudeSource


def _write_session(
    project_dir: Path,
    session_id: str,
    prompt: str,
    timestamp: str,
    cwd: str,
    mtime: float,
) -> Path:
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / f"{session_id}.jsonl"
    path.write_text(
        json.dumps(
            {
                "type": "user",
                "timestamp": timestamp,
                "cwd": cwd,
                "message": {"content": prompt},
            }
        )
        + "\n"
    )
    os.utime(path, (mtime, mtime))
    return path


def _isolate_db_and_sources(monkeypatch, tmp_path: Path, projects: Path) -> Path:
    """Point both the DB and the source registry at temp directories."""
    db_path = tmp_path / "cache" / "index.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(sessions, "DB_PATH", db_path)

    from agent_sessions.core import sources as sources_mod

    monkeypatch.setattr(
        sources_mod, "_REGISTRY", [ClaudeSource(projects_dir=projects)]
    )
    return db_path


def test_list_sessions_refreshes_stale_index(monkeypatch, tmp_path: Path):
    projects = tmp_path / "projects"
    project_dir = projects / "-Users-nathan-Developer-proj-foo"
    _isolate_db_and_sources(monkeypatch, tmp_path, projects)

    _write_session(
        project_dir,
        "old-session",
        "old prompt",
        "2026-05-18T10:00:00Z",
        "/Users/nathan/Developer/proj/foo",
        1_700_000_000.0,
    )
    assert db.index_all(projects) == ["old-session"]

    _write_session(
        project_dir,
        "new-session",
        "new prompt",
        "2026-05-20T22:13:38Z",
        "/Users/nathan/Developer/proj/foo",
        1_700_000_100.0,
    )

    found = sessions.list_sessions(projects)

    assert [s.session_id for s in found] == ["new-session", "old-session"]
    assert found[0].first_prompt == "new prompt"


def test_list_sessions_falls_back_to_jsonl_when_refresh_fails(
    monkeypatch, tmp_path: Path
):
    projects = tmp_path / "projects"
    project_dir = projects / "-Users-nathan-Developer-proj-foo"
    _isolate_db_and_sources(monkeypatch, tmp_path, projects)

    _write_session(
        project_dir,
        "old-session",
        "old prompt",
        "2026-05-18T10:00:00Z",
        "/Users/nathan/Developer/proj/foo",
        1_700_000_000.0,
    )
    assert db.index_all(projects) == ["old-session"]

    _write_session(
        project_dir,
        "new-session",
        "new prompt",
        "2026-05-20T22:13:38Z",
        "/Users/nathan/Developer/proj/foo",
        1_700_000_100.0,
    )
    monkeypatch.setattr(sessions, "_refresh_stale_index", lambda *_args: False)

    found = sessions.list_sessions(projects)

    assert [s.session_id for s in found] == ["new-session", "old-session"]
