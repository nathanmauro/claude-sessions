from __future__ import annotations

import os
import sys
from pathlib import Path

from ._compat import _env


def _migrate_cache(home: Path | None = None) -> None:
    """Migrate ``~/.claude-sessions`` → ``~/.agent-sessions`` → ``~/.agentseq`` on first run."""
    home = home if home is not None else Path.home()
    if (
        os.environ.get("AGENTSEQ_CACHE")
        or os.environ.get("AGENT_SESSIONS_CACHE")
        or os.environ.get("CLAUDE_SESSIONS_CACHE")
    ):
        return
    target = home / ".agentseq"
    for old_name in (".agent-sessions", ".claude-sessions"):
        old = home / old_name
        if not old.exists():
            continue
        if target.exists():
            print(
                f"warning: both {old} and {target} exist; using {target}",
                file=sys.stderr,
            )
            continue
        try:
            os.rename(old, target)
        except OSError as e:
            print(f"warning: failed to migrate {old} -> {target}: {e}", file=sys.stderr)


_migrate_cache()

PROJECTS_DIR = Path(os.environ.get("CLAUDE_PROJECTS_DIR", Path.home() / ".claude" / "projects"))
CACHE_DIR = Path(
    _env("AGENTSEQ_CACHE", "AGENT_SESSIONS_CACHE", "CLAUDE_SESSIONS_CACHE",
         default=str(Path.home() / ".agentseq"))
)
DB_PATH = CACHE_DIR / "index.db"
NOTION_CACHE_FILE = CACHE_DIR / "notion-todos.json"
USAGE_FILE = CACHE_DIR / "usage.json"

PORT = int(_env("AGENTSEQ_PORT", "AGENT_SESSIONS_PORT", "CLAUDE_SESSIONS_PORT", default="8765"))
HOST = _env("AGENTSEQ_HOST", "AGENT_SESSIONS_HOST", "CLAUDE_SESSIONS_HOST", default="127.0.0.1")

NOTION_DB_ID = _env("AGENTSEQ_NOTION_DB_ID", "AGENT_SESSIONS_NOTION_DB_ID", "CLAUDE_SESSIONS_NOTION_DB_ID", default="")
NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
KEYCHAIN_ACCOUNT = _env("AGENTSEQ_KEYCHAIN_ACCOUNT", "AGENT_SESSIONS_KEYCHAIN_ACCOUNT", "CLAUDE_SESSIONS_KEYCHAIN_ACCOUNT", default="notion")
KEYCHAIN_SERVICE = _env("AGENTSEQ_KEYCHAIN_SERVICE", "AGENT_SESSIONS_KEYCHAIN_SERVICE", "CLAUDE_SESSIONS_KEYCHAIN_SERVICE", default="todo-cli")

AUGGIE_BIN = _env("AGENTSEQ_AUGGIE", "AGENT_SESSIONS_AUGGIE", "CLAUDE_SESSIONS_AUGGIE", default="")

INDEXER_INTERVAL_S = int(_env("AGENTSEQ_INDEX_INTERVAL", "AGENT_SESSIONS_INDEX_INTERVAL", "CLAUDE_SESSIONS_INDEX_INTERVAL", default="60"))
