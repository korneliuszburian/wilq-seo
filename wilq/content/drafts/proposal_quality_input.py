from __future__ import annotations

from collections.abc import Iterable

from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftOutput,
    StructuredDraftOutputSection,
)
from wilq.content.inventory.records import ContentInventoryDuplicateRisk
from wilq.content.quality.review import ContentQualityReview
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.revisions import ContentDraftRevision


def persisted_selected_sections_quality_input(
    *,
    output: StructuredDraftOutput,
    base_revision: ContentDraftRevision,
    selected_headings: list[str],
) -> StructuredDraftOutput:
    """Build the exact proposal delta that the quality verdict is allowed to score."""

    output_by_heading = {section.heading: section for section in output.sections}
    base_by_heading = {section.heading: section for section in base_revision.sections}
    sections = [
        StructuredDraftOutputSection(
            heading=heading,
            body_markdown=output_by_heading[heading].body_markdown,
            evidence_ids=base_by_heading[heading].evidence_ids,
            claims_used=output_by_heading[heading].claims_used,
        )
        for heading in selected_headings
    ]
    return output.model_copy(
        update={
            "title": base_revision.title,
            "h1": base_revision.title,
            "meta_title": "",
            "meta_description": "",
            "sections": sections,
            "faq": [],
            "cta": "",
            "internal_links": [],
            "source_facts_used": _unique(
                evidence_id for section in sections for evidence_id in section.evidence_ids
            ),
            "human_review_checklist": [],
        }
    )


def proposal_duplicate_risk(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> ContentInventoryDuplicateRisk:
    if (
        snapshot.preflight.item.duplicate_status == "checked"
        and snapshot.preflight.inventory_resolution.status == "resolved"
    ):
        return "clear"
    return "review_required"


def proposal_stage_quality_review(review: ContentQualityReview) -> ContentQualityReview:
    """Keep measurement planning visible without blocking an unreviewed draft."""

    measurement_code = "missing_measurement_window"
    if not any(finding.code == measurement_code for finding in review.blockers):
        return review
    blockers = [finding for finding in review.blockers if finding.code != measurement_code]
    findings = [
        finding.model_copy(update={"severity": "needs_changes"})
        if finding.code == measurement_code
        else finding
        for finding in review.findings
    ]
    return review.model_copy(
        update={
            "verdict": "blocked" if blockers else "needs_changes",
            "blockers": blockers,
            "findings": findings,
            "measurement_readiness": review.measurement_readiness.model_copy(
                update={
                    "status": "needs_changes",
                    "reason": (
                        "Plan pomiaru jest wymagany przed human review, "
                        "ale nie blokuje zapisania roboczej propozycji."
                    ),
                }
            ),
            "safe_next_step": (
                review.safe_next_step
                if blockers
                else ("Sprawdź semantykę propozycji i dodaj plan pomiaru przed human review.")
            ),
        }
    )


def proposal_quality_ledger(
    ledger: ContentClaimLedger,
    contract: StructuredDraftGenerationContract,
) -> ContentClaimLedger:
    """Review allowed markers; generated-body guards protect known blocked language."""

    allowed_claim_ids = {marker.claim_id for marker in contract.model_input.claim_markers}
    return ledger.model_copy(
        update={"entries": [entry for entry in ledger.entries if entry.id in allowed_claim_ids]}
    )


def _unique(values: Iterable[object]) -> list[str]:
    unique: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique:
            unique.append(text)
    return unique


__all__ = [
    "persisted_selected_sections_quality_input",
    "proposal_duplicate_risk",
    "proposal_quality_ledger",
    "proposal_stage_quality_review",
]
