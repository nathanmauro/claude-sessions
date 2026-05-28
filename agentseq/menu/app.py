"""rumps-based menu bar: list sessions, smart open/focus on click."""
from __future__ import annotations

import rumps

from ..core import launcher as core_launcher
from ..core import sessions
from ..core.launcher import log_failure
from . import processes

REFRESH_SECS = 15
MAX_RUNNING_ITEMS = 20
MAX_RECENT_ITEMS = 20


class AgentseqApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("AQ", quit_button=None)
        # A menu click always spawns a GUI window; never a multiplexer pane
        # (even if the menubar process was launched from inside tmux/zellij).
        self._launcher = core_launcher.gui_window()
        self._build_menu()
        self._timer = rumps.Timer(self._on_tick, REFRESH_SECS)
        self._timer.start()

    def _on_tick(self, _: rumps.Timer) -> None:
        self._build_menu()

    def _build_menu(self) -> None:
        all_sess = [s for s in sessions.list_sessions() if s.source == "claude"]
        running = processes.list_running()
        running_map = {r.session_id: r for r in running}

        running_sessions = [s for s in all_sess if s.session_id in running_map]
        running_sessions.sort(key=lambda s: s.mtime, reverse=True)
        recent = [s for s in all_sess if s.session_id not in running_map][:MAX_RECENT_ITEMS]

        self.title = f"AQ{len(running_sessions)}" if running_sessions else "AQ"

        self.menu.clear()
        if running_sessions:
            self.menu.add(rumps.MenuItem(f"— Running ({len(running_sessions)}) —", callback=None))
            for s in running_sessions[:MAX_RUNNING_ITEMS]:
                self.menu.add(self._session_item(s, running=True))
            self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("— Recent —", callback=None))

        buckets: dict[str, list[sessions.Session]] = {}
        for s in recent:
            buckets.setdefault(s.project_name, []).append(s)
        # Sort project keys by newest mtime in each bucket (descending).
        ordered_projects = sorted(buckets, key=lambda p: buckets[p][0].mtime, reverse=True)
        for proj in ordered_projects:
            items = buckets[proj]
            parent = rumps.MenuItem(f"{proj} ({len(items)})")
            for s in items:
                parent.add(self._session_item(s, running=False, include_project=False))
            self.menu.add(parent)

        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Refresh", callback=self._refresh))
        self.menu.add(rumps.MenuItem("Quit", callback=rumps.quit_application))

    def _session_item(
        self,
        s: sessions.Session,
        running: bool,
        include_project: bool = True,
    ) -> rumps.MenuItem:
        title = sessions.session_display_title(s, maxlen=48)
        if running:
            age = sessions.age_from_iso(s.end_ts)
            label = f"● {age}  [{s.project_name}] {title}"
        elif include_project:
            label = f"  [{s.project_name}] {title}"
        else:
            label = title
        item = rumps.MenuItem(label, callback=self._on_session_click)
        item._sid = s.session_id  # type: ignore[attr-defined]
        item._cwd = s.cwd  # type: ignore[attr-defined]
        tip = (s.last_prompt or s.first_prompt or "")[:400]
        if tip:
            try:
                item._menuitem.setToolTip_(tip)
            except Exception:
                pass
        return item

    def _on_session_click(self, sender: rumps.MenuItem) -> None:
        sid = getattr(sender, "_sid", None)
        cwd = getattr(sender, "_cwd", None)
        if not sid or not cwd:
            return
        running = processes.find_running(sid)
        if running and running.terminal_pid:
            ok, msg = self._launcher.focus_pid(running.terminal_pid)
            self._report("focus_pid", ok, msg)
            return
        if running and running.terminal_app:
            ok, msg = self._launcher.focus_app(running.terminal_app)
            self._report("focus_app", ok, msg)
            return
        ok, msg = self._launcher.open_new(cwd, sid)
        self._report("open_new", ok, msg)

    def _report(self, context: str, ok: bool, msg: str) -> None:
        if ok:
            return
        log_failure(context, msg)
        try:
            rumps.notification(title="agentseq", subtitle=context, message=msg)
        except Exception:
            pass

    def _refresh(self, _: rumps.MenuItem) -> None:
        self._build_menu()


def main() -> None:
    AgentseqApp().run()


if __name__ == "__main__":
    main()
