#!/usr/bin/env bash
# claude-sessions tmux plugin
#
# Binds a key (default: prefix + C) to pop up an fzf picker for Claude Code
# sessions. Picking a session calls `claude-sessions pick --exec smart`, which
# resumes it in a new tmux pane (or focuses the existing one if already
# running).
#
# Requirements:
#   - tmux >= 3.2 (for display-popup -E)
#   - claude-sessions on $PATH (pipx / uv tool install)
#   - fzf on $PATH

default_key="C"
key=$(tmux show-option -gqv '@claude_sessions_key')
key=${key:-$default_key}

tmux bind-key "$key" display-popup -E -w 90% -h 80% \
    'claude-sessions pick --exec smart'
