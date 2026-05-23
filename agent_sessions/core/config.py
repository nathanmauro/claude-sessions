from __future__ import annotations

import os
from pathlib import Path

PROJECTS_DIR = Path(os.environ.get("CLAUDE_PROJECTS_DIR", Path.home() / ".claude" / "projects"))
CACHE_DIR = Path(os.environ.get("CLAUDE_SESSIONS_CACHE", Path.home() / ".claude-sessions"))
DB_PATH = CACHE_DIR / "index.db"
NOTION_CACHE_FILE = CACHE_DIR / "notion-todos.json"
USAGE_FILE = CACHE_DIR / "usage.json"

PORT = int(os.environ.get("CLAUDE_SESSIONS_PORT", "8765"))
HOST = os.environ.get("CLAUDE_SESSIONS_HOST", "127.0.0.1")

# Notion integration (optional). No data source ID is shipped — set
# CLAUDE_SESSIONS_NOTION_DB_ID and provide a token via NOTION_TOKEN env or
# macOS keychain (security find-generic-password -a notion -s todo-cli).
NOTION_DB_ID = os.environ.get("CLAUDE_SESSIONS_NOTION_DB_ID", "")
NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
KEYCHAIN_ACCOUNT = os.environ.get("CLAUDE_SESSIONS_KEYCHAIN_ACCOUNT", "notion")
KEYCHAIN_SERVICE = os.environ.get("CLAUDE_SESSIONS_KEYCHAIN_SERVICE", "todo-cli")

# Optional Auggie/Augment integration. Empty string disables.
AUGGIE_BIN = os.environ.get("CLAUDE_SESSIONS_AUGGIE", "")

INDEXER_INTERVAL_S = int(os.environ.get("CLAUDE_SESSIONS_INDEX_INTERVAL", "60"))
