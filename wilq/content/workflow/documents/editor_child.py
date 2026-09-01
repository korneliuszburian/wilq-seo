from __future__ import annotations

from wilq.content.workflow.contracts.contracts import ContentDraftRevisionSaveRequest
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    validate_no_inline_link,
)
from wilq.security.redaction import redact_mapping


def request_has_full_document_fields(request: ContentDraftRevisionSaveRequest) -> bool:
    return (
        request.page_assets is not None
        or request.faq is not None
        or request.official_source_references is not None
    )


def validate_full_document_child(
    request: ContentDraftRevisionSaveRequest,
    latest_revision: ContentDraftRevision | None,
    *,
    revision_context_current: bool,
    approved_source_urls: dict[str, str],
) -> None:
    if (
        latest_revision is None
        or request.base_revision_id != latest_revision.revision_id
        or latest_revision.schema_version != "wilq_content_draft_revision_v2"
        or not revision_context_current
    ):
        if request_has_full_document_fields(request):
            raise ValueError(
                "Pełny dokument można zmienić wyłącznie jako potomną wersję bieżącej rewizji."
            )
        return
    allowed_evidence = revision_evidence_ids(latest_revision)
    allowed_claims = {
        claim_id for section in latest_revision.sections for claim_id in section.claim_ids
    } | {claim_id for faq in latest_revision.faq for claim_id in faq.claim_ids}
    allowed_query_terms = {
        term for section in latest_revision.sections for term in section.query_terms
    } | {term for faq in latest_revision.faq for term in faq.query_terms}
    allowed_source_materials = {
        item for section in latest_revision.sections for item in section.source_material_ids
    }
    allowed_knowledge_cards = {
        item for section in latest_revision.sections for item in section.knowledge_card_ids
    }
    retained_section_ids = {section.section_id for section in request.sections}
    removed_section_ids = {section.section_id for section in latest_revision.sections}.difference(
        retained_section_ids
    )
    preserved_placements = {item.placement for item in latest_revision.cta_blocks} | {
        item.placement for item in latest_revision.internal_links
    }
    if removed_section_ids.intersection(preserved_placements):
        raise ValueError(
            "Nie można scalić sekcji, do której nadal przypisano CTA albo link wewnętrzny."
        )
    for section in request.sections:
        if (
            set(section.claim_ids).difference(allowed_claims)
            or set(section.query_terms).difference(allowed_query_terms)
            or set(section.source_material_ids).difference(allowed_source_materials)
            or set(section.knowledge_card_ids).difference(allowed_knowledge_cards)
        ):
            raise ValueError("Sekcja potomnej wersji zawiera obcą lineage.")
    if request.faq is not None:
        _validate_faq(
            request, latest_revision, allowed_evidence, allowed_claims, allowed_query_terms
        )
    if request.official_source_references is not None:
        _validate_official_sources(request, latest_revision, approved_source_urls)


def _validate_faq(
    request: ContentDraftRevisionSaveRequest,
    latest_revision: ContentDraftRevision,
    allowed_evidence: set[str],
    allowed_claims: set[str],
    allowed_query_terms: set[str],
) -> None:
    faq = request.faq or []
    if [item.faq_id for item in faq] != [item.faq_id for item in latest_revision.faq]:
        raise ValueError("Edycja FAQ musi zachować identyfikatory i kolejność wersji bazowej.")
    if any(set(item.evidence_ids).difference(allowed_evidence) for item in faq):
        raise ValueError("FAQ potomnej wersji może używać tylko dowodów wersji bazowej.")
    if any(
        set(item.claim_ids).difference(allowed_claims)
        or set(item.query_terms).difference(allowed_query_terms)
        for item in faq
    ):
        raise ValueError("FAQ potomnej wersji zawiera obcą lineage.")
    for item in faq:
        validate_no_inline_link(item.question)
        validate_no_inline_link(item.answer_markdown)


def _validate_official_sources(
    request: ContentDraftRevisionSaveRequest,
    latest_revision: ContentDraftRevision,
    approved_source_urls: dict[str, str],
) -> None:
    parent_by_id = {
        item.source_fact_id: item for item in latest_revision.official_source_references
    }
    references = request.official_source_references or []
    submitted_ids = [item.source_fact_id for item in references]
    if len(submitted_ids) != len(set(submitted_ids)) or not set(submitted_ids).issubset(
        parent_by_id
    ):
        raise ValueError("Źródła oficjalne potomnej wersji muszą pochodzić z wersji bazowej.")
    removed_references = [
        item for source_fact_id, item in parent_by_id.items() if source_fact_id not in submitted_ids
    ]
    removed_evidence = {
        evidence_id for item in removed_references for evidence_id in item.evidence_ids
    }
    used_evidence = revision_evidence_ids_from_request(request, latest_revision)
    parent_requirements = {
        requirement_id
        for item in latest_revision.official_source_references
        for requirement_id in item.regulatory_requirement_ids
    }
    retained_requirements = {
        requirement_id for item in references for requirement_id in item.regulatory_requirement_ids
    }
    if removed_evidence.intersection(used_evidence) or not parent_requirements.issubset(
        retained_requirements
    ):
        raise ValueError(
            "Usunięcie źródła oficjalnego wymaga usunięcia jego evidence i zachowania "
            "pełnego pokrycia regulacyjnego."
        )
    for reference in references:
        parent = parent_by_id[reference.source_fact_id]
        if (
            reference.source_title != parent.source_title
            or reference.verified_on != parent.verified_on
            or reference.evidence_ids != parent.evidence_ids
            or reference.regulatory_requirement_ids != parent.regulatory_requirement_ids
            or approved_source_urls.get(reference.source_fact_id) != reference.source_url
            or redact_mapping({"source_url": reference.source_url})["source_url"]
            != reference.source_url
        ):
            raise ValueError("Źródło oficjalne nie odpowiada bezpiecznej lineage wersji bazowej.")


def revision_evidence_ids(revision: ContentDraftRevision) -> set[str]:
    return {
        evidence_id
        for evidence_ids in (
            *(section.evidence_ids for section in revision.sections),
            *(faq.evidence_ids for faq in revision.faq),
            *(cta.evidence_ids for cta in revision.cta_blocks),
            *(link.evidence_ids for link in revision.internal_links),
        )
        for evidence_id in evidence_ids
    }


def revision_evidence_ids_from_request(
    request: ContentDraftRevisionSaveRequest,
    latest_revision: ContentDraftRevision,
) -> set[str]:
    return {
        evidence_id
        for evidence_ids in (
            *(section.evidence_ids for section in request.sections),
            *(faq.evidence_ids for faq in request.faq or latest_revision.faq),
            *(cta.evidence_ids for cta in latest_revision.cta_blocks),
            *(link.evidence_ids for link in latest_revision.internal_links),
        )
        for evidence_id in evidence_ids
    }


__all__ = [
    "request_has_full_document_fields",
    "revision_evidence_ids",
    "validate_full_document_child",
]
