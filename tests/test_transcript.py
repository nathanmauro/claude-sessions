"""Tests for transcript rendering and the `agent-sessions --view PATH` CLI."""
from __future__ import annotations

import json
from pathlib import Path

from agent_sessions.cli import main as cli
from agent_sessions.core import transcript


def _write_jsonl(path: Path, records: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return path


def test_render_markdown_handles_conversation_only(tmp_path: Path):
    path = _write_jsonl(
        tmp_path / "s.jsonl",
        [
            {"type": "user", "message": {"content": "hello"}},
            {"type": "assistant", "message": {"content": "world"}},
        ],
    )
    out = transcript.render_markdown(path)
    assert "## Conversation" in out
    assert "**User:**" in out and "hello" in out
    assert "**Claude:**" in out and "world" in out
    assert "Session Summary" not in out


def test_render_markdown_keeps_only_messages_after_compact_summary(tmp_path: Path):
    path = _write_jsonl(
        tmp_path / "s.jsonl",
        [
            {"type": "user", "message": {"content": "pre-compaction"}},
            {
                "isCompactSummary": True,
                "type": "user",
                "message": {"content": "Analysis:\nthe summary body"},
            },
            {"type": "user", "message": {"content": "post-compaction prompt"}},
            {"type": "assistant", "message": {"content": "post-compaction reply"}},
        ],
    )
    out = transcript.render_markdown(path)
    assert "## Session Summary" in out
    assert "the summary body" in out
    assert "Analysis:" not in out  # stripped
    assert "## Recent Conversation" in out
    assert "post-compaction prompt" in out
    assert "post-compaction reply" in out
    assert "pre-compaction" not in out


def test_render_markdown_strips_system_reminders_and_command_tags(tmp_path: Path):
    path = _write_jsonl(
        tmp_path / "s.jsonl",
        [
            {
                "type": "user",
                "message": {
                    "content": (
                        "real question\n"
                        "<system-reminder>noise</system-reminder>\n"
                        "<command-name>foo</command-name>"
                    )
                },
            },
        ],
    )
    out = transcript.render_markdown(path)
    assert "real question" in out
    assert "noise" not in out
    assert "<system-reminder>" not in out
    assert "<command-name>" not in out


def test_render_markdown_extracts_text_from_content_blocks(tmp_path: Path):
    path = _write_jsonl(
        tmp_path / "s.jsonl",
        [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "first block"},
                        {"type": "tool_use", "name": "Bash", "input": {}},
                        {"type": "text", "text": "second block"},
                    ]
                },
            },
        ],
    )
    out = transcript.render_markdown(path)
    assert "first block" in out
    assert "second block" in out
    assert "tool_use" not in out


def test_render_markdown_truncates_long_messages(tmp_path: Path):
    huge = "x" * 5000
    path = _write_jsonl(
        tmp_path / "s.jsonl",
        [{"type": "user", "message": {"content": huge}}],
    )
    out = transcript.render_markdown(path, max_msg_len=100)
    assert "[truncated...]" in out
    assert out.count("x") <= 200  # well under the original 5000


def test_render_markdown_skips_malformed_lines(tmp_path: Path):
    path = tmp_path / "s.jsonl"
    path.write_text(
        "not-json\n"
        + json.dumps({"type": "user", "message": {"content": "valid"}})
        + "\n"
    )
    out = transcript.render_markdown(path)
    assert "valid" in out


def test_render_markdown_empty_file_returns_empty(tmp_path: Path):
    path = tmp_path / "empty.jsonl"
    path.write_text("")
    assert transcript.render_markdown(path) == ""


def test_render_markdown_raises_when_path_missing(tmp_path: Path):
    import pytest

    with pytest.raises(FileNotFoundError):
        transcript.render_markdown(tmp_path / "nope.jsonl")


# ------------------------------- CLI ------------------------------


def test_cli_view_renders_transcript(tmp_path: Path, capsys):
    path = _write_jsonl(
        tmp_path / "s.jsonl",
        [
            {"type": "user", "message": {"content": "hi from cli"}},
            {"type": "assistant", "message": {"content": "hi back"}},
        ],
    )
    rc = cli.main(["--view", str(path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "hi from cli" in out
    assert "hi back" in out


def test_cli_view_missing_file_returns_2(tmp_path: Path, capsys):
    rc = cli.main(["--view", str(tmp_path / "nope.jsonl")])
    assert rc == 2
    assert "no such file" in capsys.readouterr().err
