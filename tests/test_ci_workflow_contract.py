from __future__ import annotations

from pathlib import Path

import yaml


def test_quality_workflow_runs_full_integration_verification() -> None:
    workflow = yaml.safe_load(
        Path(".github/workflows/quality.yml").read_text(encoding="utf-8")
    )

    assert isinstance(workflow, dict)
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    integration = jobs["integration"]
    assert isinstance(integration, dict)
    steps = integration["steps"]
    assert isinstance(steps, list)
    assert {"run": "scripts/verify.sh"} in steps
