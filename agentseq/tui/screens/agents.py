"""Live agents pane — default view."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from textual import on
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import DataTable, Static

from ..live import LiveAgent


class AgentsPane(Container):
    BINDINGS = [
        Binding("r", "resume", "Resume", show=True),
        Binding("f", "focus", "Focus", show=True),
        Binding("s", "smart_attach", "Smart Attach", show=True),
        Binding("enter", "detail", "Detail", show=False),
        Binding("space", "select", "Select", show=True),
        Binding("n", "new_session", "New Session", show=True),
    ]

    def compose(self):
        yield Static("[b]Live Agents[/b]  (auto-refreshes every 3s)", classes="section-header")
        table = DataTable(id="agents-table")
        table.cursor_type = "row"
        table.zebra_stripes = True
        yield table

    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns("Status", "Kind", "Name", "CWD", "Session", "Age", "PID")
        table.focus()

    def refresh_agents(self, agents: list[LiveAgent]):
        """Called by the app when live agents are polled."""
        table = self.query_one(DataTable)
        cursor_row = table.cursor_row
        table.clear()

        for agent in agents:
            age = self._format_age(agent.started_at)
            home = str(Path.home())
            cwd = agent.cwd.replace(home, "~") if agent.cwd else ""
            if len(cwd) > 40:
                cwd = "…" + cwd[-39:]

            status_icon = "● " if agent.status == "busy" else "○ "
            kind_label = "bg" if agent.kind == "background" else "int"
            name = agent.name or "—"
            if len(name) > 35:
                name = name[:34] + "…"
            sid = agent.session_id[:8] if agent.session_id else ""

            selected = agent.session_id in (self.app.selected_sessions or set())
            marker = "✓ " if selected else "  "

            table.add_row(
                f"{status_icon}{agent.status}",
                kind_label,
                f"{marker}{name}",
                cwd,
                sid,
                age,
                str(agent.pid),
                key=agent.session_id,
            )

        if cursor_row < table.row_count:
            table.move_cursor(row=cursor_row)

    def _format_age(self, started_at_ms: int) -> str:
        if not started_at_ms:
            return "—"
        started = dt.datetime.fromtimestamp(started_at_ms / 1000, tz=dt.timezone.utc)
        delta = dt.datetime.now(dt.timezone.utc) - started
        secs = int(delta.total_seconds())
        if secs < 60:
            return f"{secs}s"
        if secs < 3600:
            return f"{secs // 60}m"
        if secs < 86400:
            return f"{secs // 3600}h"
        return f"{secs // 86400}d"

    def _get_selected_agent(self) -> LiveAgent | None:
        table = self.query_one(DataTable)
        if table.cursor_row is None:
            return None
        try:
            row_key_value = list(table.rows.keys())[table.cursor_row]
        except (IndexError, AttributeError):
            return None
        sid = str(row_key_value.value)
        agents = self.app.live_agents or []
        for a in agents:
            if a.session_id == sid:
                return a
        return None

    @on(DataTable.RowSelected, "#agents-table")
    def on_row_selected(self, event: DataTable.RowSelected):
        self.action_detail()

    def action_resume(self):
        agent = self._get_selected_agent()
        if agent:
            self.app.resume_session(agent.session_id, agent.cwd)

    def action_focus(self):
        agent = self._get_selected_agent()
        if agent:
            self.app.focus_session(agent.session_id)

    def action_smart_attach(self):
        agent = self._get_selected_agent()
        if agent:
            self.app.smart_attach(agent.session_id, agent.cwd)

    def action_detail(self):
        agent = self._get_selected_agent()
        if agent:
            self.app.open_detail(agent.session_id)

    def action_select(self):
        agent = self._get_selected_agent()
        if agent:
            self.app.toggle_selection(agent.session_id)

    def action_new_session(self):
        agent = self._get_selected_agent()
        cwd = agent.cwd if agent else "."
        from ...core.launcher import autodetect
        launcher = autodetect()
        ok, msg = launcher.open_new(cwd)
        if ok:
            self.app.notify(f"New session in {cwd}")
        else:
            self.app.notify(f"Failed: {msg}", severity="error")
