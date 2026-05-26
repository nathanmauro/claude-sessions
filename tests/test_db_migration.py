"""Migration test for the Phase 4 schema change.

Builds a fixture DB with the pre-Phase-4 schema (no `source` column, single-
column `sessions` PK), runs `init_db`, and verifies that data is preserved
and the new shape is in place.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agent_sessions.core import db as db_module
from agent_sessions.core import sessions as sessions_module


def _build_legacy_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript("""
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                project_dir TEXT,
                cwd TEXT,
                start_ts TEXT,
                end_ts TEXT,
                title TEXT,
                first_prompt TEXT,
                last_prompt TEXT,
                user_msg_count INTEGER,
                input_tokens INTEGER,
                output_tokens INTEGER,
                cache_create_tokens INTEGER,
                cache_read_tokens INTEGER,
                mtime REAL,
                size INTEGER
            );
            CREATE TABLE tasks (
                session_id TEXT, task_id TEXT, subject TEXT,
                description TEXT, status TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            CREATE TABLE project_meta (
                cwd TEXT PRIMARY KEY, github_url TEXT, notion_page_id TEXT,
                augment_indexed_at TEXT, editor TEXT
            );
            CREATE VIRTUAL TABLE messages_fts USING fts5(
                session_id UNINDEXED, role UNINDEXED, content
            );
        """)
        conn.execute(
            "INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("sess-1", "-Users-x-proj-foo", "/Users/x/proj/foo",
             "2026-05-01T10:00:00", "2026-05-01T10:30:00",
             "title one", "first prompt", "last prompt",
             5, 100, 50, 10, 200, 1234.0, 4096),
        )
        conn.execute(
            "INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("sess-2", "-Users-x-proj-bar", "/Users/x/proj/bar",
             "2026-05-02T10:00:00", "2026-05-02T10:30:00",
             "title two", "first2", "last2",
             3, 80, 40, 5, 150, 5678.0, 2048),
        )
        conn.execute(
            "INSERT INTO tasks VALUES (?,?,?,?,?)",
            ("sess-1", "task-1", "do thing", "details", "completed"),
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def legacy_db(tmp_path, monkeypatch):
    db_path = tmp_path / "index.sqlite"
    _build_legacy_db(db_path)
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    monkeypatch.setattr(sessions_module, "DB_PATH", db_path)
    return db_path


def _table_info(conn: sqlite3.Connection, table: str):
    return conn.execute(f"PRAGMA table_info({table})").fetchall()


def test_migration_adds_source_column(legacy_db):
    db_module.init_db()
    conn = sqlite3.connect(legacy_db)
    try:
        cols = [r[1] for r in _table_info(conn, "sessions")]
        assert "source" in cols
        # Composite primary key on (source, session_id).
        pk_cols = [r[1] for r in _table_info(conn, "sessions") if r[5] > 0]
        assert set(pk_cols) == {"source", "session_id"}
    finally:
        conn.close()


def test_migration_preserves_session_rows(legacy_db):
    db_module.init_db()
    conn = sqlite3.connect(legacy_db)
    try:
        rows = list(conn.execute(
            "SELECT session_id, source, project_dir, cwd, title, user_msg_count "
            "FROM sessions ORDER BY session_id"
        ))
        assert rows == [
            ("sess-1", "claude", "-Users-x-proj-foo", "/Users/x/proj/foo",
             "title one", 5),
            ("sess-2", "claude", "-Users-x-proj-bar", "/Users/x/proj/bar",
             "title two", 3),
        ]
        distinct = list(conn.execute("SELECT DISTINCT source FROM sessions"))
        assert distinct == [("claude",)]
    finally:
        conn.close()


def test_migration_preserves_task_rows(legacy_db):
    db_module.init_db()
    conn = sqlite3.connect(legacy_db)
    try:
        task_cols = [r[1] for r in _table_info(conn, "tasks")]
        assert "source" in task_cols
        rows = list(conn.execute(
            "SELECT source, session_id, task_id, status FROM tasks"
        ))
        assert rows == [("claude", "sess-1", "task-1", "completed")]
    finally:
        conn.close()


def test_migration_recreates_fts_with_source(legacy_db):
    db_module.init_db()
    conn = sqlite3.connect(legacy_db)
    try:
        fts_cols = [r[1] for r in _table_info(conn, "messages_fts")]
        assert "source" in fts_cols
        assert "session_id" in fts_cols
    finally:
        conn.close()


def test_migration_resets_mtime_so_indexer_reprocesses(legacy_db):
    db_module.init_db()
    conn = sqlite3.connect(legacy_db)
    try:
        mtimes = [r[0] for r in conn.execute("SELECT mtime FROM sessions")]
        assert all(m == 0 for m in mtimes)
    finally:
        conn.close()


def test_init_db_is_idempotent_after_migration(legacy_db):
    db_module.init_db()
    db_module.init_db()  # second call must not fail or duplicate rows
    conn = sqlite3.connect(legacy_db)
    try:
        n = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        assert n == 2
    finally:
        conn.close()


def test_fresh_db_uses_new_schema(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh.sqlite"
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    db_module.init_db()
    conn = sqlite3.connect(db_path)
    try:
        cols = [r[1] for r in _table_info(conn, "sessions")]
        assert "source" in cols
        fts_cols = [r[1] for r in _table_info(conn, "messages_fts")]
        assert "source" in fts_cols
    finally:
        conn.close()


def test_load_sessions_from_index_surfaces_source(legacy_db):
    db_module.init_db()
    rows = sessions_module.load_sessions_from_index(legacy_db)
    assert rows is not None
    by_sid = {s.session_id: s for s in rows}
    assert by_sid["sess-1"].source == "claude"
    assert by_sid["sess-2"].source == "claude"


def test_load_sessions_returns_source_field(legacy_db):
    db_module.init_db()
    sessions = db_module.load_sessions()
    assert {s.session_id for s in sessions} == {"sess-1", "sess-2"}
    assert all(s.source == "claude" for s in sessions)
    # tasks copied with source
    s1 = next(s for s in sessions if s.session_id == "sess-1")
    assert "task-1" in s1.tasks
    assert s1.tasks["task-1"].status == "completed"
