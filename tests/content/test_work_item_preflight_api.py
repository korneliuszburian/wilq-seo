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


def _draft_package(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "draft_package_content_work_item_bdo",
        "work_item_id": "content_work_item_bdo",
        "brief_id": "sales_brief_content_work_item_bdo",
        "claim_ledger_id": "claim_ledger_bdo",
        "draft_kind": "outline",
        "title": "BDO dla firm: co trzeba sprawdzić przed działaniem",
        "sections": [
            {
                "heading": "Kogo dotyczy BDO",
                "purpose": "Sekcja outline-first do napisania po review briefu.",
                "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
                "draft_notes": ["CTA bez obietnicy wyniku."],
            }
        ],
        "section_to_evidence_map": [
            {
                "section_heading": "Kogo dotyczy BDO",
                "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
            }
        ],
        "claims_used": ["Ekologus pomaga firmom uporządkować obowiązki BDO."],
        "claims_removed_or_blocked": [],
        "human_review_questions": [
            "Czy szkic brzmi jak Ekologus?",
            "Czy claimy mają dowody?",
        ],
        "publish_ready": False,
    }
    payload.update(overrides)
    return payload


def _human_review(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "human_review_bdo",
        "work_item_id": "content_work_item_bdo",
        "stage": "draft_package",
        "reviewed_by": "wilku",
        "decision": "approved",
        "notes": "Szkic może iść dalej jako WordPress draft.",
        "checked_items": [
            "brief zgodny z dowodami",
            "claimy bez gwarancji efektu",
            "CTA bez obietnicy wyniku",
        ],
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "blocked_claims_handled": [],
        "draft_package_id": "draft_package_content_work_item_bdo",
    }
    payload.update(overrides)
    return payload


def _handoff_audit(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "audit_id": "audit_bdo",
        "actor": "wilku",
        "reason": "Zatwierdzony szkic może trafić do WordPress jako draft.",
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "human_review_id": "human_review_bdo",
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


def _post_human_review(payload: dict[str, Any]) -> dict[str, Any]:
    response = TestClient(app).post("/api/content/work-items/human-review", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert sorted(data) == [
        "blockers",
        "item",
        "review",
        "reviewed_item",
        "wordpress_handoff_allowed",
    ]
    return data


def _post_wordpress_handoff(payload: dict[str, Any]) -> dict[str, Any]:
    response = TestClient(app).post(
        "/api/content/work-items/wordpress-draft-handoff",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert sorted(data) == ["handoff_result", "item"]
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


def test_content_work_item_human_review_api_updates_approved_review_state() -> None:
    data = _post_human_review(
        {
            "item": _item(
                preflight_status="handoff_allowed",
                preserve_first_plan_status="approved",
                sales_brief_status="approved",
                sales_brief_id="sales_brief_content_work_item_bdo",
                claim_ledger_status="approved",
                claim_ledger_id="claim_ledger_bdo",
                draft_package_status="ready",
                draft_package_id="draft_package_content_work_item_bdo",
                audit_status="recorded",
                audit_id="audit_bdo",
                measurement_window_status="planned",
                measurement_window_id="measure_bdo",
            ),
            "review": _human_review(),
            "draft_package": _draft_package(),
            "claim_ledger": _draft_claim_ledger(),
        }
    )

    assert data["blockers"] == []
    assert data["reviewed_item"]["human_review_status"] == "approved"
    assert data["reviewed_item"]["human_review_id"] == "human_review_bdo"
    assert data["wordpress_handoff_allowed"] is True
    assert "wordpress_handoff" not in data


def test_content_work_item_human_review_api_blocks_missing_review_evidence() -> None:
    data = _post_human_review(
        {
            "item": _item(),
            "review": _human_review(reviewed_by=" ", checked_items=[], evidence_ids=[]),
            "draft_package": _draft_package(),
        }
    )

    assert data["reviewed_item"]["human_review_status"] == "missing"
    assert data["wordpress_handoff_allowed"] is False
    assert {blocker["code"] for blocker in data["blockers"]} == {
        "missing_reviewer",
        "missing_checked_items",
        "missing_evidence",
    }


def test_content_work_item_human_review_api_blocks_needs_changes() -> None:
    data = _post_human_review(
        {
            "item": _item(),
            "review": _human_review(decision="needs_changes"),
            "draft_package": _draft_package(),
        }
    )

    assert data["wordpress_handoff_allowed"] is False
    assert "not_approved" in [blocker["code"] for blocker in data["blockers"]]


def test_content_work_item_human_review_api_requires_blocked_claim_handling() -> None:
    data = _post_human_review(
        {
            "item": _item(),
            "review": _human_review(),
            "draft_package": _draft_package(),
            "claim_ledger": _claim_ledger(),
        }
    )

    assert data["wordpress_handoff_allowed"] is False
    assert [blocker["code"] for blocker in data["blockers"]] == [
        "unhandled_blocked_claims"
    ]


def test_content_work_item_wordpress_handoff_api_prepares_draft_only_handoff() -> None:
    data = _post_wordpress_handoff(
        {
            "item": _item(
                preflight_status="handoff_allowed",
                preserve_first_plan_status="approved",
                sales_brief_status="approved",
                sales_brief_id="sales_brief_content_work_item_bdo",
                claim_ledger_status="approved",
                claim_ledger_id="claim_ledger_bdo",
                draft_package_status="ready",
                draft_package_id="draft_package_content_work_item_bdo",
                human_review_status="approved",
                human_review_id="human_review_bdo",
                audit_status="recorded",
                audit_id="audit_bdo",
                measurement_window_status="planned",
                measurement_window_id="measure_bdo",
            ),
            "draft_package": _draft_package(),
            "human_review": _human_review(),
            "audit": _handoff_audit(),
        }
    )

    result = data["handoff_result"]
    assert result["blockers"] == []
    handoff = result["handoff"]
    assert handoff["id"] == "wordpress_draft_handoff_content_work_item_bdo"
    assert handoff["status"] == "prepared"
    assert handoff["post_status"] == "draft"
    assert handoff["publish_allowed"] is False
    assert handoff["destructive_update_allowed"] is False
    assert handoff["final_canonical_url"] == "https://ekologus.pl/bdo/"
    assert handoff["evidence_ids"] == ["ev_gsc_bdo", "ev_wp_bdo"]


def test_content_work_item_wordpress_handoff_api_blocks_missing_audit() -> None:
    data = _post_wordpress_handoff(
        {
            "item": _item(
                draft_package_status="ready",
                draft_package_id="draft_package_content_work_item_bdo",
                human_review_status="approved",
                human_review_id="human_review_bdo",
            ),
            "draft_package": _draft_package(),
            "human_review": _human_review(),
            "audit": None,
        }
    )

    assert data["handoff_result"]["handoff"] is None
    assert [blocker["code"] for blocker in data["handoff_result"]["blockers"]] == [
        "missing_audit"
    ]


def test_content_work_item_wordpress_handoff_api_blocks_non_approved_review() -> None:
    data = _post_wordpress_handoff(
        {
            "item": _item(
                draft_package_status="ready",
                draft_package_id="draft_package_content_work_item_bdo",
                human_review_status="needs_changes",
                human_review_id="human_review_bdo",
            ),
            "draft_package": _draft_package(),
            "human_review": _human_review(decision="needs_changes"),
            "audit": _handoff_audit(),
        }
    )

    assert data["handoff_result"]["handoff"] is None
    assert "human_review_not_approved" in [
        blocker["code"] for blocker in data["handoff_result"]["blockers"]
    ]


def test_content_work_item_wordpress_handoff_api_blocks_dev_canonical() -> None:
    data = _post_wordpress_handoff(
        {
            "item": _item(
                final_canonical_url="https://ekologus.dev.proudsite.pl/bdo/",
                draft_package_status="ready",
                draft_package_id="draft_package_content_work_item_bdo",
                human_review_status="approved",
                human_review_id="human_review_bdo",
            ),
            "draft_package": _draft_package(),
            "human_review": _human_review(),
            "audit": _handoff_audit(),
        }
    )

    assert data["handoff_result"]["handoff"] is None
    assert "invalid_final_canonical" in [
        blocker["code"] for blocker in data["handoff_result"]["blockers"]
    ]
