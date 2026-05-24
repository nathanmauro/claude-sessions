#!/usr/bin/env python3
"""Seed a demo SQLite index for screenshot captures.

Used by web/scripts/capture-cli.sh and web/scripts/capture-menu.sh so the
CLI and menubar screenshots show deterministic, PII-free content.

Writes to $AGENT_SESSIONS_CACHE/index.db (defaulting to /tmp/demo-agent-sessions/).
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

CACHE_DIR = Path(
    os.environ.get("AGENT_SESSIONS_CACHE", "/tmp/demo-agent-sessions")
).expanduser()
DB_PATH = CACHE_DIR / "index.db"

NOW = time.time()
H = 3600.0


def hours_ago(h: float) -> tuple[str, str, float]:
    end = NOW - h * H
    start = end - 45 * 60
    iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(t))
    return iso(start), iso(end), end


# (sid_prefix, cwd, title, age_hours, msgs, in_tok, out_tok, cache_read)
ROWS = [
    ("01k5c4xa", "/Users/demo/code/orbital-cli",    "Wire up the new router with deferred imports",   1,  14, 18500, 6200,  42000),
    ("01k5b9zd", "/Users/demo/code/lighthouse-api", "Background job retries — exponential backoff",   3,  22, 24100, 9800,  71300),
    ("01k5a2qb", "/Users/demo/code/portfolio-site", "Dark mode tokens + system-preference detection", 7,  9,  6400,  3100,  0),
    ("01k59lkp", "/Users/demo/code/orbital-cli",    "Migrate feature flags to OpenFeature",           25, 18, 31200, 12400, 88900),
    ("01k58hh1", "/Users/demo/code/lighthouse-api", "OTel tracing on the ingest pipeline",            29, 11, 14600, 5900,  30200),
    ("01k57e4w", "/Users/demo/code/portfolio-site", "Dynamic OG images for blog posts",               49, 6,  4800,  2200,  0),
    ("01k56dab", "/Users/demo/code/orbital-cli",    "Tighten the cold-start regression test",         73, 8,  9200,  3400,  18000),
    ("01k55c9f", "/Users/demo/code/lighthouse-api", "Add DLQ admin view + bulk replay",               96, 16, 21000, 8400,  52000),
]


def main() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
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
                description TEXT, status TEXT
            );
            CREATE TABLE project_meta (
                cwd TEXT PRIMARY KEY, github_url TEXT, notion_page_id TEXT,
                augment_indexed_at TEXT, editor TEXT
            );
        """)
        for sid_prefix, cwd, title, age, msgs, itok, otok, ctok in ROWS:
            sid = f"{sid_prefix}-{Path(cwd).name}"
            start_ts, end_ts, mtime = hours_ago(age)
            conn.execute(
                "INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (sid, cwd.replace("/", "-")[1:], cwd, start_ts, end_ts,
                 title, "", "", msgs, itok, otok, 0, ctok, mtime, 8192),
            )
        conn.commit()
    finally:
        conn.close()
    print(f"wrote {DB_PATH}")


if __name__ == "__main__":
    main()
