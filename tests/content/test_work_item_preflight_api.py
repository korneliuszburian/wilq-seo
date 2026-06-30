from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app


def _item(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "content_work_item_bdo",
        "topic": "BDO dla firm",
        "source_public_url": "https://ekologus.pl/bdo/",
        "final_canonical_url": "https://ekologus.pl/bdo/",
        "intended_final_url": "https://ekologus.pl/bdo/",
        "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "source_connectors": ["google_search_console", "wordpress_ekologus"],
        "inventory_status": "resolved",
        "canonical_status": "resolved",
        "duplicate_status": "checked",
    }
    payload.update(overrides)
    return payload


def _inventory_record(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "inventory_bdo",
        "url": "https://ekologus.pl/bdo/",
        "final_canonical_url": "https://ekologus.pl/bdo/",
        "intended_final_url": "https://ekologus.pl/bdo/",
        "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
        "content_status": "published",
        "source_connectors": ["wordpress_ekologus"],
        "evidence_ids": ["ev_wp_bdo"],
        "title": "BDO dla firm",
        "h1": "BDO dla firm",
        "topic_tags": ["bdo"],
    }
    payload.update(overrides)
    return payload


def _claim_ledger(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "claim_ledger_bdo",
        "work_item_id": "content_work_item_bdo",
        "reviewed_by": "wilku",
        "entries": [
            {
                "id": "claim_general_bdo",
                "claim_text": "Ekologus pomaga firmom uporządkować obowiązki BDO.",
                "claim_type": "service_claim",
                "status": "allowed_with_evidence",
                "evidence_ids": ["ev_wp_bdo"],
                "reason": "Claim ma przypisany dowód źródłowy.",
                "reviewer_id": "wilku",
            },
            {
                "id": "claim_guarantee_bdo",
                "claim_text": "Po wdrożeniu treści liczba leadów wzrośnie.",
                "claim_type": "guarantee_claim",
                "status": "blocked",
                "evidence_ids": [],
                "reason": "Gwarancje efektu nie mogą być użyte jako publish-ready language.",
            },
        ],
    }
    payload.update(overrides)
    return payload


def _draft_claim_ledger(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "claim_ledger_bdo",
        "work_item_id": "content_work_item_bdo",
        "reviewed_by": "wilku",
        "entries": [
            {
                "id": "claim_general_bdo",
                "claim_text": "Ekologus pomaga firmom uporządkować obowiązki BDO.",
                "claim_type": "service_claim",
                "status": "allowed_with_evidence",
                "evidence_ids": ["ev_wp_bdo"],
                "reason": "Claim ma przypisany dowód źródłowy.",
                "reviewer_id": "wilku",
            }
        ],
    }
    payload.update(overrides)
    return payload


def _sales_brief_seed(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "target_reader": "właściciel firmy, który musi uporządkować obowiązki BDO",
        "buyer_problem": "nie wie, czy i jak musi prowadzić ewidencję BDO",
        "buyer_trigger": "zbliża się kontrola albo termin aktualizacji danych",
        "search_intent": "informacyjno-usługowy",
        "service_fit": "konsultacja i obsługa środowiskowa Ekologus",
        "h1_direction": "BDO dla firm: co trzeba sprawdzić przed działaniem",
        "h2_direction": ["Kogo dotyczy BDO", "Co warto przygotować przed konsultacją"],
        "faq_direction": ["Czy każda firma musi mieć BDO?"],
        "cta_direction": "Zaproponuj kontakt w celu sprawdzenia sytuacji firmy.",
        "internal_link_direction": ["https://ekologus.pl/kontakt/"],
        "source_facts": [
            {
                "evidence_id": "ev_gsc_bdo",
                "source_connector": "google_search_console",
                "summary": "GSC pokazuje popyt na temat BDO.",
            },
            {
                "evidence_id": "ev_wp_bdo",
                "source_connector": "wordpress_ekologus",
                "summary": "WordPress inventory potwierdza istniejącą treść BDO.",
            },
        ],
        "missing_evidence": [],
    }
    payload.update(overrides)
    return payload


def _post_preflight(payload: dict[str, Any]) -> dict[str, Any]:
    response = TestClient(app).post("/api/content/work-items/preflight", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert sorted(data) == ["inventory_resolution", "item", "preflight_verdict"]
    return data


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


def test_content_work_item_preflight_api_blocks_dev_preview_canonical() -> None:
    data = _post_preflight(
        {
            "item": _item(final_canonical_url="https://ekologus.dev.proudsite.pl/bdo/"),
            "inventory_records": [
                _inventory_record(
                    final_canonical_url="https://ekologus.dev.proudsite.pl/bdo/"
                )
            ],
            "duplicate_risk": "clear",
        }
    )

    assert data["inventory_resolution"]["status"] == "blocked"
    assert data["inventory_resolution"]["recommended_mode"] == "block"
    assert data["preflight_verdict"]["status"] == "blocked"
    assert data["preflight_verdict"]["wordpress_draft_allowed"] is False
    assert [blocker["code"] for blocker in data["preflight_verdict"]["blockers"]] == [
        "invalid_final_canonical"
    ]


def test_content_work_item_preflight_api_preserves_evidence_for_valid_item() -> None:
    data = _post_preflight(
        {
            "item": _item(),
            "inventory_records": [_inventory_record()],
            "duplicate_risk": "clear",
        }
    )

    assert data["inventory_resolution"]["status"] == "resolved"
    assert data["inventory_resolution"]["recommended_mode"] == "preserve"
    assert data["preflight_verdict"]["status"] == "plan_allowed"
    assert data["preflight_verdict"]["sales_brief_allowed"] is False
    assert data["preflight_verdict"]["evidence_ids"] == ["ev_gsc_bdo", "ev_wp_bdo"]
    assert data["preflight_verdict"]["source_connectors"] == [
        "google_search_console",
        "wordpress_ekologus",
    ]
    assert "https://ekologus.pl/bdo/" in data["preflight_verdict"]["similar_existing_urls"]


def test_existing_content_preflight_endpoint_shape_stays_unchanged() -> None:
    response = TestClient(app).get("/api/content/preflight")
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "primary_item" in data
    assert data["items"]
    first_plan = data["primary_item"]
    assert "recommended_mode" in first_plan
    assert "inventory_gate_status" in first_plan
    assert "canonical_gate_status" in first_plan
    assert "draft_allowed" in first_plan
    assert "preflight_verdict" not in data


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
        }
    )

    assert data["preflight_verdict"]["status"] == "brief_allowed"
    result = data["draft_package_result"]
    assert result["draft_package"] is None
    assert [blocker["code"] for blocker in result["blockers"]] == [
        "preflight_not_draft_allowed"
    ]


def test_content_work_item_draft_package_api_blocks_unresolved_claims() -> None:
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
        }
    )

    result = data["draft_package_result"]
    assert result["draft_package"] is None
    assert [blocker["code"] for blocker in result["blockers"]] == [
        "claim_ledger_blocks_draft"
    ]
