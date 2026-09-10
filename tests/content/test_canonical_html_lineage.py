from __future__ import annotations

from pathlib import Path

from apps.api.wilq_api.routers.content_workflow import _build_editor_save_command
from tests.content.test_refresh_preparation_editor_child import _bound_parent
from wilq.content.workflow.contracts.contracts import ContentDraftRevisionSaveRequest
from wilq.content.workflow.documents.content_html import content_html_from_markdown
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevisionCtaBlock,
    ContentDraftRevisionFaqItem,
    ContentDraftRevisionInternalLink,
    ContentDraftRevisionOfficialSourceReference,
    ContentDraftRevisionSourceProvenance,
)

_CHILD_IDENTITY_FIELDS = {
    "revision_id",
    "revision_number",
    "base_revision_id",
    "content_digest",
    "created_by",
    "created_at",
    "correction_reason",
    "sections",
}


def test_canonical_html_alignment_preserves_exact_lineage_as_a_non_codex_child(
    tmp_path: Path,
) -> None:
    store, parent, persisted_parent = _canonical_lineage_parent(tmp_path)
    parent_before = parent.model_copy(deep=True)
    request = _canonical_alignment_request(parent)

    command = _build_editor_save_command(
        work_item_id=parent.work_item_id,
        request=request,
        latest_revision=parent,
        draft_package=None,
        planning=None,
        final_canonical_url=parent.final_canonical_url,
        revision_context_current=True,
    )
    result = store.append_draft_revision(command)

    assert result.status == "created"
    assert result.revision is not None
    _assert_exact_canonical_child(result.revision, parent, request)
    assert parent == parent_before
    assert store.list_draft_revisions(parent.work_item_id)[0] == persisted_parent


def _canonical_lineage_parent(tmp_path: Path):
    store, persisted_parent = _bound_parent(tmp_path)
    metadata = persisted_parent.proposal_metadata
    assert metadata is not None
    section = persisted_parent.sections[0].model_copy(
        update={
            "content_html": "<p>Stary render.</p>",
            "evidence_ids": ["ev_bdo", "ev_regulatory"],
            "claim_ids": ["claim_regulatory"],
            "source_material_ids": ["material_regulatory"],
            "knowledge_card_ids": ["knowledge_regulatory"],
        }
    )
    source_provenance = ContentDraftRevisionSourceProvenance(
        source_fact_id="regulatory_source_fact_green_deal_current",
        source_url_or_path="https://commission.europa.eu/current-green-deal.pdf",
        freshness_date="2026-09-09",
        evidence_ids=["ev_regulatory"],
    )
    official_source = ContentDraftRevisionOfficialSourceReference(
        source_fact_id=source_provenance.source_fact_id,
        source_url="https://commission.europa.eu/current-green-deal.pdf",
        source_title="Komisja Europejska — Zielony Ład",
        verified_on="2026-09-09",
        evidence_ids=source_provenance.evidence_ids,
        regulatory_requirement_ids=["green_deal"],
    )
    parent = persisted_parent.model_copy(
        update={
            "sections": [section],
            "source_provenance": [source_provenance],
            "faq": [_faq()],
            "cta_blocks": [_cta()],
            "internal_links": [_internal_link(section.section_id)],
            "official_source_references": [official_source],
            "proposal_metadata": metadata.model_copy(
                update={
                    "section_lineage": [
                        metadata.section_lineage[0].model_copy(
                            update={"evidence_ids": section.evidence_ids}
                        )
                    ]
                }
            ),
        }
    )
    return store, parent, persisted_parent


def _canonical_alignment_request(parent) -> ContentDraftRevisionSaveRequest:
    return ContentDraftRevisionSaveRequest(
        base_revision_id=parent.revision_id,
        title=parent.title,
        sections=[
            parent.sections[0].model_copy(
                update={
                    "content_html": content_html_from_markdown(parent.sections[0].body_markdown)
                }
            )
        ],
        correction_reason="canonical_html_alignment",
        created_by="operator_local_dashboard",
    )


def _assert_exact_canonical_child(child, parent, request: ContentDraftRevisionSaveRequest) -> None:
    assert child.base_revision_id == parent.revision_id
    assert child.correction_reason == "canonical_html_alignment"
    assert child.source_provenance == parent.source_provenance
    assert child.proposal_metadata == parent.proposal_metadata
    assert child.official_source_references == parent.official_source_references
    assert child.faq == parent.faq
    assert child.cta_blocks == parent.cta_blocks
    assert child.internal_links == parent.internal_links
    assert child.refresh_preparation_binding == parent.refresh_preparation_binding
    assert child.model_dump(exclude=_CHILD_IDENTITY_FIELDS) == parent.model_dump(
        exclude=_CHILD_IDENTITY_FIELDS
    )
    assert [section.model_dump(exclude={"content_html"}) for section in child.sections] == [
        section.model_dump(exclude={"content_html"}) for section in parent.sections
    ]
    assert child.sections == request.sections


def _faq() -> ContentDraftRevisionFaqItem:
    return ContentDraftRevisionFaqItem(
        faq_id="faq_green_deal",
        question="Jak ocenić zakres obowiązków?",
        answer_markdown="Trzeba odnieść wymagania do konkretnej działalności.",
        evidence_ids=["ev_regulatory"],
    )


def _cta() -> ContentDraftRevisionCtaBlock:
    return ContentDraftRevisionCtaBlock(
        cta_id="cta_green_deal",
        placement="after_content",
        body_markdown="Przekaż dane do weryfikacji zakresu.",
        evidence_ids=["ev_regulatory"],
    )


def _internal_link(section_id: str | None) -> ContentDraftRevisionInternalLink:
    return ContentDraftRevisionInternalLink(
        link_id="link_green_deal",
        placement=section_id or "section_refresh",
        target_url="https://www.ekologus.pl/kontakt/",
        anchor_text="Skontaktuj się z Ekologus",
        evidence_ids=["ev_regulatory"],
    )
