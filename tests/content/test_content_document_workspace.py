from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import wilq.content.workflow.document_lineage as lineage_module
import wilq.content.workflow.document_workspace as workspace_module
from wilq.content.workflow.catalog import ContentInventoryMaterialResponse
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
    ContentDraftRevisionSection,
)

WORK_ITEM_ID = "content_work_item_bdo"
SOURCE_URL = "https://www.ekologus.pl/bdo/"


def test_document_workspace_keeps_public_source_visible_when_no_revision_exists(
    monkeypatch,
) -> None:
    context = SimpleNamespace(
        work_kind="refresh_existing",
        service=SimpleNamespace(label="BDO i sprawozdawczość środowiskowa"),
        source_public=SimpleNamespace(
            url=SOURCE_URL,
            title="BDO dla firm",
            reason="Publiczny materiał jest dostępny.",
            material=SimpleNamespace(evidence_ids=["ev_wp_bdo"]),
        ),
    )
    material = ContentInventoryMaterialResponse(
        status="ready",
        url=SOURCE_URL,
        source_kind="wordpress_rest",
        title="BDO dla firm",
        content_text="Pierwszy akapit obecnej strony.\n\nDrugi akapit.",
        section_headings=["Kto powinien sprawdzić obowiązek?", "Ewidencja odpadów"],
        evidence_id="ev_wp_bdo",
        extraction_region="wordpress_rest.content",
    )
    monkeypatch.setattr(
        workspace_module,
        "build_content_decision_context",
        lambda work_item_id: context if work_item_id == WORK_ITEM_ID else None,
    )
    monkeypatch.setattr(
        workspace_module,
        "read_content_inventory_material",
        lambda _url: material,
    )
    monkeypatch.setattr(
        workspace_module,
        "content_workflow_store",
        lambda: SimpleNamespace(
            load_draft_revision_state=lambda _work_item_id: SimpleNamespace(
                status="empty", latest_revision=None
            )
        ),
    )

    workspace = workspace_module.build_content_document_workspace(WORK_ITEM_ID)

    assert workspace is not None
    assert workspace.source_snapshot.status == "available"
    assert workspace.source_snapshot.lead == "Pierwszy akapit obecnej strony."
    assert workspace.source_snapshot.evidence_ids == ["ev_wp_bdo"]
    assert workspace.source_snapshot.caveats == [
        (
            "FAQ i CTA nie są tu rozpoznawane heurystycznie; ich brak w tym widoku "
            "nie znaczy, że nie istnieją na stronie."
        ),
        "Odczyt źródła nie potwierdza miejsca authoringu ani mapowania dev.",
    ]
    assert [section.heading for section in workspace.source_snapshot.ordered_sections] == [
        "Kto powinien sprawdzić obowiązek?",
        "Ewidencja odpadów",
    ]
    assert workspace.canonical_document.status == "not_created"
    assert workspace.document_lineage.status == "not_recorded"
    assert workspace.document_lineage.knowledge_cards == []
    assert workspace.next_action.kind == "prepare_document"
    assert workspace.next_action.label == "Przygotuj nową wersję"


def test_document_workspace_exposes_only_exact_heading_pairs_for_comparison(
    monkeypatch,
) -> None:
    context = SimpleNamespace(
        work_kind="refresh_existing",
        service=SimpleNamespace(label="BDO i sprawozdawczość środowiskowa"),
        source_public=SimpleNamespace(
            url=SOURCE_URL,
            title="BDO dla firm",
            reason="Publiczny materiał jest dostępny.",
            material=SimpleNamespace(evidence_ids=["ev_wp_bdo"]),
        ),
    )
    material = ContentInventoryMaterialResponse(
        status="ready",
        url=SOURCE_URL,
        source_kind="wordpress_rest",
        title="BDO dla firm",
        content_text=(
            "Wprowadzenie.\n\n"
            "Ewidencja odpadów\n"
            "Aktualny opis ewidencji na obecnej stronie.\n\n"
            "Ewidencja odpadów\n"
            "Drugi aktualny opis ewidencji na obecnej stronie."
        ),
        section_headings=["Ewidencja odpadów", "Ewidencja odpadów"],
        evidence_id="ev_wp_bdo",
        extraction_region="wordpress_rest.content",
    )
    revision = SimpleNamespace(
        revision_id="content_revision_candidate",
        content_digest="a" * 64,
        title="Nowa wersja BDO",
        page_assets=SimpleNamespace(h1="Nowa wersja BDO", lead="Nowy lead."),
        sections=[
            SimpleNamespace(
                section_id="section_evidence",
                heading="Ewidencja odpadów",
                body_markdown="Nowy opis ewidencji.",
                content_html="<p>Nowy opis ewidencji.</p>",
            ),
            SimpleNamespace(
                section_id="section_risk",
                heading="Ryzyka formalne",
                body_markdown="Nowy opis ryzyk.",
                content_html="<p>Nowy opis ryzyk.</p>",
            ),
        ],
        faq=[],
        cta_blocks=[],
        source_material_ids=["ekologus_material_bdo"],
        knowledge_card_ids=["ekologus_service_bdo"],
    )
    monkeypatch.setattr(
        workspace_module,
        "build_content_decision_context",
        lambda work_item_id: context if work_item_id == WORK_ITEM_ID else None,
    )
    monkeypatch.setattr(workspace_module, "read_content_inventory_material", lambda _url: material)
    monkeypatch.setattr(
        lineage_module,
        "ekologus_content_knowledge_cards",
        lambda: (
            SimpleNamespace(
                id="ekologus_service_bdo",
                title="BDO i sprawozdawczość środowiskowa",
                summary="Karta przypisana do dokładnej rewizji.",
            ),
        ),
    )
    monkeypatch.setattr(
        workspace_module,
        "content_workflow_store",
        lambda: SimpleNamespace(
            load_draft_revision_state=lambda _work_item_id: SimpleNamespace(
                status="unreviewed", latest_revision=revision
            )
        ),
    )

    workspace = workspace_module.build_content_document_workspace(WORK_ITEM_ID)

    assert workspace is not None
    assert workspace.canonical_document.preview is not None
    assert [section.heading for section in workspace.canonical_document.preview.sections] == [
        "Ewidencja odpadów",
        "Ryzyka formalne",
    ]
    comparison_items = [
        (item.status, item.source_heading, item.document_heading)
        for item in workspace.comparison.items
    ]
    assert comparison_items == [
        ("same_heading", "Ewidencja odpadów", "Ewidencja odpadów"),
        ("document_only", None, "Ryzyka formalne"),
        ("source_only", "Ewidencja odpadów", None),
    ]


def test_document_workspace_fails_closed_for_unrecorded_lineage_and_incomplete_source(
    monkeypatch,
) -> None:
    revision = SimpleNamespace(
        revision_id="content_revision_candidate",
        content_digest="a" * 64,
        sections=[
            SimpleNamespace(
                section_id="section_risk",
                heading="Ryzyka formalne",
                body_markdown="Nowy opis ryzyk.",
            )
        ],
        source_material_ids=[],
        knowledge_card_ids=[],
    )
    assert lineage_module.build_content_document_lineage(None).status == "not_recorded"
    assert lineage_module.build_content_document_lineage(revision).status == "not_recorded"

    revision.knowledge_card_ids = ["missing_card"]
    monkeypatch.setattr(lineage_module, "ekologus_content_knowledge_cards", lambda: ())
    lineage = lineage_module.build_content_document_lineage(revision)
    assert lineage.status == "partial"
    assert lineage.unresolved_knowledge_card_ids == ["missing_card"]

    for status in ("unavailable", "partial"):
        source = workspace_module.ContentDocumentWorkspaceSourceSnapshot(
            status=status,
            reason="Źródło nie ma kompletnej struktury.",
        )
        comparison = workspace_module._comparison(source, revision)
        assert comparison.status == "unavailable"
        assert comparison.items == []


def test_canonical_document_carries_only_review_bound_to_exact_revision() -> None:
    revision = ContentDraftRevision(
        revision_id="content_revision_bdo",
        work_item_id=WORK_ITEM_ID,
        revision_number=1,
        content_digest="a" * 64,
        draft_package_id="content_draft_bdo",
        draft_package_digest="b" * 64,
        final_canonical_url=SOURCE_URL,
        title="BDO",
        sections=[
            ContentDraftRevisionSection(
                section_id="section_bdo",
                heading="Zakres",
                body_markdown="Sprawdź zakres obowiązków.",
            )
        ],
        created_by="wilku",
        created_at=datetime.now(UTC),
    )
    review = ContentDraftRevisionReview(
        decision_id="content_revision_review_bdo",
        decision_number=1,
        work_item_id=WORK_ITEM_ID,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        decision="approved",
        reviewed_by="wilku",
        checked_items=["Sprawdzono dokument."],
        evidence_ids=["ev_wp_bdo"],
        created_at=datetime.now(UTC),
    )

    document = workspace_module._canonical_document("approved", revision, review)

    assert document.revision is revision
    assert document.review is review
