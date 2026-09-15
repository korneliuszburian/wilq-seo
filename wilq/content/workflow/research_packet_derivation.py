"""Server-owned derivation of exact research-packet semantic fields."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from wilq.content.canonical.urls import content_normalized_path
from wilq.content.knowledge.source_facts import ContentSourceFact, ekologus_source_facts
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding
from wilq.content.workflow.research_packet_contracts import (
    ContentResearchPacketBlocker,
    ContentResearchPacketCommand,
    ContentResearchPacketContextReceipt,
    ContentResearchPacketFreshness,
    ContentResearchPacketInternalLink,
)
from wilq.content.workflow.source_pack_binding import ContentSourcePackBinding


def build_server_owned_research_packet_command(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    planning_input: ContentPlanningInput,
    source_pack: ContentSourcePackBinding,
    identity: ContentDeliveryIdentityBinding,
    now: datetime,
) -> ContentResearchPacketCommand | ContentResearchPacketBlocker:
    """Build packet input exclusively from current typed WILQ projections."""

    if planning_input.work_item_id != identity.current_work_item_id:
        return _blocker(
            "work_item_identity",
            "work_item_mismatch",
            identity.inventory_evidence_ids,
            "Planning input musi należeć do bieżącego work itemu identity.",
        )
    brief = snapshot.sales_brief.sales_brief_result.brief
    if brief is None:
        return _blocker(
            "intent",
            "intent_missing",
            tuple(snapshot.preflight.item.evidence_ids),
            "Odśwież zaakceptowany brief przed packetem.",
        )
    facts = _selected_facts(source_pack)
    if facts is None:
        return _blocker(
            "source_facts",
            "source_fact_not_registered",
            source_pack.evidence_ids,
            "Odśwież source-fact registry i source-pack względem bieżących faktów.",
        )
    evidence_ids = _packet_evidence_ids(
        source_pack=source_pack,
        identity=identity,
        planning_input=planning_input,
        facts=facts,
        brief=brief,
    )
    cta_destination = _cta_destination(snapshot, brief)
    internal_links = _internal_links(planning_input)
    context = _context_receipt(
        snapshot=snapshot,
        planning_input=planning_input,
        source_pack=source_pack,
        identity=identity,
        facts=facts,
        brief=brief,
        cta_destination=cta_destination,
        evidence_ids=evidence_ids,
        **_evidence_partitions(
            source_pack=source_pack,
            identity=identity,
            planning_input=planning_input,
            facts=facts,
            brief=brief,
        ),
    )


    blocked_claims, freshness = _fact_lineage(source_pack, facts)
    return ContentResearchPacketCommand(
        source_pack_binding_id=source_pack.binding_id,
        source_pack_binding_digest=source_pack.binding_digest,
        identity_binding_id=identity.binding_id,
        identity_binding_digest=identity.binding_digest,
        current_work_item_id=identity.current_work_item_id,
        content_kind=planning_input.content_kind,
        intent=planning_input.search_intent,
        query_cluster=_query_cluster(planning_input),
        canonical_owner=identity.canonical_path,
        target_audience=planning_input.target_reader,
        buyer_problem=planning_input.buyer_problem,
        buyer_trigger=planning_input.buyer_trigger,
        approved_source_fact_ids=tuple(sorted(source_pack.source_fact_ids)),
        blocked_claims=blocked_claims,
        evidence_ids=evidence_ids,
        freshness=freshness,
        legal_source_requirements=_legal_requirements(planning_input),
        cta_destination=cta_destination,
        internal_links=internal_links,
        context_receipt=context,
        recorded_by="planning_proposal_prepare",
        recorded_at=now,
    )


def _evidence_partitions(
    *,
    source_pack: ContentSourcePackBinding,
    identity: ContentDeliveryIdentityBinding,
    planning_input: ContentPlanningInput,
    facts: tuple[ContentSourceFact, ...],
    brief: Any,
) -> dict[str, tuple[str, ...]]:
    return {
        "source_pack_evidence_ids": tuple(
            sorted(
                {
                    *source_pack.evidence_ids,
                    *source_pack.source_fact_registry_receipt.evidence_ids,
                }
            )
        ),
        "source_fact_evidence_ids": tuple(
            sorted({evidence_id for fact in facts for evidence_id in fact.evidence_ids})
        ),
        "demand_evidence_ids": tuple(sorted(planning_input.query_portfolio.evidence_ids)),
        "measurement_evidence_ids": tuple(
            sorted(
                {
                    *planning_input.measurement_baseline_evidence_ids,
                    *(
                        evidence_id
                        for comparison in planning_input.metric_comparisons
                        for evidence_id in comparison.evidence_ids
                    ),
                }
            )
        ),
        "verified_link_evidence_ids": tuple(
            sorted(
                {
                    evidence_id
                    for candidate in planning_input.internal_link_candidates
                    for evidence_id in candidate.evidence_ids
                }
            )
        ),
        "cta_evidence_ids": tuple(sorted(brief.evidence_ids)),
        "regulatory_evidence_ids": tuple(
            sorted(
                {
                    *planning_input.regulatory_coverage.evidence_ids,
                    *(
                        evidence_id
                        for fact in planning_input.regulatory_coverage.source_facts
                        for evidence_id in fact.evidence_ids
                    ),
                }
            )
        ),
        "planning_evidence_ids": tuple(
            sorted(identity.inventory_evidence_ids)
        ),
    }


def _selected_facts(source_pack: ContentSourcePackBinding) -> tuple[ContentSourceFact, ...] | None:
    facts_by_id = {fact.source_id: fact for fact in ekologus_source_facts()}
    selected = tuple(facts_by_id.get(source_id) for source_id in source_pack.source_fact_ids)
    if any(fact is None for fact in selected):
        return None
    return tuple(fact for fact in selected if fact is not None)


def _query_cluster(planning_input: ContentPlanningInput) -> tuple[str, ...]:
    demand_rows = [
        *planning_input.query_portfolio.gsc_query_rows,
        *planning_input.query_portfolio.ads_term_rows,
        *planning_input.query_portfolio.keyword_planner_rows,
    ]
    return tuple(sorted({row.term.strip() for row in demand_rows if row.term.strip()}))


def _packet_evidence_ids(
    *,
    source_pack: ContentSourcePackBinding,
    identity: ContentDeliveryIdentityBinding,
    planning_input: ContentPlanningInput,
    facts: tuple[ContentSourceFact, ...],
    brief: Any,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                *source_pack.evidence_ids,
                *source_pack.source_fact_registry_receipt.evidence_ids,
                *identity.inventory_evidence_ids,
                *planning_input.query_portfolio.evidence_ids,
                *(evidence_id for fact in facts for evidence_id in fact.evidence_ids),
                *planning_input.regulatory_coverage.evidence_ids,
                *(
                    evidence_id
                    for candidate in planning_input.internal_link_candidates
                    for evidence_id in candidate.evidence_ids
                ),
                *brief.evidence_ids,
            }
        )
    )


def _internal_links(
    planning_input: ContentPlanningInput,
) -> tuple[ContentResearchPacketInternalLink, ...]:
    return tuple(
        ContentResearchPacketInternalLink(
            destination_path=content_normalized_path(candidate.target_url),
            anchor_text=candidate.anchor_hint,
            relation="next_step" if index == 0 else "supporting",
            verification="exact_verified",
        )
        for index, candidate in enumerate(planning_input.internal_link_candidates)
    )


def _context_receipt(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    planning_input: ContentPlanningInput,
    source_pack: ContentSourcePackBinding,
    identity: ContentDeliveryIdentityBinding,
    facts: tuple[ContentSourceFact, ...],
    brief: Any,
    cta_destination: str,
    evidence_ids: tuple[str, ...],
    source_pack_evidence_ids: tuple[str, ...],
    source_fact_evidence_ids: tuple[str, ...],
    demand_evidence_ids: tuple[str, ...],
    measurement_evidence_ids: tuple[str, ...],
    verified_link_evidence_ids: tuple[str, ...],
    cta_evidence_ids: tuple[str, ...],
    regulatory_evidence_ids: tuple[str, ...],
    planning_evidence_ids: tuple[str, ...],
) -> ContentResearchPacketContextReceipt:
    return ContentResearchPacketContextReceipt(
        classification_run_id=identity.classification_run_id,
        classification_run_digest=identity.classification_run_digest,
        classification_source_row_digest=identity.classification_source_row_digest,
        identity_binding_id=identity.binding_id,
        identity_binding_digest=identity.binding_digest,
        source_fact_authority_receipt_id=source_pack.source_fact_authority_receipt_id,
        source_fact_authority_receipt_digest=source_pack.source_fact_authority_receipt_digest,
        source_fact_authority_snapshot_digest=source_pack.source_fact_authority_snapshot_digest,
        source_fact_authority_provenance_digest=source_pack.source_fact_authority_provenance_digest,
        service_card_id=planning_input.confirmed_service_card_id,
        service_semantic_digest=_digest(snapshot.service_profile_context),
        brief_semantic_digest=_digest(brief),
        demand_evidence_digest=_digest(planning_input.query_portfolio),
        verified_links_digest=_digest(planning_input.internal_link_candidates),
        regulatory_coverage_digest=_digest(planning_input.regulatory_coverage),
        freshness_digest=_digest(
            {
                "assessment": snapshot.freshness_assessment,
                "source_facts": [
                    {"source_id": fact.source_id, "freshness_date": fact.freshness_date}
                    for fact in facts
                ],
                "registry_checked_at": source_pack.source_fact_registry_receipt.checked_at,
            }
        ),
        cta_destination=cta_destination,
        evidence_ids=evidence_ids,
        source_pack_evidence_ids=source_pack_evidence_ids,
        source_fact_evidence_ids=source_fact_evidence_ids,
        demand_evidence_ids=demand_evidence_ids,
        measurement_evidence_ids=measurement_evidence_ids,
        verified_link_evidence_ids=verified_link_evidence_ids,
        cta_evidence_ids=cta_evidence_ids,
        regulatory_evidence_ids=regulatory_evidence_ids,
        planning_evidence_ids=planning_evidence_ids,
    )


def _fact_lineage(
    source_pack: ContentSourcePackBinding,
    facts: tuple[ContentSourceFact, ...],
) -> tuple[tuple[str, ...], tuple[ContentResearchPacketFreshness, ...]]:
    blocked_claims = tuple(sorted({claim for fact in facts for claim in fact.blocked_claims}))
    checked_at = source_pack.source_fact_registry_receipt.checked_at
    freshness = tuple(
        ContentResearchPacketFreshness(
            source_id=fact.source_id,
            evidence_ids=tuple(sorted(set(fact.evidence_ids))),
            checked_at=checked_at,
            status="fresh",
        )
        for fact in facts
    )
    return blocked_claims, freshness


def _cta_destination(snapshot: ContentWorkItemWorkflowSnapshotResponse, brief: Any) -> str:
    return str(
        getattr(brief, "cta_destination", None)
        or getattr(snapshot.service_profile_context, "cta_destination", None)
        or ""
    ).strip()


def _legal_requirements(planning_input: ContentPlanningInput) -> tuple[str, ...]:
    coverage = planning_input.regulatory_coverage
    if coverage.applicability_status == "not_required":
        return ("none_identified",)
    if coverage.complete and coverage.requirements:
        return tuple(sorted(item.id for item in coverage.requirements))
    return ()


def _digest(value: object) -> str:
    return canonical_json_digest(_jsonable(value))


def _jsonable(value: object) -> object:
    if isinstance(value, BaseModel):
        return _jsonable(value.model_dump(mode="json"))
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _blocker(
    seam: str,
    reason: str,
    evidence_ids: tuple[str, ...],
    next_step: str,
) -> ContentResearchPacketBlocker:
    return ContentResearchPacketBlocker(
        seam=seam,  # type: ignore[arg-type]
        reason=reason,  # type: ignore[arg-type]
        evidence_ids=tuple(sorted(set(evidence_ids))),
        next_step_pl=next_step,
    )


__all__ = ["build_server_owned_research_packet_command"]
