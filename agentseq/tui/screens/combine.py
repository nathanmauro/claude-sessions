"""Combine workspace for multi-selected sessions."""
from __future__ import annotations

from pathlib import Path

from textual.binding import Binding
from textual.containers import Container
from textual.widgets import DataTable, Static

from ..vim import VimDataTable


class CombinePane(Container):
    BINDINGS = [
        Binding("x", "remove_selected", "Remove"),
        Binding("e", "export", "Export"),
        Binding("S", "skill_draft", "Skill Draft"),
        Binding("h", "handoff", "Handoff Summary"),
        Binding("c", "clear_all", "Clear All"),
    ]

    def compose(self):
        yield Static("[b]Combine Workspace[/b]  (Space to select sessions in other tabs)", classes="section-header")
        yield Static("No sessions selected", id="combine-stats", classes="combine-stats")
        table = VimDataTable(id="combine-table", classes="combine-list")
        table.cursor_type = "row"
        table.zebra_stripes = True
        yield table

    def on_mount(self):
        table = self.query_one("#combine-table", DataTable)
        table.add_columns("Source", "Session", "Title", "CWD", "Messages", "Tokens")

    def refresh_selected(self, selected: set[str]):
        """Called by app when selection changes."""
        from ...core.sessions import list_sessions, session_display_title

        table = self.query_one("#combine-table", DataTable)
        table.clear()

        if not selected:
            self.query_one("#combine-stats", Static).update("No sessions selected")
            return

        all_sessions = list_sessions()
        matched = [s for s in all_sessions if s.session_id in selected]

        total_msgs = 0
        cwds = set()
        for s in matched:
            title = session_display_title(s, maxlen=40)
            cwd_short = Path(s.cwd).name if s.cwd else "—"
            msgs = s.user_msg_count or 0
            total_msgs += msgs
            cwds.add(s.cwd or "unknown")
            table.add_row(
                s.source,
                s.session_id[:8],
                title,
                cwd_short,
                str(msgs),
                "—",
                key=s.session_id,
            )

        stats = (
            f"[b]{len(matched)}[/b] sessions selected  |  "
            f"[b]{total_msgs}[/b] total messages  |  "
            f"[b]{len(cwds)}[/b] unique project(s)"
        )
        self.query_one("#combine-stats", Static).update(stats)

    def _get_cursor_sid(self) -> str | None:
        table = self.query_one("#combine-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            return None
        try:
            row_key = list(table.rows.keys())[table.cursor_row]
            return str(row_key.value)
        except (IndexError, AttributeError):
            return None

    def action_remove_selected(self):
        sid = self._get_cursor_sid()
        if sid:
            self.app.toggle_selection(sid)

    def action_clear_all(self):
        self.app.selected_sessions = set()
        self.refresh_selected(set())

    def action_export(self):
        from ...core.export import export_sessions_markdown

        self._run_export("Export", export_sessions_markdown)

    def _run_export(self, label: str, export_fn):
        """Shared driver for the Combine export actions (export/skill/handoff)."""
        selected = self.app.selected_sessions
        if not selected:
            self.app.notify("No sessions selected", severity="warning")
            return
        try:
            from .jobs import JobsPane

            selected_ids = sorted(selected)
            result = export_fn(selected_ids)
            # Report what actually landed in the artifact, not the raw selection
            # (some ids may be unresolvable/unparsable and excluded).
            written_ids = [sid for sid in selected_ids if sid not in set(result.missing)]
            try:
                jobs = self.app.query_one(JobsPane)
                jobs.add_job(label, written_ids, str(result.path), status="Complete")
            except Exception:
                pass
            note = f"{label}: {result.written} sessions → {result.path}"
            if result.missing:
                note += f"  ({len(result.missing)} unresolved)"
            self.app.notify(note)
        except Exception as e:
            self.app.notify(f"{label} failed: {e}", severity="error")

    def action_skill_draft(self):
        from ...core.export import export_skill_draft

        self._run_export("Skill draft", export_skill_draft)

    def action_handoff(self):
        from ...core.export import export_handoff_summary

        self._run_export("Handoff summary", export_handoff_summary)
