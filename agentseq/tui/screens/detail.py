"""Session detail — pushed screen."""
from __future__ import annotations
import json
from pathlib import Path
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Static, RichLog, DataTable, Header, Footer
from textual.containers import Container, Vertical, Horizontal
from textual.binding import Binding
from textual import work

class DetailScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
        Binding("r", "resume", "Resume"),
        Binding("s", "smart_attach", "Smart Attach"),
        Binding("m", "toggle_raw", "Raw JSON"),
        Binding("space", "select", "Select"),
    ]

    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id
        self._session = None
        self._show_raw = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"Loading session {self.session_id[:8]}…", id="detail-loading")
        with Vertical(id="detail-content"):
            yield Static("", id="detail-meta", classes="detail-meta")
            yield RichLog(id="detail-transcript", classes="detail-transcript", wrap=True, highlight=True, markup=True)
            yield DataTable(id="detail-tasks", classes="detail-tasks")
        yield Footer()

    def on_mount(self):
        self.query_one("#detail-content").display = False
        tasks_table = self.query_one("#detail-tasks", DataTable)
        tasks_table.add_columns("Status", "Subject", "Description")
        tasks_table.cursor_type = "row"
        self.load_session()

    @work(thread=True)
    def load_session(self):
        session = None
        from ...core.config import PROJECTS_DIR
        for jsonl in PROJECTS_DIR.rglob("*.jsonl"):
            if jsonl.stem == self.session_id:
                try:
                    from ...core.parser import parse_session
                    session = parse_session(jsonl)
                except Exception:
                    pass
                break
        self.app.call_from_thread(self._render_session, session)

    def _render_session(self, session):
        self._session = session
        loading = self.query_one("#detail-loading", Static)
        content = self.query_one("#detail-content")

        if session is None:
            loading.update(f"[red]Session {self.session_id[:8]} not found[/red]")
            return

        loading.display = False
        content.display = True

        # Metadata panel
        meta = self.query_one("#detail-meta", Static)

        is_running = False
        try:
            from ...menu.processes import find_running
            running = find_running(self.session_id)
            is_running = running is not None
        except Exception:
            pass

        def fmt_tokens(n: int) -> str:
            if n >= 1_000_000:
                return f"{n / 1_000_000:.1f}M"
            if n >= 1_000:
                return f"{n / 1_000:.1f}K"
            return str(n)

        status = "[green]● Running[/green]" if is_running else "[dim]○ Stopped[/dim]"
        cwd = session.cwd or "—"
        title = session.title or "Untitled"
        start = str(session.start_ts)[:19] if session.start_ts else "—"
        end = str(session.end_ts)[:19] if session.end_ts else "—"

        meta_text = (
            f"[bold]{title}[/bold]\n"
            f"Session: {self.session_id}  {status}\n"
            f"CWD: {cwd}\n"
            f"Started: {start}  Ended: {end}\n"
            f"Messages: {session.user_msg_count}  "
            f"Tokens: in={fmt_tokens(session.input_tokens)} out={fmt_tokens(session.output_tokens)} "
            f"cache={fmt_tokens(session.cache_read_tokens)} billable={fmt_tokens(session.billable_tokens)}"
        )
        meta.update(meta_text)

        # Transcript
        log = self.query_one("#detail-transcript", RichLog)
        log.clear()
        for role, text in session.all_messages[:200]:
            if role == "user":
                log.write(f"[bold cyan]▶ User:[/bold cyan]")
            elif role == "assistant":
                log.write(f"[bold green]◀ Assistant:[/bold green]")
            else:
                log.write(f"[dim]{role}:[/dim]")
            display_text = text[:2000]
            if len(text) > 2000:
                display_text += f"\n[dim]… ({len(text) - 2000} chars truncated)[/dim]"
            log.write(display_text)
            log.write("")

        if not session.all_messages:
            log.write("[dim]No messages in transcript[/dim]")

        # Tasks
        tasks_table = self.query_one("#detail-tasks", DataTable)
        tasks_table.clear()
        for task in session.tasks.values():
            status_icon = {"completed": "✓", "in_progress": "⟳", "pending": "○"}.get(task.status, "?")
            tasks_table.add_row(
                f"{status_icon} {task.status}",
                task.subject[:60],
                (task.description or "")[:80],
            )
        if not session.tasks:
            tasks_table.add_row("—", "No tasks", "")

    def action_pop_screen(self):
        self.app.pop_screen()

    def action_resume(self):
        if self._session:
            self.app.resume_session(self.session_id, self._session.cwd)

    def action_smart_attach(self):
        if self._session:
            self.app.smart_attach(self.session_id, self._session.cwd)

    def action_select(self):
        self.app.toggle_selection(self.session_id)

    def action_toggle_raw(self):
        if not self._session:
            return
        log = self.query_one("#detail-transcript", RichLog)
        log.clear()
        self._show_raw = not self._show_raw
        if self._show_raw:
            from ...core.config import PROJECTS_DIR
            for jsonl in PROJECTS_DIR.rglob("*.jsonl"):
                if jsonl.stem == self.session_id:
                    try:
                        with open(jsonl) as f:
                            for i, line in enumerate(f):
                                if i >= 100:
                                    log.write(f"[dim]… truncated at 100 lines[/dim]")
                                    break
                                try:
                                    obj = json.loads(line)
                                    log.write(json.dumps(obj, indent=2)[:500])
                                except json.JSONDecodeError:
                                    log.write(f"[red]Invalid JSON line {i}[/red]")
                                log.write("")
                    except Exception as e:
                        log.write(f"[red]Error reading file: {e}[/red]")
                    break
        else:
            self._render_session(self._session)
