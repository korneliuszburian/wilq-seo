"""Typed current-acceptance run and wave contracts."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.canonical.urls import content_normalized_path
from wilq.content.knowledge.cards import ContentKnowledgeCard
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.workflow.current_inventory_reconciliation import (
    CurrentInventoryScopeResponse,
)
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.workspace.catalog import ContentInventoryCatalogResponse
from wilq.schemas import ContentFreshnessAssessment

CurrentAcceptanceDecision = Literal["keep", "refresh", "blocked", "excluded"]
CurrentPageMaterialStatus = Literal[
    "reviewed_material_current",
    "observed_material_current",
]
_HEX64 = r"^[0-9a-f]{64}$"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CurrentAcceptanceBlocked(ValueError):
    """A pinned inventory or source snapshot cannot safely seed a wave."""

    def __init__(self, code: str, owner: str, safe_next_step: str) -> None:
        self.code = code
        self.owner = owner
        self.safe_next_step = safe_next_step
        super().__init__(code)


class CurrentAcceptanceRow(_FrozenModel):
    canonical_path: str = Field(min_length=1, max_length=2048)
    public_url: str = Field(min_length=1, max_length=2048)
    scope_disposition: Literal["eligible", "excluded", "blocked"]
    decision: CurrentAcceptanceDecision
    current_work_item_id: str | None = Field(default=None, max_length=240)
    page_material_status: CurrentPageMaterialStatus | None = None
    identity_id: str | None = Field(default=None, max_length=240)
    identity_digest: str | None = Field(default=None, pattern=_HEX64)
    page_evidence_digest: str | None = Field(default=None, pattern=_HEX64)
    observation_id: str | None = Field(default=None, max_length=240)
    observation_digest: str | None = Field(default=None, pattern=_HEX64)
    semantic_row_digest: str | None = Field(default=None, pattern=_HEX64)
    service_card_id: str | None = Field(default=None, max_length=240)
    source_fact_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    reason_code: str | None = Field(default=None, max_length=160)
    blocker_code: str | None = Field(default=None, max_length=160)
    blocker_owner: str | None = Field(default=None, max_length=160)
    safe_next_step: str = Field(min_length=1, max_length=600)
    generation_allowed: Literal[False] = False

    @model_validator(mode="after")
    def require_exact_decision_shape(self) -> Self:
        if self.canonical_path != content_normalized_path(self.public_url):
            raise ValueError("Current acceptance row URL and path do not match.")
        if self.evidence_ids != tuple(sorted(set(self.evidence_ids))):
            raise ValueError("Current acceptance evidence IDs must be sorted and unique.")
        if self.source_fact_ids != tuple(sorted(set(self.source_fact_ids))):
            raise ValueError("Current acceptance source fact IDs must be sorted and unique.")
        if self.decision == "excluded":
            if (
                self.scope_disposition != "excluded"
                or self.reason_code is None
                or self.current_work_item_id is not None
                or self.identity_id is not None
                or self.observation_id is not None
                or self.blocker_code is not None
            ):
                raise ValueError("Excluded current acceptance rows need one exclusion reason.")
            return self
        if self.scope_disposition == "excluded" or self.reason_code is not None:
            raise ValueError("Eligible or blocked current acceptance rows cannot be excluded.")
        if self.decision == "blocked":
            if not self.blocker_code or not self.blocker_owner:
                raise ValueError("Blocked current acceptance rows need one typed blocker.")
            return self
        if (
            self.scope_disposition != "eligible"
            or not self.current_work_item_id
            or self.page_material_status is None
            or not self.identity_id
            or not self.identity_digest
            or not self.page_evidence_digest
            or not self.observation_id
            or not self.observation_digest
            or not self.semantic_row_digest
            or not self.source_fact_ids
            or not self.evidence_ids
            or self.blocker_code is not None
            or self.blocker_owner is not None
        ):
            raise ValueError("Positive current acceptance requires exact page and source lineage.")
        if self.decision == "keep" and self.page_material_status != "reviewed_material_current":
            raise ValueError("KEEP requires an approved review of the exact current material.")
        if self.decision == "refresh" and self.page_material_status != "observed_material_current":
            raise ValueError("REFRESH requires an exact automatic current-material observation.")
        return self


class CurrentAcceptanceWaveCounts(_FrozenModel):
    rows: int = Field(ge=0)
    scope_eligible: int = Field(ge=0)
    scope_excluded: int = Field(ge=0)
    scope_blocked: int = Field(ge=0)
    keep: int = Field(ge=0)
    refresh: int = Field(ge=0)
    eligible_blocked: int = Field(ge=0)

    @model_validator(mode="after")
    def cover_all_rows(self) -> Self:
        if self.rows != self.scope_eligible + self.scope_excluded + self.scope_blocked:
            raise ValueError("Current acceptance counts do not cover the inventory scope.")
        if self.scope_eligible != self.keep + self.refresh + self.eligible_blocked:
            raise ValueError("Current acceptance decisions do not cover eligible URLs.")
        return self


class CurrentAcceptanceWave(_FrozenModel):
    schema_version: Literal["wilq_current_acceptance_wave_v1"] = (
        "wilq_current_acceptance_wave_v1"
    )
    wave_id: str = Field(min_length=1, max_length=240)
    wave_digest: str = Field(pattern=_HEX64)
    run_id: str = Field(min_length=1, max_length=240)
    source_snapshot_digest: str = Field(pattern=_HEX64)
    inventory_evidence_ids: tuple[str, ...] = Field(min_length=1)
    started_at: datetime
    completed_at: datetime
    counts: CurrentAcceptanceWaveCounts
    rows: tuple[CurrentAcceptanceRow, ...]
    generation_allowed: Literal[False] = False

    @model_validator(mode="after")
    def require_self_authenticating_complete_wave(self) -> Self:
        if (
            self.started_at.tzinfo is None
            or self.started_at.utcoffset() is None
            or self.completed_at.tzinfo is None
            or self.completed_at.utcoffset() is None
        ):
            raise ValueError("Current acceptance run times must be timezone-aware.")
        paths = tuple(row.canonical_path for row in self.rows)
        if paths != tuple(sorted(paths)) or len(paths) != len(set(paths)):
            raise ValueError("Current acceptance rows must cover unique canonical paths.")
        if self.counts.rows != len(self.rows):
            raise ValueError("Current acceptance row count does not match its rows.")
        if self.inventory_evidence_ids != tuple(sorted(set(self.inventory_evidence_ids))):
            raise ValueError("Current acceptance inventory evidence must be sorted and unique.")
        if self.counts != current_acceptance_wave_counts(self.rows):
            raise ValueError("Current acceptance counts do not match row outcomes.")
        expected_digest = current_acceptance_wave_digest(self)
        if self.wave_digest != expected_digest or self.wave_id != (
            f"content_current_acceptance_wave_{expected_digest[:24]}"
        ):
            raise ValueError("Current acceptance wave identity/digest does not match.")
        return self


class CurrentAcceptanceAttempt(_FrozenModel):
    run_id: str = Field(min_length=1, max_length=240)
    request_id: str = Field(min_length=36, max_length=36, pattern=r"^[0-9a-f-]{36}$")
    input_digest: str = Field(pattern=_HEX64)
    source_snapshot_digest: str = Field(pattern=_HEX64)
    inventory_evidence_ids: tuple[str, ...] = Field(min_length=1)
    wordpress_evidence_ids: tuple[str, ...] = Field(min_length=1)
    scope_row_count: int = Field(ge=0)
    scope_row_digest: str = Field(pattern=_HEX64)
    status: Literal["queued", "running", "complete", "failed"]
    created_at: datetime
    updated_at: datetime
    wave_id: str | None = Field(default=None, max_length=240)
    wave_digest: str | None = Field(default=None, pattern=_HEX64)
    blocker_code: str | None = Field(default=None, max_length=160)
    blocker_owner: str | None = Field(default=None, max_length=160)
    safe_next_step: str | None = Field(default=None, max_length=600)

    @model_validator(mode="after")
    def require_attempt_state(self) -> Self:
        if self.inventory_evidence_ids != tuple(sorted(set(self.inventory_evidence_ids))):
            raise ValueError("Current acceptance run evidence must be sorted and unique.")
        if self.wordpress_evidence_ids != tuple(sorted(set(self.wordpress_evidence_ids))):
            raise ValueError("Current acceptance WordPress evidence must be sorted and unique.")
        if self.status == "complete":
            if not self.wave_id or not self.wave_digest or self.blocker_code:
                raise ValueError("Completed current acceptance run needs its exact wave.")
        elif self.wave_id is not None or self.wave_digest is not None:
            raise ValueError("Incomplete current acceptance run cannot reference a wave.")
        if self.status == "failed" and not (
            self.blocker_code and self.blocker_owner and self.safe_next_step
        ):
            raise ValueError("Failed current acceptance run needs one typed blocker.")
        if self.status != "failed" and any(
            value is not None
            for value in (self.blocker_code, self.blocker_owner, self.safe_next_step)
        ):
            raise ValueError("Non-failed current acceptance run cannot carry a blocker.")
        return self


class CurrentAcceptanceRunRead(_FrozenModel):
    attempt: CurrentAcceptanceAttempt
    wave: CurrentAcceptanceWave | None = None

    @model_validator(mode="after")
    def require_wave_readback(self) -> Self:
        if self.attempt.status == "complete":
            if (
                self.wave is None
                or self.wave.wave_id != self.attempt.wave_id
                or self.wave.wave_digest != self.attempt.wave_digest
            ):
                raise ValueError("Completed current acceptance run is missing exact wave readback.")
        elif self.wave is not None:
            raise ValueError("Non-completed current acceptance run cannot expose a wave.")
        return self


@dataclass(frozen=True)
class CurrentAcceptanceSnapshot:
    scope: CurrentInventoryScopeResponse
    catalog: ContentInventoryCatalogResponse
    wordpress_evidence_ids: tuple[str, ...]
    freshness_state: str
    freshness_assessment: ContentFreshnessAssessment
    source_facts: tuple[ContentSourceFact, ...]
    knowledge_cards: tuple[ContentKnowledgeCard, ...]
    captured_at: datetime
    source_snapshot_digest: str


def current_acceptance_wave_digest(value: CurrentAcceptanceWave | dict[str, Any]) -> str:
    payload = (
        value.model_dump(mode="json")
        if isinstance(value, BaseModel)
        else CurrentAcceptanceWave.model_construct(**dict(value)).model_dump(mode="json")
    )
    payload.pop("wave_id", None)
    payload.pop("wave_digest", None)
    return canonical_json_digest(payload)


def current_acceptance_scope_coverage_digest(
    rows: Iterable[tuple[str, str]],
) -> str:
    """Digest the pinned per-path scope labels used to verify sealed row coverage."""

    return canonical_json_digest(
        {
            "rows": [
                {"canonical_path": canonical_path, "disposition": disposition}
                for canonical_path, disposition in sorted(rows)
            ]
        }
    )


def current_acceptance_wave_counts(
    rows: Sequence[CurrentAcceptanceRow],
) -> CurrentAcceptanceWaveCounts:
    scope_eligible = sum(row.scope_disposition == "eligible" for row in rows)
    scope_excluded = sum(row.scope_disposition == "excluded" for row in rows)
    scope_blocked = sum(row.scope_disposition == "blocked" for row in rows)
    return CurrentAcceptanceWaveCounts(
        rows=len(rows),
        scope_eligible=scope_eligible,
        scope_excluded=scope_excluded,
        scope_blocked=scope_blocked,
        keep=sum(row.decision == "keep" for row in rows),
        refresh=sum(row.decision == "refresh" for row in rows),
        eligible_blocked=sum(
            row.scope_disposition == "eligible" and row.decision == "blocked" for row in rows
        ),
    )


__all__ = [
    "CurrentAcceptanceAttempt",
    "CurrentAcceptanceBlocked",
    "CurrentAcceptanceDecision",
    "CurrentAcceptanceRow",
    "CurrentAcceptanceRunRead",
    "CurrentAcceptanceSnapshot",
    "CurrentAcceptanceWave",
    "CurrentAcceptanceWaveCounts",
    "CurrentPageMaterialStatus",
    "current_acceptance_scope_coverage_digest",
    "current_acceptance_wave_counts",
    "current_acceptance_wave_digest",
]
