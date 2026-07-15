from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from wilq.content.workflow.contracts import ContentWorkItemStructuredDraftGenerationRequest
from wilq.content.workflow.stage_drafts import (
    build_content_work_item_structured_draft_generation_response,
)


def test_diagnostics_derived_content_item_reaches_grounded_contract_without_publish(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)

    snapshot = _get_snapshot(client)
    item = snapshot["preflight"]["item"]
    inventory = snapshot["preflight"]["inventory_resolution"]
    preflight = snapshot["preflight"]["preflight_verdict"]
    brief = snapshot["sales_brief"]["sales_brief_result"]["brief"]
    draft = snapshot["draft_package"]["draft_package_result"]["draft_package"]
    contract = _structured_generation_from_snapshot(client, snapshot)["contract"]

    _assert_initial_content_gates(item=item, inventory=inventory, preflight=preflight)
    if draft is None:
        _assert_missing_knowledge_blocks_draft(snapshot=snapshot)
        return
    if contract is None:
        raise AssertionError("Expected structured generation contract when draft package exists.")
    _assert_workflow_build_gates(snapshot=snapshot)
    _assert_claim_ledger(snapshot=snapshot)
    _assert_sales_brief(brief=brief, item=item)
    _assert_draft_package(draft=draft, brief=brief, item=snapshot["draft_package"]["item"])
    _assert_structured_contract(contract=contract, draft=draft, item=item)

    assert item["evidence_ids"]
    assert item["source_connectors"]
    assert _is_public_ekologus_url(item["final_canonical_url"])
    assert "dev.proudsite.pl" not in item["final_canonical_url"]
    assert contract["publish_ready"] is False
    assert contract["model_input"]["work_item_id"] == item["id"]

    structured_output = _structured_output_from_contract(contract)
    assert structured_output["publish_ready"] is False
    assert structured_output["source_facts_used"]
    assert structured_output["human_review_checklist"]

    initial_handoff = snapshot["wordpress_handoff"]["handoff_result"]
    assert initial_handoff["handoff"] is None
    assert {blocker["code"] for blocker in initial_handoff["blockers"]} == {
        "missing_human_review",
        "missing_audit",
    }

    review = _human_review_from_snapshot(item=item, draft=draft)
    review_response = _post_json(
        client,
        "/api/content/work-items/snapshot/human-review",
        {"review": review},
    )
    assert review_response["wordpress_handoff_allowed"] is True
    assert review_response["review"]["id"] == review["id"]

    after_review = _get_snapshot(client)
    assert after_review["human_review"]["reviewed_item"]["human_review_status"] == "approved"
    after_review_handoff_blockers = after_review["wordpress_handoff"]["handoff_result"][
        "blockers"
    ]
    assert [blocker["code"] for blocker in after_review_handoff_blockers] == ["missing_audit"]

    audit = {
        "audit_id": f"audit_{item['id']}",
        "actor": "wilku",
        "reason": "Operator zatwierdził wyłącznie przygotowanie szkicu WordPress.",
        "evidence_ids": item["evidence_ids"],
        "human_review_id": review["id"],
    }
    handoff_response = _post_json(
        client,
        "/api/content/work-items/snapshot/audit",
        {"audit": audit},
    )
    handoff = handoff_response["handoff_result"]["handoff"]
    assert handoff_response["handoff_result"]["blockers"] == []
    assert handoff["post_status"] == "draft"
    assert handoff["publish_allowed"] is False
    assert handoff["destructive_update_allowed"] is False
    assert handoff["audit_id"] == audit["audit_id"]
    assert handoff["evidence_ids"] == item["evidence_ids"]

    after_audit = _get_snapshot(client)
    measurement = after_audit["measurement_window"]
    window = measurement["measurement_window_result"]["window"]
    assert window["handoff_id"] == handoff["id"]
    assert window["content_url"] == item["final_canonical_url"]
    assert window["success_claim_allowed"] is False
    assert [blocker["code"] for blocker in measurement["outcome_blockers"]] == [
        "measurement_window_not_ready"
    ]

    execution = _post_json(
        client,
        "/api/content/work-items/wordpress-draft-execution",
        {"handoff": handoff, "draft_package": draft, "mode": "dry_run"},
    )["execution_result"]
    assert execution["status"] == "dry_run_ready"
    assert execution["external_write_attempted"] is False
    assert execution["wordpress_post_id"] is None
    assert execution["payload"]["post_status"] == "draft"
    assert execution["payload"]["publish_allowed"] is False
    assert execution["payload"]["destructive_update_allowed"] is False


def _assert_initial_content_gates(
    *,
    item: dict[str, Any],
    inventory: dict[str, Any],
    preflight: dict[str, Any],
) -> None:
    assert item["inventory_status"] == "resolved"
    assert item["canonical_status"] == "resolved"
    assert item["duplicate_status"] == "checked"
    assert item["preflight_status"] == "missing"
    assert item["preserve_first_plan_status"] == "missing"
    assert item["sales_brief_status"] == "missing"
    assert item["claim_ledger_status"] == "missing"
    assert item["draft_package_status"] == "missing"
    assert item["human_review_status"] == "missing"
    assert item["audit_status"] == "missing"
    assert item["wordpress_handoff_status"] == "missing"
    assert item["measurement_window_status"] == "missing"

    assert inventory["status"] == "resolved"
    assert inventory["recommended_mode"] == "preserve"
    assert inventory["records"]
    assert inventory["blockers"] == []
    assert item["source_public_url"] in inventory["similar_existing_urls"]
    assert set(inventory["evidence_ids"]) == set(item["evidence_ids"])
    assert set(inventory["source_connectors"]) == set(item["source_connectors"])

    assert preflight["status"] == "plan_allowed"
    assert preflight["recommended_mode"] == "preserve"
    assert preflight["create_allowed"] is False
    assert preflight["draft_allowed"] is False
    assert preflight["wordpress_draft_allowed"] is False
    assert preflight["sales_brief_allowed"] is False
    assert preflight["final_canonical_url"] == item["final_canonical_url"]
    assert preflight["preview_url"] is None
    assert set(preflight["evidence_ids"]) == set(item["evidence_ids"])
    assert set(preflight["source_connectors"]) == set(item["source_connectors"])
    assert {
        "missing_preserve_first_plan",
        "missing_sales_brief",
        "missing_claim_ledger",
        "missing_measurement_window",
        "missing_draft_package",
        "missing_human_review",
        "missing_audit",
    }.issubset({blocker["code"] for blocker in preflight["blockers"]})


def _assert_workflow_build_gates(*, snapshot: dict[str, Any]) -> None:
    sales_item = snapshot["sales_brief"]["item"]
    assert sales_item["preserve_first_plan_status"] == "approved"
    assert sales_item["measurement_window_status"] == "planned"
    assert sales_item["sales_brief_status"] == "missing"

    draft_item = snapshot["draft_package"]["item"]
    assert draft_item["preflight_status"] == "draft_allowed"
    assert draft_item["preserve_first_plan_status"] == "approved"
    assert draft_item["sales_brief_status"] == "approved"
    assert draft_item["claim_ledger_status"] == "approved"
    assert draft_item["draft_package_status"] == "missing"

    structured_item = snapshot["human_review"]["item"]
    assert structured_item["draft_package_status"] == "ready"
    assert structured_item["human_review_status"] == "missing"
    assert structured_item["audit_status"] == "missing"

    handoff_candidate = snapshot["wordpress_handoff"]["item"]
    assert handoff_candidate["preflight_status"] == "handoff_allowed"
    assert handoff_candidate["draft_package_status"] == "ready"
    assert handoff_candidate["human_review_status"] == "missing"
    assert handoff_candidate["audit_status"] == "missing"

    measurement_candidate = snapshot["measurement_window"]["updated_item"]
    assert measurement_candidate["measurement_window_status"] == "planned"


def _assert_claim_ledger(*, snapshot: dict[str, Any]) -> None:
    ledger = snapshot["claim_ledger"]
    draft_item = snapshot["draft_package"]["item"]
    assert ledger["id"] == draft_item["claim_ledger_id"]
    assert ledger["work_item_id"] == draft_item["id"]
    assert ledger["entries"]
    assert ledger["entries"][0]["evidence_ids"]
    assert ledger["entries"][0]["source_connectors"]
    claim_texts = [entry["claim_text"] for entry in ledger["entries"]]
    assert all("może pomóc użytkownikowi w temacie" not in text for text in claim_texts)
    assert any("istniejącej publicznej treści Ekologus" in text for text in claim_texts)
    assert any("poprawi pozycje SEO" in text for text in claim_texts)
    assert any("zwiększy liczbę leadów" in text for text in claim_texts)


def _assert_missing_knowledge_blocks_draft(*, snapshot: dict[str, Any]) -> None:
    brief_result = snapshot["sales_brief"]["sales_brief_result"]
    draft_result = snapshot["draft_package"]["draft_package_result"]
    generation_readiness = snapshot["structured_generation_readiness"]

    assert brief_result["brief"] is None
    assert [blocker["code"] for blocker in brief_result["blockers"]] == [
        "missing_required_knowledge_card",
        "missing_required_knowledge_card",
    ]
    assert draft_result["draft_package"] is None
    assert {
        "preflight_not_draft_allowed",
        "missing_sales_brief",
    }.issubset({blocker["code"] for blocker in draft_result["blockers"]})
    assert generation_readiness["status"] == "blocked"
    assert generation_readiness["editable_section_headings"] == []
    assert {
        "missing_sales_brief",
        "missing_draft_package",
    }.issubset({blocker["code"] for blocker in generation_readiness["blockers"]})


def _assert_sales_brief(*, brief: dict[str, Any], item: dict[str, Any]) -> None:
    assert brief["work_item_id"] == item["id"]
    assert brief["source_public_url"] == item["source_public_url"]
    assert brief["intended_final_url"] == item["intended_final_url"]
    assert brief["final_canonical_url"] == item["final_canonical_url"]
    assert brief["preview_url"] is None
    assert "preserve-first" in brief["existing_content_plan"]
    assert set(brief["evidence_ids"]) == set(item["evidence_ids"])
    assert set(brief["source_connectors"]) == set(item["source_connectors"])
    assert brief["source_facts"]
    assert {
        source_fact["evidence_id"] for source_fact in brief["source_facts"]
    } == set(item["evidence_ids"])
    assert brief["human_review_required"] is True
    assert brief["draft_allowed"] is False
    assert brief["measurement_plan"]["success_claim_rule"]
    assert brief["cta_direction"]


def _assert_draft_package(
    *,
    draft: dict[str, Any],
    brief: dict[str, Any],
    item: dict[str, Any],
) -> None:
    assert draft["work_item_id"] == item["id"]
    assert draft["brief_id"] == brief["id"]
    assert draft["claim_ledger_id"] == item["claim_ledger_id"]
    assert draft["draft_kind"] == "outline"
    assert draft["publish_ready"] is False
    assert draft["sections"]
    assert draft["section_to_evidence_map"]
    assert draft["human_review_questions"]
    assert set(_draft_evidence_ids(draft)).issubset(set(item["evidence_ids"]))
    assert any("poprawi pozycje SEO" in claim for claim in draft["claims_removed_or_blocked"])
    assert any("zwiększy liczbę leadów" in claim for claim in draft["claims_removed_or_blocked"])
    assert any(
        "gwarantuje wzrost widoczności" in claim
        for claim in draft["claims_removed_or_blocked"]
    )


def _assert_structured_contract(
    *,
    contract: dict[str, Any],
    draft: dict[str, Any],
    item: dict[str, Any],
) -> None:
    assert contract["publish_ready"] is False
    model_input = contract["model_input"]
    assert model_input["work_item_id"] == item["id"]
    assert model_input["source_public_url"] == item["source_public_url"]
    assert model_input["final_canonical_url"] == item["final_canonical_url"]
    assert model_input["preview_url"] is None
    assert model_input["language"] == "pl-PL"
    assert model_input["sections"] == draft["sections"]
    assert model_input["claims_removed_or_blocked"] == draft["claims_removed_or_blocked"]
    assert model_input["human_review_questions"] == draft["human_review_questions"]
    assert set(_contract_evidence_ids(model_input)).issubset(set(item["evidence_ids"]))


def _get_snapshot(client: TestClient) -> dict[str, Any]:
    response = client.get("/api/content/work-items/snapshot")
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def _structured_generation_from_snapshot(
    _client: TestClient,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    response = build_content_work_item_structured_draft_generation_response(
        ContentWorkItemStructuredDraftGenerationRequest.model_validate(
            {
            "item": snapshot["human_review"]["item"],
            "sales_brief": snapshot["sales_brief"]["sales_brief_result"]["brief"],
            "claim_ledger": snapshot["claim_ledger"],
            "draft_package": snapshot["draft_package"]["draft_package_result"][
                "draft_package"
            ],
            }
        )
    )
    return cast(
        dict[str, Any],
        response.structured_generation_result.model_dump(mode="json"),
    )


def _post_json(client: TestClient, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(path, json=payload)
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def _human_review_from_snapshot(*, item: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"human_review_{item['id']}",
        "work_item_id": item["id"],
        "stage": "draft_package",
        "reviewed_by": "wilku",
        "decision": "approved",
        "notes": "Operator zatwierdził plan, twierdzenia i szkic do trybu draft.",
        "checked_items": [
            "Szkic wynika z dowodów WILQ.",
            "Ryzykowne twierdzenia zostały obsłużone.",
            "WordPress może dostać wyłącznie szkic.",
        ],
        "evidence_ids": item["evidence_ids"],
        "blocked_claims_handled": draft["claims_removed_or_blocked"],
        "draft_package_id": draft["id"],
    }


def _structured_output_from_contract(contract: dict[str, Any]) -> dict[str, Any]:
    model_input = contract["model_input"]
    allowed_evidence_ids = _contract_evidence_ids(model_input)
    first_evidence_id = allowed_evidence_ids[0]
    sections = model_input["sections"] or [
        {
            "heading": model_input["title"],
            "evidence_ids": [first_evidence_id],
        }
    ]
    return {
        "draft_kind": model_input["draft_kind"],
        "language": "pl-PL",
        "title": f"{model_input['title']} - szkic do sprawdzenia",
        "meta_title": model_input["title"],
        "meta_description": "Szkic do sprawdzenia przygotowany wyłącznie z dowodów WILQ.",
        "h1": model_input["title"],
        "sections": [
            {
                "heading": section["heading"],
                "body_markdown": (
                    "Ten fragment jest szkicem do sprawdzenia przez człowieka i używa "
                    "wyłącznie dowodów wskazanych przez WILQ."
                ),
                "evidence_ids": section.get("evidence_ids") or [first_evidence_id],
                "claims_used": model_input["claims_allowed"][:1],
            }
            for section in sections[:2]
        ],
        "faq": [],
        "cta": model_input["cta_direction"],
        "internal_links": [],
        "source_facts_used": allowed_evidence_ids,
        "claims_needing_review": [],
        "forbidden_claims_avoided": model_input["claims_removed_or_blocked"],
        "human_review_checklist": model_input["human_review_questions"],
        "publish_ready": False,
    }


def _contract_evidence_ids(model_input: dict[str, Any]) -> list[str]:
    values: list[str] = []
    values.extend(fact["evidence_id"] for fact in model_input["source_facts"])
    for section in model_input["sections"]:
        values.extend(section["evidence_ids"])
    return list(dict.fromkeys(value for value in values if value))


def _draft_evidence_ids(draft: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for section in draft["sections"]:
        values.extend(section["evidence_ids"])
    for section_map in draft["section_to_evidence_map"]:
        values.extend(section_map["evidence_ids"])
    return list(dict.fromkeys(value for value in values if value))


def _is_public_ekologus_url(value: str) -> bool:
    return value.startswith(("https://ekologus.pl/", "https://www.ekologus.pl/"))
