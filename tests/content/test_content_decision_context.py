from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import wilq.content.workflow.decision_context as decision_context_module
from apps.api.wilq_api.routers import content_decision_context as decision_context_route
from wilq.content.workflow.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    ContentInventoryMaterialResponse,
)
from wilq.schemas import ContentDecisionItem, ContentFreshnessAssessment, MetricFact

BDO_WORK_ITEM_ID = "content_work_item_bdo"
BDO_URL = "https://www.ekologus.pl/bdo/"


def _bdo_decision() -> ContentDecisionItem:
    return ContentDecisionItem(
        id="bdo",
        decision_type="refresh_or_merge",
        status="ready",
        title="BDO dla firm",
        primary_query="bdo dla firm",
        priority=1,
        source_public_url=BDO_URL,
        final_canonical_url=BDO_URL,
        total_clicks=0,
        total_impressions=181,
        best_average_position=9.07,
        query_count=13,
        source_connectors=["google_search_console", "wordpress_ekologus"],
        evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
        metric_facts=[
            MetricFact(
                name="impressions",
                value=181,
                period="2026-07-01/2026-07-21",
                source_connector="google_search_console",
                evidence_id="ev_gsc_bdo",
                dimensions={"page": BDO_URL},
            )
        ],
        rationale="Istniejąca strona wymaga weryfikacji.",
        next_step="Odśwież GSC przed decyzją.",
    )
def _bdo_catalog() -> ContentInventoryCatalogResponse:
    return ContentInventoryCatalogResponse(
        total_count=1,
        ready_count=1,
        items=[
            ContentInventoryCatalogItem(
                catalog_id="catalog_bdo",
                work_item_id=BDO_WORK_ITEM_ID,
                url=BDO_URL,
                path="/bdo/",
                title="BDO dla firm",
                content_type="sitemap",
                material_status="content_and_structure",
                source_connector="wordpress_ekologus",
                evidence_id="ev_wp_bdo",
                collected_at=datetime(2026, 7, 22, tzinfo=UTC),
                content_word_count=120,
                section_count=2,
                metrics_status="available",
                metrics_impressions=181,
            )
        ],
    )
def _bdo_material() -> ContentInventoryMaterialResponse:
    return ContentInventoryMaterialResponse(
        status="ready",
        url=BDO_URL,
        source_kind="wordpress_rest",
        title="BDO dla firm",
        content_text="Treść strony BDO.",
        content_word_count=120,
        section_headings=["Kogo dotyczy BDO", "Jak zacząć"],
        evidence_id="ev_wp_bdo",
        extraction_region="wordpress_rest.content",
    )
def _stale_gsc_freshness() -> ContentFreshnessAssessment:
    return ContentFreshnessAssessment(
        state="stale",
        state_label="wymaga odświeżenia",
        requires_refresh=True,
        stale_connector_ids=["google_search_console"],
        connector_labels_requiring_refresh=["Google Search Console"],
        summary="GSC jest nieświeże dla tej decyzji.",
        next_step="Odśwież Google Search Console.",
    )

def _patch_bdo_dependencies(monkeypatch) -> None:
    decision = _bdo_decision()
    catalog = _bdo_catalog()
    material = _bdo_material()
    freshness = _stale_gsc_freshness()
    monkeypatch.setattr(
        decision_context_module,
        "inventory_decision_for_work_item",
        lambda work_item_id, **_kwargs: decision if work_item_id == BDO_WORK_ITEM_ID else None,
    )
    monkeypatch.setattr(
        decision_context_module,
        "build_content_inventory_catalog_cached",
        lambda: catalog,
    )
    monkeypatch.setattr(
        decision_context_module,
        "read_content_inventory_material",
        lambda _url, *, catalog: material,
    )
    monkeypatch.setattr(
        decision_context_module,
        "build_content_freshness_assessment_fast",
        lambda **_kwargs: freshness,
    )
    monkeypatch.setattr(
        decision_context_module,
        "build_wordpress_authoring_profile",
        lambda *_args, **_kwargs: SimpleNamespace(
            authoring_target="staging",
            write_boundary=SimpleNamespace(allowed_operation="create_wordpress_draft"),
        ),
    )
    monkeypatch.setattr(
        decision_context_module,
        "build_content_work_item_service_profile_context",
        lambda *_args, **_kwargs: SimpleNamespace(
            service_label="BDO i sprawozdawczość środowiskowa",
            reason="Usługa pochodzi z dopasowanej karty Service Profile.",
        ),
    )

def test_decision_context_keeps_missing_object_and_dev_target_explicit(monkeypatch) -> None:
    _patch_bdo_dependencies(monkeypatch)

    context = decision_context_module.build_content_decision_context(BDO_WORK_ITEM_ID)

    assert context is not None
    assert context.work_kind == "refresh_existing"
    assert context.source_public.identity_status == "partial"
    assert context.source_public.object_id is None
    assert context.source_public.post_type is None
    assert context.source_public.post_status is None
    assert context.source_public.template is None
    assert context.source_public.material.observed_surfaces == ["wordpress_rest_content"]
    assert context.source_public.material.evidence_ids == ["ev_wp_bdo"]
    assert context.applicable_signals
    signal_evidence_ids = {
        evidence_id
        for signal in context.applicable_signals
        for evidence_id in signal.evidence_ids
    }
    assert signal_evidence_ids == {"ev_gsc_bdo"}
    assert not set(context.source_public.material.evidence_ids).intersection(
        signal_evidence_ids
    )
    assert context.authoring_target.mapping_status == "unverified"
    assert context.authoring_target.object_id is None
    assert context.source_target_relation.status == "unverified"
    assert context.object_readiness.status == "review_required"
    assert context.evidence_readiness.status == "refresh_required"
    assert context.delivery_capability.request_status == "blocked"
    assert context.service.label == "BDO i sprawozdawczość środowiskowa"
    assert context.next_safe_action.kind == "refresh_connector"
    assert context.next_safe_action.connector_id == "google_search_console"
    assert "target_id" not in context.model_dump()


def test_gsc_signals_omit_aggregate_evidence_without_exact_landing_fact(monkeypatch) -> None:
    _patch_bdo_dependencies(monkeypatch)
    decision_without_landing_fact = _bdo_decision().model_copy(
        update={"metric_facts": []}
    )
    monkeypatch.setattr(
        decision_context_module,
        "inventory_decision_for_work_item",
        lambda work_item_id, **_kwargs: (
            decision_without_landing_fact
            if work_item_id == BDO_WORK_ITEM_ID
            else None
        ),
    )

    context = decision_context_module.build_content_decision_context(BDO_WORK_ITEM_ID)

    assert context is not None
    assert context.applicable_signals
    assert all(not signal.evidence_ids for signal in context.applicable_signals)


def test_fresh_public_material_opens_text_workspace_without_dev_target_mapping(monkeypatch) -> None:
    _patch_bdo_dependencies(monkeypatch)
    monkeypatch.setattr(
        decision_context_module,
        "build_content_freshness_assessment_fast",
        lambda **_kwargs: ContentFreshnessAssessment(
            state="fresh",
            state_label="aktualne",
            requires_refresh=False,
            summary="Dowody są aktualne dla tej strony.",
            next_step="Przejdź do tekstu strony.",
        ),
    )

    context = decision_context_module.build_content_decision_context(BDO_WORK_ITEM_ID)

    assert context is not None
    assert context.authoring_target.mapping_status == "unverified"
    assert context.delivery_capability.request_status == "blocked"
    assert context.next_safe_action.kind == "open_workspace"


def test_decision_context_route_returns_the_read_only_contract(monkeypatch) -> None:
    context = SimpleNamespace()
    monkeypatch.setattr(
        decision_context_route,
        "build_content_decision_context",
        lambda work_item_id: context if work_item_id == BDO_WORK_ITEM_ID else None,
    )

    assert decision_context_route.content_work_item_decision_context(BDO_WORK_ITEM_ID) is context


def test_catalog_only_source_does_not_claim_material_is_available() -> None:
    decision = ContentDecisionItem(
        id="bdo",
        decision_type="refresh_or_merge",
        title="BDO dla firm",
        source_public_url=BDO_URL,
        final_canonical_url=BDO_URL,
        rationale="Istniejąca strona wymaga sprawdzenia.",
        next_step="Sprawdź materiał strony.",
    )
    catalog_item = ContentInventoryCatalogItem(
        catalog_id="catalog_bdo",
        work_item_id=BDO_WORK_ITEM_ID,
        url=BDO_URL,
        path="/bdo/",
        title="BDO dla firm",
        content_type="sitemap",
        material_status="missing",
        source_connector="wordpress_ekologus",
        evidence_id="ev_wp_bdo",
        collected_at=datetime(2026, 7, 22, tzinfo=UTC),
    )
    material = ContentInventoryMaterialResponse(
        status="blocked",
        url=BDO_URL,
        blocker_code="wordpress_material_unavailable",
        blocker="Brakuje odczytu materiału.",
    )

    source = decision_context_module._source_public_context(decision, catalog_item, material)

    assert source.identity_status == "observed"
    assert source.material.status == "blocked"
    assert source.label == "Adres rozpoznany; materiał niedostępny"
    assert "materiał tej strony nie jest obecnie dostępny" in source.reason
    assert "Adres i materiał rozpoznane" not in source.label
