"""Session browser with full-text search."""
from __future__ import annotations

from pathlib import Path

from textual import on, work
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import DataTable, Input

from ...core.sessions import age_from_iso, list_sessions, session_display_title
from ..vim import VimDataTable


class SessionBrowserPane(Container):
    BINDINGS = [
        Binding("slash", "focus_search", "Search", show=True),
        Binding("enter", "detail", "Detail", show=False),
        Binding("space", "select", "Select", show=True),
        Binding("r", "resume", "Resume", show=True),
        Binding("s", "smart_attach", "Smart Attach", show=True),
        Binding("escape", "clear_search", "Clear Search"),
    ]

    def __init__(self):
        super().__init__()
        self._sessions = []
        self._search_query = ""
        self._visible_meta: dict[str, tuple[str, str]] = {}

    def compose(self):
        with Horizontal(classes="search-bar"):
            yield Input(placeholder="Search sessions (/ to focus)…", id="search-input")
        table = VimDataTable(id="sessions-table")
        table.cursor_type = "row"
        table.zebra_stripes = True
        yield table

    def on_mount(self):
        table = self.query_one("#sessions-table", DataTable)
        table.add_columns("Source", "Date", "Title", "Project", "Msgs", "Last Prompt")
        table.focus()
        self.load_sessions()

    @work(thread=True)
    def load_sessions(self):
        sessions = list_sessions()
        self.app.call_from_thread(self._populate_table, sessions)

    def _populate_table(self, sessions):
        self._sessions = sessions
        self._visible_meta = {}
        table = self.query_one("#sessions-table", DataTable)
        table.clear()

        for s in sessions[:500]:
            date = age_from_iso(s.start_ts) if s.start_ts else "—"
            title = session_display_title(s, maxlen=45)
            project = Path(s.cwd).name if s.cwd else "—"
            source = s.source
            msgs = str(s.user_msg_count) if s.user_msg_count else "—"
            last = (s.last_prompt or "")[:50]
            if len(last) == 50:
                last += "…"

            selected = s.session_id in (self.app.selected_sessions or set())
            marker = "✓ " if selected else "  "
            self._visible_meta[s.session_id] = (s.cwd or ".", s.source)

            table.add_row(source, date, f"{marker}{title}", project, msgs, last, key=s.session_id)

    @on(Input.Changed, "#search-input")
    def on_search_changed(self, event: Input.Changed):
        self._search_query = event.value.strip()
        if not self._search_query:
            self._populate_table(self._sessions)
            return
        self.do_search(self._search_query)

    @work(thread=True)
    def do_search(self, query: str):
        try:
            from ...core.db import search
            results = search(query, limit=100)
            self.app.call_from_thread(self._show_search_results, results)
        except Exception:
            q = query.lower()
            filtered = [s for s in self._sessions if q in (s.title or "").lower()
                       or q in (s.first_prompt or "").lower()
                       or q in (s.last_prompt or "").lower()
                       or q in (s.cwd or "").lower()]
            self.app.call_from_thread(self._populate_table, filtered)

    def _show_search_results(self, results):
        table = self.query_one("#sessions-table", DataTable)
        table.clear()
        self._visible_meta = {}
        for r in results:
            snippet = (r.snippet or "")[:50]
            if len(snippet) == 50:
                snippet += "…"
            self._visible_meta[r.session_id] = (r.cwd or ".", r.source)
            table.add_row(
                r.source,
                r.date or "—",
                r.title or "—",
                Path(r.cwd).name if r.cwd else "—",
                "—",
                snippet,
                key=r.session_id,
            )

    def _get_selected_session_id(self) -> str | None:
        table = self.query_one("#sessions-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            return None
        try:
            row_key = list(table.rows.keys())[table.cursor_row]
            return str(row_key.value)
        except (IndexError, AttributeError):
            return None

    def _get_session_cwd(self, session_id: str) -> str:
        if session_id in self._visible_meta:
            return self._visible_meta[session_id][0]
        for s in self._sessions:
            if s.session_id == session_id:
                return s.cwd or "."
        return "."

    def _get_session_source(self, session_id: str) -> str:
        if session_id in self._visible_meta:
            return self._visible_meta[session_id][1]
        for s in self._sessions:
            if s.session_id == session_id:
                return s.source
        return "claude"

    @on(DataTable.RowSelected, "#sessions-table")
    def on_row_selected(self, event: DataTable.RowSelected):
        self.action_detail()

    def action_focus_search(self):
        self.query_one("#search-input", Input).focus()

    def action_clear_search(self):
        inp = self.query_one("#search-input", Input)
        inp.value = ""
        self._populate_table(self._sessions)
        self.query_one("#sessions-table", DataTable).focus()

    def action_detail(self):
        sid = self._get_selected_session_id()
        if sid:
            self.app.open_detail(sid)

    def action_select(self):
        sid = self._get_selected_session_id()
        if sid:
            self.app.toggle_selection(sid)
            self._populate_table(self._sessions)

    def action_resume(self):
        sid = self._get_selected_session_id()
        if sid:
            self.app.resume_session(
                sid,
                self._get_session_cwd(sid),
                self._get_session_source(sid),
            )

    def action_smart_attach(self):
        sid = self._get_selected_session_id()
        if sid:
            self.app.smart_attach(
                sid,
                self._get_session_cwd(sid),
                self._get_session_source(sid),
            )
