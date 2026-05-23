from __future__ import annotations

import os
import sys
from pathlib import Path

from ._compat import _env


def _migrate_cache(home: Path | None = None) -> None:
    """Rename ``~/.claude-sessions`` → ``~/.agent-sessions`` on first run.

    Silently skips if the old dir is absent or the user has overridden the
    cache path via env var. If both default dirs exist, logs one stderr line
    and leaves both in place (new path wins)."""
    home = home if home is not None else Path.home()
    if os.environ.get("AGENT_SESSIONS_CACHE") or os.environ.get("CLAUDE_SESSIONS_CACHE"):
        return
    old = home / ".claude-sessions"
    new = home / ".agent-sessions"
    if not old.exists():
        return
    if new.exists():
        print(
            f"warning: both {old} and {new} exist; using {new}",
            file=sys.stderr,
        )
        return
    try:
        os.rename(old, new)
    except OSError as e:
        print(f"warning: failed to migrate {old} -> {new}: {e}", file=sys.stderr)


_migrate_cache()

PROJECTS_DIR = Path(os.environ.get("CLAUDE_PROJECTS_DIR", Path.home() / ".claude" / "projects"))
CACHE_DIR = Path(
    _env("AGENT_SESSIONS_CACHE", "CLAUDE_SESSIONS_CACHE", str(Path.home() / ".agent-sessions"))
)
DB_PATH = CACHE_DIR / "index.db"
NOTION_CACHE_FILE = CACHE_DIR / "notion-todos.json"
USAGE_FILE = CACHE_DIR / "usage.json"

PORT = int(_env("AGENT_SESSIONS_PORT", "CLAUDE_SESSIONS_PORT", "8765"))
HOST = _env("AGENT_SESSIONS_HOST", "CLAUDE_SESSIONS_HOST", "127.0.0.1")

# Notion integration (optional). No data source ID is shipped — set
# AGENT_SESSIONS_NOTION_DB_ID and provide a token via NOTION_TOKEN env or
# macOS keychain (security find-generic-password -a notion -s todo-cli).
NOTION_DB_ID = _env("AGENT_SESSIONS_NOTION_DB_ID", "CLAUDE_SESSIONS_NOTION_DB_ID", "")
NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
KEYCHAIN_ACCOUNT = _env("AGENT_SESSIONS_KEYCHAIN_ACCOUNT", "CLAUDE_SESSIONS_KEYCHAIN_ACCOUNT", "notion")
KEYCHAIN_SERVICE = _env("AGENT_SESSIONS_KEYCHAIN_SERVICE", "CLAUDE_SESSIONS_KEYCHAIN_SERVICE", "todo-cli")

# Optional Auggie/Augment integration. Empty string disables.
AUGGIE_BIN = _env("AGENT_SESSIONS_AUGGIE", "CLAUDE_SESSIONS_AUGGIE", "")

INDEXER_INTERVAL_S = int(_env("AGENT_SESSIONS_INDEX_INTERVAL", "CLAUDE_SESSIONS_INDEX_INTERVAL", "60"))
