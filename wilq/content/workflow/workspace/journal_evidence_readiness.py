"""Indexed, read-only evidence readiness for the canonical content journal."""

from __future__ import annotations

import csv
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, Protocol, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.canonical.urls import content_normalized_path
from wilq.content.workflow.workspace.journal_reconciliation import (
    _EXPECTED_JOURNAL_RECORD_COUNT,
    _canonical_journal_path,
    _normalized_path,
)


class _CatalogObservation(Protocol):
    work_item_id: str
    path: str
    url: str
    catalog_id: str
    content_type: str
    material_status: str
    source_connector: str
    evidence_id: str
    collected_at: datetime


class ContentEvidenceReadinessBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = ()
    safe_next_step: str = Field(min_length=1)


class ContentEvidenceAuthoringInventoryReceiptReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["current", "missing", "stale"]
    receipt_id: str | None = None
    receipt_digest: str | None = None
    evidence_id: str | None = None
    collected_at: datetime | None = None
    freshness: Literal["fresh", "stale", "missing"]

    @model_validator(mode="after")
    def require_receipt_state(self) -> Self:
        has_identity = all(
            value is not None
            for value in (self.receipt_id, self.receipt_digest, self.evidence_id)
        )
        if self.status == "current" and (not has_identity or self.freshness != "fresh"):
            raise ValueError("Current authoring receipt readiness requires fresh receipt identity.")
        if self.status == "missing" and (
            has_identity or self.freshness != "missing" or self.collected_at is not None
        ):
            raise ValueError("Missing authoring receipt readiness cannot expose receipt identity.")
        if self.status == "stale" and (not has_identity or self.freshness != "stale"):
            raise ValueError("Stale authoring receipt readiness requires receipt identity.")
        return self


class ContentEvidenceAcquisitionReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    recorded_status: Literal["missing", "blocked", "ready_for_researcher"]
    current_status: Literal["missing", "blocked", "ready_for_researcher"]
    run_id: str | None = None
    run_digest: str | None = None
    evidence_ids: tuple[str, ...] = ()
    subject_kind: Literal["identity_binding", "authoring_inventory_receipt"] | None = None
    subject_id: str | None = None
    freshness: Literal["fresh", "stale", "missing", "not_applicable"]
    blockers: tuple[ContentEvidenceReadinessBlocker, ...] = ()
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_acquisition_state(self) -> Self:
        if self.recorded_status == "missing" and (
            self.current_status != "missing"
            or self.run_id is not None
            or self.run_digest is not None
            or self.evidence_ids
            or self.subject_kind is not None
            or self.subject_id is not None
        ):
            raise ValueError("Missing acquisition readiness cannot expose a run.")
        if self.current_status == "blocked" and not self.blockers:
            raise ValueError("Blocked acquisition readiness requires typed blockers.")
        return self


class ContentEvidenceResearchProposalReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["missing", "blocked", "ready_for_review"]
    proposal_id: str | None = None
    proposal_digest: str | None = None
    acquisition_run_id: str | None = None
    review_required: bool
    approved: Literal[False] = False
    blockers: tuple[ContentEvidenceReadinessBlocker, ...] = ()
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_research_state(self) -> Self:
        if self.status == "missing" and (
            self.proposal_id is not None
            or self.proposal_digest is not None
            or self.acquisition_run_id is not None
            or self.review_required
        ):
            raise ValueError("Missing research readiness cannot expose a proposal.")
        if self.status == "blocked" and not self.blockers:
            raise ValueError("Blocked research readiness requires typed blockers.")
        if self.status == "ready_for_review" and not self.review_required:
            raise ValueError("Research proposal readiness requires human review.")
        return self


class ContentEvidenceIdentityReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["missing", "exact_current", "reconciled_retained", "blocked"]
    binding_id: str | None = None
    binding_digest: str | None = None
    blockers: tuple[ContentEvidenceReadinessBlocker, ...] = ()
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_identity_state(self) -> Self:
        if self.status == "missing" and (
            self.binding_id is not None or self.binding_digest is not None
        ):
            raise ValueError("Missing identity readiness cannot expose a binding.")
        if self.status in {"reconciled_retained", "blocked"} and not self.blockers:
            raise ValueError("Non-current identity readiness requires a blocker.")
        return self


class ContentEvidenceServiceCardReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["missing", "approved_current", "review_required", "blocked"]
    card_id: str | None = None
    card_status: str | None = None
    evidence_ids: tuple[str, ...] = ()
    source_connectors: tuple[str, ...] = ()
    blockers: tuple[ContentEvidenceReadinessBlocker, ...] = ()
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_card_state(self) -> Self:
        if self.status == "missing" and self.card_id is not None:
            raise ValueError("Missing card readiness cannot expose a card.")
        if self.status != "approved_current" and not self.blockers:
            raise ValueError("Unapproved card readiness requires a blocker.")
        return self


class ContentEvidencePromotionReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["missing", "blocked", "review_required", "approved_current", "rejected"]
    receipt_id: str | None = None
    source_fact_id: str | None = None
    blockers: tuple[ContentEvidenceReadinessBlocker, ...] = ()
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_promotion_state(self) -> Self:
        if self.status == "approved_current" and (
            self.receipt_id is None or self.source_fact_id is None or self.blockers
        ):
            raise ValueError("Approved promotion readiness requires a receipt and source fact.")
        if (
            self.status in {"missing", "blocked", "review_required", "rejected"}
            and not self.blockers
        ):
            raise ValueError("Non-approved promotion readiness requires a blocker.")
        return self


class ContentEvidenceReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["missing", "blocked", "ready_for_researcher", "review_required"]
    status_label: str = Field(min_length=1)
    authoring_inventory_receipt: ContentEvidenceAuthoringInventoryReceiptReadiness
    evidence_acquisition: ContentEvidenceAcquisitionReadiness
    research_proposal: ContentEvidenceResearchProposalReadiness
    identity: ContentEvidenceIdentityReadiness
    service_card: ContentEvidenceServiceCardReadiness
    promotion: ContentEvidencePromotionReadiness
    blockers: tuple[ContentEvidenceReadinessBlocker, ...] = ()
    generation_allowed: Literal[False] = False
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_overall_state(self) -> Self:
        if self.status == "blocked" and not self.blockers:
            raise ValueError("Blocked content evidence readiness requires a blocker.")
        if self.status != "blocked" and self.blockers:
            raise ValueError("Non-blocked content evidence readiness cannot carry blockers.")
        return self


class ContentEvidenceReadinessSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    total_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    review_required_count: int = Field(ge=0)
    ready_for_researcher_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    authoring_receipt_current_count: int = Field(ge=0)
    authoring_receipt_stale_count: int = Field(ge=0)
    authoring_receipt_missing_count: int = Field(ge=0)
    acquisition_ready_count: int = Field(ge=0)
    acquisition_blocked_count: int = Field(ge=0)
    acquisition_missing_count: int = Field(ge=0)
    research_ready_count: int = Field(ge=0)
    research_blocked_count: int = Field(ge=0)
    research_missing_count: int = Field(ge=0)
    identity_exact_current_count: int = Field(ge=0)
    identity_blocked_count: int = Field(ge=0)
    identity_missing_count: int = Field(ge=0)
    service_card_approved_current_count: int = Field(ge=0)
    service_card_review_required_count: int = Field(ge=0)
    promotion_approved_current_count: int = Field(ge=0)
    generation_allowed: Literal[False] = False


class ContentInventoryJournalCatalogObservation(BaseModel):
    """Current observation only; it deliberately carries no authoring identity."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    url: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    material_status: str = Field(min_length=1)
    source_connector: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    collected_at: datetime


class ContentInventoryJournalReadinessRow(BaseModel):
    """One journal decision with an exact current observation, never a binding."""

    model_config = ConfigDict(extra="forbid")

    canonical_path: str = Field(min_length=1)
    historical_as_of: str = Field(min_length=1)
    content_kind: str = Field(min_length=1)
    final_disposition: Literal["keep", "noindex", "redirect", "remove"]
    historical_next_action: str = Field(min_length=1)
    operational_owner: Literal["WILQ content workflow", "WILQ sitemap operations"]
    production_cohort: bool
    current_catalog_state: Literal["exact_path_observed", "not_observed", "ambiguous"]
    current_catalog_observation: ContentInventoryJournalCatalogObservation | None = None
    content_evidence_readiness: ContentEvidenceReadiness


class ContentInventoryJournalReadiness(BaseModel):
    """Full 214-row journal view; historical decisions remain visibly historical."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["complete", "incomplete", "blocked"]
    journal_record_count: int = Field(ge=0)
    catalog_coverage_status: Literal["complete", "partial", "unknown"]
    rows: list[ContentInventoryJournalReadinessRow] = Field(default_factory=list)
    content_evidence_readiness: ContentEvidenceReadinessSummary
    caveat: str = Field(min_length=1)
    safe_next_step: str = Field(min_length=1)



class ContentEvidenceReadinessStore(Protocol):
    """Read-only store port used to build one indexed journal projection."""

    def list_content_authoring_inventory_receipts(self) -> list[Any]: ...

    def list_evidence_acquisition_runs(self) -> list[Any]: ...

    def list_research_proposals(self) -> list[Any]: ...

    def list_research_proposals_with_diagnostics(self) -> list[Any]: ...

    def list_content_delivery_identity_current_projections(self) -> list[Any]: ...

    def list_research_fact_promotion_receipts(self) -> list[Any]: ...


@dataclass(frozen=True, slots=True)
class _EvidenceReadinessIndex:
    receipts_by_path: dict[str, Any]
    acquisitions_by_path: dict[str, Any]
    research_by_path: dict[str, Any]
    research_diagnostics_by_path: dict[str, tuple[ContentEvidenceReadinessBlocker, ...]]
    global_research_diagnostics: tuple[ContentEvidenceReadinessBlocker, ...]
    identities_by_path: dict[str, Any]
    promotions_by_path: dict[str, Any]
    cards_by_path: dict[str, tuple[Any, ...]]
    catalog_snapshot_digest: str | None
    store_blocker: ContentEvidenceReadinessBlocker | None = None



def project_content_evidence_readiness(
    journal_paths: Iterable[str],
    catalog_by_path: Mapping[str, list[Any]],
    *,
    evidence_store: ContentEvidenceReadinessStore | None,
    assessed_at: datetime,
    catalog_snapshot_digest: str | None,
) -> tuple[dict[str, ContentEvidenceReadiness], ContentEvidenceReadinessSummary]:
    """Project supplied journal paths using one indexed, read-only store pass."""

    index = _load_evidence_readiness_index(
        evidence_store,
        catalog_snapshot_digest=catalog_snapshot_digest,
    )
    projections: dict[str, ContentEvidenceReadiness] = {}
    for path in journal_paths:
        matches = catalog_by_path.get(path, [])
        projections[path] = _build_content_evidence_readiness(
            path,
            catalog_item=matches[0] if len(matches) == 1 else None,
            index=index,
            assessed_at=assessed_at,
        )
    return projections, _summarize_content_evidence_readiness(projections.values())


def build_content_inventory_journal_readiness(
    catalog_items: Iterable[_CatalogObservation],
    *,
    catalog_coverage_status: Literal["complete", "partial", "unknown"],
    journal_path: Path | None = None,
    evidence_store: ContentEvidenceReadinessStore | None = None,
    assessed_at: datetime | None = None,
    catalog_snapshot_digest: str | None = None,
) -> ContentInventoryJournalReadiness:
    """Project every journal row without converting an exact path into an identity."""

    journal = _load_readiness_journal(journal_path or _canonical_journal_path())
    if journal is None:
        return ContentInventoryJournalReadiness(
            status="blocked",
            journal_record_count=0,
            catalog_coverage_status=catalog_coverage_status,
            content_evidence_readiness=empty_content_evidence_readiness_summary(),
            caveat="Nie można odczytać kanonicznego journalu do pełnej projekcji readiness.",
            safe_next_step="Napraw i zweryfikuj kanoniczny journal przed decyzjami per URL.",
        )
    assessed_at = (assessed_at or datetime.now(UTC)).astimezone(UTC)
    catalog_items = list(catalog_items)
    catalog_by_path: dict[str, list[_CatalogObservation]] = {}
    for item in catalog_items:
        path = _normalized_path(item.path)
        catalog_by_path.setdefault(path, []).append(item)
    evidence_by_path, evidence_summary = project_content_evidence_readiness(
        (row["path"] for row in journal),
        catalog_by_path,
        evidence_store=evidence_store,
        assessed_at=assessed_at,
        catalog_snapshot_digest=catalog_snapshot_digest,
    )
    rows: list[ContentInventoryJournalReadinessRow] = []
    for journal_row in journal:
        path = journal_row["path"]
        matches = catalog_by_path.get(path, [])
        observation = _catalog_observation(matches[0]) if len(matches) == 1 else None
        current_catalog_state: Literal["exact_path_observed", "not_observed", "ambiguous"] = (
            "exact_path_observed"
            if observation is not None
            else "ambiguous"
            if matches
            else "not_observed"
        )
        final_disposition = cast(
            Literal["keep", "noindex", "redirect", "remove"],
            journal_row["final_disposition"],
        )
        production_cohort = final_disposition == "keep"
        rows.append(
            ContentInventoryJournalReadinessRow(
                canonical_path=path,
                historical_as_of=journal_row["as_of"],
                content_kind=journal_row["content_kind"],
                final_disposition=final_disposition,
                historical_next_action=journal_row["next_action"],
                operational_owner=(
                    "WILQ content workflow"
                    if production_cohort
                    else "WILQ sitemap operations"
                ),
                production_cohort=production_cohort,
                current_catalog_state=current_catalog_state,
                current_catalog_observation=observation,
                content_evidence_readiness=evidence_by_path[path],
            )
        )
    journal_scope_complete = len(rows) == _EXPECTED_JOURNAL_RECORD_COUNT
    all_observed = all(row.current_catalog_state == "exact_path_observed" for row in rows)
    status: Literal["complete", "incomplete", "blocked"] = (
        "complete"
        if catalog_coverage_status == "complete" and journal_scope_complete and all_observed
        else "incomplete"
        if catalog_coverage_status == "complete"
        else "blocked"
    )
    return ContentInventoryJournalReadiness(
        status=status,
        journal_record_count=len(rows),
        catalog_coverage_status=catalog_coverage_status,
        rows=rows,
        content_evidence_readiness=evidence_summary,
        caveat=(
            "Bieżący katalog ma pełne coverage i obserwację dokładnej ścieżki dla każdego URL."
            if status == "complete"
            else (
                "Journal nie ma wymaganych 214 unikalnych wierszy."
                if not journal_scope_complete
                else (
                    "Journal zachowuje historyczne decyzje; brak pełnego bieżącego coverage "
                    "nie potwierdza ich runtime."
                )
            )
        ),
        safe_next_step=(
            "Przejdź do evidence-bound readiness kohorty keep."
            if status == "complete"
            else (
                "Przywróć i zweryfikuj pełne 214 wierszy kanonicznego journalu."
                if not journal_scope_complete
                else (
                    "Uzupełnij pełny bieżący inventory albo zachowaj per-URL brak obserwacji "
                    "jako blocker."
                )
            )
        ),
    )


def _load_readiness_journal(path: Path) -> list[dict[str, str]] | None:
    required = {"as_of", "path", "content_kind", "final_disposition", "next_action"}
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or not required.issubset(reader.fieldnames):
                return None
            rows: list[dict[str, str]] = []
            paths: set[str] = set()
            for raw in reader:
                normalized_path = _normalized_path(str(raw.get("path") or ""))
                if not normalized_path or normalized_path in paths:
                    return None
                final_disposition = str(raw.get("final_disposition") or "").strip()
                if final_disposition not in {"keep", "noindex", "redirect", "remove"}:
                    return None
                values = {
                    "as_of": str(raw.get("as_of") or "").strip(),
                    "path": normalized_path,
                    "content_kind": str(raw.get("content_kind") or "").strip(),
                    "final_disposition": final_disposition,
                    "next_action": str(raw.get("next_action") or "").strip(),
                }
                if not all(values.values()):
                    return None
                paths.add(normalized_path)
                rows.append(values)
    except (OSError, csv.Error):
        return None
    return rows or None


def _catalog_observation(item: _CatalogObservation) -> ContentInventoryJournalCatalogObservation:
    return ContentInventoryJournalCatalogObservation(
        path=_normalized_path(item.path),
        url=item.url,
        content_type=item.content_type,
        material_status=item.material_status,
        source_connector=item.source_connector,
        evidence_id=item.evidence_id,
        collected_at=item.collected_at,
    )


def _empty_evidence_readiness_summary() -> ContentEvidenceReadinessSummary:
    return ContentEvidenceReadinessSummary(
        total_count=0,
        blocked_count=0,
        review_required_count=0,
        ready_for_researcher_count=0,
        missing_count=0,
        authoring_receipt_current_count=0,
        authoring_receipt_stale_count=0,
        authoring_receipt_missing_count=0,
        acquisition_ready_count=0,
        acquisition_blocked_count=0,
        acquisition_missing_count=0,
        research_ready_count=0,
        research_blocked_count=0,
        research_missing_count=0,
        identity_exact_current_count=0,
        identity_blocked_count=0,
        identity_missing_count=0,
        service_card_approved_current_count=0,
        service_card_review_required_count=0,
        promotion_approved_current_count=0,
    )


def _default_evidence_readiness_store() -> ContentEvidenceReadinessStore:
    from wilq.content.workflow.store.store import content_workflow_store

    return content_workflow_store()


def _load_evidence_readiness_index(
    evidence_store: ContentEvidenceReadinessStore | None,
    *,
    catalog_snapshot_digest: str | None,
) -> _EvidenceReadinessIndex:
    store = evidence_store or _default_evidence_readiness_store()
    try:
        receipts = store.list_content_authoring_inventory_receipts()
        acquisitions = store.list_evidence_acquisition_runs()
        proposal_results = store.list_research_proposals_with_diagnostics()
        identities = store.list_content_delivery_identity_current_projections()
        promotions = store.list_research_fact_promotion_receipts()
    except Exception:
        return _empty_evidence_readiness_index(
            ContentEvidenceReadinessBlocker(
                code="content_evidence_readiness_store_unavailable",
                reason="Canonical evidence readiness records could not be read.",
                safe_next_step="Sprawdź lokalny store WILQ przed decyzją per URL.",
            ),
            catalog_snapshot_digest=catalog_snapshot_digest,
        )

    proposals = [
        result.proposal
        for result in proposal_results
        if getattr(result, "proposal", None) is not None
    ]
    proposal_diagnostics = [
        result.diagnostic
        for result in proposal_results
        if getattr(result, "diagnostic", None) is not None
    ]
    receipts_by_path = _latest_by_path(
        receipts,
        lambda record: getattr(record, "canonical_path", ""),
        lambda record: (
            getattr(record, "recorded_at", datetime.min),
            getattr(record, "collected_at", datetime.min),
            str(getattr(record, "receipt_id", "")),
        ),
    )
    receipt_paths_by_id = {
        str(getattr(record, "receipt_id", "")): _normalized_path(
            str(getattr(record, "canonical_path", ""))
        )
        for record in receipts
        if getattr(record, "receipt_id", None)
    }
    acquisition_paths_by_id = {
        str(getattr(record, "run_id", "")): _acquisition_path(
            record, receipt_paths_by_id
        )
        for record in acquisitions
        if getattr(record, "run_id", None)
    }
    acquisitions_by_path = _latest_by_path(
        acquisitions,
        lambda record: _acquisition_path(record, receipt_paths_by_id),
        lambda record: (
            int(getattr(record, "attempt", 0)),
            str(getattr(record, "run_id", "")),
        ),
    )
    research_by_path = _latest_by_path(
        proposals,
        lambda record: _research_path(record, acquisition_paths_by_id),
        lambda record: (
            getattr(record, "recorded_at", datetime.min),
            str(getattr(record, "proposal_id", "")),
        ),
    )
    identities_by_path = _latest_by_path(
        identities,
        _identity_path,
        lambda record: (
            _identity_recorded_at(record),
            str(getattr(_identity_binding(record), "binding_id", "")),
        ),
    )
    promotions_by_path = _latest_by_path(
        promotions,
        lambda record: _promotion_path(record),
        lambda record: (
            getattr(record, "recorded_at", datetime.min),
            str(getattr(record, "receipt_id", "")),
        ),
    )
    research_diagnostics_by_path, global_research_diagnostics = _research_diagnostic_index(
        proposal_diagnostics,
        acquisition_paths_by_id,
    )
    return _EvidenceReadinessIndex(
        receipts_by_path=receipts_by_path,
        acquisitions_by_path=acquisitions_by_path,
        research_by_path=research_by_path,
        research_diagnostics_by_path=research_diagnostics_by_path,
        global_research_diagnostics=global_research_diagnostics,
        identities_by_path=identities_by_path,
        promotions_by_path=promotions_by_path,
        cards_by_path=_service_cards_by_path(),
        catalog_snapshot_digest=catalog_snapshot_digest,
    )


def _empty_evidence_readiness_index(
    blocker: ContentEvidenceReadinessBlocker,
    *,
    catalog_snapshot_digest: str | None,
) -> _EvidenceReadinessIndex:
    return _EvidenceReadinessIndex(
        receipts_by_path={},
        acquisitions_by_path={},
        research_by_path={},
        research_diagnostics_by_path={},
        global_research_diagnostics=(),
        identities_by_path={},
        promotions_by_path={},
        cards_by_path={},
        catalog_snapshot_digest=catalog_snapshot_digest,
        store_blocker=blocker,
    )


def _latest_by_path(
    records: Iterable[Any],
    path_getter: Callable[[Any], str],
    sort_key: Callable[[Any], tuple[Any, ...]],
) -> dict[str, Any]:
    latest: dict[str, Any] = {}
    for record in records:
        raw_path = path_getter(record)
        path = _normalized_path(raw_path) if raw_path else ""
        if not path:
            continue
        current = latest.get(path)
        if current is None or sort_key(record) > sort_key(current):
            latest[path] = record
    return latest


def _acquisition_path(record: Any, receipt_paths_by_id: dict[str, str]) -> str:
    path = str(getattr(record, "canonical_path", "") or "").strip()
    if not path and getattr(record, "subject_kind", None) == "authoring_inventory_receipt":
        receipt_id = str(getattr(record, "authoring_inventory_receipt_id", "") or "")
        path = receipt_paths_by_id.get(receipt_id, "")
    return path


def _research_path(record: Any, acquisition_paths_by_id: dict[str, str]) -> str:
    source_url = str(getattr(record, "source_url", "") or "").strip()
    if source_url:
        return _path_from_reference(source_url)
    return acquisition_paths_by_id.get(
        str(getattr(record, "acquisition_run_id", "") or ""), ""
    )


def _research_diagnostic_index(
    diagnostics: Iterable[Any],
    acquisition_paths_by_id: dict[str, str],
) -> tuple[
    dict[str, tuple[ContentEvidenceReadinessBlocker, ...]],
    tuple[ContentEvidenceReadinessBlocker, ...],
]:
    by_path: dict[str, list[ContentEvidenceReadinessBlocker]] = {}
    global_blockers: list[ContentEvidenceReadinessBlocker] = []
    for diagnostic in diagnostics:
        blocker = _readiness_blocker(
            diagnostic.code,
            diagnostic.reason,
            next_step=diagnostic.safe_next_step,
        )
        path = _path_from_reference(diagnostic.source_url or "")
        if not path:
            path = acquisition_paths_by_id.get(diagnostic.acquisition_run_id or "", "")
        if path:
            by_path.setdefault(path, []).append(blocker)
        else:
            global_blockers.append(blocker)
    return (
        {path: _unique_blockers(items) for path, items in by_path.items()},
        _unique_blockers(global_blockers),
    )


def _promotion_path(record: Any) -> str:
    snapshot = getattr(record, "snapshot", None)
    return "" if snapshot is None else _path_from_reference(snapshot.source_url)


def _path_from_reference(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    try:
        return _normalized_path(content_normalized_path(value))
    except ValueError:
        return ""


def _service_cards_by_path() -> dict[str, tuple[Any, ...]]:
    from wilq.content.knowledge.cards import ekologus_content_knowledge_cards

    by_path: dict[str, list[Any]] = {}
    for card in ekologus_content_knowledge_cards():
        if card.card_type != "service":
            continue
        for url in card.service_binding_urls:
            path = _path_from_reference(url)
            if path:
                by_path.setdefault(path, []).append(card)
    return {path: tuple(cards) for path, cards in by_path.items()}


def _build_content_evidence_readiness(
    path: str,
    *,
    catalog_item: Any | None,
    index: _EvidenceReadinessIndex,
    assessed_at: datetime,
) -> ContentEvidenceReadiness:
    receipt = index.receipts_by_path.get(path)
    receipt_readiness = _authoring_receipt_readiness(
        receipt,
        catalog_item,
        assessed_at,
        catalog_snapshot_digest=index.catalog_snapshot_digest,
    )
    identity = _identity_readiness(index.identities_by_path.get(path))
    acquisition = _acquisition_readiness(
        index.acquisitions_by_path.get(path),
        receipt_readiness,
        identity,
        assessed_at,
    )
    research = _research_readiness(index.research_by_path.get(path), acquisition)
    card = _service_card_readiness(index.cards_by_path.get(path, ()))
    promotion = _promotion_readiness(
        index.promotions_by_path.get(path),
        identity=identity,
        service_card=card,
        research=research,
        acquisition=acquisition,
        path=path,
    )
    blockers: list[ContentEvidenceReadinessBlocker] = []
    if index.store_blocker is not None:
        blockers.append(index.store_blocker)
    if catalog_item is None:
        blockers.append(
            _readiness_blocker(
                "current_catalog_observation_missing",
                "No exact current catalog observation exists for this journal path.",
                next_step="Odśwież WordPress inventory i potwierdź exact ścieżkę.",
            )
        )
    if receipt_readiness.status != "current":
        blockers.append(
            _receipt_readiness_blocker(receipt_readiness)
        )
    if acquisition.current_status != "ready_for_researcher":
        if acquisition.current_status == "missing":
            blockers.append(
                _readiness_blocker(
                    "evidence_acquisition_missing",
                    "No evidence acquisition run is available for this URL.",
                    next_step="Uruchom exact evidence acquisition po potwierdzeniu źródła.",
                )
            )
        else:
            blockers.extend(acquisition.blockers)
    if research.status != "ready_for_review":
        if research.status == "missing":
            blockers.append(
                _readiness_blocker(
                    "research_proposal_missing",
                    "No server-owned research proposal exists for this URL.",
                    next_step="Najpierw uzyskaj current evidence acquisition.",
                )
            )
        else:
            blockers.extend(research.blockers)
    blockers.extend(index.research_diagnostics_by_path.get(path, ()))
    blockers.extend(index.global_research_diagnostics)
    if identity.status != "exact_current":
        if identity.status == "missing":
            blockers.append(
                _readiness_blocker(
                    "identity_binding_missing",
                    "Exact current identity binding is missing for this URL.",
                    next_step="Zwiąż exact S1 identity dopiero po weryfikacji disposition.",
                )
            )
        else:
            blockers.extend(identity.blockers)
    if card.status != "approved_current":
        blockers.extend(card.blockers)
    if promotion.status != "approved_current":
        blockers.extend(promotion.blockers)
    blockers = list(_unique_blockers(blockers))
    status: Literal["missing", "blocked", "ready_for_researcher", "review_required"]
    if blockers:
        status = "blocked"
    elif research.status == "ready_for_review":
        status = "review_required"
    elif acquisition.current_status == "ready_for_researcher":
        status = "ready_for_researcher"
    else:
        status = "missing"
    labels = {
        "missing": "Brakuje danych",
        "blocked": "Zablokowane",
        "ready_for_researcher": "Gotowe do researchu",
        "review_required": "Wymaga review",
    }
    return ContentEvidenceReadiness(
        status=status,
        status_label=labels[status],
        authoring_inventory_receipt=receipt_readiness,
        evidence_acquisition=acquisition,
        research_proposal=research,
        identity=identity,
        service_card=card,
        promotion=promotion,
        blockers=tuple(blockers),
        safe_next_step=(
            blockers[0].safe_next_step
            if blockers
            else "Przejdź do następnego exact kroku researchu."
        ),
    )


def _authoring_receipt_readiness(
    receipt: Any | None,
    catalog_item: _CatalogObservation | None,
    assessed_at: datetime,
    *,
    catalog_snapshot_digest: str | None,
) -> ContentEvidenceAuthoringInventoryReceiptReadiness:
    if receipt is None:
        return ContentEvidenceAuthoringInventoryReceiptReadiness(
            status="missing", freshness="missing"
        )
    if (
        catalog_item is None
        or catalog_snapshot_digest is None
        or receipt.catalog_snapshot_digest != catalog_snapshot_digest
        or not _receipt_matches_catalog_item(receipt, catalog_item)
    ):
        return ContentEvidenceAuthoringInventoryReceiptReadiness(
            status="stale",
            receipt_id=receipt.receipt_id,
            receipt_digest=receipt.receipt_digest,
            evidence_id=receipt.evidence_id,
            collected_at=receipt.collected_at,
            freshness="stale",
        )
    fresh = _receipt_is_fresh(receipt, assessed_at)
    return ContentEvidenceAuthoringInventoryReceiptReadiness(
        status="current" if fresh else "stale",
        receipt_id=receipt.receipt_id,
        receipt_digest=receipt.receipt_digest,
        evidence_id=receipt.evidence_id,
        collected_at=receipt.collected_at,
        freshness="fresh" if fresh else "stale",
    )


def _receipt_matches_catalog_item(receipt: Any, item: Any) -> bool:
    from wilq.content.workflow.authoring_inventory_receipt import (
        content_inventory_catalog_item_digest,
    )

    return all(
        (
            receipt.catalog_id == item.catalog_id,
            receipt.current_work_item_id == item.work_item_id,
            receipt.public_url == item.url,
            receipt.canonical_path == _normalized_path(item.path),
            receipt.source_connector == "wordpress_ekologus",
            receipt.evidence_id == item.evidence_id,
            receipt.collected_at == item.collected_at,
            receipt.catalog_item_digest == content_inventory_catalog_item_digest(item),
        )
    )


def _receipt_is_fresh(receipt: Any, assessed_at: datetime) -> bool:
    from wilq.briefing.content_diagnostics import CONTENT_STALE_AFTER_HOURS

    collected_at = getattr(receipt, "collected_at", None)
    if not isinstance(collected_at, datetime):
        return False
    age = assessed_at.astimezone(UTC) - collected_at.astimezone(UTC)
    return timedelta(0) <= age <= timedelta(hours=CONTENT_STALE_AFTER_HOURS)


def _acquisition_readiness(
    run: Any | None,
    receipt: ContentEvidenceAuthoringInventoryReceiptReadiness,
    identity: ContentEvidenceIdentityReadiness,
    assessed_at: datetime,
) -> ContentEvidenceAcquisitionReadiness:
    if run is None:
        return ContentEvidenceAcquisitionReadiness(
            recorded_status="missing",
            current_status="missing",
            freshness="missing",
            safe_next_step="Uruchom exact evidence acquisition po potwierdzeniu źródła.",
        )
    blockers = _record_blockers(getattr(run, "blockers", ()))
    evidence_ids = _observation_evidence_ids(getattr(run, "observation", None))
    current_status: Literal["blocked", "ready_for_researcher"] = run.status
    freshness: Literal["fresh", "stale", "not_applicable"] = "not_applicable"
    if run.status == "ready_for_researcher":
        observation = getattr(run, "observation", None)
        if getattr(run, "subject_kind", None) == "identity_binding" and identity.status != (
            "exact_current"
        ):
            current_status = "blocked"
            blockers = identity.blockers or (
                _readiness_blocker(
                    "identity_binding_missing",
                    "Exact current identity binding is required for acquisition.",
                    next_step="Zwiąż exact S1 identity przed evidence acquisition.",
                ),
            )
        elif observation is None:
            current_status = "blocked"
            blockers = (
                _readiness_blocker(
                    "acquisition_observation_missing",
                    "Researcher-ready acquisition has no exact observation.",
                    next_step="Wykonaj nowy exact current-page read.",
                ),
            )
        elif (
            getattr(run, "subject_kind", None) == "authoring_inventory_receipt"
            and (
                receipt.status != "current"
                or getattr(run, "authoring_inventory_receipt_digest", None)
                != receipt.receipt_digest
            )
        ):
            current_status = "blocked"
            blockers = (_receipt_readiness_blocker(receipt),)
            freshness = "stale"
        else:
            from wilq.content.workflow.evidence_acquisition_snapshot import (
                current_page_receipt_is_fresh,
            )

            if current_page_receipt_is_fresh(observation, now=assessed_at):
                freshness = "fresh"
            else:
                current_status = "blocked"
                freshness = "stale"
                blockers = (
                    _readiness_blocker(
                        "current_page_snapshot_stale",
                        "The stored current-page observation is stale for research use.",
                        evidence_ids=evidence_ids,
                        next_step="Uruchom nowy exact current-page read.",
                    ),
                )
    subject_kind = getattr(run, "subject_kind", None)
    subject_id = (
        getattr(run, "identity_binding_id", None)
        if subject_kind == "identity_binding"
        else getattr(run, "authoring_inventory_receipt_id", None)
    )
    return ContentEvidenceAcquisitionReadiness(
        recorded_status=run.status,
        current_status=current_status,
        run_id=run.run_id,
        run_digest=run.run_digest,
        evidence_ids=evidence_ids,
        subject_kind=subject_kind,
        subject_id=subject_id,
        freshness=freshness,
        blockers=blockers,
        safe_next_step=(
            blockers[0].safe_next_step
            if blockers
            else "Przekaż exact observation do researchera."
        ),
    )


def _research_readiness(
    proposal: Any | None,
    acquisition: ContentEvidenceAcquisitionReadiness,
) -> ContentEvidenceResearchProposalReadiness:
    if proposal is None:
        return ContentEvidenceResearchProposalReadiness(
            status="missing",
            review_required=False,
            safe_next_step="Najpierw uzyskaj current evidence acquisition.",
        )
    blockers = _record_blockers(getattr(proposal, "blockers", ()))
    status: Literal["blocked", "ready_for_review"] = proposal.status
    acquisition_drifted = (
        acquisition.run_id is not None
        and (
            proposal.acquisition_run_id != acquisition.run_id
            or getattr(proposal, "acquisition_run_digest", None)
            != acquisition.run_digest
        )
    )
    if status == "ready_for_review" and acquisition_drifted:
        status = "blocked"
        blockers = (
            _readiness_blocker(
                "research_proposal_acquisition_drift",
                "Research proposal belongs to an older acquisition run.",
                evidence_ids=acquisition.evidence_ids,
                next_step=(
                    "Uruchom researcher dla bieżącego acquisition run i przygotuj "
                    "nową propozycję."
                ),
            ),
        )
    elif status == "ready_for_review" and acquisition.current_status != "ready_for_researcher":
        status = "blocked"
        blockers = acquisition.blockers or (
            _readiness_blocker(
                "evidence_acquisition_blocked",
                "Current acquisition is not ready for this research proposal.",
                next_step="Usuń blocker evidence acquisition i przygotuj nową próbę.",
            ),
        )
    return ContentEvidenceResearchProposalReadiness(
        status=status,
        proposal_id=proposal.proposal_id,
        proposal_digest=proposal.proposal_digest,
        acquisition_run_id=proposal.acquisition_run_id,
        review_required=bool(proposal.review_required),
        approved=False,
        blockers=blockers,
        safe_next_step=(
            blockers[0].safe_next_step
            if blockers
            else "Przekaż propozycję do human review."
        ),
    )


def _identity_readiness(record: Any | None) -> ContentEvidenceIdentityReadiness:
    if record is None:
        return ContentEvidenceIdentityReadiness(
            status="missing",
            safe_next_step="Zwiąż exact S1 identity dopiero po weryfikacji disposition.",
        )
    binding = getattr(record, "recorded_binding", getattr(record, "binding", record))
    current = getattr(record, "current", record if hasattr(record, "current_status") else None)
    if current is not None:
        current_blocker = getattr(current, "current_blocker", None)
        blockers: tuple[ContentEvidenceReadinessBlocker, ...] = (
            (_identity_current_blocker(current_blocker),)
            if current_blocker is not None
            else ()
        )
        if getattr(current, "current_status", "blocked") == "blocked" and not blockers:
            blockers = (
                _readiness_blocker(
                    "identity_current_projection_blocked",
                    "Current identity projection is blocked.",
                    next_step=getattr(
                        current,
                        "current_safe_next_step",
                        "Odśwież exact S1/classification context.",
                    ),
                ),
            )
        status: Literal["exact_current", "blocked"] = (
            "exact_current"
            if getattr(current, "current_status", "blocked") == "exact_current"
            else "blocked"
        )
        return ContentEvidenceIdentityReadiness(
            status=status,
            binding_id=getattr(binding, "binding_id", None),
            binding_digest=getattr(binding, "binding_digest", None),
            blockers=blockers,
            safe_next_step=(
                blockers[0].safe_next_step
                if blockers
                else "Exact current identity is available for the next gate."
            ),
        )
    blockers = _record_blockers((record.blocker,) if record.blocker is not None else ())
    if record.status == "reconciled_retained":
        blockers = blockers or (
            _readiness_blocker(
                "identity_not_exact_current",
                "The available identity is retained history, not exact current authority.",
                next_step="Zarejestruj exact current identity binding.",
            ),
        )
    return ContentEvidenceIdentityReadiness(
        status=record.status,
        binding_id=binding.binding_id,
        binding_digest=binding.binding_digest,
        blockers=blockers,
        safe_next_step=(
            blockers[0].safe_next_step
            if blockers
            else "Exact current identity is available for the next gate."
        ),
    )


def _identity_path(record: Any) -> str:
    binding = _identity_binding(record)
    return str(getattr(binding, "canonical_path", ""))


def _identity_binding(record: Any) -> Any:
    return getattr(record, "recorded_binding", getattr(record, "binding", record))


def _identity_recorded_at(record: Any) -> datetime:
    value = getattr(_identity_binding(record), "recorded_at", datetime.min)
    return value if isinstance(value, datetime) else datetime.min


def _identity_current_blocker(blocker: Any) -> ContentEvidenceReadinessBlocker:
    reason = str(getattr(blocker, "reason", "")).strip()
    code = (
        reason
        if re.fullmatch(r"[a-z][a-z0-9_]{0,119}", reason)
        else "identity_current_projection_blocked"
    )
    seam = str(getattr(blocker, "seam", "identity")).strip() or "identity"
    return _readiness_blocker(
        code,
        f"Current identity {seam} blocker: {reason or 'exact state unavailable'}.",
        evidence_ids=getattr(blocker, "evidence_ids", ()),
        next_step=str(
            getattr(blocker, "next_step", "Odśwież exact S1/classification context.")
        ),
    )


def _service_card_readiness(cards: tuple[Any, ...]) -> ContentEvidenceServiceCardReadiness:
    if not cards:
        return ContentEvidenceServiceCardReadiness(
            status="missing",
            blockers=(
                _readiness_blocker(
                    "service_card_missing",
                    "No exact service card is bound to this canonical path.",
                    next_step="Zwiąż i zweryfikuj exact Service Profile card.",
                ),
            ),
            safe_next_step="Zwiąż i zweryfikuj exact Service Profile card.",
        )
    if len(cards) != 1:
        blocker = _readiness_blocker(
            "service_card_ambiguous",
            "More than one service card matches this exact canonical path.",
            next_step="Rozstrzygnij exact Service Profile card przed research promotion.",
        )
        return ContentEvidenceServiceCardReadiness(
            status="blocked",
            blockers=(blocker,),
            safe_next_step=blocker.safe_next_step,
        )
    card = cards[0]
    evidence_ids = tuple(sorted(set(card.evidence_ids)))
    connectors = tuple(sorted(set(card.source_connectors)))
    if card.lifecycle_status == "approved_current":
        return ContentEvidenceServiceCardReadiness(
            status="approved_current",
            card_id=card.id,
            card_status=card.lifecycle_status,
            evidence_ids=evidence_ids,
            source_connectors=connectors,
            safe_next_step="Exact Service Profile card is current.",
        )
    blocker = _readiness_blocker(
        "service_card_review_required",
        "Exact Service Profile card is not approved_current.",
        evidence_ids=evidence_ids,
        next_step="Sprawdź i zatwierdź exact Service Profile card przez człowieka.",
    )
    return ContentEvidenceServiceCardReadiness(
        status="review_required",
        card_id=card.id,
        card_status=card.lifecycle_status,
        evidence_ids=evidence_ids,
        source_connectors=connectors,
        blockers=(blocker,),
        safe_next_step=blocker.safe_next_step,
    )


def _promotion_readiness(
    receipt: Any | None,
    *,
    identity: ContentEvidenceIdentityReadiness,
    service_card: ContentEvidenceServiceCardReadiness,
    research: ContentEvidenceResearchProposalReadiness,
    acquisition: ContentEvidenceAcquisitionReadiness,
    path: str,
) -> ContentEvidencePromotionReadiness:
    if receipt is not None:
        source_fact = receipt.source_fact
        if _promotion_receipt_is_current(
            receipt,
            path=path,
            identity=identity,
            service_card=service_card,
            acquisition=acquisition,
        ):
            if source_fact.review_status == "approved":
                return ContentEvidencePromotionReadiness(
                    status="approved_current",
                    receipt_id=receipt.receipt_id,
                    source_fact_id=source_fact.source_id,
                    safe_next_step="Approved source fact is available for exact selection.",
                )
            if source_fact.review_status == "rejected":
                blocker = _readiness_blocker(
                    "promotion_rejected",
                    "The source-fact promotion receipt was rejected by human review.",
                    next_step="Pozyskaj nowe credible evidence i rozpocznij osobny review.",
                )
                return ContentEvidencePromotionReadiness(
                    status="rejected",
                    receipt_id=receipt.receipt_id,
                    source_fact_id=source_fact.source_id,
                    blockers=(blocker,),
                    safe_next_step=blocker.safe_next_step,
                )
        blocker = _readiness_blocker(
            "promotion_receipt_stale",
            "The promotion receipt is not current for this exact URL and evidence.",
            next_step="Odśwież research proposal i wykonaj nowy promotion review.",
        )
        return ContentEvidencePromotionReadiness(
            status="blocked",
            receipt_id=receipt.receipt_id,
            source_fact_id=source_fact.source_id,
            blockers=(blocker,),
            safe_next_step=blocker.safe_next_step,
        )
    if identity.status != "exact_current":
        blocker = _readiness_blocker(
            "promotion_identity_required",
            "Promotion requires exact current identity binding.",
            next_step="Najpierw zwiąż exact current identity binding.",
        )
    elif service_card.status != "approved_current":
        blocker = service_card.blockers[0]
    elif research.status == "ready_for_review":
        blocker = _readiness_blocker(
            "promotion_review_required",
            "Research proposal remains review-only and has no approved source-fact receipt.",
            next_step="Przeprowadź canonical human review promotion source factu.",
        )
    elif research.status == "blocked":
        blocker = research.blockers[0]
    else:
        blocker = _readiness_blocker(
            "promotion_research_missing",
            "Promotion cannot start without a current research proposal.",
            next_step="Najpierw uzyskaj review-only research proposal.",
        )
    return ContentEvidencePromotionReadiness(
        status=(
            "review_required"
            if blocker.code == "promotion_review_required"
            else "blocked"
        ),
        blockers=(blocker,),
        safe_next_step=blocker.safe_next_step,
    )


def _promotion_receipt_is_current(
    receipt: Any,
    *,
    path: str,
    identity: ContentEvidenceIdentityReadiness,
    service_card: ContentEvidenceServiceCardReadiness,
    acquisition: ContentEvidenceAcquisitionReadiness,
) -> bool:
    snapshot = receipt.snapshot
    source_fact = receipt.source_fact
    return all(
        (
            _path_from_reference(snapshot.source_url) == path,
            identity.status == "exact_current",
            snapshot.identity_binding_id == identity.binding_id,
            service_card.status == "approved_current",
            snapshot.target_card_id == service_card.card_id,
            acquisition.current_status == "ready_for_researcher",
            snapshot.acquisition_run_id == acquisition.run_id,
            snapshot.acquisition_run_digest == acquisition.run_digest,
            source_fact.target_card_id == snapshot.target_card_id,
            bool(source_fact.evidence_ids),
        )
    )


def _receipt_readiness_blocker(
    readiness: ContentEvidenceAuthoringInventoryReceiptReadiness,
) -> ContentEvidenceReadinessBlocker:
    if readiness.status == "missing":
        return _readiness_blocker(
            "authoring_inventory_receipt_missing",
            "No current authoring inventory receipt exists for this URL.",
            next_step="Zarejestruj exact current authoring inventory receipt.",
        )
    return _readiness_blocker(
        "authoring_inventory_receipt_stale",
        "Authoring inventory receipt is stale or no longer matches current catalog.",
        evidence_ids=_optional_ids((readiness.evidence_id,)),
        next_step="Odśwież exact authoring inventory receipt.",
    )


def _readiness_blocker(
    code: str,
    reason: str,
    *,
    evidence_ids: Iterable[str] = (),
    next_step: str,
) -> ContentEvidenceReadinessBlocker:
    return ContentEvidenceReadinessBlocker(
        code=code,
        reason=reason,
        evidence_ids=tuple(sorted({item for item in evidence_ids if item})),
        safe_next_step=next_step,
    )


def _record_blockers(records: Iterable[Any]) -> tuple[ContentEvidenceReadinessBlocker, ...]:
    return tuple(
        _readiness_blocker(
            str(getattr(record, "code", "record_blocked")),
            str(getattr(record, "reason", "Canonical record is blocked.")),
            evidence_ids=getattr(record, "evidence_ids", ()),
            next_step=str(
                getattr(record, "safe_next_step", "Sprawdź i usuń exact blocker.")
            ),
        )
        for record in records
    )


def _unique_blockers(
    blockers: Iterable[ContentEvidenceReadinessBlocker],
) -> tuple[ContentEvidenceReadinessBlocker, ...]:
    unique: dict[str, ContentEvidenceReadinessBlocker] = {}
    for blocker in blockers:
        unique.setdefault(blocker.code, blocker)
    return tuple(unique.values())


def _optional_ids(values: Iterable[str | None]) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if value}))


def _observation_evidence_ids(observation: Any | None) -> tuple[str, ...]:
    if observation is None:
        return ()
    return tuple(sorted({item for item in observation.evidence_ids if item}))


def _summarize_content_evidence_readiness(
    readiness: Iterable[ContentEvidenceReadiness],
) -> ContentEvidenceReadinessSummary:
    readiness = list(readiness)
    return ContentEvidenceReadinessSummary(
        total_count=len(readiness),
        blocked_count=sum(item.status == "blocked" for item in readiness),
        review_required_count=sum(item.status == "review_required" for item in readiness),
        ready_for_researcher_count=sum(
            item.status == "ready_for_researcher" for item in readiness
        ),
        missing_count=sum(item.status == "missing" for item in readiness),
        authoring_receipt_current_count=sum(
            item.authoring_inventory_receipt.status == "current" for item in readiness
        ),
        authoring_receipt_stale_count=sum(
            item.authoring_inventory_receipt.status == "stale" for item in readiness
        ),
        authoring_receipt_missing_count=sum(
            item.authoring_inventory_receipt.status == "missing" for item in readiness
        ),
        acquisition_ready_count=sum(
            item.evidence_acquisition.current_status == "ready_for_researcher"
            for item in readiness
        ),
        acquisition_blocked_count=sum(
            item.evidence_acquisition.current_status == "blocked" for item in readiness
        ),
        acquisition_missing_count=sum(
            item.evidence_acquisition.current_status == "missing" for item in readiness
        ),
        research_ready_count=sum(
            item.research_proposal.status == "ready_for_review" for item in readiness
        ),
        research_blocked_count=sum(
            item.research_proposal.status == "blocked" for item in readiness
        ),
        research_missing_count=sum(
            item.research_proposal.status == "missing" for item in readiness
        ),
        identity_exact_current_count=sum(
            item.identity.status == "exact_current" for item in readiness
        ),
        identity_blocked_count=sum(
            item.identity.status in {"blocked", "reconciled_retained"}
            for item in readiness
        ),
        identity_missing_count=sum(
            item.identity.status == "missing" for item in readiness
        ),
        service_card_approved_current_count=sum(
            item.service_card.status == "approved_current" for item in readiness
        ),
        service_card_review_required_count=sum(
            item.service_card.status == "review_required" for item in readiness
        ),
        promotion_approved_current_count=sum(
            item.promotion.status == "approved_current" for item in readiness
        ),
    )
__all__ = [
    "ContentEvidenceAcquisitionReadiness",
    "ContentEvidenceAuthoringInventoryReceiptReadiness",
    "ContentEvidenceIdentityReadiness",
    "ContentEvidencePromotionReadiness",
    "ContentEvidenceReadiness",
    "ContentEvidenceReadinessBlocker",
    "ContentEvidenceReadinessStore",
    "ContentEvidenceReadinessSummary",
    "ContentEvidenceResearchProposalReadiness",
    "ContentEvidenceServiceCardReadiness",
    "ContentInventoryJournalCatalogObservation",
    "ContentInventoryJournalReadiness",
    "ContentInventoryJournalReadinessRow",
    "build_content_inventory_journal_readiness",
    "empty_content_evidence_readiness_summary",
    "project_content_evidence_readiness",
]


empty_content_evidence_readiness_summary = _empty_evidence_readiness_summary
