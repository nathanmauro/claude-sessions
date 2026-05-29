from __future__ import annotations

import json
from pathlib import Path

from agentseq.core.export import (
    export_handoff_summary,
    export_sessions_markdown,
    export_skill_draft,
)


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")


def _write_claude_session(projects_dir: Path, sid: str, cwd: str, lines: list[dict]) -> None:
    """Write a minimal Claude transcript discoverable by ``find_session_path``."""
    project_slug = "-" + cwd.strip("/").replace("/", "-")
    _write_jsonl(projects_dir / project_slug / f"{sid}.jsonl", lines)


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


def test_export_handoff_summary_rolls_up_goal_open_tasks_and_last_activity(tmp_path: Path):
    projects_dir = tmp_path / "claude-projects"
    output_dir = tmp_path / "exports"

    _write_claude_session(
        projects_dir,
        "handoff-1",
        "/tmp/proj",
        [
            {
                "type": "user",
                "timestamp": "2026-05-20T09:00:00Z",
                "message": {"content": "build the widget pipeline"},
            },
            {
                "type": "assistant",
                "timestamp": "2026-05-20T09:00:01Z",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "TaskCreate",
                            "input": {
                                "taskId": "1",
                                "subject": "Wire the export button",
                                "description": "still pending",
                            },
                        }
                    ]
                },
            },
            {
                "type": "assistant",
                "timestamp": "2026-05-20T09:00:02Z",
                "message": {"content": [{"type": "text", "text": "left off mid-wiring"}]},
            },
        ],
    )

    output = export_handoff_summary(
        ["handoff-1"], output_dir=output_dir, projects_dir=projects_dir
    )

    text = output.read_text()
    assert "handoff" in output.name
    assert "Agentseq Handoff Summary" in text
    assert "Open tasks across all sessions" in text
    assert "Wire the export button" in text  # the open task surfaces in the roll-up
    assert "build the widget pipeline" in text  # the goal
    assert "left off mid-wiring" in text  # last activity


def test_export_skill_draft_scaffolds_frontmatter_and_recurring_prompts(tmp_path: Path):
    projects_dir = tmp_path / "claude-projects"
    output_dir = tmp_path / "exports"

    _write_claude_session(
        projects_dir,
        "skill-1",
        "/tmp/scraper",
        [
            {
                "type": "user",
                "timestamp": "2026-05-21T10:00:00Z",
                "message": {"content": "scrape the pricing table from the vendor site"},
            },
            {
                "type": "assistant",
                "timestamp": "2026-05-21T10:00:01Z",
                "message": {"content": [{"type": "text", "text": "done"}]},
            },
        ],
    )

    output = export_skill_draft(["skill-1"], output_dir=output_dir, projects_dir=projects_dir)

    text = output.read_text()
    assert "skill" in output.name
    # name derived from the project basename (scraper -> scraper-workflow)
    assert "name: scraper-workflow" in text
    assert "## When to use" in text
    assert "## Recurring prompts (raw material)" in text
    assert "scrape the pricing table from the vendor site" in text
    assert "## Source sessions" in text


def test_export_handoff_reports_missing_ids(tmp_path: Path):
    projects_dir = tmp_path / "claude-projects"
    output_dir = tmp_path / "exports"

    _write_claude_session(
        projects_dir,
        "present-1",
        "/tmp/proj",
        [
            {
                "type": "user",
                "timestamp": "2026-05-20T09:00:00Z",
                "message": {"content": "hello"},
            },
            {
                "type": "assistant",
                "timestamp": "2026-05-20T09:00:01Z",
                "message": {"content": [{"type": "text", "text": "hi"}]},
            },
        ],
    )

    output = export_handoff_summary(
        ["present-1", "ghost-2"], output_dir=output_dir, projects_dir=projects_dir
    )

    text = output.read_text()
    assert "Missing" in text
    assert "ghost-2" in text
