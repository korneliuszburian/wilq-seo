from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi import HTTPException

from apps.api.wilq_api.routers.content_workflow import (
    _build_editor_save_command,
    _validate_canonical_html_alignment,
)
from wilq.content.workflow.content_html import content_html_from_markdown
from wilq.content.workflow.contracts import ContentDraftRevisionSaveRequest
from wilq.content.workflow.revision_children import build_child_draft_revision_command
from wilq.content.workflow.revision_persistence import (
    build_stored_draft_revision,
    draft_revision_content_digest,
)
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionPageAssets,
    ContentDraftRevisionProposalMetadata,
    ContentDraftRevisionSection,
)
from wilq.content.workflow.store import ContentWorkflowStore


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
                content_html=(
                    content_html_from_markdown("Treść oparta na dowodzie.")
                    if schema_version.endswith("v2")
                    else None
                ),
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


def test_store_reads_a_legacy_payload_without_new_lineage_fields(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    created = store.append_draft_revision(_command(schema_version="wilq_content_draft_revision_v1"))
    assert created.revision is not None

    with sqlite3.connect(tmp_path / "wilq.sqlite3") as connection:
        row = connection.execute(
            "SELECT payload_json FROM content_draft_revisions WHERE revision_id = ?",
            (created.revision.revision_id,),
        ).fetchone()
        assert row is not None
        payload = json.loads(row[0])
        payload.pop("source_material_ids", None)
        payload.pop("knowledge_card_ids", None)
        for section in payload["sections"]:
            section.pop("source_material_ids", None)
            section.pop("knowledge_card_ids", None)
        connection.execute(
            "UPDATE content_draft_revisions SET payload_json = ? WHERE revision_id = ?",
            (json.dumps(payload), created.revision.revision_id),
        )

    state = store.load_draft_revision_state("content_work_item_lineage")
    assert state.latest_revision is not None
    assert state.latest_revision.source_material_ids == []
    assert state.latest_revision.sections[0].knowledge_card_ids == []


def test_child_revision_preserves_full_document_lineage() -> None:
    command = _command(
        schema_version="wilq_content_draft_revision_v2",
        source_material_ids=["ekologus_material_approved"],
    )
    revision = build_stored_draft_revision(
        command,
        revision_number=1,
        content_digest=draft_revision_content_digest(command),
    )
    metadata = ContentDraftRevisionProposalMetadata(
        codex_run_id="codex_lineage_child",
        selected_section_headings=[revision.sections[0].heading],
        section_lineage=[
            {"heading": revision.sections[0].heading, "evidence_ids": ["ev_lineage"]}
        ],
        quality_verdict="reviewable",
    )

    child = build_child_draft_revision_command(
        revision,
        sections=revision.sections,
        proposal_metadata=metadata,
        created_by="codex",
    )

    assert child.source_material_ids == revision.source_material_ids
    assert child.knowledge_card_ids == revision.knowledge_card_ids
    assert child.sections[0].source_material_ids == revision.sections[0].source_material_ids


def test_editor_save_v2_carries_page_assets_and_lineage() -> None:
    command = _command(
        schema_version="wilq_content_draft_revision_v2",
        source_material_ids=["ekologus_material_approved"],
    )
    revision = build_stored_draft_revision(
        command,
        revision_number=1,
        content_digest=draft_revision_content_digest(command),
    )
    request = ContentDraftRevisionSaveRequest(
        base_revision_id=revision.revision_id,
        title="Zmieniony tytuł",
        sections=revision.sections,
        created_by="wilku",
    )

    saved = _build_editor_save_command(
        work_item_id=revision.work_item_id,
        request=request,
        latest_revision=revision,
        draft_package=None,  # v2 carryover must not read the fallback package.
        planning=None,
        final_canonical_url=revision.final_canonical_url,
        revision_context_current=True,
    )

    assert saved.schema_version == "wilq_content_draft_revision_v2"
    assert saved.page_assets is not None
    assert saved.page_assets.wordpress_title == "Zmieniony tytuł"
    assert saved.page_assets.meta_title == revision.page_assets.meta_title
    assert saved.page_assets.meta_description == revision.page_assets.meta_description
    assert saved.source_material_ids == revision.source_material_ids
    assert saved.knowledge_card_ids == revision.knowledge_card_ids


def test_canonical_html_alignment_can_change_only_derived_html() -> None:
    current_section = ContentDraftRevisionSection(
        section_id="section_lineage",
        heading="Najważniejsze fakty",
        body_markdown="Tekst po humanizacji.",
        content_html="<p>Stary render.</p>",
        evidence_ids=["ev_lineage"],
    )
    latest = ContentDraftRevision.model_construct(
        revision_id="content_revision_current",
        title="Treść oparta na źródłach",
        sections=[current_section],
    )
    request = ContentDraftRevisionSaveRequest(
        base_revision_id=latest.revision_id,
        title=latest.title,
        sections=[
            current_section.model_copy(
                update={"content_html": content_html_from_markdown(current_section.body_markdown)}
            )
        ],
        correction_reason="canonical_html_alignment",
        created_by="operator_local_dashboard",
    )

    _validate_canonical_html_alignment(request, latest)

    changed_body = request.model_copy(
        update={
            "sections": [
                request.sections[0].model_copy(update={"body_markdown": "Inny tekst."})
            ]
        }
    )
    with pytest.raises(HTTPException, match="wyłącznie kanoniczne HTML"):
        _validate_canonical_html_alignment(changed_body, latest)


def test_canonical_html_alignment_is_not_a_second_codex_proposal() -> None:
    command = _command(schema_version="wilq_content_draft_revision_v2")
    proposal_metadata = ContentDraftRevisionProposalMetadata(
        codex_run_id="codex_historical_proposal",
        selected_section_headings=[command.sections[0].heading],
        section_lineage=[
            {"heading": command.sections[0].heading, "evidence_ids": ["ev_lineage"]}
        ],
        quality_verdict="needs_changes",
    )
    revision = build_stored_draft_revision(
        command.model_copy(
            update={
                "proposal_metadata": proposal_metadata,
                "sections": [
                    command.sections[0].model_copy(update={"content_html": "<p>Stary render.</p>"})
                ],
            }
        ),
        revision_number=2,
        content_digest="a" * 64,
    )
    request = ContentDraftRevisionSaveRequest(
        base_revision_id=revision.revision_id,
        title=revision.title,
        sections=[
            revision.sections[0].model_copy(
                update={
                    "content_html": content_html_from_markdown(
                        revision.sections[0].body_markdown
                    )
                }
            )
        ],
        correction_reason="canonical_html_alignment",
        created_by="operator_local_dashboard",
    )

    saved = _build_editor_save_command(
        work_item_id=revision.work_item_id,
        request=request,
        latest_revision=revision,
        draft_package=None,
        planning=None,
        final_canonical_url=revision.final_canonical_url,
        revision_context_current=True,
    )

    assert saved.correction_reason == "canonical_html_alignment"
    assert saved.proposal_metadata is None
    assert saved.sections == request.sections
