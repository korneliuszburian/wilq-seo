from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from wilq.content.drafts.package import (
    ContentDraftEvidenceMap,
    ContentDraftPackage,
    ContentDraftSection,
)
from wilq.content.handoff.revision_document_renderer import revision_document_markdown
from wilq.content.handoff.revision_wordpress import (
    build_revision_bound_wordpress_draft_handoff,
)
from wilq.content.handoff.wordpress_execution import (
    execute_content_wordpress_draft_handoff,
)
from wilq.content.workflow.models import ContentWorkItem
from wilq.content.workflow.revision_children import build_child_draft_revision_command
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionProposalMetadata,
    ContentDraftRevisionProposalSectionLineage,
    ContentDraftRevisionReviewCommand,
    content_draft_package_digest,
)
from wilq.content.workflow.store import ContentWorkflowStore


def test_full_document_v2_round_trips_and_renders_without_losing_assets(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    package = _draft_package()
    legacy_command = _legacy_command(package)
    legacy = store.append_draft_revision(legacy_command).revision
    assert legacy is not None
    assert legacy.schema_version == "wilq_content_draft_revision_v1"
    assert legacy.content_digest == _legacy_digest(legacy_command)
    assert legacy.page_assets is None

    command = _full_document_command(package, base_revision_id=legacy.revision_id)
    created = store.append_draft_revision(command).revision
    assert created is not None
    assert created.schema_version == "wilq_content_draft_revision_v2"
    assert created.page_assets == command.page_assets
    assert created.sections == command.sections
    assert created.faq == command.faq
    assert created.cta_blocks == command.cta_blocks
    assert created.internal_links == command.internal_links

    review = store.review_draft_revision(
        ContentDraftRevisionReviewCommand(
            work_item_id=created.work_item_id,
            revision_id=created.revision_id,
            revision_digest=created.content_digest,
            decision="approved",
            reviewed_by="wilku",
            checked_items=["pełny dokument", "dowody", "meta", "CTA", "linki"],
            evidence_ids=["ev_wp", "ev_gsc"],
        )
    ).review
    assert review is not None
    state = store.load_draft_revision_state(created.work_item_id)
    assert state.status == "approved"
    assert state.latest_revision == created

    handoff = build_revision_bound_wordpress_draft_handoff(
        item=_work_item(),
        draft_package=package,
        revision_state=state,
        planning_digest=created.planning_digest,
        planning_input_digest=created.planning_input_digest,
        service_card_id=created.service_card_id,
    ).handoff
    assert handoff is not None
    assert handoff.revision_document == created
    dry_run = execute_content_wordpress_draft_handoff(
        handoff=handoff,
        draft_package=package,
        mode="dry_run",
    )
    assert dry_run.status == "dry_run_ready"
    assert dry_run.payload is not None
    assert dry_run.payload.title == "Doradztwo środowiskowe dla firm"
    assert dry_run.payload.meta_title == "Doradztwo środowiskowe — Ekologus"
    assert dry_run.payload.meta_description == "Sprawdź zakres bez zgadywania obowiązków."
    assert dry_run.payload.meta_write_status == "review_required"
    assert dry_run.payload.metadata_blockers[0].code == "missing_wordpress_meta_mapping"
    assert dry_run.payload.content_markdown == _expected_markdown()

    stale_handoff = build_revision_bound_wordpress_draft_handoff(
        item=_work_item(),
        draft_package=package,
        revision_state=state,
        planning_digest=created.planning_digest,
        planning_input_digest="9" * 64,
        service_card_id=created.service_card_id,
    )
    assert stale_handoff.handoff is None
    assert [blocker.code for blocker in stale_handoff.blockers] == ["revision_context_changed"]

    _assert_child_command_preserves_full_document(created)

    changed = command.model_copy(
        update={
            "base_revision_id": created.revision_id,
            "page_assets": command.page_assets.model_copy(
                update={"meta_description": "Zmieniony opis meta."}
            )
            if command.page_assets is not None
            else None,
        }
    )
    changed_revision = store.append_draft_revision(changed).revision
    assert changed_revision is not None
    assert changed_revision.content_digest != created.content_digest
    changed_state = store.load_draft_revision_state(created.work_item_id)
    assert changed_state.status == "unreviewed"
    assert changed_state.latest_review is None


def test_renderer_escapes_an_unsafe_historical_internal_link_anchor(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    package = _draft_package()
    legacy = store.append_draft_revision(_legacy_command(package)).revision
    assert legacy is not None
    created = store.append_draft_revision(
        _full_document_command(package, base_revision_id=legacy.revision_id)
    ).revision
    assert created is not None
    unsafe_historical = created.model_copy(
        update={
            "schema_version": "wilq_content_draft_revision_v1",
            "internal_links": [
                created.internal_links[0].model_copy(
                    update={
                        "anchor_text": "Kontakt](https://example.com/phish)[dalej",
                        "target_url": (
                            "https://www.ekologus.pl/kontakt) "
                            "[phish](https://example.com"
                        ),
                    }
                )
            ],
        }
    )

    escaped_historical = revision_document_markdown(unsafe_historical)

    assert "[Kontakt](https://example.com/phish)" not in escaped_historical
    assert "](https://example.com)" not in escaped_historical
    assert "Kontakt\\](https://example.com/phish)\\[dalej" in escaped_historical


def test_every_page_asset_changes_the_full_document_digest(tmp_path: Path) -> None:
    package = _draft_package()
    replacements = {
        "wordpress_title": "Nowy tytuł WordPress",
        "meta_title": "Nowy meta title",
        "meta_description": "Nowy meta description",
        "h1": "Nowy nagłówek H1",
        "lead": "Nowy lead dokumentu.",
    }
    for field, value in replacements.items():
        store = ContentWorkflowStore(tmp_path / field / "wilq.sqlite3")
        legacy = store.append_draft_revision(_legacy_command(package)).revision
        assert legacy is not None
        baseline_command = _full_document_command(
            package,
            base_revision_id=legacy.revision_id,
        )
        baseline = store.append_draft_revision(baseline_command).revision
        assert baseline is not None
        assert baseline_command.page_assets is not None
        changed_assets = baseline_command.page_assets.model_copy(update={field: value})
        changed_command = baseline_command.model_copy(
            update={
                "base_revision_id": baseline.revision_id,
                "title": (value if field == "wordpress_title" else baseline_command.title),
                "page_assets": changed_assets,
            }
        )
        changed = store.append_draft_revision(changed_command).revision
        assert changed is not None
        assert changed.content_digest != baseline.content_digest


@pytest.mark.parametrize(
    "invalid_link",
    [
        {
            "link_id": "link_without_lineage",
            "placement": "section_when_support",
            "target_url": "https://www.ekologus.pl/kontakt/",
            "anchor_text": "Kontakt",
            "evidence_ids": [" "],
        },
        {
            "link_id": "link_external",
            "placement": "section_when_support",
            "target_url": "https://example.com/kontakt/",
            "anchor_text": "Kontakt",
            "evidence_ids": ["ev_wp"],
        },
        {
            "link_id": "link_destination_injection",
            "placement": "section_when_support",
            "target_url": "https://www.ekologus.pl/kontakt) [phish](https://example.com",
            "anchor_text": "Kontakt",
            "evidence_ids": ["ev_wp"],
        },
    ],
)
def test_full_document_v2_rejects_untraced_or_external_internal_links(
    invalid_link: dict[str, object],
) -> None:
    command = _full_document_command(_draft_package(), base_revision_id="content_revision_base")
    payload = command.model_dump(mode="json")
    payload["internal_links"] = [invalid_link]

    with pytest.raises(ValidationError):
        ContentDraftRevisionAppendCommand.model_validate(payload)


def test_full_document_v2_requires_section_evidence_lineage() -> None:
    command = _full_document_command(_draft_package(), base_revision_id="content_revision_base")
    payload = command.model_dump(mode="json")
    payload["sections"][0]["evidence_ids"] = []

    with pytest.raises(ValidationError):
        ContentDraftRevisionAppendCommand.model_validate(payload)


@pytest.mark.parametrize(
    ("collection", "field"),
    [
        ("page_assets", "lead"),
        ("sections", "heading"),
        ("sections", "body_markdown"),
        ("faq", "answer_markdown"),
        ("cta_blocks", "body_markdown"),
    ],
)
def test_full_document_v2_rejects_inline_links_in_generated_text(
    collection: str,
    field: str,
) -> None:
    command = _full_document_command(_draft_package(), base_revision_id="content_revision_base")
    payload = command.model_dump(mode="json")
    target = payload[collection] if collection == "page_assets" else payload[collection][0]
    target[field] = "Treść [phish](https://example.com)."

    with pytest.raises(ValidationError):
        ContentDraftRevisionAppendCommand.model_validate(payload)


@pytest.mark.parametrize(
    "inline_link",
    [
        '<a\thref\t=\t"//example.com/phish">kliknij</a>',
        "[phish]: //example.com/phish\nKliknij [phish]",
    ],
)
def test_full_document_v2_rejects_indirect_inline_link_syntax(
    inline_link: str,
) -> None:
    command = _full_document_command(_draft_package(), base_revision_id="content_revision_base")
    payload = command.model_dump(mode="json")
    payload["sections"][0]["body_markdown"] = inline_link

    with pytest.raises(ValidationError):
        ContentDraftRevisionAppendCommand.model_validate(payload)


def test_full_document_v2_rejects_blank_visible_page_content() -> None:
    command = _full_document_command(_draft_package(), base_revision_id="content_revision_base")
    invalid_paths = (
        ("faq", "answer_markdown"),
        ("cta_blocks", "body_markdown"),
        ("internal_links", "anchor_text"),
    )

    for collection, field in invalid_paths:
        payload = command.model_dump(mode="json")
        payload[collection][0][field] = "   "

        with pytest.raises(ValidationError):
            ContentDraftRevisionAppendCommand.model_validate(payload)


def _draft_package() -> ContentDraftPackage:
    return ContentDraftPackage(
        id="draft_package_consulting",
        work_item_id="content_work_item_consulting",
        brief_id="brief_consulting",
        claim_ledger_id="claim_ledger_consulting",
        title="Doradztwo środowiskowe dla firm",
        sections=[
            ContentDraftSection(
                heading="Kiedy firma potrzebuje wsparcia",
                purpose="Wyjaśnić moment decyzji.",
                evidence_ids=["ev_wp", "ev_gsc"],
            )
        ],
        section_to_evidence_map=[
            ContentDraftEvidenceMap(
                section_heading="Kiedy firma potrzebuje wsparcia",
                evidence_ids=["ev_wp", "ev_gsc"],
            )
        ],
        publish_ready=False,
    )


def _assert_child_command_preserves_full_document(created: ContentDraftRevision) -> None:
    child_command = build_child_draft_revision_command(
        created,
        sections=[
            created.sections[0].model_copy(update={"body_markdown": "Poprawiona treść sekcji."})
        ],
        proposal_metadata=ContentDraftRevisionProposalMetadata(
            codex_run_id="codex_run_child",
            selected_section_headings=[created.sections[0].heading],
            section_lineage=[
                ContentDraftRevisionProposalSectionLineage(
                    heading=created.sections[0].heading,
                    evidence_ids=created.sections[0].evidence_ids,
                )
            ],
            quality_verdict="needs_changes",
            quality_finding_codes=["semantic_review_required"],
        ),
        created_by="wilku",
    )
    assert child_command.schema_version == "wilq_content_draft_revision_v2"
    assert child_command.planning_input_digest == created.planning_input_digest
    assert child_command.service_card_id == created.service_card_id
    assert child_command.service_digest == created.service_digest
    assert child_command.inventory_digest == created.inventory_digest
    assert child_command.page_assets == created.page_assets
    assert child_command.faq == created.faq
    assert child_command.cta_blocks == created.cta_blocks
    assert child_command.internal_links == created.internal_links


def _legacy_command(package: ContentDraftPackage) -> ContentDraftRevisionAppendCommand:
    return ContentDraftRevisionAppendCommand(
        work_item_id=package.work_item_id,
        draft_package_id=package.id,
        draft_package_digest=content_draft_package_digest(package),
        planning_digest="1" * 64,
        final_canonical_url="https://www.ekologus.pl/oferta/doradztwo/",
        title=package.title,
        sections=[
            {
                "heading": "Kiedy firma potrzebuje wsparcia",
                "body_markdown": "Starsza treść sekcji.",
                "evidence_ids": ["ev_wp"],
            }
        ],
        created_by="wilku",
    )


def _full_document_command(
    package: ContentDraftPackage,
    *,
    base_revision_id: str,
) -> ContentDraftRevisionAppendCommand:
    return ContentDraftRevisionAppendCommand(
        schema_version="wilq_content_draft_revision_v2",
        work_item_id=package.work_item_id,
        base_revision_id=base_revision_id,
        draft_package_id=package.id,
        draft_package_digest=content_draft_package_digest(package),
        planning_digest="2" * 64,
        planning_input_digest="3" * 64,
        service_card_id="ekologus_service_environmental_consulting_outsourcing",
        service_digest="4" * 64,
        inventory_digest="5" * 64,
        final_canonical_url="https://www.ekologus.pl/oferta/doradztwo/",
        title="Doradztwo środowiskowe dla firm",
        page_assets={
            "wordpress_title": "Doradztwo środowiskowe dla firm",
            "meta_title": "Doradztwo środowiskowe — Ekologus",
            "meta_description": "Sprawdź zakres bez zgadywania obowiązków.",
            "h1": "Kiedy doradztwo środowiskowe pomaga firmie",
            "lead": "Najpierw sprawdź sytuację firmy i zakres potrzebnego wsparcia.",
        },
        sections=[
            {
                "section_id": "section_when_support",
                "heading": "Kiedy firma potrzebuje wsparcia",
                "body_markdown": "Wsparcie warto dopasować do sytuacji i obowiązków firmy.",
                "query_terms": ["outsourcing środowiskowy"],
                "evidence_ids": ["ev_wp", "ev_gsc"],
                "claim_ids": ["claim_consulting_scope"],
            }
        ],
        faq=[
            {
                "faq_id": "faq_start",
                "question": "Od czego zacząć?",
                "answer_markdown": "Od zebrania informacji o działalności i obowiązkach.",
                "query_terms": ["doradztwo środowiskowe"],
                "evidence_ids": ["ev_wp"],
                "claim_ids": [],
            }
        ],
        cta_blocks=[
            {
                "cta_id": "cta_consultation",
                "placement": "after_content",
                "body_markdown": "Opisz sytuację firmy i poproś o weryfikację zakresu.",
                "evidence_ids": ["ev_wp"],
                "claim_ids": [],
            }
        ],
        internal_links=[
            {
                "link_id": "link_contact",
                "placement": "section_when_support",
                "target_url": "https://www.ekologus.pl/kontakt/",
                "anchor_text": "Skontaktuj się z Ekologus",
                "evidence_ids": ["ev_wp"],
                "claim_ids": [],
            }
        ],
        created_by="wilku",
    )


def _work_item() -> ContentWorkItem:
    return ContentWorkItem(
        id="content_work_item_consulting",
        topic="Doradztwo środowiskowe",
        source_public_url="https://www.ekologus.pl/oferta/doradztwo/",
        final_canonical_url="https://www.ekologus.pl/oferta/doradztwo/",
        intended_final_url="https://www.ekologus.pl/oferta/doradztwo/",
        evidence_ids=["ev_wp", "ev_gsc"],
        source_connectors=["wordpress_ekologus", "google_search_console"],
        inventory_status="resolved",
        canonical_status="resolved",
        duplicate_status="checked",
        preflight_status="handoff_allowed",
        preserve_first_plan_status="approved",
        sales_brief_status="approved",
        claim_ledger_status="approved",
        draft_package_status="ready",
        human_review_status="approved",
        audit_status="recorded",
    )


def _legacy_digest(command: ContentDraftRevisionAppendCommand) -> str:
    payload = {
        "work_item_id": command.work_item_id,
        "draft_package_id": command.draft_package_id,
        "draft_package_digest": command.draft_package_digest,
        "planning_digest": command.planning_digest,
        "final_canonical_url": command.final_canonical_url,
        "title": command.title,
        "sections": [
            {
                "heading": section.heading,
                "body_markdown": section.body_markdown,
                "evidence_ids": section.evidence_ids,
            }
            for section in command.sections
        ],
        "publish_ready": False,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def _expected_markdown() -> str:
    return "\n\n".join(
        [
            "# Kiedy doradztwo środowiskowe pomaga firmie",
            "Najpierw sprawdź sytuację firmy i zakres potrzebnego wsparcia.",
            "## Kiedy firma potrzebuje wsparcia",
            "Wsparcie warto dopasować do sytuacji i obowiązków firmy.",
            "[Skontaktuj się z Ekologus](https://www.ekologus.pl/kontakt/)",
            "## Najczęstsze pytania",
            "### Od czego zacząć?",
            "Od zebrania informacji o działalności i obowiązkach.",
            "Opisz sytuację firmy i poproś o weryfikację zakresu.",
        ]
    )
