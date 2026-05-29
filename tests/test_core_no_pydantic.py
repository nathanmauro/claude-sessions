"""Guard the zero-third-party-deps invariant for agentseq.core.

The P0 regression this prevents: a base `pip install agentseq` (no extras) must
produce a working CLI. pydantic only lives under the [dash]/[all] extras, so the
core import chain (cli.main -> core.sessions -> core.parser -> core.models) must
not import it. We assert that in a clean subprocess so a stray import anywhere in
the chain fails the build.
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

from agentseq.core.models import SearchResult, Session, Task, UsageTotals

_SUBPROCESS_SCRIPT = """
import sys

# Importing the CLI entrypoint pulls in the whole core import chain.
import agentseq.cli.main  # noqa: F401
import agentseq.core.models  # noqa: F401
import agentseq.core.parser  # noqa: F401
import agentseq.core.sessions  # noqa: F401
import agentseq.core.db  # noqa: F401
import agentseq.core.export  # noqa: F401
import agentseq.core.events  # noqa: F401
import agentseq.core.indexer  # noqa: F401

leaked = sorted(m for m in sys.modules if "pydantic" in m)
if leaked:
    print("PYDANTIC LEAKED:", leaked, file=sys.stderr)
    sys.exit(1)
print("OK")
sys.exit(0)
"""


def test_core_import_chain_does_not_pull_pydantic():
    proc = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS_SCRIPT],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"core/CLI import chain imported pydantic.\n"
        f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )
    assert "OK" in proc.stdout


def test_core_models_module_has_no_pydantic_import():
    src = (Path(__file__).resolve().parent.parent
           / "agentseq" / "core" / "models.py").read_text()
    assert "import pydantic" not in src
    assert "from pydantic" not in src


def test_session_to_dict_json_serializable():
    sess = Session(
        session_id="abc",
        project_dir="-Users-nathan-Developer-proj-foo",
        cwd="/Users/nathan/Developer/proj/foo",
        path=Path("/tmp/abc.jsonl"),
        start_ts=dt.datetime(2026, 5, 18, 10, 0, tzinfo=dt.UTC),
        end_ts=dt.datetime(2026, 5, 18, 11, 0, tzinfo=dt.UTC),
        title="Refactor",
        tasks={"1": Task(task_id="1", subject="do it", status="completed")},
        input_tokens=100,
        output_tokens=50,
        cache_create_tokens=35,
        cache_read_tokens=200,
    )
    d = sess.to_dict()
    # round-trips through json without a custom encoder
    round = json.loads(json.dumps(d))

    # Path serialized to a string, datetimes to ISO strings.
    assert round["path"] == "/tmp/abc.jsonl"
    assert isinstance(round["path"], str)
    # UTC rendered with a Z suffix, matching the prior pydantic model_dump.
    assert round["start_ts"] == "2026-05-18T10:00:00Z"
    assert round["end_ts"] == "2026-05-18T11:00:00Z"
    # computed properties present (matches the prior pydantic model_dump shape).
    assert round["billable_tokens"] == 185
    assert round["total_tokens"] == 385
    # nested Task serialized to a plain dict.
    assert round["tasks"]["1"] == {
        "task_id": "1",
        "subject": "do it",
        "description": "",
        "status": "completed",
    }


def test_ts_to_json_non_utc_and_naive_pass_through():
    """Only a +00:00 offset becomes ``Z``; other offsets / naive datetimes
    fall through ``isoformat()`` unchanged, matching prior pydantic output."""
    from agentseq.core.models import _ts_to_json

    # UTC -> Z suffix
    assert _ts_to_json(dt.datetime(2026, 5, 18, 10, 0, tzinfo=dt.UTC)) == "2026-05-18T10:00:00Z"
    # Non-UTC offset passes through unchanged (no Z).
    offset = dt.timezone(dt.timedelta(hours=-4))
    assert _ts_to_json(dt.datetime(2026, 5, 18, 10, 0, tzinfo=offset)) == "2026-05-18T10:00:00-04:00"
    # Naive datetime passes through unchanged.
    assert _ts_to_json(dt.datetime(2026, 5, 18, 10, 0)) == "2026-05-18T10:00:00"
    assert _ts_to_json(None) is None


def test_session_to_dict_handles_none_timestamps():
    sess = Session(
        session_id="x",
        project_dir="d",
        cwd="/c",
        path=Path("/tmp/x.jsonl"),
    )
    d = sess.to_dict()
    json.dumps(d)  # must not raise
    assert d["start_ts"] is None
    assert d["end_ts"] is None


def test_session_to_dict_exclude():
    sess = Session(
        session_id="x",
        project_dir="d",
        cwd="/c",
        path=Path("/tmp/x.jsonl"),
        user_prompts=["hi"],
        all_messages=[("user", "hi")],
    )
    d = sess.to_dict(exclude={"path", "all_messages", "user_prompts"})
    assert "path" not in d
    assert "all_messages" not in d
    assert "user_prompts" not in d
    json.dumps(d)  # still serializable


def test_search_result_to_dict_json_serializable():
    sr = SearchResult(
        session_id="sid",
        title="t",
        snippet="snip",
        cwd="/c",
        source="codex",
        date="2026-05-18 10:00",
    )
    d = sr.to_dict()
    round = json.loads(json.dumps(d))
    assert round == {
        "session_id": "sid",
        "source": "codex",
        "title": "t",
        "snippet": "snip",
        "cwd": "/c",
        "date": "2026-05-18 10:00",
    }


def test_usage_totals_to_dict_json_serializable():
    sessions = [
        Session(
            session_id="a",
            project_dir="d",
            cwd="/c",
            path=Path("/tmp/a.jsonl"),
            input_tokens=10,
            output_tokens=5,
            cache_create_tokens=2,
            cache_read_tokens=3,
        )
    ]
    totals = UsageTotals.from_sessions(sessions)
    d = totals.to_dict()
    round = json.loads(json.dumps(d))
    assert round["input"] == 10
    assert round["billable"] == 17
    assert round["total"] == 20
    assert round["session_count"] == 1
    assert isinstance(round["cache_hit_pct"], float)
