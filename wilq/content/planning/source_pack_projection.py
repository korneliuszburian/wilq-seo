"""Server-owned projection of one exact selected source-pack fact set.

The source-pack receipt contains identifiers and digests, never source text.  A
consumer must therefore hydrate the selected, approved facts from the current
registry before constructing a packet context or a model turn.  Keeping that
operation here prevents prepare, read/revalidation and generation from slowly
acquiring different fact-selection rules.
"""

from __future__ import annotations

from collections.abc import Collection
from typing import TYPE_CHECKING

from wilq.content.canonical.urls import content_normalized_path
from wilq.content.claims.ledger import (
    ContentClaimLedger,
    ContentClaimLedgerEntry,
    claim_ledger_blockers,
)
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.input_sources import (
    ContentPlanningSourceFact,
    ContentPlanningSourceProvenance,
)
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    regulatory_content_coverage,
    regulatory_content_profile,
)
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.source_pack_v2 import SourcePackV2Fact

if TYPE_CHECKING:
    from wilq.content.planning.dynamic_input import ContentPlanningInput


def project_selected_source_pack_facts(
    planning_input: ContentPlanningInput,
    source_fact_ids: Collection[str],
    source_facts: Collection[ContentSourceFact],
) -> ContentPlanningInput:
    """Replace caller fact payload with the exact approved registry projection.

    ``source_fact_ids`` is the allow-list from the persisted source-pack.  The
    registry is the only authority for text, evidence, provenance and
    regulatory bindings.  IDs must already be the sorted, unique source-pack
    representation; silently sorting or accepting a partial set would make a
    stale/caller-built pack look current.
    """

    selected_ids = tuple(source_fact_ids)
    if not selected_ids or selected_ids != tuple(sorted(set(selected_ids))):
        raise ValueError("Selected source-pack fact IDs must be sorted and unique.")
    registry = tuple(source_facts)
    registry_by_id = {fact.source_id: fact for fact in registry}
    if len(registry_by_id) != len(registry):
        raise ValueError("Source-fact registry contains duplicate source IDs.")
    selected = tuple(registry_by_id.get(source_id) for source_id in selected_ids)
    if any(fact is None for fact in selected):
        raise ValueError("Selected source-pack fact is not registered.")
    approved = tuple(fact for fact in selected if fact is not None)
    if any(fact.review_status != "approved" for fact in approved):
        raise ValueError("Selected source-pack facts must be approved.")
    if any(not fact.evidence_ids or not fact.source_connectors for fact in approved):
        raise ValueError("Selected source-pack facts require evidence and connectors.")
    if getattr(planning_input, "content_kind", "service") != "editorial":
        # Service planning has a separate refresh-authorization digest.  This
        # editorial-path slice must not rewrite that service input while it is
        # merely carrying a packet through the existing service lifecycle.
        return planning_input

    projected_facts = [
        ContentPlanningSourceFact(
            fact_id=f"planning_source_pack_fact_{fact.source_id}",
            summary=fact.extracted_fact,
            source_connector=fact.source_connectors[0],
            evidence_ids=list(dict.fromkeys(fact.evidence_ids)),
            source_fact_ids=[fact.source_id],
            # SourceFact has no source-material authority.  In particular, do
            # not copy the selected service profile's material IDs onto legal
            # facts merely because both are used by this page.
            source_material_ids=[],
            regulatory_requirement_ids=sorted(set(fact.regulatory_requirement_ids)),
        )
        for fact in approved
    ]
    provenance = [
        ContentPlanningSourceProvenance(
            source_fact_id=fact.source_id,
            source_url_or_path=fact.source_url_or_path,
            freshness_date=fact.freshness_date,
            reviewer=fact.reviewer,
            evidence_ids=list(dict.fromkeys(fact.evidence_ids)),
        )
        for fact in approved
    ]
    coverage = _regulatory_coverage(planning_input, approved)
    payload = planning_input.model_copy(
        update={
            "source_facts": projected_facts,
            "source_provenance": provenance,
            "regulatory_coverage": coverage,
            "evidence_ids": _project_evidence_ids(planning_input, approved),
            "source_connectors": list(
                dict.fromkeys(
                    [
                        *planning_input.source_connectors,
                        *(fact.source_connectors[0] for fact in approved),
                    ]
                )
            ),
        }
    )
    return _recompute_digest(payload)


def project_research_packet_v2_facts(
    planning_input: ContentPlanningInput,
    selected_facts: Collection[SourcePackV2Fact],
    source_facts: Collection[ContentSourceFact],
) -> ContentPlanningInput:
    """Hydrate only exact preview facts from the current registry for packet v2."""
    selected = tuple(selected_facts)
    selected_ids = tuple(fact.source_fact_id for fact in selected)
    if not selected or selected_ids != tuple(sorted(set(selected_ids))):
        raise ValueError("Selected v2 packet fact IDs must be sorted, unique and non-empty.")
    registry = tuple(source_facts)
    registry_by_id = {fact.source_id: fact for fact in registry}
    if len(registry_by_id) != len(registry):
        raise ValueError("Source-fact registry contains duplicate source IDs.")

    current: list[ContentSourceFact] = []
    for packet_fact in selected:
        fact = registry_by_id.get(packet_fact.source_fact_id)
        if fact is None:
            raise ValueError("Selected v2 packet fact is not registered.")
        if fact.review_status != "approved" or fact.privacy_class != "commit_safe":
            raise ValueError("Selected v2 packet fact is not approved and commit-safe.")
        if not fact.evidence_ids or not fact.source_connectors:
            raise ValueError("Selected v2 packet fact requires evidence and connectors.")
        exact = (
            canonical_json_digest(fact.model_dump(mode="json")) == packet_fact.fact_digest
            and fact.extracted_fact == packet_fact.text
            and fact.source_url_or_path == packet_fact.source_reference
            and fact.source_type == packet_fact.source_type
            and fact.freshness_date == packet_fact.freshness_date
            and tuple(sorted(set(fact.source_connectors))) == packet_fact.source_connectors
            and tuple(sorted(set(fact.evidence_ids))) == packet_fact.evidence_ids
        )
        if not exact:
            raise ValueError("Selected v2 packet fact differs from the current registry.")
        current.append(fact)

    approved = tuple(current)
    payload = planning_input.model_copy(
        update={
            "source_facts": _planning_facts(approved),
            "source_provenance": _planning_provenance(approved),
            "claim_ledger": _project_v2_claims(planning_input, approved),
            "regulatory_coverage": _v2_regulatory_coverage(planning_input, approved),
            "evidence_ids": _project_v2_evidence_ids(planning_input, approved),
            "source_connectors": _project_v2_connectors(planning_input, approved),
        }
    )
    return _recompute_digest(payload)


def _planning_facts(
    source_facts: tuple[ContentSourceFact, ...],
) -> list[ContentPlanningSourceFact]:
    return [
        ContentPlanningSourceFact(
            fact_id=f"planning_source_pack_fact_{fact.source_id}",
            summary=fact.extracted_fact,
            source_connector=sorted(set(fact.source_connectors))[0],
            evidence_ids=list(dict.fromkeys(fact.evidence_ids)),
            source_fact_ids=[fact.source_id],
            source_material_ids=[],
            regulatory_requirement_ids=sorted(set(fact.regulatory_requirement_ids)),
        )
        for fact in source_facts
    ]


def _planning_provenance(
    source_facts: tuple[ContentSourceFact, ...],
) -> list[ContentPlanningSourceProvenance]:
    return [
        ContentPlanningSourceProvenance(
            source_fact_id=fact.source_id,
            source_url_or_path=fact.source_url_or_path,
            freshness_date=fact.freshness_date,
            reviewer=fact.reviewer,
            evidence_ids=list(dict.fromkeys(fact.evidence_ids)),
        )
        for fact in source_facts
    ]


def _project_v2_claims(
    planning_input: ContentPlanningInput,
    selected: tuple[ContentSourceFact, ...],
) -> list[ContentClaimLedgerEntry]:
    selected_evidence = {evidence for fact in selected for evidence in fact.evidence_ids}
    selected_connectors = {
        connector for fact in selected for connector in fact.source_connectors
    }
    inconsistent_ids = {
        blocker.claim_id
        for blocker in claim_ledger_blockers(
            ContentClaimLedger(
                id="research_packet_v2_projection",
                work_item_id=planning_input.work_item_id,
                entries=planning_input.claim_ledger,
            )
        )
    }
    approved: list[ContentClaimLedgerEntry] = []
    for claim in planning_input.claim_ledger:
        supported = (
            claim.status == "allowed_with_evidence"
            and claim.id not in inconsistent_ids
            and bool(claim.evidence_ids)
            and set(claim.evidence_ids).issubset(selected_evidence)
            and bool(claim.source_connectors)
            and set(claim.source_connectors).issubset(selected_connectors)
        )
        if supported:
            approved.append(claim)
        elif claim.required and claim.status in {"allowed_with_evidence", "allowed_general"}:
            raise ValueError("Required planning claim is outside selected v2 packet facts.")
    return approved


def _v2_regulatory_coverage(
    planning_input: ContentPlanningInput,
    selected: tuple[ContentSourceFact, ...],
) -> ContentRegulatoryCoverage:
    content_kind = getattr(planning_input, "content_kind", "service")
    service_card_id = None
    canonical_path = None
    if content_kind == "service":
        service_card_id = getattr(planning_input, "confirmed_service_card_id", None)
    else:
        canonical_path = content_normalized_path(
            getattr(planning_input, "final_canonical_url", None)
        )
    return regulatory_content_coverage(
        service_card_id=service_card_id,
        canonical_path=canonical_path,
        source_facts=selected,
    )


def _project_v2_evidence_ids(
    planning_input: ContentPlanningInput,
    selected: tuple[ContentSourceFact, ...],
) -> list[str]:
    caller_fact_evidence = {
        evidence_id
        for fact in planning_input.source_facts
        for evidence_id in fact.evidence_ids
    }
    selected_evidence = {evidence_id for fact in selected for evidence_id in fact.evidence_ids}
    independent_evidence = set(planning_input.inventory.evidence_ids)
    independent_evidence.update(
        evidence_id
        for section in planning_input.inventory.sections
        for evidence_id in section.evidence_ids
    )
    independent_evidence.update(
        evidence_id
        for assessment in planning_input.source_assessments
        for evidence_id in assessment.evidence_ids
    )
    independent_evidence.update(planning_input.query_portfolio.evidence_ids)
    independent_evidence.update(planning_input.query_portfolio.optional_ads_evidence_ids)
    independent_evidence.update(
        evidence_id
        for row in (
            planning_input.query_portfolio.gsc_query_rows
            + planning_input.query_portfolio.ads_term_rows
            + planning_input.query_portfolio.keyword_planner_rows
        )
        for evidence_id in row.evidence_ids
    )
    independent_evidence.update(
        evidence_id
        for candidate in planning_input.internal_link_candidates
        for evidence_id in candidate.evidence_ids
    )
    independent_evidence.update(planning_input.measurement_baseline_evidence_ids)
    return list(
        dict.fromkeys(
            [
                evidence_id
                for evidence_id in planning_input.evidence_ids
                if evidence_id not in caller_fact_evidence
                or evidence_id in selected_evidence
                or evidence_id in independent_evidence
            ]
            + [evidence_id for fact in selected for evidence_id in fact.evidence_ids]
        )
    )


def _project_v2_connectors(
    planning_input: ContentPlanningInput,
    selected: tuple[ContentSourceFact, ...],
) -> list[str]:
    caller_fact_connectors = {fact.source_connector for fact in planning_input.source_facts}
    selected_connectors = {connector for fact in selected for connector in fact.source_connectors}
    independent_connectors = set(planning_input.inventory.source_connectors)
    independent_connectors.update(planning_input.query_portfolio.source_connectors)
    return list(
        dict.fromkeys(
            [
                connector
                for connector in planning_input.source_connectors
                if connector not in caller_fact_connectors
                or connector in selected_connectors
                or connector in independent_connectors
            ]
            + [connector for fact in selected for connector in fact.source_connectors]
        )
    )


def _regulatory_coverage(
    planning_input: ContentPlanningInput,
    selected: tuple[ContentSourceFact, ...],
) -> ContentRegulatoryCoverage:
    content_kind = getattr(planning_input, "content_kind", "service")
    if content_kind != "editorial":
        # This slice owns the explicit BDO editorial canonical-path binding.
        # Existing service planning already resolves its service profile; do
        # not reinterpret that separate subject while projecting a pack.
        return planning_input.regulatory_coverage
    service_card_id = None
    canonical_path = content_normalized_path(getattr(planning_input, "final_canonical_url", None))
    profile = regulatory_content_profile(
        service_card_id=service_card_id,
        canonical_path=canonical_path,
    )
    if profile is None:
        # An editorial page is not regulated by default.  Crucially, this is
        # not a runtime blessing of an arbitrary profile or empty path.
        return ContentRegulatoryCoverage()
    return regulatory_content_coverage(
        service_card_id=service_card_id,
        canonical_path=canonical_path,
        source_facts=selected,
    )


def _project_evidence_ids(
    planning_input: ContentPlanningInput,
    selected: tuple[ContentSourceFact, ...],
) -> list[str]:
    selected_evidence = {evidence_id for fact in selected for evidence_id in fact.evidence_ids}
    caller_fact_evidence = {
        evidence_id
        for fact in planning_input.source_facts
        if fact.source_fact_ids
        for evidence_id in fact.evidence_ids
    }
    return list(
        dict.fromkeys(
            [
                evidence_id
                for evidence_id in planning_input.evidence_ids
                if evidence_id not in caller_fact_evidence or evidence_id in selected_evidence
            ]
            + [fact_evidence for fact in selected for fact_evidence in fact.evidence_ids]
        )
    )


def _recompute_digest(planning_input: ContentPlanningInput) -> ContentPlanningInput:
    from wilq.content.planning.dynamic_input import _digest

    payload = planning_input.model_dump(mode="json")
    payload.pop("planning_input_digest", None)
    digest = _digest(
        {
            "schema_name": planning_input.schema_name,
            "criteria_version": planning_input.criteria_version,
            "inventory_mapping_policy": planning_input.inventory_mapping_policy,
            **payload,
        }
    )
    return planning_input.model_copy(update={"planning_input_digest": digest})


__all__ = [
    "project_research_packet_v2_facts",
    "project_selected_source_pack_facts",
]
