"""Executable action-order observer; retire when isolated Vitest runs at both snapshots."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def test_action_ui_orders_validate_preview_review_and_completion() -> None:
    root = Path(__file__).resolve().parents[2]
    module = root / "apps/dashboard/src/routes/ActionPanels/lifecycleOrder.ts"
    assert module.is_file(), "Canonical action UI ordering module is absent."
    node = shutil.which("node")
    assert node is not None, "Node runtime is required for the browser contract."
    script = """
import { ACTION_LIFECYCLE_ORDER } from "./apps/dashboard/src/routes/ActionPanels/lifecycleOrder.ts";
process.stdout.write(JSON.stringify(ACTION_LIFECYCLE_ORDER));
"""
    result = subprocess.run(
        [node, "--experimental-strip-types", "--input-type=module", "-e", script],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-500:]
    assert json.loads(result.stdout) == [
        "validate", "preview", "review", "confirm_impact_apply"
    ]
