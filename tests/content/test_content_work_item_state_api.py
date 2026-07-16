from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from tests.content.test_content_revision_workspace_api import (
    _structured_generation_from_snapshot,
)
from wilq.content.workflow.store import content_workflow_store


def test_selected_content_work_item_state_is_isolated(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)
    first, second = _first_two_actionable_queue_items(client)

    first_snapshot = _get_selected_snapshot(client, first["work_item_id"])

    first_item = first_snapshot["preflight"]["item"]
    first_draft = first_snapshot["draft_package"]["draft_package_result"]["draft_package"]
    review = _human_review(first_item, first_draft)

    review_response = client.post(
        f"/api/content/work-items/{first['work_item_id']}/human-review",
        json={"review": review},
    )
    assert review_response.status_code == 200
    assert review_response.json()["wordpress_handoff_allowed"] is True

    wrong_item_response = client.post(
        f"/api/content/work-items/{second['work_item_id']}/human-review",
        json={"review": review},
    )
    assert wrong_item_response.status_code == 200
    assert wrong_item_response.json()["wordpress_handoff_allowed"] is False
    assert "wrong_work_item" in [
        blocker["code"] for blocker in wrong_item_response.json()["blockers"]
    ]

    first_after_review = _get_selected_snapshot(client, first["work_item_id"])
    second_after_review = _get_selected_snapshot(client, second["work_item_id"])
    assert first_after_review["human_review"]["review"]["id"] == review["id"]
    assert first_after_review["human_review"]["reviewed_item"]["human_review_status"] == "approved"
    assert second_after_review["human_review"]["review"] is None
    assert second_after_review["human_review"]["reviewed_item"]["human_review_status"] == "missing"

    audit = _audit(first_item, review)
    audit_response = client.post(
        f"/api/content/work-items/{first['work_item_id']}/audit",
        json={"audit": audit},
    )
    assert audit_response.status_code == 200
    assert audit_response.json()["handoff_result"]["handoff"]["post_status"] == "draft"
    assert audit_response.json()["handoff_result"]["handoff"]["publish_allowed"] is False

    first_after_audit = _get_selected_snapshot(client, first["work_item_id"])
    second_after_audit = _get_selected_snapshot(client, second["work_item_id"])
    assert first_after_audit["wordpress_handoff"]["handoff_result"]["handoff"]["audit_id"] == audit[
        "audit_id"
    ]
    assert second_after_audit["wordpress_handoff"]["handoff_result"]["handoff"] is None
    assert "missing_human_review" in [
        blocker["code"]
        for blocker in second_after_audit["wordpress_handoff"]["handoff_result"]["blockers"]
    ]


def test_blocked_queue_item_returns_typed_blocked_snapshot_without_fake_workflow(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)
    queue = client.get("/api/content/work-items/queue").json()
    blocked = next(
        candidate for candidate in queue["candidates"] if candidate["recommended_mode"] == "block"
    )

    response = client.get(f"/api/content/work-items/{blocked['work_item_id']}/snapshot")

    assert response.status_code == 200
    payload = response.json()
    assert payload["response_type"] == "blocked_snapshot"
    assert payload["work_item_id"] == blocked["work_item_id"]
    assert payload["recommended_mode"] == "block"
    assert payload["freshness_assessment"]["next_step"]
    assert payload["blockers"]
    assert payload["candidate"]["work_item_id"] == blocked["work_item_id"]
    assert "preflight" not in payload
    assert "sales_brief" not in payload
    assert payload["service_profile_context"]["binding_status"] == "not_evaluated"
    assert payload["service_profile_context"]["decision_status"] == "not_evaluated"
    assert payload["service_profile_context"]["service_card_id"] is None
    assert payload["service_profile_context"]["safe_next_step"] == blocked["safe_next_step"]


def test_homepage_work_item_builds_review_required_public_brief_without_publish(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)

    snapshot = _get_selected_snapshot(
        client,
        "content_work_item_content_decision_https___www_ekologus_pl",
    )
    assert snapshot["candidate"]["work_item_id"] == snapshot["preflight"]["item"]["id"]
    assert snapshot["candidate"]["freshness_assessment"]["next_step"]
    service_profile_context = snapshot["service_profile_context"]
    assert service_profile_context["binding_status"] == "bound"
    assert service_profile_context["decision_status"] == "blocked"
    assert service_profile_context["service_card_id"] == "ekologus_service_homepage_overview"
    assert service_profile_context["service_label"] == "Strona główna i przegląd oferty Ekologus"
    assert service_profile_context["service_status"] == "source_backed_review_required"
    assert service_profile_context["evidence_ids"] == ["ev_content_service_profile_source_facts"]
    assert service_profile_context["source_connectors"] == ["public_site"]
    assert service_profile_context["freshness_as_of"] == "2026-07-02"
    assert service_profile_context["claim_policy_scope_label"].startswith(
        "Ten skrót dotyczy tylko"
    )
    assert service_profile_context["missing_contracts"]
    assert service_profile_context["safe_next_step"]
    brief_result = snapshot["sales_brief"]["sales_brief_result"]
    blocker_codes = [blocker["code"] for blocker in brief_result["blockers"]]

    assert "missing_required_knowledge_card" not in blocker_codes
    brief = brief_result["brief"]
    assert brief is not None
    assert brief["signal_quality"]["status"] == "review_required"
    assert brief["draft_allowed"] is False
    assert "SEO:" not in brief["h1_direction"]
    assert "odśwież" not in brief["h1_direction"].lower()
    assert brief["h1_direction"].startswith("Ekologus")
    assert brief["h2_direction"] == [
        "W czym pomaga Ekologus",
        "Kiedy warto skonsultować obowiązki środowiskowe",
        "Jak przygotować się do rozmowy",
    ]
    assert "bez obietnicy wyniku" in brief["cta_direction"]
    assert "ekologus_service_homepage_overview" in brief["knowledge_card_ids"]
    assert "ekologus_cta_homepage_contact_review_required" in brief[
        "knowledge_card_ids"
    ]

    generation_readiness = snapshot["structured_generation_readiness"]
    assert generation_readiness["publish_ready"] is False
    if generation_readiness["status"] == "ready":
        assert generation_readiness["editable_section_headings"]
        assert generation_readiness["blockers"] == []
    else:
        assert generation_readiness["editable_section_headings"] == []
        assert generation_readiness["blockers"]
    handoff = snapshot["wordpress_handoff"]["handoff_result"]
    assert handoff["handoff"] is None
    assert "missing_human_review" in {blocker["code"] for blocker in handoff["blockers"]}
    measurement = snapshot["measurement_window"]
    assert measurement["measurement_window_result"]["window"] is None
    assert measurement["measurement_window_result"]["blockers"][0]["code"] == (
        "missing_publication_event"
    )


def test_selected_content_work_item_output_and_quality_state_is_isolated(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)
    first, second = _first_two_actionable_queue_items(client)
    first_snapshot = _get_selected_snapshot(client, first["work_item_id"])

    contract = _structured_generation_from_snapshot(client, first_snapshot)["contract"]
    output = _structured_output_from_contract(contract)

    store = content_workflow_store()
    assert store.load_draft_revision_state(first["work_item_id"]).status == "empty"
    assert store.load_draft_revision_state(second["work_item_id"]).status == "empty"

    item = first_snapshot["human_review"]["item"]
    quality_response = client.post(
        f"/api/content/work-items/{first['work_item_id']}/quality-review",
        json={
            "item": item,
            "sales_brief": first_snapshot["sales_brief"]["sales_brief_result"]["brief"],
            "draft_package": first_snapshot["draft_package"]["draft_package_result"][
                "draft_package"
            ],
            "claim_ledger": _claim_ledger_for_item(item, output),
            "structured_output": output,
            "duplicate_risk": "clear",
        },
    )
    assert quality_response.status_code == 200
    assert quality_response.json()["quality_review"]["work_item_id"] == first["work_item_id"]
    assert content_workflow_store().latest_quality_review(first["work_item_id"]) is not None
    assert content_workflow_store().latest_quality_review(second["work_item_id"]) is None

    revision_response = client.post(
        f"/api/content/work-items/{first['work_item_id']}/revision-plan",
        json={
            "item": item,
            "quality_review": quality_response.json()["quality_review"],
        },
    )
    assert revision_response.status_code == 200
    assert revision_response.json()["revision_plan"]["work_item_id"] == first["work_item_id"]

    wrong_revision_response = client.post(
        f"/api/content/work-items/{second['work_item_id']}/revision-plan",
        json={
            "item": item,
            "quality_review": quality_response.json()["quality_review"],
        },
    )
    assert wrong_revision_response.status_code == 400

    wrong_quality_response = client.post(
        f"/api/content/work-items/{second['work_item_id']}/quality-review",
        json={
            "item": item,
            "structured_output": output,
            "duplicate_risk": "clear",
        },
    )
    assert wrong_quality_response.status_code == 400
    assert content_workflow_store().latest_quality_review(second["work_item_id"]) is None


def _first_two_actionable_queue_items(client: TestClient) -> tuple[dict[str, Any], dict[str, Any]]:
    queue = client.get("/api/content/work-items/queue").json()
    actionable = [
        candidate for candidate in queue["candidates"] if candidate["recommended_mode"] != "block"
    ]
    if len(actionable) < 2:
        pytest.skip("Content state isolation requires two non-blocked queue items.")
    return actionable[0], actionable[1]


def _get_selected_snapshot(client: TestClient, work_item_id: str) -> dict[str, Any]:
    response = client.get(f"/api/content/work-items/{work_item_id}/snapshot")
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def _human_review(item: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"human_review_{item['id']}",
        "work_item_id": item["id"],
        "stage": "draft_package",
        "reviewed_by": "wilku",
        "decision": "approved",
        "notes": "Szkic może iść dalej jako WordPress draft.",
        "checked_items": [
            "brief zgodny z dowodami",
            "claimy bez gwarancji efektu",
            "CTA bez obietnicy wyniku",
        ],
        "evidence_ids": item["evidence_ids"],
        "blocked_claims_handled": [],
        "draft_package_id": draft["id"],
    }


def _audit(item: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    return {
        "audit_id": f"audit_{item['id']}",
        "actor": "wilku",
        "reason": "Zatwierdzony szkic może trafić do WordPress jako draft.",
        "evidence_ids": item["evidence_ids"],
        "human_review_id": review["id"],
    }


def _structured_output_from_contract(contract: dict[str, Any]) -> dict[str, Any]:
    model_input = contract["model_input"]
    section = model_input["sections"][0]
    evidence_ids = section["evidence_ids"]
    return {
        "draft_kind": "section_draft",
        "language": "pl-PL",
        "title": model_input["title"],
        "meta_title": model_input["title"],
        "meta_description": "Sprawdź, co warto wiedzieć przed kontaktem z Ekologus.",
        "h1": model_input["title"],
        "sections": [
            {
                "heading": section["heading"],
                "body_markdown": "Treść opiera się na wskazanych danych i wymaga review.",
                "evidence_ids": evidence_ids,
                "claims_used": model_input["claims_allowed"],
            }
        ],
        "faq": ["Co warto sprawdzić przed kontaktem z Ekologus?"],
        "cta": "Skontaktuj się z Ekologus, żeby sprawdzić sytuację firmy.",
        "internal_links": ["https://ekologus.pl/kontakt/"],
        "source_facts_used": evidence_ids,
        "claims_needing_review": [],
        "forbidden_claims_avoided": model_input["claims_removed_or_blocked"],
        "human_review_checklist": model_input["human_review_questions"],
        "publish_ready": False,
    }


def _claim_ledger_for_item(
    item: dict[str, Any],
    output: dict[str, Any],
) -> dict[str, Any]:
    claim_text = output["sections"][0]["claims_used"][0]
    return {
        "id": item["claim_ledger_id"],
        "work_item_id": item["id"],
        "reviewed_by": "wilku",
        "entries": [
            {
                "id": f"claim_allowed_{item['id']}",
                "claim_text": claim_text,
                "claim_type": "service_claim",
                "status": "allowed_with_evidence",
                "evidence_ids": item["evidence_ids"][0:1],
                "source_connectors": item["source_connectors"],
                "reason": "Twierdzenie ma przypisany dowód źródłowy.",
                "reviewer_id": "wilku",
            }
        ],
    }
