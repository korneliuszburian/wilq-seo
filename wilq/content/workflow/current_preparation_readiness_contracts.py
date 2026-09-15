"""Typed read-only current-preparation readiness contracts."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.workflow.decisions.production import ContentProductionClassificationRun
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding
from wilq.content.workflow.source_pack_binding import ContentSourcePackBinding


class CurrentPreparationReadinessStore(Protocol):
    def load_latest_production_classification(
        self,
    ) -> ContentProductionClassificationRun | None: ...

    def load_content_delivery_identity(
        self, binding_id: str
    ) -> ContentDeliveryIdentityBinding | None: ...

    def list_content_source_pack_bindings(
        self, *, current_work_item_id: str | None = None
    ) -> list[ContentSourcePackBinding]: ...


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContentCurrentPreparationReadinessBlocked(_FrozenModel):
    status: Literal["blocked"]
    work_item_id: str = Field(min_length=1)
    code: str = Field(min_length=1)
    reason_pl: str = Field(min_length=1)
    safe_next_step_pl: str = Field(min_length=1)
    classification_run_id: str | None = None
    classification_run_digest: str | None = None
    decision_set_digest: str | None = None
    source_packet_row_digest: str | None = None
    identity_binding_id: str | None = None
    identity_binding_digest: str | None = None
    source_pack_binding_id: str | None = None
    source_pack_binding_digest: str | None = None


class ContentCurrentPreparationReadyForRefreshAuthorization(_FrozenModel):
    status: Literal["ready_for_refresh_authorization"]
    work_item_id: str = Field(min_length=1)
    classification_run_id: str = Field(min_length=1)
    classification_run_digest: str = Field(min_length=1)
    decision_set_digest: str = Field(min_length=1)
    source_packet_row_digest: str = Field(min_length=1)
    identity_binding_id: str = Field(min_length=1)
    identity_binding_digest: str = Field(min_length=1)
    source_pack_binding_id: str = Field(min_length=1)
    source_pack_binding_digest: str = Field(min_length=1)
    reason_pl: str = (
        "Exact current identity i source-pack są gotowe do autoryzacji refresh; "
        "klasyfikacja pozostaje immutable blocked."
    )
    safe_next_step_pl: str = (
        "Otwórz przygotowanie refresh i zapisz autoryzację dla bieżącej strony."
    )


ContentCurrentPreparationReadiness = (
    ContentCurrentPreparationReadyForRefreshAuthorization
    | ContentCurrentPreparationReadinessBlocked
)
ContentCurrentPreparationReadinessBlocker = ContentCurrentPreparationReadinessBlocked
ContentCurrentPreparationReady = ContentCurrentPreparationReadyForRefreshAuthorization


__all__ = [
    "ContentCurrentPreparationReadiness",
    "ContentCurrentPreparationReadinessBlocked",
    "ContentCurrentPreparationReadinessBlocker",
    "ContentCurrentPreparationReady",
    "ContentCurrentPreparationReadyForRefreshAuthorization",
    "CurrentPreparationReadinessStore",
]
