from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import actions as actions_router
from apps.api.wilq_api.routers import content_workflow as content_workflow_router
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.workflow.contracts import ContentWorkItemStructuredDraftGenerationRequest
from wilq.content.workflow.revisions import (
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionReviewCommand,
    content_draft_package_digest,
)
from wilq.content.workflow.stage_drafts import (
    build_content_work_item_structured_draft_generation_response,
)
from wilq.content.workflow.store import content_workflow_store
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    AuditEvent,
    MetricFact,
    OpportunityDomain,
)


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


def test_approved_revision_builds_the_exact_wordpress_handoff_without_legacy_review(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, work_item_id, snapshot = _revision_ready_snapshot(monkeypatch, tmp_path)
    save_payload = _save_payload(snapshot)
    save_payload["title"] = f"{save_payload['title']} — zatwierdzona wersja"
    save_payload["sections"] = [
        {
            **section,
            "body_markdown": f"Treść zatwierdzonej sekcji {index + 1}.",
        }
        for index, section in enumerate(save_payload["sections"])
    ]
    revision = client.post(_save_path(work_item_id), json=save_payload).json()[
        "revision"
    ]

    approval_response = client.post(
        _review_path(work_item_id, revision["revision_id"]),
        json=_review_payload(revision, "approved"),
    )

    assert approval_response.status_code == 200
    approval = approval_response.json()["review"]
    reloaded = _selected_snapshot(client, work_item_id)
    assert reloaded["human_review"]["review"] is None
    handoff = reloaded["wordpress_handoff"]["handoff_result"]["handoff"]
    assert handoff is not None
    assert handoff["revision_binding"] == {
        "work_item_id": work_item_id,
        "handoff_id": handoff["id"],
        "revision_id": revision["revision_id"],
        "content_digest": revision["content_digest"],
        "draft_package_id": revision["draft_package_id"],
        "draft_package_digest": revision["draft_package_digest"],
        "approval_decision_id": approval["decision_id"],
        "final_canonical_url": revision["final_canonical_url"],
    }
    assert handoff["title"] == revision["title"]
    assert handoff["revision_sections"] == revision["sections"]
    assert handoff["human_review_id"] is None
    assert handoff["audit_id"] is None
    assert handoff["evidence_ids"] == list(
        dict.fromkeys(
            evidence_id
            for section in revision["sections"]
            for evidence_id in section["evidence_ids"]
        )
    )
    assert handoff["post_status"] == "draft"
    assert handoff["publish_allowed"] is False
    assert handoff["destructive_update_allowed"] is False

    package = ContentDraftPackage.model_validate(
        snapshot["draft_package"]["draft_package_result"]["draft_package"]
    )
    mismatched = content_workflow_store().append_draft_revision(
        ContentDraftRevisionAppendCommand(
            work_item_id=work_item_id,
            base_revision_id=revision["revision_id"],
            draft_package_id=package.id,
            draft_package_digest=content_draft_package_digest(package),
            final_canonical_url=revision["final_canonical_url"],
            title=revision["title"],
            sections=[
                {
                    **section,
                    "heading": f"Nieaktualna sekcja {index + 1}",
                }
                for index, section in enumerate(revision["sections"])
            ],
            created_by="direct-store-corruption-proof",
        )
    )
    assert mismatched.revision is not None
    mismatched_review = content_workflow_store().review_draft_revision(
        ContentDraftRevisionReviewCommand(
            work_item_id=work_item_id,
            revision_id=mismatched.revision.revision_id,
            revision_digest=mismatched.revision.content_digest,
            decision="approved",
            reviewed_by="wilku",
            checked_items=["tekst", "dowody"],
            evidence_ids=list(
                dict.fromkeys(
                    evidence_id
                    for section in mismatched.revision.sections
                    for evidence_id in section.evidence_ids
                )
            ),
        )
    )
    assert mismatched_review.review is not None
    blocked_handoff = _selected_snapshot(client, work_item_id)["wordpress_handoff"][
        "handoff_result"
    ]
    assert blocked_handoff["handoff"] is None
    assert "revision_context_changed" in {
        blocker["code"] for blocker in blocked_handoff["blockers"]
    }


def test_action_apply_sends_only_the_exact_approved_revision_and_blocks_replay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, work_item_id, snapshot = _revision_ready_snapshot(monkeypatch, tmp_path)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")
    save_payload = _save_payload(snapshot)
    save_payload["title"] = f"{save_payload['title']} — wersja v1"
    save_payload["sections"] = [
        {
            **section,
            "body_markdown": f"Zatwierdzona treść v1, sekcja {index + 1}.",
        }
        for index, section in enumerate(save_payload["sections"])
    ]
    revision = client.post(_save_path(work_item_id), json=save_payload).json()[
        "revision"
    ]
    approval_response = client.post(
        _review_path(work_item_id, revision["revision_id"]),
        json=_review_payload(revision, "approved"),
    )
    assert approval_response.status_code == 200
    approved_snapshot = _selected_snapshot(client, work_item_id)
    handoff = approved_snapshot["wordpress_handoff"]["handoff_result"]["handoff"]
    binding = cast(dict[str, Any], handoff["revision_binding"])
    operator = "operator_revision_v1"
    action = ActionObject(
        id="act_apply_wordpress_draft_handoff",
        title="Utwórz dokładnie zatwierdzony szkic WordPress",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.medium,
        status=ActionStatus.ready,
        evidence_ids=["ev_wordpress_revision_apply"],
        metrics=[
            MetricFact(
                name="revision_apply_proof",
                value=1,
                period="synthetic_test",
                source_connector="wordpress_ekologus",
                evidence_id="ev_wordpress_revision_apply",
            )
        ],
        human_diagnosis="Syntetyczny proof dokładnej wersji szkicu.",
        recommended_reason="Chroni przed wysłaniem innej wersji niż zatwierdzona.",
        payload={
            "action_type": "wordpress_draft_handoff",
            "allowed_operation": "create_wordpress_draft",
            "payload_preview": [{"id": "preview_revision_v1"}],
            "apply_allowed": False,
            "api_mutation_ready": False,
            "destructive": False,
        },
        validation_status="valid",
        created_by="test",
    )
    selected_action = {"value": action}
    monkeypatch.setattr(
        actions_router,
        "get_action",
        lambda _action_id: selected_action["value"],
    )
    monkeypatch.setattr(
        "wilq.actions.service.get_connector_status",
        lambda _connector_id: type(
            "Connector", (), {"configured": True, "label": "WordPress"}
        )(),
    )
    adapter_payloads: list[Any] = []

    def capture_draft(payload: Any) -> str:
        adapter_payloads.append(payload)
        return "synthetic-wordpress-draft-1"

    monkeypatch.setattr(
        "wilq.actions.wordpress_mutation_requirements.create_wordpress_draft_post",
        capture_draft,
    )

    stage_requests = [
        (
            "preview",
            {
                "requested_by": operator,
                "wordpress_draft": binding,
            },
        ),
        (
            "review",
            {
                "outcome": "approved_for_prepare",
                "reviewed_by": operator,
                "notes": "Sprawdzono dokładną wersję v1.",
                "checked_items": ["tekst", "dowody", "draft-only"],
                "blockers": [],
                "wordpress_draft": binding,
            },
        ),
        (
            "confirm",
            {
                "confirmed_by": operator,
                "notes": "Potwierdzam dokładną wersję v1.",
                "preview_acknowledged": True,
                "wordpress_draft": binding,
            },
        ),
        (
            "impact-check",
            {
                "checked_by": operator,
                "notes": "Syntetyczny impact check bez claimu wyniku.",
                "wordpress_draft": binding,
            },
        ),
    ]
    for stage, payload in stage_requests:
        response = client.post(
            f"/api/actions/act_apply_wordpress_draft_handoff/{stage}",
            json=payload,
        )
        assert response.status_code == 200, response.text
        assert response.json()["audit_event"]["details"][
            "wordpress_draft_binding"
        ] == binding

    apply_payload = {
        "confirm": True,
        "confirmed_by": operator,
        "wordpress_draft": binding,
    }
    apply_response = client.post(
        "/api/actions/act_apply_wordpress_draft_handoff/apply",
        json=apply_payload,
    )
    assert apply_response.status_code == 200, apply_response.text
    applied = apply_response.json()
    assert applied["wordpress_revision_blockers"] == []
    assert applied["audit_event"]["details"]["wordpress_draft_binding"] == binding
    assert applied["mutation_audit"]["wordpress_draft_binding"] == binding
    assert applied["mutation_audit"]["adapter_reached"] is True
    assert applied["mutation_audit"]["external_write_attempted"] is True
    assert len(adapter_payloads) == 1
    created_payload = adapter_payloads[0]
    expected_markdown = "\n\n".join(
        [f"# {revision['title']}"]
        + [
            chunk
            for section in revision["sections"]
            for chunk in [f"## {section['heading']}", section["body_markdown"]]
        ]
    )
    assert created_payload.title == revision["title"]
    assert created_payload.content_markdown == expected_markdown
    assert created_payload.post_status == "draft"
    assert created_payload.publish_allowed is False
    assert created_payload.destructive_update_allowed is False

    for field, changed_value in {
        "handoff_id": f"{binding['handoff_id']}_other",
        "revision_id": f"{binding['revision_id']}_other",
        "content_digest": "f" * 64,
        "draft_package_id": f"{binding['draft_package_id']}_other",
        "draft_package_digest": "e" * 64,
        "approval_decision_id": f"{binding['approval_decision_id']}_other",
        "final_canonical_url": "https://ekologus.pl/inny-testowy-adres/",
    }.items():
        tampered = {**binding, field: changed_value}
        response = client.post(
            "/api/actions/act_apply_wordpress_draft_handoff/apply",
            json={**apply_payload, "wordpress_draft": tampered},
        )
        assert response.status_code == 409, (field, response.text)
        detail = response.json()["detail"]
        assert detail["wordpress_revision_blockers"][0]["code"] == (
            "wordpress_revision_binding_mismatch"
        )
        assert detail["mutation_audit"]["adapter_reached"] is False
        assert detail["mutation_audit"]["external_write_attempted"] is False
    assert len(adapter_payloads) == 1

    selected_action["value"] = action.model_copy(
        deep=True,
        update={
            "audit_events": [
                AuditEvent(
                    id=f"audit_legacy_{event_type}",
                    action_id=action.id,
                    event_type=event_type,
                    actor=operator,
                    summary="Historyczny event bez bindingu.",
                )
                for event_type in [
                    "action_preview_generated",
                    "human_review_approved_for_prepare",
                    "action_apply_confirmed",
                    "action_impact_check_completed",
                ]
            ]
        },
    )
    legacy_response = client.post(
        "/api/actions/act_apply_wordpress_draft_handoff/apply",
        json=apply_payload,
    )
    assert legacy_response.status_code == 409
    legacy_detail = legacy_response.json()["detail"]
    assert legacy_detail["wordpress_revision_blockers"][0]["code"] == (
        "wordpress_action_chain_binding_mismatch"
    )
    assert legacy_detail["mutation_audit"]["adapter_reached"] is False
    assert len(adapter_payloads) == 1

    package = ContentDraftPackage.model_validate(
        approved_snapshot["draft_package"]["draft_package_result"]["draft_package"]
    )
    v2 = content_workflow_store().append_draft_revision(
        ContentDraftRevisionAppendCommand(
            work_item_id=work_item_id,
            base_revision_id=revision["revision_id"],
            draft_package_id=package.id,
            draft_package_digest=content_draft_package_digest(package),
            final_canonical_url=revision["final_canonical_url"],
            title=revision["title"],
            sections=[
                {**section, "body_markdown": f"Treść v2: {section['body_markdown']}"}
                for section in revision["sections"]
            ],
            created_by="operator_revision_v2",
        )
    )
    assert v2.revision is not None
    selected_action["value"] = action
    stale_response = client.post(
        "/api/actions/act_apply_wordpress_draft_handoff/apply",
        json=apply_payload,
    )
    assert stale_response.status_code == 409
    stale_detail = stale_response.json()["detail"]
    assert stale_detail["wordpress_revision_blockers"][0]["code"] == (
        "revision_not_approved"
    )
    assert stale_detail["mutation_audit"]["adapter_reached"] is False
    assert stale_detail["mutation_audit"]["external_write_attempted"] is False
    assert len(adapter_payloads) == 1


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
