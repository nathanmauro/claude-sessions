"""Tests for the show + pick CLI subcommands."""
from __future__ import annotations

import argparse
import json
import subprocess

import pytest

from claude_sessions.cli import main as cli
from claude_sessions.core.sessions import Session


def _make_session(**overrides) -> Session:
    defaults = dict(
        session_id="abc123def-4567-89ab-cdef-0123456789ab",
        cwd="/Users/nathan/Developer/proj/foo",
        project_dir="-Users-nathan-Developer-proj-foo",
        path="/tmp/session.jsonl",
        mtime=1700000000.0,
        size=1024,
        start_ts="2026-05-18T10:00:00+00:00",
        end_ts="2026-05-18T11:00:00+00:00",
        title="Refactor the thing",
        first_prompt="how do i do the thing",
        last_prompt="ok that worked, thanks",
        user_msg_count=7,
    )
    defaults.update(overrides)
    return Session(**defaults)


@pytest.fixture
def one_session(monkeypatch):
    sess = _make_session()
    monkeypatch.setattr(cli.sessions, "list_sessions", lambda: [sess])
    return sess


# ------------------------------- show ------------------------------


def test_show_full_includes_metadata_and_prompts(capsys, one_session):
    rc = cli._cmd_show(
        argparse.Namespace(session_id=one_session.session_id, json=False, short=False)
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert one_session.session_id in out
    assert one_session.cwd in out
    assert "Refactor the thing" in out
    assert "first prompt:" in out
    assert "last prompt:" in out
    assert "how do i do the thing" in out
    assert "ok that worked, thanks" in out


def test_show_omits_duplicate_last_prompt(capsys, monkeypatch):
    sess = _make_session(last_prompt="how do i do the thing")  # same as first
    monkeypatch.setattr(cli.sessions, "list_sessions", lambda: [sess])
    rc = cli._cmd_show(
        argparse.Namespace(session_id=sess.session_id, json=False, short=False)
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "first prompt:" in out
    assert "last prompt:" not in out  # collapsed since identical


def test_show_short_is_compact(capsys, one_session):
    rc = cli._cmd_show(
        argparse.Namespace(session_id=one_session.session_id, json=False, short=True)
    )
    out = capsys.readouterr().out
    assert rc == 0
    lines = out.strip().splitlines()
    # 4 metadata lines + blank + last prompt = 6 lines (short prompt fits one line)
    assert len(lines) <= 8
    assert "project:" in lines[0]
    assert "ok that worked" in out
    # The expensive full session_id should NOT appear in --short mode
    assert one_session.session_id not in out


def test_show_json_dumps_full_dict(capsys, one_session):
    rc = cli._cmd_show(
        argparse.Namespace(session_id=one_session.session_id, json=True, short=False)
    )
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["session_id"] == one_session.session_id
    assert payload["cwd"] == one_session.cwd


def test_show_unknown_session_returns_2(capsys, monkeypatch):
    monkeypatch.setattr(cli.sessions, "list_sessions", lambda: [])
    rc = cli._cmd_show(
        argparse.Namespace(session_id="deadbeef", json=False, short=False)
    )
    assert rc == 2
    assert "no session matched" in capsys.readouterr().err


def test_show_prefix_match(capsys, one_session):
    rc = cli._cmd_show(
        argparse.Namespace(session_id="abc123", json=False, short=False)
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert one_session.session_id in out


# ------------------------------- pick ------------------------------


@pytest.fixture
def two_sessions(monkeypatch):
    a = _make_session(
        session_id="aaaaaaaa-1111-2222-3333-444444444444",
        cwd="/Users/nathan/Developer/proj/alpha",
        title="alpha session",
    )
    b = _make_session(
        session_id="bbbbbbbb-1111-2222-3333-444444444444",
        cwd="/Users/nathan/Developer/proj/beta",
        title="beta session",
    )
    monkeypatch.setattr(cli.sessions, "list_sessions", lambda: [a, b])
    return a, b


def test_pick_builds_fzf_argv_and_prints_chosen_sid(monkeypatch, capsys, two_sessions):
    a, _b = two_sessions
    captured = {}

    def fake_run(args, input=None, capture_output=None, text=None, **_kwargs):
        captured["args"] = args
        captured["input"] = input
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=f"{a.session_id}\tproject\ttitle\n",
            stderr="",
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    rc = cli._cmd_pick(argparse.Namespace(exec="none", launcher=None))
    assert rc == 0
    assert capsys.readouterr().out.strip() == a.session_id
    argv = captured["args"]
    assert argv[0] == "fzf"
    assert "--delimiter=\t" in argv
    assert "--with-nth=2,3" in argv
    assert "--preview" in argv
    assert "show --short {1}" in argv[argv.index("--preview") + 1]
    # Confirm both sessions made it into stdin
    assert a.session_id in captured["input"]
    assert "alpha session" in captured["input"]


def test_pick_handles_user_cancel(monkeypatch, capsys, two_sessions):
    def fake_run(args, **_kwargs):
        return subprocess.CompletedProcess(
            args=args, returncode=130, stdout="", stderr=""
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    rc = cli._cmd_pick(argparse.Namespace(exec="none", launcher=None))
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_pick_handles_missing_fzf(monkeypatch, capsys, two_sessions):
    def boom(*_a, **_kw):
        raise FileNotFoundError("fzf")

    monkeypatch.setattr(cli.subprocess, "run", boom)
    rc = cli._cmd_pick(argparse.Namespace(exec="none", launcher=None))
    assert rc == 5
    err = capsys.readouterr().err
    assert "fzf not found" in err
    assert "brew install fzf" in err


def test_pick_no_sessions_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(cli.sessions, "list_sessions", lambda: [])
    rc = cli._cmd_pick(argparse.Namespace(exec="none", launcher=None))
    assert rc == 1
    assert "no sessions found" in capsys.readouterr().err


def test_pick_exec_smart_chains_into_smart_resume(monkeypatch, two_sessions):
    a, _b = two_sessions

    def fake_run(args, **_kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=f"{a.session_id}\tproject\ttitle\n",
            stderr="",
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    smart_called = {}

    def fake_smart(ns):
        smart_called["ns"] = ns
        return 0

    monkeypatch.setattr(cli, "_cmd_smart", fake_smart)
    rc = cli._cmd_pick(argparse.Namespace(exec="smart", launcher="tmux"))
    assert rc == 0
    assert smart_called["ns"].session_id == a.session_id
    assert smart_called["ns"].launcher == "tmux"


def test_pick_exec_open_chains_into_open(monkeypatch, two_sessions):
    a, _b = two_sessions

    def fake_run(args, **_kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=f"{a.session_id}\tproject\ttitle\n",
            stderr="",
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    open_called = {}

    def fake_open(ns):
        open_called["ns"] = ns
        return 0

    monkeypatch.setattr(cli, "_cmd_open", fake_open)
    rc = cli._cmd_pick(argparse.Namespace(exec="open", launcher=None))
    assert rc == 0
    assert open_called["ns"].session_id == a.session_id
    assert open_called["ns"].prompt == ""
