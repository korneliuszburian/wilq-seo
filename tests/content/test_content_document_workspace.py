from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import APIRouter

import apps.api.wilq_api.routers.content_document_workspace as document_workspace_router
import wilq.content.workflow.workspace.document_lineage as lineage_module
import wilq.content.workflow.workspace.document_workspace as workspace_module
import wilq.content.workflow.workspace.selected_workspace as selected_workspace_module
from apps.api.wilq_api.routers.content_document_workspace import (
    register_content_document_workspace_route,
)
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionPageAssets,
    ContentDraftRevisionReview,
    ContentDraftRevisionSection,
)
from wilq.content.workflow.pipeline_steps.operator_steps import (
    ContentWorkflowOperatorFacts,
    build_content_workflow_operator_journey,
)
from wilq.content.workflow.workspace.catalog import ContentInventoryMaterialResponse

WORK_ITEM_ID = "content_work_item_bdo"
SOURCE_URL = "https://www.ekologus.pl/bdo/"


def _no_candidates(*_args, **_kwargs) -> list[object]:
    return []


def _full_revision() -> ContentDraftRevision:
    return ContentDraftRevision(
        schema_version="wilq_content_draft_revision_v2",
        revision_id="content_revision_bdo_full",
        work_item_id=WORK_ITEM_ID,
        revision_number=2,
        content_digest="a" * 64,
        draft_package_id="content_draft_bdo",
        draft_package_digest="b" * 64,
        planning_digest="c" * 64,
        planning_input_digest="d" * 64,
        service_card_id="ekologus_service_bdo_reporting",
        service_digest="e" * 64,
        inventory_digest="f" * 64,
        final_canonical_url=SOURCE_URL,
        title="BDO",
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="BDO",
            meta_title="BDO dla firm",
            meta_description="Sprawdź obowiązki BDO swojej firmy.",
            h1="BDO dla firm",
            lead="Sprawdź obowiązki swojej firmy.",
        ),
        sections=[
            ContentDraftRevisionSection(
                section_id="section_bdo",
                heading="Zakres",
                body_markdown="Sprawdź zakres obowiązków.",
                evidence_ids=["ev_wp_bdo"],
            )
        ],
        created_by="wilku",
        created_at=datetime.now(UTC),
    )


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
    assert workspace.source_snapshot.status_label == "materiał dostępny"
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


def test_document_workspace_projects_claim_ledger_onto_full_revision(
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
        content_text="Aktualny materiał strony.",
        evidence_id="ev_wp_bdo",
    )
    revision = _full_revision()
    item = ContentWorkItem(
        id=WORK_ITEM_ID,
        topic="BDO dla firm",
        evidence_ids=["ev_wp_bdo"],
        source_connectors=["wordpress_ekologus"],
    )
    monkeypatch.setattr(
        workspace_module,
        "build_content_decision_context",
        lambda _id, **_kwargs: context,
    )
    monkeypatch.setattr(workspace_module, "read_content_inventory_material", lambda _url: material)
    monkeypatch.setattr(workspace_module, "_regulatory_review_candidates", _no_candidates)
    monkeypatch.setattr(
        workspace_module,
        "content_workflow_store",
        lambda: SimpleNamespace(
            load_draft_revision_state=lambda _work_item_id: SimpleNamespace(
                status="unreviewed",
                latest_revision=revision,
            )
        ),
    )

    monkeypatch.setattr(
        selected_workspace_module,
        "build_content_document_workspace",
        workspace_module.build_content_document_workspace,
    )

    selected = selected_workspace_module.build_content_selected_workspace(
        WORK_ITEM_ID,
        operator_journey=build_content_workflow_operator_journey(
            ContentWorkflowOperatorFacts(
                sales_brief_present=True,
                sales_brief_signal_status="strong",
                sales_brief_signal_reason="Źródła są gotowe.",
                sales_brief_safe_next_step="Przejdź do planu sekcji.",
                sales_brief_blocker=None,
                section_map_present=True,
                section_map_blocker=None,
                section_map_safe_next_step="Przejdź do szkicu.",
                structured_contract_present=True,
                structured_contract_blocker=None,
                structured_contract_safe_next_step="Sprawdź szkic.",
                revision_workspace_status="unreviewed",
            )
        ),
        item=item,
    )

    assert selected.status == "ready"
    workspace = selected.workspace
    assert workspace is not None
    projected_revision = workspace.canonical_document.revision
    assert projected_revision is not None
    assert projected_revision.claim_ledger is not None
    assert projected_revision.claim_ledger.work_item_id == WORK_ITEM_ID
    assert projected_revision.claim_ledger.entries
    assert projected_revision.claim_ledger.entries[0].evidence_ids == ["ev_wp_bdo"]
    assert revision.claim_ledger is None


def test_document_workspace_keeps_legacy_revision_without_claim_ledger() -> None:
    revision = ContentDraftRevision(
        revision_id="content_revision_bdo_legacy",
        work_item_id=WORK_ITEM_ID,
        revision_number=1,
        content_digest="a" * 64,
        draft_package_id="content_draft_bdo",
        draft_package_digest="b" * 64,
        final_canonical_url=SOURCE_URL,
        title="BDO",
        sections=[
            ContentDraftRevisionSection(
                heading="Zakres",
                body_markdown="Sprawdź zakres obowiązków.",
            )
        ],
        created_by="wilku",
        created_at=datetime.now(UTC),
    )
    item = ContentWorkItem(
        id=WORK_ITEM_ID,
        topic="BDO dla firm",
        evidence_ids=["ev_wp_bdo"],
        source_connectors=["wordpress_ekologus"],
    )

    projected = workspace_module._revision_with_claim_ledger(revision, item=item)

    assert projected is revision
    assert projected.claim_ledger is None


def test_document_workspace_route_projects_ledger_only_for_full_revision(
    monkeypatch,
) -> None:
    legacy_work_item_id = "content_work_item_bdo_legacy"
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
        content_text="Aktualny materiał strony.",
        evidence_id="ev_wp_bdo",
    )
    legacy_revision = ContentDraftRevision(
        revision_id="content_revision_bdo_legacy_route",
        work_item_id=legacy_work_item_id,
        revision_number=1,
        content_digest="a" * 64,
        draft_package_id="content_draft_bdo_legacy",
        draft_package_digest="b" * 64,
        final_canonical_url=SOURCE_URL,
        title="BDO",
        sections=[
            ContentDraftRevisionSection(
                heading="Zakres",
                body_markdown="Sprawdź zakres obowiązków.",
            )
        ],
        created_by="wilku",
        created_at=datetime.now(UTC),
    )
    revisions = {
        WORK_ITEM_ID: _full_revision(),
        legacy_work_item_id: legacy_revision,
    }
    items = {
        work_item_id: ContentWorkItem(
            id=work_item_id,
            topic="BDO dla firm",
            evidence_ids=["ev_wp_bdo"],
            source_connectors=["wordpress_ekologus"],
        )
        for work_item_id in revisions
    }
    monkeypatch.setattr(
        workspace_module,
        "build_content_decision_context",
        lambda _id, **_kwargs: context,
    )
    monkeypatch.setattr(workspace_module, "read_content_inventory_material", lambda _url: material)
    monkeypatch.setattr(workspace_module, "_regulatory_review_candidates", _no_candidates)
    monkeypatch.setattr(
        workspace_module,
        "content_workflow_store",
        lambda: SimpleNamespace(
            load_draft_revision_state=lambda work_item_id: SimpleNamespace(
                status="unreviewed",
                latest_revision=revisions[work_item_id],
            )
        ),
    )
    monkeypatch.setattr(
        document_workspace_router,
        "snapshot_for_work_item_or_404",
        lambda work_item_id: SimpleNamespace(
            revision_workspace=SimpleNamespace(context_current=False),
            preflight=SimpleNamespace(item=items[work_item_id]),
        ),
    )
    router = APIRouter()
    register_content_document_workspace_route(router)
    endpoint = next(
        route.endpoint
        for route in router.routes
        if getattr(route, "path", "").endswith("/document-workspace")
    )
    full_workspace = endpoint(WORK_ITEM_ID)
    legacy_workspace = endpoint(legacy_work_item_id)

    full_revision = full_workspace.canonical_document.revision
    assert full_revision is not None
    assert full_revision.claim_ledger is not None
    assert full_revision.claim_ledger.work_item_id == WORK_ITEM_ID
    assert full_revision.claim_ledger.entries
    assert full_revision.claim_ledger.entries[0].evidence_ids == ["ev_wp_bdo"]
    assert full_workspace.service_label == "BDO i sprawozdawczość środowiskowa"
    assert full_workspace.next_action.label == "Przygotuj świeżą wersję"
    projected_legacy_revision = legacy_workspace.canonical_document.revision
    assert projected_legacy_revision is not None
    assert projected_legacy_revision.claim_ledger is None


def test_source_snapshot_projects_api_owned_label_for_each_status() -> None:
    context = SimpleNamespace(
        source_public=SimpleNamespace(
            url=SOURCE_URL,
            title="BDO dla firm",
            reason="Publiczny materiał jest dostępny.",
            material=SimpleNamespace(evidence_ids=["ev_wp_bdo"]),
        )
    )
    available_material = ContentInventoryMaterialResponse(
        status="ready",
        url=SOURCE_URL,
        source_kind="wordpress_rest",
        content_text="Aktualny materiał strony.",
    )
    partial_material = available_material.model_copy(update={"content_text": None})

    snapshots = [
        workspace_module._source_snapshot(context, available_material),
        workspace_module._source_snapshot(context, partial_material),
        workspace_module._source_snapshot(context, None),
    ]

    assert [(snapshot.status, snapshot.status_label) for snapshot in snapshots] == [
        ("available", "materiał dostępny"),
        ("partial", "materiał częściowy"),
        ("unavailable", "materiał niedostępny"),
    ]


def test_persisted_material_does_not_promote_summary_only_metadata() -> None:
    item = ContentWorkItem(
        id=WORK_ITEM_ID,
        topic="BDO dla firm",
        wordpress_content_summary="Utrwalone podsumowanie bez treści i struktury.",
        wordpress_content_inventory_status="available",
    )

    material = workspace_module._persisted_material_from_item(item, url=SOURCE_URL)

    assert material is None


def test_document_workspace_projects_one_repair_action_after_human_changes() -> None:
    document = workspace_module.ContentDocumentWorkspaceDocument(
        status="needs_changes",
        review_state="needs_changes",
        label="Tekst wymaga zmian",
        reason="Marketer zapisał dokładne uwagi do dokumentu.",
    )

    action = workspace_module._next_action(document)

    assert action.kind == "repair_document"
    assert action.label == "Przygotuj poprawkę"


def test_stale_revision_stays_readable_but_cannot_offer_review() -> None:
    document = workspace_module.ContentDocumentWorkspaceDocument.model_construct(
        status="unreviewed",
        review_state="unreviewed",
        label="Nowa wersja czeka na review",
        reason="Dokument czeka na decyzję człowieka.",
        revision=SimpleNamespace(revision_id="content_revision_old"),
    )

    projected = workspace_module._document_for_current_context(
        document,
        revision_context_current=False,
    )
    action = workspace_module._next_action(
        projected,
        revision_context_current=False,
    )

    assert projected.revision is document.revision
    assert projected.label == "Wersja pochodzi z wcześniejszego planu"
    assert "Nie można zapisać" in projected.reason
    assert action.kind == "prepare_document"
    assert action.label == "Przygotuj świeżą wersję"


def test_document_workspace_uses_revision_service_binding_for_official_review_candidates(
    monkeypatch,
) -> None:
    revision = SimpleNamespace(service_card_id="ekologus_service_bdo_reporting")
    candidate = SimpleNamespace(candidate_id="bdo_sanctions")
    coverage = SimpleNamespace()
    seen: dict[str, object] = {}
    monkeypatch.setattr(workspace_module, "ekologus_source_facts", lambda: ("fact",))
    monkeypatch.setattr(
        workspace_module,
        "regulatory_content_coverage",
        lambda *, service_card_id, canonical_path, source_facts: seen.update(
            service_card_id=service_card_id,
            canonical_path=canonical_path,
            source_facts=source_facts,
        ) or coverage,
    )
    monkeypatch.setattr(
        workspace_module,
        "regulatory_review_candidates",
        lambda *, service_card_id, canonical_path, coverage: [candidate]
        if service_card_id == "ekologus_service_bdo_reporting"
        and canonical_path is None
        and coverage is not None
        else [],
    )

    candidates = workspace_module._regulatory_review_candidates(revision)

    assert candidates == [candidate]
    assert seen == {
        "service_card_id": "ekologus_service_bdo_reporting",
        "canonical_path": None,
        "source_facts": ("fact",),
    }


def test_document_workspace_prefers_editorial_path_over_legacy_revision_service(
    monkeypatch,
) -> None:
    candidate = SimpleNamespace(candidate_id="integrated_permit_candidate")
    coverage = SimpleNamespace()
    item = ContentWorkItem(
        id="content_work_item_integrated_permit",
        topic="Analiza pozwoleń zintegrowanych",
        final_canonical_url="https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/",
        content_kind="editorial",
    )
    seen: dict[str, object] = {}
    monkeypatch.setattr(workspace_module, "ekologus_source_facts", lambda: ("fact",))
    monkeypatch.setattr(
        workspace_module,
        "regulatory_content_coverage",
        lambda *, service_card_id, canonical_path, source_facts: seen.update(
            service_card_id=service_card_id,
            canonical_path=canonical_path,
            source_facts=source_facts,
        ) or coverage,
    )
    monkeypatch.setattr(
        workspace_module,
        "regulatory_review_candidates",
        lambda *, service_card_id, canonical_path, coverage: [candidate]
        if service_card_id is None
        and canonical_path == "/analiza-pozwolen-zintegrowanych"
        and coverage is not None
        else [],
    )

    legacy_revision = SimpleNamespace(service_card_id="ekologus_service_operat_wodnoprawny")
    candidates = workspace_module._regulatory_review_candidates(legacy_revision, item=item)

    assert candidates == [candidate]
    assert seen == {
        "service_card_id": None,
        "canonical_path": "/analiza-pozwolen-zintegrowanych",
        "source_facts": ("fact",),
    }


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
        source_provenance=[],
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
                card_type="service",
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
    assert workspace.document_lineage.knowledge_cards[0].card_type == "service"


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
            status_label=(
                "materiał niedostępny" if status == "unavailable" else "materiał częściowy"
            ),
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
