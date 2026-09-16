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


__all__ = ["project_selected_source_pack_facts"]
