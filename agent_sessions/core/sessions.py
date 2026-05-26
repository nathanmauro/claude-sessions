"""Enumerate Claude Code sessions, preferring the SQLite index when present."""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import DB_PATH, PROJECTS_DIR


@dataclass
class Session:
    session_id: str
    cwd: str
    project_dir: str
    path: str
    mtime: float
    size: int
    start_ts: str | None = None
    end_ts: str | None = None
    title: str | None = None
    first_prompt: str | None = None
    last_prompt: str | None = None
    user_msg_count: int = 0
    source: str = "claude"

    @property
    def project_name(self) -> str:
        return Path(self.cwd).name or self.cwd

    def to_dict(self) -> dict:
        return asdict(self)


def _decode_project_dir(name: str) -> str:
    if name.startswith("-"):
        return "/" + name[1:].replace("-", "/")
    return name.replace("-", "/")


def _is_real_prompt(text: str) -> bool:
    if not text:
        return False
    t = text.strip()
    if not t:
        return False
    for bad in ("<command-", "<local-command-", "<system-reminder"):
        if t.startswith(bad):
            return False
    if "Messages below were generated" in t:
        return False
    return True


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                out.append(c.get("text", ""))
        return "\n".join(out)
    return ""


def parse_session_file(path: Path) -> Session | None:
    try:
        st = path.stat()
    except OSError:
        return None
    project_dir = path.parent.name
    sess = Session(
        session_id=path.stem,
        cwd=_decode_project_dir(project_dir),
        project_dir=project_dir,
        path=str(path),
        mtime=st.st_mtime,
        size=st.st_size,
    )
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    j = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if j.get("cwd"):
                    sess.cwd = j["cwd"]
                ts = j.get("timestamp")
                if ts:
                    if sess.start_ts is None or ts < sess.start_ts:
                        sess.start_ts = ts
                    if sess.end_ts is None or ts > sess.end_ts:
                        sess.end_ts = ts
                t = j.get("type")
                if t == "ai-title":
                    sess.title = j.get("aiTitle") or sess.title
                elif t == "user" and not j.get("isSidechain") and not j.get("isMeta"):
                    text = _extract_text((j.get("message") or {}).get("content", ""))
                    if _is_real_prompt(text):
                        sess.user_msg_count += 1
                        snip = text.strip()
                        if not sess.first_prompt:
                            sess.first_prompt = snip
                        sess.last_prompt = snip
    except OSError:
        return None
    return sess


def load_sessions_from_index(db_path: Path = DB_PATH) -> list[Session] | None:
    """Read session rows from the SQLite index. Returns None on any
    schema/availability issue so the caller can fall back to JSONL parsing."""
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        return None
    try:
        cur = conn.execute(
            "SELECT session_id, source, project_dir, cwd, start_ts, end_ts, "
            "title, first_prompt, last_prompt, user_msg_count, mtime, size "
            "FROM sessions"
        )
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()
    out: list[Session] = []
    for r in rows:
        out.append(
            Session(
                session_id=r[0],
                source=r[1] or "claude",
                project_dir=r[2] or "",
                cwd=r[3] or "",
                path="",
                mtime=float(r[10] or 0.0),
                size=int(r[11] or 0),
                start_ts=r[4],
                end_ts=r[5],
                title=r[6],
                first_prompt=r[7],
                last_prompt=r[8],
                user_msg_count=int(r[9] or 0),
            )
        )
    return out


def list_sessions(projects_dir: Path = PROJECTS_DIR) -> list[Session]:
    if DB_PATH.exists():
        rows = load_sessions_from_index(DB_PATH)
        if rows is not None:
            rows.sort(key=lambda s: s.mtime, reverse=True)
            return rows
    from .sources import get_sources

    out: list[Session] = []
    for source in get_sources():
        for jsonl in source.iter_session_files():
            s = parse_session_file(jsonl)
            if s is not None:
                s.source = source.name
                out.append(s)
    out.sort(key=lambda s: s.mtime, reverse=True)
    return out


def age_from_iso(iso_ts: str | None) -> str:
    """Compact age string from an ISO-8601 timestamp."""
    if not iso_ts:
        return "-"
    try:
        ts = dt.datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return "-"
    delta = dt.datetime.now(dt.UTC) - ts
    secs = int(delta.total_seconds())
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m"
    if secs < 86400:
        return f"{secs // 3600}h"
    return f"{secs // 86400}d"


def iter_session_paths(projects_dir: Path = PROJECTS_DIR) -> Iterator[Path]:
    from .sources import get_sources

    for source in get_sources():
        yield from source.iter_session_files()


def session_display_title(s: Session, maxlen: int = 60) -> str:
    """Best human-readable label."""
    candidate = s.title or s.first_prompt or s.session_id[:8]
    candidate = " ".join(candidate.split())
    if len(candidate) > maxlen:
        candidate = candidate[: maxlen - 1] + "…"
    return candidate
