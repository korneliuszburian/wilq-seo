from __future__ import annotations

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
        "preflight_status": "draft_allowed",
        "preserve_first_plan_status": "approved",
        "sales_brief_status": "approved",
        "sales_brief_id": "sales_brief_content_work_item_bdo",
        "claim_ledger_status": "approved",
        "claim_ledger_id": "claim_ledger_bdo",
        "draft_package_status": "ready",
        "draft_package_id": "draft_package_content_work_item_bdo",
        "measurement_window_status": "planned",
        "measurement_window_id": "measurement_window_content_work_item_bdo",
    }
    payload.update(overrides)
    return payload


def _sales_brief() -> dict[str, object]:
    return {
        "id": "sales_brief_content_work_item_bdo",
        "work_item_id": "content_work_item_bdo",
        "topic": "BDO dla firm",
        "target_reader": "właściciel firmy",
        "buyer_problem": "nie wie, jak podejść do BDO",
        "buyer_trigger": "zbliża się kontrola",
        "search_intent": "informacyjno-usługowy",
        "service_fit": "obsługa środowiskowa",
        "source_public_url": "https://ekologus.pl/bdo/",
        "final_canonical_url": "https://ekologus.pl/bdo/",
        "intended_final_url": "https://ekologus.pl/bdo/",
        "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
        "existing_content_plan": "Zacznij od istniejącej treści.",
        "h1_direction": "BDO dla firm",
        "h2_direction": ["Kogo dotyczy BDO"],
        "faq_direction": ["Czy każda firma musi mieć BDO?"],
        "cta_direction": "Skontaktuj się z Ekologus.",
        "internal_link_direction": ["https://ekologus.pl/kontakt/"],
        "source_facts": [
            {
                "evidence_id": "ev_gsc_bdo",
                "source_connector": "google_search_console",
                "summary": "GSC pokazuje popyt na temat BDO.",
            }
        ],
        "forbidden_claims": [],
        "missing_evidence": [],
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "source_connectors": ["google_search_console", "wordpress_ekologus"],
        "measurement_plan": {
            "measurement_window_id": "measurement_window_content_work_item_bdo",
            "metrics_to_watch": ["GSC clicks"],
            "earliest_verdict_note": "Nie oceniaj przed końcem okna.",
            "success_claim_rule": "Nie claimuj sukcesu bez danych.",
        },
        "human_review_required": True,
        "draft_allowed": True,
    }


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
            }
        ],
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
        "title": "BDO dla firm",
        "sections": [
            {
                "heading": "Kogo dotyczy BDO",
                "purpose": "Sekcja konspektu do napisania po sprawdzeniu planu.",
                "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
                "draft_notes": ["Zachowaj kierunek H1: BDO dla firm"],
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
        "human_review_questions": ["Czy to brzmi jak Ekologus?"],
        "publish_ready": False,
    }
    payload.update(overrides)
    return payload


def test_structured_draft_generation_api_returns_strict_contract() -> None:
    response = TestClient(app).post(
        "/api/content/work-items/structured-draft-generation",
        json={
            "item": _item(),
            "sales_brief": _sales_brief(),
            "claim_ledger": _claim_ledger(),
            "draft_package": _draft_package(),
        },
    )

    assert response.status_code == 200
    data = response.json()
    result = data["structured_generation_result"]
    assert result["blockers"] == []
    contract = result["contract"]
    assert contract["schema_name"] == "wilq_content_structured_draft_v1"
    assert contract["strict_schema"] is True
    assert contract["publish_ready"] is False
    assert contract["model_input"]["final_canonical_url"] == "https://ekologus.pl/bdo/"
    assert contract["model_input"]["source_facts"][0]["evidence_id"] == "ev_gsc_bdo"
    assert contract["model_input"]["sections"][0]["evidence_ids"] == [
        "ev_gsc_bdo",
        "ev_wp_bdo",
    ]
    assert contract["output_schema"]["additionalProperties"] is False


def test_structured_draft_generation_api_returns_typed_blockers() -> None:
    response = TestClient(app).post(
        "/api/content/work-items/structured-draft-generation",
        json={"item": _item()},
    )

    assert response.status_code == 200
    data = response.json()
    result = data["structured_generation_result"]
    assert result["contract"] is None
    assert {"missing_draft_package", "missing_sales_brief", "missing_claim_ledger"} <= {
        blocker["code"] for blocker in result["blockers"]
    }


def test_structured_draft_runtime_api_returns_dry_run_payload() -> None:
    generation = TestClient(app).post(
        "/api/content/work-items/structured-draft-generation",
        json={
            "item": _item(),
            "sales_brief": _sales_brief(),
            "claim_ledger": _claim_ledger(),
            "draft_package": _draft_package(),
        },
    )
    assert generation.status_code == 200
    contract = generation.json()["structured_generation_result"]["contract"]

    response = TestClient(app).post(
        "/api/content/work-items/structured-draft-runtime",
        json={"contract": contract, "model": "gpt-5"},
    )

    assert response.status_code == 200
    result = response.json()["runtime_result"]
    assert result["status"] == "dry_run_ready"
    assert result["external_call_attempted"] is False
    assert result["output"] is None
    format_payload = result["request_payload"]["text"]["format"]
    assert format_payload["type"] == "json_schema"
    assert format_payload["name"] == "wilq_content_structured_draft_v1"
    assert format_payload["strict"] is True


def test_structured_draft_runtime_api_blocks_live_mode() -> None:
    generation = TestClient(app).post(
        "/api/content/work-items/structured-draft-generation",
        json={
            "item": _item(),
            "sales_brief": _sales_brief(),
            "claim_ledger": _claim_ledger(),
            "draft_package": _draft_package(),
        },
    )
    assert generation.status_code == 200
    contract = generation.json()["structured_generation_result"]["contract"]

    response = TestClient(app).post(
        "/api/content/work-items/structured-draft-runtime",
        json={"contract": contract, "model": "gpt-5", "mode": "live"},
    )

    assert response.status_code == 200
    result = response.json()["runtime_result"]
    assert result["status"] == "blocked"
    assert result["external_call_attempted"] is False
    assert "live_generation_disabled" in {
        blocker["code"] for blocker in result["blockers"]
    }
