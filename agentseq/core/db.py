from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

from .config import CODEX_SESSIONS_DIR, DB_PATH, PROJECTS_DIR
from .models import SearchResult, Session, Task
from .parser import parse_any_session, parse_ts


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
    keys = set(r.keys())
    source = r["source"] if "source" in keys and r["source"] else "claude"
    path = (
        Path(r["path"])
        if "path" in keys and r["path"]
        else PROJECTS_DIR / (r["project_dir"] or "") / f"{sid}.jsonl"
    )
    task_rows = conn.execute(
        "SELECT * FROM tasks WHERE session_id = ?", (sid,)
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
        source=source,
        project_dir=r["project_dir"] or "",
        cwd=r["cwd"] or "",
        path=path,
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


def _ensure_column(conn: sqlite3.Connection, table: str, column_def: str) -> None:
    column = column_def.split()[0]
    cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")


def init_db() -> None:
    with get_db() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                source TEXT,
                project_dir TEXT,
                cwd TEXT,
                path TEXT,
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
            CREATE TABLE IF NOT EXISTS tasks (
                session_id TEXT,
                task_id TEXT,
                subject TEXT,
                description TEXT,
                status TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            CREATE TABLE IF NOT EXISTS project_meta (
                cwd TEXT PRIMARY KEY,
                github_url TEXT,
                notion_page_id TEXT,
                augment_indexed_at TEXT,
                editor TEXT
                );
            """)
        _ensure_column(conn, "sessions", "source TEXT")
        _ensure_column(conn, "sessions", "path TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_source_path ON sessions(source, path)"
        )
        try:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                    session_id UNINDEXED, role UNINDEXED, content,
                    tokenize='trigram'
                );
            """)
        except sqlite3.OperationalError:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                    session_id UNINDEXED, role UNINDEXED, content
                );
            """)


def iter_source_paths(
    projects_dir: Path = PROJECTS_DIR,
    codex_dir: Path = CODEX_SESSIONS_DIR,
) -> Iterator[tuple[str, Path]]:
    if projects_dir.exists():
        for proj in projects_dir.iterdir():
            if not proj.is_dir():
                continue
            for jsonl in proj.glob("*.jsonl"):
                yield "claude", jsonl
    if codex_dir.exists():
        for jsonl in codex_dir.rglob("*.jsonl"):
            yield "codex", jsonl


def index_all(
    projects_dir: Path = PROJECTS_DIR,
    codex_dir: Path = CODEX_SESSIONS_DIR,
) -> list[str]:
    init_db()
    changed: list[str] = []
    with get_db() as conn:
        for source, jsonl in iter_source_paths(projects_dir, codex_dir):
            stat = jsonl.stat()
            cur = conn.execute(
                "SELECT mtime, size FROM sessions WHERE source = ? AND path = ?",
                (source, str(jsonl)),
            ).fetchone()
            if cur and cur["mtime"] == stat.st_mtime and cur["size"] == stat.st_size:
                continue
            sess = parse_any_session(jsonl, source)
            if not sess:
                continue
            conn.execute("DELETE FROM messages_fts WHERE session_id = ?", (sess.session_id,))
            conn.execute("DELETE FROM tasks WHERE session_id = ?", (sess.session_id,))
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions(
                    session_id, source, project_dir, cwd, path, start_ts, end_ts,
                    title, first_prompt, last_prompt, user_msg_count,
                    input_tokens, output_tokens, cache_create_tokens,
                    cache_read_tokens, mtime, size
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    sess.session_id, sess.source, sess.project_dir, sess.cwd,
                    str(sess.path),
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
                    "INSERT INTO messages_fts(session_id, role, content) VALUES (?, ?, ?)",
                    (sess.session_id, role, content),
                )
            for t in sess.tasks.values():
                conn.execute(
                    """
                    INSERT INTO tasks(session_id, task_id, subject, description, status)
                    VALUES (?,?,?,?,?)
                    """,
                    (sess.session_id, t.task_id, t.subject, t.description, t.status),
                )
            changed.append(sess.session_id)
    return changed


def search(query: str, limit: int = 50) -> list[SearchResult]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT s.session_id, s.source, s.title, s.first_prompt, s.cwd, s.start_ts,
                   snippet(messages_fts, 2, '<b>', '</b>', '...', 64) as snippet
            FROM messages_fts
            JOIN sessions s ON s.session_id = messages_fts.session_id
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
            source=r["source"] or "claude",
            title=r["title"] or (r["first_prompt"] or "")[:80] or r["session_id"],
            snippet=r["snippet"] or "",
            cwd=r["cwd"] or "",
            date=ts.strftime("%Y-%m-%d %H:%M") if ts else "",
        ))
    return out
