"""Tests for backcompat plumbing: env-var fallback, cache migration, legacy CLI alias."""
from __future__ import annotations

import pytest

from agentseq.core import _compat
from agentseq.core._compat import _env
from agentseq.core.config import _migrate_cache


@pytest.fixture(autouse=True)
def _reset_warned():
    _compat._warned.clear()
    yield
    _compat._warned.clear()


# ----------------------------- _env helper -----------------------------


def test_env_prefers_new_name(monkeypatch, capsys):
    monkeypatch.setenv("AGENTSEQ_FOO", "new")
    monkeypatch.setenv("AGENT_SESSIONS_FOO", "mid")
    monkeypatch.setenv("CLAUDE_SESSIONS_FOO", "old")
    assert _env("AGENTSEQ_FOO", "AGENT_SESSIONS_FOO", "CLAUDE_SESSIONS_FOO", default="d") == "new"
    assert capsys.readouterr().err == ""


def test_env_falls_back_to_mid_with_warning(monkeypatch, capsys):
    monkeypatch.delenv("AGENTSEQ_FOO", raising=False)
    monkeypatch.setenv("AGENT_SESSIONS_FOO", "mid")
    monkeypatch.setenv("CLAUDE_SESSIONS_FOO", "old")
    assert _env("AGENTSEQ_FOO", "AGENT_SESSIONS_FOO", "CLAUDE_SESSIONS_FOO", default="d") == "mid"
    err = capsys.readouterr().err
    assert "$AGENT_SESSIONS_FOO" in err
    assert "deprecated" in err
    assert "$AGENTSEQ_FOO" in err


def test_env_falls_back_to_old_with_warning(monkeypatch, capsys):
    monkeypatch.delenv("AGENTSEQ_FOO", raising=False)
    monkeypatch.delenv("AGENT_SESSIONS_FOO", raising=False)
    monkeypatch.setenv("CLAUDE_SESSIONS_FOO", "old")
    assert _env("AGENTSEQ_FOO", "AGENT_SESSIONS_FOO", "CLAUDE_SESSIONS_FOO", default="d") == "old"
    err = capsys.readouterr().err
    assert "$CLAUDE_SESSIONS_FOO" in err
    assert "deprecated" in err
    assert "$AGENTSEQ_FOO" in err


def test_env_returns_default_when_none_set(monkeypatch, capsys):
    monkeypatch.delenv("AGENTSEQ_FOO", raising=False)
    monkeypatch.delenv("AGENT_SESSIONS_FOO", raising=False)
    monkeypatch.delenv("CLAUDE_SESSIONS_FOO", raising=False)
    assert _env("AGENTSEQ_FOO", "AGENT_SESSIONS_FOO", "CLAUDE_SESSIONS_FOO", default="d") == "d"
    assert capsys.readouterr().err == ""


def test_env_warning_fires_once_per_process(monkeypatch, capsys):
    monkeypatch.delenv("AGENTSEQ_FOO", raising=False)
    monkeypatch.setenv("CLAUDE_SESSIONS_FOO", "old")
    _env("AGENTSEQ_FOO", "CLAUDE_SESSIONS_FOO")
    _env("AGENTSEQ_FOO", "CLAUDE_SESSIONS_FOO")
    err = capsys.readouterr().err
    assert err.count("deprecated") == 1


# ---------------------- legacy launcher env var ------------------------


def test_legacy_launcher_env_var(monkeypatch, tmp_path, capsys):
    """Setting only CLAUDE_SESSIONS_LAUNCHER still routes to the right launcher."""
    from agentseq.core.launcher import TmuxLauncher, autodetect, detect

    for var in ("AGENTSEQ_LAUNCHER", "AGENT_SESSIONS_LAUNCHER", "CLAUDE_SESSIONS_LAUNCHER", "ZELLIJ", "TMUX"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("CLAUDE_SESSIONS_LAUNCHER", "tmux")
    monkeypatch.setattr(detect, "GHOSTTY_APP", str(tmp_path))
    assert isinstance(autodetect(), TmuxLauncher)
    err = capsys.readouterr().err
    assert "$CLAUDE_SESSIONS_LAUNCHER" in err
    assert "deprecated" in err


# ---------------------------- legacy_main ------------------------------


def test_legacy_main_warns_and_invokes_main(monkeypatch, capsys):
    from agentseq.cli import main as cli_main

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
    assert "deprecated" in err


# --------------------------- cache migration ---------------------------


def test_cache_migration_from_claude_sessions(tmp_path, monkeypatch, capsys):
    """~/.claude-sessions → ~/.agentseq."""
    monkeypatch.delenv("AGENTSEQ_CACHE", raising=False)
    monkeypatch.delenv("AGENT_SESSIONS_CACHE", raising=False)
    monkeypatch.delenv("CLAUDE_SESSIONS_CACHE", raising=False)
    old = tmp_path / ".claude-sessions"
    old.mkdir()
    (old / "marker.txt").write_text("hello")
    _migrate_cache(home=tmp_path)
    assert not old.exists()
    target = tmp_path / ".agentseq"
    assert target.exists()
    assert (target / "marker.txt").read_text() == "hello"
    assert capsys.readouterr().err == ""


def test_cache_migration_from_agent_sessions(tmp_path, monkeypatch, capsys):
    """~/.agent-sessions → ~/.agentseq."""
    monkeypatch.delenv("AGENTSEQ_CACHE", raising=False)
    monkeypatch.delenv("AGENT_SESSIONS_CACHE", raising=False)
    monkeypatch.delenv("CLAUDE_SESSIONS_CACHE", raising=False)
    old = tmp_path / ".agent-sessions"
    old.mkdir()
    (old / "marker.txt").write_text("hello")
    _migrate_cache(home=tmp_path)
    assert not old.exists()
    target = tmp_path / ".agentseq"
    assert target.exists()
    assert (target / "marker.txt").read_text() == "hello"


def test_cache_no_migration_when_target_exists(tmp_path, monkeypatch, capsys):
    """Both old dir and target exist → neither touched, warning emitted."""
    monkeypatch.delenv("AGENTSEQ_CACHE", raising=False)
    monkeypatch.delenv("AGENT_SESSIONS_CACHE", raising=False)
    monkeypatch.delenv("CLAUDE_SESSIONS_CACHE", raising=False)
    old = tmp_path / ".claude-sessions"
    target = tmp_path / ".agentseq"
    old.mkdir()
    target.mkdir()
    (old / "old.txt").write_text("o")
    (target / "new.txt").write_text("n")
    _migrate_cache(home=tmp_path)
    assert old.exists() and (old / "old.txt").exists()
    assert target.exists() and (target / "new.txt").exists()
    err = capsys.readouterr().err
    assert "both" in err


def test_cache_migration_skipped_with_env_override(tmp_path, monkeypatch, capsys):
    """User-set AGENTSEQ_CACHE skips migration."""
    monkeypatch.setenv("AGENTSEQ_CACHE", str(tmp_path / "custom"))
    old = tmp_path / ".claude-sessions"
    old.mkdir()
    _migrate_cache(home=tmp_path)
    assert old.exists()
    assert not (tmp_path / ".agentseq").exists()


def test_cache_migration_skipped_when_old_absent(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("AGENTSEQ_CACHE", raising=False)
    monkeypatch.delenv("AGENT_SESSIONS_CACHE", raising=False)
    monkeypatch.delenv("CLAUDE_SESSIONS_CACHE", raising=False)
    _migrate_cache(home=tmp_path)
    assert not (tmp_path / ".agentseq").exists()
    assert capsys.readouterr().err == ""
