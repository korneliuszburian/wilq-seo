from __future__ import annotations

from pathlib import Path


def test_security_gate_audits_dependencies_with_the_active_uv_interpreter() -> None:
    script = Path("scripts/security.sh").read_text(encoding="utf-8")

    assert "uv run --extra dev python -m pip_audit" in script
    assert "uv run --extra dev pip-audit" not in script


def test_python_quality_tools_use_the_active_uv_interpreter() -> None:
    expected_commands = {
        "scripts/lint.sh": "uv run --extra dev python -m ruff check .",
        "scripts/typecheck.sh": "uv run --extra dev python -m mypy",
        "scripts/test.sh": "uv run --extra dev python -m pytest \"$@\"",
        "scripts/security.sh": "uv run --extra dev python -m bandit",
        "scripts/verify.sh": "uv run python -m uvicorn",
        "scripts/local_stack.sh": "uv run python -m uvicorn",
        "scripts/access_pack_manifest.sh": "uv run python -",
        "scripts/access_pack_check.sh": "uv run python -",
        ".github/workflows/quality.yml": "scripts/test.sh",
    }

    for path, command in expected_commands.items():
        assert command in Path(path).read_text(encoding="utf-8")

    verify_script = Path("scripts/verify.sh").read_text(encoding="utf-8")
    assert ".venv/bin/" not in verify_script
    assert "uv run python -m wilq.cli jobs status" in verify_script
    assert (
        "uv run python -m uvicorn apps.api.wilq_api.main:app "
        '--host 127.0.0.1 --port "$skill_api_port"'
    ) in verify_script
