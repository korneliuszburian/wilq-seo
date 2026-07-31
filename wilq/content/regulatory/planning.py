from __future__ import annotations

from wilq.content.planning.input_sources import ContentPlanningSourceFact
from wilq.content.regulatory.policy import ContentRegulatoryCoverage


def regulatory_planning_source_facts(
    coverage: ContentRegulatoryCoverage,
    *,
    knowledge_card_ids: list[str],
    source_material_ids: list[str],
) -> list[ContentPlanningSourceFact]:
    """Materialise exact official coverage into the model's source allowlist."""

    covered_by_fact = {
        source_fact_id: sorted(
            {
                item.requirement_id
                for item in coverage.requirement_coverage
                if source_fact_id in item.source_fact_ids
            }
        )
        for source_fact_id in coverage.source_fact_ids
    }
    return [
        ContentPlanningSourceFact(
            fact_id=f"planning_regulatory_fact_{fact.source_id}",
            summary=fact.extracted_fact,
            source_connector=fact.source_connectors[0],
            evidence_ids=fact.evidence_ids,
            knowledge_card_ids=knowledge_card_ids,
            source_fact_ids=[fact.source_id],
            source_material_ids=source_material_ids,
            regulatory_requirement_ids=covered_by_fact[fact.source_id],
        )
        for fact in coverage.source_facts
        if fact.source_connectors and fact.evidence_ids and covered_by_fact.get(fact.source_id)
    ]
