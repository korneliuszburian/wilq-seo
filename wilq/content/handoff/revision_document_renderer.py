from __future__ import annotations

from wilq.content.workflow.revisions import ContentDraftRevision


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


def _placed_blocks(document: ContentDraftRevision, placement: str) -> list[str]:
    blocks = [
        item.body_markdown.strip() for item in document.cta_blocks if item.placement == placement
    ]
    blocks.extend(
        f"[{item.anchor_text}]({item.target_url})"
        for item in document.internal_links
        if item.placement == placement
    )
    return blocks
