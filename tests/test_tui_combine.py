"""Combine workspace action tests.

The Export / Skill draft / Handoff actions share ``_run_export``: resolve the
selected sessions, write a markdown artifact, register a Jobs row, and notify.
These tests drive the actions through a mounted pane (textual is an optional
extra, so skip when absent) and assert the artifact lands on disk.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("textual")

from agentseq.tui.app import AgentSeqApp  # noqa: E402
from agentseq.tui.screens.combine import CombinePane  # noqa: E402
from agentseq.tui.screens.jobs import JobsPane  # noqa: E402

TRANSCRIPT = [
    {
        "type": "user",
        "timestamp": "2026-05-22T08:00:00Z",
        "message": {"content": "draft a skill from these sessions"},
    },
    {
        "type": "assistant",
        "timestamp": "2026-05-22T08:00:01Z",
        "message": {"content": [{"type": "text", "text": "on it"}]},
    },
]


def _write_claude_session(projects_dir: Path, sid: str, cwd: str) -> Path:
    project_slug = "-" + cwd.strip("/").replace("/", "-")
    path = projects_dir / project_slug / f"{sid}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(line) for line in TRANSCRIPT) + "\n")
    return path


def _run_pane_action(tmp_path: Path, action_name: str, glob: str) -> list[Path]:
    """Mount the app, select one fixture session, fire a Combine action.

    Returns the artifacts written under the patched exports dir.
    """
    projects_dir = tmp_path / "claude-projects"
    exports_root = tmp_path / "cache"
    fixture = _write_claude_session(projects_dir, "combine-1", "/tmp/proj")

    written: list[Path] = []
    notes: list[tuple] = []

    async def run():
        app = AgentSeqApp()
        with (
            patch("agentseq.tui.app.fetch_live_agents", return_value=[]),
            patch("agentseq.tui.screens.browser.list_sessions", return_value=[]),
            patch("agentseq.core.export.find_session_path", return_value=("claude", fixture)),
            patch("agentseq.core.export.CACHE_DIR", exports_root),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await app.workers.wait_for_complete()
                await pilot.pause()

                app.notify = lambda msg, **kw: notes.append((msg, kw))  # type: ignore[assignment]
                app.selected_sessions = {"combine-1"}
                pane = app.query_one(CombinePane)
                getattr(pane, action_name)()
                await pilot.pause()

                exports_dir = exports_root / "exports"
                if exports_dir.exists():
                    written.extend(exports_dir.glob(glob))
                # the action also logs a completed Jobs row
                jobs_table = app.query_one(JobsPane).query_one("#jobs-table")
                written.append(jobs_table.row_count)  # type: ignore[arg-type]

    asyncio.run(run())
    assert not any("failed" in m for m, _ in notes), f"action errored: {notes}"
    return written


def test_skill_draft_action_writes_artifact(tmp_path: Path):
    results = _run_pane_action(tmp_path, "action_skill_draft", "agentseq-skill-*.md")
    files = [r for r in results if isinstance(r, Path)]
    job_rows = [r for r in results if isinstance(r, int)]
    assert len(files) == 1
    assert "draft a skill from these sessions" in files[0].read_text()
    assert job_rows and job_rows[0] >= 1


def test_handoff_action_writes_artifact(tmp_path: Path):
    results = _run_pane_action(tmp_path, "action_handoff", "agentseq-handoff-*.md")
    files = [r for r in results if isinstance(r, Path)]
    assert len(files) == 1
    assert "Agentseq Handoff Summary" in files[0].read_text()


def test_combine_action_no_selection_is_a_safe_warning():
    async def run():
        app = AgentSeqApp()
        notes: list[tuple] = []
        with (
            patch("agentseq.tui.app.fetch_live_agents", return_value=[]),
            patch("agentseq.tui.screens.browser.list_sessions", return_value=[]),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                app.notify = lambda msg, **kw: notes.append((msg, kw))  # type: ignore[assignment]
                app.selected_sessions = set()
                pane = app.query_one(CombinePane)
                pane.action_skill_draft()  # must not raise
                await pilot.pause()

        assert notes, "expected a notification"
        msg, kw = notes[-1]
        assert "No sessions selected" in msg
        assert kw.get("severity") == "warning"

    asyncio.run(run())
