"""Export and generation jobs queue."""
from __future__ import annotations

from textual.binding import Binding
from textual.containers import Container
from textual.widgets import DataTable, Static


class JobsPane(Container):
    BINDINGS = [
        Binding("enter", "view_output", "View Output"),
        Binding("r", "retry", "Retry"),
        Binding("d", "delete", "Delete"),
    ]

    def compose(self):
        yield Static("[b]Jobs & Exports[/b]", classes="section-header")
        table = DataTable(id="jobs-table")
        table.cursor_type = "row"
        table.zebra_stripes = True
        yield table
        yield Static("[dim]No jobs yet. Use [b]e[/b]xport, [b]k[/b] skill draft, or [b]h[/b] handoff from the Combine tab.[/dim]",
                     id="jobs-empty", classes="empty-state")

    def on_mount(self):
        table = self.query_one("#jobs-table", DataTable)
        table.add_columns("Status", "Type", "Sessions", "Output", "Created")
        table.display = False

    def add_job(
        self,
        job_type: str,
        session_ids: list[str],
        output_path: str = "",
        status: str = "Complete",
    ):
        table = self.query_one("#jobs-table", DataTable)
        table.display = True
        self.query_one("#jobs-empty").display = False
        table.add_row(
            status,
            job_type,
            str(len(session_ids)),
            output_path or "—",
            "just now",
        )

    def action_view_output(self):
        self.app.notify("Job output viewer — coming soon")

    def action_retry(self):
        self.app.notify("Retry — coming soon")

    def action_delete(self):
        self.app.notify("Delete — coming soon")
