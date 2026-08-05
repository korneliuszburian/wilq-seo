from __future__ import annotations

from typing import cast

from markdown_it import MarkdownIt

from wilq.content.canonical.urls import content_is_safe_public_url
from wilq.content.workflow.revisions import ContentDraftRevision

_WORDPRESS_MARKDOWN = MarkdownIt("commonmark", {"html": False, "linkify": False})


def revision_document_markdown(document: ContentDraftRevision) -> str:
    assets = document.page_assets
    if assets is None:
        raise RuntimeError("Full-document renderer requires page assets.")
    chunks = [f"# {assets.h1}", assets.lead]
    chunks.extend(_placed_blocks(document, "after_lead"))
    for section in document.sections:
        chunks.extend([f"## {section.heading}", section.body_markdown.strip()])
        if section.section_id is not None:
            chunks.extend(_placed_blocks(document, section.section_id))
    if document.faq:
        chunks.append("## Najczęstsze pytania")
        for item in document.faq:
            chunks.extend([f"### {item.question}", item.answer_markdown.strip()])
    chunks.extend(_placed_blocks(document, "after_content"))
    return "\n\n".join(chunk for chunk in chunks if chunk.strip())


def revision_document_html(document: ContentDraftRevision) -> str:
    """Render readable editorial Markdown into safe WordPress HTML."""

    return cast(str, _WORDPRESS_MARKDOWN.render(revision_document_markdown(document)))


def _placed_blocks(document: ContentDraftRevision, placement: str) -> list[str]:
    blocks = [
        item.body_markdown.strip() for item in document.cta_blocks if item.placement == placement
    ]
    blocks.extend(
        _render_internal_link(item.anchor_text, item.target_url)
        for item in document.internal_links
        if item.placement == placement
    )
    return blocks


def _markdown_link_label(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\r", " ")
        .replace("\n", " ")
        .replace("\t", " ")
    )


def _render_internal_link(anchor_text: str, target_url: str) -> str:
    label = _markdown_link_label(anchor_text)
    if not content_is_safe_public_url(target_url):
        return label
    return f"[{label}]({target_url})"
