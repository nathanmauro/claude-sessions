from __future__ import annotations

import datetime as dt
import subprocess
import threading
from pathlib import Path

from ..core import db
from ..core.config import AUGGIE_BIN
from ..core.launcher import gui_window


def start_session(cwd: str, prompt: str = "") -> tuple[bool, str]:
    return gui_window().open_new(cwd, session_id=None, extra=prompt)


def resume_session(session_id: str, cwd: str, prompt: str = "") -> tuple[bool, str]:
    return gui_window().open_new(cwd, session_id=session_id, extra=prompt)


def open_finder(cwd: str) -> tuple[bool, str]:
    try:
        subprocess.run(["open", cwd], check=True)
        return True, "ok"
    except Exception as e:
        return False, str(e)


def open_editor(cwd: str) -> tuple[bool, str]:
    for cmd in ("cursor", "code"):
        try:
            subprocess.run([cmd, cwd], check=True)
            return True, f"opened with {cmd}"
        except FileNotFoundError:
            continue
        except Exception as e:
            return False, str(e)
    return False, "cursor/code not found in PATH"


def _augment_index_worker(cwd: str) -> None:
    if not AUGGIE_BIN:
        return
    try:
        subprocess.run([AUGGIE_BIN, "index", "--print"], cwd=cwd, check=True)
        db.set_augment_indexed_at(cwd, dt.datetime.now().isoformat())
    except Exception as e:
        print(f"Augment index error: {e}")


def trigger_augment_index(cwd: str) -> tuple[bool, str]:
    if not AUGGIE_BIN:
        return False, "set AGENT_SESSIONS_AUGGIE to enable augment integration"
    threading.Thread(target=_augment_index_worker, args=(cwd,), daemon=True).start()
    return True, "indexing started"


def get_github_url(cwd: str) -> str | None:
    config = Path(cwd) / ".git" / "config"
    if not config.exists():
        return None
    try:
        for line in config.read_text().splitlines():
            if "url =" in line:
                url = line.split("=", 1)[1].strip()
                if url.startswith("git@github.com:"):
                    return "https://github.com/" + url[15:].replace(".git", "")
                if url.startswith("https://github.com/"):
                    return url.replace(".git", "")
    except OSError:
        pass
    return None


def get_augment_status(cwd: str) -> str:
    when = db.get_augment_indexed_at(cwd)
    if when:
        return f"indexed at {when[:16]}"
    if (Path(cwd) / ".augment").exists():
        return "indexed"
    return "not indexed"
