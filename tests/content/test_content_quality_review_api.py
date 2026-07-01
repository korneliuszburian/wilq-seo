from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app


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
    snapshot = TestClient(app).get("/api/content/work-items/snapshot").json()
    item = deepcopy(snapshot["structured_generation"]["item"])
    brief = deepcopy(snapshot["sales_brief"]["sales_brief_result"]["brief"])
    draft_package = deepcopy(snapshot["draft_package"]["draft_package_result"]["draft_package"])
    contract = snapshot["structured_generation"]["structured_generation_result"]["contract"]
    model_input = contract["model_input"]
    return {
        "item": item,
        "sales_brief": brief,
        "draft_package": draft_package,
        "claim_ledger": _claim_ledger(item),
        "structured_output": _structured_output(model_input),
        "duplicate_risk": "clear",
    }


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
