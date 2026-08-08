"""Create-only WordPress payload projection for an exact new-page revision."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.handoff.revision_document_renderer import revision_document_html
from wilq.content.workflow.documents.revisions import ContentDraftRevision
from wilq.content.workflow.target.new_page_revision_binding import ContentNewPageDraftBinding


class ContentNewPageDevDraftWritePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector: Literal["wordpress_ekologus"] = "wordpress_ekologus"
    endpoint: Literal["posts", "pages"]
    post_status: Literal["draft"] = "draft"
    create_only: Literal[True] = True
    publish_allowed: Literal[False] = False
    update_allowed: Literal[False] = False
    delete_allowed: Literal[False] = False
    title: str = Field(min_length=1)
    content_html: str = Field(min_length=1)
    binding: ContentNewPageDraftBinding


def build_new_page_dev_draft_write_payload(
    revision: ContentDraftRevision,
    binding: ContentNewPageDraftBinding,
) -> ContentNewPageDevDraftWritePayload:
    """Project one approved new-page revision; never resolve a latest fallback."""
    identity = revision.new_page_document_identity
    if (
        revision.document_kind != "new_page"
        or identity is None
        or revision.revision_id != binding.revision_id
        or revision.content_digest != binding.revision_digest
        or revision.work_item_id != binding.work_item_id
        or identity.brief_id != binding.brief_id
        or identity.brief_digest != binding.brief_digest
        or identity.foundation_id != binding.foundation_id
        or identity.service_card_id != binding.service_card_id
        or identity.service_card_digest != binding.service_card_digest
    ):
        raise ValueError("Rewizja nowej strony nie pasuje do exact bindingu akcji.")
    return ContentNewPageDevDraftWritePayload(
        endpoint="pages" if binding.content_type == "page" else "posts",
        title=revision.title,
        content_html=revision_document_html(revision),
        binding=binding,
    )
