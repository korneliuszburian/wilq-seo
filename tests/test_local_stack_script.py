from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STACK_SCRIPT = ROOT / "scripts" / "local_stack.sh"


def test_local_stack_script_is_executable_and_valid_bash() -> None:
    assert STACK_SCRIPT.exists()
    assert os.access(STACK_SCRIPT, os.X_OK)

    result = subprocess.run(
        ["bash", "-n", str(STACK_SCRIPT)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_local_stack_help_documents_operator_commands() -> None:
    result = subprocess.run(
        [str(STACK_SCRIPT), "--help"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "start|stop|restart|status|logs" in result.stdout
    assert "http://127.0.0.1:8000" in result.stdout
    assert "http://127.0.0.1:5173/command-center" in result.stdout


def test_operator_docs_point_to_local_stack_manager() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    context = (ROOT / "docs" / "CONTEXT.md").read_text(encoding="utf-8")
    goal = (ROOT / "docs" / "goals" / "001-goal.md").read_text(encoding="utf-8")

    for content in (agents, context, goal):
        assert "scripts/local_stack.sh" in content
    assert "Do not hand-roll" in agents
