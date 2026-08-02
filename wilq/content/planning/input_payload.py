from __future__ import annotations

from collections.abc import Callable

from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceCandidate,
    ContentWorkItemServiceProfileContext,
)
from wilq.content.measurement.aggregates import MeasurementPeriodComparison
from wilq.content.planning.input_sources import (
    ContentPlanningInventory,
    ContentPlanningSourceAssessment,
    ContentPlanningSourceFact,
    build_source_provenance,
    planning_source_connectors,
    usable_query_portfolio,
)
from wilq.content.planning.internal_link_candidates import ContentPlanningInternalLinkCandidate
from wilq.content.regulatory.policy import ContentRegulatoryCoverage
from wilq.content.workflow.models import ContentWorkItem
from wilq.content.workflow.planning import ContentPlanningProposal


def refresh_planning_payload(
    *,
    item: ContentWorkItem,
    service_profile: ContentWorkItemServiceProfileContext,
    candidate: ContentWorkItemServiceCandidate,
    brief: ContentSalesBrief,
    baseline: ContentPlanningProposal,
    inventory: ContentPlanningInventory,
    source_facts: list[ContentPlanningSourceFact],
    source_assessments: list[ContentPlanningSourceAssessment],
    regulatory_coverage: ContentRegulatoryCoverage,
    claim_ledger: ContentClaimLedger,
    metric_comparisons: list[MeasurementPeriodComparison],
    evidence_ids: list[str],
    internal_link_candidates_loader: Callable[
        [list[str], list[str]], list[ContentPlanningInternalLinkCandidate]
    ],
) -> dict[str, object]:
    query_portfolio = usable_query_portfolio(baseline.search_demand, source_assessments)
    internal_link_candidates = internal_link_candidates_loader(
        brief.internal_link_direction,
        evidence_ids,
    )
    return {
        "work_item_id": item.id,
        "final_canonical_url": brief.final_canonical_url,
        "service_candidates": service_profile.service_candidates,
        "confirmed_service_card_id": candidate.service_card_id,
        "service_label": candidate.service_label,
        "inventory": inventory,
        "internal_link_candidates": internal_link_candidates,
        "target_reader": brief.target_reader,
        "buyer_problem": brief.buyer_problem,
        "buyer_trigger": brief.buyer_trigger,
        "search_intent": brief.search_intent,
        "source_facts": source_facts,
        "source_provenance": build_source_provenance(source_facts),
        "source_assessments": source_assessments,
        "regulatory_coverage": regulatory_coverage,
        "query_portfolio": query_portfolio,
        "claim_ledger": claim_ledger.entries,
        "measurement_metrics": brief.measurement_plan.metrics_to_watch,
        "metric_comparisons": metric_comparisons,
        "measurement_baseline_evidence_ids": [
            evidence_id
            for evidence_id in brief.measurement_plan.baseline_evidence_ids
            if evidence_id in evidence_ids
        ],
        "measurement_observation_rule": brief.measurement_plan.earliest_verdict_note,
        "measurement_success_claim_rule": brief.measurement_plan.success_claim_rule,
        "knowledge_card_ids": brief.knowledge_card_ids,
        "evidence_ids": evidence_ids,
        "source_connectors": planning_source_connectors(
            inventory=inventory,
            service_profile=service_profile,
            demand=query_portfolio,
            source_facts=source_facts,
            assessments=source_assessments,
        ),
        "baseline_cta_direction": baseline.cta_direction,
    }
