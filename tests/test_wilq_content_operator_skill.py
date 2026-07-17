from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

CONTENT_OPERATOR_SMOKE_PATH = Path(
    ".agents/skills/wilq-content-operator/scripts/smoke_skill_contract.py"
)


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


def test_content_operator_smoke_reads_current_model_free_workflow_statuses() -> None:
    smoke = load_smoke_script()
    summary = smoke.validate_snapshot(
        {
            "response_type": "workflow_snapshot",
            "current_step_id": "scope",
            "operator_steps": [
                {"id": step}
                for step in ("scope", "section_map", "draft", "review", "dev_draft")
            ],
            "preflight": {
                "item": {
                    "id": "content_work_item_bdo",
                    "evidence_ids": ["ev_gsc_bdo"],
                    "source_connectors": ["google_search_console"],
                }
            },
            "planning_workspace": {
                "scope_current": False,
                "section_map_current": False,
                "proposal": {
                    "planning_digest": "a" * 64,
                    "search_demand": {
                        "gsc_query_rows": [
                            {
                                "source_connector": "google_search_console",
                                "evidence_ids": ["ev_gsc_bdo"],
                                "section_headings": ["Kogo dotyczy BDO"],
                                "section_mapping_status": "lexical_relevance",
                                "period": "last_28_days",
                                "freshness": "fresh",
                            }
                        ],
                        "ads_term_rows": [],
                        "keyword_planner_rows": [],
                        "optional_ads_status": "not_exactly_mapped",
                    },
                },
            },
            "revision_workspace": {"status": "empty", "latest_revision": None},
            "wordpress_handoff": {"handoff_result": {"handoff": None}},
            "publish_ready": False,
        },
        "content_work_item_bdo",
    )

    assert summary == {
        "current_step_id": "scope",
        "planning_digest": "a" * 64,
        "planning_input_digest": None,
        "service_card_id": None,
        "scope_current": False,
        "section_map_current": False,
        "gsc_query_rows": [
            {
                "source_connector": "google_search_console",
                "evidence_ids": ["ev_gsc_bdo"],
                "section_headings": ["Kogo dotyczy BDO"],
                "section_mapping_status": "lexical_relevance",
                "period": "last_28_days",
                "freshness": "fresh",
            }
        ],
        "gsc_query_row_count": 1,
        "ads_term_row_count": 0,
        "keyword_planner_row_count": 0,
        "revision_status": "empty",
        "latest_revision_id": None,
        "latest_revision_digest": None,
        "handoff_revision_bound": False,
        "evidence_ids": ["ev_gsc_bdo"],
        "source_connectors": ["google_search_console"],
    }
    assert smoke.validate_planning_generation_status(
        {
            "status": "not_generated",
            "work_item_id": "content_work_item_bdo",
            "service_card_id": "service_bdo",
            "planning_input_digest": "b" * 64,
            "input_summary": {},
            "proposal": None,
            "runtime": {"status": "not_started"},
            "blockers": [],
            "safe_next_step": "Wygeneruj plan po decyzji operatora.",
            "publish_ready": False,
        },
        "content_work_item_bdo",
        "service_bdo",
    ) == {
        "status": "not_generated",
        "planning_input_digest": "b" * 64,
        "proposal_id": None,
        "runtime_status": "not_started",
        "blocker_codes": [],
    }
    assert smoke.validate_semantic_review_status(
        {
            "status": "not_generated",
            "work_item_id": "content_work_item_bdo",
            "revision_id": "revision_1",
            "revision_digest": "c" * 64,
            "review": None,
            "run_id": None,
            "runtime": {"status": "not_started"},
            "blockers": [],
            "safe_next_step": "Uruchom review po decyzji operatora.",
            "publish_ready": False,
            "human_review_required": True,
            "action_object_created": False,
        },
        "content_work_item_bdo",
        "revision_1",
        "c" * 64,
    ) == {
        "status": "not_generated",
        "revision_digest": "c" * 64,
        "runtime_status": "not_started",
        "blocker_codes": [],
    }


def test_content_operator_smoke_enforces_exact_bindings_but_accepts_stale_history() -> None:
    smoke = load_smoke_script()
    with pytest.raises(SystemExit, match="exact persisted bindings"):
        smoke.validate_planning_generation_status(
            {
                "status": "ready",
                "work_item_id": "content_work_item_bdo",
                "service_card_id": "service_bdo",
                "planning_input_digest": "a" * 64,
                "proposal": {
                    "proposal_id": "proposal_1",
                    "work_item_id": "content_work_item_other",
                    "service_card_id": "service_bdo",
                    "planning_input_digest": "a" * 64,
                },
                "runtime": {"status": "completed"},
                "blockers": [],
                "publish_ready": False,
            },
            "content_work_item_bdo",
            "service_bdo",
        )

    stale = smoke.validate_semantic_review_status(
        {
            "status": "stale",
            "work_item_id": "content_work_item_bdo",
            "revision_id": "revision_old",
            "revision_digest": "b" * 64,
            "review": {
                "work_item_id": "content_work_item_bdo",
                "revision_id": "revision_old",
                "revision_digest": "b" * 64,
                "codex_run_id": "run_old",
            },
            "run_id": "run_old",
            "runtime": {"status": "not_started"},
            "blockers": [],
            "publish_ready": False,
            "human_review_required": True,
            "action_object_created": False,
        },
        "content_work_item_bdo",
        "revision_current",
        "c" * 64,
    )
    assert stale["status"] == "stale"
    assert stale["revision_digest"] == "b" * 64

    with pytest.raises(SystemExit, match="Current semantic review binding mismatch"):
        smoke.validate_semantic_review_status(
            {
                "status": "ready",
                "work_item_id": "content_work_item_bdo",
                "revision_id": "revision_current",
                "revision_digest": "b" * 64,
                "review": {
                    "work_item_id": "content_work_item_bdo",
                    "revision_id": "revision_current",
                    "revision_digest": "b" * 64,
                    "codex_run_id": "run_current",
                },
                "run_id": "run_current",
                "runtime": {"status": "completed"},
                "blockers": [],
                "publish_ready": False,
                "human_review_required": True,
                "action_object_created": False,
            },
            "content_work_item_bdo",
            "revision_current",
            "c" * 64,
        )
