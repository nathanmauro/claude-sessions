from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

TaskStatus = Literal["pending", "in_progress", "completed"]


def _ts_to_json(value: dt.datetime | None) -> str | None:
    """ISO-8601 string, rendering UTC as a ``Z`` suffix.

    Matches the prior pydantic ``model_dump(mode="json")`` output exactly so the
    dash payload shape is unchanged (pydantic emits ``Z`` for a ``+00:00``
    offset; other offsets / naive datetimes pass through ``isoformat()``).
    """
    if value is None:
        return None
    iso = value.isoformat()
    if iso.endswith("+00:00"):
        return iso[:-6] + "Z"
    return iso


@dataclass
class Task:
    task_id: str
    subject: str = ""
    description: str = ""
    status: TaskStatus = "pending"

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "subject": self.subject,
            "description": self.description,
            "status": self.status,
        }


# kw_only: every construction site passes keyword args. The defaulted ``source``
# field sits after the required path fields, which only a kw-only init allows —
# and it forbids positional construction so the field order can't bite later.
@dataclass(kw_only=True)
class Session:
    session_id: str
    project_dir: str
    cwd: str
    path: Path
    source: str = "claude"
    start_ts: dt.datetime | None = None
    end_ts: dt.datetime | None = None
    title: str = ""
    first_prompt: str = ""
    last_prompt: str = ""
    user_prompts: list[str] = field(default_factory=list)
    all_messages: list[tuple[str, str]] = field(default_factory=list)
    tasks: dict[str, Task] = field(default_factory=dict)
    user_msg_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_create_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def billable_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_create_tokens

    @property
    def total_tokens(self) -> int:
        return self.billable_tokens + self.cache_read_tokens

    @property
    def incomplete_tasks(self) -> list[Task]:
        return [t for t in self.tasks.values() if t.status != "completed"]

    @property
    def completed_tasks(self) -> list[Task]:
        return [t for t in self.tasks.values() if t.status == "completed"]

    def to_dict(self, exclude: set[str] | None = None) -> dict:
        """JSON-safe dict. Path -> str, datetime -> isoformat, nested Task -> dict.

        Mirrors the prior pydantic ``model_dump(mode="json")`` output: includes
        the computed ``billable_tokens`` / ``total_tokens`` fields. ``exclude``
        drops top-level keys (used by the dash to omit path/transcript fields).
        """
        exclude = exclude or set()
        data: dict = {
            "session_id": self.session_id,
            "source": self.source,
            "project_dir": self.project_dir,
            "cwd": self.cwd,
            "path": str(self.path),
            "start_ts": _ts_to_json(self.start_ts),
            "end_ts": _ts_to_json(self.end_ts),
            "title": self.title,
            "first_prompt": self.first_prompt,
            "last_prompt": self.last_prompt,
            "user_prompts": list(self.user_prompts),
            "all_messages": [list(m) for m in self.all_messages],
            "tasks": {tid: t.to_dict() for tid, t in self.tasks.items()},
            "user_msg_count": self.user_msg_count,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_create_tokens": self.cache_create_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "billable_tokens": self.billable_tokens,
            "total_tokens": self.total_tokens,
        }
        for key in exclude:
            data.pop(key, None)
        return data


@dataclass
class UsageTotals:
    input: int = 0
    output: int = 0
    cache_create: int = 0
    cache_read: int = 0
    billable: int = 0
    total: int = 0
    cache_hit_pct: float = 0.0
    session_count: int = 0

    @classmethod
    def from_sessions(cls, sessions: list[Session]) -> UsageTotals:
        inp = sum(s.input_tokens for s in sessions)
        out = sum(s.output_tokens for s in sessions)
        cc = sum(s.cache_create_tokens for s in sessions)
        cr = sum(s.cache_read_tokens for s in sessions)
        denom = cr + cc + inp
        return cls(
            input=inp,
            output=out,
            cache_create=cc,
            cache_read=cr,
            billable=inp + out + cc,
            total=inp + out + cc + cr,
            cache_hit_pct=(100.0 * cr / denom) if denom else 0.0,
            session_count=len(sessions),
        )

    def to_dict(self) -> dict:
        return {
            "input": self.input,
            "output": self.output,
            "cache_create": self.cache_create,
            "cache_read": self.cache_read,
            "billable": self.billable,
            "total": self.total,
            "cache_hit_pct": self.cache_hit_pct,
            "session_count": self.session_count,
        }


@dataclass(kw_only=True)
class SearchResult:
    session_id: str
    title: str
    snippet: str
    cwd: str
    source: str = "claude"
    date: str = ""

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "source": self.source,
            "title": self.title,
            "snippet": self.snippet,
            "cwd": self.cwd,
            "date": self.date,
        }
