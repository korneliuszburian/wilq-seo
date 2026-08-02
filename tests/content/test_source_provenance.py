from __future__ import annotations

from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.planning.input_sources import (
    ContentPlanningSourceFact,
    build_source_provenance,
)


def test_planning_provenance_preserves_approved_source_lineage() -> None:
    source = next(
        fact
        for fact in ekologus_source_facts()
        if "bdo" in fact.source_id and fact.review_status == "approved"
    )

    provenance = build_source_provenance(
        [
            ContentPlanningSourceFact(
                fact_id="planning_fact_01",
                summary=source.extracted_fact,
                source_connector="public_site",
                evidence_ids=source.evidence_ids,
                source_fact_ids=[source.source_id],
            )
        ]
    )

    assert len(provenance) == 1
    assert provenance[0].source_fact_id == source.source_id
    assert provenance[0].source_url_or_path == source.source_url_or_path
    assert provenance[0].freshness_date == source.freshness_date
    assert provenance[0].reviewer == source.reviewer
    assert provenance[0].evidence_ids == source.evidence_ids


def test_planning_provenance_does_not_invent_unknown_source_identity() -> None:
    provenance = build_source_provenance(
        [
            ContentPlanningSourceFact(
                fact_id="planning_fact_unknown",
                summary="Nieznany fakt",
                source_connector="public_site",
                evidence_ids=["ev_unknown"],
                source_fact_ids=["source_fact_unknown"],
            )
        ]
    )

    assert provenance == []
