#!/usr/bin/env bash
# Capture docs/screenshots/cli.png using vhs + a seeded demo DB.
#
# Runs from repo root. Requires:
#   - vhs (brew install vhs)
#   - .venv/bin/agent-sessions (pip install -e '.[menu]')
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

if ! command -v vhs >/dev/null 2>&1; then
  echo "error: vhs not installed. run: brew install vhs" >&2
  exit 1
fi

if [[ ! -x .venv/bin/agent-sessions ]]; then
  echo "error: .venv/bin/agent-sessions not found." >&2
  echo "  run: uv venv && uv pip install -e '.[menu]'" >&2
  exit 1
fi

DEMO_CACHE="/tmp/demo-agent-sessions"
export AGENT_SESSIONS_CACHE="$DEMO_CACHE"

python3 web/scripts/seed-demo-db.py >&2

# Put the venv's bin first so `agent-sessions` resolves to it inside vhs.
export PATH="$REPO_ROOT/.venv/bin:$PATH"

vhs docs/screenshots/cli.tape

ls -lh docs/screenshots/cli.png
