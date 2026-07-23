from __future__ import annotations

from datetime import UTC, datetime

import pytest

from wilq.content.handoff.html_package import build_content_revision_html_package
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionPageAssets,
    ContentDraftRevisionReview,
    ContentDraftRevisionSection,
)


def test_html_package_carries_the_exact_approved_revision_and_its_lineage() -> None:
    revision = _approved_revision()
    package = build_content_revision_html_package(revision, _exact_review(revision))

    assert package.manifest.model_dump() == {
        "work_item_id": revision.work_item_id,
        "revision_id": revision.revision_id,
        "content_digest": revision.content_digest,
        "final_canonical_url": revision.final_canonical_url,
        "evidence_ids": ["ev_section"],
        "source_material_ids": ["material_bdo"],
        "knowledge_card_ids": ["knowledge_bdo"],
        "section_count": 1,
    }
    assert package.file_name == "wilq-exact-revision-content_revision_approved.html"
    assert package.html_document.startswith("<!doctype html>")
    assert revision.content_digest in package.html_document
    assert "<h1>BDO</h1>" in package.html_document
    assert "Treść sekcji." in package.html_document


def test_html_package_rejects_a_review_for_a_different_exact_revision() -> None:
    revision = _approved_revision()
    review = _exact_review(revision).model_copy(update={"revision_digest": "b" * 64})

    with pytest.raises(ValueError, match="exact revision and digest"):
        build_content_revision_html_package(revision, review)


def _approved_revision() -> ContentDraftRevision:
    return ContentDraftRevision(
        revision_id="content_revision_approved",
        work_item_id="content_work_item_bdo",
        revision_number=1,
        content_digest="a" * 64,
        draft_package_id="draft_package_bdo",
        draft_package_digest="b" * 64,
        final_canonical_url="https://www.ekologus.pl/bdo/",
        title="BDO",
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="BDO",
            meta_title="BDO",
            meta_description="Opis BDO",
            h1="BDO",
            lead="Wprowadzenie."
        ),
        sections=[
            ContentDraftRevisionSection(
                section_id="section_1",
                heading="Sekcja",
                body_markdown="Treść sekcji.",
                content_html="<p>Treść sekcji.</p>",
                evidence_ids=["ev_section"],
                source_material_ids=["material_bdo"],
                knowledge_card_ids=["knowledge_bdo"],
            )
        ],
        created_by="operator_local_dashboard",
        created_at=datetime(2026, 7, 23, tzinfo=UTC),
    )


def _exact_review(revision: ContentDraftRevision) -> ContentDraftRevisionReview:
    return ContentDraftRevisionReview(
        decision_id="content_revision_review_approved",
        decision_number=1,
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        decision="approved",
        reviewed_by="operator_local_dashboard",
        checked_items=["Przeczytano dokładną treść tej wersji."],
        evidence_ids=["ev_section"],
        created_at=datetime(2026, 7, 23, tzinfo=UTC),
    )
