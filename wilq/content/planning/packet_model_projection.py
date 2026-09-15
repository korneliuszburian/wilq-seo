"""Bounded model projection for an exact server-owned research packet."""

from __future__ import annotations

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.research_packet import ContentResearchPacket


def project_planning_input_for_packet(
    planning_input: ContentPlanningInput,
    packet: ContentResearchPacket,
) -> dict[str, object]:
    """Expose only source facts, queries and evidence authorized by the packet."""

    payload = planning_input.model_dump(mode="json", warnings="none")
    allowed_facts = set(packet.approved_source_fact_ids)
    allowed_evidence = set(packet.evidence_ids)
    payload["evidence_ids"] = sorted(
        evidence_id
        for evidence_id in payload.get("evidence_ids", [])
        if evidence_id in allowed_evidence
    )
    payload["source_facts"] = _authorized_source_facts(
        payload.get("source_facts"), allowed_facts, allowed_evidence
    )
    payload["source_provenance"] = _authorized_provenance(
        payload.get("source_provenance"), allowed_facts, allowed_evidence
    )
    payload["query_portfolio"] = _authorized_queries(
        payload.get("query_portfolio"), packet.query_cluster, allowed_evidence
    )
    payload["claim_ledger"] = _authorized_claims(
        payload.get("claim_ledger"), allowed_evidence
    )
    payload["internal_link_candidates"] = _authorized_links(
        payload.get("internal_link_candidates"), packet, allowed_evidence
    )
    _restrict_regulatory_coverage(payload, allowed_facts, allowed_evidence)
    _trim_model_evidence_fields(payload, allowed_evidence)
    return payload


def current_research_packet_for_model(
    planning_input: ContentPlanningInput,
) -> ContentResearchPacket | None:
    if planning_input.research_packet_id is None:
        return None
    from wilq.content.workflow.store.store import content_workflow_store

    packet = content_workflow_store().load_content_research_packet(
        planning_input.research_packet_id
    )
    if (
        packet is None
        or packet.packet_digest != planning_input.research_packet_digest
        or packet.status != "exact_current"
        or packet.context_receipt is None
    ):
        raise ValueError("Research packet is missing or does not match planning input.")
    return packet


def _authorized_source_facts(
    value: object,
    allowed_facts: set[str],
    allowed_evidence: set[str],
) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    authorized: list[dict[str, object]] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        fact_ids = set(_string_list(raw.get("source_fact_ids"))) or {
            str(raw.get("fact_id", ""))
        }
        authorized_fact_ids = sorted(fact_ids.intersection(allowed_facts))
        if not authorized_fact_ids:
            continue
        evidence_ids = [
            evidence_id
            for evidence_id in _string_list(raw.get("evidence_ids"))
            if evidence_id in allowed_evidence
        ]
        if not evidence_ids:
            continue
        authorized.append(
            {
                **raw,
                "source_fact_ids": authorized_fact_ids,
                "evidence_ids": evidence_ids,
            }
        )
    return authorized


def _authorized_provenance(
    value: object,
    allowed_facts: set[str],
    allowed_evidence: set[str],
) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [
        {**raw, "evidence_ids": evidence_ids}
        for raw in value
        if isinstance(raw, dict)
        and str(raw.get("source_fact_id", "")) in allowed_facts
        and (evidence_ids := [
            evidence_id
            for evidence_id in _string_list(raw.get("evidence_ids"))
            if evidence_id in allowed_evidence
        ])
    ]


def _authorized_queries(
    value: object,
    query_cluster: tuple[str, ...],
    allowed_evidence: set[str],
) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    cluster = set(query_cluster)
    return {
        key: [
            {**row, "evidence_ids": [
                evidence_id
                for evidence_id in _string_list(row.get("evidence_ids"))
                if evidence_id in allowed_evidence
            ]}
            for row in rows
            if isinstance(row, dict)
            and str(row.get("term", "")).strip() in cluster
            and any(
                evidence_id in allowed_evidence
                for evidence_id in _string_list(row.get("evidence_ids"))
            )
        ]
        if isinstance(rows, list)
        else rows
        for key, rows in value.items()
    }


def _authorized_claims(value: object, allowed_evidence: set[str]) -> object:
    if isinstance(value, dict):
        entries = value.get("entries")
        if not isinstance(entries, list):
            return {**value, "entries": []}
        return {
            **value,
            "entries": _authorized_claim_entries(entries, allowed_evidence),
        }
    if isinstance(value, list):
        return _authorized_claim_entries(value, allowed_evidence)
    return {}


def _authorized_claim_entries(
    entries: list[object],
    allowed_evidence: set[str],
) -> list[dict[str, object]]:
    authorized: list[dict[str, object]] = []
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        original = _string_list(raw.get("evidence_ids"))
        evidence_ids = _trim_evidence_ids(original, allowed_evidence)
        if original and not evidence_ids:
            continue
        authorized.append({**raw, "evidence_ids": evidence_ids})
    return authorized


def _trim_model_evidence_fields(
    payload: dict[str, object],
    allowed_evidence: set[str],
) -> None:
    payload["measurement_baseline_evidence_ids"] = _trim_evidence_ids(
        payload.get("measurement_baseline_evidence_ids"), allowed_evidence
    )
    inventory = payload.get("inventory")
    if isinstance(inventory, dict):
        inventory["evidence_ids"] = _trim_evidence_ids(
            inventory.get("evidence_ids"), allowed_evidence
        )
        sections = inventory.get("sections")
        if isinstance(sections, list):
            inventory["sections"] = [
                {
                    **section,
                    "evidence_ids": _trim_evidence_ids(
                        section.get("evidence_ids"), allowed_evidence
                    ),
                }
                for section in sections
                if isinstance(section, dict)
            ]
    assessments = payload.get("source_assessments")
    if isinstance(assessments, list):
        payload["source_assessments"] = [
            {
                **assessment,
                "evidence_ids": _trim_evidence_ids(
                    assessment.get("evidence_ids"), allowed_evidence
                ),
            }
            for assessment in assessments
            if isinstance(assessment, dict)
        ]
    comparisons = payload.get("metric_comparisons")
    if isinstance(comparisons, list):
        payload["metric_comparisons"] = [
            {
                **comparison,
                "evidence_ids": _trim_evidence_ids(
                    comparison.get("evidence_ids"), allowed_evidence
                ),
            }
            for comparison in comparisons
            if isinstance(comparison, dict)
        ]


def _trim_evidence_ids(value: object, allowed_evidence: set[str]) -> list[str]:
    return [
        evidence_id
        for evidence_id in _string_list(value)
        if evidence_id in allowed_evidence
    ]


def _authorized_links(
    value: object,
    packet: ContentResearchPacket,
    allowed_evidence: set[str],
) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    destinations = {link.destination_path for link in packet.internal_links}
    authorized: list[dict[str, object]] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        evidence_ids = _trim_evidence_ids(raw.get("evidence_ids"), allowed_evidence)
        if (
            not evidence_ids
            or not str(raw.get("target_url", "")).rstrip("/").split("/")[-1]
            or _link_path(raw.get("target_url")) not in destinations
        ):
            continue
        authorized.append({**raw, "evidence_ids": evidence_ids})
    return authorized


def _restrict_regulatory_coverage(
    payload: dict[str, object],
    allowed_facts: set[str],
    allowed_evidence: set[str],
) -> None:
    coverage = payload.get("regulatory_coverage")
    if not isinstance(coverage, dict):
        return
    coverage["source_fact_ids"] = [
        fact_id
        for fact_id in _string_list(coverage.get("source_fact_ids"))
        if fact_id in allowed_facts
    ]
    rows = coverage.get("requirement_coverage")
    if isinstance(rows, list):
        coverage["requirement_coverage"] = [
            {
                **row,
                "source_fact_ids": [
                    fact_id
                    for fact_id in _string_list(row.get("source_fact_ids"))
                    if fact_id in allowed_facts
                ],
                "evidence_ids": [
                    evidence_id
                    for evidence_id in _string_list(row.get("evidence_ids"))
                    if evidence_id in allowed_evidence
                ],
            }
            for row in rows
            if isinstance(row, dict)
        ]
    source_facts = coverage.get("source_facts")
    if isinstance(source_facts, list):
        requirement_ids = {
            str(row.get("requirement_id"))
            for row in rows
            if isinstance(row, dict) and row.get("requirement_id")
        } if isinstance(rows, list) else set()
        coverage["source_facts"] = [
            {
                **fact,
                "evidence_ids": [
                    evidence_id
                    for evidence_id in _string_list(fact.get("evidence_ids"))
                    if evidence_id in allowed_evidence
                ],
                "regulatory_requirement_ids": [
                    requirement_id
                    for requirement_id in _string_list(fact.get("regulatory_requirement_ids"))
                    if requirement_id in requirement_ids
                ],
            }
            for fact in source_facts
            if isinstance(fact, dict)
            and str(fact.get("source_id", "")) in allowed_facts
            and any(
                evidence_id in allowed_evidence
                for evidence_id in _string_list(fact.get("evidence_ids"))
            )
        ]


def _link_path(value: object) -> str:
    text = str(value or "")
    if "://" in text:
        return "/" + text.split("://", 1)[1].split("/", 1)[1].rstrip("/")
    return text.rstrip("/") or "/"


def _string_list(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


__all__ = ["current_research_packet_for_model", "project_planning_input_for_packet"]
