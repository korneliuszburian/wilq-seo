from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest

import wilq.content.workflow.workspace.selected_workspace as selected_workspace_module
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from wilq.actions.authority_audit_context import stamp_authority_audit_context
from wilq.content.canonical.urls import content_normalized_path
from wilq.content.workflow.authoring_inventory_receipt import (
    _build_content_authoring_inventory_receipt_from_catalog,
)
from wilq.content.workflow.current_preparation_readiness import (
    resolve_current_preparation_readiness,
)
from wilq.content.workflow.current_preparation_readiness_contracts import (
    ContentCurrentPreparationReadinessBlocked,
    ContentCurrentPreparationReadyForRefreshAuthorization,
)
from wilq.content.workflow.decisions.current_blocked import (
    build_current_all_blocked_classification,
)
from wilq.content.workflow.decisions.production import (
    ContentProductionBlocker,
    ContentProductionClassificationRun,
    ContentProductionRegisteredInventoryReceipt,
    project_content_production_classification,
)
from wilq.content.workflow.delivery_identity import (
    ContentDeliveryIdentityBinding,
    ContentDeliveryIdentityCommand,
    inventory_evidence_digest,
)
from wilq.content.workflow.pipeline_steps.operator_steps import (
    ContentWorkflowOperatorFacts,
    build_content_workflow_operator_journey,
)
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationBlocked,
    ContentRefreshPreparationBlocker,
    ContentRefreshPreparationClassificationBinding,
    build_content_refresh_preparation_authorization,
)
from wilq.content.workflow.refresh_preparation_operations import (
    preview as preview_refresh_preparation,
)
from wilq.content.workflow.refresh_preparation_resolution import classified_refresh_context
from wilq.content.workflow.source_fact_authority import (
    ContentSourceFactAuthorityPreviewCommand,
    execute_content_source_fact_authority,
    prepare_content_source_fact_authority_preview,
)
from wilq.content.workflow.source_pack_binding import (
    ContentSourcePackBindingCommand,
    build_content_source_pack_prerequisites,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
)
from wilq.content.workflow.workspace.document_lineage import (
    ContentDocumentWorkspaceDocumentLineage,
)
from wilq.content.workflow.workspace.document_workspace import (
    ContentDocumentWorkspace,
    ContentDocumentWorkspaceComparison,
    ContentDocumentWorkspaceDocument,
    ContentDocumentWorkspaceNextAction,
    ContentDocumentWorkspaceSourceSnapshot,
)
from wilq.content.workflow.workspace.production_decision import (
    build_content_production_decision,
)
from wilq.schemas import AuditEvent, ConnectorCoveredWindow, ContentFreshnessAssessment

CHECKED_AT = datetime.now(UTC) - timedelta(minutes=1)
WORK_ITEM_ID = "content_work_item_inventory_bdo"
BDO_PATH = "/bdo-co-musi-wiedziec-przedsiebiorca"
UNPROTECTED_PATH = "/oferta/doradztwo-i-outsourcing-ekologiczny"
UNPROTECTED_SOURCE_FACT_ID = "ekologus_public_consulting_outsourcing_offer_2026_07_01"
_ReadinessSeed = tuple[ContentWorkflowStore, ContentProductionClassificationRun]


def _catalog(*, path: str = BDO_PATH) -> ContentInventoryCatalogResponse:
    is_bdo = path == BDO_PATH
    return ContentInventoryCatalogResponse(
        total_count=1,
        items=[
            ContentInventoryCatalogItem(
                catalog_id="catalog_bdo_current" if is_bdo else "catalog_unprotected_current",
                work_item_id=WORK_ITEM_ID,
                url=f"https://www.ekologus.pl{path}/",
                path=f"{path}/",
                content_type="post" if is_bdo else "page",
                content_summary=(
                    "Bieżący materiał BDO."
                    if is_bdo
                    else "Bieżąca strona doradztwa środowiskowego."
                ),
                section_headings=["Zakres"],
                material_status="content_and_structure",
                source_connector="wordpress_ekologus",
                evidence_id="ev_wp_current_readiness",
                collected_at=CHECKED_AT,
            )
        ],
        source_connectors=["wordpress_ekologus"],
        evidence_ids=["ev_wp_current_readiness"],
    )


def _freshness() -> ContentFreshnessAssessment:
    return ContentFreshnessAssessment(
        state="fresh",
        checked_at=CHECKED_AT,
        requires_refresh=False,
        connector_covered_windows={
            "google_search_console": ConnectorCoveredWindow(),
            "wordpress_ekologus": ConnectorCoveredWindow(),
        },
        summary="fresh",
        next_step="continue",
    )


def _seed_exact_current_receipts(
    tmp_path: Path,
) -> tuple[ContentWorkflowStore, ContentProductionClassificationRun]:
    store = ContentWorkflowStore(tmp_path / "current-readiness.sqlite3")
    run, identity = _seed_legacy_inventory(store, catalog=_catalog())
    _seed_exact_source_pack(store, identity)
    return store, run


def _seed_unprotected_exact_current_receipts(
    tmp_path: Path,
) -> _ReadinessSeed:
    store = ContentWorkflowStore(tmp_path / "current-readiness-unprotected.sqlite3")
    run, identity = _seed_legacy_inventory(store, catalog=_catalog(path=UNPROTECTED_PATH))
    _seed_exact_source_pack(store, identity, source_fact_id=UNPROTECTED_SOURCE_FACT_ID)
    return store, run


def _seed_legacy_inventory(
    store: ContentWorkflowStore,
    *,
    catalog: ContentInventoryCatalogResponse,
) -> tuple[ContentProductionClassificationRun, ContentDeliveryIdentityBinding]:
    freshness = _freshness()
    item = catalog.items[0]
    receipt = _build_content_authoring_inventory_receipt_from_catalog(
        item=item,
        catalog=catalog,
        recorded_by="readiness_test",
        recorded_at=CHECKED_AT,
    )
    run = build_current_all_blocked_classification(
        catalog=catalog,
        freshness=freshness,
        base_revision="a" * 40,
        recorded_at=CHECKED_AT,
        inventory_receipts={content_normalized_path(item.path): receipt},
    )
    store.record_content_authoring_inventory_receipt(receipt)
    store.record_production_classification(run)
    row = next(item for item in run.rows if item.current_work_item_id == WORK_ITEM_ID)
    registered_receipt = cast(
        ContentProductionRegisteredInventoryReceipt,
        row.source_receipt,
    )
    evidence_ids = tuple(sorted(registered_receipt.catalog_snapshot_evidence_ids))
    identity_command = ContentDeliveryIdentityCommand(
        canonical_path=row.canonical_path,
        public_url=row.public_url,
        current_work_item_id=WORK_ITEM_ID,
        classification_run_id=run.run_id,
        classification_run_digest=run.run_digest,
        classification_decision_set_digest=run.input.decision_set_digest,
        classification_source_row_digest=row.source_packet_row_digest,
        inventory_evidence_ids=evidence_ids,
        inventory_evidence_digest=inventory_evidence_digest(evidence_ids),
        final_disposition="keep",
        inventory_receipt_id=registered_receipt.receipt_id,
        inventory_receipt_digest=registered_receipt.receipt_digest,
        inventory_catalog_id=registered_receipt.catalog_id,
        inventory_catalog_item_digest=registered_receipt.catalog_item_digest,
        inventory_catalog_snapshot_digest=registered_receipt.catalog_snapshot_digest,
        inventory_catalog_snapshot_evidence_ids=evidence_ids,
        inventory_receipt=registered_receipt,
        recorded_by="readiness_test",
        recorded_at=CHECKED_AT,
    )
    identity = store.record_content_delivery_identity(identity_command).binding
    return run, identity


def _seed_exact_source_pack(
    store: ContentWorkflowStore,
    identity: ContentDeliveryIdentityBinding,
    *,
    source_fact_id: str = "ekologus_public_bdo_faq_2026_07_01",
) -> None:
    preview = prepare_content_source_fact_authority_preview(
        store,
        ContentSourceFactAuthorityPreviewCommand(
            identity_binding_id=identity.binding_id,
            proposed_source_fact_ids=(source_fact_id,),
        ),
    )
    assert preview.status == "preview_ready", preview
    events = []
    for index, event_type in enumerate(
        (
            "action_preview_generated",
            "human_review_approved_for_prepare",
            "action_apply_confirmed",
            "action_impact_check_completed",
        )
    ):
        event = AuditEvent(
            id=f"audit_readiness_{index}",
            action_id=preview.action.id,
            event_type=event_type,
            actor="wilku",
            summary=event_type,
        )
        stamp_authority_audit_context(preview.action, event)
        events.append(event)
    applied, errors = execute_content_source_fact_authority(
        preview.action,
        store=store,
        audit_events=events,
    )
    assert errors == []
    assert applied is not None
    authority = store.list_content_source_fact_authority_receipts(
        identity_binding_id=identity.binding_id,
        current_work_item_id=WORK_ITEM_ID,
    )[-1]
    prerequisites = build_content_source_pack_prerequisites(
        identity,
        authority_receipt=authority,
        authority_receipts=(authority,),
        classification=store.load_production_classification_for_work_item(WORK_ITEM_ID),
        checked_at=datetime.now(UTC),
    )
    assert prerequisites.row_authority_status == "exact_current", prerequisites
    source_pack = store.record_content_source_pack_binding(
        ContentSourcePackBindingCommand(
            source_pack_id="source_pack_bdo_readiness",
            source_pack_sha256="a" * 64,
            identity_binding_id=identity.binding_id,
            identity_binding_digest=identity.binding_digest,
            current_work_item_id=WORK_ITEM_ID,
            source_fact_ids=prerequisites.approved_source_fact_ids,
            evidence_ids=prerequisites.row_authority_evidence_ids,
            fresh_context_digest=prerequisites.fresh_context_digest,
            source_fact_registry_receipt=prerequisites.source_fact_registry_receipt,
            fresh_context_attestation=prerequisites.fresh_context_attestation,
            source_fact_authority_receipt_id=authority.receipt_id,
            source_fact_authority_receipt_digest=authority.receipt_digest,
            source_fact_authority_snapshot_digest=authority.authority_snapshot.context_digest,
            recorded_by="readiness_test",
            recorded_at=CHECKED_AT,
        )
    )
    assert source_pack.binding.status == "exact_current", source_pack.binding.blocker


def _operator_journey():
    return build_content_workflow_operator_journey(
        ContentWorkflowOperatorFacts(
            sales_brief_present=True,
            sales_brief_signal_status="strong",
            sales_brief_signal_reason="Źródła są dostępne.",
            sales_brief_safe_next_step="Przejdź do planu.",
            sales_brief_blocker=None,
            section_map_present=True,
            section_map_blocker=None,
            section_map_safe_next_step="Przejdź do szkicu.",
            structured_contract_present=True,
            structured_contract_blocker=None,
            structured_contract_safe_next_step="Sprawdź szkic.",
        )
    )


def _workspace(work_item_id: str) -> ContentDocumentWorkspace:
    return ContentDocumentWorkspace(
        work_item_id=work_item_id,
        work_kind="refresh_existing",
        source_snapshot=ContentDocumentWorkspaceSourceSnapshot(
            status="unavailable",
            status_label="materiał niedostępny",
            reason="Testowy snapshot bez odczytu vendora.",
        ),
        canonical_document=ContentDocumentWorkspaceDocument(
            status="not_created",
            label="Brak rewizji",
            reason="Nie ma zapisanej rewizji.",
        ),
        document_lineage=ContentDocumentWorkspaceDocumentLineage(
            status="not_recorded",
            reason="Brak rewizji.",
        ),
        comparison=ContentDocumentWorkspaceComparison(
            status="unavailable",
            reason="Brak porównania.",
        ),
        next_action=ContentDocumentWorkspaceNextAction(
            kind="prepare_document",
            label="Przygotuj dokument",
            reason="Przygotowanie.",
        ),
    )


class _StoreProxy:
    def __init__(self, store: ContentWorkflowStore, *, identity=None, packs=None) -> None:
        self._store = store
        self._identity = identity
        self._packs = packs

    def __getattr__(self, name: str):
        return getattr(self._store, name)

    def load_latest_production_classification(self):
        return self._store.load_latest_production_classification()

    def load_content_delivery_identity(self, binding_id: str):
        return self._identity

    def load_content_delivery_identity_record(self, binding_id: str):
        if self._identity is None:
            return None
        return self._store.load_content_delivery_identity_record(binding_id)

    def list_content_source_pack_bindings(self, *, current_work_item_id: str | None = None):
        if self._packs is not None:
            return self._packs
        return self._store.list_content_source_pack_bindings(
            current_work_item_id=current_work_item_id
        )


def test_non_current_or_non_registered_blocked_row_never_upgrades() -> None:
    run = exact_public_bdo_run()
    result = resolve_current_preparation_readiness(
        object(),  # type: ignore[arg-type]
        run.rows[1].current_work_item_id or "work_current_2",
        run=run,
    )

    assert result.status == "blocked"
    assert result.code in {
        "registered_current_inventory_required",
        "current_content_binding_missing",
    }


def test_exact_current_receipts_are_ready_without_changing_blocked_classification(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, run = _seed_unprotected_exact_current_receipts(tmp_path)
    row = next(item for item in run.rows if item.current_work_item_id == WORK_ITEM_ID)
    assert row.decision == "blocked"
    assert len(row.blockers) == 1
    assert row.blockers[0].code == "current_content_binding_missing"
    assert row.blocked_historical_protection is None
    before = (run.run_digest, row.source_packet_row_digest, row.model_dump(mode="json"))

    readiness = resolve_current_preparation_readiness(store, WORK_ITEM_ID)

    assert isinstance(readiness, ContentCurrentPreparationReadyForRefreshAuthorization)
    assert readiness.status == "ready_for_refresh_authorization"
    assert readiness.identity_binding_id.startswith("content_delivery_identity_")
    assert readiness.source_pack_binding_id.startswith("content_source_pack_binding_")
    current = store.load_latest_production_classification()
    assert current is not None
    current_row = next(item for item in current.rows if item.current_work_item_id == WORK_ITEM_ID)
    assert (
        current.run_digest,
        current_row.source_packet_row_digest,
        current_row.model_dump(mode="json"),
    ) == before


def test_protected_historical_revision_blocks_refresh_before_preview_or_atomic_write(
    tmp_path: Path,
) -> None:
    store, run = _seed_exact_current_receipts(tmp_path)
    row = next(item for item in run.rows if item.current_work_item_id == WORK_ITEM_ID)
    protection = row.blocked_historical_protection
    assert row.canonical_path == "/bdo-co-musi-wiedziec-przedsiebiorca"
    assert protection is not None

    readiness = resolve_current_preparation_readiness(store, WORK_ITEM_ID)
    assert isinstance(readiness, ContentCurrentPreparationReadinessBlocked)
    assert readiness.status == "blocked"
    assert readiness.code == "protected_revision_reconciliation_required"
    assert readiness.classification_run_id == run.run_id
    assert readiness.classification_run_digest == run.run_digest
    assert readiness.decision_set_digest == run.input.decision_set_digest
    assert readiness.source_packet_row_digest == row.source_packet_row_digest
    assert readiness.reason_pl
    assert readiness.safe_next_step_pl
    operator_guidance = f"{readiness.reason_pl} {readiness.safe_next_step_pl}"
    assert protection.historical_revision_id not in operator_guidance
    assert protection.historical_revision_digest not in operator_guidance

    classified = classified_refresh_context(store, WORK_ITEM_ID)
    assert isinstance(classified, ContentRefreshPreparationBlocker)
    assert classified.code == "refresh_preparation_protected_revision_reconciliation_required"
    assert classified.reason == readiness.reason_pl
    assert classified.next_step == readiness.safe_next_step_pl

    preview = preview_refresh_preparation(
        store=store,
        snapshot_loader=lambda *_args: pytest.fail("Blocked classification must not rebuild."),
        work_item_id=WORK_ITEM_ID,
        service_card_id=None,
        content_kind_inventory_loader=lambda _work_item_id: pytest.fail(
            "Blocked classification must not read inventory."
        ),
    )
    assert isinstance(preview, ContentRefreshPreparationBlocked)
    assert preview.status == "blocked"
    assert preview.blockers == [classified]
    assert preview.safe_next_step == readiness.safe_next_step_pl

    classification = ContentRefreshPreparationClassificationBinding(
        classification_run_id=run.run_id,
        classification_run_digest=run.run_digest,
        decision_set_digest=run.input.decision_set_digest,
        source_packet_row_digest=row.source_packet_row_digest,
        current_work_item_id=WORK_ITEM_ID,
        canonical_path=row.canonical_path,
        public_url=row.public_url,
        classification_blocker_codes=[item.code for item in row.blockers],
    )
    authorization = build_content_refresh_preparation_authorization(
        work_item_id=WORK_ITEM_ID,
        classification=classification,
        planning_input_digest="f" * 64,
        service_card_id="ekologus_service_test",
        acknowledged_classification_blocker_codes=classification.classification_blocker_codes,
        authorized_by="wilku",
        authorized_at=CHECKED_AT,
    )
    with pytest.raises(
        ValueError,
        match="Refresh authorization does not bind the current classified row",
    ):
        store.record_refresh_preparation_authorization(authorization)
    assert store.load_refresh_preparation_authorization(authorization.authorization_id) is None
    with store._connect() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM content_refresh_preparation_authorizations"
        ).fetchone()[0]
    assert count == 0


def test_protected_bdo_blocked_readiness_keeps_workspace_generation_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, run = _seed_exact_current_receipts(tmp_path)
    row = next(item for item in run.rows if item.current_work_item_id == WORK_ITEM_ID)
    protection = row.blocked_historical_protection
    assert row.canonical_path == "/bdo-co-musi-wiedziec-przedsiebiorca"
    assert protection is not None
    readiness = resolve_current_preparation_readiness(store, WORK_ITEM_ID)
    classified = classified_refresh_context(store, WORK_ITEM_ID)

    assert isinstance(readiness, ContentCurrentPreparationReadinessBlocked)
    assert readiness.status == "blocked"
    assert readiness.code == "protected_revision_reconciliation_required"
    assert readiness.work_item_id == WORK_ITEM_ID
    assert readiness.classification_run_id == run.run_id
    assert readiness.classification_run_digest == run.run_digest
    assert isinstance(classified, ContentRefreshPreparationBlocker)
    assert classified.code == "refresh_preparation_protected_revision_reconciliation_required"
    assert classified.reason == readiness.reason_pl
    assert classified.next_step == readiness.safe_next_step_pl
    production = build_content_production_decision(
        WORK_ITEM_ID,
        classification=project_content_production_classification(run, row),
    )
    identity_binding_id = selected_workspace_module.selected_workspace_identity_binding_id(
        production
    )
    assert identity_binding_id is not None
    identity_record = store.load_content_delivery_identity_record(identity_binding_id)
    assert identity_record is not None
    assert identity_record.binding.binding_id == identity_binding_id
    assert identity_record.binding.current_work_item_id == WORK_ITEM_ID
    assert identity_record.binding.classification_run_id == run.run_id
    assert identity_record.binding.classification_run_digest == run.run_digest
    monkeypatch.setattr(
        selected_workspace_module,
        "build_content_document_workspace",
        lambda _work_item_id, **_kwargs: _workspace(WORK_ITEM_ID),
    )
    selected = selected_workspace_module.build_content_selected_workspace_with_context(
        WORK_ITEM_ID,
        operator_journey=_operator_journey(),
        production_decision=production,
        identity_record=identity_record,
        current_preparation_readiness=readiness,
    )

    assert selected.status == "ready"
    assert selected.work_item_id == WORK_ITEM_ID
    assert selected.requested_work_item_id == WORK_ITEM_ID
    assert selected.identity_readiness.status == "bound"
    assert selected.identity_readiness.binding_id == identity_record.binding.binding_id
    assert selected.production_decision == production
    assert selected.production_decision.decision == "blocked"
    assert selected.production_decision.generation_allowed is False
    assert (
        selected.production_decision.current_work_item_id,
        selected.production_decision.run_id,
        selected.production_decision.run_digest,
        selected.production_decision.source_packet_row_digest,
    ) == (WORK_ITEM_ID, run.run_id, run.run_digest, row.source_packet_row_digest)
    assert tuple(blocker.code for blocker in selected.production_decision.blockers) == (
        "current_content_binding_missing",
        "protected_revision_reconciliation_required",
    )
    protected_blocker = selected.production_decision.blockers[1]
    assert protected_blocker.sources == (protection.current_verification_evidence_id,)
    assert protection.current_verification_evidence_id in (
        selected.production_decision.primary_evidence_ids
    )
    assert "revision_binding" not in selected.production_decision.model_dump()
    expected_reason = (
        "Historyczna klasyfikacja wskazuje chronioną rewizję; przed dalszą pracą "
        "trzeba zweryfikować jej dokładną tożsamość i skrót."
    )
    expected_safe_next_step = (
        "Przejrzyj w historycznej klasyfikacji dokładny identyfikator chronionej "
        "rewizji i jej skrót; nie uzgadniaj rewizji wyłącznie na podstawie URL."
    )
    assert selected.production_decision.reason_pl == expected_reason
    assert selected.production_decision.safe_next_step_pl == expected_safe_next_step
    assert selected.reason == expected_reason
    assert selected.safe_next_step == expected_safe_next_step
    operator_guidance = f"{selected.reason} {selected.safe_next_step}"
    assert protection.historical_revision_id not in operator_guidance
    assert protection.historical_revision_digest not in operator_guidance
    assert selected.workspace is not None
    assert selected.workspace.next_action.kind == "none"
    _assert_legacy_protected_ready_fails_closed(selected, readiness, identity_record)


def _assert_legacy_protected_ready_fails_closed(selected, readiness, identity_record):
    legacy_ready = ContentCurrentPreparationReadyForRefreshAuthorization.model_construct(
        **(readiness.model_dump() | {
            "status": "ready_for_refresh_authorization",
            "identity_binding_id": identity_record.binding.binding_id,
            "identity_binding_digest": identity_record.binding.binding_digest,
            "source_pack_binding_id": "legacy_source_pack",
            "source_pack_binding_digest": "a" * 64,
        })
    )
    with pytest.raises(ValueError, match="sole current_content_binding_missing blocker"):
        selected_workspace_module.ContentSelectedWorkspace.model_validate(
            {**selected.model_dump(), "current_preparation_readiness": legacy_ready}
        )


def test_generic_one_blocker_ready_receipts_keep_refresh_authorization_available(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, run = _seed_unprotected_exact_current_receipts(tmp_path)
    row = next(item for item in run.rows if item.current_work_item_id == WORK_ITEM_ID)
    assert row.decision == "blocked"
    assert len(row.blockers) == 1
    assert row.blockers[0].code == "current_content_binding_missing"
    assert row.blocked_historical_protection is None
    readiness = resolve_current_preparation_readiness(store, WORK_ITEM_ID)
    assert isinstance(readiness, ContentCurrentPreparationReadyForRefreshAuthorization)
    assert readiness.status == "ready_for_refresh_authorization"
    production = build_content_production_decision(
        WORK_ITEM_ID,
        classification=project_content_production_classification(run, row),
    )
    identity_record = store.load_content_delivery_identity_record(readiness.identity_binding_id)
    assert identity_record is not None
    monkeypatch.setattr(
        selected_workspace_module,
        "build_content_document_workspace",
        lambda _work_item_id, **_kwargs: _workspace(WORK_ITEM_ID),
    )

    selected = selected_workspace_module.build_content_selected_workspace_with_context(
        WORK_ITEM_ID,
        operator_journey=_operator_journey(),
        production_decision=production,
        identity_record=identity_record,
        current_preparation_readiness=readiness,
    )

    assert selected.status == "ready"
    assert selected.work_item_id == WORK_ITEM_ID
    assert selected.requested_work_item_id == WORK_ITEM_ID
    assert selected.identity_readiness.status == "bound"
    assert selected.identity_readiness.binding_id == readiness.identity_binding_id
    assert selected.production_decision.decision == "blocked"
    assert selected.production_decision.generation_allowed is False
    assert (
        selected.production_decision.current_work_item_id,
        selected.production_decision.run_id,
        selected.production_decision.run_digest,
        selected.production_decision.source_packet_row_digest,
    ) == (WORK_ITEM_ID, run.run_id, run.run_digest, row.source_packet_row_digest)
    assert tuple(blocker.code for blocker in selected.production_decision.blockers) == (
        "current_content_binding_missing",
    )
    assert selected.workspace is not None
    assert selected.workspace.next_action.kind == "prepare_document"
    assert selected.workspace.next_action.label == "Autoryzuj bieżący refresh"
    assert selected.reason == readiness.reason_pl
    assert selected.safe_next_step == readiness.safe_next_step_pl


@pytest.mark.parametrize(
    "mutation",
    [
        "foreign_work_item",
        "run_digest",
        "source_row_digest",
        "identity_id",
        "refresh_decision",
        "reuse_decision",
    ],
)
def test_public_selected_workspace_rejects_misaligned_ready_state(
    mutation: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, run = _seed_unprotected_exact_current_receipts(tmp_path)
    row = next(item for item in run.rows if item.current_work_item_id == WORK_ITEM_ID)
    assert row.blocked_historical_protection is None
    readiness = resolve_current_preparation_readiness(store, WORK_ITEM_ID)
    assert isinstance(readiness, ContentCurrentPreparationReadyForRefreshAuthorization)
    assert readiness.status == "ready_for_refresh_authorization"
    production = build_content_production_decision(
        WORK_ITEM_ID,
        classification=project_content_production_classification(run, row),
    )
    identity_record = store.load_content_delivery_identity_record(readiness.identity_binding_id)
    assert identity_record is not None
    monkeypatch.setattr(
        selected_workspace_module,
        "build_content_document_workspace",
        lambda _work_item_id, **_kwargs: _workspace(WORK_ITEM_ID),
    )
    selected = selected_workspace_module.build_content_selected_workspace_with_context(
        WORK_ITEM_ID,
        operator_journey=_operator_journey(),
        production_decision=production,
        identity_record=identity_record,
        current_preparation_readiness=readiness,
    )
    assert selected.work_item_id == WORK_ITEM_ID
    assert selected.requested_work_item_id == WORK_ITEM_ID
    assert selected.production_decision.run_id == run.run_id
    assert selected.production_decision.run_digest == run.run_digest
    assert selected.production_decision.current_work_item_id == WORK_ITEM_ID
    payload = selected.model_dump(mode="python")
    payload["current_preparation_readiness"] = readiness
    payload["production_decision"]["source_packet_row_digest"] = (
        production.source_packet_row_digest
    )
    assert (
        selected_workspace_module.ContentSelectedWorkspace.model_validate(payload) == selected
    )
    if mutation == "foreign_work_item":
        payload["current_preparation_readiness"] = readiness.model_copy(
            update={"work_item_id": "foreign_work_item"}
        )
    elif mutation == "run_digest":
        payload["current_preparation_readiness"] = readiness.model_copy(
            update={"classification_run_digest": "a" * 64}
        )
    elif mutation == "source_row_digest":
        payload["current_preparation_readiness"] = readiness.model_copy(
            update={"source_packet_row_digest": "a" * 64}
        )
    elif mutation == "identity_id":
        payload["identity_readiness"] = selected.identity_readiness.model_copy(
            update={"binding_id": "content_delivery_identity_foreign"}
        )
    elif mutation == "refresh_decision":
        payload["production_decision"] = production.model_copy(update={"decision": "refresh"})
    elif mutation == "reuse_decision":
        payload["production_decision"] = production.model_copy(update={"decision": "reuse"})

    with pytest.raises(ValueError):
        selected_workspace_module.ContentSelectedWorkspace.model_validate(payload)


@pytest.mark.parametrize(
    ("case", "expected_code"),
    [
        ("missing_identity", "identity_binding_missing"),
        ("nonkeep", "disposition_not_keep"),
        ("additional_blocker", "current_content_binding_missing"),
        ("newer_blocked_source_pack", "source_pack_binding_blocked"),
    ],
)
def test_receipt_drift_never_upgrades_current_blocked_row(
    case: str,
    expected_code: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, run = _seed_unprotected_exact_current_receipts(tmp_path)
    row = next(item for item in run.rows if item.current_work_item_id == WORK_ITEM_ID)
    assert row.blocked_historical_protection is None
    baseline = resolve_current_preparation_readiness(store, WORK_ITEM_ID)
    assert isinstance(baseline, ContentCurrentPreparationReadyForRefreshAuthorization)
    assert baseline.status == "ready_for_refresh_authorization"
    identity = store.load_content_delivery_identity(baseline.identity_binding_id)
    assert identity is not None
    proxy = _StoreProxy(store, identity=identity)
    row_override = row
    if case == "missing_identity":
        proxy = _StoreProxy(store, identity=None)
    elif case == "nonkeep":
        proxy = _StoreProxy(
            store,
            identity=identity.model_copy(update={"final_disposition": "redirect"}),
        )
    elif case == "additional_blocker":
        row_override = row.model_copy(
            update={
                "blockers": (
                    *row.blockers,
                    ContentProductionBlocker(
                        code="additional_blocker",
                        owner="test",
                        next_step_pl="Napraw dodatkowy blocker.",
                        sources=("test",),
                        blocks_initial_generation=True,
                    ),
                )
            }
        )
    else:
        exact_pack = store.list_content_source_pack_bindings(current_work_item_id=WORK_ITEM_ID)[0]
        blocked = store.record_content_source_pack_binding(
            ContentSourcePackBindingCommand(
                source_pack_id="source_pack_bdo_newer_blocked",
                source_pack_sha256="b" * 64,
                identity_binding_id=exact_pack.identity_binding_id,
                identity_binding_digest=exact_pack.identity_binding_digest,
                current_work_item_id=WORK_ITEM_ID,
                source_fact_ids=exact_pack.source_fact_ids,
                evidence_ids=exact_pack.evidence_ids,
                fresh_context_digest=exact_pack.fresh_context_digest,
                source_fact_registry_receipt=exact_pack.source_fact_registry_receipt.model_copy(
                    update={"registry_digest": "c" * 64}
                ),
                fresh_context_attestation=exact_pack.fresh_context_attestation,
                recorded_by="readiness_test",
                recorded_at=datetime.now(UTC),
            )
        )
        assert blocked.binding.status == "blocked"
    result = resolve_current_preparation_readiness(
        proxy,
        WORK_ITEM_ID,
        run=run,
        row=row_override,
    )

    assert result.status == "blocked"
    assert result.code == expected_code
