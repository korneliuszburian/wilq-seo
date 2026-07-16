from __future__ import annotations

import json
from hashlib import sha256
from uuid import uuid4

from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionSection,
)
from wilq.schemas.core import utc_now
from wilq.security.redaction import redact_mapping


def draft_revision_content_digest(command: ContentDraftRevisionAppendCommand) -> str:
    payload: dict[str, object] = {
        "work_item_id": command.work_item_id,
        "draft_package_id": command.draft_package_id,
        "draft_package_digest": command.draft_package_digest,
        "planning_digest": command.planning_digest,
        "final_canonical_url": command.final_canonical_url,
        "title": command.title,
        "sections": [
            _section_digest_payload(section, command.schema_version) for section in command.sections
        ],
        "publish_ready": command.publish_ready,
    }
    if command.schema_version == "wilq_content_draft_revision_v2":
        payload.update(_full_document_digest_payload(command))
    canonical_json = json.dumps(
        redact_mapping(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical_json.encode("utf-8")).hexdigest()


def build_stored_draft_revision(
    command: ContentDraftRevisionAppendCommand,
    *,
    revision_number: int,
    content_digest: str,
) -> ContentDraftRevision:
    return ContentDraftRevision(
        **command.model_dump(mode="python", exclude={"requested_at"}),
        revision_id=f"content_revision_{uuid4().hex}",
        revision_number=revision_number,
        content_digest=content_digest,
        created_at=utc_now(),
    )


def _full_document_digest_payload(
    command: ContentDraftRevisionAppendCommand,
) -> dict[str, object]:
    return {
        "schema_version": command.schema_version,
        "planning_input_digest": command.planning_input_digest,
        "service_card_id": command.service_card_id,
        "service_digest": command.service_digest,
        "inventory_digest": command.inventory_digest,
        "page_assets": (
            None if command.page_assets is None else command.page_assets.model_dump(mode="json")
        ),
        "faq": [item.model_dump(mode="json") for item in command.faq],
        "cta_blocks": [item.model_dump(mode="json") for item in command.cta_blocks],
        "internal_links": [item.model_dump(mode="json") for item in command.internal_links],
    }


def _section_digest_payload(
    section: ContentDraftRevisionSection,
    schema_version: str,
) -> dict[str, object]:
    if schema_version == "wilq_content_draft_revision_v2":
        return section.model_dump(mode="json")
    return {
        "heading": section.heading,
        "body_markdown": section.body_markdown,
        "evidence_ids": section.evidence_ids,
    }
