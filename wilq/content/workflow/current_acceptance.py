"""Snapshot-bound per-URL acceptance over the current public inventory."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, cast

from wilq.content.workflow.content_kind import classify_content_kind_from_inventory
from wilq.content.workflow.current_acceptance_contracts import (
    CurrentAcceptanceBlocked,
    CurrentAcceptanceRow,
    CurrentAcceptanceSnapshot,
    CurrentAcceptanceWave,
    CurrentPageMaterialStatus,
    current_acceptance_wave_counts,
    current_acceptance_wave_digest,
)
from wilq.content.workflow.current_acceptance_snapshot import (
    current_acceptance_snapshot_is_current,
)
from wilq.content.workflow.current_inventory_reconciliation import (
    CurrentInventoryScopeRow,
)
from wilq.content.workflow.current_page_evidence import (
    CurrentPageEvidenceResponse,
    resolve_current_page_evidence,
)
from wilq.content.workflow.current_page_identity_v3 import (
    CurrentPageIdentityV3Response,
    resolve_current_page_identity_v3,
)
from wilq.content.workflow.material_review import MaterialReviewStore
from wilq.content.workflow.per_url_decision_authority import (
    ContentPerUrlDecisionAuthorityBlocked,
    ContentPerUrlDecisionObservation,
    ContentPerUrlDecisionPolicyFacts,
    ContentPerUrlPolicyFact,
    build_content_per_url_decision_observation,
)
from wilq.content.workflow.source_fact_candidate_v3 import (
    ContentSourceFactCandidateV3Projection,
    build_content_source_fact_candidates_v3_projection,
)
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
)
from wilq.schemas.core import utc_now


def build_current_acceptance_wave(
    *,
    run_id: str,
    snapshot: CurrentAcceptanceSnapshot,
    rows: Sequence[CurrentAcceptanceRow],
    started_at: datetime,
    completed_at: datetime,
) -> CurrentAcceptanceWave:
    canonical_rows = tuple(sorted(rows, key=lambda row: row.canonical_path))
    payload: dict[str, object] = {
        "schema_version": "wilq_current_acceptance_wave_v1",
        "run_id": run_id,
        "source_snapshot_digest": snapshot.source_snapshot_digest,
        "inventory_evidence_ids": snapshot.scope.inventory_evidence_ids,
        "started_at": started_at,
        "completed_at": completed_at,
        "counts": current_acceptance_wave_counts(canonical_rows),
        "rows": canonical_rows,
        "generation_allowed": False,
    }
    digest = current_acceptance_wave_digest(payload)
    return CurrentAcceptanceWave.model_validate(
        payload
        | {
            "wave_id": f"content_current_acceptance_wave_{digest[:24]}",
            "wave_digest": digest,
        }
    )


def execute_current_acceptance_run(
    run_id: str,
    snapshot: CurrentAcceptanceSnapshot,
    *,
    store_factory: Callable[[], Any],
) -> None:
    """Read every pinned URL, then atomically persist its observations and sealed wave."""

    store = store_factory()
    attempt = store.mark_current_acceptance_running(run_id)
    if attempt is None or attempt.status != "running":
        return
    started_at = attempt.created_at
    rows: list[CurrentAcceptanceRow] = []
    observations: list[ContentPerUrlDecisionObservation] = []
    try:
        for scope_row in snapshot.scope.rows:
            try:
                row, observation = observe_current_acceptance_url(
                    run_id=run_id,
                    scope_row=scope_row,
                    snapshot=snapshot,
                    store=store,
                )
            except Exception:
                row = _blocked_row(
                    scope_row,
                    "current_acceptance_row_invalid",
                    "WILQ content workflow",
                    "Ponów exact odczyt tej strony i sprawdź aktualne powiązania źródeł.",
                )
                observation = None
            rows.append(row)
            if observation is not None:
                observations.append(observation)
        if not current_acceptance_snapshot_is_current(snapshot):
            rows = _superseded_rows(snapshot.scope.rows)
            observations = []
        wave = build_current_acceptance_wave(
            run_id=run_id,
            snapshot=snapshot,
            rows=rows,
            started_at=started_at,
            completed_at=utc_now(),
        )
        store.record_current_acceptance_wave(wave, tuple(observations))
    except CurrentAcceptanceBlocked as blocker:
        store.fail_current_acceptance_attempt(
            run_id,
            blocker.code,
            blocker.owner,
            blocker.safe_next_step,
        )
    except Exception:
        store.fail_current_acceptance_attempt(
            run_id,
            "current_acceptance_worker_failed",
            "WILQ content workflow",
            "Sprawdź stan źródeł i uruchom nową próbę z nowym request ID.",
        )


@dataclass(frozen=True)
class _ExactCurrentPageInputs:
    page: CurrentPageEvidenceResponse
    identity: CurrentPageIdentityV3Response
    catalog_item: ContentInventoryCatalogItem


def observe_current_acceptance_url(
    *,
    run_id: str,
    scope_row: CurrentInventoryScopeRow,
    snapshot: CurrentAcceptanceSnapshot,
    store: MaterialReviewStore,
    read_time: datetime | None = None,
) -> tuple[CurrentAcceptanceRow, ContentPerUrlDecisionObservation | None]:
    """Observe one exact page and classify only from pinned, reviewed source inputs."""
    if scope_row.disposition == "excluded":
        return _scope_excluded(scope_row), None
    if scope_row.disposition == "blocked":
        return _scope_blocked(scope_row), None
    work_item_id = scope_row.current_work_item_id
    if work_item_id is None:
        return _blocked_row(
            scope_row,
            "current_acceptance_work_item_binding_missing",
            "WILQ content workflow",
            "Uzupełnij dokładne powiązanie URL-a z bieżącym work-itemem.",
        ), None
    page_inputs = _resolve_current_page_inputs(scope_row, snapshot, store, work_item_id)
    if isinstance(page_inputs, CurrentAcceptanceRow):
        return page_inputs, None
    page, identity, item = (
        page_inputs.page,
        page_inputs.identity,
        page_inputs.catalog_item,
    )
    try:
        candidates, content_kind = _current_source_candidates(identity, item, snapshot)
    except Exception:
        return _blocked_row(
            scope_row,
            "current_acceptance_source_projection_failed",
            "WILQ content workflow",
            "Odczytaj ponownie exact page i zatwierdzone źródła tej strony.",
            identity=identity,
            page=page,
        ), None
    if content_kind is None:
        return _blocked_row(
            scope_row,
            "current_acceptance_content_kind_unsupported",
            "WILQ content workflow",
            "Ustal exact typ tej strony przed klasyfikacją contentu.",
            identity=identity,
            page=page,
            candidates=candidates,
        ), None
    if candidates.status != "eligible":
        return _blocked_row(
            scope_row,
            candidates.blocker_code or "source_fact_candidates_blocked",
            candidates.blocker_owner or "WILQ content workflow",
            candidates.safe_next_step,
            identity=identity,
            page=page,
            candidates=candidates,
        ), None
    observed_at = _aware_read_time(read_time)
    try:
        policy, service_card_id, observation = _create_current_page_observation(
            run_id=run_id,
            identity=identity,
            content_kind=content_kind,
            candidates=candidates,
            snapshot=snapshot,
            observed_at=observed_at,
        )
    except (CurrentAcceptanceBlocked, ContentPerUrlDecisionAuthorityBlocked) as blocker:
        return _blocked_from_source_error(
            scope_row, page, identity, candidates, blocker
        ), None
    row, persist_observation = _classify_current_acceptance_row(
            scope_row=scope_row,
            page=page,
            identity=identity,
            candidates=candidates,
            policy=policy,
            observation=observation,
            service_card_id=service_card_id,
        )
    return (
        row,
        observation if persist_observation else None,
    )


def _resolve_current_page_inputs(
    scope_row: CurrentInventoryScopeRow,
    snapshot: CurrentAcceptanceSnapshot,
    store: MaterialReviewStore,
    work_item_id: str,
) -> _ExactCurrentPageInputs | CurrentAcceptanceRow:
    try:
        page = resolve_current_page_evidence(
            work_item_id=work_item_id,
            catalog=snapshot.catalog,
            latest_wordpress_evidence_ids=snapshot.wordpress_evidence_ids,
            wordpress_freshness_state=snapshot.freshness_state,
            store=store,
        )
    except Exception:
        return _blocked_row(
            scope_row,
            "current_acceptance_page_read_failed",
            "WILQ WordPress connector",
            "Ponów dokładny odczyt bieżącego materiału tej strony.",
        )
    identity = resolve_current_page_identity_v3(work_item_id, page)
    if identity.status != "exact_current":
        return _blocked_from_identity(scope_row, identity)
    if (
        identity.canonical_path != scope_row.canonical_path
        or identity.page_url != scope_row.public_url
        or identity.work_item_id != work_item_id
    ):
        return _blocked_row(
            scope_row,
            "current_acceptance_page_identity_mismatch",
            "WILQ content workflow",
            "Odczytaj ponownie exact URL i work-item z bieżącego katalogu.",
            identity=identity,
        )
    matches = [item for item in snapshot.catalog.items if item.work_item_id == work_item_id]
    if len(matches) != 1:
        return _blocked_row(
            scope_row,
            "current_acceptance_catalog_item_ambiguous",
            "WILQ content workflow",
            "Napraw dokładne, pojedyncze powiązanie work-itemu z katalogiem.",
            identity=identity,
        )
    return _ExactCurrentPageInputs(page, identity, matches[0])


def _current_source_candidates(
    identity: CurrentPageIdentityV3Response,
    item: ContentInventoryCatalogItem,
    snapshot: CurrentAcceptanceSnapshot,
) -> tuple[
    ContentSourceFactCandidateV3Projection,
    Literal["editorial", "service", "landing_or_hub"] | None,
]:
    candidates = build_content_source_fact_candidates_v3_projection(
        identity=identity,
        facts=snapshot.source_facts,
        cards=snapshot.knowledge_cards,
        checked_at=snapshot.captured_at,
    )
    _, content_kind = classify_content_kind_from_inventory(
        item.content_type,
        public_url=item.url,
        dev_objects=[(obj.url, obj.content_type) for obj in snapshot.catalog.rest_content_objects],
    )
    if content_kind not in {"editorial", "service", "landing_or_hub"}:
        return candidates, None
    return candidates, cast(Literal["editorial", "service", "landing_or_hub"], content_kind)


def _create_current_page_observation(
    *,
    run_id: str,
    identity: CurrentPageIdentityV3Response,
    content_kind: Literal["editorial", "service", "landing_or_hub"],
    candidates: ContentSourceFactCandidateV3Projection,
    snapshot: CurrentAcceptanceSnapshot,
    observed_at: datetime,
) -> tuple[
    ContentPerUrlDecisionPolicyFacts,
    str | None,
    ContentPerUrlDecisionObservation,
]:
    policy, service_card_id = _policy_facts(
        identity=identity,
        content_kind=content_kind,
        candidate_projection=candidates,
        snapshot=snapshot,
    )
    observation = build_content_per_url_decision_observation(
        identity,
        policy,
        observed_at=observed_at,
        source_wave_id=run_id,
    )
    return policy, service_card_id, observation


def _classify_current_acceptance_row(
    *,
    scope_row: CurrentInventoryScopeRow,
    page: CurrentPageEvidenceResponse,
    identity: CurrentPageIdentityV3Response,
    candidates: ContentSourceFactCandidateV3Projection,
    policy: ContentPerUrlDecisionPolicyFacts,
    observation: ContentPerUrlDecisionObservation,
    service_card_id: str | None,
) -> tuple[CurrentAcceptanceRow, bool]:
    evidence_ids = _row_evidence_ids(page, identity, candidates, policy)
    source_fact_ids = tuple(sorted(fact.source_fact_id for fact in policy.source_facts))
    if not _candidate_matches_identity(candidates, identity) or not source_fact_ids:
        return (
            _blocked_row(
                scope_row,
                "current_acceptance_source_binding_mismatch",
                "WILQ content workflow",
                "Odczytaj ponownie źródła zatwierdzone dla dokładnej strony.",
                identity=identity,
                page=page,
                candidates=candidates,
                service_card_id=service_card_id,
                evidence_ids=evidence_ids,
            ),
            False,
        )
    page_status = cast(CurrentPageMaterialStatus, page.status)
    decision: Literal["keep", "refresh"] = (
        "keep" if page_status == "reviewed_material_current" else "refresh"
    )
    return CurrentAcceptanceRow(
        canonical_path=scope_row.canonical_path,
        public_url=scope_row.public_url,
        scope_disposition="eligible",
        decision=decision,
        current_work_item_id=scope_row.current_work_item_id,
        page_material_status=page_status,
        identity_id=identity.identity_id,
        identity_digest=identity.identity_digest,
        page_evidence_digest=identity.evidence_digest,
        observation_id=observation.observation_id,
        observation_digest=observation.observation_digest,
        semantic_row_digest=observation.semantic_row_digest,
        service_card_id=service_card_id,
        source_fact_ids=source_fact_ids,
        evidence_ids=evidence_ids,
        safe_next_step=(
            "Zachowaj exact, aktualnie reviewed materiał; dalsza zmiana wymaga osobnej decyzji."
            if decision == "keep"
            else "Otwórz review exact page i zatwierdzonych faktów; bez publikacji."
        ),
    ), True


def _blocked_from_source_error(
    scope_row: CurrentInventoryScopeRow,
    page: CurrentPageEvidenceResponse,
    identity: CurrentPageIdentityV3Response,
    candidates: ContentSourceFactCandidateV3Projection,
    blocker: CurrentAcceptanceBlocked | ContentPerUrlDecisionAuthorityBlocked,
) -> CurrentAcceptanceRow:
    return _blocked_row(
        scope_row,
        getattr(blocker, "code", "per_url_policy_facts_invalid"),
        getattr(blocker, "owner", "WILQ content workflow"),
        getattr(blocker, "safe_next_step", "Odczytaj ponownie exact źródła i freshness strony."),
        identity=identity,
        page=page,
        candidates=candidates,
    )


def _aware_read_time(read_time: datetime | None) -> datetime:
    observed_at = read_time or utc_now()
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("Current acceptance observation time must be timezone-aware.")
    return observed_at.astimezone(UTC)


def _policy_facts(
    *,
    identity: CurrentPageIdentityV3Response,
    content_kind: Literal["editorial", "service", "landing_or_hub"],
    candidate_projection: ContentSourceFactCandidateV3Projection,
    snapshot: CurrentAcceptanceSnapshot,
) -> tuple[ContentPerUrlDecisionPolicyFacts, str | None]:
    binding = candidate_projection.service_binding
    service_card_id = None if binding is None else binding.card_id
    if content_kind == "service" and not service_card_id:
        raise CurrentAcceptanceBlocked(
            "service_binding_missing",
            "WILQ content workflow",
            "Utwórz exact reviewed powiązanie strony z profilem usługi.",
        )
    facts_by_id = {fact.source_id: fact for fact in snapshot.source_facts}
    if content_kind != "service" and any(
        candidate.deterministic_origin == "exact_service_card_binding"
        for candidate in candidate_projection.candidates
    ):
        raise CurrentAcceptanceBlocked(
            "source_fact_service_binding_not_allowed_for_content_kind",
            "WILQ content workflow",
            "Dla strony editorial lub landing użyj wyłącznie exact page-bound source facts.",
        )
    policy_facts: list[ContentPerUrlPolicyFact] = []
    regulatory_profiles: set[tuple[str, str]] = set()
    for candidate in candidate_projection.candidates:
        source_fact = facts_by_id.get(candidate.source_fact_id)
        if source_fact is None:
            raise CurrentAcceptanceBlocked(
                "source_fact_registry_binding_missing",
                "WILQ content workflow",
                "Odczytaj ponownie dokładne zatwierdzone fakty źródłowe.",
            )
        if source_fact.regulatory_profile_id and source_fact.regulatory_profile_version:
            regulatory_profiles.add(
                (source_fact.regulatory_profile_id, source_fact.regulatory_profile_version)
            )
        policy_facts.append(
            ContentPerUrlPolicyFact(
                source_fact_id=candidate.source_fact_id,
                semantic_digest=candidate.fact_digest,
                requirement_ids=tuple(sorted(set(source_fact.regulatory_requirement_ids))),
                evidence_ids=tuple(sorted(set(candidate.evidence_ids))),
            )
        )
    if len(regulatory_profiles) > 1:
        raise CurrentAcceptanceBlocked(
            "source_fact_regulatory_profile_conflict",
            "WILQ content workflow",
            "Uzgodnij jeden current regulatory profile przed klasyfikacją tej strony.",
        )
    regulatory_profile = next(iter(regulatory_profiles), None)
    requirement_ids = tuple(
        sorted({item for fact in policy_facts for item in fact.requirement_ids})
    )
    policy = ContentPerUrlDecisionPolicyFacts(
        current_work_item_id=identity.work_item_id,
        public_url=identity.page_url or "",
        canonical_path=identity.canonical_path or "",
        policy_id="wilq_current_acceptance_v1",
        policy_version="1",
        content_kind=content_kind,
        service_card_id=service_card_id if content_kind == "service" else None,
        regulatory_profile_id=None if regulatory_profile is None else regulatory_profile[0],
        regulatory_profile_version=(
            None if regulatory_profile is None else regulatory_profile[1]
        ),
        source_facts=tuple(sorted(policy_facts, key=lambda item: item.source_fact_id)),
        requirement_ids=requirement_ids,
        freshness_assessment=snapshot.freshness_assessment,
        freshness_connector_ids=("wordpress_ekologus",),
        freshness_evidence_ids=snapshot.scope.inventory_evidence_ids,
    )
    return policy, service_card_id


def _candidate_matches_identity(
    projection: ContentSourceFactCandidateV3Projection,
    identity: CurrentPageIdentityV3Response,
) -> bool:
    return (
        projection.work_item_id == identity.work_item_id
        and projection.page_url == identity.page_url
        and projection.canonical_path == identity.canonical_path
        and projection.identity_id == identity.identity_id
        and projection.identity_digest == identity.identity_digest
        and projection.evidence_digest == identity.evidence_digest
        and bool(projection.candidates)
        and projection.service_binding is not None
        and projection.service_binding.status == "exact_bound"
    )


def _row_evidence_ids(
    page: CurrentPageEvidenceResponse,
    identity: CurrentPageIdentityV3Response,
    candidates: ContentSourceFactCandidateV3Projection,
    policy: ContentPerUrlDecisionPolicyFacts,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            set(page.current_evidence_ids)
            | set(page.catalog_evidence_ids)
            | set(identity.current_evidence_ids)
            | set(identity.catalog_evidence_ids)
            | set(candidates.registry_evidence_ids)
            | set(candidates.blocker_evidence_ids)
            | set(policy.freshness_evidence_ids)
            | {evidence_id for fact in policy.source_facts for evidence_id in fact.evidence_ids}
        )
    )


def _blocked_from_identity(
    scope_row: CurrentInventoryScopeRow,
    identity: CurrentPageIdentityV3Response,
) -> CurrentAcceptanceRow:
    return _blocked_row(
        scope_row,
        identity.blocker_code or "current_page_identity_blocked",
        identity.blocker_owner or "WILQ content workflow",
        identity.safe_next_step,
        evidence_ids=(
            *identity.current_evidence_ids,
            *identity.catalog_evidence_ids,
            *scope_row.source_evidence_ids,
            *scope_row.catalog_evidence_ids,
        ),
    )


def _blocked_row(
    scope_row: CurrentInventoryScopeRow,
    code: str,
    owner: str,
    safe_next_step: str,
    *,
    identity: CurrentPageIdentityV3Response | None = None,
    page: CurrentPageEvidenceResponse | None = None,
    candidates: ContentSourceFactCandidateV3Projection | None = None,
    observation: ContentPerUrlDecisionObservation | None = None,
    service_card_id: str | None = None,
    source_fact_ids: tuple[str, ...] = (),
    evidence_ids: tuple[str, ...] = (),
) -> CurrentAcceptanceRow:
    combined_evidence = set(evidence_ids)
    combined_evidence.update(scope_row.source_evidence_ids)
    combined_evidence.update(scope_row.catalog_evidence_ids)
    if identity is not None:
        combined_evidence.update(identity.current_evidence_ids)
        combined_evidence.update(identity.catalog_evidence_ids)
    if page is not None:
        combined_evidence.update(page.current_evidence_ids)
        combined_evidence.update(page.catalog_evidence_ids)
    if candidates is not None:
        combined_evidence.update(candidates.registry_evidence_ids)
        combined_evidence.update(candidates.blocker_evidence_ids)
    return CurrentAcceptanceRow(
        canonical_path=scope_row.canonical_path,
        public_url=scope_row.public_url,
        scope_disposition=scope_row.disposition,
        decision="blocked",
        current_work_item_id=scope_row.current_work_item_id,
        page_material_status=None if page is None or page.status == "blocked" else page.status,
        identity_id=None if identity is None else identity.identity_id,
        identity_digest=None if identity is None else identity.identity_digest,
        page_evidence_digest=None if identity is None else identity.evidence_digest,
        observation_id=None if observation is None else observation.observation_id,
        observation_digest=None if observation is None else observation.observation_digest,
        semantic_row_digest=None if observation is None else observation.semantic_row_digest,
        service_card_id=service_card_id,
        source_fact_ids=tuple(sorted(set(source_fact_ids))),
        evidence_ids=tuple(sorted(item for item in combined_evidence if item.strip())),
        blocker_code=code,
        blocker_owner=owner,
        safe_next_step=safe_next_step,
    )


def _scope_excluded(scope_row: CurrentInventoryScopeRow) -> CurrentAcceptanceRow:
    assert scope_row.reason_code is not None
    return CurrentAcceptanceRow(
        canonical_path=scope_row.canonical_path,
        public_url=scope_row.public_url,
        scope_disposition="excluded",
        decision="excluded",
        reason_code=scope_row.reason_code,
        evidence_ids=scope_row.source_evidence_ids,
        safe_next_step=scope_row.safe_next_step,
    )


def _scope_blocked(scope_row: CurrentInventoryScopeRow) -> CurrentAcceptanceRow:
    assert scope_row.blocker_code is not None and scope_row.blocker_owner is not None
    return _blocked_row(
        scope_row,
        scope_row.blocker_code,
        scope_row.blocker_owner,
        scope_row.safe_next_step,
    )


def _superseded_rows(
    scope_rows: Sequence[CurrentInventoryScopeRow],
) -> list[CurrentAcceptanceRow]:
    result: list[CurrentAcceptanceRow] = []
    for row in scope_rows:
        if row.disposition == "excluded":
            result.append(_scope_excluded(row))
        else:
            result.append(
                _blocked_row(
                    row,
                    "current_acceptance_source_snapshot_superseded",
                    "WILQ content workflow",
                    "Uruchom nową kwalifikację na jednym niezmienionym snapshotcie źródeł.",
                )
            )
    return result


__all__ = [
    "CurrentAcceptanceRow",
    "CurrentAcceptanceSnapshot",
    "CurrentAcceptanceWave",
    "build_current_acceptance_wave",
    "execute_current_acceptance_run",
    "observe_current_acceptance_url",
]
