from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from tests.content.test_work_item_preflight_api import (
    _claim_ledger,
    _draft_claim_ledger,
    _enrichment,
    _handoff_audit,
    _human_review,
    _inventory_record,
    _item,
    _post_human_review,
    _post_preflight,
    _post_wordpress_handoff,
    _sales_brief_seed,
)


def _post_sales_brief(payload: dict[str, Any]) -> dict[str, Any]:
    response = TestClient(app).post("/api/content/work-items/sales-brief", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert sorted(data) == [
        "inventory_resolution",
        "item",
        "preflight_verdict",
        "sales_brief_result",
    ]
    return data


def _post_draft_package(payload: dict[str, Any]) -> dict[str, Any]:
    response = TestClient(app).post("/api/content/work-items/draft-package", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert sorted(data) == [
        "draft_package_result",
        "inventory_resolution",
        "item",
        "preflight_verdict",
        "sales_brief_result",
    ]
    return data


def test_content_work_item_sales_brief_api_builds_typed_brief() -> None:
    data = _post_sales_brief(
        {
            "item": _item(
                preserve_first_plan_status="approved",
                measurement_window_status="planned",
                measurement_window_id="measure_bdo",
            ),
            "inventory_records": [_inventory_record()],
            "duplicate_risk": "clear",
            "claim_ledger": _claim_ledger(),
            "seed": _sales_brief_seed(),
            "enrichment": _enrichment(),
        }
    )

    assert data["preflight_verdict"]["status"] == "brief_allowed"
    result = data["sales_brief_result"]
    assert result["blockers"] == []
    brief = result["brief"]
    assert brief["id"] == "sales_brief_content_work_item_bdo"
    assert brief["final_canonical_url"] == "https://ekologus.pl/bdo/"
    assert brief["existing_content_plan"].startswith("Zacznij od istniejącej treści")
    assert brief["evidence_ids"] == ["ev_gsc_bdo", "ev_wp_bdo"]
    assert brief["source_connectors"] == ["google_search_console", "wordpress_ekologus"]
    assert brief["measurement_plan"]["measurement_window_id"] == "measure_bdo"
    assert brief["draft_allowed"] is False
    assert [claim["claim_id"] for claim in brief["forbidden_claims"]] == [
        "claim_guarantee_bdo"
    ]
    assert "draft_package" not in data
    assert "wordpress_handoff" not in data


def test_content_work_item_sales_brief_api_blocks_missing_source_facts() -> None:
    data = _post_sales_brief(
        {
            "item": _item(
                preserve_first_plan_status="approved",
                measurement_window_status="planned",
                measurement_window_id="measure_bdo",
            ),
            "inventory_records": [_inventory_record()],
            "duplicate_risk": "clear",
            "claim_ledger": _claim_ledger(),
            "seed": _sales_brief_seed(source_facts=[]),
            "enrichment": _enrichment(),
        }
    )

    assert data["preflight_verdict"]["status"] == "brief_allowed"
    result = data["sales_brief_result"]
    assert result["brief"] is None
    assert [blocker["code"] for blocker in result["blockers"]] == ["missing_source_fact"]


def test_content_work_item_draft_package_api_returns_outline_only_package() -> None:
    data = _post_draft_package(
        {
            "item": _item(
                preflight_status="draft_allowed",
                preserve_first_plan_status="approved",
                sales_brief_status="approved",
                sales_brief_id="sales_brief_content_work_item_bdo",
                claim_ledger_status="approved",
                claim_ledger_id="claim_ledger_bdo",
                measurement_window_status="planned",
                measurement_window_id="measure_bdo",
            ),
            "inventory_records": [_inventory_record()],
            "duplicate_risk": "clear",
            "claim_ledger": _draft_claim_ledger(),
            "seed": _sales_brief_seed(),
            "enrichment": _enrichment(),
        }
    )

    assert data["preflight_verdict"]["status"] == "draft_allowed"
    assert data["sales_brief_result"]["brief"]["id"] == "sales_brief_content_work_item_bdo"
    result = data["draft_package_result"]
    assert result["blockers"] == []
    draft = result["draft_package"]
    assert draft["id"] == "draft_package_content_work_item_bdo"
    assert draft["draft_kind"] == "outline"
    assert draft["publish_ready"] is False
    assert draft["brief_id"] == "sales_brief_content_work_item_bdo"
    assert draft["claim_ledger_id"] == "claim_ledger_bdo"
    assert draft["section_to_evidence_map"][0]["evidence_ids"] == [
        "ev_gsc_bdo",
        "ev_wp_bdo",
    ]
    assert draft["human_review_questions"]
    assert "wordpress_handoff" not in data


def test_content_work_item_draft_package_api_blocks_before_draft_allowed() -> None:
    data = _post_draft_package(
        {
            "item": _item(
                preserve_first_plan_status="approved",
                measurement_window_status="planned",
                measurement_window_id="measure_bdo",
            ),
            "inventory_records": [_inventory_record()],
            "duplicate_risk": "clear",
            "claim_ledger": _draft_claim_ledger(),
            "seed": _sales_brief_seed(),
            "enrichment": _enrichment(),
        }
    )

    assert data["preflight_verdict"]["status"] == "brief_allowed"
    result = data["draft_package_result"]
    assert result["draft_package"] is None
    assert [blocker["code"] for blocker in result["blockers"]] == [
        "preflight_not_draft_allowed"
    ]


def test_content_work_item_draft_package_api_removes_blocked_claims() -> None:
    data = _post_draft_package(
        {
            "item": _item(
                preflight_status="draft_allowed",
                preserve_first_plan_status="approved",
                sales_brief_status="approved",
                sales_brief_id="sales_brief_content_work_item_bdo",
                claim_ledger_status="approved",
                claim_ledger_id="claim_ledger_bdo",
                measurement_window_status="planned",
                measurement_window_id="measure_bdo",
            ),
            "inventory_records": [_inventory_record()],
            "duplicate_risk": "clear",
            "claim_ledger": _claim_ledger(),
            "seed": _sales_brief_seed(),
            "enrichment": _enrichment(),
        }
    )

    result = data["draft_package_result"]
    assert result["blockers"] == []
    draft = result["draft_package"]
    assert draft["claims_used"] == ["Ekologus pomaga firmom uporządkować obowiązki BDO."]
    assert draft["claims_removed_or_blocked"] == [
        "Po wdrożeniu treści liczba leadów wzrośnie."
    ]


def _build_chain_sales_brief() -> dict[str, Any]:
    sales_brief = _post_sales_brief(
        {
            "item": _item(
                preserve_first_plan_status="approved",
                measurement_window_status="planned",
                measurement_window_id="measure_bdo",
            ),
            "inventory_records": [_inventory_record()],
            "duplicate_risk": "clear",
            "claim_ledger": _draft_claim_ledger(),
            "seed": _sales_brief_seed(),
            "enrichment": _enrichment(),
        }
    )
    brief = sales_brief["sales_brief_result"]["brief"]
    assert brief["id"] == "sales_brief_content_work_item_bdo"
    assert brief["evidence_ids"] == ["ev_gsc_bdo", "ev_wp_bdo"]
    return brief


def _build_chain_draft_package(brief: dict[str, Any]) -> dict[str, Any]:
    draft_package = _post_draft_package(
        {
            "item": _item(
                preflight_status="draft_allowed",
                preserve_first_plan_status="approved",
                sales_brief_status="approved",
                sales_brief_id=brief["id"],
                claim_ledger_status="approved",
                claim_ledger_id="claim_ledger_bdo",
                measurement_window_status="planned",
                measurement_window_id="measure_bdo",
            ),
            "inventory_records": [_inventory_record()],
            "duplicate_risk": "clear",
            "claim_ledger": _draft_claim_ledger(),
            "seed": _sales_brief_seed(),
            "enrichment": _enrichment(),
            "sales_brief": brief,
        }
    )
    draft = draft_package["draft_package_result"]["draft_package"]
    assert draft["id"] == "draft_package_content_work_item_bdo"
    assert draft["brief_id"] == brief["id"]
    assert draft["publish_ready"] is False
    assert draft["section_to_evidence_map"][0]["evidence_ids"] == [
        "ev_gsc_bdo",
        "ev_wp_bdo",
    ]
    return draft


def _approve_chain_human_review(
    brief: dict[str, Any], draft: dict[str, Any]
) -> dict[str, Any]:
    human_review = _post_human_review(
        {
            "item": _item(
                preflight_status="handoff_allowed",
                preserve_first_plan_status="approved",
                sales_brief_status="approved",
                sales_brief_id=brief["id"],
                claim_ledger_status="approved",
                claim_ledger_id="claim_ledger_bdo",
                draft_package_status="ready",
                draft_package_id=draft["id"],
                audit_status="recorded",
                audit_id="audit_bdo",
                measurement_window_status="planned",
                measurement_window_id="measure_bdo",
            ),
            "review": _human_review(draft_package_id=draft["id"]),
            "draft_package": draft,
            "claim_ledger": _draft_claim_ledger(),
        }
    )
    reviewed_item = human_review["reviewed_item"]
    assert human_review["wordpress_handoff_allowed"] is True
    assert reviewed_item["human_review_status"] == "approved"
    return reviewed_item


def _build_chain_wordpress_handoff(
    reviewed_item: dict[str, Any], draft: dict[str, Any]
) -> dict[str, Any]:
    wordpress_handoff = _post_wordpress_handoff(
        {
            "item": reviewed_item,
            "draft_package": draft,
            "human_review": _human_review(draft_package_id=draft["id"]),
            "audit": _handoff_audit(),
        }
    )
    handoff = wordpress_handoff["handoff_result"]["handoff"]
    assert handoff["post_status"] == "draft"
    assert handoff["publish_allowed"] is False
    assert handoff["destructive_update_allowed"] is False
    assert handoff["evidence_ids"] == ["ev_gsc_bdo", "ev_wp_bdo"]
    return handoff


def test_content_work_item_api_chain_keeps_all_content_production_gates() -> None:
    preflight = _post_preflight(
        {
            "item": _item(),
            "inventory_records": [_inventory_record()],
            "duplicate_risk": "clear",
        }
    )
    assert preflight["preflight_verdict"]["status"] == "plan_allowed"
    assert preflight["preflight_verdict"]["evidence_ids"] == ["ev_gsc_bdo", "ev_wp_bdo"]

    brief = _build_chain_sales_brief()
    draft = _build_chain_draft_package(brief)
    reviewed_item = _approve_chain_human_review(brief, draft)
    _build_chain_wordpress_handoff(reviewed_item, draft)
