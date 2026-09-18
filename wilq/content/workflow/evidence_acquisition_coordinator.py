"""Deep, server-owned foundation for exact-URL evidence acquisition."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from wilq.content.workflow.evidence_acquisition_contracts import (
    ClassificationLoader,
    CurrentPageSnapshotReader,
    EvidenceAcquisitionAuthoringInventorySubject,
    EvidenceAcquisitionCurrentProjection,
    EvidenceAcquisitionIdentitySubject,
    EvidenceAcquisitionRun,
    EvidenceAcquisitionStartCommand,
    EvidenceAcquisitionStore,
    EvidenceAcquisitionSubject,
    IdentityLoader,
    ServerClock,
    _run_digest,  # noqa: F401 - retained for existing direct test seam
)
from wilq.content.workflow.evidence_acquisition_current import (
    _authoring_catalog_context_digest,
    _authoring_inventory_receipt_is_fresh,
    _current_authoring_inventory_item,
    _project_run,
)
from wilq.content.workflow.evidence_acquisition_snapshot import (
    WordPressCurrentPageSnapshotAdapter,
)
from wilq.content.workflow.evidence_acquisition_subjects import (
    EvidenceAcquisitionContext,
    read_acquisition,
    sanitize_research_question,
    start_acquisition,
)


class EvidenceAcquisitionCoordinator:
    """Small start/read seam over the subject and current-read modules."""

    def __init__(
        self,
        *,
        identity_loader: IdentityLoader,
        classification_loader: ClassificationLoader,
        store: EvidenceAcquisitionStore,
        current_page_snapshot_reader: CurrentPageSnapshotReader | None = None,
        catalog_loader: Callable[[], Any] | None = None,
        clock: ServerClock | None = None,
    ) -> None:
        self._identity_loader = identity_loader
        self._classification_loader = classification_loader
        self._store = store
        self._context = EvidenceAcquisitionContext(
            identity_loader=identity_loader,
            classification_loader=classification_loader,
            store=store,
            current_page_snapshot_reader=current_page_snapshot_reader,
            catalog_loader=catalog_loader or _default_inventory_catalog,
            clock=clock or (lambda: datetime.now(UTC)),
            project_run=_project_run,
            current_authoring_inventory_item=_current_authoring_inventory_item,
            authoring_catalog_context_digest=_authoring_catalog_context_digest,
            authoring_inventory_receipt_is_fresh=_authoring_inventory_receipt_is_fresh,
        )

    def start(
        self, command: EvidenceAcquisitionStartCommand
    ) -> EvidenceAcquisitionCurrentProjection:
        return start_acquisition(command, context=self._context)

    def read(self, run_id: str) -> EvidenceAcquisitionCurrentProjection | None:
        return read_acquisition(run_id, context=self._context)
def _default_inventory_catalog() -> Any:
    from wilq.content.workflow.workspace.catalog import build_content_inventory_catalog_cached

    return build_content_inventory_catalog_cached()

def build_default_evidence_acquisition_coordinator() -> EvidenceAcquisitionCoordinator:
    from wilq.content.workflow.store.store import content_workflow_store

    store = content_workflow_store()
    return EvidenceAcquisitionCoordinator(
        identity_loader=store.load_content_delivery_identity,
        classification_loader=store.load_production_classification_for_work_item,
        store=store,
        current_page_snapshot_reader=WordPressCurrentPageSnapshotAdapter().read,
    )


__all__ = [
    "EvidenceAcquisitionAuthoringInventorySubject",
    "EvidenceAcquisitionCoordinator",
    "EvidenceAcquisitionCurrentProjection",
    "EvidenceAcquisitionIdentitySubject",
    "EvidenceAcquisitionRun",
    "EvidenceAcquisitionSubject",
    "EvidenceAcquisitionStartCommand",
    "build_default_evidence_acquisition_coordinator",
    "sanitize_research_question",
]
