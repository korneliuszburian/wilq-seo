"""Server-owned acquisition subjects and persistence contracts."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from wilq.content.workflow.decisions.production import ContentProductionClassificationProjection
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding
from wilq.content.workflow.evidence_acquisition_contracts import (
    ClassificationLoader,
    CurrentPageSnapshotReader,
    EvidenceAcquisitionAuthoringInventorySubject,
    EvidenceAcquisitionCurrentProjection,
    EvidenceAcquisitionIdentitySubject,
    EvidenceAcquisitionRun,
    EvidenceAcquisitionRunBlocker,
    EvidenceAcquisitionStartCommand,
    EvidenceAcquisitionStore,
    EvidenceAcquisitionSubject,
    EvidenceObservationReceipt,
    IdentityLoader,
    OfficialGuidanceObservationReceipt,
    ServerClock,
    _finalize_run,
    _question_digest,
    _request_digest,
)
from wilq.content.workflow.evidence_acquisition_snapshot import (
    CurrentPageSnapshotReadError,
)
from wilq.content.workflow.official_guidance import (
    OfficialGuidanceReadError,
    resolve_official_guidance_candidate,
)
from wilq.security.redaction import SECRET_VALUE_RE

_SECRET_FIELD_RE = re.compile(
    r"(?i)(?:token|secret|password|credential|api[_-]?key)\s*[:=]\s*\S+"
)
@dataclass(frozen=True, slots=True)
class EvidenceAcquisitionContext:
    """Private execution context passed behind the coordinator's small seam."""

    identity_loader: IdentityLoader
    classification_loader: ClassificationLoader
    store: EvidenceAcquisitionStore
    current_page_snapshot_reader: CurrentPageSnapshotReader | None
    official_guidance_snapshot_reader: Callable[..., OfficialGuidanceObservationReceipt] | None
    catalog_loader: Callable[[], Any]
    clock: ServerClock
    project_run: Callable[..., EvidenceAcquisitionCurrentProjection]
    current_authoring_inventory_item: Callable[..., Any | None]
    authoring_catalog_context_digest: Callable[..., str]
    authoring_inventory_receipt_is_fresh: Callable[..., bool]
    researcher_executor_available: bool = False


def _researcher_executor_status(
    available: bool,
) -> Literal["missing", "available"]:
    return "available" if available else "missing"


def start_acquisition(
    command: EvidenceAcquisitionStartCommand,
    *,
    context: EvidenceAcquisitionContext,
) -> EvidenceAcquisitionCurrentProjection:
    question_safe = sanitize_research_question(command.research_question)
    if command.subject.subject_kind == "authoring_inventory_receipt":
        return _start_authoring_inventory_receipt(
            command,
            question_safe=question_safe,
            context=context,
        )
    return _start_identity_acquisition(command, question_safe=question_safe, context=context)


def _start_identity_acquisition(
    command: EvidenceAcquisitionStartCommand,
    *,
    question_safe: str,
    context: EvidenceAcquisitionContext,
) -> EvidenceAcquisitionCurrentProjection:
    subject = command.subject
    if not isinstance(subject, EvidenceAcquisitionIdentitySubject):
        raise TypeError("Identity acquisition requires an identity binding subject.")
    identity_binding_id = subject.identity_binding_id
    identity = context.identity_loader(identity_binding_id)
    classification = (
        None
        if identity is None
        else context.classification_loader(identity.current_work_item_id)
    )
    request_digest = _request_digest(
        command,
        question_safe=question_safe,
        identity=identity,
        classification=classification,
    )
    existing = context.store.get_evidence_acquisition_run_by_request_digest(request_digest)
    if existing is not None:
        return _project_existing(existing, context)
    if identity is None:
        return _persist_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            blocker=EvidenceAcquisitionRunBlocker(
                code="identity_binding_missing",
                reason="Exact current S1 identity was not found.",
                safe_next_step="Zarejestruj exact current S1 identity.",
            ),
            context=context,
        )
    blocker = _exact_context_blocker(identity, classification)
    if blocker is not None:
        return _persist_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            identity=identity,
            classification=classification,
            blocker=blocker,
            context=context,
        )
    assert classification is not None
    if command.source_intent == "official_primary":
        return _start_official_primary(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            identity=identity,
            classification=classification,
            context=context,
        )
    return _start_exact_current_page(
        command,
        question_safe=question_safe,
        request_digest=request_digest,
        identity=identity,
        classification=classification,
        context=context,
    )


def _start_official_primary(
    command: EvidenceAcquisitionStartCommand,
    *,
    question_safe: str,
    request_digest: str,
    identity: ContentDeliveryIdentityBinding,
    classification: ContentProductionClassificationProjection,
    context: EvidenceAcquisitionContext,
) -> EvidenceAcquisitionCurrentProjection:
    selector = command.source_selector
    candidate = (
        None
        if selector is None
        else resolve_official_guidance_candidate(selector.candidate_id)
    )
    if selector is None:
        return _persist_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            identity=identity,
            classification=classification,
            blocker=EvidenceAcquisitionRunBlocker(
                code="official_guidance_selector_missing",
                reason="Official-primary acquisition requires a server-owned candidate selector.",
                evidence_ids=identity.inventory_evidence_ids,
                safe_next_step="Wybierz exact official-guidance candidate po ID.",
            ),
            context=context,
        )
    if candidate is None:
        return _persist_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            identity=identity,
            classification=classification,
            blocker=EvidenceAcquisitionRunBlocker(
                code="official_guidance_candidate_missing",
                reason="The requested official-guidance candidate is not registered.",
                evidence_ids=identity.inventory_evidence_ids,
                safe_next_step="Użyj zarejestrowanego official-guidance candidate ID.",
            ),
            context=context,
        )
    if candidate.canonical_path != identity.canonical_path:
        return _persist_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            identity=identity,
            classification=classification,
            blocker=EvidenceAcquisitionRunBlocker(
                code="official_guidance_candidate_path_mismatch",
                reason="Official-guidance candidate is not bound to the exact content path.",
                evidence_ids=identity.inventory_evidence_ids,
                safe_next_step="Wybierz candidate przypisany do exact canonical pathu.",
            ),
            context=context,
        )
    if context.official_guidance_snapshot_reader is None:
        return _persist_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            identity=identity,
            classification=classification,
            candidate=candidate,
            blocker=EvidenceAcquisitionRunBlocker(
                code="official_guidance_transport_unavailable",
                reason="No safe public-IP-pinned official-guidance transport is configured.",
                evidence_ids=identity.inventory_evidence_ids,
                safe_next_step=(
                    "Skonfiguruj kontrolowany reader official guidance albo pozostań "
                    "przy blockerze transportu."
                ),
            ),
            context=context,
        )
    try:
        observation = context.official_guidance_snapshot_reader(
            candidate_id=candidate.candidate_id,
            source_url=candidate.source_url,
            canonical_path=candidate.canonical_path,
        )
    except OfficialGuidanceReadError as exc:
        return _persist_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            identity=identity,
            classification=classification,
            candidate=candidate,
            vendor_read_status="blocked",
            blocker=EvidenceAcquisitionRunBlocker(
                code=exc.code,
                reason=str(exc),
                evidence_ids=identity.inventory_evidence_ids,
                safe_next_step=(
                    "Sprawdź kontrolowany exact official-guidance read i spróbuj "
                    "ponownie."
                ),
            ),
            context=context,
        )
    except Exception:
        return _persist_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            identity=identity,
            classification=classification,
            candidate=candidate,
            vendor_read_status="blocked",
            blocker=EvidenceAcquisitionRunBlocker(
                code="official_guidance_transport_unavailable",
                reason="Official-guidance transport did not complete safely.",
                evidence_ids=identity.inventory_evidence_ids,
                safe_next_step=(
                    "Sprawdź kontrolowany exact official-guidance read i spróbuj "
                    "ponownie."
                ),
            ),
            context=context,
        )
    if not isinstance(observation, OfficialGuidanceObservationReceipt):
        return _persist_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            identity=identity,
            classification=classification,
            candidate=candidate,
            vendor_read_status="blocked",
            blocker=EvidenceAcquisitionRunBlocker(
                code="official_guidance_lineage_mismatch",
                reason="Official-guidance reader returned the wrong observation type.",
                evidence_ids=identity.inventory_evidence_ids,
                safe_next_step="Użyj OfficialGuidanceObservationAdapter dla exact candidate read.",
            ),
            context=context,
        )
    if (
        observation.candidate_id != candidate.candidate_id
        or observation.candidate_digest != candidate.candidate_digest
        or observation.source_url != candidate.source_url
        or observation.canonical_path != candidate.canonical_path
        or not set(observation.evidence_ids).isdisjoint(identity.inventory_evidence_ids)
    ):
        return _persist_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            identity=identity,
            classification=classification,
            candidate=candidate,
            vendor_read_status="blocked",
            blocker=EvidenceAcquisitionRunBlocker(
                code="official_guidance_lineage_mismatch",
                reason="Official-guidance observation is not bound to the exact candidate.",
                evidence_ids=identity.inventory_evidence_ids,
                safe_next_step=(
                    "Wykonaj nowy exact official-guidance read bez reuse inventory "
                    "evidence."
                ),
            ),
            context=context,
        )
    return _persist(
        _build_ready(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            identity=identity,
            classification=classification,
            observation=observation,
            candidate=candidate,
            researcher_executor_available=context.researcher_executor_available,
        ),
        context,
    )


def _start_authoring_inventory_receipt(
    command: EvidenceAcquisitionStartCommand,
    *,
    question_safe: str,
    context: EvidenceAcquisitionContext,
) -> EvidenceAcquisitionCurrentProjection:
    subject = command.subject
    if not isinstance(subject, EvidenceAcquisitionAuthoringInventorySubject):
        raise TypeError("Observation acquisition requires an authoring receipt subject.")
    receipt = context.store.load_content_authoring_inventory_receipt(
        subject.authoring_inventory_receipt_id
    )
    if receipt is None:
        return _persist_subject_blocked(
            command,
            question_safe=question_safe,
            request_digest=_request_digest(
                command,
                question_safe=question_safe,
                identity=None,
                classification=None,
            ),
            blocker=EvidenceAcquisitionRunBlocker(
                code="authoring_inventory_receipt_missing",
                reason="Exact authoring inventory receipt was not found.",
                safe_next_step="Zarejestruj exact current authoring inventory receipt.",
            ),
            context=context,
        )
    catalog = context.catalog_loader()
    catalog_item = context.current_authoring_inventory_item(receipt, catalog=catalog)
    catalog_context_digest = context.authoring_catalog_context_digest(
        catalog, catalog_item=catalog_item
    )
    receipt_freshness: Literal["fresh", "stale"] = (
        "fresh"
        if context.authoring_inventory_receipt_is_fresh(receipt, now=context.clock())
        else "stale"
    )
    request_digest = _request_digest(
        command,
        question_safe=question_safe,
        identity=None,
        classification=None,
        receipt=receipt,
        catalog_context_digest=catalog_context_digest,
        receipt_freshness=receipt_freshness,
    )
    blocker = _authoring_start_blocker(
        command,
        receipt=receipt,
        catalog_item=catalog_item,
        receipt_freshness=receipt_freshness,
    )
    if blocker is not None:
        return _persist_subject_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            receipt=receipt,
            catalog_item=catalog_item,
            catalog_context_digest=catalog_context_digest,
            blocker=blocker,
            context=context,
        )
    existing = context.store.get_evidence_acquisition_run_by_request_digest(request_digest)
    if existing is not None:
        return _project_existing(existing, context)
    return _complete_authoring_snapshot(
        command,
        question_safe=question_safe,
        request_digest=request_digest,
        receipt=receipt,
        catalog_item=catalog_item,
        catalog_context_digest=catalog_context_digest,
        context=context,
    )


def _authoring_start_blocker(
    command: EvidenceAcquisitionStartCommand,
    *,
    receipt: Any,
    catalog_item: Any | None,
    receipt_freshness: Literal["fresh", "stale"],
) -> EvidenceAcquisitionRunBlocker | None:
    if catalog_item is None:
        return EvidenceAcquisitionRunBlocker(
            code="authoring_inventory_receipt_stale",
            reason="Authoring inventory receipt no longer matches the current catalog.",
            evidence_ids=(receipt.evidence_id,),
            safe_next_step="Odśwież exact authoring inventory receipt przed acquisition.",
        )
    if receipt_freshness == "stale":
        return EvidenceAcquisitionRunBlocker(
            code="authoring_inventory_receipt_stale",
            reason=(
                "Authoring inventory receipt is outside the current content "
                "freshness horizon."
            ),
            evidence_ids=(receipt.evidence_id,),
            safe_next_step="Odśwież exact authoring inventory receipt przed acquisition.",
        )
    if command.source_intent != "current_page":
        return EvidenceAcquisitionRunBlocker(
            code="researcher_executor_missing",
            reason="Authoring acquisition supports current_page intent only in this slice.",
            evidence_ids=(receipt.evidence_id,),
            safe_next_step=(
                "Użyj current_page albo dodaj osobny, zatwierdzony researcher adapter."
            ),
        )
    return None


def _complete_authoring_snapshot(
    command: EvidenceAcquisitionStartCommand,
    *,
    question_safe: str,
    request_digest: str,
    receipt: Any,
    catalog_item: Any,
    catalog_context_digest: str,
    context: EvidenceAcquisitionContext,
) -> EvidenceAcquisitionCurrentProjection:
    if context.current_page_snapshot_reader is None:
        return _persist_subject_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            receipt=receipt,
            catalog_item=catalog_item,
            catalog_context_digest=catalog_context_digest,
            blocker=EvidenceAcquisitionRunBlocker(
                code="current_page_snapshot_unavailable",
                reason="No exact current-page snapshot adapter is configured.",
                evidence_ids=(receipt.evidence_id,),
                safe_next_step="Configure a sanitized WordPress current-page read adapter.",
            ),
            context=context,
        )
    try:
        observation = context.current_page_snapshot_reader(
            source_url=receipt.public_url,
            canonical_path=receipt.canonical_path,
        )
    except CurrentPageSnapshotReadError as exc:
        return _persist_subject_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            receipt=receipt,
            catalog_item=catalog_item,
            catalog_context_digest=catalog_context_digest,
            vendor_read_status="blocked",
            blocker=EvidenceAcquisitionRunBlocker(
                code=exc.code,
                reason=str(exc),
                evidence_ids=(receipt.evidence_id,),
                safe_next_step="Sprawdź exact WordPress read receipt i spróbuj ponownie.",
            ),
            context=context,
        )
    if (
        observation.source_url != receipt.public_url
        or observation.canonical_path != receipt.canonical_path
        or set(observation.evidence_ids) == {receipt.evidence_id}
    ):
        return _persist_subject_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            receipt=receipt,
            catalog_item=catalog_item,
            catalog_context_digest=catalog_context_digest,
            vendor_read_status="blocked",
            blocker=EvidenceAcquisitionRunBlocker(
                code="authoring_inventory_observation_lineage_mismatch",
                reason="Current observation is not a new exact read for the inventory subject.",
                evidence_ids=(receipt.evidence_id,),
                safe_next_step="Wykonaj nowy exact material read bez reuse inventory evidence.",
            ),
            context=context,
        )
    return _persist(
        _build_subject_ready(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            receipt=receipt,
            catalog_item=catalog_item,
            catalog_context_digest=catalog_context_digest,
            observation=observation,
            researcher_executor_available=context.researcher_executor_available,
        ),
        context,
    )


def _start_exact_current_page(
    command: EvidenceAcquisitionStartCommand,
    *,
    question_safe: str,
    request_digest: str,
    identity: ContentDeliveryIdentityBinding,
    classification: ContentProductionClassificationProjection,
    context: EvidenceAcquisitionContext,
) -> EvidenceAcquisitionCurrentProjection:
    if command.source_intent != "current_page":
        return _persist_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            identity=identity,
            classification=classification,
            blocker=EvidenceAcquisitionRunBlocker(
                code="researcher_executor_missing",
                reason="The requested source intent has no researcher adapter in this slice.",
                evidence_ids=identity.inventory_evidence_ids,
                safe_next_step="Add a testable researcher adapter for this source intent.",
            ),
            context=context,
        )
    if context.current_page_snapshot_reader is None:
        return _persist_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            identity=identity,
            classification=classification,
            blocker=EvidenceAcquisitionRunBlocker(
                code="current_page_snapshot_unavailable",
                reason=(
                    "No exact current-page snapshot adapter is configured; this slice "
                    "does not perform a live vendor read."
                ),
                evidence_ids=identity.inventory_evidence_ids,
                safe_next_step="Configure a sanitized WordPress current-page read adapter.",
            ),
            context=context,
        )
    try:
        observation = context.current_page_snapshot_reader(
            source_url=identity.public_url,
            canonical_path=identity.canonical_path,
        )
    except CurrentPageSnapshotReadError as exc:
        return _persist_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            identity=identity,
            classification=classification,
            vendor_read_status="blocked",
            blocker=EvidenceAcquisitionRunBlocker(
                code=exc.code,
                reason=str(exc),
                evidence_ids=identity.inventory_evidence_ids,
                safe_next_step="Sprawdź exact WordPress read receipt i spróbuj ponownie.",
            ),
            context=context,
        )
    lineage_blocker = _observation_lineage_blocker(observation, identity)
    if lineage_blocker is not None:
        return _persist_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            identity=identity,
            classification=classification,
            vendor_read_status="blocked",
            blocker=lineage_blocker,
            context=context,
        )
    return _persist(
        _build_ready(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            identity=identity,
            classification=classification,
            observation=observation,
            researcher_executor_available=context.researcher_executor_available,
        ),
        context,
    )


def _project_existing(
    run: EvidenceAcquisitionRun,
    context: EvidenceAcquisitionContext,
) -> EvidenceAcquisitionCurrentProjection:
    return context.project_run(
        run,
        clock=context.clock,
        store=context.store,
        catalog_loader=context.catalog_loader,
        identity_loader=context.identity_loader,
        classification_loader=context.classification_loader,
    )


def _persist_blocked(
    command: EvidenceAcquisitionStartCommand,
    *,
    question_safe: str,
    request_digest: str,
    blocker: EvidenceAcquisitionRunBlocker,
    context: EvidenceAcquisitionContext,
    identity: ContentDeliveryIdentityBinding | None = None,
    classification: ContentProductionClassificationProjection | None = None,
    candidate: Any | None = None,
    vendor_read_status: Literal["not_attempted", "blocked"] = "not_attempted",
) -> EvidenceAcquisitionCurrentProjection:
    return _persist(
        _build_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            identity=identity,
            classification=classification,
            candidate=candidate,
            vendor_read_status=vendor_read_status,
            blocker=blocker,
        ),
        context,
    )


def _persist_subject_blocked(
    command: EvidenceAcquisitionStartCommand,
    *,
    question_safe: str,
    request_digest: str,
    blocker: EvidenceAcquisitionRunBlocker,
    context: EvidenceAcquisitionContext,
    receipt: Any | None = None,
    catalog_item: Any | None = None,
    catalog_context_digest: str | None = None,
    vendor_read_status: Literal["not_attempted", "blocked"] = "not_attempted",
) -> EvidenceAcquisitionCurrentProjection:
    return _persist(
        _build_blocked(
            command,
            question_safe=question_safe,
            request_digest=request_digest,
            vendor_read_status=vendor_read_status,
            blocker=blocker,
            receipt=receipt,
            catalog_item=catalog_item,
            catalog_context_digest=catalog_context_digest,
        ),
        context,
    )


def read_acquisition(
    run_id: str,
    *,
    context: EvidenceAcquisitionContext,
) -> EvidenceAcquisitionCurrentProjection | None:
    run = context.store.get_evidence_acquisition_run(run_id)
    return None if run is None else _project_existing(run, context)


def _persist(
    run: EvidenceAcquisitionRun,
    context: EvidenceAcquisitionContext,
) -> EvidenceAcquisitionCurrentProjection:
    return context.project_run(
        context.store.save_evidence_acquisition_run(run),
        clock=context.clock,
        store=context.store,
        catalog_loader=context.catalog_loader,
        identity_loader=context.identity_loader,
        classification_loader=context.classification_loader,
    )


def _build_blocked(
    command: EvidenceAcquisitionStartCommand,
    *,
    question_safe: str,
    request_digest: str,
    blocker: EvidenceAcquisitionRunBlocker,
    identity: ContentDeliveryIdentityBinding | None = None,
    classification: ContentProductionClassificationProjection | None = None,
    candidate: Any | None = None,
    vendor_read_status: Literal["not_attempted", "blocked"] = "not_attempted",
    receipt: Any | None = None,
    catalog_item: Any | None = None,
    catalog_context_digest: str | None = None,
) -> EvidenceAcquisitionRun:
    subject_kind = command.subject.subject_kind
    receipt_id = (
        receipt.receipt_id
        if receipt is not None
        else (
            _authoring_receipt_subject_id(command.subject)
            if subject_kind == "authoring_inventory_receipt"
            else None
        )
    )
    payload: dict[str, Any] = {
        "response_type": "content_evidence_acquisition_run",
        "contract_version": "content_evidence_acquisition_run_v2",
        "run_id": "pending",
        "run_digest": "0" * 64,
        "request_digest": request_digest,
        "attempt": command.attempt,
        "status": "blocked",
        "run_status": "proposal_only",
        "subject_kind": subject_kind,
        "identity_binding_id": (
            _identity_subject_id(command.subject)
            if subject_kind == "identity_binding"
            else None
        ),
        "identity_binding_digest": None if identity is None else identity.binding_digest,
        "authoring_inventory_receipt_id": receipt_id,
        "authoring_inventory_receipt_digest": (
            None if receipt is None else receipt.receipt_digest
        ),
        "authoring_catalog_context_digest": catalog_context_digest,
        "subject_public_url": None if receipt is None else receipt.public_url,
        "subject_canonical_path": None if receipt is None else receipt.canonical_path,
        "subject_evidence_ids": () if receipt is None else (receipt.evidence_id,),
        "production_authority": False,
        "disposition_status": "unknown",
        "source_authority_status": "unknown",
        "generation_allowed": False,
        "current_work_item_id": None if identity is None else identity.current_work_item_id,
        "canonical_path": None if identity is None else identity.canonical_path,
        "public_url": None if identity is None else identity.public_url,
        "classification_run_id": None if classification is None else classification.run_id,
        "classification_run_digest": (
            None if classification is None else classification.run_digest
        ),
        "classification_source_row_digest": (
            None if classification is None else classification.row.source_packet_row_digest
        ),
        "official_guidance_candidate_id": (
            candidate.candidate_id
            if candidate is not None
            else (
                command.source_selector.candidate_id
                if command.source_selector is not None
                else None
            )
        ),
        "official_guidance_candidate_digest": (
            None if candidate is None else candidate.candidate_digest
        ),
        "inventory_evidence_ids": () if identity is None else identity.inventory_evidence_ids,
        "research_question_safe": question_safe,
        "question_digest": _question_digest(question_safe),
        "source_intent": command.source_intent,
        "observation": None,
        "proposed_facts": (),
        "vendor_read_status": vendor_read_status,
        "researcher_executor_status": "missing",
        "blockers": (blocker,),
        "safe_next_step": blocker.safe_next_step,
    }
    return _finalize_run(payload)


def _build_ready(
    command: EvidenceAcquisitionStartCommand,
    *,
    question_safe: str,
    request_digest: str,
    identity: ContentDeliveryIdentityBinding,
    classification: ContentProductionClassificationProjection,
    observation: EvidenceObservationReceipt | OfficialGuidanceObservationReceipt,
    candidate: Any | None = None,
    researcher_executor_available: bool = False,
) -> EvidenceAcquisitionRun:
    payload: dict[str, Any] = {
        "response_type": "content_evidence_acquisition_run",
        "contract_version": "content_evidence_acquisition_run_v2",
        "run_id": "pending",
        "run_digest": "0" * 64,
        "request_digest": request_digest,
        "attempt": command.attempt,
        "status": "ready_for_researcher",
        "run_status": "proposal_only",
        "subject_kind": "identity_binding",
        "identity_binding_id": identity.binding_id,
        "identity_binding_digest": identity.binding_digest,
        "current_work_item_id": identity.current_work_item_id,
        "canonical_path": identity.canonical_path,
        "public_url": identity.public_url,
        "classification_run_id": classification.run_id,
        "classification_run_digest": classification.run_digest,
        "classification_source_row_digest": classification.row.source_packet_row_digest,
        "official_guidance_candidate_id": (
            None if candidate is None else candidate.candidate_id
        ),
        "official_guidance_candidate_digest": (
            None if candidate is None else candidate.candidate_digest
        ),
        "inventory_evidence_ids": identity.inventory_evidence_ids,
        "authoring_inventory_receipt_id": None,
        "authoring_inventory_receipt_digest": None,
        "subject_public_url": identity.public_url,
        "subject_canonical_path": identity.canonical_path,
        "subject_evidence_ids": identity.inventory_evidence_ids,
        "production_authority": False,
        "disposition_status": "unknown",
        "source_authority_status": "unknown",
        "generation_allowed": False,
        "research_question_safe": question_safe,
        "question_digest": _question_digest(question_safe),
        "source_intent": command.source_intent,
        "observation": observation,
        "proposed_facts": (),
        "vendor_read_status": "completed",
        "researcher_executor_status": _researcher_executor_status(
            researcher_executor_available
        ),
        "blockers": (),
        "safe_next_step": "Przekaż exact observation do osobnego researchera.",
    }
    return _finalize_run(payload)


def _build_subject_ready(
    command: EvidenceAcquisitionStartCommand,
    *,
    question_safe: str,
    request_digest: str,
    receipt: Any,
    catalog_item: Any,
    catalog_context_digest: str,
    observation: EvidenceObservationReceipt,
    researcher_executor_available: bool = False,
) -> EvidenceAcquisitionRun:
    payload: dict[str, Any] = {
        "response_type": "content_evidence_acquisition_run",
        "contract_version": "content_evidence_acquisition_run_v2",
        "run_id": "pending",
        "run_digest": "0" * 64,
        "request_digest": request_digest,
        "attempt": command.attempt,
        "status": "ready_for_researcher",
        "run_status": "proposal_only",
        "subject_kind": "authoring_inventory_receipt",
        "identity_binding_id": None,
        "identity_binding_digest": None,
        "authoring_inventory_receipt_id": receipt.receipt_id,
        "authoring_inventory_receipt_digest": receipt.receipt_digest,
        "authoring_catalog_context_digest": catalog_context_digest,
        "subject_public_url": receipt.public_url,
        "subject_canonical_path": receipt.canonical_path,
        "subject_evidence_ids": (receipt.evidence_id,),
        "current_work_item_id": catalog_item.work_item_id,
        "canonical_path": receipt.canonical_path,
        "public_url": receipt.public_url,
        "classification_run_id": None,
        "classification_run_digest": None,
        "classification_source_row_digest": None,
        "inventory_evidence_ids": (receipt.evidence_id,),
        "production_authority": False,
        "disposition_status": "unknown",
        "source_authority_status": "unknown",
        "generation_allowed": False,
        "research_question_safe": question_safe,
        "question_digest": _question_digest(question_safe),
        "source_intent": command.source_intent,
        "observation": observation,
        "proposed_facts": (),
        "vendor_read_status": "completed",
        "researcher_executor_status": _researcher_executor_status(
            researcher_executor_available
        ),
        "blockers": (),
        "safe_next_step": "Przekaż exact observation do osobnego researchera.",
    }
    return _finalize_run(payload)


def _exact_context_blocker(
    identity: ContentDeliveryIdentityBinding,
    classification: ContentProductionClassificationProjection | None,
) -> EvidenceAcquisitionRunBlocker | None:
    if identity.status != "exact_current":
        return EvidenceAcquisitionRunBlocker(
            code="identity_binding_not_exact_current",
            reason="Research acquisition requires exact current S1 identity.",
            evidence_ids=identity.inventory_evidence_ids,
            safe_next_step="Usuń blocker identity i spróbuj ponownie.",
        )
    if classification is None:
        return EvidenceAcquisitionRunBlocker(
            code="classification_missing",
            reason="Research acquisition requires current classification.",
            evidence_ids=identity.inventory_evidence_ids,
            safe_next_step="Uzyskaj current classification dla identity.",
        )
    if classification.freshness.state != "fresh" or classification.freshness.requires_refresh:
        return EvidenceAcquisitionRunBlocker(
            code="classification_stale",
            reason="Research acquisition requires fresh current classification.",
            evidence_ids=identity.inventory_evidence_ids,
            safe_next_step="Odśwież bieżącą klasyfikację przed acquisition.",
        )
    if (
        classification.run_id != identity.classification_run_id
        or classification.run_digest != identity.classification_run_digest
        or classification.row.current_work_item_id != identity.current_work_item_id
        or classification.row.canonical_path != identity.canonical_path
        or classification.row.public_url != identity.public_url
        or classification.row.source_packet_row_digest
        != identity.classification_source_row_digest
    ):
        return EvidenceAcquisitionRunBlocker(
            code="identity_classification_drift",
            reason="Identity and classification no longer describe the same exact row.",
            evidence_ids=identity.inventory_evidence_ids,
            safe_next_step="Odśwież exact S1/classification context.",
        )
    return None


def _observation_lineage_blocker(
    observation: EvidenceObservationReceipt,
    identity: ContentDeliveryIdentityBinding,
) -> EvidenceAcquisitionRunBlocker | None:
    if (
        observation.source_url != identity.public_url
        or observation.canonical_path != identity.canonical_path
        or not set(observation.evidence_ids).isdisjoint(identity.inventory_evidence_ids)
    ):
        return EvidenceAcquisitionRunBlocker(
            code="current_page_snapshot_lineage_mismatch",
            reason=(
                "Current-page receipt is not bound to the exact identity or is reusing "
                "inventory evidence."
            ),
            evidence_ids=identity.inventory_evidence_ids,
            safe_next_step="Uzyskaj nowy, exact WordPress read receipt dla bieżącej strony.",
        )
    return None


def _identity_subject_id(subject: EvidenceAcquisitionSubject) -> str | None:
    return (
        subject.identity_binding_id
        if isinstance(subject, EvidenceAcquisitionIdentitySubject)
        else None
    )


def _authoring_receipt_subject_id(subject: EvidenceAcquisitionSubject) -> str | None:
    return (
        subject.authoring_inventory_receipt_id
        if isinstance(subject, EvidenceAcquisitionAuthoringInventorySubject)
        else None
    )


def sanitize_research_question(value: str) -> str:
    normalized = " ".join(value.strip().split())
    normalized = _SECRET_FIELD_RE.sub("[redacted]", normalized)
    normalized = SECRET_VALUE_RE.sub("[redacted]", normalized)
    return normalized[:1000]
