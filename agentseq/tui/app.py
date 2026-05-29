"""Main Textual app for agentseq."""
from __future__ import annotations

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Footer, Header, TabbedContent, TabPane

from .live import LiveAgent, fetch_live_agents
from .screens.agents import AgentsPane
from .screens.browser import SessionBrowserPane
from .screens.combine import CombinePane
from .screens.detail import DetailScreen
from .screens.jobs import JobsPane


class AgentSeqApp(App):
    TITLE = "agentseq"
    SUB_TITLE = "Claude session monitor"
    CSS_PATH = "agentseq.tcss"
    BINDINGS = [
        Binding("1", "switch_tab('agents')", "Agents", priority=True),
        Binding("2", "switch_tab('sessions')", "Sessions", priority=True),
        Binding("3", "switch_tab('combine')", "Combine", priority=True),
        Binding("4", "switch_tab('jobs')", "Jobs", priority=True),
        Binding("left_square_bracket", "prev_tab", "Prev Tab", show=False),
        Binding("right_square_bracket", "next_tab", "Next Tab", show=False),
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "show_help", "Help"),
    ]

    TAB_IDS = ["agents", "sessions", "combine", "jobs"]

    selected_sessions: reactive[set[str]] = reactive(set, always_update=True)
    live_agents: reactive[list[LiveAgent]] = reactive(list, always_update=True)

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="main-tabs"):
            with TabPane("Agents [1]", id="agents"):
                yield AgentsPane()
            with TabPane("Sessions [2]", id="sessions"):
                yield SessionBrowserPane()
            with TabPane("Combine [3]", id="combine"):
                yield CombinePane()
            with TabPane("Jobs [4]", id="jobs"):
                yield JobsPane()
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_agents_now()
        self.set_interval(3, self.refresh_agents_now)

    @work(exclusive=True, thread=True)
    def refresh_agents_now(self) -> None:
        agents = fetch_live_agents()
        self.call_from_thread(self._update_agents, agents)

    def _update_agents(self, agents: list[LiveAgent]) -> None:
        self.live_agents = agents
        try:
            pane = self.query_one(AgentsPane)
            pane.refresh_agents(agents)
        except Exception:
            pass

    def action_switch_tab(self, tab_id: str) -> None:
        tabs = self.query_one(TabbedContent)
        tabs.active = tab_id

    def _cycle_tab(self, delta: int) -> None:
        tabs = self.query_one(TabbedContent)
        try:
            idx = self.TAB_IDS.index(tabs.active)
        except ValueError:
            idx = 0
        tabs.active = self.TAB_IDS[(idx + delta) % len(self.TAB_IDS)]

    def action_prev_tab(self) -> None:
        self._cycle_tab(-1)

    def action_next_tab(self) -> None:
        self._cycle_tab(1)

    def action_show_help(self) -> None:
        self.notify(
            "? = help  1-4 = tabs  [ ] = prev/next tab  "
            "j/k = move  gg/G = top/bottom  ctrl+d/ctrl+u = half-page  "
            "Enter = detail  r = resume  s = smart-attach  "
            "Space = select  / = search  q = quit"
        )

    def toggle_selection(self, session_id: str) -> None:
        current = set(self.selected_sessions)
        if session_id in current:
            current.discard(session_id)
        else:
            current.add(session_id)
        self.selected_sessions = current
        # Refresh combine pane
        try:
            pane = self.query_one(CombinePane)
            pane.refresh_selected(current)
        except Exception:
            pass

    def open_detail(self, session_id: str) -> None:
        self.push_screen(DetailScreen(session_id))

    def resume_session(self, session_id: str, cwd: str = "", source: str = "claude") -> None:
        if source != "claude":
            self.notify(f"Resume only supports Claude sessions, got {source}", severity="warning")
            return
        from ..core.launcher import autodetect

        launcher = autodetect()
        ok, msg = launcher.open_new(cwd or ".", session_id=session_id)
        if ok:
            self.notify(f"Resumed {session_id[:8]} via {launcher.name}")
        else:
            self.notify(f"Failed: {msg}", severity="error")

    def smart_attach(self, session_id: str, cwd: str = "", source: str = "claude") -> None:
        if source != "claude":
            self.notify(f"Smart attach only supports Claude sessions, got {source}", severity="warning")
            return
        try:
            from ..menu.processes import find_running

            running = find_running(session_id)
            if running:
                from ..core.launcher import autodetect

                launcher = autodetect()
                ok, msg = launcher.focus_pid(running.pid)
                if ok:
                    self.notify(f"Focused {session_id[:8]} (pid {running.pid})")
                    return
        except Exception:
            pass
        self.resume_session(session_id, cwd, source)

    def focus_session(self, session_id: str, source: str = "claude") -> None:
        if source != "claude":
            self.notify(f"Focus only supports Claude sessions, got {source}", severity="warning")
            return
        try:
            from ..menu.processes import find_running

            running = find_running(session_id)
            if running:
                from ..core.launcher import autodetect

                launcher = autodetect()
                ok, msg = launcher.focus_pid(running.pid)
                if ok:
                    self.notify(f"Focused pid {running.pid}")
                else:
                    self.notify(f"Can't focus: {msg}", severity="warning")
            else:
                self.notify("Session not running", severity="warning")
        except Exception as e:
            self.notify(f"Focus failed: {e}", severity="error")
