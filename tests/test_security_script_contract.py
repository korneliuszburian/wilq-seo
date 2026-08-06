from __future__ import annotations

from pathlib import Path


def test_security_gate_audits_dependencies_with_the_active_uv_interpreter() -> None:
    script = Path("scripts/security.sh").read_text(encoding="utf-8")

    assert "uv run --extra dev python -m pip_audit" in script
    assert "uv run --extra dev pip-audit" not in script
