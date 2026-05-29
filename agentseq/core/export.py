from __future__ import annotations

import datetime as dt
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .config import CACHE_DIR, CODEX_SESSIONS_DIR, PROJECTS_DIR
from .parser import parse_any_session
from .sessions import find_session_path


@dataclass
class ExportResult:
    """Outcome of an export: where it landed and how much it actually wrote.

    ``written`` is the count of sessions that resolved + parsed into the
    artifact (``missing`` were selected but couldn't be found/parsed). The TUI
    reports ``written`` so the toast/Jobs row never overcount a partial export.
    """

    path: Path
    written: int
    missing: list[str]


def _session_title(session, prompt_len: int = 80) -> str:
    return session.title or session.first_prompt[:prompt_len] or session.session_id


def _started_ended(session) -> tuple[str, str]:
    started = session.start_ts.isoformat() if session.start_ts else "-"
    ended = session.end_ts.isoformat() if session.end_ts else "-"
    return started, ended


def _render_message(role: str, text: str) -> str:
    label = "User" if role == "user" else "Assistant" if role == "assistant" else role.title()
    return f"### {label}\n\n{text.strip()}\n"


def _render_session(session) -> str:
    title = _session_title(session)
    started, ended = _started_ended(session)
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


def _parse_selected(
    session_ids: Iterable[str],
    projects_dir: Path = PROJECTS_DIR,
    codex_dir: Path = CODEX_SESSIONS_DIR,
) -> tuple[list, list[str]]:
    """Resolve + parse the selected session ids, sorted oldest-first.

    Returns ``(parsed_sessions, missing_ids)``. Raises ``ValueError`` if the
    selection is empty or nothing could be parsed — the callers all surface
    that message to the user.
    """
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

    parsed.sort(key=_sort_key)
    return parsed, missing


def _sort_key(session) -> dt.datetime:
    """Oldest-first sort key that never compares naive against aware.

    ``parse_ts`` yields an aware datetime for ``Z``/offset timestamps but a
    naive one for offset-less timestamps; sorting a mix would raise
    ``TypeError``. Coerce naive values to UTC (and ``None`` to a UTC sentinel).
    """
    ts = session.start_ts
    if ts is None:
        return dt.datetime.min.replace(tzinfo=dt.UTC)
    return ts if ts.tzinfo else ts.replace(tzinfo=dt.UTC)


def _write_markdown(lines: list[str], kind: str, count: int, output_dir: Path | None) -> Path:
    """Write ``lines`` to a timestamped file under the exports dir, return path."""
    target_dir = output_dir or CACHE_DIR / "exports"
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = target_dir / f"agentseq-{kind}-{stamp}-{count}-sessions.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _collapse(text: str, limit: int = 280) -> str:
    """Collapse whitespace and truncate to ``limit`` chars with an ellipsis."""
    flat = " ".join((text or "").split())
    return flat if len(flat) <= limit else flat[:limit].rstrip() + "…"


def _last_assistant(session) -> str:
    for role, text in reversed(session.all_messages):
        if role == "assistant" and text.strip():
            return text.strip()
    return ""


def _missing_block(missing: list[str]) -> list[str]:
    if not missing:
        return []
    return ["", "Missing (not found / unparsable):", *[f"- `{sid}`" for sid in missing]]


def export_sessions_markdown(
    session_ids: Iterable[str],
    output_dir: Path | None = None,
    projects_dir: Path = PROJECTS_DIR,
    codex_dir: Path = CODEX_SESSIONS_DIR,
) -> ExportResult:
    parsed, missing = _parse_selected(session_ids, projects_dir, codex_dir)

    lines = [
        "# Agentseq Session Export",
        "",
        f"Generated: {dt.datetime.now(dt.UTC).isoformat()}",
        f"Sessions: {len(parsed)}",
    ]
    lines.extend(_missing_block(missing))
    lines.append("")
    for session in parsed:
        lines.append(_render_session(session))

    path = _write_markdown(lines, "export", len(parsed), output_dir)
    return ExportResult(path=path, written=len(parsed), missing=missing)


def export_handoff_summary(
    session_ids: Iterable[str],
    output_dir: Path | None = None,
    projects_dir: Path = PROJECTS_DIR,
    codex_dir: Path = CODEX_SESSIONS_DIR,
) -> ExportResult:
    """Condense the selected sessions into a resume-context handoff doc.

    Unlike the full export (every message), this is the "where we left off"
    digest: the goal, open tasks, and last activity per session, plus an
    aggregate roll-up of open tasks across the whole selection.
    """
    parsed, missing = _parse_selected(session_ids, projects_dir, codex_dir)

    projects = {s.cwd or "unknown" for s in parsed}
    starts = [s.start_ts for s in parsed if s.start_ts]
    ends = [s.end_ts for s in parsed if s.end_ts]
    open_tasks = [(s, t) for s in parsed for t in s.incomplete_tasks]

    span = "-"
    if starts and ends:
        span = f"{min(starts).isoformat()} → {max(ends).isoformat()}"

    lines = [
        "# Agentseq Handoff Summary",
        "",
        f"Generated: {dt.datetime.now(dt.UTC).isoformat()}",
        "",
        f"- Sessions: {len(parsed)}",
        f"- Projects: {len(projects)}",
        f"- Open tasks: {len(open_tasks)}",
        f"- Span: {span}",
    ]
    lines.extend(_missing_block(missing))

    lines.extend(["", "## Open tasks across all sessions", ""])
    if open_tasks:
        for session, task in open_tasks:
            mark = "~" if task.status == "in_progress" else " "
            lines.append(f"- [{mark}] {task.subject or task.task_id} ({session.session_id[:8]})")
    else:
        lines.append("_No open tasks recorded._")

    lines.extend(["", "## Sessions", ""])
    for session in parsed:
        title = _session_title(session)
        started, ended = _started_ended(session)
        lines.extend(
            [
                f"### {title}",
                "",
                f"- Source: `{session.source}`  |  Session: `{session.session_id}`",
                f"- CWD: `{session.cwd}`",
                f"- When: `{started}` → `{ended}`",
                f"- Messages: {session.user_msg_count}  |  Billable tokens: {session.billable_tokens}",
                f"- Tasks: {len(session.completed_tasks)} done / {len(session.incomplete_tasks)} open",
                "",
                f"**Goal:** {_collapse(session.first_prompt) or '—'}",
                "",
            ]
        )
        if session.incomplete_tasks:
            lines.append("**Still open:**")
            for task in session.incomplete_tasks:
                lines.append(f"- {task.subject or task.task_id}")
            lines.append("")
        last = _last_assistant(session)
        lines.extend([f"**Last activity:** {_collapse(last) or '—'}", ""])

    path = _write_markdown(lines, "handoff", len(parsed), output_dir)
    return ExportResult(path=path, written=len(parsed), missing=missing)


def export_skill_draft(
    session_ids: Iterable[str],
    output_dir: Path | None = None,
    projects_dir: Path = PROJECTS_DIR,
    codex_dir: Path = CODEX_SESSIONS_DIR,
) -> ExportResult:
    """Scaffold a Claude Code skill from patterns across the selected sessions.

    Deterministic: it cannot infer intent, so it seeds a ``SKILL.md`` skeleton
    with the real raw material (recurring prompts, source sessions, common
    project) and leaves clearly-marked ``TODO`` slots for the judgment calls.
    """
    parsed, missing = _parse_selected(session_ids, projects_dir, codex_dir)

    # Derive a kebab-case skill name from the most common project basename.
    basenames = Counter(Path(s.cwd).name for s in parsed if s.cwd)
    base = basenames.most_common(1)[0][0] if basenames else "session"
    slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-") or "session"
    name = f"{slug}-workflow"

    # Recurring prompts are the skill's raw "triggers" — dedup, keep order.
    seen: set[str] = set()
    prompts: list[str] = []
    for session in parsed:
        for prompt in session.user_prompts:
            collapsed = _collapse(prompt, limit=200)
            key = collapsed.lower()
            if collapsed and key not in seen:
                seen.add(key)
                prompts.append(collapsed)

    lines = [
        "---",
        f"name: {name}",
        "description: TODO — one line: what this skill does and when to trigger it.",
        "---",
        "",
        f"# {base} workflow (DRAFT)",
        "",
        "> Auto-scaffolded by `agentseq` from "
        f"{len(parsed)} session(s). Fill the TODO slots, prune the raw material, "
        "then move this to your skills directory.",
    ]
    lines.extend(_missing_block(missing))

    lines.extend(
        [
            "",
            "## When to use",
            "",
            "TODO — describe the trigger conditions. The recurring prompts below "
            "are the raw signal for this.",
            "",
            "## Workflow",
            "",
            "TODO — the repeatable steps. Derive them from the source transcripts.",
            "",
            "## Recurring prompts (raw material)",
            "",
        ]
    )
    if prompts:
        for prompt in prompts[:30]:
            lines.append(f"- {prompt}")
        if len(prompts) > 30:
            lines.append(f"- … and {len(prompts) - 30} more")
    else:
        lines.append("_No user prompts captured._")

    lines.extend(["", "## Source sessions", ""])
    for session in parsed:
        title = _session_title(session, prompt_len=60)
        lines.append(
            f"- `{session.source}:{session.session_id[:8]}` — {_collapse(title, 80)} "
            f"(`{session.cwd}`)"
        )

    path = _write_markdown(lines, "skill", len(parsed), output_dir)
    return ExportResult(path=path, written=len(parsed), missing=missing)
