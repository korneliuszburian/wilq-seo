from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from fastapi.testclient import TestClient

import wilq.actions.service as action_service
from apps.api.wilq_api.main import app
from wilq.actions.service import apply_action
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.handoff.wordpress import ContentWordPressDraftHandoff
from wilq.content.handoff.wordpress_execution import ContentWordPressDraftWriteAuthorization
from wilq.schemas import (
    ActionApplyRequest,
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    ActionWordPressDraftApplyInput,
    AuditEvent,
    OpportunityDomain,
)


def _get_mutation_readiness(action_id: str) -> dict[str, Any]:
    response = TestClient(app).get(
        f"/api/actions/{action_id}/mutation-readiness",
    )
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["response_type"] == "action_mutation_readiness"
    return data


def _get_mutation_readiness_summary() -> dict[str, Any]:
    response = TestClient(app).get("/api/actions/mutation-readiness")
    assert response.status_code == 200, response.text
    data = cast(dict[str, Any], response.json())
    assert data["response_type"] == "action_mutation_readiness_summary"
    return data


def test_action_mutation_readiness_blocks_prepare_only_action(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "actions.sqlite3"))

    data = _get_mutation_readiness("act_prepare_wordpress_draft_handoff")

    assert data["ready_to_request_apply"] is False
    assert data["vendor_write_possible"] is False
    assert data["would_attempt_vendor_write"] is False
    assert data["mutation_adapter"] is None
    assert data["mode"] == "prepare"
    assert data["source_connectors"] == ["wordpress_ekologus"]
    assert data["evidence_ids"]
    apply_contract = data["apply_contract"]
    assert apply_contract["allowed_operation"] == "create_wordpress_draft"
    assert apply_contract["required_mode"] == "apply"
    assert apply_contract["draft_only"] is True
    assert apply_contract["publication_allowed"] is False
    assert apply_contract["destructive_allowed"] is False
    assert apply_contract["adapter_status"] == "not_implemented"
    assert "WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES" in apply_contract["required_env_flags"]
    assert "wordpress_publish" in apply_contract["blocked_outputs"]
    blocker_codes = [blocker["code"] for blocker in data["blockers"]]
    assert "missing_apply_mode" in blocker_codes
    assert "missing_mutation_adapter" in blocker_codes
    assert any(
        requirement["code"] == "mutation_adapter" and requirement["satisfied"] is False
        for requirement in data["requirements"]
    )
    assert "validate" in data["operator_next_step"]


def test_action_mutation_readiness_exposes_blocked_wordpress_apply_action(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "actions_apply.sqlite3"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "0")

    data = _get_mutation_readiness("act_apply_wordpress_draft_handoff")

    assert data["mode"] == "apply"
    assert data["ready_to_request_apply"] is False
    assert data["vendor_write_possible"] is False
    assert data["would_attempt_vendor_write"] is False
    assert data["mutation_adapter"] == "wordpress_draft_execution_boundary"
    assert data["apply_contract"]["allowed_operation"] == "create_wordpress_draft"
    assert data["apply_contract"]["adapter_status"] == "implemented"
    assert data["apply_contract"]["publication_allowed"] is False
    assert data["target_candidate_id"]
    assert data["target_label"]
    assert data["target_url"].startswith("https://")
    assert data["write_authorization_status"] == "missing_audit_trace"
    assert data["missing_audit_event_types"] == [
        "action_preview_generated",
        "human_review_*",
        "action_apply_confirmed",
    ]
    blocker_codes = [blocker["code"] for blocker in data["blockers"]]
    requirement_codes = {requirement["code"] for requirement in data["requirements"]}
    assert "missing_apply_mode" not in blocker_codes
    assert "missing_payload_apply_allowed" in blocker_codes
    assert "missing_mutation_adapter" not in blocker_codes
    assert "wordpress_draft_write_readiness" in requirement_codes
    assert "wordpress_draft_handoff_ready" in requirement_codes
    assert "wordpress_draft_package_ready" in requirement_codes
    assert "wordpress_draft_target_content_ready" in requirement_codes
    assert "wordpress_draft_live_write_env" in requirement_codes
    assert "wordpress_write_authorization" in requirement_codes
    assert "missing_wordpress_draft_handoff_ready" in blocker_codes
    assert "missing_wordpress_draft_package_ready" not in blocker_codes
    assert "missing_wordpress_draft_target_content_ready" in blocker_codes
    assert "missing_wordpress_draft_write_readiness" in blocker_codes
    assert "missing_wordpress_draft_live_write_env" in blocker_codes
    assert "missing_wordpress_write_authorization" in blocker_codes
    target_requirement = next(
        requirement
        for requirement in data["requirements"]
        if requirement["code"] == "wordpress_draft_target_content_ready"
    )
    assert target_requirement["satisfied"] is False
    assert "draft_package_ready=true" in target_requirement["evidence"]
    assert "human_review_ready=false" in target_requirement["evidence"]
    package_requirement = next(
        requirement
        for requirement in data["requirements"]
        if requirement["code"] == "wordpress_draft_package_ready"
    )
    assert package_requirement["satisfied"] is True
    assert package_requirement["evidence"].startswith("draft_package_")
    target_blocker = next(
        blocker
        for blocker in data["blockers"]
        if blocker["code"] == "missing_wordpress_draft_target_content_ready"
    )
    assert "Claim Ledger" in target_blocker["reason"]
    assert "draft package" in target_blocker["next_step"]


def test_wordpress_apply_action_blocks_payload_before_vendor_write(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "actions_apply_block.sqlite3"))

    client = TestClient(app)
    response = client.post(
        "/api/actions/act_apply_wordpress_draft_handoff/apply",
        json={"confirm": True, "confirmed_by": "operator_test"},
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["status"] == "blocked"
    assert detail["applied"] is False
    assert detail["mutation_audit"]["mutation_attempted"] is False
    assert detail["mutation_audit"]["adapter_reached"] is False
    assert detail["mutation_audit"]["external_write_attempted"] is False
    assert detail["mutation_audit"]["mutation_adapter"] == "wordpress_draft_execution_boundary"
    assert detail["adapter_result"] is None
    serialized = str(detail)
    assert "Payload akcji nie pozwala jeszcze na zapis zmian." in serialized
    assert "Payload akcji nie jest gotowy do mutacji API." in serialized
    action_response = client.get("/api/actions/act_apply_wordpress_draft_handoff")
    assert action_response.status_code == 200
    review_gate = action_response.json()["review_gate"]
    assert review_gate["last_mutation_adapter_reached"] is False
    assert review_gate["last_external_write_attempted"] is False
    assert (
        review_gate["last_mutation_adapter_reached_label"]
        == "adapter wykonania nie został osiągnięty"
    )


def test_wordpress_apply_audit_separates_adapter_boundary_from_vendor_write(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "wilq.actions.service.get_connector_status",
        lambda _connector_id: SimpleNamespace(configured=True),
    )
    action = ActionObject(
        id="act_apply_wordpress_draft_handoff",
        title="Aktywuj zapis szkicu WordPress draft-only",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.medium,
        status=ActionStatus.ready,
        evidence_ids=["ev_wordpress_draft_apply_boundary"],
        human_diagnosis="Testowy apply-mode kandydat dla granicy adaptera WordPress.",
        recommended_reason="Sprawdza, czy audit nie myli adaptera z vendor write.",
        payload={
            "action_type": "wordpress_draft_handoff",
            "connector": "wordpress_ekologus",
            "allowed_operation": "create_wordpress_draft",
            "apply_allowed": True,
            "api_mutation_ready": True,
            "destructive": False,
        },
        validation_status="valid",
        created_by="test",
        audit_events=[
            AuditEvent(
                id="audit_preview_test",
                action_id="act_apply_wordpress_draft_handoff",
                event_type="action_preview_generated",
                actor="operator_test",
                summary="Podgląd zapisany.",
            ),
            AuditEvent(
                id="audit_confirm_test",
                action_id="act_apply_wordpress_draft_handoff",
                event_type="action_apply_confirmed",
                actor="operator_test",
                summary="Potwierdzenie zapisane.",
            ),
            AuditEvent(
                id="audit_impact_test",
                action_id="act_apply_wordpress_draft_handoff",
                event_type="action_impact_check_completed",
                actor="operator_test",
                summary="Impact check zapisany.",
            ),
        ],
    )

    result = apply_action(
        action,
        ActionApplyRequest(confirm=True, confirmed_by="operator_test"),
    )

    assert result.applied is False
    assert result.status == "blocked"
    assert result.adapter_result is None
    assert result.errors == [
        "Apply szkicu WordPress wymaga typed work item, handoff, draft package i target URL."
    ]
    assert result.mutation_audit.adapter_reached is False
    assert result.mutation_audit.external_write_attempted is False
    assert result.mutation_audit.mutation_attempted is False
    assert "Mutation blocked before any vendor API call" in result.mutation_audit.summary


def test_wordpress_apply_uses_typed_capability_and_dev_adapter(monkeypatch) -> None:
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")
    monkeypatch.setattr(
        "wilq.actions.service.get_connector_status",
        lambda _connector_id: SimpleNamespace(configured=True),
    )
    action = ActionObject(
        id="act_apply_wordpress_draft_handoff",
        title="Aktywuj zapis szkicu WordPress draft-only",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.medium,
        status=ActionStatus.ready,
        evidence_ids=["ev_wordpress_draft_apply_boundary"],
        human_diagnosis="Testowy apply capability.",
        recommended_reason="Testuje centralny adapter dev-only.",
        payload={
            "action_type": "wordpress_draft_handoff",
            "connector": "wordpress_ekologus",
            "allowed_operation": "create_wordpress_draft",
            "apply_allowed": False,
            "api_mutation_ready": False,
            "destructive": False,
        },
        validation_status="valid",
        created_by="test",
        audit_events=[
            AuditEvent(
                id="audit_preview_test",
                action_id="act_apply_wordpress_draft_handoff",
                event_type="action_preview_generated",
                actor="operator_test",
                summary="Podgląd zapisany.",
            ),
            AuditEvent(
                id="audit_confirm_test",
                action_id="act_apply_wordpress_draft_handoff",
                event_type="action_apply_confirmed",
                actor="operator_test",
                summary="Potwierdzenie zapisane.",
            ),
            AuditEvent(
                id="audit_impact_test",
                action_id="act_apply_wordpress_draft_handoff",
                event_type="action_impact_check_completed",
                actor="operator_test",
                summary="Impact check zapisany.",
            ),
        ],
    )
    handoff = ContentWordPressDraftHandoff.model_validate(
        {
            "id": "wordpress_draft_handoff_content_work_item_bdo",
            "work_item_id": "content_work_item_bdo",
            "draft_package_id": "draft_package_content_work_item_bdo",
            "human_review_id": "human_review_bdo",
            "audit_id": "audit_bdo",
            "title": "BDO dla firm",
            "final_canonical_url": "https://ekologus.pl/bdo/",
            "intended_final_url": "https://ekologus.pl/bdo/",
            "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
            "evidence_ids": ["ev_wordpress_draft_apply_boundary"],
        }
    )
    draft_package = ContentDraftPackage.model_validate(
        {
            "id": "draft_package_content_work_item_bdo",
            "work_item_id": "content_work_item_bdo",
            "brief_id": "brief_bdo",
            "claim_ledger_id": "ledger_bdo",
            "draft_kind": "outline",
            "title": "BDO dla firm",
            "sections": [],
            "section_to_evidence_map": [],
            "claims_used": [],
            "claims_removed_or_blocked": [],
            "human_review_questions": [],
            "publish_ready": False,
        }
    )
    capability = action_service.WordPressDraftApplyCapability(
        handoff=handoff,
        draft_package=draft_package,
        write_authorization=ContentWordPressDraftWriteAuthorization(
            action_id=action.id,
            preview_audit_id="audit_preview_test",
            review_audit_id="audit_review_test",
            confirmation_audit_id="audit_confirm_test",
            confirmed_by="operator_test",
        ),
    )
    monkeypatch.setattr(
        action_service,
        "_wordpress_draft_apply_capability",
        lambda *_: (capability, []),
    )
    monkeypatch.setattr(action_service, "create_wordpress_draft_post", lambda _payload: "321")

    result = apply_action(
        action,
        ActionApplyRequest(
            confirm=True,
            confirmed_by="operator_test",
            wordpress_draft=ActionWordPressDraftApplyInput(
                work_item_id="content_work_item_bdo",
                handoff_id=handoff.id,
                draft_package_id=draft_package.id,
                target_url=handoff.final_canonical_url,
            ),
        ),
    )

    assert result.adapter_result is not None
    assert result.adapter_result["execution_result"]["blockers"] == []
    assert result.errors == []
    assert result.applied is True
    assert result.adapter_result is not None
    assert result.adapter_result["execution_status"] == "created"
    assert result.adapter_result["external_write_attempted"] is True
    assert result.mutation_audit.adapter_reached is True


def test_wordpress_apply_capability_builder_binds_current_snapshot(monkeypatch) -> None:
    action = ActionObject(
        id="act_apply_wordpress_draft_handoff",
        title="Aktywuj zapis szkicu WordPress draft-only",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.medium,
        status=ActionStatus.ready,
        evidence_ids=["ev_wordpress_draft_apply_boundary"],
        human_diagnosis="Test wiązania bieżącego snapshotu.",
        recommended_reason="Nie pozwala rozjechać identyfikatorów apply.",
        payload={"allowed_operation": "create_wordpress_draft"},
        validation_status="valid",
        created_by="test",
        audit_events=[
            AuditEvent(
                id="audit_preview_builder",
                action_id=action_id,
                event_type="action_preview_generated",
                actor="operator_test",
                summary="Podgląd zapisany.",
            )
            for action_id in ["act_apply_wordpress_draft_handoff"]
        ]
        + [
            AuditEvent(
                id="audit_confirm_builder",
                action_id="act_apply_wordpress_draft_handoff",
                event_type="action_apply_confirmed",
                actor="operator_test",
                summary="Potwierdzenie zapisane.",
            )
        ],
    )
    handoff = SimpleNamespace(
        id="wordpress_draft_handoff_content_work_item_bdo",
        work_item_id="content_work_item_bdo",
        final_canonical_url="https://ekologus.pl/bdo/",
        publish_allowed=False,
        destructive_update_allowed=False,
    )
    draft_package = SimpleNamespace(id="draft_package_content_work_item_bdo")
    snapshot = SimpleNamespace(
        draft_package=SimpleNamespace(
            draft_package_result=SimpleNamespace(draft_package=draft_package)
        ),
        wordpress_handoff=SimpleNamespace(
            handoff_result=SimpleNamespace(handoff=handoff)
        ),
    )
    review = SimpleNamespace(id="human_review_content_work_item_bdo")
    audit = SimpleNamespace(id="audit_content_work_item_bdo")
    monkeypatch.setattr(
        "wilq.briefing.content_diagnostics.build_content_diagnostics_cached",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        action_service,
        "content_workflow_store",
        lambda: SimpleNamespace(
            latest_human_review=lambda _work_item_id: review,
            latest_audit_for_review=lambda _review_id: audit,
        ),
    )
    monkeypatch.setattr(
        action_service,
        "build_content_work_item_diagnostics_snapshot_response_for_work_item",
        lambda _diagnostics, _work_item_id, *, human_review, audit: snapshot,
    )

    capability, errors = action_service._wordpress_draft_apply_capability(
        action,
        ActionApplyRequest(
            confirm=True,
            confirmed_by="operator_test",
            wordpress_draft=ActionWordPressDraftApplyInput(
                work_item_id="content_work_item_bdo",
                handoff_id=handoff.id,
                draft_package_id=draft_package.id,
                target_url=handoff.final_canonical_url,
            ),
        ),
    )

    assert errors == []
    assert capability is not None
    assert capability.write_authorization.review_audit_id == review.id
    assert capability.write_authorization.confirmation_audit_id == "audit_confirm_builder"

    mismatch, mismatch_errors = action_service._wordpress_draft_apply_capability(
        action,
        ActionApplyRequest(
            confirm=True,
            confirmed_by="operator_test",
            wordpress_draft=ActionWordPressDraftApplyInput(
                work_item_id="content_work_item_bdo",
                handoff_id=handoff.id,
                draft_package_id=draft_package.id,
                target_url="https://ekologus.pl/inny-adres/",
            ),
        ),
    )
    assert mismatch is None
    assert mismatch_errors == ["Canonical URL nie pasuje do zatwierdzonego handoffu."]


def test_wordpress_apply_route_reaches_adapter_only_after_real_capability_binding(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "route_apply.sqlite3"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")
    action = ActionObject(
        id="act_apply_wordpress_draft_handoff",
        title="Aktywuj zapis szkicu WordPress draft-only",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.medium,
        status=ActionStatus.ready,
        evidence_ids=["ev_wordpress_draft_apply_boundary"],
        human_diagnosis="Test route apply.",
        recommended_reason="Testuje centralną granicę.",
        payload={"allowed_operation": "create_wordpress_draft"},
        validation_status="valid",
        created_by="test",
        audit_events=[
            AuditEvent(
                id="audit_preview_route",
                action_id="act_apply_wordpress_draft_handoff",
                event_type="action_preview_generated",
                actor="operator_route",
                summary="Podgląd.",
            ),
            AuditEvent(
                id="audit_confirm_route",
                action_id="act_apply_wordpress_draft_handoff",
                event_type="action_apply_confirmed",
                actor="operator_route",
                summary="Potwierdzenie.",
            ),
            AuditEvent(
                id="audit_impact_route",
                action_id="act_apply_wordpress_draft_handoff",
                event_type="action_impact_check_completed",
                actor="operator_route",
                summary="Impact check.",
            ),
        ],
    )
    handoff = SimpleNamespace(
        id="handoff_route",
        work_item_id="work_item_route",
        final_canonical_url="https://ekologus.pl/route/",
        publish_allowed=False,
        destructive_update_allowed=False,
    )
    draft_package = SimpleNamespace(id="draft_package_route")
    snapshot = SimpleNamespace(
        draft_package=SimpleNamespace(
            draft_package_result=SimpleNamespace(draft_package=draft_package)
        ),
        wordpress_handoff=SimpleNamespace(
            handoff_result=SimpleNamespace(handoff=handoff)
        ),
    )
    review = SimpleNamespace(id="review_route")
    monkeypatch.setattr("apps.api.wilq_api.routers.actions.get_action", lambda _id: action)
    monkeypatch.setattr(
        "wilq.actions.service.get_connector_status",
        lambda _id: SimpleNamespace(configured=True),
    )
    monkeypatch.setattr(
        "wilq.briefing.content_diagnostics.build_content_diagnostics_cached",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        action_service,
        "content_workflow_store",
        lambda: SimpleNamespace(
            latest_human_review=lambda _id: review,
            latest_audit_for_review=lambda _id: SimpleNamespace(id="audit_content_route"),
        ),
    )
    monkeypatch.setattr(
        action_service,
        "build_content_work_item_diagnostics_snapshot_response_for_work_item",
        lambda *_args, **_kwargs: snapshot,
    )
    monkeypatch.setattr(
        action_service,
        "execute_content_wordpress_draft_handoff",
        lambda **_kwargs: SimpleNamespace(
            status="created",
            mode="live",
            external_write_attempted=True,
            wordpress_post_id="42",
            blockers=[],
            boundary=SimpleNamespace(
                allowed_operation="create_wordpress_draft",
                dry_run_default=True,
                live_write_enabled=True,
                live_adapter_configured=True,
                publish_allowed=False,
                destructive_update_allowed=False,
            ),
            payload={},
            model_dump=lambda **_kwargs: {
                "status": "created",
                "mode": "live",
                "external_write_attempted": True,
                "wordpress_post_id": "42",
                "blockers": [],
            },
        ),
    )

    response = TestClient(app).post(
        "/api/actions/act_apply_wordpress_draft_handoff/apply",
        json={
            "confirm": True,
            "confirmed_by": "operator_route",
            "wordpress_draft": {
                "work_item_id": handoff.work_item_id,
                "handoff_id": handoff.id,
                "draft_package_id": draft_package.id,
                "target_url": handoff.final_canonical_url,
            },
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["applied"] is True
    assert data["adapter_result"]["external_write_attempted"] is True
    assert data["mutation_audit"]["adapter_reached"] is True


def test_action_mutation_readiness_summary_reports_no_vendor_writes(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "actions_summary.sqlite3"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "0")

    data = _get_mutation_readiness_summary()

    assert data["action_count"] >= 1
    assert data["vendor_write_possible_count"] == 0
    assert data["would_attempt_vendor_write_count"] == 0
    assert data["missing_adapter_count"] == data["action_count"] - 1
    assert "missing_mutation_adapter" in data["top_blockers"]
    assert data["first_write_candidate"]["action_id"] == "act_apply_wordpress_draft_handoff"
    assert data["first_write_candidate"]["vendor_write_possible"] is False
    assert data["first_write_candidate"]["mutation_adapter"] == "wordpress_draft_execution_boundary"
    assert data["first_write_candidate"]["target_label"]
    assert data["first_write_candidate"]["write_authorization_status"] == "missing_audit_trace"
    assert data["first_write_candidate"]["missing_audit_event_types"] == [
        "action_preview_generated",
        "human_review_*",
        "action_apply_confirmed",
    ]
    assert data["first_write_candidate"]["apply_contract"]["adapter_status"] == "implemented"
    assert "WordPress draft-only" in data["first_write_candidate_reason"]
    assert "boundary i paczka szkicu" in data["first_write_candidate_reason"]
    assert any("draft-only" in step for step in data["activation_plan_steps"])
    assert any(
        "boundary i paczka szkicu istnieją" in step
        for step in data["activation_plan_steps"]
    )
    assert any("handoff" in step for step in data["activation_plan_steps"])
    assert not any(
        "Podepnij zatwierdzoną paczkę szkicu" in step
        for step in data["activation_plan_steps"]
    )
    assert any("Claim Ledger" in step for step in data["activation_plan_steps"])
    assert "Adapter boundary już istnieje" in data["activation_next_step"]
    assert "zostaw adapter" not in data["activation_next_step"]
    assert data["items"][0]["response_type"] == "action_mutation_readiness"
    assert "adapter boundary" in data["operator_next_step"]
    assert "boundary i paczkę szkicu" in data["operator_next_step"]
    assert "human review i audit" in data["operator_next_step"]
    assert data["first_write_candidate"]["target_url"] in data["operator_next_step"]


def test_action_mutation_readiness_returns_404_for_unknown_action() -> None:
    response = TestClient(app).get(
        "/api/actions/no-such-action/mutation-readiness",
    )

    assert response.status_code == 404
