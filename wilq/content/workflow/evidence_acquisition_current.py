"""Current read projection and freshness policy for evidence acquisition."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal

from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.delivery_identity import (
    ContentDeliveryClassificationLookup,
    build_content_delivery_identity_current_projection,
)
from wilq.content.workflow.evidence_acquisition_contracts import (
    ClassificationLoader,
    EvidenceAcquisitionCurrentProjection,
    EvidenceAcquisitionRun,
    EvidenceAcquisitionRunBlocker,
    EvidenceAcquisitionStartCommand,
    EvidenceAcquisitionStore,
    IdentityLoader,
    OfficialGuidanceObservationReceipt,
    ServerClock,
    _request_digest,
)
from wilq.content.workflow.evidence_acquisition_snapshot import current_page_receipt_is_fresh
from wilq.content.workflow.official_guidance import official_guidance_receipt_is_fresh

if TYPE_CHECKING:
    from wilq.content.workflow.authoring_inventory_receipt import (
        ContentAuthoringInventoryReceipt,
    )


def _project_run(
    run: EvidenceAcquisitionRun,
    *,
    clock: ServerClock,
    store: EvidenceAcquisitionStore,
    catalog_loader: Callable[[], Any],
    identity_loader: IdentityLoader,
    classification_loader: ClassificationLoader,
) -> EvidenceAcquisitionCurrentProjection:
    assessed_at = clock()
    freshness: Literal["fresh", "stale", "not_applicable"] = "not_applicable"
    current_status = run.status
    current_blockers = run.blockers
    current_safe_next_step = run.safe_next_step
    if run.subject_kind == "identity_binding" and run.status == "ready_for_researcher":
        identity_blocker = _identity_current_projection_blocker(
            run,
            identity_loader=identity_loader,
            classification_loader=classification_loader,
            assessed_at=assessed_at,
        )
        if identity_blocker is not None:
            current_status = "blocked"
            current_blockers = (identity_blocker,)
            current_safe_next_step = identity_blocker.safe_next_step
    if run.subject_kind == "authoring_inventory_receipt" and run.status == "ready_for_researcher":
        authoring_blocker = _authoring_current_projection_blocker(
            run,
            store=store,
            catalog_loader=catalog_loader,
            assessed_at=assessed_at,
        )
        if authoring_blocker is not None:
            freshness = "stale"
            current_status = "blocked"
            current_blockers = (authoring_blocker,)
            current_safe_next_step = authoring_blocker.safe_next_step
    if current_status == "ready_for_researcher" and run.observation is not None:
        observation_is_fresh = (
            official_guidance_receipt_is_fresh(run.observation, now=assessed_at)
            if isinstance(run.observation, OfficialGuidanceObservationReceipt)
            else current_page_receipt_is_fresh(run.observation, now=assessed_at)
        )
        if observation_is_fresh:
            freshness = "fresh"
        else:
            freshness = "stale"
            current_status = "blocked"
            stale_blocker = EvidenceAcquisitionRunBlocker(
                code="current_page_snapshot_stale",
                reason=(
                    "The stored current-page observation is no longer fresh for "
                    "researcher use."
                ),
                evidence_ids=run.observation.evidence_ids,
                safe_next_step="Zwiększ attempt i wykonaj nowy exact current-page read.",
            )
            current_blockers = (stale_blocker,)
            current_safe_next_step = stale_blocker.safe_next_step
    return EvidenceAcquisitionCurrentProjection(
        recorded_run=run,
        run_id=run.run_id,
        run_digest=run.run_digest,
        request_digest=run.request_digest,
        attempt=run.attempt,
        recorded_status=run.status,
        assessed_at=assessed_at,
        freshness=freshness,
        current_status=current_status,
        current_blockers=current_blockers,
        current_safe_next_step=current_safe_next_step,
    )


def _identity_current_projection_blocker(
    run: EvidenceAcquisitionRun,
    *,
    identity_loader: IdentityLoader,
    classification_loader: ClassificationLoader,
    assessed_at: datetime,
) -> EvidenceAcquisitionRunBlocker | None:
    identity_id = run.identity_binding_id
    if not identity_id:
        return EvidenceAcquisitionRunBlocker(
            code="identity_classification_drift",
            reason="Ready identity acquisition has no exact binding identity.",
            evidence_ids=run.inventory_evidence_ids,
            safe_next_step="Odśwież exact S1/classification context.",
        )
    identity = identity_loader(identity_id)
    if identity is None:
        return EvidenceAcquisitionRunBlocker(
            code="identity_classification_drift",
            reason="The persisted identity binding is no longer available.",
            evidence_ids=run.inventory_evidence_ids,
            safe_next_step="Odśwież exact S1/classification context.",
        )
    classification = classification_loader(identity.current_work_item_id)
    lookup = ContentDeliveryClassificationLookup(
        row_status="missing" if classification is None else "exact",
        run=classification,
    )
    current = build_content_delivery_identity_current_projection(
        identity,
        lookup,
        assessed_at=assessed_at,
    )
    if current.current_blocker is not None:
        blocker = current.current_blocker
        return EvidenceAcquisitionRunBlocker(
            code=blocker.reason,
            reason="Current identity classification context is no longer exact.",
            evidence_ids=blocker.evidence_ids,
            safe_next_step=blocker.next_step,
        )
    if any(
        (
            run.identity_binding_digest != identity.binding_digest,
            run.current_work_item_id != identity.current_work_item_id,
            run.canonical_path != identity.canonical_path,
            run.public_url != identity.public_url,
            run.subject_public_url != identity.public_url,
            run.subject_canonical_path != identity.canonical_path,
            run.subject_evidence_ids != identity.inventory_evidence_ids,
            run.inventory_evidence_ids != identity.inventory_evidence_ids,
            run.classification_run_id != identity.classification_run_id,
            run.classification_run_digest != identity.classification_run_digest,
            run.classification_source_row_digest
            != identity.classification_source_row_digest,
        )
    ):
        return EvidenceAcquisitionRunBlocker(
            code="identity_classification_drift",
            reason="The acquisition run is not bound to the current identity context.",
            evidence_ids=identity.inventory_evidence_ids,
            safe_next_step="Odśwież exact S1/classification context.",
        )
    return None


def _authoring_current_projection_blocker(
    run: EvidenceAcquisitionRun,
    *,
    store: EvidenceAcquisitionStore,
    catalog_loader: Callable[[], Any],
    assessed_at: datetime,
) -> EvidenceAcquisitionRunBlocker | None:
    receipt_id = run.authoring_inventory_receipt_id
    if not receipt_id:
        return EvidenceAcquisitionRunBlocker(
            code="authoring_inventory_receipt_missing",
            reason="The authoring inventory receipt subject is missing from the run.",
            evidence_ids=run.subject_evidence_ids,
            safe_next_step="Zarejestruj exact current authoring inventory receipt.",
        )
    receipt = store.load_content_authoring_inventory_receipt(receipt_id)
    if receipt is None:
        return EvidenceAcquisitionRunBlocker(
            code="authoring_inventory_receipt_missing",
            reason="The persisted authoring inventory receipt is no longer available.",
            evidence_ids=run.subject_evidence_ids,
            safe_next_step="Zarejestruj exact current authoring inventory receipt.",
        )
    catalog = catalog_loader()
    catalog_item = _current_authoring_inventory_item(receipt, catalog=catalog)
    catalog_context_digest = _authoring_catalog_context_digest(
        catalog, catalog_item=catalog_item
    )
    if (
        catalog_item is None
        or run.authoring_catalog_context_digest is None
        or run.authoring_catalog_context_digest != catalog_context_digest
        or run.authoring_inventory_receipt_digest != receipt.receipt_digest
    ):
        return EvidenceAcquisitionRunBlocker(
            code="authoring_inventory_receipt_stale",
            reason="The authoring receipt no longer matches the current catalog snapshot.",
            evidence_ids=(receipt.evidence_id,),
            safe_next_step="Odśwież exact authoring inventory receipt przed researcherem.",
        )
    receipt_freshness: Literal["fresh", "stale"] = (
        "fresh"
        if _authoring_inventory_receipt_is_fresh(receipt, now=assessed_at)
        else "stale"
    )
    if receipt_freshness == "stale":
        return EvidenceAcquisitionRunBlocker(
            code="authoring_inventory_receipt_stale",
            reason="The authoring receipt is outside the current content freshness horizon.",
            evidence_ids=(receipt.evidence_id,),
            safe_next_step="Odśwież exact authoring inventory receipt przed researcherem.",
        )
    blocker = _authoring_observation_or_request_blocker(
        run,
        receipt=receipt,
        catalog_item=catalog_item,
        catalog_context_digest=catalog_context_digest,
        receipt_freshness=receipt_freshness,
    )
    if blocker is not None:
        return blocker
    return None


def _authoring_observation_or_request_blocker(
    run: EvidenceAcquisitionRun,
    *,
    receipt: Any,
    catalog_item: Any,
    catalog_context_digest: str,
    receipt_freshness: Literal["fresh", "stale"],
) -> EvidenceAcquisitionRunBlocker | None:
    if (
        run.subject_public_url != receipt.public_url
        or run.subject_canonical_path != receipt.canonical_path
        or run.subject_evidence_ids != (receipt.evidence_id,)
        or run.current_work_item_id != catalog_item.work_item_id
        or run.canonical_path != receipt.canonical_path
        or run.public_url != receipt.public_url
        or run.inventory_evidence_ids != (receipt.evidence_id,)
        or run.observation is None
        or run.observation.source_url != receipt.public_url
        or run.observation.canonical_path != receipt.canonical_path
        or set(run.observation.evidence_ids) == {receipt.evidence_id}
    ):
        return EvidenceAcquisitionRunBlocker(
            code="authoring_inventory_observation_lineage_mismatch",
            reason="The recorded authoring observation is not bound to the current receipt.",
            evidence_ids=(receipt.evidence_id,),
            safe_next_step="Wykonaj nowy exact material read dla bieżącego receipt.",
        )
    try:
        command = EvidenceAcquisitionStartCommand.model_validate(
            {
                "subject": {
                    "subject_kind": "authoring_inventory_receipt",
                    "authoring_inventory_receipt_id": receipt.receipt_id,
                },
                "research_question": run.research_question_safe,
                "attempt": run.attempt,
                "source_intent": run.source_intent,
            },
            strict=True,
        )
    except ValueError:
        return EvidenceAcquisitionRunBlocker(
            code="authoring_inventory_receipt_stale",
            reason="The recorded authoring request context is not valid for current use.",
            evidence_ids=(receipt.evidence_id,),
            safe_next_step="Utwórz nowy exact authoring acquisition attempt.",
        )
    expected_request_digest = _request_digest(
        command,
        question_safe=run.research_question_safe,
        identity=None,
        classification=None,
        receipt=receipt,
        catalog_context_digest=catalog_context_digest,
        receipt_freshness=receipt_freshness,
    )
    if expected_request_digest != run.request_digest:
        return EvidenceAcquisitionRunBlocker(
            code="authoring_inventory_receipt_stale",
            reason="The recorded authoring request context drifted from current evidence.",
            evidence_ids=(receipt.evidence_id,),
            safe_next_step="Utwórz nowy exact authoring acquisition attempt.",
        )
    return None


def _current_authoring_inventory_item(
    receipt: Any,
    *,
    catalog: Any,
) -> Any | None:
    from wilq.content.canonical.urls import content_normalized_path
    from wilq.content.workflow.authoring_inventory_receipt import (
        content_inventory_catalog_item_digest,
        content_inventory_catalog_snapshot_digest,
    )
    if receipt.catalog_snapshot_digest != content_inventory_catalog_snapshot_digest(catalog):
        return None
    matches = [
        item
        for item in catalog.items
        if item.catalog_id == receipt.catalog_id
        and item.work_item_id == receipt.current_work_item_id
        and item.url == receipt.public_url
        and content_normalized_path(item.path) == receipt.canonical_path
        and item.source_connector == "wordpress_ekologus"
        and item.evidence_id == receipt.evidence_id
        and item.collected_at == receipt.collected_at
        and content_inventory_catalog_item_digest(item) == receipt.catalog_item_digest
    ]
    return matches[0] if len(matches) == 1 else None


def _authoring_catalog_context_digest(catalog: Any, *, catalog_item: Any | None) -> str:
    from wilq.content.workflow.authoring_inventory_receipt import (
        content_inventory_catalog_item_digest,
        content_inventory_catalog_snapshot_digest,
    )

    return canonical_json_digest(
        {
            "catalog_snapshot_digest": content_inventory_catalog_snapshot_digest(catalog),
            "catalog_item_digest": (
                None
                if catalog_item is None
                else content_inventory_catalog_item_digest(catalog_item)
            ),
            "catalog_item_evidence_id": (
                None if catalog_item is None else catalog_item.evidence_id
            ),
        }
    )


def _authoring_inventory_receipt_is_fresh(
    receipt: ContentAuthoringInventoryReceipt, *, now: datetime
) -> bool:
    from wilq.briefing.content_diagnostics import CONTENT_STALE_AFTER_HOURS

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Authoring inventory freshness assessment requires an aware server time.")
    age = now.astimezone(UTC) - receipt.collected_at.astimezone(UTC)
    return timedelta(0) <= age <= timedelta(hours=CONTENT_STALE_AFTER_HOURS)
