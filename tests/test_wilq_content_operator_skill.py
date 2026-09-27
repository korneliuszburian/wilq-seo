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
    document_workspace = {
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
    selected_workspace = {
        "response_type": "content_selected_workspace",
        "status": "ready",
        "work_item_id": "content_work_item_bdo",
        "workspace": document_workspace,
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
    assert (
        smoke.validate_selected_workspace(selected_workspace, "content_work_item_bdo")
        is document_workspace
    )
    assert smoke.validate_planning(planning, "content_work_item_bdo") is planning
    assert "zapisz\n   exact `scope` review" not in skill
    assert "zapisuje exact planning\n   review" not in skill
    assert "→ przygotuj tekst" in skill
    assert "po jasnym „przygotuj plan”" not in skill
    assert "„przygotuj pierwszą wersję”" not in skill
    assert "Co już jest:` plan" not in skill
    assert "stan przygotowania tekstu / rewizja / review" in skill
    assert "POST .../initial-draft" in skill
    assert "GET /api/content/new-page-topics" in skill


def test_content_operator_skill_routes_through_v3_packet_and_intent() -> None:
    skill = CONTENT_OPERATOR_SKILL_PATH.read_text(encoding="utf-8")

    assert "POST /api/content/work-items/{work_item_id}/planning-proposals" not in skill
    assert (
        "POST /api/content/work-items/{work_item_id}/research-packet-v3-action/preview" in skill
    )
    assert (
        "POST /api/content/work-items/{work_item_id}/planning-generation-intent-v3/preview"
        in skill
    )
    assert (
        "POST /api/content/planning-generation-intents-v3/{action_id}/dispatch" in skill
    )
    assert "per_url_delivery_identity_action_id" in skill
    assert "GET /api/content/work-items/{work_item_id}/planning-proposals" in skill
    assert "POST .../initial-draft" in skill
    assert "initial_draft_action_required" in skill


def test_content_operator_skill_routes_a_bare_ask_through_the_intake_queue() -> None:
    skill = CONTENT_OPERATOR_SKILL_PATH.read_text(encoding="utf-8")

    assert "POST /api/content/intake-requests" in skill
    assert "GET /api/content/intake-requests/{queue_id}" in skill
    assert "GET /api/content/intake-requests/{queue_id}/research" in skill
    assert "GET /api/content/intake-requests/{queue_id}/workflow" in skill
    assert "GET /api/content/intake-requests/{queue_id}/brief" in skill
    assert "queue ID" in skill
    assert "intake_target_missing" in skill
    assert "intake_ask_too_generic" in skill
    assert "new_topic_discovery_source_unavailable" in skill
    assert "Status kolejki" in skill


def test_content_operator_smoke_allows_an_empty_entry_only_when_requested() -> None:
    smoke = load_smoke_script()
    empty_entry = {"response_type": "content_workflow_entry", "recommendations": []}

    with pytest.raises(SystemExit, match="No evidence-bound recommendation is available"):
        smoke.validate_entry(empty_entry)
    assert smoke.validate_entry(empty_entry, allow_empty=True) is None


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
