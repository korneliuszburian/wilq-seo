from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from tests.content.test_structured_generation_api import (
    _claim_ledger,
    _draft_package,
    _item,
    _sales_brief,
    _structured_output,
)


def test_adversarial_generation_blocks_missing_evidence_and_source_connector() -> None:
    response = _post_generation(
        item=_item(evidence_ids=[], source_connectors=[]),
    )

    result = response.json()["structured_generation_result"]
    assert result["contract"] is None
    assert {"missing_evidence", "missing_source_connector"} <= _blocker_codes(result)


def test_adversarial_generation_blocks_dev_url_as_canonical() -> None:
    response = _post_generation(
        item=_item(final_canonical_url="https://ekologus.dev.proudsite.pl/bdo/"),
    )

    result = response.json()["structured_generation_result"]
    assert result["contract"] is None
    assert "invalid_final_canonical" in _blocker_codes(result)


def test_adversarial_generation_blocks_missing_preflight_even_with_forged_artifacts() -> None:
    response = _post_generation(
        item=_item(preflight_status="missing"),
    )

    result = response.json()["structured_generation_result"]
    assert result["contract"] is None
    assert "missing_preflight" in _blocker_codes(result)


def test_adversarial_generation_blocks_missing_claim_gate_even_with_ledger_payload() -> None:
    response = _post_generation(
        item=_item(claim_ledger_status="missing", claim_ledger_id=None),
    )

    result = response.json()["structured_generation_result"]
    assert result["contract"] is None
    assert "missing_claim_ledger" in _blocker_codes(result)


def test_adversarial_generation_blocks_missing_measurement_window() -> None:
    response = _post_generation(
        item=_item(measurement_window_status="missing", measurement_window_id=None),
    )

    result = response.json()["structured_generation_result"]
    assert result["contract"] is None
    assert "missing_measurement_window" in _blocker_codes(result)


def test_adversarial_structured_preview_rejects_publish_ready_true() -> None:
    contract = _generation_contract()
    output = _structured_output()
    output["publish_ready"] = True

    response = TestClient(app).post(
        "/api/content/work-items/structured-draft-preview",
        json={"contract": contract, "output": output},
    )

    assert response.status_code == 422


def test_adversarial_quality_review_blocks_forbidden_guarantee_claim() -> None:
    payload = _quality_payload()
    forbidden_claim = "Ekologus gwarantuje uniknięcie kar po przeczytaniu tej treści."
    payload["claim_ledger"]["entries"].append(
        {
            "id": "claim_forbidden_guarantee",
            "claim_text": forbidden_claim,
            "claim_type": "guarantee_claim",
            "status": "blocked",
            "evidence_ids": [],
            "reason": "Gwarancja efektu jest zablokowana.",
        }
    )
    payload["structured_output"]["sections"][0]["claims_used"].append(forbidden_claim)

    response = TestClient(app).post("/api/content/work-items/quality-review", json=payload)

    assert response.status_code == 200
    review = response.json()["quality_review"]
    assert review["verdict"] == "blocked"
    assert {"claim_ledger_blocks_quality", "forbidden_claim_used"} <= _blocker_codes(review)


def test_adversarial_quality_review_blocks_claim_outside_ledger() -> None:
    payload = _quality_payload()
    payload["structured_output"]["sections"][0]["claims_used"].append(
        "Ekologus przejmie pełną odpowiedzialność za wszystkie obowiązki BDO."
    )

    response = TestClient(app).post("/api/content/work-items/quality-review", json=payload)

    assert response.status_code == 200
    review = response.json()["quality_review"]
    assert review["verdict"] == "blocked"
    assert review["claim_safety"]["status"] == "blocked"
    assert "unsupported_claim_used" in _blocker_codes(review)


def test_adversarial_wordpress_publish_request_is_rejected_and_live_write_is_blocked() -> None:
    publish_response = TestClient(app).post(
        "/api/content/work-items/wordpress-draft-execution",
        json={
            "handoff": _wordpress_handoff(post_status="publish", publish_allowed=True),
            "draft_package": _draft_package(),
            "mode": "dry_run",
        },
    )
    assert publish_response.status_code == 422

    live_response = TestClient(app).post(
        "/api/content/work-items/wordpress-draft-execution",
        json={
            "handoff": _wordpress_handoff(),
            "draft_package": _draft_package(),
            "mode": "live",
        },
    )
    assert live_response.status_code == 200
    result = live_response.json()["execution_result"]
    assert result["status"] == "blocked"
    assert result["external_write_attempted"] is False
    assert _blocker_codes(result) == {"action_apply_required"}


def test_adversarial_measurement_outcome_is_blocked_before_window_is_ready() -> None:
    response = TestClient(app).post(
        "/api/content/work-items/measurement-window",
        json={
            "item": _item(),
            "handoff": _wordpress_handoff(),
            "baseline_period": {"start": "2026-05-01", "end": "2026-05-31"},
            "observation_period": {"start": "2026-07-01", "end": "2026-07-31"},
            "allowed_metrics": ["gsc_clicks", "ga4_engaged_sessions"],
            "source_connectors": ["google_search_console", "google_analytics_4"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    window = data["measurement_window_result"]["window"]
    assert window["status"] == "planned"
    assert window["success_claim_allowed"] is False
    assert [blocker["code"] for blocker in data["outcome_blockers"]] == [
        "measurement_window_not_ready"
    ]


def test_adversarial_wrong_item_review_cannot_unlock_handoff() -> None:
    other_item = _item(
        id="content_work_item_zielony_lad",
        topic="Zielony Ład",
        draft_package_id="draft_package_content_work_item_zielony_lad",
    )

    response = TestClient(app).post(
        "/api/content/work-items/human-review",
        json={
            "item": other_item,
            "review": _human_review(),
            "draft_package": _draft_package(),
            "claim_ledger": _claim_ledger(),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["wordpress_handoff_allowed"] is False
    assert {"wrong_work_item", "draft_package_mismatch"} <= _blocker_codes(data)


def _post_generation(*, item: dict[str, object]) -> Any:
    response = TestClient(app).post(
        "/api/content/work-items/structured-draft-generation",
        json={
            "item": item,
            "sales_brief": _sales_brief(),
            "claim_ledger": _claim_ledger(),
            "draft_package": _draft_package(),
        },
    )
    assert response.status_code == 200
    return response


def _generation_contract() -> dict[str, Any]:
    response = _post_generation(item=_item())
    result = response.json()["structured_generation_result"]
    assert result["blockers"] == []
    return result["contract"]


def _quality_payload() -> dict[str, Any]:
    return {
        "item": _item(),
        "sales_brief": _sales_brief(),
        "draft_package": _draft_package(),
        "claim_ledger": _claim_ledger(),
        "structured_output": deepcopy(_structured_output()),
        "duplicate_risk": "clear",
    }


def _human_review(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "human_review_bdo",
        "work_item_id": "content_work_item_bdo",
        "stage": "draft_package",
        "reviewed_by": "wilku",
        "decision": "approved",
        "notes": "Szkic może iść dalej jako WordPress draft.",
        "checked_items": ["claimy bez gwarancji efektu", "CTA bez obietnicy wyniku"],
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "blocked_claims_handled": [],
        "draft_package_id": "draft_package_content_work_item_bdo",
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
        "title": "BDO dla firm",
        "final_canonical_url": "https://ekologus.pl/bdo/",
        "intended_final_url": "https://ekologus.pl/bdo/",
        "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "publish_allowed": False,
        "destructive_update_allowed": False,
    }
    payload.update(overrides)
    return payload


def _blocker_codes(payload: dict[str, Any]) -> set[str]:
    return {blocker["code"] for blocker in payload["blockers"]}
