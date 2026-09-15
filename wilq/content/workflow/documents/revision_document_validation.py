"""Structural validation for full draft-revision documents."""

from __future__ import annotations

from typing import Any

from wilq.content.canonical.urls import content_is_safe_public_url


def validate_full_document(document: Any) -> None:
    """Validate the shared document shape used by revisions and append commands."""

    if document.schema_version == "wilq_content_draft_revision_v1":
        if (
            document.document_kind != "refresh_existing"
            or document.new_page_document_identity is not None
            or document.official_source_references
            or not document.final_canonical_url
            or not document.final_canonical_url.strip()
        ):
            raise ValueError(
                "Historical v1 revision requires a refresh URL and cannot carry "
                "new-page identity or official source references."
            )
        return
    if document.document_kind == "refresh_existing":
        if not document.final_canonical_url or document.new_page_document_identity is not None:
            raise ValueError(
                "Refresh revision requires a public canonical URL and no new-page identity."
            )
    elif (
        document.final_canonical_url is not None
        or document.new_page_document_identity is None
        or document.new_page_document_identity.work_item_id != document.work_item_id
        or document.service_card_id != document.new_page_document_identity.service_card_id
        or document.service_digest != document.new_page_document_identity.service_card_digest
    ):
        raise ValueError(
            "New-page revision requires exact pre-document identity and no public URL."
        )
    required_bindings = (
        document.planning_input_digest,
        document.inventory_digest,
        document.page_assets,
    )
    if any(value is None for value in required_bindings):
        raise ValueError("Full-document revision requires exact planning bindings and page assets.")
    if (document.content_kind == "service") != (document.service_card_id is not None):
        raise ValueError("Full-document content kind must match its service identity.")
    if (document.content_kind == "service") != (document.service_digest is not None):
        raise ValueError("Full-document content kind must match its service digest.")
    if document.page_assets is None or document.page_assets.wordpress_title != document.title:
        raise ValueError("Full-document WordPress title must match the revision title.")
    section_ids = [section.section_id for section in document.sections]
    if any(section_id is None for section_id in section_ids):
        raise ValueError("Full-document revision requires a stable ID for every section.")
    _require_unique_ids([str(value) for value in section_ids], "section")
    _require_unique_ids([item.faq_id for item in document.faq], "FAQ")
    _require_unique_ids([item.cta_id for item in document.cta_blocks], "CTA")
    _require_unique_ids([item.link_id for item in document.internal_links], "internal link")
    _require_official_source_reference_ids(document)
    allowed_placements = {"after_lead", "after_content", *map(str, section_ids)}
    placements = [item.placement for item in document.cta_blocks]
    placements.extend(item.placement for item in document.internal_links)
    if not set(placements).issubset(allowed_placements):
        raise ValueError("Full-document CTA and link placement must target the document structure.")
    if any(not content_is_safe_public_url(item.target_url) for item in document.internal_links):
        raise ValueError("Full-document internal links require public Ekologus URLs.")
    for item in document.internal_links:
        _validate_plain_anchor(item.anchor_text)
    _validate_generated_content(document)


def _validate_generated_content(document: Any) -> None:
    generated_text = [
        document.page_assets.wordpress_title,
        document.page_assets.meta_title,
        document.page_assets.meta_description,
        document.page_assets.h1,
        document.page_assets.lead,
        *(item.heading for item in document.sections),
        *(item.body_markdown for item in document.sections),
        *(item.question for item in document.faq),
        *(item.answer_markdown for item in document.faq),
        *(item.body_markdown for item in document.cta_blocks),
    ]
    for value in generated_text:
        _validate_no_inline_link(value)
    evidence_collections = [
        *(item.evidence_ids for item in document.sections),
        *(item.evidence_ids for item in document.faq),
        *(item.evidence_ids for item in document.cta_blocks),
        *(item.evidence_ids for item in document.internal_links),
    ]
    if any(
        not evidence_ids or any(not value.strip() for value in evidence_ids)
        for evidence_ids in evidence_collections
    ):
        raise ValueError("Full-document content requires non-empty evidence lineage.")
    query_terms = [
        *(value for item in document.sections for value in item.query_terms),
        *(value for item in document.faq for value in item.query_terms),
    ]
    if any(not value.strip() for value in query_terms):
        raise ValueError("Full-document query lineage cannot contain blank values.")
    claim_ids = [
        *(value for item in document.sections for value in item.claim_ids),
        *(value for item in document.faq for value in item.claim_ids),
        *(value for item in document.cta_blocks for value in item.claim_ids),
        *(value for item in document.internal_links for value in item.claim_ids),
    ]
    if any(not value.strip() for value in claim_ids):
        raise ValueError("Full-document claim lineage cannot contain blank values.")


def _require_unique_ids(values: list[str], label: str) -> None:
    normalized = [value.strip() for value in values]
    if any(not value for value in normalized):
        raise ValueError(f"Full-document {label} IDs cannot be blank.")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"Full-document {label} IDs must be unique after stripping.")


def _require_official_source_reference_ids(document: Any) -> None:
    _require_unique_ids(
        [item.source_fact_id for item in document.official_source_references],
        "official source",
    )


def _validate_plain_anchor(value: str) -> None:
    from wilq.content.workflow.documents.revisions import validate_plain_internal_link_anchor

    validate_plain_internal_link_anchor(value)


def _validate_no_inline_link(value: str) -> None:
    from wilq.content.workflow.documents.revisions import validate_no_inline_link

    validate_no_inline_link(value)


__all__ = ["validate_full_document"]
