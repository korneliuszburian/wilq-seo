"""Bounded model projection for an exact server-owned research packet."""

from __future__ import annotations

from dataclasses import dataclass

from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.packet_input_binding import (
    bind_packet_identity_to_planning_input,
    unbind_packet_identity_from_planning_input,
)
from wilq.content.planning.proposal_v3_packet_read import (
    V3PlanningPacketContext,
    is_v3_research_packet_id,
    resolve_v3_planning_packet_context,
)
from wilq.content.planning.source_pack_projection import (
    project_research_packet_v2_facts,
    project_selected_source_pack_facts,
)
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.research_packet import ContentResearchPacket
from wilq.content.workflow.research_packet_v2_preview import ResearchPacketV2Preview
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store


@dataclass(frozen=True, slots=True)
class ResearchPacketV2ModelProjection:
    packet_id: str
    packet_digest: str
    preview: ResearchPacketV2Preview
    planning_input: ContentPlanningInput


@dataclass(frozen=True, slots=True)
class ContentPacketModelInput:
    planning_input: ContentPlanningInput
    packet: ContentResearchPacket | None = None
    packet_context: V3PlanningPacketContext | None = None

    @property
    def allowed_source_fact_ids(self) -> set[str] | None:
        if self.packet_context is not None:
            return {fact.source_fact_id for fact in self.packet_context.packet.selected_facts}
        return None if self.packet is None else set(self.packet.approved_source_fact_ids)


def content_packet_model_input(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
) -> ContentPacketModelInput:
    """Use one verified frozen v3 context, retaining the legacy projection seam."""
    if any(
        packet_id is not None and is_v3_research_packet_id(packet_id)
        for packet_id in (planning_input.research_packet_id, proposal.research_packet_id)
    ):
        result = resolve_v3_planning_packet_context(proposal=proposal)
        context = result.context
        if context is None:
            raise ValueError(result.blocker_code)
        if context.planning_input != planning_input:
            raise ValueError("research_packet_v3_frozen_input_identity_mismatch")
        return ContentPacketModelInput(planning_input=planning_input, packet_context=context)
    packet = current_research_packet_for_model(planning_input)
    projected = (
        planning_input
        if packet is None
        else project_selected_source_pack_facts(
            planning_input,
            packet.approved_source_fact_ids,
            ekologus_source_facts(),
        )
    )
    return ContentPacketModelInput(planning_input=projected, packet=packet)


def current_research_packet_v2_for_model(
    planning_input: ContentPlanningInput,
    *,
    store: ContentWorkflowStore | None = None,
) -> ResearchPacketV2ModelProjection | None:
    """Load the exact immutable v2 approval and reproject its selected registry facts."""
    packet_id = planning_input.research_packet_id
    if packet_id is None or not packet_id.startswith("content_research_packet_v2_"):
        return None
    packet_digest = planning_input.research_packet_digest
    if packet_digest is None:
        raise ValueError("Approved v2 packet model input requires its exact digest.")
    workflow_store = store or content_workflow_store()
    receipt = workflow_store.load_research_packet_v2_approval_receipt(packet_id)
    if receipt is None or receipt.packet_id != packet_id or receipt.packet_digest != packet_digest:
        raise ValueError("Approved v2 packet receipt is missing or differs from the input.")
    record = workflow_store.load_research_packet_v2_preview(receipt.packet_digest)
    if record is None or record.preview_hash != receipt.packet_digest:
        raise ValueError("Approved v2 packet preview is missing or differs from its receipt.")
    preview = record.snapshot
    if (
        preview.status != "ready"
        or preview.work_item_id != planning_input.work_item_id
        or record.work_item_id != planning_input.work_item_id
        or preview.preview_hash != receipt.packet_digest
    ):
        raise ValueError("Approved v2 packet preview is not ready for this work item.")

    raw_input = unbind_packet_identity_from_planning_input(planning_input)
    if raw_input.work_item_id != preview.work_item_id:
        raise ValueError("Approved v2 packet work item differs from the supplied input.")
    projected = project_research_packet_v2_facts(
        raw_input,
        preview.selected_facts,
        ekologus_source_facts(),
    )
    bound = bind_packet_identity_to_planning_input(
        projected,
        work_item_id=preview.work_item_id,
        packet_id=receipt.packet_id,
        packet_digest=receipt.packet_digest,
    )
    if bound.planning_input_digest != planning_input.planning_input_digest:
        raise ValueError("Approved v2 packet projection differs from the supplied planning input.")
    return ResearchPacketV2ModelProjection(
        packet_id=receipt.packet_id,
        packet_digest=receipt.packet_digest,
        preview=preview,
        planning_input=bound,
    )


def project_planning_input_for_packet_v2(
    packet: ResearchPacketV2ModelProjection,
) -> dict[str, object]:
    """Build the model view from exact selected v2 facts and preview lineage."""
    planning_input = packet.planning_input
    preview = packet.preview
    allowed_evidence = set(planning_input.evidence_ids).intersection(preview.evidence_ids)
    selected_fact_ids = {fact.source_fact_id for fact in preview.selected_facts}
    payload = planning_input.model_dump(mode="json", warnings="none")
    payload["evidence_ids"] = sorted(allowed_evidence)
    payload["source_facts"] = _authorized_source_facts(
        payload.get("source_facts"), selected_fact_ids, allowed_evidence
    )
    payload["source_provenance"] = _authorized_provenance(
        payload.get("source_provenance"), selected_fact_ids, allowed_evidence
    )
    payload["query_portfolio"] = _authorized_v2_queries(
        payload.get("query_portfolio"), allowed_evidence
    )
    selected_fact_evidence = {
        evidence_id for fact in preview.selected_facts for evidence_id in fact.evidence_ids
    }
    payload["claim_ledger"] = _authorized_v2_claims(
        payload.get("claim_ledger"), selected_fact_evidence, allowed_evidence
    )
    payload["internal_link_candidates"] = _preview_internal_links(packet, allowed_evidence)
    _restrict_regulatory_coverage(payload, selected_fact_ids, allowed_evidence)
    _trim_model_evidence_fields(payload, allowed_evidence)
    coverage = payload.get("regulatory_coverage")
    if isinstance(coverage, dict):
        coverage.pop("source_facts", None)
    return payload


def _authorized_v2_queries(value: object, allowed_evidence: set[str]) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    row_keys = {"gsc_query_rows", "ads_term_rows", "keyword_planner_rows"}
    projected: dict[str, object] = {}
    for key, rows in value.items():
        if key not in row_keys or not isinstance(rows, list):
            projected[key] = (
                _trim_evidence_ids(rows, allowed_evidence)
                if key in {"evidence_ids", "optional_ads_evidence_ids"}
                else rows
            )
            continue
        accepted: list[dict[str, object]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            evidence_ids = _trim_evidence_ids(row.get("evidence_ids"), allowed_evidence)
            if evidence_ids:
                accepted.append({**row, "evidence_ids": evidence_ids})
        projected[key] = accepted
    return projected


def _authorized_v2_claims(
    value: object,
    selected_fact_evidence: set[str],
    allowed_evidence: set[str],
) -> object:
    if isinstance(value, dict):
        entries = value.get("entries")
        return (
            {
                **value,
                "entries": _authorized_v2_claim_entries(
                    entries, selected_fact_evidence, allowed_evidence
                ),
            }
            if isinstance(entries, list)
            else {**value, "entries": []}
        )
    if isinstance(value, list):
        return _authorized_v2_claim_entries(value, selected_fact_evidence, allowed_evidence)
    return {}


def _authorized_v2_claim_entries(
    entries: list[object],
    selected_fact_evidence: set[str],
    allowed_evidence: set[str],
) -> list[dict[str, object]]:
    accepted: list[dict[str, object]] = []
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        evidence_ids = _trim_evidence_ids(raw.get("evidence_ids"), allowed_evidence)
        if set(evidence_ids).intersection(selected_fact_evidence):
            accepted.append({**raw, "evidence_ids": evidence_ids})
    return accepted


def _preview_internal_links(
    packet: ResearchPacketV2ModelProjection,
    allowed_evidence: set[str],
) -> list[dict[str, object]]:
    links: list[dict[str, object]] = []
    for link in packet.preview.internal_links:
        evidence_ids = list(link.evidence_ids)
        if not evidence_ids or not set(evidence_ids).issubset(allowed_evidence):
            raise ValueError("Research packet v2 internal link lost its exact evidence binding.")
        links.append(
            {
                "target_url": link.target_url,
                "anchor_hint": link.anchor_hint,
                "source_connector": link.source_connector,
                "evidence_ids": evidence_ids,
            }
        )
    return links


def project_planning_input_for_packet(
    planning_input: ContentPlanningInput,
    packet: ContentResearchPacket,
) -> dict[str, object]:
    """Expose only source facts, queries and evidence authorized by the packet."""

    projected_input = project_selected_source_pack_facts(
        planning_input,
        packet.approved_source_fact_ids,
        ekologus_source_facts(),
    )
    payload = projected_input.model_dump(mode="json", warnings="none")
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
    payload["claim_ledger"] = _authorized_claims(payload.get("claim_ledger"), allowed_evidence)
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
        fact_ids = set(_string_list(raw.get("source_fact_ids"))) or {str(raw.get("fact_id", ""))}
        if not fact_ids.issubset(allowed_facts):
            continue
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
        and (
            evidence_ids := [
                evidence_id
                for evidence_id in _string_list(raw.get("evidence_ids"))
                if evidence_id in allowed_evidence
            ]
        )
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
            {
                **row,
                "evidence_ids": [
                    evidence_id
                    for evidence_id in _string_list(row.get("evidence_ids"))
                    if evidence_id in allowed_evidence
                ],
            }
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
    return [evidence_id for evidence_id in _string_list(value) if evidence_id in allowed_evidence]


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
        requirement_ids = (
            {
                str(row.get("requirement_id"))
                for row in rows
                if isinstance(row, dict) and row.get("requirement_id")
            }
            if isinstance(rows, list)
            else set()
        )
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
