"""Unified CLI for claude-sessions: ls / running / open / focus / smart / menu / dash / index."""
from __future__ import annotations

import argparse
import json
import sys

from ..core import launcher as core_launcher
from ..core import sessions
from ..core.sessions import age_from_iso
from ..menu import processes


def _get_launcher(args: argparse.Namespace) -> core_launcher.Launcher:
    """Honor --launcher flag; otherwise autodetect from $TMUX / $ZELLIJ / Ghostty."""
    name = getattr(args, "launcher", None)
    if name:
        return core_launcher.get_launcher(name)
    return core_launcher.autodetect()


def _cmd_ls(args: argparse.Namespace) -> int:
    items = sessions.list_sessions()
    running_ids = {r.session_id for r in processes.list_running()}
    if args.json:
        out = []
        for s in items[: args.limit]:
            d = s.to_dict()
            d["running"] = s.session_id in running_ids
            d["display"] = sessions.session_display_title(s)
            out.append(d)
        print(json.dumps(out, indent=2))
        return 0
    print(f"{'AGE':>5}  {'RUN':<3}  {'PROJECT':<24}  {'TITLE':<60}  SESSION_ID")
    for s in items[: args.limit]:
        age = age_from_iso(s.end_ts)
        run = "yes" if s.session_id in running_ids else ""
        proj = s.project_name[:24]
        title = sessions.session_display_title(s, maxlen=60)
        print(f"{age:>5}  {run:<3}  {proj:<24}  {title:<60}  {s.session_id}")
    return 0


def _cmd_running(args: argparse.Namespace) -> int:
    items = processes.list_running()
    if args.json:
        print(json.dumps([r.to_dict() for r in items], indent=2))
        return 0
    if not items:
        print("(no running claude --resume sessions)")
        return 0
    print(f"{'PID':>6}  {'TERM':<10}  {'TERM_PID':>8}  SESSION_ID")
    for r in items:
        term = r.terminal_app or "?"
        tpid = str(r.terminal_pid) if r.terminal_pid else "-"
        print(f"{r.pid:>6}  {term:<10}  {tpid:>8}  {r.session_id}")
    return 0


def _cmd_open(args: argparse.Namespace) -> int:
    sess = _find_session(args.session_id)
    if sess is None:
        print(f"no session matched: {args.session_id}", file=sys.stderr)
        return 2
    lnc = _get_launcher(args)
    ok, msg = lnc.open_new(sess.cwd, sess.session_id, extra=args.prompt or "")
    print(msg)
    return 0 if ok else 1


def _cmd_focus(args: argparse.Namespace) -> int:
    sess = _find_session(args.session_id)
    if sess is None:
        print(f"no session matched: {args.session_id}", file=sys.stderr)
        return 2
    running = processes.find_running(sess.session_id)
    if running is None:
        print(f"session {sess.session_id[:8]} is not running", file=sys.stderr)
        return 3
    lnc = _get_launcher(args)
    if running.terminal_pid:
        ok, msg = lnc.focus_pid(running.terminal_pid)
    elif running.terminal_app:
        ok, msg = lnc.focus_app(running.terminal_app)
    else:
        ok, msg = False, "no terminal located in parent chain"
    print(msg)
    return 0 if ok else 1


def _cmd_smart(args: argparse.Namespace) -> int:
    sess = _find_session(args.session_id)
    if sess is None:
        print(f"no session matched: {args.session_id}", file=sys.stderr)
        return 2
    lnc = _get_launcher(args)
    running = processes.find_running(sess.session_id)
    if running and running.terminal_pid:
        ok, msg = lnc.focus_pid(running.terminal_pid)
        print(f"focus: {msg}")
        return 0 if ok else 1
    if running and running.terminal_app:
        ok, msg = lnc.focus_app(running.terminal_app)
        print(f"focus: {msg}")
        return 0 if ok else 1
    ok, msg = lnc.open_new(sess.cwd, sess.session_id)
    print(f"open: {msg}")
    return 0 if ok else 1


def _cmd_menu(_: argparse.Namespace) -> int:
    try:
        from ..menu.app import main as menu_main
    except ImportError as e:
        print(f"menu extra not installed: {e}", file=sys.stderr)
        print("install with: pip install 'claude-sessions[menu]'", file=sys.stderr)
        return 5
    menu_main()
    return 0


def _cmd_dash(args: argparse.Namespace) -> int:
    try:
        import uvicorn
        from ..dash.server import app
        from ..core.config import HOST, PORT
    except ImportError as e:
        print(f"dash extra not installed: {e}", file=sys.stderr)
        print("install with: pip install 'claude-sessions[dash]'", file=sys.stderr)
        return 5
    host = args.host or HOST
    port = args.port or PORT
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


def _cmd_index(args: argparse.Namespace) -> int:
    from ..core import db
    from ..core.config import PROJECTS_DIR
    changed = db.index_all(PROJECTS_DIR)
    print(f"indexed: {len(changed)} sessions changed")
    if args.verbose:
        for sid in changed:
            print(f"  {sid}")
    return 0


def _find_session(needle: str):
    items = sessions.list_sessions()
    exact = [s for s in items if s.session_id == needle]
    if exact:
        return exact[0]
    prefix = [s for s in items if s.session_id.startswith(needle)]
    if len(prefix) == 1:
        return prefix[0]
    if len(prefix) > 1:
        print(f"ambiguous prefix '{needle}' matches {len(prefix)} sessions", file=sys.stderr)
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="claude-sessions",
        description="Browse, resume, and visualize Claude Code sessions.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_ls = sub.add_parser("ls", help="list known sessions")
    p_ls.add_argument("--json", action="store_true")
    p_ls.add_argument("--limit", type=int, default=50)
    p_ls.set_defaults(func=_cmd_ls)

    p_run = sub.add_parser("running", help="list active claude --resume processes")
    p_run.add_argument("--json", action="store_true")
    p_run.set_defaults(func=_cmd_running)

    launcher_choices = ["ghostty", "tmux", "zellij", "generic"]
    launcher_help = (
        "override launcher backend (default: autodetect $ZELLIJ / $TMUX / Ghostty.app; "
        "also honors $CLAUDE_SESSIONS_LAUNCHER env var)"
    )

    p_open = sub.add_parser("open", help="open session in a new terminal window or pane")
    p_open.add_argument("session_id")
    p_open.add_argument("--prompt", default="")
    p_open.add_argument("--launcher", choices=launcher_choices, default=None, help=launcher_help)
    p_open.set_defaults(func=_cmd_open)

    p_focus = sub.add_parser("focus", help="focus terminal running this session")
    p_focus.add_argument("session_id")
    p_focus.add_argument("--launcher", choices=launcher_choices, default=None, help=launcher_help)
    p_focus.set_defaults(func=_cmd_focus)

    p_smart = sub.add_parser("smart", help="focus if running, else open new")
    p_smart.add_argument("session_id")
    p_smart.add_argument("--launcher", choices=launcher_choices, default=None, help=launcher_help)
    p_smart.set_defaults(func=_cmd_smart)

    p_menu = sub.add_parser("menu", help="launch macOS menubar app (requires [menu] extra)")
    p_menu.set_defaults(func=_cmd_menu)

    p_dash = sub.add_parser("dash", help="launch web dashboard (requires [dash] extra)")
    p_dash.add_argument("--host", default=None)
    p_dash.add_argument("--port", type=int, default=None)
    p_dash.set_defaults(func=_cmd_dash)

    p_index = sub.add_parser("index", help="refresh SQLite session index")
    p_index.add_argument("-v", "--verbose", action="store_true")
    p_index.set_defaults(func=_cmd_index)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
