from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app


def test_diagnostics_derived_content_item_reaches_draft_dry_run_without_publish(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)

    snapshot = _get_snapshot(client)
    item = snapshot["preflight"]["item"]
    draft = snapshot["draft_package"]["draft_package_result"]["draft_package"]
    contract = snapshot["structured_generation"]["structured_generation_result"]["contract"]

    assert item["evidence_ids"]
    assert item["source_connectors"]
    assert _is_public_ekologus_url(item["final_canonical_url"])
    assert "dev.proudsite.pl" not in item["final_canonical_url"]
    assert contract["publish_ready"] is False
    assert contract["model_input"]["work_item_id"] == item["id"]

    runtime = _post_json(
        client,
        "/api/content/work-items/structured-draft-runtime",
        {"contract": contract, "model": "gpt-5", "mode": "dry_run"},
    )["runtime_result"]
    assert runtime["status"] == "dry_run_ready"
    assert runtime["external_call_attempted"] is False
    assert runtime["output"] is None

    structured_output = _structured_output_from_contract(contract)
    preview = _post_json(
        client,
        "/api/content/work-items/structured-draft-preview",
        {"contract": contract, "output": structured_output},
    )["preview_result"]
    assert preview["blockers"] == []
    assert preview["preview"]["publish_ready"] is False
    assert preview["preview"]["source_facts_used"] == structured_output["source_facts_used"]
    assert preview["preview"]["human_review_checklist"]

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


def _get_snapshot(client: TestClient) -> dict[str, Any]:
    response = client.get("/api/content/work-items/snapshot")
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


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


def _is_public_ekologus_url(value: str) -> bool:
    return value.startswith(("https://ekologus.pl/", "https://www.ekologus.pl/"))
