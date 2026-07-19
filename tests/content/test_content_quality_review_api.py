from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from tests.content.test_content_work_item_brief_draft_api import (
    _post_draft_package,
    _post_sales_brief,
)
from tests.content.test_work_item_preflight_api import (
    _draft_claim_ledger,
    _enrichment,
    _inventory_record,
    _item,
    _sales_brief_seed,
)
from wilq.content.workflow.contracts import ContentWorkItemStructuredDraftGenerationRequest
from wilq.content.workflow.stage_drafts import (
    build_content_work_item_structured_draft_generation_response,
)


def test_content_quality_review_accepts_evidence_bound_draft() -> None:
    payload = _quality_payload()

    response = TestClient(app).post("/api/content/work-items/quality-review", json=payload)

    assert response.status_code == 200
    review = response.json()["quality_review"]
    assert review["verdict"] == "ready_for_human_review"
    assert review["blockers"] == []
    assert review["evidence_coverage"]["status"] == "pass"
    assert review["claim_safety"]["status"] == "pass"
    assert review["measurement_readiness"]["status"] == "pass"
    assert review["safe_next_step"].startswith("Przekaż szkic do sprawdzenia człowieka")


def test_content_quality_review_blocks_missing_section_evidence() -> None:
    payload = _quality_payload()
    payload["structured_output"]["sections"][0]["evidence_ids"] = []

    response = TestClient(app).post("/api/content/work-items/quality-review", json=payload)

    assert response.status_code == 200
    review = response.json()["quality_review"]
    assert review["verdict"] == "blocked"
    assert "section_missing_evidence" in _blocker_codes(review)
    assert review["evidence_coverage"]["status"] == "blocked"


def test_content_quality_review_blocks_claim_without_required_section_evidence() -> None:
    payload = _quality_payload()
    payload["structured_output"]["sections"][0]["evidence_ids"] = ["ev_gsc_bdo"]
    payload["structured_output"]["source_facts_used"] = ["ev_gsc_bdo", "ev_wp_bdo"]

    response = TestClient(app).post("/api/content/work-items/quality-review", json=payload)

    assert response.status_code == 200
    review = response.json()["quality_review"]
    assert review["verdict"] == "blocked"
    assert "claim_missing_required_evidence" in _blocker_codes(review)
    assert review["claim_safety"]["status"] == "blocked"
    blocker = next(
        blocker
        for blocker in review["blockers"]
        if blocker["code"] == "claim_missing_required_evidence"
    )
    assert blocker["affected_section"] == payload["structured_output"]["sections"][0]["heading"]
    assert blocker["evidence_ids"] == ["ev_wp_bdo"]


def test_content_quality_review_blocks_missing_required_claim() -> None:
    payload = _quality_payload()
    payload["claim_ledger"]["entries"][0]["required"] = True
    required_claim = payload["claim_ledger"]["entries"][0]["claim_text"]
    payload["structured_output"]["sections"][0]["claims_used"] = []

    response = TestClient(app).post("/api/content/work-items/quality-review", json=payload)

    assert response.status_code == 200
    review = response.json()["quality_review"]
    assert review["verdict"] == "blocked"
    assert "required_claim_missing" in _blocker_codes(review)
    assert review["claim_safety"]["status"] == "blocked"
    blocker = next(
        blocker for blocker in review["blockers"] if blocker["code"] == "required_claim_missing"
    )
    assert required_claim in blocker["next_step"]


def test_content_quality_review_blocks_missing_forbidden_claim_acknowledgement() -> None:
    payload = _quality_payload()
    blocked_claim = "Nie obiecuj leadów po publikacji."
    payload["draft_package"]["claims_removed_or_blocked"] = [blocked_claim]
    payload["structured_output"]["forbidden_claims_avoided"] = []

    response = TestClient(app).post("/api/content/work-items/quality-review", json=payload)

    assert response.status_code == 200
    review = response.json()["quality_review"]
    assert review["verdict"] == "blocked"
    assert "missing_forbidden_claim_acknowledgement" in _blocker_codes(review)
    assert review["claim_safety"]["status"] == "blocked"
    blocker = next(
        blocker
        for blocker in review["blockers"]
        if blocker["code"] == "missing_forbidden_claim_acknowledgement"
    )
    assert blocked_claim in blocker["next_step"]


def test_content_quality_review_blocks_forbidden_claims_and_publish_ready_package() -> None:
    payload = _quality_payload()
    forbidden_claim = "WILQ gwarantuje wzrost leadów po publikacji."
    payload["claim_ledger"]["entries"].append(
        {
            "id": "claim_forbidden_growth",
            "claim_text": forbidden_claim,
            "claim_type": "guarantee_claim",
            "status": "blocked",
            "evidence_ids": [],
            "reason": "Gwarancje efektu są zablokowane.",
        }
    )
    payload["structured_output"]["sections"][0]["claims_used"].append(forbidden_claim)
    payload["draft_package"]["publish_ready"] = True

    response = TestClient(app).post("/api/content/work-items/quality-review", json=payload)

    assert response.status_code == 200
    review = response.json()["quality_review"]
    assert review["verdict"] == "blocked"
    assert {
        "claim_ledger_blocks_quality",
        "forbidden_claim_used",
        "draft_package_marked_publish_ready",
    }.issubset(_blocker_codes(review))
    assert review["claim_safety"]["status"] == "blocked"


def test_content_quality_review_blocks_duplicate_and_missing_measurement() -> None:
    payload = _quality_payload()
    payload["duplicate_risk"] = "high"
    payload["item"]["duplicate_status"] = "risk_found"
    payload["item"]["measurement_window_status"] = "missing"
    payload["item"]["measurement_window_id"] = None

    response = TestClient(app).post("/api/content/work-items/quality-review", json=payload)

    assert response.status_code == 200
    review = response.json()["quality_review"]
    assert review["verdict"] == "blocked"
    assert {"duplicate_risk_not_clear", "missing_measurement_window"}.issubset(
        _blocker_codes(review)
    )
    assert review["duplicate_risk"]["status"] == "blocked"
    assert review["measurement_readiness"]["status"] == "blocked"


def test_content_quality_review_flags_review_required_sales_brief_signal() -> None:
    payload = _quality_payload()
    payload["sales_brief"]["signal_quality"] = {
        **payload["sales_brief"]["signal_quality"],
        "status": "review_required",
        "status_label": "wymaga review źródeł",
        "reason": "Brief opiera się na źródłach review-required.",
        "safe_next_step": "Pokaż brief Wilkowi i zbierz decyzję źródłową.",
    }

    response = TestClient(app).post("/api/content/work-items/quality-review", json=payload)

    assert response.status_code == 200
    review = response.json()["quality_review"]
    assert review["verdict"] == "needs_changes"
    assert "sales_brief_signal_review_required" in [
        finding["code"] for finding in review["findings"]
    ]
    assert review["evidence_coverage"]["status"] == "needs_changes"
    assert review["usefulness"]["status"] == "needs_changes"
    assert review["safe_next_step"] == "Pokaż brief Wilkowi i zbierz decyzję źródłową."


def test_content_quality_review_blocks_thin_sales_brief_signal() -> None:
    payload = _quality_payload()
    payload["sales_brief"]["signal_quality"] = {
        **payload["sales_brief"]["signal_quality"],
        "status": "thin",
        "status_label": "cienki sygnał",
        "reason": "Brief ma zbyt mało dowodów i źródeł.",
        "missing_evidence_count": 2,
        "measurement_baseline_ready": False,
        "safe_next_step": "Uzupełnij dowody i źródła przed szkicem.",
    }

    response = TestClient(app).post("/api/content/work-items/quality-review", json=payload)

    assert response.status_code == 200
    review = response.json()["quality_review"]
    assert review["verdict"] == "blocked"
    assert "sales_brief_signal_thin" in _blocker_codes(review)
    assert review["evidence_coverage"]["status"] == "blocked"
    assert review["usefulness"]["status"] == "blocked"
    assert review["safe_next_step"] == "Uzupełnij dowody i źródła przed szkicem."


def test_content_quality_review_returns_revision_instruction_for_weak_cta() -> None:
    payload = _quality_payload()
    payload["structured_output"]["cta"] = "kliknij tutaj"

    response = TestClient(app).post("/api/content/work-items/quality-review", json=payload)

    assert response.status_code == 200
    review = response.json()["quality_review"]
    assert review["verdict"] == "needs_changes"
    assert "weak_cta" in [finding["code"] for finding in review["findings"]]
    assert review["cta_quality"]["status"] == "needs_changes"
    assert review["revision_instructions"]


def _quality_payload() -> dict[str, Any]:
    item = _item(
        preflight_status="draft_allowed",
        preserve_first_plan_status="approved",
        sales_brief_status="approved",
        sales_brief_id="sales_brief_content_work_item_bdo",
        claim_ledger_status="approved",
        claim_ledger_id="claim_ledger_bdo",
        draft_package_status="ready",
        draft_package_id="draft_package_content_work_item_bdo",
        measurement_window_status="planned",
        measurement_window_id="measure_bdo",
    )
    claim_ledger = _draft_claim_ledger()
    brief_response = _post_sales_brief(
        {
            "item": _item(
                preserve_first_plan_status="approved",
                measurement_window_status="planned",
                measurement_window_id="measure_bdo",
            ),
            "inventory_records": [_inventory_record()],
            "duplicate_risk": "clear",
            "claim_ledger": claim_ledger,
            "seed": _sales_brief_seed(),
            "enrichment": _enrichment(),
        }
    )
    brief = deepcopy(brief_response["sales_brief_result"]["brief"])
    brief["signal_quality"] = {
        **brief["signal_quality"],
        "status": "strong",
        "status_label": "mocny sygnał",
        "reason": "Testowy brief ma komplet dowodów wymaganych dla happy path.",
        "missing_evidence_count": 0,
        "review_required_knowledge_card_count": 0,
        "measurement_baseline_ready": True,
        "safe_next_step": "Przekaż szkic do sprawdzenia człowieka.",
    }
    draft_response = _post_draft_package(
        {
            "item": item,
            "inventory_records": [_inventory_record()],
            "duplicate_risk": "clear",
            "claim_ledger": claim_ledger,
            "seed": _sales_brief_seed(),
            "enrichment": _enrichment(),
            "sales_brief": brief,
        }
    )
    draft_package = deepcopy(draft_response["draft_package_result"]["draft_package"])
    generation_response = build_content_work_item_structured_draft_generation_response(
        ContentWorkItemStructuredDraftGenerationRequest.model_validate(
            {
            "item": item,
            "sales_brief": brief,
            "claim_ledger": claim_ledger,
            "draft_package": draft_package,
            }
        )
    )
    contract = generation_response.structured_generation_result.contract
    assert contract is not None
    model_input = contract.model_input.model_dump(mode="json")
    return {
        "item": item,
        "sales_brief": brief,
        "draft_package": draft_package,
        "claim_ledger": claim_ledger,
        "structured_output": _structured_output(model_input),
        "duplicate_risk": "clear",
    }


def _quality_review(payload: dict[str, Any]) -> dict[str, Any]:
    response = TestClient(app).post("/api/content/work-items/quality-review", json=payload)
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    return cast(dict[str, Any], data["quality_review"])


def _claim_ledger(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["claim_ledger_id"],
        "work_item_id": item["id"],
        "reviewed_by": "wilku",
        "entries": [
            {
                "id": f"claim_service_{item['id']}",
                "claim_text": f"Ekologus może pomóc użytkownikowi w temacie: {item['topic']}.",
                "claim_type": "service_claim",
                "status": "allowed_with_evidence",
                "evidence_ids": [item["evidence_ids"][0]],
                "source_connectors": item["source_connectors"],
                "reason": "Twierdzenie ma przypisany dowód źródłowy.",
                "reviewer_id": "wilku",
            }
        ],
    }


def _structured_output(model_input: dict[str, Any]) -> dict[str, Any]:
    section = model_input["sections"][0]
    evidence_ids = section["evidence_ids"]
    return {
        "draft_kind": "section_draft",
        "language": "pl-PL",
        "title": model_input["title"],
        "meta_title": model_input["title"],
        "meta_description": "Sprawdź, co firma powinna wiedzieć przed kontaktem z Ekologus.",
        "h1": model_input["title"],
        "sections": [
            {
                "heading": section["heading"],
                "body_markdown": "Treść opiera się na wskazanych danych i wymaga review człowieka.",
                "evidence_ids": evidence_ids,
                "claims_used": model_input["claims_allowed"],
            }
        ],
        "faq": ["Co warto sprawdzić przed kontaktem z Ekologus?"],
        "cta": "Skontaktuj się z Ekologus, żeby sprawdzić sytuację firmy bez obietnicy wyniku.",
        "internal_links": model_input.get("internal_links", ["https://ekologus.pl/kontakt/"]),
        "source_facts_used": evidence_ids,
        "claims_needing_review": [],
        "forbidden_claims_avoided": model_input["claims_removed_or_blocked"],
        "human_review_checklist": model_input["human_review_questions"],
        "publish_ready": False,
    }


def _blocker_codes(review: dict[str, Any]) -> set[str]:
    return {blocker["code"] for blocker in review["blockers"]}
