from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

CONTENT_OPERATOR_SMOKE_PATH = Path(
    ".agents/skills/wilq-content-operator/scripts/smoke_skill_contract.py"
)
CONTENT_OPERATOR_SKILL_PATH = Path(".agents/skills/wilq-content-operator/SKILL.md")


def load_smoke_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "wilq_content_operator_smoke",
        CONTENT_OPERATOR_SMOKE_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_content_operator_skill_uses_one_prepare_text_action() -> None:
    smoke = load_smoke_script()
    skill = CONTENT_OPERATOR_SKILL_PATH.read_text(encoding="utf-8")
    entry = {
        "response_type": "content_workflow_entry",
        "recommendations": [
            {"work_item_id": "content_work_item_bdo", "url": "https://www.ekologus.pl/bdo/"}
        ],
    }
    workspace = {
        "response_type": "content_document_workspace",
        "work_item_id": "content_work_item_bdo",
        "work_kind": "refresh_existing",
        "source_snapshot": {"status": "available", "evidence_ids": ["ev_wp_bdo"]},
        "canonical_document": {
            "status": "unreviewed",
            "revision_id": "revision_bdo",
            "content_digest": "b" * 64,
            "revision": {"revision_id": "revision_bdo", "content_digest": "b" * 64},
        },
    }
    planning = {
        "status": "ready",
        "work_item_id": "content_work_item_bdo",
        "planning_input_digest": "a" * 64,
        "proposal": {
            "proposal_id": "proposal_bdo",
            "planning_digest": "c" * 64,
            "planning_input_digest": "a" * 64,
        },
        "publish_ready": False,
    }

    assert smoke.validate_entry(entry)["work_item_id"] == "content_work_item_bdo"
    assert smoke.validate_workspace(workspace, "content_work_item_bdo") is workspace
    assert smoke.validate_planning(planning, "content_work_item_bdo") is planning
    assert "zapisz\n   exact `scope` review" not in skill
    assert "zapisuje exact planning\n   review" not in skill
    assert "→ przygotuj tekst" in skill
    assert "po jasnym „przygotuj plan”" not in skill
    assert "„przygotuj pierwszą wersję”" not in skill
    assert "POST .../initial-draft" in skill
    assert "GET /api/content/new-page-topics" in skill


def test_content_operator_smoke_rejects_mismatched_exact_read_models() -> None:
    smoke = load_smoke_script()
    planning = {
        "status": "ready",
        "work_item_id": "content_work_item_other",
        "planning_input_digest": "a" * 64,
        "proposal": {
            "proposal_id": "proposal_bdo",
            "planning_digest": "c" * 64,
            "planning_input_digest": "a" * 64,
        },
        "publish_ready": False,
    }
    workspace = {
        "response_type": "content_document_workspace",
        "work_item_id": "content_work_item_bdo",
        "work_kind": "refresh_existing",
        "source_snapshot": {"status": "available", "evidence_ids": ["ev_wp_bdo"]},
        "canonical_document": {
            "status": "unreviewed",
            "revision_id": "revision_bdo",
            "content_digest": "b" * 64,
            "revision": {"revision_id": "revision_bdo", "content_digest": "d" * 64},
        },
    }

    with pytest.raises(SystemExit, match="Planning status work_item_id mismatch"):
        smoke.validate_planning(planning, "content_work_item_bdo")
    with pytest.raises(SystemExit, match="Workspace revision is not exact-bound"):
        smoke.validate_workspace(workspace, "content_work_item_bdo")
