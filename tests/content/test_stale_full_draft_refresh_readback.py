from __future__ import annotations

from pathlib import Path

from wilq.content.workflow.revisions import (
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionPageAssets,
    ContentDraftRevisionSection,
)
from wilq.content.workflow.store import ContentWorkflowStore


def _command(
    *,
    base_revision_id: str | None = None,
    body: str = "Pierwsza wersja",
) -> ContentDraftRevisionAppendCommand:
    return ContentDraftRevisionAppendCommand(
        schema_version="wilq_content_draft_revision_v2",
        work_item_id="work_item_refresh",
        base_revision_id=base_revision_id,
        draft_package_id="draft_package_refresh",
        draft_package_digest="0" * 64,
        planning_digest="1" * 64,
        planning_input_digest="2" * 64,
        service_card_id="service_refresh",
        service_digest="3" * 64,
        inventory_digest="4" * 64,
        final_canonical_url="https://www.ekologus.pl/refresh/",
        title="Refresh test",
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Refresh test",
            meta_title="Refresh test",
            meta_description="Opis refresh test.",
            h1="Refresh test",
            lead="Lead refresh test.",
        ),
        sections=[
            ContentDraftRevisionSection(
                section_id="section_refresh",
                heading="Odpowiedź",
                body_markdown=body,
                evidence_ids=["ev_refresh"],
            )
        ],
        created_by="wilku",
    )


def test_stale_full_draft_refresh_round_trips_as_immutable_child(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    first = store.append_draft_revision(_command()).revision
    assert first is not None

    refreshed = store.append_draft_revision(
        _command(base_revision_id=first.revision_id, body="Odświeżona wersja")
    ).revision
    assert refreshed is not None
    assert refreshed.base_revision_id == first.revision_id
    assert refreshed.revision_number == 2
    assert refreshed.sections[0].body_markdown == "Odświeżona wersja"

    state = store.load_draft_revision_state("work_item_refresh")
    assert state.latest_revision == refreshed
    assert state.revision_count == 2
    assert first.content_digest != refreshed.content_digest
