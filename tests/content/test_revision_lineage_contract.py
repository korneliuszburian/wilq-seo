from __future__ import annotations

from wilq.content.workflow.revision_persistence import (
    build_stored_draft_revision,
    draft_revision_content_digest,
)
from wilq.content.workflow.revisions import (
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionPageAssets,
    ContentDraftRevisionSection,
)


def _command(
    *, schema_version: str, source_material_ids: list[str] | None = None
) -> ContentDraftRevisionAppendCommand:
    return ContentDraftRevisionAppendCommand(
        schema_version=schema_version,
        work_item_id="content_work_item_lineage",
        draft_package_id="draft_package_lineage",
        draft_package_digest="1" * 64,
        planning_digest="2" * 64,
        planning_input_digest="3" * 64 if schema_version.endswith("v2") else None,
        service_card_id="ekologus_service_lineage" if schema_version.endswith("v2") else None,
        service_digest="4" * 64 if schema_version.endswith("v2") else None,
        inventory_digest="5" * 64 if schema_version.endswith("v2") else None,
        source_material_ids=source_material_ids or [],
        knowledge_card_ids=["ekologus_card_lineage"] if schema_version.endswith("v2") else [],
        final_canonical_url="https://www.ekologus.pl/lineage",
        title="Treść oparta na źródłach",
        page_assets=(
            ContentDraftRevisionPageAssets(
                wordpress_title="Treść oparta na źródłach",
                meta_title="Treść oparta na źródłach — Ekologus",
                meta_description="Opis oparty na zatwierdzonych faktach.",
                h1="Treść oparta na źródłach",
                lead="Lead oparty na zatwierdzonych faktach.",
            )
            if schema_version.endswith("v2")
            else None
        ),
        sections=[
            ContentDraftRevisionSection(
                section_id="section_lineage",
                heading="Najważniejsze fakty",
                body_markdown="Treść oparta na dowodzie.",
                query_terms=["fakty"],
                evidence_ids=["ev_lineage"],
                source_material_ids=source_material_ids or [],
                knowledge_card_ids=(
                    ["ekologus_card_lineage"] if schema_version.endswith("v2") else []
                ),
            )
        ],
        created_by="codex",
    )


def test_v1_payload_without_lineage_still_reads_with_empty_defaults() -> None:
    command = _command(schema_version="wilq_content_draft_revision_v1")
    revision = build_stored_draft_revision(
        command,
        revision_number=1,
        content_digest=draft_revision_content_digest(command),
    )

    assert revision.source_material_ids == []
    assert revision.knowledge_card_ids == []
    assert revision.sections[0].source_material_ids == []


def test_v1_digest_remains_isolated_from_v2_lineage_fields() -> None:
    baseline = _command(schema_version="wilq_content_draft_revision_v1")
    with_lineage = baseline.model_copy(
        update={
            "source_material_ids": ["legacy_material"],
            "knowledge_card_ids": ["legacy_card"],
            "sections": [
                baseline.sections[0].model_copy(
                    update={
                        "source_material_ids": ["legacy_material"],
                        "knowledge_card_ids": ["legacy_card"],
                    }
                )
            ],
        }
    )

    assert draft_revision_content_digest(baseline) == draft_revision_content_digest(with_lineage)


def test_v2_lineage_is_deterministic_and_part_of_digest() -> None:
    command = _command(
        schema_version="wilq_content_draft_revision_v2",
        source_material_ids=["ekologus_material_approved"],
    )
    first = draft_revision_content_digest(command)
    second = draft_revision_content_digest(command.model_copy(deep=True))
    changed = draft_revision_content_digest(
        command.model_copy(update={"source_material_ids": ["ekologus_material_other"]})
    )

    assert first == second
    assert changed != first
