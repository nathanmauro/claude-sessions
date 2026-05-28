from __future__ import annotations

import json
from pathlib import Path

from agentseq.core.export import export_sessions_markdown


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")


def test_export_sessions_markdown_combines_claude_and_codex(tmp_path: Path):
    projects_dir = tmp_path / "claude-projects"
    codex_dir = tmp_path / "codex-sessions"
    output_dir = tmp_path / "exports"

    _write_jsonl(
        projects_dir / "-tmp-claude" / "claude-export-123.jsonl",
        [
            {
                "type": "user",
                "timestamp": "2026-05-18T10:00:00Z",
                "message": {"content": "claude export question"},
            },
            {
                "type": "assistant",
                "timestamp": "2026-05-18T10:00:01Z",
                "message": {"content": [{"type": "text", "text": "claude export answer"}]},
            },
        ],
    )
    _write_jsonl(
        codex_dir / "2026" / "05" / "28" / "rollout-codex-export-123.jsonl",
        [
            {
                "type": "session_meta",
                "timestamp": "2026-05-28T16:00:00Z",
                "payload": {"id": "codex-export-123", "cwd": "/tmp/codex"},
            },
            {
                "type": "response_item",
                "timestamp": "2026-05-28T16:00:01Z",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "codex export question"}],
                },
            },
            {
                "type": "response_item",
                "timestamp": "2026-05-28T16:00:02Z",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "codex export answer"}],
                },
            },
        ],
    )

    output = export_sessions_markdown(
        ["claude-export-123", "codex-export-123"],
        output_dir=output_dir,
        projects_dir=projects_dir,
        codex_dir=codex_dir,
    )

    text = output.read_text()
    assert output.parent == output_dir
    assert "Agentseq Session Export" in text
    assert "claude export question" in text
    assert "codex export answer" in text
    assert "Source: `claude`" in text
    assert "Source: `codex`" in text
