"""Render a Claude Code JSONL transcript as plain markdown.

Mirrors the behavior of ~/.claude/hooks/extract-session.js default mode:
keeps the last compact-summary block (if any) and every real user/assistant
turn that follows, with command/system-reminder noise stripped out.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_STRIP_TAGS = (
    "system-reminder",
    "local-command-caveat",
    "command-name",
    "command-message",
    "command-args",
    "local-command-stdout",
)
_STRIP_RES = tuple(
    re.compile(rf"<{tag}>[\s\S]*?</{tag}>") for tag in _STRIP_TAGS
)

_DEFAULT_MAX_MSG_LEN = 2000


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(parts)
    return ""


def _scrub(text: str) -> str:
    for pat in _STRIP_RES:
        text = pat.sub("", text)
    return text.strip()


def render_markdown(path: Path, max_msg_len: int = _DEFAULT_MAX_MSG_LEN) -> str:
    """Return a markdown transcript for the JSONL session at `path`."""
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise FileNotFoundError(f"cannot read transcript {path}: {e}") from e

    last_summary: str | None = None
    last_summary_idx = -1
    messages: list[tuple[int, str, str]] = []  # (idx, role, text)

    for i, line in enumerate(raw.splitlines()):
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        if obj.get("isCompactSummary"):
            summary = _extract_text((obj.get("message") or {}).get("content", ""))
            if summary:
                last_summary = summary
                last_summary_idx = i
            continue

        role = obj.get("type")
        if role not in ("user", "assistant"):
            continue
        text = _extract_text((obj.get("message") or {}).get("content", ""))
        text = _scrub(text)
        if not text:
            continue
        messages.append((i, role, text))

    recent = [m for m in messages if m[0] > last_summary_idx] if last_summary_idx >= 0 else messages

    out: list[str] = []
    if last_summary:
        cleaned = re.sub(
            r"^This session is being continued from a previous conversation.*?\n+",
            "",
            last_summary,
            flags=re.DOTALL,
        )
        cleaned = re.sub(r"^Analysis:\s*\n", "", cleaned)
        out.append("## Session Summary\n")
        out.append(cleaned.strip())
        out.append("\n")

    if recent:
        if last_summary:
            out.append("---\n")
            out.append("## Recent Conversation\n")
        else:
            out.append("## Conversation\n")
        for _idx, role, text in recent:
            label = "**User:**" if role == "user" else "**Claude:**"
            if len(text) > max_msg_len:
                text = text[:max_msg_len] + "\n\n*[truncated...]*"
            out.append(f"{label}\n{text}\n")

    return "\n".join(out)
