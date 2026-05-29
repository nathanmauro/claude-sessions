"""TUI screen tests: smoke, detail screen, search.

textual is an optional extra, so skip the whole module when it is not
installed (keeps a base/CI install without ``[tui]`` green). There is no
pytest-asyncio plugin here, so each test drives textual's async ``run_test``
pilot via ``asyncio.run`` inside an ordinary sync test — matching
``test_tui_vim.py``.

The TUI loads data through threaded ``@work`` workers; tests wait on
``app.workers.wait_for_complete()`` plus a pilot pause so the
``call_from_thread`` UI update has been pumped before asserting.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("textual")

from textual.widgets import DataTable, TabbedContent, TabPane  # noqa: E402

from agentseq.core.models import SearchResult, Session  # noqa: E402
from agentseq.tui.app import AgentSeqApp  # noqa: E402
from agentseq.tui.live import LiveAgent  # noqa: E402
from agentseq.tui.screens.agents import AgentsPane  # noqa: E402
from agentseq.tui.screens.browser import SessionBrowserPane  # noqa: E402
from agentseq.tui.screens.detail import DetailScreen  # noqa: E402

CLAUDE_TRANSCRIPT = [
    {
        "type": "user",
        "timestamp": "2026-05-20T09:00:00Z",
        "message": {"content": "investigate the failing test"},
    },
    {
        "type": "assistant",
        "timestamp": "2026-05-20T09:00:01Z",
        "message": {"content": [{"type": "text", "text": "looking into it now"}]},
    },
]


def _write_claude_session(projects_dir: Path, sid: str, cwd: str, lines: list[dict]) -> Path:
    project_slug = "-" + cwd.strip("/").replace("/", "-")
    path = projects_dir / project_slug / f"{sid}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
    return path


def _session(sid: str, title: str, cwd: str) -> Session:
    return Session(
        session_id=sid,
        project_dir="-" + cwd.strip("/").replace("/", "-"),
        cwd=cwd,
        path=Path(f"{cwd}/{sid}.jsonl"),
        title=title,
        first_prompt=title,
        last_prompt=title,
        source="claude",
    )


def test_app_mounts_all_four_tabs_and_agents_table_accepts_data():
    async def run():
        app = AgentSeqApp()
        with (
            patch("agentseq.tui.app.fetch_live_agents", return_value=[]),
            patch("agentseq.tui.screens.browser.list_sessions", return_value=[]),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                # let the on-mount agents/sessions workers settle first
                await app.workers.wait_for_complete()
                await pilot.pause()

                assert app.query_one(TabbedContent) is not None
                pane_ids = {p.id for p in app.query(TabPane)}
                assert {"agents", "sessions", "combine", "jobs"} <= pane_ids

                agent = LiveAgent(
                    pid=4242,
                    cwd="/tmp/x",
                    kind="interactive",
                    started_at=0,
                    session_id="abc12345",
                    name="demo",
                    status="busy",
                )
                app._update_agents([agent])
                await pilot.pause()

                table = app.query_one(AgentsPane).query_one(DataTable)
                assert table.row_count == 1

    asyncio.run(run())


def test_detail_screen_loads_transcript_and_toggles_raw(tmp_path: Path):
    projects_dir = tmp_path / "claude-projects"
    fixture = _write_claude_session(projects_dir, "detail-1", "/tmp/proj", CLAUDE_TRANSCRIPT)

    # the binding is wired (independent of focus routing)
    assert any(b.key == "m" and b.action == "toggle_raw" for b in DetailScreen.BINDINGS)

    async def run():
        app = AgentSeqApp()
        with (
            patch("agentseq.tui.app.fetch_live_agents", return_value=[]),
            patch("agentseq.tui.screens.browser.list_sessions", return_value=[]),
            patch(
                "agentseq.core.sessions.find_session_path",
                return_value=("claude", fixture),
            ),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                app.push_screen(DetailScreen("detail-1"))
                await pilot.pause()
                await app.workers.wait_for_complete()
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, DetailScreen)
                assert screen._session is not None
                assert len(screen._session.all_messages) == 2

                log = screen.query_one("#detail-transcript")
                assert log.lines  # transcript rendered something

                assert screen._show_raw is False
                screen.action_toggle_raw()
                await pilot.pause()
                assert screen._show_raw is True
                assert log.lines  # raw JSON rendered

                screen.action_toggle_raw()
                await pilot.pause()
                assert screen._show_raw is False

    asyncio.run(run())


def test_search_uses_fts_then_falls_back_to_substring():
    s_alpha = _session("alpha-1", "alpha project", "/tmp/a")
    s_beta = _session("beta-1", "beta project", "/tmp/b")
    fts_hit = SearchResult(
        session_id="fts-99",
        title="FTS HIT",
        snippet="snippet",
        cwd="/tmp/f",
        source="claude",
        date="2026-05-01",
    )

    async def run():
        app = AgentSeqApp()
        with (
            patch("agentseq.tui.app.fetch_live_agents", return_value=[]),
            patch("agentseq.tui.screens.browser.list_sessions", return_value=[]),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await app.workers.wait_for_complete()
                await pilot.pause()

                pane = app.query_one(SessionBrowserPane)
                pane._sessions = [s_alpha, s_beta]

                # FTS path: db.search returns results -> they render verbatim.
                with patch("agentseq.core.db.search", return_value=[fts_hit]):
                    pane.do_search("anything")
                    await app.workers.wait_for_complete()
                    await pilot.pause()
                    assert "fts-99" in pane._visible_meta
                    assert "alpha-1" not in pane._visible_meta

                # Fallback: db.search raises -> substring filter over _sessions.
                with patch("agentseq.core.db.search", side_effect=RuntimeError("no fts")):
                    pane.do_search("alpha")
                    await app.workers.wait_for_complete()
                    await pilot.pause()
                    assert "alpha-1" in pane._visible_meta
                    assert "beta-1" not in pane._visible_meta

    asyncio.run(run())
