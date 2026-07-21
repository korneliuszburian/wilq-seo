from __future__ import annotations

from pathlib import Path
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
                "source_connectors": ["wordpress_ekologus"],
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
                "source_connectors": ["wordpress_ekologus"],
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


def _enrichment(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "content_opportunity_enrichment_content_work_item_bdo",
        "work_item_id": "content_work_item_bdo",
        "decision_id": "bdo",
        "status": "ready",
        "title": "BDO dla firm",
        "topic": "BDO dla firm",
        "recommended_mode": "refresh",
        "intent": "compliance_risk",
        "intent_label": "intencja ryzyka lub obowiązku",
        "buyer_problem": "Firma nie wie, czy obowiązki BDO dotyczą jej sytuacji.",
        "buyer_trigger": "obawa przed błędem formalnym, terminem albo kontrolą",
        "service_fit": "obsługa środowiskowa i zgodność obowiązków",
        "cta_hypothesis": "Zaproponuj konsultację obowiązków bez gwarancji wyniku.",
        "source_facts": [],
        "measurement_baseline": {
            "status": "ready_to_plan",
            "label": "baza pomiaru do zaplanowania",
            "reason": "GSC i WordPress dają bazę do późniejszego pomiaru.",
            "metrics_to_watch": ["gsc_clicks", "gsc_impressions"],
            "source_connectors": ["google_search_console"],
            "evidence_ids": ["ev_gsc_bdo"],
        },
        "blockers": [],
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "source_connectors": ["google_search_console", "wordpress_ekologus"],
        "safe_next_step": "Przygotuj preserve-first brief.",
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


def _wordpress_handoff(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "wordpress_draft_handoff_content_work_item_bdo",
        "work_item_id": "content_work_item_bdo",
        "draft_package_id": "draft_package_content_work_item_bdo",
        "human_review_id": "human_review_bdo",
        "audit_id": "audit_bdo",
        "title": "BDO dla firm: co trzeba sprawdzić przed działaniem",
        "final_canonical_url": "https://ekologus.pl/bdo/",
        "intended_final_url": "https://ekologus.pl/bdo/",
        "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
    }
    payload.update(overrides)
    return payload


def _post_preflight(payload: dict[str, Any]) -> dict[str, Any]:
    response = TestClient(app).post("/api/content/work-items/preflight", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert sorted(data) == ["inventory_resolution", "item", "preflight_verdict"]
    return data


def _post_human_review(payload: dict[str, Any]) -> dict[str, Any]:
    response = TestClient(app).post("/api/content/work-items/human-review", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert sorted(data) == [
        "blockers",
        "item",
        "review",
        "review_recordable",
        "review_recorded",
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
                _inventory_record(final_canonical_url="https://ekologus.dev.proudsite.pl/bdo/")
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
    assert data["review_recordable"] is True
    assert data["review_recorded"] is False
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

    assert data["review_recordable"] is True
    assert data["review_recorded"] is False
    assert data["reviewed_item"]["human_review_status"] == "needs_changes"
    assert data["reviewed_item"]["human_review_id"] == "human_review_bdo"
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
    assert [blocker["code"] for blocker in data["blockers"]] == ["unhandled_blocked_claims"]


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
    assert [blocker["code"] for blocker in data["handoff_result"]["blockers"]] == ["missing_audit"]


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


def test_content_work_item_snapshot_is_derived_from_content_diagnostics(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)
    diagnostics = client.get("/api/content/diagnostics").json()
    source_decision = next(
        decision
        for decision in diagnostics["decision_queue"]
        if decision["status"] == "ready"
        and decision.get("final_canonical_url")
        and decision.get("evidence_ids")
        and decision.get("source_connectors")
    )

    response = client.get("/api/content/work-items/snapshot")
    assert response.status_code == 200
    data = response.json()

    item = data["preflight"]["item"]
    assert item["id"] == f"content_work_item_{source_decision['id']}"
    # The marketer-facing topic uses the exact WordPress title/H1 when the
    # selected inventory row has one; the diagnostics queue title may be a
    # decision label such as “Istniejący URL …”.
    assert item["topic"] == (
        source_decision.get("wordpress_title_or_h1") or source_decision["title"]
    )
    assert item["source_public_url"] == source_decision["source_public_url"]
    assert item["final_canonical_url"] == source_decision["final_canonical_url"]
    assert item["preview_url"] == source_decision["preview_url"]
    # Snapshot enrichment preserves the selected decision lineage and may add
    # exact inventory/metric evidence from the same page.
    assert set(source_decision["evidence_ids"]).issubset(item["evidence_ids"])
    assert set(source_decision["source_connectors"]).issubset(item["source_connectors"])
    assert item["id"] != "content_work_item_bdo"

    preflight = data["preflight"]["preflight_verdict"]
    assert preflight["status"] == "plan_allowed"
    assert preflight["final_canonical_url"] == source_decision["final_canonical_url"]
    assert set(source_decision["source_connectors"]).issubset(
        preflight["source_connectors"]
    )

    generation_readiness = data["structured_generation_readiness"]
    brief_result = data["sales_brief"]["sales_brief_result"]
    brief = brief_result["brief"]
    if brief is None:
        assert [blocker["code"] for blocker in brief_result["blockers"]] == [
            "missing_required_knowledge_card",
            "missing_required_knowledge_card",
        ]
        assert {
            "missing_sales_brief",
            "missing_draft_package",
        }.issubset(
            {blocker["code"] for blocker in generation_readiness["blockers"]}
        )
        assert generation_readiness["status"] == "blocked"
        assert generation_readiness["editable_section_headings"] == []
    else:
        assert brief["work_item_id"] == item["id"]
        assert brief["final_canonical_url"] == source_decision["final_canonical_url"]
        assert generation_readiness["publish_ready"] is False
        if generation_readiness["status"] == "ready":
            assert generation_readiness["blockers"] == []
            draft = data["draft_package"]["draft_package_result"]["draft_package"]
            assert generation_readiness["editable_section_headings"] == [
                section["heading"] for section in draft["sections"]
            ]
        else:
            assert generation_readiness["status"] == "blocked"
            assert generation_readiness["blockers"]

    human_review = data["human_review"]
    assert human_review["review"] is None
    assert human_review["reviewed_item"]["human_review_status"] == "missing"
    assert human_review["wordpress_handoff_allowed"] is False
    assert [blocker["code"] for blocker in human_review["blockers"]] == ["missing_human_review"]

    handoff_result = data["wordpress_handoff"]["handoff_result"]
    assert handoff_result["handoff"] is None
    handoff_blocker_codes = [blocker["code"] for blocker in handoff_result["blockers"]]
    if brief is None:
        assert handoff_blocker_codes == [
            "missing_draft_package",
            "missing_human_review",
            "missing_audit",
        ]
    else:
        assert handoff_blocker_codes == [
            "missing_human_review",
            "missing_audit",
        ]

    measurement = data["measurement_window"]
    assert measurement["measurement_window_result"]["window"] is None
    assert [
        blocker["code"] for blocker in measurement["measurement_window_result"]["blockers"]
    ] == [
        "missing_publication_event"
    ]
    assert measurement["outcome_blockers"] == []

    operator_steps = data["operator_steps"]
    assert [step["id"] for step in operator_steps] == [
        "scope",
        "section_map",
        "draft",
        "review",
        "dev_draft",
    ]
    assert [step["title"] for step in operator_steps] == [
        "Zakres i cel",
        "Plan sekcji",
        "Szkic treści",
        "Sprawdzenie treści",
        "Szkic na devie",
    ]
    current_steps = [step for step in operator_steps if step["phase"] == "current"]
    assert len(current_steps) == 1
    assert current_steps[0]["id"] == data["current_step_id"]
    assert all(
        {
            "id",
            "title",
            "phase",
            "readiness",
            "status_label",
            "summary",
            "can_open",
            "can_submit",
            "blocker",
            "safe_next_step",
        }.issubset(step)
        for step in operator_steps
    )
    draft_package = data["draft_package"]["draft_package_result"]["draft_package"]
    planning_workspace = data["planning_workspace"]
    if brief is None or brief["signal_quality"]["status"] == "thin":
        assert data["current_step_id"] == "scope"
    elif draft_package is None:
        # Section mapping is an API-owned projection. The marketer stays on
        # scope while the generated plan is being produced; no map approval
        # step is exposed.
        assert data["current_step_id"] == "scope"
    elif (
        not planning_workspace["scope_current"]
        or not planning_workspace["section_map_current"]
    ):
        assert data["current_step_id"] == "scope"
    else:
        assert data["current_step_id"] == "draft"
        draft_step = current_steps[0]
        assert draft_step["can_open"] is True
        assert draft_step["can_submit"] is True
        assert draft_step["readiness"] == "review_required"
        assert draft_step["blocker"]["code"] == "missing_revision_bound_draft"
        assert [step["phase"] for step in operator_steps[:2]] == [
            "complete",
            "complete",
        ]
        assert all(step["can_open"] is True for step in operator_steps[:3])
        assert all(step["phase"] == "pending" for step in operator_steps[3:])
        assert all(step["can_open"] is False for step in operator_steps[3:])
    operator_text = " ".join(
        " ".join(
            value
            for value in (
                step["title"],
                step["status_label"],
                step["summary"],
                step["safe_next_step"],
                "" if step["blocker"] is None else step["blocker"]["reason"],
            )
            if value
        )
        for step in operator_steps
    )
    assert "/api/content" not in operator_text
    assert "ContentWorkItem" not in operator_text
    assert "workflow" not in operator_text.lower()


def _snapshot_blocks_draft_on_missing_knowledge(snapshot: dict[str, Any]) -> bool:
    brief_result = snapshot["sales_brief"]["sales_brief_result"]
    draft_result = snapshot["draft_package"]["draft_package_result"]
    generation_readiness = snapshot["structured_generation_readiness"]
    return (
        brief_result["brief"] is None
        and [blocker["code"] for blocker in brief_result["blockers"]]
        == ["missing_required_knowledge_card", "missing_required_knowledge_card"]
        and draft_result["draft_package"] is None
        and "missing_sales_brief" in {blocker["code"] for blocker in draft_result["blockers"]}
        and generation_readiness["status"] == "blocked"
        and generation_readiness["editable_section_headings"] == []
    )


def test_content_work_item_snapshot_persists_real_human_review(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)

    initial = client.get("/api/content/work-items/snapshot").json()
    item = initial["preflight"]["item"]
    draft = initial["draft_package"]["draft_package_result"]["draft_package"]
    if draft is None:
        assert _snapshot_blocks_draft_on_missing_knowledge(initial)
        return
    review = _human_review(
        id=f"human_review_{item['id']}",
        work_item_id=item["id"],
        evidence_ids=item["evidence_ids"],
        draft_package_id=draft["id"],
        blocked_claims_handled=draft["claims_removed_or_blocked"],
    )

    response = client.post(
        "/api/content/work-items/snapshot/human-review",
        json={"review": review},
    )
    assert response.status_code == 200
    assert response.json()["wordpress_handoff_allowed"] is True

    persisted = client.get("/api/content/work-items/snapshot").json()
    human_review = persisted["human_review"]
    assert human_review["review"]["id"] == review["id"]
    assert human_review["reviewed_item"]["human_review_status"] == "approved"
    assert human_review["review_recorded"] is True
    assert human_review["wordpress_handoff_allowed"] is True

    handoff_result = persisted["wordpress_handoff"]["handoff_result"]
    assert handoff_result["handoff"] is None
    assert [blocker["code"] for blocker in handoff_result["blockers"]] == ["missing_audit"]
    assert persisted["current_step_id"] == "scope"
    journey = {step["id"]: step for step in persisted["operator_steps"]}
    assert journey["scope"]["phase"] == "current"
    assert journey["draft"]["phase"] == "pending"
    assert journey["review"]["phase"] == "pending"
    assert journey["review"]["can_submit"] is False


def test_content_work_item_snapshot_does_not_persist_wrong_work_item_review(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)

    initial = client.get("/api/content/work-items/snapshot").json()
    item = initial["preflight"]["item"]
    draft = initial["draft_package"]["draft_package_result"]["draft_package"]
    if draft is None:
        assert _snapshot_blocks_draft_on_missing_knowledge(initial)
        return

    response = client.post(
        "/api/content/work-items/snapshot/human-review",
        json={
            "review": _human_review(
                id=f"human_review_{item['id']}",
                work_item_id="content_work_item_wrong",
                evidence_ids=item["evidence_ids"],
                draft_package_id=draft["id"],
            )
        },
    )
    assert response.status_code == 200
    assert response.json()["review_recordable"] is False
    assert response.json()["review_recorded"] is False
    assert response.json()["wordpress_handoff_allowed"] is False
    assert "wrong_work_item" in [blocker["code"] for blocker in response.json()["blockers"]]

    persisted = client.get("/api/content/work-items/snapshot").json()
    assert persisted["human_review"]["review"] is None
    assert persisted["human_review"]["reviewed_item"]["human_review_status"] == "missing"


def test_content_work_item_snapshot_persists_needs_changes_without_allowing_handoff(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)

    initial = client.get("/api/content/work-items/snapshot").json()
    item = initial["preflight"]["item"]
    draft = initial["draft_package"]["draft_package_result"]["draft_package"]
    if draft is None:
        assert _snapshot_blocks_draft_on_missing_knowledge(initial)
        return
    review = _human_review(
        id=f"human_review_{item['id']}_needs_changes",
        work_item_id=item["id"],
        decision="needs_changes",
        evidence_ids=item["evidence_ids"],
        draft_package_id=draft["id"],
        blocked_claims_handled=draft["claims_removed_or_blocked"],
    )

    response = client.post(
        "/api/content/work-items/snapshot/human-review",
        json={"review": review},
    )

    assert response.status_code == 200
    assert response.json()["review_recordable"] is True
    assert response.json()["review_recorded"] is True
    assert response.json()["reviewed_item"]["human_review_status"] == "needs_changes"
    assert response.json()["wordpress_handoff_allowed"] is False

    persisted = client.get("/api/content/work-items/snapshot").json()["human_review"]
    assert persisted["review"]["id"] == review["id"]
    assert persisted["reviewed_item"]["human_review_status"] == "needs_changes"
    assert persisted["review_recorded"] is True
    assert persisted["wordpress_handoff_allowed"] is False


def test_content_work_item_snapshot_persists_matching_audit_envelope(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)

    initial = client.get("/api/content/work-items/snapshot").json()
    item = initial["preflight"]["item"]
    draft = initial["draft_package"]["draft_package_result"]["draft_package"]
    if draft is None:
        assert _snapshot_blocks_draft_on_missing_knowledge(initial)
        return
    review = _human_review(
        id=f"human_review_{item['id']}",
        work_item_id=item["id"],
        evidence_ids=item["evidence_ids"],
        draft_package_id=draft["id"],
        blocked_claims_handled=draft["claims_removed_or_blocked"],
    )
    client.post("/api/content/work-items/snapshot/human-review", json={"review": review})

    audit = {
        "audit_id": f"audit_{item['id']}",
        "actor": "wilku",
        "reason": "Zatwierdzony szkic może trafić do WordPress jako draft.",
        "evidence_ids": item["evidence_ids"],
        "human_review_id": review["id"],
    }
    response = client.post("/api/content/work-items/snapshot/audit", json={"audit": audit})
    assert response.status_code == 200
    assert response.json()["handoff_result"]["blockers"] == []

    persisted = client.get("/api/content/work-items/snapshot").json()
    handoff = persisted["wordpress_handoff"]["handoff_result"]["handoff"]
    assert handoff["post_status"] == "draft"
    assert handoff["publish_allowed"] is False
    assert handoff["destructive_update_allowed"] is False
    assert handoff["human_review_id"] == review["id"]
    assert handoff["audit_id"] == audit["audit_id"]
    assert handoff["evidence_ids"] == item["evidence_ids"]

    measurement = persisted["measurement_window"]
    assert measurement["measurement_window_result"]["window"] is None
    assert measurement["measurement_window_result"]["blockers"][0]["code"] == (
        "missing_publication_event"
    )
    assert persisted["current_step_id"] == "scope"
    operator_steps = {step["id"]: step for step in persisted["operator_steps"]}
    assert operator_steps["scope"]["phase"] == "current"
    assert operator_steps["draft"]["phase"] == "pending"
    assert operator_steps["review"]["phase"] == "pending"
    assert operator_steps["review"]["blocker"]["code"] == (
        "missing_revision_bound_draft"
    )
    assert operator_steps["dev_draft"]["phase"] == "pending"
    assert operator_steps["dev_draft"]["can_submit"] is False


def test_content_work_item_snapshot_does_not_persist_mismatched_audit(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)

    initial = client.get("/api/content/work-items/snapshot").json()
    item = initial["preflight"]["item"]
    draft = initial["draft_package"]["draft_package_result"]["draft_package"]
    if draft is None:
        assert _snapshot_blocks_draft_on_missing_knowledge(initial)
        return
    review = _human_review(
        id=f"human_review_{item['id']}",
        work_item_id=item["id"],
        evidence_ids=item["evidence_ids"],
        draft_package_id=draft["id"],
        blocked_claims_handled=draft["claims_removed_or_blocked"],
    )
    client.post("/api/content/work-items/snapshot/human-review", json={"review": review})

    response = client.post(
        "/api/content/work-items/snapshot/audit",
        json={
            "audit": {
                "audit_id": f"audit_{item['id']}",
                "actor": "wilku",
                "reason": "Zatwierdzony szkic może trafić do WordPress jako draft.",
                "evidence_ids": item["evidence_ids"],
                "human_review_id": "human_review_other",
            }
        },
    )
    assert response.status_code == 200
    assert response.json()["handoff_result"]["handoff"] is None
    assert "audit_human_review_mismatch" in [
        blocker["code"] for blocker in response.json()["handoff_result"]["blockers"]
    ]

    persisted = client.get("/api/content/work-items/snapshot").json()
    assert persisted["wordpress_handoff"]["handoff_result"]["handoff"] is None
    assert "missing_audit" in [
        blocker["code"] for blocker in persisted["wordpress_handoff"]["handoff_result"]["blockers"]
    ]
