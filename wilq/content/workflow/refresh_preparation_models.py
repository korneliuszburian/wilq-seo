"""Internal state shapes behind the classified-refresh authority interface."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.content_kind_receipt import (
    ContentKindReceipt,
    ContentKindReceiptRecordResult,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.inventory_binding import ContentKindInventoryBinding
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationRow,
    ContentProductionClassificationRun,
)
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationAuthorization,
    ContentRefreshPreparationAuthorizationRecordResult,
    ContentRefreshPreparationBinding,
    ContentRefreshPreparationBlocker,
    ContentRefreshPreparationClassificationBinding,
    ContentRefreshPreparationServiceCandidate,
)

RefreshPreparationSnapshotLoader = Callable[
    [str, str | None], ContentWorkItemWorkflowSnapshotResponse
]
ContentKindInventoryLoader = Callable[[str], ContentKindInventoryBinding | None]


class RefreshPreparationStore(Protocol):
    def load_latest_production_classification(
        self,
    ) -> ContentProductionClassificationRun | None: ...

    def record_refresh_preparation_authorization(
        self,
        authorization: ContentRefreshPreparationAuthorization,
    ) -> ContentRefreshPreparationAuthorizationRecordResult: ...

    def load_refresh_preparation_authorization(
        self,
        authorization_id: str,
    ) -> ContentRefreshPreparationAuthorization | None: ...

    def find_refresh_preparation_authorization(
        self,
        *,
        work_item_id: str,
        classification_run_digest: str,
        decision_set_digest: str,
        source_packet_row_digest: str,
        canonical_path: str,
        public_url: str,
        planning_input_digest: str,
        service_card_id: str | None,
        content_kind: str = "service",
    ) -> ContentRefreshPreparationAuthorization | None: ...

    def record_content_kind_receipt(
        self,
        receipt: ContentKindReceipt,
    ) -> ContentKindReceiptRecordResult: ...

    def load_content_kind_receipt(self, receipt_id: str) -> ContentKindReceipt | None: ...


@dataclass(frozen=True, slots=True)
class RefreshPreparationUnclassified:
    work_item_id: str


@dataclass(frozen=True, slots=True)
class RefreshPreparationRuntimeBlocked:
    work_item_id: str
    blocker: ContentRefreshPreparationBlocker


@dataclass(frozen=True, slots=True)
class RefreshPreparationRuntimeAuthorized:
    work_item_id: str
    snapshot: ContentWorkItemWorkflowSnapshotResponse
    planning_input: ContentPlanningInput
    classification: ContentRefreshPreparationClassificationBinding
    service_candidate: ContentRefreshPreparationServiceCandidate | None
    authorization: ContentRefreshPreparationAuthorization

    @property
    def binding(self) -> ContentRefreshPreparationBinding:
        return self.authorization.binding


RefreshPreparationRuntimeResolution = (
    RefreshPreparationUnclassified
    | RefreshPreparationRuntimeBlocked
    | RefreshPreparationRuntimeAuthorized
)


@dataclass(frozen=True, slots=True)
class RefreshClassificationContext:
    run: ContentProductionClassificationRun
    row: ContentProductionClassificationRow
    binding: ContentRefreshPreparationClassificationBinding


@dataclass(frozen=True, slots=True)
class RefreshPreparationRebuilt:
    snapshot: ContentWorkItemWorkflowSnapshotResponse
    planning_input: ContentPlanningInput
    content_kind: Literal["service", "editorial"]
    service_candidate: ContentRefreshPreparationServiceCandidate | None
    content_kind_receipt: ContentKindReceipt | None
    informational_blockers: list[ContentRefreshPreparationBlocker]


__all__ = [
    "RefreshClassificationContext",
    "ContentKindInventoryLoader",
    "RefreshPreparationRebuilt",
    "RefreshPreparationRuntimeAuthorized",
    "RefreshPreparationRuntimeBlocked",
    "RefreshPreparationRuntimeResolution",
    "RefreshPreparationSnapshotLoader",
    "RefreshPreparationStore",
    "RefreshPreparationUnclassified",
]
