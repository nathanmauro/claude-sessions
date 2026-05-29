"""Tests for vim-style navigation in the agentseq TUI.

The TUI is optional (textual is an extra), so skip the whole module when
textual is not installed to keep CI green. There is no pytest-asyncio plugin
in this project, so each test drives textual's async ``run_test`` pilot via
``asyncio.run`` inside an ordinary synchronous test function.
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

pytest.importorskip("textual")

from textual.app import App, ComposeResult  # noqa: E402

from agentseq.tui.app import AgentSeqApp  # noqa: E402
from agentseq.tui.screens.combine import CombinePane  # noqa: E402
from agentseq.tui.vim import VimDataTable, VimRichLog  # noqa: E402


class TableHarness(App):
    """Minimal app hosting a VimDataTable with 20 known rows."""

    def compose(self) -> ComposeResult:
        yield VimDataTable(id="t")

    def on_mount(self) -> None:
        table = self.query_one(VimDataTable)
        table.cursor_type = "row"
        table.add_columns("idx")
        for i in range(20):
            table.add_row(str(i))
        table.focus()


class LogHarness(App):
    """Minimal app hosting a VimRichLog with many lines."""

    def compose(self) -> ComposeResult:
        yield VimRichLog(id="log")

    def on_mount(self) -> None:
        log = self.query_one(VimRichLog)
        # Disable auto-scroll so the log stays pinned at the top after writing;
        # otherwise it sits at the bottom and a broken ``G`` would still "pass".
        log.auto_scroll = False
        for i in range(200):
            log.write(f"line {i}")
        log.focus()


class TwoTableHarness(App):
    """Two VimDataTables, used to exercise focus-change (blur) behavior."""

    def compose(self) -> ComposeResult:
        yield VimDataTable(id="a")
        yield VimDataTable(id="b")

    def on_mount(self) -> None:
        for tid in ("a", "b"):
            table = self.query_one(f"#{tid}", VimDataTable)
            table.cursor_type = "row"
            table.add_columns("idx")
            for i in range(20):
                table.add_row(str(i))
        self.query_one("#a", VimDataTable).focus()


def test_j_moves_cursor_down_and_k_moves_up():
    async def run():
        app = TableHarness()
        async with app.run_test() as pilot:
            table = app.query_one(VimDataTable)
            assert table.cursor_row == 0
            await pilot.press("j")
            assert table.cursor_row == 1
            await pilot.press("j")
            assert table.cursor_row == 2
            await pilot.press("k")
            assert table.cursor_row == 1

    asyncio.run(run())


def test_gg_jumps_to_top():
    async def run():
        app = TableHarness()
        async with app.run_test() as pilot:
            table = app.query_one(VimDataTable)
            table.move_cursor(row=5)
            assert table.cursor_row == 5
            await pilot.press("g")
            await pilot.press("g")
            assert table.cursor_row == 0

    asyncio.run(run())


def test_capital_g_jumps_to_bottom():
    async def run():
        app = TableHarness()
        async with app.run_test() as pilot:
            table = app.query_one(VimDataTable)
            await pilot.press("G")
            assert table.cursor_row == table.row_count - 1

    asyncio.run(run())


def test_ctrl_d_and_ctrl_u_move_half_page():
    async def run():
        app = TableHarness()
        async with app.run_test(size=(80, 12)) as pilot:
            table = app.query_one(VimDataTable)
            table.move_cursor(row=0)
            await pilot.press("ctrl+d")
            after_down = table.cursor_row
            assert after_down > 0
            await pilot.press("ctrl+u")
            assert table.cursor_row < after_down

    asyncio.run(run())


def test_single_g_then_other_key_does_not_reset_wrongly():
    """A lone ``g`` followed by ``j`` should not jump to top; cursor moves down."""

    async def run():
        app = TableHarness()
        async with app.run_test() as pilot:
            table = app.query_one(VimDataTable)
            table.move_cursor(row=5)
            await pilot.press("g")  # pending
            await pilot.press("j")  # cancels pending, moves down
            assert table.cursor_row == 6

    asyncio.run(run())


def test_richlog_vim_scrolling():
    async def run():
        app = LogHarness()
        async with app.run_test(size=(80, 10)) as pilot:
            log = app.query_one(VimRichLog)
            await pilot.pause()
            assert log.max_scroll_y > 0
            # Starts pinned at the top (auto_scroll disabled in the harness).
            assert log.scroll_offset.y == 0

            # G -> bottom (exactly max_scroll_y, not merely > 0).
            await pilot.press("G")
            await pilot.pause()
            assert log.scroll_offset.y == log.max_scroll_y

            # k from the bottom moves up one line.
            await pilot.press("k")
            await pilot.pause()
            assert log.scroll_offset.y == log.max_scroll_y - 1

            # gg -> back to the top.
            await pilot.press("g")
            await pilot.press("g")
            await pilot.pause()
            assert log.scroll_offset.y == 0

            # j from the top moves down one line.
            await pilot.press("j")
            await pilot.pause()
            assert log.scroll_offset.y == 1

            # ctrl+d scrolls a half page (further than the single j line).
            await pilot.press("ctrl+d")
            await pilot.pause()
            half = log.scroll_offset.y
            assert half > 1

            # ctrl+u scrolls back up.
            await pilot.press("ctrl+u")
            await pilot.pause()
            assert log.scroll_offset.y < half

    asyncio.run(run())


def test_pending_g_then_capital_g_goes_to_bottom():
    """A pending ``g`` must not corrupt a following ``G`` into a top-jump."""

    async def run():
        app = TableHarness()
        async with app.run_test() as pilot:
            table = app.query_one(VimDataTable)
            table.move_cursor(row=5)
            await pilot.press("g")  # half-typed gg
            await pilot.press("G")  # cancels pending, jumps to bottom
            assert table.cursor_row == table.row_count - 1

    asyncio.run(run())


def test_pending_g_cleared_on_blur():
    """A half-typed ``gg`` is abandoned when focus leaves the widget.

    Without the on_blur reset, the pending ``g`` survives the focus round-trip
    and the next lone ``g`` spuriously jumps to the top (regression guard).
    """

    async def run():
        app = TwoTableHarness()
        async with app.run_test() as pilot:
            a = app.query_one("#a", VimDataTable)
            b = app.query_one("#b", VimDataTable)
            a.move_cursor(row=8)
            await pilot.press("g")  # pending on A
            b.focus()  # A blurs -> pending must clear
            await pilot.pause()
            a.focus()
            await pilot.pause()
            await pilot.press("g")  # single g; must NOT jump to top
            assert a.cursor_row == 8

    asyncio.run(run())


def test_richlog_can_focus():
    assert VimRichLog.can_focus is True


def test_combine_skill_draft_rebound_to_S_not_k():
    keys = {b.key: b.action for b in CombinePane.BINDINGS}
    assert keys.get("S") == "skill_draft"
    # "k" must NOT be bound to skill_draft (it is now vim "up" on the table).
    assert keys.get("k") != "skill_draft"
    assert "k" not in keys


def test_app_has_bracket_tab_bindings():
    keys = {b.key: b.action for b in AgentSeqApp.BINDINGS}
    assert keys.get("left_square_bracket") == "prev_tab"
    assert keys.get("right_square_bracket") == "next_tab"
    # The original 1-4 tab bindings stay intact.
    assert keys.get("1") == "switch_tab('agents')"
    assert keys.get("4") == "switch_tab('jobs')"


def test_app_tab_cycling_wraps_in_order():
    """next/prev cycle the tab id list with wraparound.

    Each pane focuses its own table on mount, and focusing a widget inside a
    hidden pane re-activates that pane; that pre-existing behavior makes
    ``tabs.active`` drift across event-loop pauses. To test the cycling logic
    deterministically we set ``active`` and call the action synchronously,
    reading the result before yielding control back to the loop.
    """

    async def run():
        from textual.widgets import TabbedContent

        app = AgentSeqApp()
        # Don't shell out to ``claude agents --json`` during a unit test.
        with patch("agentseq.tui.app.fetch_live_agents", return_value=[]):
            async with app.run_test(size=(120, 40)) as pilot:
                tabs = app.query_one(TabbedContent)
                await pilot.pause()

                forward = []
                cur = "agents"
                for _ in range(len(AgentSeqApp.TAB_IDS) + 1):
                    tabs.active = cur
                    app.action_next_tab()
                    cur = tabs.active
                    forward.append(cur)
                assert forward == ["sessions", "combine", "jobs", "agents", "sessions"]

                backward = []
                cur = "agents"
                for _ in range(len(AgentSeqApp.TAB_IDS) + 1):
                    tabs.active = cur
                    app.action_prev_tab()
                    cur = tabs.active
                    backward.append(cur)
                assert backward == ["jobs", "combine", "sessions", "agents", "jobs"]

    asyncio.run(run())
