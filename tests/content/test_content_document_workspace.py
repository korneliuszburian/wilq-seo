from __future__ import annotations

from types import SimpleNamespace

import wilq.content.workflow.document_workspace as workspace_module
from wilq.content.workflow.catalog import ContentInventoryMaterialResponse

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
    assert [section.heading for section in workspace.source_snapshot.ordered_sections] == [
        "Kto powinien sprawdzić obowiązek?",
        "Ewidencja odpadów",
    ]
    assert workspace.canonical_document.status == "not_created"
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
            "Kontakt\n"
            "Aktualne wezwanie do kontaktu."
        ),
        section_headings=["Ewidencja odpadów", "Kontakt"],
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
    )
    monkeypatch.setattr(
        workspace_module,
        "build_content_decision_context",
        lambda work_item_id: context if work_item_id == WORK_ITEM_ID else None,
    )
    monkeypatch.setattr(workspace_module, "read_content_inventory_material", lambda _url: material)
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
        ("source_only", "Kontakt", None),
    ]
