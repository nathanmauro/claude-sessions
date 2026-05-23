#!/usr/bin/env bash
# TPM loader. The real plugin lives under share/tmux/ to match the repo layout;
# TPM autodiscovers *.tmux at the repo root, so this one-liner forwards to it.
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$CURRENT_DIR/share/tmux/agent-sessions.tmux"
