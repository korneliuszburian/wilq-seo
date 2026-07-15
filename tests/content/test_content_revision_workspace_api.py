from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import actions as actions_router
from apps.api.wilq_api.routers import content_workflow as content_workflow_router
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.workflow.revisions import (
    ContentDraftRevisionAppendCommand,
    content_draft_package_digest,
)
from wilq.content.workflow.store import content_workflow_store


def test_snapshot_seeds_api_owned_editor_and_starts_at_draft(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, work_item_id, snapshot = _revision_ready_snapshot(monkeypatch, tmp_path)

    workspace = snapshot["revision_workspace"]
    draft = snapshot["draft_package"]["draft_package_result"]["draft_package"]
    steps = {step["id"]: step for step in snapshot["operator_steps"]}

    assert snapshot["preflight"]["item"]["id"] == work_item_id
    assert workspace["status"] == "empty"
    assert workspace["latest_revision"] is None
    assert workspace["latest_review"] is None
    assert workspace["revision_count"] == 0
    assert workspace["editor_title"] == draft["title"]
    assert [section["heading"] for section in workspace["editor_sections"]] == [
        section["heading"] for section in draft["sections"]
    ]
    assert workspace["can_save"] is True
    assert workspace["can_review"] is False
    assert snapshot["current_step_id"] == "draft"
    assert steps["draft"]["can_submit"] is True
    assert steps["review"]["can_submit"] is False
    assert steps["dev_draft"]["can_submit"] is False
    assert steps["dev_draft"]["blocker"]["code"] == "missing_revision_bound_draft"

    reloaded = _selected_snapshot(client, work_item_id)
    assert reloaded["revision_workspace"] == workspace


def test_structured_preview_does_not_create_a_mutable_saved_draft(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, work_item_id, snapshot = _revision_ready_snapshot(monkeypatch, tmp_path)
    contract = snapshot["structured_generation"]["structured_generation_result"][
        "contract"
    ]

    response = client.post(
        f"/api/content/work-items/{work_item_id}/structured-draft-preview",
        json={
            "contract": contract,
            "output": _structured_output_from_contract(contract),
        },
    )

    assert response.status_code == 200
    workspace = _selected_snapshot(client, work_item_id)["revision_workspace"]
    assert workspace["status"] == "empty"
    assert workspace["revision_count"] == 0
    assert workspace["latest_revision"] is None


def test_revision_save_is_reloadable_idempotent_and_returns_raw_stale_conflict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, work_item_id, snapshot = _revision_ready_snapshot(monkeypatch, tmp_path)
    payload = _save_payload(snapshot)

    created = client.post(_save_path(work_item_id), json=payload)

    assert created.status_code == 200
    created_body = created.json()
    assert created_body["status"] == "created"
    revision = created_body["revision"]
    assert revision["revision_number"] == 1
    assert revision["base_revision_id"] is None
    assert revision["draft_package_id"] == snapshot["draft_package"][
        "draft_package_result"
    ]["draft_package"]["id"]
    package = ContentDraftPackage.model_validate(
        snapshot["draft_package"]["draft_package_result"]["draft_package"]
    )
    assert revision["draft_package_digest"] == content_draft_package_digest(package)
    assert content_draft_package_digest(
        package.model_copy(update={"title": f"{package.title} — zmieniony plan"})
    ) != content_draft_package_digest(package)
    assert revision["final_canonical_url"] == (
        snapshot["preflight"]["item"]["final_canonical_url"]
        or snapshot["preflight"]["item"]["intended_final_url"]
    )
    assert len(revision["content_digest"]) == 64
    assert revision["publish_ready"] is False
    assert created_body["workspace"]["status"] == "unreviewed"
    assert created_body["workspace"]["editor_sections"] == revision["sections"]

    reloaded = _selected_snapshot(client, work_item_id)
    assert reloaded["current_step_id"] == "review"
    assert reloaded["revision_workspace"]["latest_revision"] == revision
    assert reloaded["revision_workspace"]["can_save"] is False
    assert reloaded["revision_workspace"]["can_review"] is True

    retried = client.post(_save_path(work_item_id), json=payload)
    assert retried.status_code == 200
    assert retried.json()["status"] == "idempotent"
    assert retried.json()["revision"]["revision_id"] == revision["revision_id"]

    stale_payload = {**payload, "title": f"{payload['title']} — lokalna zmiana"}
    stale = client.post(_save_path(work_item_id), json=stale_payload)
    assert stale.status_code == 409
    assert stale.json() == {
        "status": "conflict",
        "code": "stale_base",
        "current_revision_id": revision["revision_id"],
        "current_digest": revision["content_digest"],
        "safe_next_step": (
            "Na serwerze jest nowsza wersja. Zachowaj swój tekst, porównaj zmiany "
            "i dopiero potem zapisz kolejną wersję na aktualnej bazie."
        ),
    }
    after_conflict = _selected_snapshot(client, work_item_id)["revision_workspace"]
    assert after_conflict["revision_count"] == 1
    assert after_conflict["latest_revision"]["title"] == payload["title"]


@pytest.mark.parametrize(
    (
        "decision",
        "expected_step",
        "expected_can_submit",
        "expected_can_save",
        "expected_can_review",
    ),
    [
        ("approved", "dev_draft", False, False, False),
        ("needs_changes", "draft", True, True, False),
        ("rejected", "draft", True, True, False),
        ("deferred", "review", True, False, True),
    ],
)
def test_exact_revision_decision_drives_the_five_step_journey(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    decision: str,
    expected_step: str,
    expected_can_submit: bool,
    expected_can_save: bool,
    expected_can_review: bool,
) -> None:
    client, work_item_id, snapshot = _revision_ready_snapshot(monkeypatch, tmp_path)
    revision = client.post(_save_path(work_item_id), json=_save_payload(snapshot)).json()[
        "revision"
    ]
    review_payload = _review_payload(revision, decision)

    response = client.post(
        _review_path(work_item_id, revision["revision_id"]),
        json=review_payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "recorded"
    assert body["review"]["revision_id"] == revision["revision_id"]
    assert body["review"]["revision_digest"] == revision["content_digest"]
    assert body["review"]["decision"] == decision
    assert body["workspace"]["status"] == decision
    assert body["workspace"]["can_save"] is expected_can_save
    assert body["workspace"]["can_review"] is expected_can_review

    persisted = _selected_snapshot(client, work_item_id)
    steps = {step["id"]: step for step in persisted["operator_steps"]}
    assert persisted["current_step_id"] == expected_step
    assert steps[expected_step]["can_submit"] is expected_can_submit
    assert steps["dev_draft"]["readiness"] == "blocked"
    assert steps["dev_draft"]["can_submit"] is False
    if decision == "approved":
        assert steps["dev_draft"]["blocker"]["code"] == (
            "missing_revision_bound_wordpress_seam"
        )

    retried = client.post(
        _review_path(work_item_id, revision["revision_id"]),
        json=review_payload,
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "idempotent"
    assert retried.json()["review"]["decision_id"] == body["review"]["decision_id"]


def test_revision_review_rejects_wrong_digest_revision_and_unbound_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, work_item_id, snapshot = _revision_ready_snapshot(monkeypatch, tmp_path)
    revision = client.post(_save_path(work_item_id), json=_save_payload(snapshot)).json()[
        "revision"
    ]
    payload = _review_payload(revision, "approved")

    wrong_digest = client.post(
        _review_path(work_item_id, revision["revision_id"]),
        json={**payload, "expected_revision_digest": "0" * 64},
    )
    assert wrong_digest.status_code == 409
    assert wrong_digest.json()["status"] == "conflict"
    assert wrong_digest.json()["code"] == "digest_mismatch"
    assert wrong_digest.json()["current_revision_id"] == revision["revision_id"]

    wrong_revision = client.post(
        _review_path(work_item_id, "content_revision_unknown"),
        json=payload,
    )
    assert wrong_revision.status_code == 409
    assert wrong_revision.json()["code"] == "revision_not_found"

    unknown_evidence = client.post(
        _review_path(work_item_id, revision["revision_id"]),
        json={**payload, "evidence_ids": ["ev_outside_exact_revision"]},
    )
    assert unknown_evidence.status_code == 422
    assert "spoza snapshotu" in unknown_evidence.json()["detail"]
    assert _selected_snapshot(client, work_item_id)["revision_workspace"]["status"] == (
        "unreviewed"
    )


def test_approval_of_v1_never_approves_a_new_v2(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    external_calls: list[str] = []

    def reject_external_call(*_args: object, **_kwargs: object) -> None:
        external_calls.append("unexpected")
        raise AssertionError("Revision save/review crossed an external execution seam.")

    monkeypatch.setattr(
        content_workflow_router,
        "build_content_work_item_wordpress_draft_execution_response",
        reject_external_call,
    )
    monkeypatch.setattr(
        content_workflow_router,
        "build_content_work_item_structured_draft_runtime_response",
        reject_external_call,
    )
    monkeypatch.setattr(actions_router, "apply_action", reject_external_call)
    client, work_item_id, snapshot = _revision_ready_snapshot(monkeypatch, tmp_path)
    v1 = client.post(_save_path(work_item_id), json=_save_payload(snapshot)).json()[
        "revision"
    ]
    approved = client.post(
        _review_path(work_item_id, v1["revision_id"]),
        json=_review_payload(v1, "approved"),
    )
    assert approved.status_code == 200

    v2_result = content_workflow_store().append_draft_revision(
        ContentDraftRevisionAppendCommand(
            work_item_id=work_item_id,
            base_revision_id=v1["revision_id"],
            draft_package_id=v1["draft_package_id"],
            draft_package_digest="0" * 64,
            final_canonical_url=v1["final_canonical_url"],
            title=f"{v1['title']} — wersja 2",
            sections=[
                {
                    **section,
                    "heading": f"Nieaktualny plan {index + 1}",
                }
                for index, section in enumerate(v1["sections"])
            ],
            created_by="wilku",
        )
    )
    assert v2_result.status == "created"
    assert v2_result.revision is not None

    snapshot_v2 = _selected_snapshot(client, work_item_id)
    workspace = snapshot_v2["revision_workspace"]
    assert workspace["latest_revision"]["revision_id"] == v2_result.revision.revision_id
    assert workspace["latest_review"] is None
    assert workspace["status"] == "unreviewed"
    assert workspace["context_current"] is False
    assert workspace["can_review"] is False
    assert workspace["can_save"] is True
    current_package = snapshot["draft_package"]["draft_package_result"]["draft_package"]
    assert [section["heading"] for section in workspace["editor_sections"]] == [
        section["heading"] for section in current_package["sections"]
    ]
    assert [section["evidence_ids"] for section in workspace["editor_sections"]] == [
        section["evidence_ids"] for section in current_package["sections"]
    ]
    assert snapshot_v2["current_step_id"] == "draft"
    assert snapshot_v2["operator_steps"][2]["blocker"]["code"] == (
        "revision_context_changed"
    )
    assert snapshot_v2["operator_steps"][4]["can_submit"] is False

    rebound = client.post(
        _save_path(work_item_id),
        json={
            "base_revision_id": v2_result.revision.revision_id,
            "title": workspace["editor_title"],
            "sections": workspace["editor_sections"],
            "created_by": "wilku",
        },
    )
    assert rebound.status_code == 200
    assert rebound.json()["status"] == "created"
    assert rebound.json()["revision"]["draft_package_id"] == v1["draft_package_id"]
    assert rebound.json()["workspace"]["status"] == "unreviewed"
    assert rebound.json()["workspace"]["context_current"] is True
    assert rebound.json()["workspace"]["can_review"] is True
    assert external_calls == []


def test_revision_endpoints_reject_sections_or_evidence_outside_draft_package(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, work_item_id, snapshot = _revision_ready_snapshot(monkeypatch, tmp_path)
    payload = _save_payload(snapshot)
    section = payload["sections"][0]

    unknown_heading = client.post(
        _save_path(work_item_id),
        json={
            **payload,
            "sections": [{**section, "heading": "Nieznana sekcja"}],
        },
    )
    assert unknown_heading.status_code == 422

    unknown_evidence = client.post(
        _save_path(work_item_id),
        json={
            **payload,
            "sections": [
                {**section, "evidence_ids": ["ev_outside_draft_package"]},
                *payload["sections"][1:],
            ],
        },
    )
    assert unknown_evidence.status_code == 422
    assert content_workflow_store().load_draft_revision_state(work_item_id).status == (
        "empty"
    )


@pytest.mark.parametrize("field", ["title", "created_by"])
def test_revision_save_rejects_blank_metadata_without_persisting(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    field: str,
) -> None:
    client, work_item_id, snapshot = _revision_ready_snapshot(monkeypatch, tmp_path)

    response = client.post(
        _save_path(work_item_id),
        json={**_save_payload(snapshot), field: "   "},
    )

    assert response.status_code == 422
    assert content_workflow_store().load_draft_revision_state(work_item_id).status == (
        "empty"
    )


def test_first_revision_respects_a_workspace_save_blocker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, work_item_id, snapshot = _revision_ready_snapshot(monkeypatch, tmp_path)
    api_snapshot = content_workflow_router._snapshot_for_work_item_or_404(work_item_id)
    blocked_snapshot = api_snapshot.model_copy(
        update={
            "revision_workspace": api_snapshot.revision_workspace.model_copy(
                update={
                    "can_save": False,
                    "safe_next_step": "Najpierw domknij aktualny kontrakt szkicu.",
                }
            )
        }
    )
    monkeypatch.setattr(
        content_workflow_router,
        "_snapshot_for_work_item_or_404",
        lambda _work_item_id: blocked_snapshot,
    )

    response = client.post(_save_path(work_item_id), json=_save_payload(snapshot))

    assert response.status_code == 409
    assert response.json() == {
        "status": "conflict",
        "code": "workspace_not_saveable",
        "current_revision_id": None,
        "current_digest": None,
        "safe_next_step": "Najpierw domknij aktualny kontrakt szkicu.",
    }
    assert content_workflow_store().load_draft_revision_state(work_item_id).status == (
        "empty"
    )


def _revision_ready_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[TestClient, str, dict[str, Any]]:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)
    queue = client.get("/api/content/work-items/queue").json()
    for candidate in queue["candidates"]:
        response = client.get(
            f"/api/content/work-items/{candidate['work_item_id']}/snapshot"
        )
        if response.status_code != 200:
            continue
        snapshot = cast(dict[str, Any], response.json())
        if snapshot.get("response_type") != "workflow_snapshot":
            continue
        workspace = snapshot["revision_workspace"]
        evidence_ids = {
            evidence_id
            for section in workspace["editor_sections"]
            for evidence_id in section["evidence_ids"]
        }
        if workspace["can_save"] and evidence_ids:
            return client, candidate["work_item_id"], snapshot
    pytest.fail("Revision API proof requires one saveable work item with bound evidence.")


def _selected_snapshot(client: TestClient, work_item_id: str) -> dict[str, Any]:
    response = client.get(f"/api/content/work-items/{work_item_id}/snapshot")
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def _save_payload(snapshot: dict[str, Any]) -> dict[str, Any]:
    workspace = snapshot["revision_workspace"]
    return {
        "base_revision_id": None,
        "title": workspace["editor_title"],
        "sections": workspace["editor_sections"],
        "created_by": "wilku",
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
        "meta_description": "Sprawdź zakres przed kontaktem z Ekologus.",
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


def _review_payload(revision: dict[str, Any], decision: str) -> dict[str, Any]:
    evidence_ids = list(
        dict.fromkeys(
            evidence_id
            for section in revision["sections"]
            for evidence_id in section["evidence_ids"]
        )
    )
    assert evidence_ids
    return {
        "expected_revision_digest": revision["content_digest"],
        "reviewed_by": "wilku",
        "decision": decision,
        "notes": "Sprawdzono dokładną zapisaną wersję.",
        "checked_items": ["tekst", "dowody", "CTA"],
        "evidence_ids": evidence_ids,
    }


def _save_path(work_item_id: str) -> str:
    return f"/api/content/work-items/{work_item_id}/draft-revisions"


def _review_path(work_item_id: str, revision_id: str) -> str:
    return (
        f"/api/content/work-items/{work_item_id}/draft-revisions/"
        f"{revision_id}/review"
    )
