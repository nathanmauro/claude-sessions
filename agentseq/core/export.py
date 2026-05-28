from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from pathlib import Path

from .config import CACHE_DIR, CODEX_SESSIONS_DIR, PROJECTS_DIR
from .parser import parse_any_session
from .sessions import find_session_path


def _render_message(role: str, text: str) -> str:
    label = "User" if role == "user" else "Assistant" if role == "assistant" else role.title()
    return f"### {label}\n\n{text.strip()}\n"


def _render_session(session) -> str:
    title = session.title or session.first_prompt[:80] or session.session_id
    started = session.start_ts.isoformat() if session.start_ts else "-"
    ended = session.end_ts.isoformat() if session.end_ts else "-"
    parts = [
        f"## {title}",
        "",
        f"- Source: `{session.source}`",
        f"- Session: `{session.session_id}`",
        f"- CWD: `{session.cwd}`",
        f"- Started: `{started}`",
        f"- Ended: `{ended}`",
        "",
    ]
    if session.all_messages:
        for role, text in session.all_messages:
            parts.append(_render_message(role, text))
    else:
        parts.append("_No transcript messages parsed._\n")
    return "\n".join(parts).rstrip() + "\n"


def export_sessions_markdown(
    session_ids: Iterable[str],
    output_dir: Path | None = None,
    projects_dir: Path = PROJECTS_DIR,
    codex_dir: Path = CODEX_SESSIONS_DIR,
) -> Path:
    ids = list(dict.fromkeys(session_ids))
    if not ids:
        raise ValueError("no sessions selected")

    parsed = []
    missing = []
    for sid in ids:
        found = find_session_path(sid, projects_dir=projects_dir, codex_dir=codex_dir)
        if not found:
            missing.append(sid)
            continue
        source, path = found
        session = parse_any_session(path, source)
        if session is None:
            missing.append(sid)
            continue
        parsed.append(session)

    if not parsed:
        raise ValueError("no selected sessions could be parsed")

    parsed.sort(key=lambda s: s.start_ts or dt.datetime.min.replace(tzinfo=dt.UTC))
    target_dir = output_dir or CACHE_DIR / "exports"
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = target_dir / f"agentseq-export-{stamp}-{len(parsed)}-sessions.md"

    lines = [
        "# Agentseq Session Export",
        "",
        f"Generated: {dt.datetime.now(dt.UTC).isoformat()}",
        f"Sessions: {len(parsed)}",
    ]
    if missing:
        lines.extend(["", "Missing:", *[f"- `{sid}`" for sid in missing]])
    lines.append("")
    for session in parsed:
        lines.append(_render_session(session))

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
