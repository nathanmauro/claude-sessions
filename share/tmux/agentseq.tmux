#!/usr/bin/env bash
# agentseq tmux plugin
#
# Binds a key (default: prefix + C) to pop up an fzf picker for Claude Code
# sessions. Picking a session calls `agentseq pick --exec smart`, which
# resumes it in a new tmux pane (or focuses the existing one if already
# running).
#
# Requirements:
#   - tmux >= 3.2 (for display-popup -E)
#   - agentseq on $PATH (pipx / uv tool install)
#   - fzf on $PATH

default_key="C"
key=$(tmux show-option -gqv '@agentseq_key')
key=${key:-$default_key}

tmux bind-key "$key" display-popup -E -w 90% -h 80% \
    'agentseq pick --exec smart'
