"""Unit tests for core.launcher: detection + each backend's subprocess argv."""
from __future__ import annotations

import subprocess

import pytest

from agent_sessions.core import launcher as core_launcher
from agent_sessions.core.launcher import (
    GenericLauncher,
    GhosttyLauncher,
    TmuxLauncher,
    ZellijLauncher,
    autodetect,
    detect,
    get_launcher,
    gui_window,
)


@pytest.fixture
def fake_claude_bin(monkeypatch):
    """Pin claude_bin() so backends emit a deterministic argv."""
    monkeypatch.setattr(core_launcher, "claude_bin", lambda: "/bin/claude")
    # The launcher modules import claude_bin by name at module level; patch
    # each module's local reference too.
    for mod_name in ("ghostty", "tmux", "zellij"):
        mod = __import__(
            f"agent_sessions.core.launcher.{mod_name}", fromlist=["claude_bin"]
        )
        monkeypatch.setattr(mod, "claude_bin", lambda: "/bin/claude")
    return "/bin/claude"


class _Recorder:
    """Fake subprocess.run that records calls and returns success by default."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.stdout = ""
        self.returncode = 0

    def __call__(self, args, **kwargs):
        self.calls.append(list(args))
        return subprocess.CompletedProcess(
            args=args, returncode=self.returncode, stdout=self.stdout, stderr=b""
        )


@pytest.fixture
def fake_run(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(subprocess, "run", rec)
    return rec


@pytest.fixture
def existing_cwd(tmp_path) -> str:
    return str(tmp_path)


# ----------------------------- Ghostty -----------------------------


def test_ghostty_open_new_builds_open_args(fake_claude_bin, fake_run, existing_cwd):
    ok, msg = GhosttyLauncher().open_new(existing_cwd, "abc-123", extra="hello")
    assert ok, msg
    assert msg == "opened Ghostty window"
    assert len(fake_run.calls) == 1
    argv = fake_run.calls[0]
    assert argv[:5] == ["open", "-na", "/Applications/Ghostty.app", "--args", "-e"]
    assert argv[5:7] == ["/bin/zsh", "-lc"]
    inner = argv[7]
    assert existing_cwd in inner
    assert "/bin/claude" in inner
    assert "--resume" in inner
    assert "abc-123" in inner
    assert "hello" in inner


def test_ghostty_open_new_rejects_missing_cwd(fake_claude_bin, fake_run):
    ok, msg = GhosttyLauncher().open_new("/no/such/dir", "abc")
    assert not ok
    assert "cwd does not exist" in msg
    assert fake_run.calls == []


def test_ghostty_focus_pid_runs_osascript(fake_run):
    ok, msg = GhosttyLauncher().focus_pid(1234)
    assert ok
    assert msg == "focused pid 1234"
    argv = fake_run.calls[0]
    assert argv[0] == "osascript"
    assert "1234" in argv[2]


def test_ghostty_focus_app_runs_osascript(fake_run):
    ok, msg = GhosttyLauncher().focus_app("Ghostty")
    assert ok
    assert "Ghostty" in msg
    assert fake_run.calls[0][0] == "osascript"


# ------------------------------- tmux ------------------------------


def test_tmux_open_new_calls_tmux_new_window(fake_claude_bin, fake_run, existing_cwd):
    ok, msg = TmuxLauncher().open_new(existing_cwd, "sid-xyz")
    assert ok, msg
    assert msg == "opened tmux window"
    argv = fake_run.calls[0]
    assert argv[:3] == ["tmux", "new-window", "-c"]
    assert argv[3] == existing_cwd
    assert "--resume" in argv[4]
    assert "sid-xyz" in argv[4]


def test_tmux_open_new_handles_missing_binary(fake_claude_bin, monkeypatch, existing_cwd):
    def boom(*_args, **_kwargs):
        raise FileNotFoundError("tmux")

    monkeypatch.setattr(subprocess, "run", boom)
    ok, msg = TmuxLauncher().open_new(existing_cwd, "sid")
    assert not ok
    assert "tmux binary not found" in msg


def test_tmux_focus_pid_finds_matching_pane(monkeypatch):
    list_panes_output = (
        "111 main:0.0\n"
        "222 main:1.0\n"
        "333 work:0.0\n"
    )

    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(list(args))
        if args[:2] == ["tmux", "list-panes"]:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout=list_panes_output, stderr=b""
            )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    ok, msg = TmuxLauncher().focus_pid(222)
    assert ok, msg
    assert "main:1.0" in msg
    assert calls[-1][:3] == ["tmux", "select-window", "-t"]
    assert calls[-1][3] == "main:1.0"


def test_tmux_focus_pid_not_found(monkeypatch):
    def fake_run(args, **_kwargs):
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="999 a:0.0\n", stderr=b""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    ok, msg = TmuxLauncher().focus_pid(123)
    assert not ok
    assert "no tmux pane" in msg


def test_tmux_focus_app_is_unsupported(fake_run):
    ok, msg = TmuxLauncher().focus_app("Ghostty")
    assert not ok
    assert "not meaningful" in msg
    assert fake_run.calls == []


# ------------------------------ zellij -----------------------------


def test_zellij_open_new_calls_zellij_action(fake_claude_bin, fake_run, existing_cwd):
    ok, msg = ZellijLauncher().open_new(existing_cwd, "sid-zzz", extra="continue")
    assert ok, msg
    assert msg == "opened zellij pane"
    argv = fake_run.calls[0]
    assert argv[:5] == ["zellij", "action", "new-pane", "--", "/bin/zsh"]
    assert argv[5] == "-lc"
    inner = argv[6]
    assert existing_cwd in inner
    assert "--resume" in inner
    assert "sid-zzz" in inner
    assert "continue" in inner


def test_zellij_focus_returns_unsupported(fake_run):
    ok, msg = ZellijLauncher().focus_pid(42)
    assert not ok
    assert "no per-pane focus" in msg
    assert fake_run.calls == []


# ------------------------------ generic ----------------------------


def test_generic_open_new_returns_actionable_error():
    ok, msg = GenericLauncher().open_new("/tmp", "sid")
    assert not ok
    assert "CLAUDE_SESSIONS_LAUNCHER" in msg


def test_generic_focus_returns_unsupported():
    ok, msg = GenericLauncher().focus_pid(1)
    assert not ok
    assert "not supported" in msg


# --------------------------- get_launcher --------------------------


@pytest.mark.parametrize(
    "name,cls",
    [
        ("ghostty", GhosttyLauncher),
        ("tmux", TmuxLauncher),
        ("zellij", ZellijLauncher),
        ("generic", GenericLauncher),
    ],
)
def test_get_launcher_returns_expected_class(name, cls):
    assert isinstance(get_launcher(name), cls)


def test_get_launcher_unknown_raises():
    with pytest.raises(ValueError, match="unknown launcher"):
        get_launcher("kitty")


# ---------------------------- autodetect ---------------------------


def _clear_env(monkeypatch):
    for var in ("CLAUDE_SESSIONS_LAUNCHER", "ZELLIJ", "TMUX"):
        monkeypatch.delenv(var, raising=False)


def test_autodetect_prefers_zellij(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("ZELLIJ", "1")
    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,1,0")
    monkeypatch.setattr(detect, "GHOSTTY_APP", str(tmp_path))
    assert isinstance(autodetect(), ZellijLauncher)


def test_autodetect_falls_back_to_tmux(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,1,0")
    monkeypatch.setattr(detect, "GHOSTTY_APP", str(tmp_path))
    assert isinstance(autodetect(), TmuxLauncher)


def test_autodetect_uses_ghostty_when_present(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    # tmp_path exists, so Path(GHOSTTY_APP).exists() returns True
    monkeypatch.setattr(detect, "GHOSTTY_APP", str(tmp_path))
    assert isinstance(autodetect(), GhosttyLauncher)


def test_autodetect_falls_back_to_generic(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    missing = tmp_path / "no-ghostty"
    monkeypatch.setattr(detect, "GHOSTTY_APP", str(missing))
    assert isinstance(autodetect(), GenericLauncher)


def test_autodetect_honors_env_override(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("ZELLIJ", "1")
    monkeypatch.setenv("TMUX", "x")
    monkeypatch.setenv("CLAUDE_SESSIONS_LAUNCHER", "tmux")
    monkeypatch.setattr(detect, "GHOSTTY_APP", str(tmp_path))
    assert isinstance(autodetect(), TmuxLauncher)


# ---------------------------- gui_window ---------------------------


def test_gui_window_ignores_tmux_env(monkeypatch, tmp_path):
    """Even inside tmux/zellij, dash + menu clicks should spawn a GUI window."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("TMUX", "x")
    monkeypatch.setenv("ZELLIJ", "1")
    monkeypatch.setattr(detect, "GHOSTTY_APP", str(tmp_path))
    assert isinstance(gui_window(), GhosttyLauncher)


def test_gui_window_falls_back_to_generic_without_ghostty(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setattr(detect, "GHOSTTY_APP", str(tmp_path / "missing"))
    assert isinstance(gui_window(), GenericLauncher)


def test_gui_window_rejects_tmux_override(monkeypatch, tmp_path):
    """gui_window only honors GUI-safe overrides (ghostty, generic)."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("CLAUDE_SESSIONS_LAUNCHER", "tmux")
    monkeypatch.setattr(detect, "GHOSTTY_APP", str(tmp_path))
    # The override is ignored; falls through to the Ghostty path
    assert isinstance(gui_window(), GhosttyLauncher)


def test_gui_window_honors_generic_override(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("CLAUDE_SESSIONS_LAUNCHER", "generic")
    monkeypatch.setattr(detect, "GHOSTTY_APP", str(tmp_path))
    assert isinstance(gui_window(), GenericLauncher)
