from __future__ import annotations

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.generated_proposal_contracts import ContentPlanningModelOutput


def planning_output_lineage_errors(
    planning_input: ContentPlanningInput,
    output: ContentPlanningModelOutput,
) -> list[str]:
    """Reject model output that cannot be traced to the exact planning input."""

    allowed_queries = {
        row.term
        for row in (
            *planning_input.query_portfolio.gsc_query_rows,
            *planning_input.query_portfolio.ads_term_rows,
            *planning_input.query_portfolio.keyword_planner_rows,
        )
    }
    allowed_evidence = set(planning_input.evidence_ids)
    allowed_claims = {
        entry.id
        for entry in planning_input.claim_ledger
        if entry.status in {"allowed_with_evidence", "allowed_general"}
    }
    allowed_internal_links = {
        candidate.target_url: set(candidate.evidence_ids)
        for candidate in planning_input.internal_link_candidates
    }
    inventory_headings = {item.heading for item in planning_input.inventory.sections}
    inventory_section_ids = {item.section_id for item in planning_input.inventory.sections}
    errors = _section_lineage_errors(
        output,
        allowed_queries=allowed_queries,
        allowed_evidence=allowed_evidence,
        allowed_claims=allowed_claims,
        inventory_headings=inventory_headings,
        inventory_section_ids=inventory_section_ids,
    )
    if output.service_card_id != planning_input.confirmed_service_card_id:
        errors.append("service_card_id")
    errors.extend(
        _asset_lineage_errors(
            output,
            allowed_queries=allowed_queries,
            allowed_evidence=allowed_evidence,
            allowed_claims=allowed_claims,
            allowed_internal_links=allowed_internal_links,
        )
    )
    errors.extend(_hypothesis_lineage_errors(planning_input, output))
    errors.extend(_measurement_lineage_errors(planning_input, output))
    errors.extend(regulatory_planning_lineage_errors(planning_input, output))
    return list(dict.fromkeys(errors))


def regulatory_planning_lineage_errors(
    planning_input: ContentPlanningInput,
    output: ContentPlanningModelOutput,
) -> list[str]:
    """Require every regulated topic to be assigned exact official evidence."""

    required_evidence = {
        item.requirement_id: set(item.evidence_ids)
        for item in planning_input.regulatory_coverage.requirement_coverage
    }
    required_ids = set(required_evidence)
    errors: list[str] = []
    unknown_requirements = {
        requirement_id
        for section in output.sections
        for requirement_id in section.regulatory_requirement_ids
        if requirement_id not in required_ids
    }
    errors.extend(f"regulatory_requirement_unknown:{requirement_id}" for requirement_id in sorted(unknown_requirements))
    for requirement in planning_input.regulatory_coverage.requirements:
        matching_sections = [
            section
            for section in output.sections
            if requirement.id in section.regulatory_requirement_ids
        ]
        if not matching_sections:
            errors.append(f"regulatory_requirement:{requirement.id}")
            continue
        if not any(
            set(section.evidence_ids).intersection(required_evidence.get(requirement.id, set()))
            for section in matching_sections
        ):
            errors.append(f"regulatory_evidence:{requirement.id}")
    return errors


def _section_lineage_errors(
    output: ContentPlanningModelOutput,
    *,
    allowed_queries: set[str],
    allowed_evidence: set[str],
    allowed_claims: set[str],
    inventory_headings: set[str],
    inventory_section_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    for section in output.sections:
        if not set(section.query_terms).issubset(allowed_queries):
            errors.append(f"section_query:{section.heading}")
        if not set(section.evidence_ids).issubset(allowed_evidence):
            errors.append(f"section_evidence:{section.heading}")
        if not set(section.claim_ids).issubset(allowed_claims):
            errors.append(f"section_claim:{section.heading}")
        if section.inventory_disposition == "create":
            if section.inventory_heading is not None or section.inventory_section_id is not None:
                errors.append(f"created_section_inventory:{section.heading}")
        else:
            if (
                section.inventory_section_id is not None
                and section.inventory_section_id not in inventory_section_ids
            ):
                errors.append(f"inventory_section_id:{section.heading}")
            if section.inventory_heading not in inventory_headings:
                errors.append(f"inventory_heading:{section.heading}")
    return errors


def _asset_lineage_errors(
    output: ContentPlanningModelOutput,
    *,
    allowed_queries: set[str],
    allowed_evidence: set[str],
    allowed_claims: set[str],
    allowed_internal_links: dict[str, set[str]],
) -> list[str]:
    errors: list[str] = []
    for faq in output.faq:
        if not set(faq.query_terms).issubset(allowed_queries):
            errors.append(f"faq_query:{faq.question}")
        if not set(faq.evidence_ids).issubset(allowed_evidence):
            errors.append(f"faq_evidence:{faq.question}")
        if not set(faq.claim_ids).issubset(allowed_claims):
            errors.append(f"faq_claim:{faq.question}")
    for cta in output.cta_blocks:
        if not set(cta.evidence_ids).issubset(allowed_evidence):
            errors.append(f"cta_evidence:{cta.placement}")
        if not set(cta.claim_ids).issubset(allowed_claims):
            errors.append(f"cta_claim:{cta.placement}")
    for link in output.internal_links:
        link_evidence = set(link.evidence_ids)
        candidate_evidence = allowed_internal_links.get(link.target_url)
        if candidate_evidence is None:
            errors.append(f"link_target:{link.target_url}")
        elif not link_evidence or not link_evidence.issubset(candidate_evidence):
            errors.append(f"link_inventory_evidence:{link.target_url}")
        if not link_evidence.issubset(allowed_evidence):
            errors.append(f"link_evidence:{link.target_url}")
        if not set(link.claim_ids).issubset(allowed_claims):
            errors.append(f"link_claim:{link.target_url}")
    return errors


def _hypothesis_lineage_errors(
    planning_input: ContentPlanningInput,
    output: ContentPlanningModelOutput,
) -> list[str]:
    errors: list[str] = []
    allowed_evidence = set(planning_input.evidence_ids)
    used_channels = {
        assessment.source
        for assessment in planning_input.source_assessments
        if assessment.status == "used"
    }
    for hypothesis in output.conditional_hypotheses:
        source = "google_ads" if hypothesis.channel == "google_ads" else "social"
        if source not in used_channels:
            errors.append(f"hypothesis_source:{hypothesis.channel}")
        if not set(hypothesis.evidence_ids).issubset(allowed_evidence):
            errors.append(f"hypothesis_evidence:{hypothesis.channel}")
    return errors


def _measurement_lineage_errors(
    planning_input: ContentPlanningInput,
    output: ContentPlanningModelOutput,
) -> list[str]:
    errors: list[str] = []
    if not set(output.measurement_plan.metrics_to_watch).issubset(
        planning_input.measurement_metrics
    ):
        errors.append("measurement_metrics")
    if not set(output.measurement_plan.baseline_evidence_ids).issubset(
        planning_input.measurement_baseline_evidence_ids
    ):
        errors.append("measurement_evidence")
    if output.measurement_plan.observation_rule != planning_input.measurement_observation_rule:
        errors.append("measurement_observation_rule")
    if output.measurement_plan.success_claim_rule != planning_input.measurement_success_claim_rule:
        errors.append("measurement_success_claim_rule")
    return errors
