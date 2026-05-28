from __future__ import annotations

import json
from pathlib import Path

from agentseq.core import db


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")


def test_index_all_indexes_claude_and_codex_sources(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "index.db")

    claude_dir = tmp_path / "claude-projects"
    _write_jsonl(
        claude_dir / "-Users-nathan-Developer-proj-foo" / "claude-123.jsonl",
        [
            {
                "type": "user",
                "timestamp": "2026-05-18T10:00:00Z",
                "message": {"content": "claude question"},
            },
            {
                "type": "assistant",
                "timestamp": "2026-05-18T10:00:01Z",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "TaskCreate",
                            "input": {"taskId": "t1", "subject": "created task"},
                        }
                    ]
                },
            },
        ],
    )

    codex_dir = tmp_path / "codex-sessions"
    _write_jsonl(
        codex_dir / "2026" / "05" / "28" / "rollout-codex-123.jsonl",
        [
            {
                "type": "session_meta",
                "timestamp": "2026-05-28T16:00:00Z",
                "payload": {"id": "codex-123", "cwd": "/tmp/codex-project"},
            },
            {
                "type": "response_item",
                "timestamp": "2026-05-28T16:00:01Z",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "codex question"}],
                },
            },
            {
                "type": "response_item",
                "timestamp": "2026-05-28T16:00:02Z",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "codex answer"}],
                },
            },
        ],
    )

    db.init_db()
    with db.get_db() as conn:
        conn.execute("ALTER TABLE tasks ADD COLUMN older_schema_extra TEXT")

    changed = db.index_all(claude_dir, codex_dir)
    hits = db.search("question", limit=10)

    assert set(changed) == {"claude-123", "codex-123"}
    assert {hit.source for hit in hits} == {"claude", "codex"}
