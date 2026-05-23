"""Tests for backcompat plumbing: env-var fallback, cache migration, legacy CLI alias."""
from __future__ import annotations

import sys

import pytest

from agent_sessions.core import _compat
from agent_sessions.core._compat import _env
from agent_sessions.core.config import _migrate_cache


@pytest.fixture(autouse=True)
def _reset_warned():
    _compat._warned.clear()
    yield
    _compat._warned.clear()


# ----------------------------- _env helper -----------------------------


def test_env_prefers_new_name(monkeypatch, capsys):
    monkeypatch.setenv("AGENT_SESSIONS_FOO", "new")
    monkeypatch.setenv("CLAUDE_SESSIONS_FOO", "old")
    assert _env("AGENT_SESSIONS_FOO", "CLAUDE_SESSIONS_FOO", "d") == "new"
    assert capsys.readouterr().err == ""


def test_env_falls_back_to_old_with_warning(monkeypatch, capsys):
    monkeypatch.delenv("AGENT_SESSIONS_FOO", raising=False)
    monkeypatch.setenv("CLAUDE_SESSIONS_FOO", "old")
    assert _env("AGENT_SESSIONS_FOO", "CLAUDE_SESSIONS_FOO", "d") == "old"
    err = capsys.readouterr().err
    assert "$CLAUDE_SESSIONS_FOO" in err
    assert "deprecated" in err
    assert "$AGENT_SESSIONS_FOO" in err


def test_env_returns_default_when_neither_set(monkeypatch, capsys):
    monkeypatch.delenv("AGENT_SESSIONS_FOO", raising=False)
    monkeypatch.delenv("CLAUDE_SESSIONS_FOO", raising=False)
    assert _env("AGENT_SESSIONS_FOO", "CLAUDE_SESSIONS_FOO", "d") == "d"
    assert capsys.readouterr().err == ""


def test_env_warning_fires_once_per_process(monkeypatch, capsys):
    monkeypatch.delenv("AGENT_SESSIONS_FOO", raising=False)
    monkeypatch.setenv("CLAUDE_SESSIONS_FOO", "old")
    _env("AGENT_SESSIONS_FOO", "CLAUDE_SESSIONS_FOO")
    _env("AGENT_SESSIONS_FOO", "CLAUDE_SESSIONS_FOO")
    err = capsys.readouterr().err
    assert err.count("deprecated") == 1


# ---------------------- legacy launcher env var ------------------------


def test_legacy_launcher_env_var(monkeypatch, tmp_path, capsys):
    """Setting only CLAUDE_SESSIONS_LAUNCHER still routes to the right launcher."""
    from agent_sessions.core.launcher import TmuxLauncher, autodetect, detect

    for var in ("AGENT_SESSIONS_LAUNCHER", "CLAUDE_SESSIONS_LAUNCHER", "ZELLIJ", "TMUX"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("CLAUDE_SESSIONS_LAUNCHER", "tmux")
    monkeypatch.setattr(detect, "GHOSTTY_APP", str(tmp_path))
    assert isinstance(autodetect(), TmuxLauncher)
    err = capsys.readouterr().err
    assert "$CLAUDE_SESSIONS_LAUNCHER" in err
    assert "deprecated" in err


# ---------------------------- legacy_main ------------------------------


def test_legacy_main_warns_and_invokes_main(monkeypatch, capsys):
    from agent_sessions.cli import main as cli_main

    called: dict[str, bool] = {}

    def fake_main(argv=None):
        called["yes"] = True
        return 0

    monkeypatch.setattr(cli_main, "main", fake_main)
    with pytest.raises(SystemExit) as excinfo:
        cli_main.legacy_main()
    assert excinfo.value.code == 0
    assert called.get("yes") is True
    err = capsys.readouterr().err
    assert "claude-sessions" in err
    assert "deprecated" in err


# --------------------------- cache migration ---------------------------


def test_cache_migration(tmp_path, monkeypatch, capsys):
    """Old dir alone → renamed to new."""
    monkeypatch.delenv("AGENT_SESSIONS_CACHE", raising=False)
    monkeypatch.delenv("CLAUDE_SESSIONS_CACHE", raising=False)
    old = tmp_path / ".claude-sessions"
    new = tmp_path / ".agent-sessions"
    old.mkdir()
    (old / "marker.txt").write_text("hello")
    _migrate_cache(home=tmp_path)
    assert not old.exists()
    assert new.exists()
    assert (new / "marker.txt").read_text() == "hello"
    assert capsys.readouterr().err == ""


def test_cache_no_migration_when_both_exist(tmp_path, monkeypatch, capsys):
    """Both dirs present → neither touched, single warning emitted."""
    monkeypatch.delenv("AGENT_SESSIONS_CACHE", raising=False)
    monkeypatch.delenv("CLAUDE_SESSIONS_CACHE", raising=False)
    old = tmp_path / ".claude-sessions"
    new = tmp_path / ".agent-sessions"
    old.mkdir()
    new.mkdir()
    (old / "old.txt").write_text("o")
    (new / "new.txt").write_text("n")
    _migrate_cache(home=tmp_path)
    assert old.exists() and (old / "old.txt").exists()
    assert new.exists() and (new / "new.txt").exists()
    err = capsys.readouterr().err
    assert "both" in err
    assert str(old) in err
    assert str(new) in err


def test_cache_migration_skipped_with_env_override(tmp_path, monkeypatch, capsys):
    """User-set AGENT_SESSIONS_CACHE/CLAUDE_SESSIONS_CACHE skips migration."""
    monkeypatch.setenv("AGENT_SESSIONS_CACHE", str(tmp_path / "custom"))
    old = tmp_path / ".claude-sessions"
    old.mkdir()
    _migrate_cache(home=tmp_path)
    assert old.exists()
    assert not (tmp_path / ".agent-sessions").exists()


def test_cache_migration_skipped_when_old_absent(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("AGENT_SESSIONS_CACHE", raising=False)
    monkeypatch.delenv("CLAUDE_SESSIONS_CACHE", raising=False)
    _migrate_cache(home=tmp_path)
    assert not (tmp_path / ".agent-sessions").exists()
    assert capsys.readouterr().err == ""
