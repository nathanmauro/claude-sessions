from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from .models import Session, Task


def decode_project_dir(name: str) -> str:
    if name.startswith("-"):
        return "/" + name[1:].replace("-", "/")
    return name.replace("-", "/")


def parse_ts(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                out.append(c.get("text", ""))
        return "\n".join(out)
    return ""


def extract_codex_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get("type") in {"input_text", "output_text", "text"}:
                out.append(c.get("text", ""))
        return "\n".join(x for x in out if x)
    return ""


def is_real_user_prompt(text: str) -> bool:
    if not text:
        return False
    t = text.strip()
    if (
        not t
        or t.startswith("<command-")
        or t.startswith("<local-command-")
        or t.startswith("<system-reminder")
        or "Messages below were generated" in t
    ):
        return False
    return True


def is_real_codex_user_prompt(text: str) -> bool:
    if not is_real_user_prompt(text):
        return False
    t = text.strip()
    if t.startswith("# AGENTS.md instructions for "):
        return False
    if t.startswith("<environment_context>"):
        return False
    return True


def parse_session(path: Path) -> Session | None:
    project_dir = path.parent.name
    sess = Session(
        session_id=path.stem,
        project_dir=project_dir,
        cwd=decode_project_dir(project_dir),
        path=path,
    )
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    j = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = j.get("type")
                if j.get("cwd"):
                    sess.cwd = j["cwd"]
                ts = parse_ts(j.get("timestamp"))
                if ts:
                    if sess.start_ts is None or ts < sess.start_ts:
                        sess.start_ts = ts
                    if sess.end_ts is None or ts > sess.end_ts:
                        sess.end_ts = ts
                if t == "ai-title":
                    sess.title = j.get("aiTitle", "") or sess.title
                elif t == "user" and not j.get("isSidechain") and not j.get("isMeta"):
                    text = extract_text((j.get("message") or {}).get("content", ""))
                    if text:
                        sess.all_messages.append(("user", text))
                    if is_real_user_prompt(text):
                        sess.user_msg_count += 1
                        snippet = text.strip()
                        if not sess.first_prompt:
                            sess.first_prompt = snippet
                        sess.last_prompt = snippet
                        if len(sess.user_prompts) < 50:
                            sess.user_prompts.append(snippet)
                elif t == "assistant" and not j.get("isSidechain"):
                    msg = j.get("message", {}) or {}
                    text = extract_text(msg.get("content", ""))
                    if text:
                        sess.all_messages.append(("assistant", text))
                    usage = msg.get("usage") or {}
                    sess.input_tokens += usage.get("input_tokens", 0) or 0
                    sess.output_tokens += usage.get("output_tokens", 0) or 0
                    sess.cache_create_tokens += usage.get("cache_creation_input_tokens", 0) or 0
                    sess.cache_read_tokens += usage.get("cache_read_input_tokens", 0) or 0
                    for c in msg.get("content", []):
                        if not isinstance(c, dict) or c.get("type") != "tool_use":
                            continue
                        name = c.get("name")
                        inp = c.get("input", {}) or {}
                        if name == "TaskCreate":
                            tid = str(inp.get("taskId") or len(sess.tasks) + 1)
                            sess.tasks[tid] = Task(
                                task_id=tid,
                                subject=inp.get("subject", ""),
                                description=inp.get("description", ""),
                            )
                        elif name == "TaskUpdate":
                            tid = str(inp.get("taskId", ""))
                            if tid in sess.tasks and inp.get("status"):
                                sess.tasks[tid].status = inp["status"]
    except OSError:
        return None
    return sess if sess.start_ts else None


def parse_codex_session(path: Path) -> Session | None:
    project_dir = str(path.parent)
    sess = Session(
        session_id=path.stem,
        source="codex",
        project_dir=project_dir,
        cwd="",
        path=path,
    )
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    j = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = parse_ts(j.get("timestamp"))
                if ts:
                    if sess.start_ts is None or ts < sess.start_ts:
                        sess.start_ts = ts
                    if sess.end_ts is None or ts > sess.end_ts:
                        sess.end_ts = ts

                payload = j.get("payload") or {}
                record_type = j.get("type")
                if record_type == "session_meta":
                    sid = payload.get("id")
                    if sid:
                        sess.session_id = str(sid)
                    if payload.get("cwd"):
                        sess.cwd = payload["cwd"]
                elif record_type == "turn_context" and payload.get("cwd") and not sess.cwd:
                    sess.cwd = payload["cwd"]
                elif record_type == "response_item" and payload.get("type") == "message":
                    role = payload.get("role")
                    if role not in {"user", "assistant"}:
                        continue
                    text = extract_codex_text(payload.get("content", ""))
                    if not text:
                        continue
                    if role == "user":
                        if not is_real_codex_user_prompt(text):
                            continue
                        sess.user_msg_count += 1
                        snippet = text.strip()
                        if not sess.first_prompt:
                            sess.first_prompt = snippet
                            sess.title = " ".join(snippet.split())[:80]
                        sess.last_prompt = snippet
                        if len(sess.user_prompts) < 50:
                            sess.user_prompts.append(snippet)
                    sess.all_messages.append((role, text))
    except OSError:
        return None
    if not sess.cwd:
        sess.cwd = path.parent.name
    return sess if sess.start_ts else None


def parse_any_session(path: Path, source: str = "claude") -> Session | None:
    if source == "codex":
        return parse_codex_session(path)
    return parse_session(path)
