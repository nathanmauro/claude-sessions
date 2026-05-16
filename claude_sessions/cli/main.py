"""CLI for testing the pipes: list / running / open / focus / smart."""
from __future__ import annotations

import argparse
import json
import sys

from claude_session_menu import launcher, processes, sessions
from claude_session_menu.sessions import age_from_iso


def _cmd_list(args: argparse.Namespace) -> int:
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
    ok, msg = launcher.open_new(sess.cwd, sess.session_id, extra=args.prompt or "")
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
    if running.terminal_pid:
        ok, msg = launcher.focus_pid(running.terminal_pid)
    elif running.terminal_app:
        ok, msg = launcher.focus_app(running.terminal_app)
    else:
        ok, msg = False, "no terminal located in parent chain"
    print(msg)
    return 0 if ok else 1


def _cmd_smart(args: argparse.Namespace) -> int:
    """If session is running, focus; else open new."""
    sess = _find_session(args.session_id)
    if sess is None:
        print(f"no session matched: {args.session_id}", file=sys.stderr)
        return 2
    running = processes.find_running(sess.session_id)
    if running and running.terminal_pid:
        ok, msg = launcher.focus_pid(running.terminal_pid)
        print(f"focus: {msg}")
        return 0 if ok else 1
    if running and running.terminal_app:
        ok, msg = launcher.focus_app(running.terminal_app)
        print(f"focus: {msg}")
        return 0 if ok else 1
    ok, msg = launcher.open_new(sess.cwd, sess.session_id)
    print(f"open: {msg}")
    return 0 if ok else 1


def _find_session(needle: str):
    """Match by full session_id or unique prefix."""
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
    p = argparse.ArgumentParser(prog="csm", description="Claude session menu CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="list known sessions")
    p_list.add_argument("--json", action="store_true")
    p_list.add_argument("--limit", type=int, default=50)
    p_list.set_defaults(func=_cmd_list)

    p_run = sub.add_parser("running", help="list active claude --resume processes")
    p_run.add_argument("--json", action="store_true")
    p_run.set_defaults(func=_cmd_running)

    p_open = sub.add_parser("open", help="open session in new Ghostty window")
    p_open.add_argument("session_id")
    p_open.add_argument("--prompt", default="")
    p_open.set_defaults(func=_cmd_open)

    p_focus = sub.add_parser("focus", help="focus the terminal running this session")
    p_focus.add_argument("session_id")
    p_focus.set_defaults(func=_cmd_focus)

    p_smart = sub.add_parser("smart", help="focus if running, else open new")
    p_smart.add_argument("session_id")
    p_smart.set_defaults(func=_cmd_smart)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
