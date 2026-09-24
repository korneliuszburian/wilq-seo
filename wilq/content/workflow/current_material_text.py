"""Transient, exact current-page text for read-only operator inspection."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.workflow.evidence_acquisition_snapshot import (
    CurrentPageSnapshotReadError,
    WordPressCurrentPageSnapshotAdapter,
)
from wilq.content.workflow.material_review_action_v2 import (
    load_current_material_review_action_v2,
    parse_material_review_action_preview,
)
from wilq.content.workflow.store.store import ContentWorkflowStore


class CurrentMaterialTextExact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["current_material_text_v1"] = "current_material_text_v1"
    status: Literal["exact"] = "exact"
    is_generated: Literal[False] = False
    action_id: str
    preview_id: str
    preview_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_url: str
    title: str
    text: str
    body_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    read_at: str
    evidence_ids: list[str]


class CurrentMaterialTextBlocked(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["current_material_text_v1"] = "current_material_text_v1"
    status: Literal["blocked"] = "blocked"
    is_generated: Literal[False] = False
    blocker_code: Literal["material_review_text_changed", "material_review_text_unavailable"]
    blocker_owner: Literal["WILQ content workflow", "WILQ WordPress connector"]
    safe_next_step: str
    evidence_ids: list[str]


def read_exact_current_material_text(
    *,
    work_item_id: str,
    action_id: str,
    store: ContentWorkflowStore,
    adapter: WordPressCurrentPageSnapshotAdapter,
) -> CurrentMaterialTextExact | CurrentMaterialTextBlocked | None:
    """Match a transient full read to the stored exact preview without writing it."""

    action = load_current_material_review_action_v2(action_id, store=store)
    if action is None:
        return None
    preview = parse_material_review_action_preview(action.payload["material_review_preview"])
    if preview.work_item_id != work_item_id:
        return None
    try:
        page = adapter.read_text(
            source_url=preview.public_url,
            canonical_path=preview.canonical_path,
        )
    except CurrentPageSnapshotReadError:
        return CurrentMaterialTextBlocked(
            blocker_code="material_review_text_unavailable",
            blocker_owner="WILQ WordPress connector",
            safe_next_step="Ponów dokładny odczyt bieżącej strony z WordPress.",
            evidence_ids=list(preview.evidence_ids),
        )
    if (
        page.body_digest != preview.observation.body_digest
        or page.extraction_region != preview.observation.extraction_region
    ):
        return CurrentMaterialTextBlocked(
            blocker_code="material_review_text_changed",
            blocker_owner="WILQ content workflow",
            safe_next_step="Przygotuj nowy exact odczyt aktualnej strony.",
            evidence_ids=list(preview.evidence_ids),
        )
    return CurrentMaterialTextExact(
        action_id=action_id,
        preview_id=preview.preview_id,
        preview_digest=preview.preview_digest,
        source_url=page.url,
        title=page.title,
        text=page.text,
        body_digest=page.body_digest,
        read_at=page.read_at.isoformat(),
        evidence_ids=list(preview.evidence_ids),
    )
