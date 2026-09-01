from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from apps.api.wilq_api.routers.content_workflow import (
    _build_editor_save_command,
    _validate_canonical_html_alignment,
    _validate_revision_sections,
)
from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftModelOutput
from wilq.content.drafts.initial_full_draft_turn import initial_full_draft_output_schema
from wilq.content.workflow.contracts.contracts import ContentDraftRevisionSaveRequest
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.content_html import content_html_from_markdown
from wilq.content.workflow.documents.editor_child import validate_full_document_child
from wilq.content.workflow.documents.revision_children import build_child_draft_revision_command
from wilq.content.workflow.documents.revision_persistence import (
    build_stored_draft_revision,
    draft_revision_content_digest,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionCtaBlock,
    ContentDraftRevisionFaqItem,
    ContentDraftRevisionOfficialSourceReference,
    ContentDraftRevisionPageAssets,
    ContentDraftRevisionProposalMetadata,
    ContentDraftRevisionSection,
    ContentDraftRevisionSourceProvenance,
)
from wilq.content.workflow.store.store import ContentWorkflowStore


def test_draft_revision_page_assets_accepts_byline() -> None:
    page_assets = ContentDraftRevisionPageAssets.model_validate(
        _page_assets_payload() | {"byline": "Ekspert Ekologus"}
    )

    assert page_assets.byline == "Ekspert Ekologus"


def test_draft_revision_page_assets_rejects_inline_link_byline() -> None:
    payload = _page_assets_payload() | {"byline": "[Ekspert Ekologus](https://www.ekologus.pl/)"}

    with pytest.raises(ValidationError, match="cannot contain inline links"):
        ContentDraftRevisionPageAssets.model_validate(payload)


def test_draft_revision_page_assets_rejects_blank_byline() -> None:
    payload = _page_assets_payload() | {"byline": "   "}

    with pytest.raises(ValidationError, match="byline cannot be blank"):
        ContentDraftRevisionPageAssets.model_validate(payload)


def test_draft_revision_page_assets_accepts_none_and_missing_byline() -> None:
    explicit_none = ContentDraftRevisionPageAssets.model_validate(
        _page_assets_payload() | {"byline": None}
    )
    missing = ContentDraftRevisionPageAssets.model_validate(_page_assets_payload())

    assert explicit_none.byline is None
    assert missing.byline is None


def test_initial_draft_generation_leaves_byline_unset() -> None:
    output = ContentInitialDraftModelOutput.model_validate(
        {
            "page_assets": _page_assets_payload() | {"byline": "Niezweryfikowany autor"},
            "sections": [
                {
                    "section_id": "section_scope",
                    "heading": "Zakres",
                    "body_markdown": "Treść oparta na dowodzie.",
                }
            ],
        }
    )

    assert output.page_assets.byline is None


def test_initial_draft_generation_schema_excludes_byline() -> None:
    proposal = ContentPlanningProposal.model_construct(
        sections=[],
        faq=[],
        cta_blocks=[],
        internal_links=[],
    )
    schema = initial_full_draft_output_schema(proposal)

    page_assets_schema = schema["$defs"]["ContentDraftRevisionPageAssets"]
    assert "byline" not in page_assets_schema["properties"]
    assert "byline" not in page_assets_schema["required"]


def _page_assets_payload() -> dict[str, str]:
    return {
        "wordpress_title": "Treść oparta na źródłach",
        "meta_title": "Treść oparta na źródłach — Ekologus",
        "meta_description": "Opis oparty na zatwierdzonych faktach.",
        "h1": "Treść oparta na źródłach",
        "lead": "Lead oparty na zatwierdzonych faktach.",
    }


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


def test_v1_digest_binds_source_provenance() -> None:
    baseline = _command(schema_version="wilq_content_draft_revision_v1")
    with_provenance = baseline.model_copy(
        update={
            "source_provenance": [
                ContentDraftRevisionSourceProvenance(
                    source_fact_id="source_fact_lineage",
                    source_url_or_path="https://bdo.mos.gov.pl/zasady-rejestracji/",
                    freshness_date="2026-08-02",
                    reviewer="Ekspert Ekologus",
                    evidence_ids=["ev_lineage"],
                )
            ]
        }
    )

    assert draft_revision_content_digest(with_provenance) != draft_revision_content_digest(baseline)


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
        section_lineage=[{"heading": revision.sections[0].heading, "evidence_ids": ["ev_lineage"]}],
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


def test_regulatory_assurance_provenance_is_canonicalized_for_shared_contracts() -> None:
    metadata = ContentDraftRevisionProposalMetadata(
        codex_run_id="codex_lineage_child",
        selected_section_headings=["Zakres"],
        section_lineage=[{"heading": "Zakres", "evidence_ids": ["ev_lineage"]}],
        quality_verdict="reviewable",
        regulatory_assurance_run_id=" codex_assurance ",
        regulatory_assurance_criteria_version=" criteria_v1 ",
    )

    assert metadata.regulatory_assurance_run_id == "codex_assurance"
    assert metadata.regulatory_assurance_criteria_version == "criteria_v1"


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


def _full_document_child_fixture():
    command = _command(schema_version="wilq_content_draft_revision_v2")
    second_section = command.sections[0].model_copy(
        update={"section_id": "section_monitoring", "heading": "Monitoring"}
    )
    source = ContentDraftRevisionOfficialSourceReference(
        source_fact_id="regulatory_source_fact_ekoportal",
        source_url=(
            "https://www.ekoportal.gov.pl/fileadmin/Ekoportal/Pozwolenia_zintegrowane/"
            "poradniki_branzowe/opracowania/"
            "Wytyczne_do_sporzadzania_wniosku_o_wydanie_PZ.pdf"
        ),
        source_title="Wytyczne Ekoportal",
        verified_on="2026-09-01",
        evidence_ids=["ev_official"],
        regulatory_requirement_ids=["initial_report"],
    )
    command = command.model_copy(
        update={
            "sections": [
                command.sections[0].model_copy(
                    update={"evidence_ids": ["ev_lineage", "ev_official"]}
                ),
                second_section,
            ],
            "faq": [
                ContentDraftRevisionFaqItem(
                    faq_id="faq_initial_report",
                    question="Kiedy raport może być wymagany?",
                    answer_markdown="Odpowiedź bazowa.",
                    evidence_ids=["ev_lineage"],
                )
            ],
            "official_source_references": [source],
        }
    )
    revision = build_stored_draft_revision(
        command,
        revision_number=2,
        content_digest=draft_revision_content_digest(command),
    )
    merged_section = revision.sections[0].model_copy(
        update={
            "heading": "Dokumentacja i monitoring",
            "body_markdown": "Połączona treść bez powtórzeń.",
            "content_html": content_html_from_markdown("Połączona treść bez powtórzeń."),
        }
    )
    page_assets = revision.page_assets.model_copy(
        update={
            "meta_description": "Opis uwzględniający raport początkowy.",
        }
    )
    request = ContentDraftRevisionSaveRequest(
        base_revision_id=revision.revision_id,
        title=revision.title,
        page_assets=page_assets,
        sections=[merged_section],
        faq=[
            revision.faq[0].model_copy(
                update={
                    "answer_markdown": "Obowiązek zależy od dwóch łącznych warunków.",
                    "evidence_ids": ["ev_official"],
                }
            )
        ],
        official_source_references=[source],
        created_by="wilku",
    )
    return revision, source, request, page_assets


def test_editor_child_can_merge_sections_and_repair_faq_with_existing_lineage() -> None:
    revision, source, request, page_assets = _full_document_child_fixture()
    snapshot = SimpleNamespace(
        draft_package=SimpleNamespace(
            draft_package_result=SimpleNamespace(draft_package=SimpleNamespace(sections=[]))
        )
    )

    _validate_revision_sections(
        request,
        snapshot,
        latest_revision=revision,
        revision_context_current=True,
    )
    validate_full_document_child(
        request,
        revision,
        revision_context_current=True,
        approved_source_urls={source.source_fact_id: source.source_url},
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

    assert [section.section_id for section in saved.sections] == ["section_lineage"]
    assert saved.faq[0].evidence_ids == ["ev_official"]
    assert saved.page_assets.meta_description == page_assets.meta_description
    assert saved.official_source_references == [source]


def test_editor_child_rejects_official_url_not_bound_to_approved_source_fact() -> None:
    revision, source, request, _page_assets = _full_document_child_fixture()
    wrong_url = request.model_copy(
        update={
            "official_source_references": [
                source.model_copy(update={"source_url": "https://eli.gov.pl/inny-dokument"})
            ]
        }
    )
    with pytest.raises(ValueError, match="bezpiecznej lineage"):
        validate_full_document_child(
            wrong_url,
            revision,
            revision_context_current=True,
            approved_source_urls={source.source_fact_id: source.source_url},
        )


def test_editor_child_rejects_foreign_component_lineage() -> None:
    revision, source, request, _page_assets = _full_document_child_fixture()
    foreign = request.model_copy(
        update={
            "sections": [request.sections[0].model_copy(update={"claim_ids": ["foreign_claim"]})]
        }
    )

    with pytest.raises(ValueError, match="obcą lineage"):
        validate_full_document_child(
            foreign,
            revision,
            revision_context_current=True,
            approved_source_urls={source.source_fact_id: source.source_url},
        )


def test_editor_child_rejects_stale_full_document_context() -> None:
    revision, source, request, _page_assets = _full_document_child_fixture()

    with pytest.raises(ValueError, match="potomną wersję bieżącej rewizji"):
        validate_full_document_child(
            request,
            revision,
            revision_context_current=False,
            approved_source_urls={source.source_fact_id: source.source_url},
        )


def test_editor_child_rejects_merge_with_component_on_removed_section() -> None:
    revision, source, request, _page_assets = _full_document_child_fixture()
    revision = revision.model_copy(
        update={
            "cta_blocks": [
                ContentDraftRevisionCtaBlock(
                    cta_id="cta_monitoring",
                    placement="section_monitoring",
                    body_markdown="Omów dokumentację.",
                    evidence_ids=["ev_lineage"],
                )
            ]
        }
    )

    with pytest.raises(ValueError, match="przypisano CTA"):
        validate_full_document_child(
            request,
            revision,
            revision_context_current=True,
            approved_source_urls={source.source_fact_id: source.source_url},
        )


def test_editor_child_rejects_duplicate_edited_headings() -> None:
    revision, _source, request, _page_assets = _full_document_child_fixture()
    duplicate_sections = [
        section.model_copy(update={"heading": "Ten sam nagłówek"}) for section in revision.sections
    ]
    duplicate_request = request.model_copy(update={"sections": duplicate_sections})
    snapshot = SimpleNamespace(
        draft_package=SimpleNamespace(
            draft_package_result=SimpleNamespace(draft_package=SimpleNamespace(sections=[]))
        )
    )

    with pytest.raises(HTTPException, match="muszą być unikalne"):
        _validate_revision_sections(
            duplicate_request,
            snapshot,
            latest_revision=revision,
            revision_context_current=True,
        )


def test_full_document_fields_reject_legacy_revision_parent() -> None:
    command = _command(schema_version="wilq_content_draft_revision_v1")
    revision = build_stored_draft_revision(
        command,
        revision_number=1,
        content_digest=draft_revision_content_digest(command),
    )
    request = ContentDraftRevisionSaveRequest(
        base_revision_id=revision.revision_id,
        title=revision.title,
        sections=[
            revision.sections[0].model_copy(
                update={"content_html": "<p>Treść oparta na dowodzie.</p>"}
            )
        ],
        faq=[],
        created_by="wilku",
    )

    with pytest.raises(ValueError, match="potomną wersję bieżącej rewizji"):
        validate_full_document_child(
            request,
            revision,
            revision_context_current=True,
            approved_source_urls={},
        )


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

    with pytest.raises(HTTPException, match="pozostałych pól"):
        _validate_canonical_html_alignment(request.model_copy(update={"faq": []}), latest)

    changed_body = request.model_copy(
        update={
            "sections": [request.sections[0].model_copy(update={"body_markdown": "Inny tekst."})]
        }
    )
    with pytest.raises(HTTPException, match="wyłącznie kanoniczne HTML"):
        _validate_canonical_html_alignment(changed_body, latest)


def test_current_v2_child_validates_against_its_exact_parent_sections() -> None:
    parent_section = ContentDraftRevisionSection(
        section_id="section_planning",
        heading="Pełny zakres planu regulacyjnego",
        body_markdown="Treść oparta na zatwierdzonych źródłach.",
        content_html=content_html_from_markdown("Treść oparta na zatwierdzonych źródłach."),
        evidence_ids=["ev_regulatory"],
    )
    latest = ContentDraftRevision.model_construct(
        schema_version="wilq_content_draft_revision_v2",
        revision_id="content_revision_parent",
        title="BDO dla przedsiębiorcy",
        sections=[parent_section],
    )
    request = ContentDraftRevisionSaveRequest(
        base_revision_id=latest.revision_id,
        title=latest.title,
        sections=[
            parent_section.model_copy(
                update={
                    "body_markdown": "Treść poprawiona bez powielenia.",
                    "content_html": content_html_from_markdown("Treść poprawiona bez powielenia."),
                }
            )
        ],
        created_by="wilku",
    )
    unrelated_package = SimpleNamespace(
        sections=[SimpleNamespace(heading="Starszy pakiet edytora", evidence_ids=["ev_old"])]
    )
    snapshot = SimpleNamespace(
        draft_package=SimpleNamespace(
            draft_package_result=SimpleNamespace(draft_package=unrelated_package)
        )
    )

    _validate_revision_sections(
        request,
        snapshot,
        latest_revision=latest,
        revision_context_current=True,
    )


def test_canonical_html_alignment_is_not_a_second_codex_proposal() -> None:
    command = _command(schema_version="wilq_content_draft_revision_v2")
    proposal_metadata = ContentDraftRevisionProposalMetadata(
        codex_run_id="codex_historical_proposal",
        selected_section_headings=[command.sections[0].heading],
        section_lineage=[{"heading": command.sections[0].heading, "evidence_ids": ["ev_lineage"]}],
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
                    "content_html": content_html_from_markdown(revision.sections[0].body_markdown)
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


def test_editor_child_is_not_a_replay_of_its_parent_codex_completion() -> None:
    command = _command(schema_version="wilq_content_draft_revision_v2")
    revision = build_stored_draft_revision(
        command.model_copy(
            update={
                "proposal_metadata": ContentDraftRevisionProposalMetadata(
                    codex_run_id="codex_parent_proposal",
                    selected_section_headings=[command.sections[0].heading],
                    section_lineage=[
                        {"heading": command.sections[0].heading, "evidence_ids": ["ev_lineage"]}
                    ],
                    quality_verdict="needs_changes",
                )
            }
        ),
        revision_number=2,
        content_digest="b" * 64,
    )
    request = ContentDraftRevisionSaveRequest(
        base_revision_id=revision.revision_id,
        title=revision.title,
        sections=[
            revision.sections[0].model_copy(
                update={
                    "body_markdown": "Tekst po ręcznej poprawce.",
                    "content_html": content_html_from_markdown("Tekst po ręcznej poprawce."),
                }
            )
        ],
        created_by="wilku",
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

    assert saved.proposal_metadata is None
