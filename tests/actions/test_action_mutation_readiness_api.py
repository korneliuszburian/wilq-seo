from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock
from types import SimpleNamespace
from typing import Any, cast

from fastapi.testclient import TestClient
from typer.testing import CliRunner

import wilq.actions.service as action_service
from apps.api.wilq_api.main import app
from wilq.actions.service import apply_action
from wilq.actions.wordpress_mutation_requirements import WordPressDraftApplyCapability
from wilq.cli import app as cli_app
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.handoff.wordpress import ContentWordPressDraftHandoff
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftExecutionBoundary,
    ContentWordPressDraftExecutionResult,
    ContentWordPressDraftWriteAuthorization,
)
from wilq.content.workflow.revision_binding import ContentDraftRevisionBinding
from wilq.content.workflow.revisions import (
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionReviewCommand,
    ContentDraftRevisionSection,
)
from wilq.content.workflow.store import content_workflow_store
from wilq.schemas import (
    ActionApplyRequest,
    ActionMode,
    ActionMutationAuditRecord,
    ActionObject,
    ActionRisk,
    ActionStatus,
    AuditEvent,
    OpportunityDomain,
)
from wilq.storage.local_state import local_state_store


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


def _seed_approved_revision_binding(
    *,
    work_item_id: str,
    draft_package_id: str,
    final_canonical_url: str,
) -> ContentDraftRevisionBinding:
    store = content_workflow_store()
    created = store.append_draft_revision(
        ContentDraftRevisionAppendCommand(
            work_item_id=work_item_id,
            draft_package_id=draft_package_id,
            draft_package_digest="b" * 64,
            planning_digest="c" * 64,
            final_canonical_url=final_canonical_url,
            title="Zatwierdzona treść",
            sections=[
                ContentDraftRevisionSection(
                    heading="Zakres usługi",
                    body_markdown="Dokładna treść zatwierdzonej wersji.",
                    evidence_ids=["ev_wordpress_draft_apply_boundary"],
                )
            ],
            created_by="operator_test",
        )
    )
    assert created.revision is not None
    revision = created.revision
    reviewed = store.review_draft_revision(
        ContentDraftRevisionReviewCommand(
            work_item_id=work_item_id,
            revision_id=revision.revision_id,
            revision_digest=revision.content_digest,
            decision="approved",
            reviewed_by="operator_test",
            checked_items=["tekst", "dowody"],
            evidence_ids=["ev_wordpress_draft_apply_boundary"],
        )
    )
    assert reviewed.review is not None
    return ContentDraftRevisionBinding(
        work_item_id=work_item_id,
        handoff_id=f"wordpress_draft_handoff_{work_item_id}_{revision.revision_id}",
        revision_id=revision.revision_id,
        content_digest=revision.content_digest,
        draft_package_id=revision.draft_package_id,
        draft_package_digest=revision.draft_package_digest,
        planning_digest=revision.planning_digest,
        approval_decision_id=reviewed.review.decision_id,
        final_canonical_url=revision.final_canonical_url,
    )


def test_failed_wordpress_apply_claim_consumes_binding_and_releases_revision_lock(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "failed_apply_claim.sqlite3"))
    binding = _seed_approved_revision_binding(
        work_item_id="work_item_failed_claim",
        draft_package_id="draft_package_failed_claim",
        final_canonical_url="https://ekologus.pl/failed-claim/",
    )
    store = content_workflow_store()

    assert (
        store.claim_wordpress_revision_apply(
            binding,
            action_id="act_apply_wordpress_draft_handoff",
            claimed_by="operator_test",
        )
        == "acquired"
    )
    outcome_audit = AuditEvent(
        id="audit_failed_claim_outcome",
        action_id="act_apply_wordpress_draft_handoff",
        event_type="apply_blocked",
        actor="operator_test",
        summary="Adapter zwrócił niepewny wynik.",
        details={"wordpress_draft_binding": binding.model_dump(mode="json")},
    )
    mutation_audit = ActionMutationAuditRecord(
        id="mutation_failed_claim_outcome",
        action_id="act_apply_wordpress_draft_handoff",
        connector="wordpress_ekologus",
        status="blocked",
        actor="operator_test",
        audit_event_id=outcome_audit.id,
        summary="Niepewny wynik adaptera został zapisany atomowo.",
        wordpress_draft_binding=binding,
    )
    blocked_execution = ContentWordPressDraftExecutionResult(
        status="blocked",
        mode="live",
        boundary=ContentWordPressDraftExecutionBoundary(
            live_write_enabled=True,
            live_adapter_configured=True,
        ),
        external_write_attempted=True,
    )
    store.finish_wordpress_revision_apply_claim(
        binding,
        status="failed",
        audit_event=outcome_audit,
        mutation_audit=mutation_audit,
        adapter_result={
            "execution_result": blocked_execution.model_dump(mode="json")
        },
    )
    assert (
        store.claim_wordpress_revision_apply(
            binding,
            action_id="act_apply_wordpress_draft_handoff",
            claimed_by="operator_test",
        )
        == "failed"
    )
    assert local_state_store().list_audit_events(action_id=outcome_audit.action_id)[0].id == (
        outcome_audit.id
    )
    assert local_state_store().list_action_mutation_audits(
        action_id=outcome_audit.action_id
    )[0].id == mutation_audit.id
    assert store.latest_wordpress_draft_execution(binding.work_item_id) == blocked_execution

    next_revision = store.append_draft_revision(
        ContentDraftRevisionAppendCommand(
            work_item_id=binding.work_item_id,
            base_revision_id=binding.revision_id,
            draft_package_id=binding.draft_package_id,
            draft_package_digest=binding.draft_package_digest,
            planning_digest=binding.planning_digest,
            final_canonical_url=binding.final_canonical_url,
            title="Nowa wersja po nieudanym apply",
            sections=[
                ContentDraftRevisionSection(
                    heading="Zakres usługi",
                    body_markdown="Jawnie nowa wersja wymaga nowego review.",
                    evidence_ids=["ev_wordpress_draft_apply_boundary"],
                )
            ],
            created_by="operator_test",
        )
    )
    assert next_revision.status == "created"
    assert (
        store.claim_wordpress_revision_apply(
            binding,
            action_id="act_apply_wordpress_draft_handoff",
            claimed_by="operator_test",
        )
        == "not_current"
    )


def test_failed_wordpress_apply_claim_retries_when_adapter_was_not_reached(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "retryable_apply_claim.sqlite3"))
    binding = _seed_approved_revision_binding(
        work_item_id="work_item_retryable_claim",
        draft_package_id="draft_package_retryable_claim",
        final_canonical_url="https://ekologus.pl/retryable-claim/",
    )
    store = content_workflow_store()
    assert (
        store.claim_wordpress_revision_apply(
            binding,
            action_id="act_apply_wordpress_draft_handoff",
            claimed_by="operator_test",
        )
        == "acquired"
    )
    outcome_audit = AuditEvent(
        id="audit_retryable_claim_outcome",
        action_id="act_apply_wordpress_draft_handoff",
        event_type="apply_blocked",
        actor="operator_test",
        summary="Walidacja zablokowała zapis przed adapterem.",
        details={"wordpress_draft_binding": binding.model_dump(mode="json")},
    )
    mutation_audit = ActionMutationAuditRecord(
        id="mutation_retryable_claim_outcome",
        action_id="act_apply_wordpress_draft_handoff",
        connector="wordpress_ekologus",
        status="blocked",
        actor="operator_test",
        audit_event_id=outcome_audit.id,
        summary="Zapis zatrzymał się przed wywołaniem vendora.",
        wordpress_draft_binding=binding,
    )
    blocked_execution = ContentWordPressDraftExecutionResult(
        status="blocked",
        mode="live",
        boundary=ContentWordPressDraftExecutionBoundary(
            live_write_enabled=True,
            live_adapter_configured=True,
        ),
        revision_binding=binding,
        external_write_attempted=False,
    )
    store.finish_wordpress_revision_apply_claim(
        binding,
        status="failed",
        audit_event=outcome_audit,
        mutation_audit=mutation_audit,
        adapter_result={"execution_result": blocked_execution.model_dump(mode="json")},
    )
    assert (
        store.claim_wordpress_revision_apply(
            binding,
            action_id="act_apply_wordpress_draft_handoff",
            claimed_by="operator_test",
        )
        == "acquired"
    )


def test_wordpress_apply_reconciliation_reads_draft_and_never_retries_write(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "reconcile_apply_claim.sqlite3"))
    binding = _seed_approved_revision_binding(
        work_item_id="work_item_reconcile_claim",
        draft_package_id="draft_package_reconcile_claim",
        final_canonical_url="https://ekologus.pl/reconcile-claim/",
    )
    store = content_workflow_store()
    assert (
        store.claim_wordpress_revision_apply(
            binding,
            action_id="act_apply_wordpress_draft_handoff",
            claimed_by="operator_before_crash",
        )
        == "acquired"
    )
    readback_ids: list[str] = []
    write_attempts: list[str] = []

    def draft_readback(post_id: str):
        readback_ids.append(post_id)
        return SimpleNamespace(status="draft")

    def forbidden_write(*_args, **_kwargs):
        write_attempts.append("unexpected")
        raise AssertionError("Reconciliation retried the WordPress write.")

    monkeypatch.setattr("wilq.cli.read_wordpress_draft_post", draft_readback)
    monkeypatch.setattr(
        "wilq.connectors.wordpress.client.create_wordpress_draft_post",
        forbidden_write,
    )

    cli_args = [
        "wordpress-apply",
        "reconcile",
        "--work-item-id",
        binding.work_item_id,
        "--outcome",
        "applied",
        "--confirmed-by",
        "operator_recovery",
        "--notes",
        "Sprawdzono istniejący szkic na devie po przerwanym procesie.",
        "--wordpress-post-id",
        "1275",
        "--confirm-inspection",
    ]
    active_claim = CliRunner().invoke(cli_app, cli_args)
    assert active_claim.exit_code != 0
    assert readback_ids == ["1275"]
    assert write_attempts == []

    monkeypatch.setattr(
        "wilq.content.workflow.store.WORDPRESS_APPLY_RECONCILIATION_MIN_AGE_SECONDS",
        0,
    )
    result = CliRunner().invoke(cli_app, cli_args)

    assert result.exit_code == 0, result.output
    assert readback_ids == ["1275", "1275"]
    assert write_attempts == []
    assert "local_operator_attribution_only" in result.output
    reconciled_execution = store.latest_wordpress_draft_execution(binding.work_item_id)
    assert reconciled_execution is not None
    assert reconciled_execution.wordpress_post_id == "1275"
    assert (
        store.claim_wordpress_revision_apply(
            binding,
            action_id="act_apply_wordpress_draft_handoff",
            claimed_by="operator_replay",
        )
        == "applied"
    )
    assert any(
        event.event_type == "action_apply_reconciled"
        for event in local_state_store().list_audit_events(
            action_id="act_apply_wordpress_draft_handoff"
        )
    )


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
    assert [blocker.code for blocker in result.wordpress_revision_blockers] == [
        "wordpress_revision_binding_required"
    ]
    assert result.errors == [
        "Brakuje dokładnej wersji treści: Apply WordPress wymaga "
        "identyfikatorów zapisanej wersji, paczki i decyzji."
    ]
    assert result.mutation_audit.adapter_reached is False
    assert result.mutation_audit.external_write_attempted is False
    assert result.mutation_audit.mutation_attempted is False
    assert "Mutation blocked before any vendor API call" in result.mutation_audit.summary


def test_wordpress_apply_uses_typed_capability_and_dev_adapter(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "adapter_apply.sqlite3"))
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
    binding = _seed_approved_revision_binding(
        work_item_id="content_work_item_bdo",
        draft_package_id="draft_package_content_work_item_bdo",
        final_canonical_url="https://ekologus.pl/bdo/",
    )
    handoff = ContentWordPressDraftHandoff.model_validate(
        {
            "id": binding.handoff_id,
            "work_item_id": "content_work_item_bdo",
            "draft_package_id": "draft_package_content_work_item_bdo",
            "human_review_id": "human_review_bdo",
            "audit_id": "audit_bdo",
            "title": "BDO dla firm",
            "final_canonical_url": "https://ekologus.pl/bdo/",
            "intended_final_url": "https://ekologus.pl/bdo/",
            "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
            "evidence_ids": ["ev_wordpress_draft_apply_boundary"],
            "revision_binding": binding.model_dump(mode="json"),
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
    capability = WordPressDraftApplyCapability(
        handoff=handoff,
        draft_package=draft_package,
            write_authorization=ContentWordPressDraftWriteAuthorization(
                action_id=action.id,
                preview_audit_id="audit_preview_test",
                review_audit_id="audit_review_test",
                confirmation_audit_id="audit_confirm_test",
                impact_audit_id="audit_impact_test",
                confirmed_by="operator_test",
                wordpress_draft_binding=binding,
            ),
            section_overrides=[],
        )
    monkeypatch.setattr(
        action_service,
        "_wordpress_draft_apply_capability",
        lambda *_: (capability, []),
    )
    monkeypatch.setattr(
        "wilq.actions.wordpress_mutation_requirements.create_wordpress_draft_post",
        lambda _payload: "321",
    )
    monkeypatch.setattr(
        "wilq.actions.wordpress_mutation_requirements.wordpress_draft_write_authorization_verified",
        lambda _authorization: True,
    )

    result = apply_action(
        action,
        ActionApplyRequest(
            confirm=True,
            confirmed_by="operator_test",
            wordpress_draft=binding,
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
    binding = ContentDraftRevisionBinding(
        work_item_id="content_work_item_bdo",
        handoff_id="wordpress_draft_handoff_content_work_item_bdo",
        revision_id="content_revision_bdo_v1",
        content_digest="a" * 64,
        draft_package_id="draft_package_content_work_item_bdo",
        draft_package_digest="b" * 64,
        planning_digest="c" * 64,
        approval_decision_id="content_revision_decision_bdo_v1",
        final_canonical_url="https://ekologus.pl/bdo/",
    )
    binding_details = {"wordpress_draft_binding": binding.model_dump(mode="json")}
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
                action_id="act_apply_wordpress_draft_handoff",
                event_type="action_preview_generated",
                actor="operator_test",
                summary="Podgląd zapisany.",
                details=binding_details,
            ),
            AuditEvent(
                id="audit_review_builder",
                action_id="act_apply_wordpress_draft_handoff",
                event_type="human_review_approved_for_prepare",
                actor="operator_test",
                summary="Review zapisane.",
                details=binding_details,
            ),
            AuditEvent(
                id="audit_confirm_builder",
                action_id="act_apply_wordpress_draft_handoff",
                event_type="action_apply_confirmed",
                actor="operator_test",
                summary="Potwierdzenie zapisane.",
                details=binding_details,
            ),
            AuditEvent(
                id="audit_impact_builder",
                action_id="act_apply_wordpress_draft_handoff",
                event_type="action_impact_check_completed",
                actor="operator_test",
                summary="Impact zapisany.",
                details=binding_details,
            ),
        ],
    )
    handoff = SimpleNamespace(
        id=binding.handoff_id,
        work_item_id="content_work_item_bdo",
        final_canonical_url="https://ekologus.pl/bdo/",
        publish_allowed=False,
        destructive_update_allowed=False,
        revision_binding=binding,
        revision_sections=[],
    )
    draft_package = SimpleNamespace(id="draft_package_content_work_item_bdo")
    snapshot = SimpleNamespace(
        draft_package=SimpleNamespace(
            draft_package_result=SimpleNamespace(draft_package=draft_package)
        ),
        wordpress_handoff=SimpleNamespace(
            handoff_result=SimpleNamespace(handoff=handoff, blockers=[])
        ),
    )
    monkeypatch.setattr(
        "wilq.briefing.content_diagnostics.build_content_diagnostics_cached",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.store.content_workflow_store",
        lambda: SimpleNamespace(
            load_draft_revision_state=lambda _work_item_id: SimpleNamespace(),
            load_planning_decisions=lambda _work_item_id: [],
        ),
    )
    monkeypatch.setattr(
        "wilq.actions.wordpress_mutation_requirements.read_content_planning_proposal",
        lambda **_kwargs: SimpleNamespace(
            status="ready",
            proposal=SimpleNamespace(),
        ),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.api.build_content_work_item_diagnostics_snapshot_response_for_work_item",
        lambda _diagnostics, _work_item_id, **_kwargs: snapshot,
    )
    monkeypatch.setattr(
        "wilq.actions.wordpress_mutation_requirements.wordpress_draft_write_authorization_verified",
        lambda _authorization: True,
    )

    capability, errors = action_service._wordpress_draft_apply_capability(
        action,
        ActionApplyRequest(
            confirm=True,
            confirmed_by="operator_test",
            wordpress_draft=binding,
        ),
    )

    assert errors == []
    assert capability is not None
    assert capability.write_authorization.review_audit_id == "audit_review_builder"
    assert capability.write_authorization.confirmation_audit_id == "audit_confirm_builder"

    mismatch, mismatch_errors = action_service._wordpress_draft_apply_capability(
        action,
        ActionApplyRequest(
            confirm=True,
            confirmed_by="operator_test",
            wordpress_draft=binding.model_copy(
                update={"final_canonical_url": "https://ekologus.pl/inny-adres/"}
            ),
        ),
    )
    assert mismatch is None
    assert [blocker.code for blocker in mismatch_errors] == [
        "wordpress_revision_binding_mismatch"
    ]


def test_wordpress_apply_route_reaches_adapter_only_after_real_capability_binding(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "route_apply.sqlite3"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")
    binding = _seed_approved_revision_binding(
        work_item_id="work_item_route",
        draft_package_id="draft_package_route",
        final_canonical_url="https://ekologus.pl/route/",
    )
    binding_details = {"wordpress_draft_binding": binding.model_dump(mode="json")}
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
                actor="local_operator",
                summary="Podgląd.",
                details=binding_details,
            ),
            AuditEvent(
                id="audit_review_route",
                action_id="act_apply_wordpress_draft_handoff",
                event_type="human_review_approved_for_prepare",
                actor="local_operator",
                summary="Review.",
                details=binding_details,
            ),
            AuditEvent(
                id="audit_confirm_route",
                action_id="act_apply_wordpress_draft_handoff",
                event_type="action_apply_confirmed",
                actor="local_operator",
                summary="Potwierdzenie.",
                details=binding_details,
            ),
            AuditEvent(
                id="audit_impact_route",
                action_id="act_apply_wordpress_draft_handoff",
                event_type="action_impact_check_completed",
                actor="local_operator",
                summary="Impact check.",
                details=binding_details,
            ),
        ],
    )
    handoff = SimpleNamespace(
        id=binding.handoff_id,
        work_item_id="work_item_route",
        final_canonical_url="https://ekologus.pl/route/",
        publish_allowed=False,
        destructive_update_allowed=False,
        revision_binding=binding,
        revision_sections=[],
    )
    draft_package = SimpleNamespace(id="draft_package_route")
    snapshot = SimpleNamespace(
        draft_package=SimpleNamespace(
            draft_package_result=SimpleNamespace(draft_package=draft_package)
        ),
        wordpress_handoff=SimpleNamespace(
            handoff_result=SimpleNamespace(handoff=handoff, blockers=[])
        ),
    )
    monkeypatch.setattr("apps.api.wilq_api.routers.actions.get_action", lambda _id: action)
    monkeypatch.setattr(
        "wilq.actions.service.get_connector_status",
        lambda _id: SimpleNamespace(configured=True, label="WordPress"),
    )
    monkeypatch.setattr(
        "wilq.briefing.content_diagnostics.build_content_diagnostics_cached",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.store.content_workflow_store",
        lambda: SimpleNamespace(
            load_draft_revision_state=lambda _id: SimpleNamespace(),
            load_planning_decisions=lambda _id: [],
        ),
    )
    monkeypatch.setattr(
        "wilq.actions.wordpress_mutation_requirements.read_content_planning_proposal",
        lambda **_kwargs: SimpleNamespace(
            status="ready",
            proposal=SimpleNamespace(),
        ),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.api.build_content_work_item_diagnostics_snapshot_response_for_work_item",
        lambda *_args, **_kwargs: snapshot,
    )
    monkeypatch.setattr(
        "wilq.actions.wordpress_mutation_requirements.wordpress_draft_write_authorization_verified",
        lambda _authorization: True,
    )
    adapter_started = Event()
    release_adapter = Event()
    adapter_call_lock = Lock()
    adapter_call_count = 0

    def execute_wordpress_draft(**_kwargs):
        nonlocal adapter_call_count
        with adapter_call_lock:
            adapter_call_count += 1
        adapter_started.set()
        assert release_adapter.wait(timeout=5)
        return ContentWordPressDraftExecutionResult(
            status="created",
            mode="live",
            external_write_attempted=True,
            wordpress_post_id="42",
            boundary=ContentWordPressDraftExecutionBoundary(
                live_write_enabled=True,
                live_adapter_configured=True,
            ),
        )

    monkeypatch.setattr(
        "wilq.actions.wordpress_mutation_requirements.execute_content_wordpress_draft_handoff",
        execute_wordpress_draft,
    )

    apply_payload = {
        "confirm": True,
        "confirmed_by": "local_operator",
        "wordpress_draft": binding.model_dump(mode="json"),
    }

    def request_apply():
        return TestClient(app).post(
            "/api/actions/act_apply_wordpress_draft_handoff/apply",
            json=apply_payload,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(request_apply)
        assert adapter_started.wait(timeout=5)
        second_response = executor.submit(request_apply).result(timeout=5)

        append_during_apply = content_workflow_store().append_draft_revision(
            ContentDraftRevisionAppendCommand(
                work_item_id=binding.work_item_id,
                base_revision_id=binding.revision_id,
                draft_package_id=binding.draft_package_id,
                draft_package_digest=binding.draft_package_digest,
                planning_digest=binding.planning_digest,
                final_canonical_url=binding.final_canonical_url,
                title="Nowsza wersja podczas apply",
                sections=[
                    ContentDraftRevisionSection(
                        heading="Zakres usługi",
                        body_markdown="Treść, która nie może wyprzedzić trwającego apply.",
                        evidence_ids=["ev_wordpress_draft_apply_boundary"],
                    )
                ],
                created_by="operator_route",
            )
        )
        assert append_during_apply.conflict is not None
        assert append_during_apply.conflict.code == "apply_in_progress"

        release_adapter.set()
        first_response = first_future.result(timeout=5)

    assert first_response.status_code == 200, first_response.text
    first_data = first_response.json()
    assert first_data["applied"] is True
    assert first_data["adapter_result"]["external_write_attempted"] is True
    assert first_data["mutation_audit"]["adapter_reached"] is True

    assert second_response.status_code == 409, second_response.text
    second_detail = second_response.json()["detail"]
    assert [
        blocker["code"] for blocker in second_detail["wordpress_revision_blockers"]
    ] == ["wordpress_revision_apply_in_progress"]
    assert second_detail["adapter_result"] is None
    assert second_detail["mutation_audit"]["adapter_reached"] is False
    assert second_detail["mutation_audit"]["external_write_attempted"] is False

    replay_response = TestClient(app).post(
        "/api/actions/act_apply_wordpress_draft_handoff/apply",
        json=apply_payload,
    )
    assert replay_response.status_code == 409, replay_response.text
    replay_detail = replay_response.json()["detail"]
    assert [
        blocker["code"] for blocker in replay_detail["wordpress_revision_blockers"]
    ] == ["wordpress_revision_already_applied"]
    assert replay_detail["mutation_audit"]["adapter_reached"] is False
    assert replay_detail["mutation_audit"]["external_write_attempted"] is False
    assert adapter_call_count == 1

    append_after_apply = content_workflow_store().append_draft_revision(
        ContentDraftRevisionAppendCommand(
            work_item_id=binding.work_item_id,
            base_revision_id=binding.revision_id,
            draft_package_id=binding.draft_package_id,
            draft_package_digest=binding.draft_package_digest,
            planning_digest=binding.planning_digest,
            final_canonical_url=binding.final_canonical_url,
            title="Nowsza wersja po apply",
            sections=[
                ContentDraftRevisionSection(
                    heading="Zakres usługi",
                    body_markdown="Nowa wersja jest dozwolona po finalizacji claimu.",
                    evidence_ids=["ev_wordpress_draft_apply_boundary"],
                )
            ],
            created_by="operator_route",
        )
    )
    assert append_after_apply.status == "created"


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
