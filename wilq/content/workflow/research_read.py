"""Ask-scoped research read over the existing exact per-URL evidence seams."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.canonical.urls import content_normalized_path
from wilq.content.knowledge.cards import ContentKnowledgeCard
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.current_page_identity_v3 import (
    CurrentPageIdentityV3Response,
    resolve_current_page_identity_v3,
)
from wilq.content.workflow.intake import (
    DEMAND_CONNECTOR_IDS,
    WORDPRESS_CONNECTOR_ID,
    ContentIntakeQueueItem,
)
from wilq.content.workflow.source_fact_candidate_v3 import (
    ContentSourceFactCandidateV3Projection,
    build_content_source_fact_candidates_v3_projection,
)

DEMAND_OWNER = "WILQ demand evidence"
COMPETITOR_OWNER = "WILQ competitor evidence"
COMPETITOR_CONNECTOR_ID = "ahrefs"
_HEX64 = r"^[0-9a-f]{64}$"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContentResearchReadFact(_FrozenModel):
    source_fact_id: str = Field(min_length=1, max_length=240)
    fact_digest: str = Field(pattern=_HEX64)
    source_type: str = Field(min_length=1)
    source_url: str = Field(min_length=1, max_length=2048)
    language: Literal["unknown"] = "unknown"
    freshness_date: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    authority: Literal["official", "reviewed"]
    review_status: Literal["approved"] = "approved"
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    source_connectors: tuple[str, ...] = Field(min_length=1)
    target_card_id: str = Field(min_length=1, max_length=240)
    deterministic_origin: Literal["exact_canonical_path", "exact_service_card_binding"]

    @model_validator(mode="after")
    def require_sorted_evidence(self) -> Self:
        if self.evidence_ids != tuple(sorted(set(self.evidence_ids))):
            raise ValueError("Research read evidence IDs must be sorted and unique.")
        return self


class ContentResearchReadBlockedSource(_FrozenModel):
    source_fact_id: str = Field(min_length=1, max_length=240)
    review_status: str = Field(min_length=1)
    source_url: str = Field(min_length=1, max_length=2048)
    evidence_ids: tuple[str, ...] = ()
    reason_code: Literal["source_fact_review_required"] = "source_fact_review_required"
    blocker_owner: str = Field(min_length=1)
    safe_next_step: str = Field(min_length=1)


class ContentResearchReadBlocker(_FrozenModel):
    code: str = Field(min_length=1, max_length=160)
    owner: str = Field(min_length=1, max_length=160)
    detail: str = Field(min_length=1, max_length=600)


class ContentResearchReadClaimGate(_FrozenModel):
    claim: Literal["demand", "competitor"]
    allowed: Literal[False] = False
    code: str = Field(min_length=1, max_length=160)
    owner: str = Field(min_length=1, max_length=160)
    detail: str = Field(min_length=1, max_length=600)


class ContentResearchReadResponse(_FrozenModel):
    schema_version: Literal["wilq_content_research_read_v1"] = "wilq_content_research_read_v1"
    queue_id: str = Field(min_length=1, max_length=240)
    work_item_id: str | None = Field(default=None, max_length=240)
    status: Literal["ready", "blocked"]
    page_url: str | None = Field(default=None, max_length=2048)
    canonical_path: str | None = Field(default=None, max_length=2048)
    identity_id: str | None = Field(default=None, max_length=240)
    facts: tuple[ContentResearchReadFact, ...] = ()
    blocked_sources: tuple[ContentResearchReadBlockedSource, ...] = ()
    blockers: tuple[ContentResearchReadBlocker, ...] = ()
    claim_gates: tuple[ContentResearchReadClaimGate, ...] = ()
    research_packet_created: Literal[False] = False
    action_created: Literal[False] = False
    generation_allowed: Literal[False] = False
    safe_next_step: str = Field(min_length=1, max_length=600)

    @model_validator(mode="after")
    def require_exact_read_shape(self) -> Self:
        if self.status == "blocked" and (not self.blockers or self.facts):
            raise ValueError("Blocked research reads need a blocker and no accepted facts.")
        if self.status == "ready" and not self.facts:
            raise ValueError("Ready research reads need at least one accepted fact.")
        if len({blocker.code for blocker in self.blockers}) != len(self.blockers):
            raise ValueError("Research read blockers must be unique.")
        if len({gate.claim for gate in self.claim_gates}) != len(self.claim_gates):
            raise ValueError("Research read claim gates must be unique.")
        return self


def resolve_content_research_read(
    store: Any,
    queue_id: str,
    *,
    evidence_loader: Callable[[str], CurrentPageEvidenceResponse],
    source_facts_loader: Callable[[], tuple[ContentSourceFact, ...]],
    cards_loader: Callable[[], tuple[ContentKnowledgeCard, ...]],
    connector_freshness: Mapping[str, str],
) -> ContentResearchReadResponse | None:
    """Resolve one ask-scoped research read, or None when the queue item is missing."""

    item = store.load_content_intake_request(queue_id)
    if item is None or not isinstance(item, ContentIntakeQueueItem):
        return None
    facts = source_facts_loader()
    identity = None
    candidates = None
    if len(item.candidate_work_item_ids) == 1:
        work_item_id = item.candidate_work_item_ids[0]
        identity = resolve_current_page_identity_v3(
            work_item_id, evidence_loader(work_item_id)
        )
        candidates = build_content_source_fact_candidates_v3_projection(
            identity=identity,
            facts=facts,
            cards=cards_loader(),
        )
    return build_content_research_read(
        queue_item=item,
        identity=identity,
        candidates=candidates,
        source_facts=facts,
        connector_freshness=connector_freshness,
    )


def build_content_research_read(
    *,
    queue_item: ContentIntakeQueueItem,
    identity: CurrentPageIdentityV3Response | None,
    candidates: ContentSourceFactCandidateV3Projection | None,
    source_facts: Sequence[ContentSourceFact],
    connector_freshness: Mapping[str, str],
) -> ContentResearchReadResponse:
    """Join one accepted ask with the exact page's reviewed sources only.

    The read never creates a research packet, ActionObject, plan or draft and
    never turns stale or unverified sources into demand or competitor claims.
    """

    if len(queue_item.candidate_work_item_ids) != 1:
        code = (
            "research_target_missing"
            if not queue_item.candidate_work_item_ids
            else "research_target_ambiguous"
        )
        return _blocked_read(
            queue_item,
            code,
            "WILQ content workflow",
            (
                "Prośba nie ma dokładnie jednego bieżącego work itemu do odczytu researchu."
            ),
            (
                "Doprecyzuj prośbę do jednego istniejącego adresu albo work itemu."
            ),
        )
    work_item_id = queue_item.candidate_work_item_ids[0]
    if identity is None or identity.status != "exact_current":
        return _blocked_read(
            queue_item,
            str(getattr(identity, "blocker_code", "research_identity_not_current")),
            str(getattr(identity, "blocker_owner", "WILQ content workflow")),
            "Bieżąca tożsamość strony nie jest exact current.",
            str(
                getattr(
                    identity,
                    "safe_next_step",
                    "Odczytaj ponownie exact materiał i tożsamość strony.",
                )
            ),
            work_item_id=work_item_id,
        )
    if candidates is None or candidates.status != "eligible":
        return _blocked_read(
            queue_item,
            str(getattr(candidates, "blocker_code", "research_candidates_blocked")),
            str(getattr(candidates, "blocker_owner", "WILQ content workflow")),
            "Zatwierdzone fakty źródłowe dla tej strony nie są gotowe.",
            str(
                getattr(
                    candidates,
                    "safe_next_step",
                    "Zatwierdź exact fakty źródłowe dla tej strony.",
                )
            ),
            work_item_id=work_item_id,
            page_url=identity.page_url,
            canonical_path=identity.canonical_path,
            identity_id=identity.identity_id,
            blocked_sources=_blocked_sources(
                identity.canonical_path,
                source_facts,
                service_card_id=_service_card_id(candidates),
            ),
        )
    by_id = {fact.source_id: fact for fact in source_facts}
    facts = _registered_facts(candidates, by_id)
    if facts is None:
        return _blocked_read(
            queue_item,
            "research_fact_binding_missing",
            "WILQ content workflow",
            "Zatwierdzony kandydat nie ma dokładnego wpisu w rejestrze źródeł.",
            "Odczytaj ponownie rejestr źródeł i powiązania tej strony.",
            work_item_id=work_item_id,
            page_url=identity.page_url,
            canonical_path=identity.canonical_path,
            identity_id=identity.identity_id,
        )
    return ContentResearchReadResponse(
        queue_id=queue_item.queue_id,
        work_item_id=work_item_id,
        status="ready",
        page_url=identity.page_url,
        canonical_path=identity.canonical_path,
        identity_id=identity.identity_id,
        facts=facts,
        blocked_sources=_blocked_sources(
            identity.canonical_path,
            source_facts,
            service_card_id=_service_card_id(candidates),
        ),
        claim_gates=_claim_gates(connector_freshness),
        safe_next_step="Otwórz review briefu na tych zatwierdzonych źródłach; bez generacji.",
    )


def _registered_facts(
    candidates: ContentSourceFactCandidateV3Projection,
    facts_by_id: Mapping[str, ContentSourceFact],
) -> tuple[ContentResearchReadFact, ...] | None:
    mapped: list[ContentResearchReadFact] = []
    for candidate in candidates.candidates:
        registered = facts_by_id.get(candidate.source_fact_id)
        if registered is None:
            return None
        mapped.append(
            ContentResearchReadFact(
                source_fact_id=candidate.source_fact_id,
                fact_digest=candidate.fact_digest,
                source_type=candidate.source_type,
                source_url=registered.source_url_or_path,
                freshness_date=candidate.freshness_date,
                scope=candidate.scope,
                authority="official" if registered.official_source else "reviewed",
                evidence_ids=candidate.evidence_ids,
                source_connectors=candidate.source_connectors,
                target_card_id=candidate.target_card_id,
                deterministic_origin=candidate.deterministic_origin,
            )
        )
    return tuple(mapped)


def _service_card_id(
    candidates: ContentSourceFactCandidateV3Projection | None,
) -> str | None:
    if candidates is None or candidates.service_binding is None:
        return None
    return candidates.service_binding.card_id


def _blocked_sources(
    canonical_path: str | None,
    source_facts: Sequence[ContentSourceFact],
    *,
    service_card_id: str | None,
) -> tuple[ContentResearchReadBlockedSource, ...]:
    if not canonical_path:
        return ()
    normalized = content_normalized_path(canonical_path).casefold()
    blocked = [
        fact
        for fact in source_facts
        if fact.review_status != "approved"
        and (
            any(
                content_normalized_path(path).casefold() == normalized
                for path in fact.applicable_canonical_paths
            )
            or (
                service_card_id is not None
                and (
                    fact.target_card_id == service_card_id
                    or service_card_id in fact.applicable_service_card_ids
                )
            )
        )
    ]
    return tuple(
        ContentResearchReadBlockedSource(
            source_fact_id=fact.source_id,
            review_status=fact.review_status,
            source_url=fact.source_url_or_path,
            evidence_ids=tuple(sorted(set(fact.evidence_ids))),
            blocker_owner="Wilku",
            safe_next_step="Zatwierdź exact fakt źródłowy dla tej strony przed briefem.",
        )
        for fact in sorted(blocked, key=lambda item: item.source_id)
    )


def _claim_gates(
    connector_freshness: Mapping[str, str],
) -> tuple[ContentResearchReadClaimGate, ...]:
    gates: list[ContentResearchReadClaimGate] = []
    stale_demand = tuple(
        connector_id
        for connector_id in DEMAND_CONNECTOR_IDS
        if connector_freshness.get(connector_id) != "fresh"
    )
    if stale_demand or connector_freshness.get(WORDPRESS_CONNECTOR_ID) != "fresh":
        gates.append(
            ContentResearchReadClaimGate(
                claim="demand",
                code="demand_evidence_not_fresh",
                owner=DEMAND_OWNER,
                detail="Bez świeżych danych popytu: nie tworzę claimu popytowego.",
            )
        )
    if connector_freshness.get(COMPETITOR_CONNECTOR_ID) != "fresh":
        gates.append(
            ContentResearchReadClaimGate(
                claim="competitor",
                code="competitor_evidence_not_fresh",
                owner=COMPETITOR_OWNER,
                detail="Bez świeżych danych konkurencji: nie tworzę claimu konkurencyjnego.",
            )
        )
    return tuple(gates)


def _blocked_read(
    queue_item: ContentIntakeQueueItem,
    code: str,
    owner: str,
    detail: str,
    safe_next_step: str,
    *,
    work_item_id: str | None = None,
    page_url: str | None = None,
    canonical_path: str | None = None,
    identity_id: str | None = None,
    blocked_sources: tuple[ContentResearchReadBlockedSource, ...] = (),
) -> ContentResearchReadResponse:
    return ContentResearchReadResponse(
        queue_id=queue_item.queue_id,
        work_item_id=work_item_id,
        status="blocked",
        page_url=page_url,
        canonical_path=canonical_path,
        identity_id=identity_id,
        blocked_sources=blocked_sources,
        blockers=(ContentResearchReadBlocker(code=code, owner=owner, detail=detail),),
        safe_next_step=safe_next_step,
    )


__all__ = [
    "ContentResearchReadBlocker",
    "ContentResearchReadBlockedSource",
    "ContentResearchReadClaimGate",
    "ContentResearchReadFact",
    "ContentResearchReadResponse",
    "build_content_research_read",
    "resolve_content_research_read",
]
