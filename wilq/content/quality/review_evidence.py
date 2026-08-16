from __future__ import annotations

from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.drafts.structured_generation import StructuredDraftOutput
from wilq.content.operator_copy import unique
from wilq.content.workflow.contracts.models import ContentWorkItem


def allowed_evidence_ids(
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
) -> set[str]:
    values = set(item.evidence_ids)
    if draft_package is None:
        return {value for value in values if value}
    for section in draft_package.sections:
        values.update(section.evidence_ids)
    for mapping in draft_package.section_to_evidence_map:
        values.update(mapping.evidence_ids)
    return {value for value in values if value}


def structured_output_evidence_ids(output: StructuredDraftOutput) -> set[str]:
    values = set(output.source_facts_used)
    for section in output.sections:
        values.update(section.evidence_ids)
    return {value for value in values if value}


def review_evidence_ids(
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
    structured_output: StructuredDraftOutput | None,
    claim_ledger: ContentClaimLedger | None,
) -> list[str]:
    values: list[object] = [*item.evidence_ids]
    if draft_package is not None:
        values.extend(
            evidence_id
            for section in draft_package.sections
            for evidence_id in section.evidence_ids
        )
    if structured_output is not None:
        values.extend(structured_output_evidence_ids(structured_output))
    if claim_ledger is not None:
        values.extend(
            evidence_id for entry in claim_ledger.entries for evidence_id in entry.evidence_ids
        )
    return unique(values)
