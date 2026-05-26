from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

from .config import DB_PATH, PROJECTS_DIR
from .models import SearchResult, Session, Task
from .parser import parse_ts
from .sources import get_sources


def build_project_index(sessions: Iterable[Session]) -> dict[str, tuple[str, str]]:
    """Map project name and cwd (both lowercased) → (cwd, latest_session_id).

    Used to wire Notion todos to recent project sessions for quick start/resume.
    """
    idx: dict[str, tuple[str, str]] = {}
    for s in sessions:
        cwd = s.cwd
        base = Path(cwd).name
        for key in (cwd.lower(), base.lower()):
            if key and key not in idx:
                idx[key] = (cwd, s.session_id)
    return idx


def _row_to_session(r, conn) -> Session:
    sid = r["session_id"]
    src = r["source"] or "claude"
    task_rows = conn.execute(
        "SELECT * FROM tasks WHERE source = ? AND session_id = ?", (src, sid)
    ).fetchall()
    tasks = {
        tr["task_id"]: Task(
            task_id=tr["task_id"],
            subject=tr["subject"] or "",
            description=tr["description"] or "",
            status=tr["status"] or "pending",
        )
        for tr in task_rows
    }
    return Session(
        session_id=sid,
        project_dir=r["project_dir"] or "",
        cwd=r["cwd"] or "",
        path=PROJECTS_DIR / (r["project_dir"] or "") / f"{sid}.jsonl",
        source=src,
        start_ts=parse_ts(r["start_ts"]),
        end_ts=parse_ts(r["end_ts"]),
        title=r["title"] or "",
        first_prompt=r["first_prompt"] or "",
        last_prompt=r["last_prompt"] or "",
        tasks=tasks,
        user_msg_count=r["user_msg_count"] or 0,
        input_tokens=r["input_tokens"] or 0,
        output_tokens=r["output_tokens"] or 0,
        cache_create_tokens=r["cache_create_tokens"] or 0,
        cache_read_tokens=r["cache_read_tokens"] or 0,
    )


def load_sessions(
    on_date=None,
    since=None,
    until=None,
) -> list[Session]:

    with get_db() as conn:
        q = "SELECT * FROM sessions"
        params: list = []
        if on_date:
            q += " WHERE date(start_ts) = ?"
            params.append(on_date.isoformat())
        elif since or until:
            q += " WHERE 1=1"
            if since:
                q += " AND date(end_ts) >= ?"
                params.append(since.isoformat())
            if until:
                q += " AND date(end_ts) <= ?"
                params.append(until.isoformat())
        q += " ORDER BY end_ts DESC"
        rows = conn.execute(q, params).fetchall()
        return [_row_to_session(r, conn) for r in rows]


def get_augment_indexed_at(cwd: str) -> str | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT augment_indexed_at FROM project_meta WHERE cwd = ?", (cwd,)
        ).fetchone()
        return row["augment_indexed_at"] if row else None


def set_augment_indexed_at(cwd: str, when: str) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO project_meta(cwd, augment_indexed_at) VALUES (?, ?)",
            (cwd, when),
        )


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


_SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS sessions (
        source TEXT NOT NULL DEFAULT 'claude',
        session_id TEXT NOT NULL,
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
        size INTEGER,
        PRIMARY KEY (source, session_id)
    );
    CREATE TABLE IF NOT EXISTS tasks (
        source TEXT NOT NULL DEFAULT 'claude',
        session_id TEXT NOT NULL,
        task_id TEXT,
        subject TEXT,
        description TEXT,
        status TEXT,
        FOREIGN KEY(source, session_id) REFERENCES sessions(source, session_id)
    );
    CREATE TABLE IF NOT EXISTS project_meta (
        cwd TEXT PRIMARY KEY,
        github_url TEXT,
        notion_page_id TEXT,
        augment_indexed_at TEXT,
        editor TEXT
    );
"""


def _migrate_add_source(conn: sqlite3.Connection) -> None:
    """Migrate pre-Phase-4 schema: add `source` column + composite PK.

    Safe to call on a fresh DB (no-op when `sessions` doesn't yet exist) or on
    an already-migrated DB (no-op when the `source` column is present).
    """
    cols = [r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()]
    if not cols or "source" in cols:
        return
    conn.execute("ALTER TABLE sessions RENAME TO _sessions_legacy")
    conn.execute("ALTER TABLE tasks RENAME TO _tasks_legacy")
    conn.executescript(_SCHEMA_SQL)
    conn.execute(
        """
        INSERT INTO sessions
            (source, session_id, project_dir, cwd, start_ts, end_ts, title,
             first_prompt, last_prompt, user_msg_count, input_tokens,
             output_tokens, cache_create_tokens, cache_read_tokens, mtime, size)
        SELECT 'claude', session_id, project_dir, cwd, start_ts, end_ts, title,
               first_prompt, last_prompt, user_msg_count, input_tokens,
               output_tokens, cache_create_tokens, cache_read_tokens, mtime, size
        FROM _sessions_legacy
        """
    )
    conn.execute(
        """
        INSERT INTO tasks
            (source, session_id, task_id, subject, description, status)
        SELECT 'claude', session_id, task_id, subject, description, status
        FROM _tasks_legacy
        """
    )
    conn.execute("DROP TABLE _sessions_legacy")
    conn.execute("DROP TABLE _tasks_legacy")
    conn.execute("DROP TABLE IF EXISTS messages_fts")
    conn.execute("UPDATE sessions SET mtime = 0")


def init_db() -> None:
    with get_db() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        _migrate_add_source(conn)
        conn.executescript(_SCHEMA_SQL)
        try:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                    session_id UNINDEXED, source UNINDEXED, role UNINDEXED, content,
                    tokenize='trigram'
                );
            """)
        except sqlite3.OperationalError:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                    session_id UNINDEXED, source UNINDEXED, role UNINDEXED, content
                );
            """)


def index_all(projects_dir: Path = PROJECTS_DIR) -> list[str]:
    init_db()
    changed: list[str] = []
    with get_db() as conn:
        for source in get_sources():
            src_name = source.name
            for jsonl in source.iter_session_files():
                try:
                    stat = jsonl.stat()
                except OSError:
                    continue
                cur = conn.execute(
                    "SELECT mtime, size FROM sessions WHERE source = ? AND session_id = ?",
                    (src_name, jsonl.stem),
                ).fetchone()
                if cur and cur["mtime"] == stat.st_mtime and cur["size"] == stat.st_size:
                    continue
                sess = source.parse(jsonl)
                if not sess:
                    continue
                conn.execute(
                    "DELETE FROM messages_fts WHERE source = ? AND session_id = ?",
                    (src_name, sess.session_id),
                )
                conn.execute(
                    "DELETE FROM tasks WHERE source = ? AND session_id = ?",
                    (src_name, sess.session_id),
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO sessions
                        (source, session_id, project_dir, cwd, start_ts, end_ts,
                         title, first_prompt, last_prompt, user_msg_count,
                         input_tokens, output_tokens, cache_create_tokens,
                         cache_read_tokens, mtime, size)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        src_name, sess.session_id, sess.project_dir, sess.cwd,
                        sess.start_ts.isoformat() if sess.start_ts else None,
                        sess.end_ts.isoformat() if sess.end_ts else None,
                        sess.title, sess.first_prompt, sess.last_prompt,
                        sess.user_msg_count, sess.input_tokens, sess.output_tokens,
                        sess.cache_create_tokens, sess.cache_read_tokens,
                        stat.st_mtime, stat.st_size,
                    ),
                )
                for role, content in sess.all_messages:
                    conn.execute(
                        "INSERT INTO messages_fts(session_id, source, role, content) "
                        "VALUES (?, ?, ?, ?)",
                        (sess.session_id, src_name, role, content),
                    )
                for t in sess.tasks.values():
                    conn.execute(
                        "INSERT INTO tasks "
                        "(source, session_id, task_id, subject, description, status) "
                        "VALUES (?,?,?,?,?,?)",
                        (src_name, sess.session_id, t.task_id, t.subject,
                         t.description, t.status),
                    )
                changed.append(sess.session_id)
    return changed


def search(query: str, limit: int = 50) -> list[SearchResult]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT s.session_id, s.title, s.first_prompt, s.cwd, s.start_ts,
                   snippet(messages_fts, 3, '<b>', '</b>', '...', 64) as snippet
            FROM messages_fts
            JOIN sessions s
              ON s.session_id = messages_fts.session_id
             AND s.source = messages_fts.source
            WHERE messages_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
    out: list[SearchResult] = []
    for r in rows:
        ts = parse_ts(r["start_ts"])
        out.append(SearchResult(
            session_id=r["session_id"],
            title=r["title"] or (r["first_prompt"] or "")[:80] or r["session_id"],
            snippet=r["snippet"] or "",
            cwd=r["cwd"] or "",
            date=ts.strftime("%Y-%m-%d %H:%M") if ts else "",
        ))
    return out
