from __future__ import annotations

import json
from html import escape

from wilq.content.handoff.revision_document_renderer import revision_document_html
from wilq.content.workflow.contracts import (
    ContentRevisionHtmlPackageManifest,
    ContentRevisionHtmlPackageResponse,
)
from wilq.content.workflow.revisions import ContentDraftRevision, ContentDraftRevisionReview


def build_content_revision_html_package(
    revision: ContentDraftRevision,
    review: ContentDraftRevisionReview,
) -> ContentRevisionHtmlPackageResponse:
    """Build a read-only, manifest-bound HTML file for one approved revision."""

    if revision.page_assets is None:
        raise ValueError("HTML package requires a full-document revision.")
    if (
        review.revision_id != revision.revision_id
        or review.revision_digest != revision.content_digest
    ):
        raise ValueError("HTML package review must bind the exact revision and digest.")
    if review.decision != "approved":
        raise ValueError("HTML package requires an approved human review.")

    manifest = ContentRevisionHtmlPackageManifest(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        content_digest=revision.content_digest,
        final_canonical_url=revision.final_canonical_url,
        evidence_ids=_revision_evidence_ids(revision),
        source_material_ids=_revision_lineage_ids(revision, "source_material_ids"),
        knowledge_card_ids=_revision_lineage_ids(revision, "knowledge_card_ids"),
        section_count=len(revision.sections),
    )
    manifest_json = json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
    html_document = "\n".join(
        (
            "<!doctype html>",
            '<html lang="pl">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            f"  <title>{escape(revision.page_assets.meta_title)}</title>",
            "</head>",
            "<body>",
            f"<!-- WILQ exact-revision manifest: {manifest_json} -->",
            "<main>",
            revision_document_html(revision).strip(),
            "</main>",
            "</body>",
            "</html>",
        )
    )
    return ContentRevisionHtmlPackageResponse(
        manifest=manifest,
        file_name=f"wilq-exact-revision-{revision.revision_id}.html",
        html_document=html_document,
    )


def _revision_evidence_ids(revision: ContentDraftRevision) -> list[str]:
    return list(
        dict.fromkeys(
            evidence_id
            for collection in (
                revision.sections,
                revision.faq,
                revision.cta_blocks,
                revision.internal_links,
            )
            for item in collection
            for evidence_id in item.evidence_ids
        )
    )


def _revision_lineage_ids(
    revision: ContentDraftRevision,
    attribute: str,
) -> list[str]:
    revision_ids = getattr(revision, attribute)
    section_ids = [
        item_id
        for section in revision.sections
        for item_id in getattr(section, attribute)
    ]
    return list(
        dict.fromkeys([*revision_ids, *section_ids])
    )
