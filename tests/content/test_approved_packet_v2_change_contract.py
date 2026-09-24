"""Counterfactual observer for exact v2 fact projection into the planner."""

from __future__ import annotations

import wilq.content.planning.source_pack_projection as projection
from tests.content.test_selected_source_pack_projection import _fact, _planning_input
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.source_pack_v2 import SourcePackV2Fact


def test_planner_projects_only_exact_approved_v2_packet_facts() -> None:
    selected = _fact("selected_packet_fact")
    foreign = _fact("foreign_packet_fact")
    planning_input = _planning_input(selected, foreign).model_copy(
        update={"content_kind": "service"}
    )
    packet_fact = SourcePackV2Fact(
        source_fact_id=selected.source_id,
        fact_digest=canonical_json_digest(selected.model_dump(mode="json")),
        text=selected.extracted_fact,
        source_reference=selected.source_url_or_path,
        freshness_date=selected.freshness_date,
        source_type=selected.source_type,
        source_connectors=tuple(selected.source_connectors),
        evidence_ids=tuple(selected.evidence_ids),
    )

    assert hasattr(projection, "project_research_packet_v2_facts")
    projected = projection.project_research_packet_v2_facts(
        planning_input, (packet_fact,), (selected, foreign)
    )

    assert [fact.source_fact_ids for fact in projected.source_facts] == [[selected.source_id]]
    assert foreign.evidence_ids[0] not in projected.evidence_ids
