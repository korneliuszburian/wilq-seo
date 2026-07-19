from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_workflow
from wilq.content.planning.decisions import content_decision_work_item_id_for_url
from wilq.content.workflow.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    inventory_work_item_id,
)
from wilq.content.workflow.queue import build_content_work_item_queue_response
from wilq.schemas import (
    ContentDecisionItem,
    ContentDiagnosticsResponse,
    ContentFreshnessAssessment,
)


def test_content_work_item_queue_exposes_api_owned_candidates() -> None:
    response = TestClient(app).get("/api/content/work-items/queue")

    assert response.status_code == 200
    data = response.json()
    assert data["queue_status"] in {"ready", "blocked"}
    assert data["candidate_count"] >= 1
    assert data["actionable_candidate_count"] >= 0
    assert data["freshness_assessment"]["state"] in {"fresh", "stale", "missing", "blocked"}
    assert data["freshness_assessment"]["next_step"]
    assert "Gotowe do pracy:" in data["operator_summary"]
    assert "WILQ widzi" not in data["operator_summary"]

    for candidate in data["candidates"]:
        assert candidate["work_item_id"].startswith("content_work_item_")
        assert candidate["decision_id"].startswith("content_decision_")
        assert candidate["recommended_mode"] in {
            "preserve",
            "refresh",
            "merge",
            "create",
            "block",
        }
        assert candidate["evidence_ids"]
        assert candidate["source_connectors"]
        if candidate["recommended_mode"] != "block":
            assert "act_prepare_content_refresh_queue" in candidate["action_ids"]
            assert candidate["action_summary_label"]
        assert candidate["preflight_status"] in {
            "blocked",
            "plan_allowed",
            "brief_allowed",
            "draft_allowed",
            "handoff_allowed",
        }
        assert candidate["recommended_mode_label"]
        assert candidate["status_label"]
        assert candidate["duplicate_canonical_risk_summary"]
        assert candidate["measurement_readiness"]["label"]
        assert candidate["safe_next_step"]
        assert candidate["freshness_assessment"]["state"] in {
            "fresh",
            "stale",
            "missing",
            "blocked",
        }
        assert "ekologus.dev.proudsite.pl" not in str(candidate["final_canonical_url"])

    blocked_without_final_url = [
        candidate for candidate in data["candidates"] if candidate["final_canonical_url"] is None
    ]
    assert blocked_without_final_url
    assert blocked_without_final_url[0]["recommended_mode"] == "block"
    assert {
        blocker["code"] for blocker in blocked_without_final_url[0]["blockers"]
    } >= {"missing_final_canonical"}


def test_queue_can_include_selected_inventory_work_item_not_in_recommendation_queue(
    monkeypatch,
) -> None:
    inventory_id = "content_work_item_inventory_selected"
    selected_decision = ContentDecisionItem(
        id="inventory_selected",
        decision_type="refresh_or_merge",
        status="ready",
        title="Istniejący materiał do pracy",
        primary_query="gospodarka odpadami",
        priority=50,
        source_public_url="https://www.ekologus.pl/gospodarka-odpadami/",
        final_canonical_url="https://www.ekologus.pl/gospodarka-odpadami/",
        source_connectors=["google_search_console", "wordpress_ekologus"],
        evidence_ids=["ev_gsc_selected", "ev_wp_selected"],
        rationale="Inventory binding wskazał istniejący materiał.",
        next_step="Przejdź do planu odświeżenia.",
    )
    monkeypatch.setattr(
        "wilq.content.workflow.queue.inventory_decision_for_work_item",
        lambda work_item_id, **_kwargs: (
            selected_decision if work_item_id == inventory_id else None
        ),
    )
    diagnostics = ContentDiagnosticsResponse.model_construct(
        freshness_assessment=ContentFreshnessAssessment(
            state="fresh",
            state_label="dane treści świeże",
            requires_refresh=False,
            summary="Dane są świeże.",
            next_step="Można przejść do decyzji.",
        ),
        decision_queue=[],
    )

    queue = build_content_work_item_queue_response(
        diagnostics,
        minimum_actionable_candidates=1,
        selected_work_item_id=inventory_id,
    )

    assert [candidate.work_item_id for candidate in queue.candidates] == [inventory_id]
    assert queue.candidates[0].final_canonical_url == selected_decision.final_canonical_url


def test_queue_rebuilds_source_labels_from_authoritative_connector_ids() -> None:
    decision = ContentDecisionItem(
        id="content_decision_source_labels",
        decision_type="refresh_or_merge",
        status="ready",
        title="Strona z pełnym śladem źródeł",
        primary_query="doradztwo środowiskowe",
        priority=10,
        source_public_url="https://www.ekologus.pl/doradztwo/",
        final_canonical_url="https://www.ekologus.pl/doradztwo/",
        source_connectors=["wordpress_ekologus", "google_search_console", "google_ads"],
        # Simulate a legacy persisted projection that predates Ads lineage.
        source_connector_labels=["WordPress ekologus.pl", "Google Search Console"],
        evidence_ids=["ev_wp", "ev_gsc", "ev_ads"],
        rationale="Test pełnego śladu źródeł.",
        next_step="Przejdź do decyzji.",
    )
    diagnostics = ContentDiagnosticsResponse.model_construct(
        freshness_assessment=ContentFreshnessAssessment(
            state="fresh",
            state_label="dane treści świeże",
            requires_refresh=False,
            summary="Dane są świeże.",
            next_step="Można przejść do decyzji.",
        ),
        decision_queue=[decision],
    )

    queue = build_content_work_item_queue_response(
        diagnostics,
        minimum_actionable_candidates=1,
    )

    assert queue.candidates[0].source_connector_labels == [
        "WordPress ekologus.pl",
        "Google Search Console",
        "Google Ads",
    ]


def test_selected_inventory_queue_reads_material_without_full_diagnostics(monkeypatch) -> None:
    inventory_id = "content_work_item_inventory_fast"
    selected_decision = ContentDecisionItem(
        id="inventory_fast",
        decision_type="refresh_or_merge",
        status="ready",
        title="Szybki odczyt wybranej strony",
        primary_query="gospodarka odpadami",
        priority=10,
        source_public_url="https://www.ekologus.pl/gospodarka-odpadami/",
        final_canonical_url="https://www.ekologus.pl/gospodarka-odpadami/",
        source_connectors=["google_search_console", "wordpress_ekologus"],
        evidence_ids=["ev_gsc_fast", "ev_wp_fast"],
        rationale="Wybrany materiał z inventory.",
        next_step="Przejdź do decyzji.",
    )
    calls: list[bool] = []

    def selected_inventory_decision(work_item_id: str, **kwargs):
        calls.append(kwargs["read_material"])
        assert kwargs["allow_material_pending"] is True
        return selected_decision if work_item_id == inventory_id else None

    monkeypatch.setattr(
        content_workflow,
        "inventory_decision_for_work_item",
        selected_inventory_decision,
    )
    monkeypatch.setattr(
        content_workflow,
        "build_content_freshness_assessment_fast",
        lambda: ContentFreshnessAssessment(
            state="fresh",
            state_label="dane treści świeże",
            requires_refresh=False,
            summary="Dane są świeże.",
            next_step="Można przejść do decyzji.",
        ),
    )
    monkeypatch.setattr(
        content_workflow,
        "build_content_diagnostics_cached",
        lambda: (_ for _ in ()).throw(AssertionError("full diagnostics must not run")),
    )

    response = TestClient(app).get(f"/api/content/work-items/queue?work_item_id={inventory_id}")

    assert response.status_code == 200
    assert response.json()["candidates"][0]["work_item_id"] == inventory_id
    assert calls == [False]
    assert response.json()["candidates"][0]["status_label"] == "materiał wymaga odczytu"


def test_selected_diagnostics_work_item_uses_the_catalog_fast_path(monkeypatch) -> None:
    url = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    work_item_id = content_decision_work_item_id_for_url(url)
    selected_decision = ContentDecisionItem(
        id=work_item_id.removeprefix("content_work_item_"),
        decision_type="refresh_or_merge",
        status="ready",
        title="BDO",
        primary_query="bdo",
        priority=10,
        source_public_url=url,
        final_canonical_url=url,
        source_connectors=["google_search_console", "wordpress_ekologus"],
        evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
        rationale="Katalog WordPress i GSC.",
        next_step="Przejdź do decyzji.",
    )
    monkeypatch.setattr(
        content_workflow,
        "inventory_decision_for_work_item",
        lambda selected_id, **_kwargs: selected_decision
        if selected_id == work_item_id
        else None,
    )
    monkeypatch.setattr(
        content_workflow,
        "build_content_diagnostics_cached",
        lambda: (_ for _ in ()).throw(AssertionError("full diagnostics must not run")),
    )
    monkeypatch.setattr(
        content_workflow,
        "build_content_freshness_assessment_fast",
        lambda: ContentFreshnessAssessment(
            state="fresh",
            state_label="dane treści świeże",
            requires_refresh=False,
            summary="Dane są świeże.",
            next_step="Można przejść do decyzji.",
        ),
    )

    response = TestClient(app).get(f"/api/content/work-items/queue?work_item_id={work_item_id}")

    assert response.status_code == 200
    assert response.json()["candidate_count"] == 1
    assert response.json()["candidates"][0]["decision_id"] == selected_decision.id


def test_selected_diagnostics_work_item_resolves_through_real_catalog_binding(
    monkeypatch,
) -> None:
    url = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    work_item_id = content_decision_work_item_id_for_url(url)
    catalog = ContentInventoryCatalogResponse(
        total_count=1,
        items=[
            ContentInventoryCatalogItem(
                catalog_id="catalog_bdo",
                work_item_id=inventory_work_item_id(url),
                url=url,
                path="/bdo-co-musi-wiedziec-przedsiebiorca/",
                title="BDO",
                content_type="page",
                material_status="content_summary",
                content_summary="Istniejąca strona BDO.",
                source_connector="wordpress_ekologus",
                evidence_id="ev_wp_bdo",
                collected_at=datetime(2026, 7, 19, tzinfo=UTC),
            )
        ],
    )
    monkeypatch.setattr(
        "wilq.content.workflow.inventory_binding.build_content_inventory_catalog",
        lambda: catalog,
    )
    monkeypatch.setattr(
        "wilq.content.workflow.inventory_binding.inventory_metric_facts",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        content_workflow,
        "build_content_diagnostics_cached",
        lambda: (_ for _ in ()).throw(AssertionError("full diagnostics must not run")),
    )

    response = TestClient(app).get(f"/api/content/work-items/queue?work_item_id={work_item_id}")

    assert response.status_code == 200
    assert response.json()["candidate_count"] == 1
    assert response.json()["candidates"][0]["decision_id"] == work_item_id.removeprefix(
        "content_work_item_"
    )


def test_content_work_item_queue_blocks_dev_url_as_final_canonical() -> None:
    diagnostics = ContentDiagnosticsResponse.model_construct(
        freshness_assessment=ContentFreshnessAssessment(
            state="fresh",
            state_label="dane treści świeże",
            requires_refresh=False,
            summary="Podstawowe dane treści są świeże.",
            next_step="Można przejść do decyzji contentowej.",
        ),
        decision_queue=[
            ContentDecisionItem(
                id="content_decision_dev_preview",
                decision_type="inventory_check_before_create",
                status="ready",
                title="Nowa treść z podglądu",
                priority=10,
                source_public_url="https://www.ekologus.pl/bdo/",
                final_canonical_url="https://ekologus.dev.proudsite.pl/bdo/",
                preview_url="https://ekologus.dev.proudsite.pl/bdo/",
                source_connectors=["google_search_console", "wordpress_ekologus"],
                evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
                rationale="Test blokady dev URL.",
                next_step="Ustaw publiczny finalny adres przed planem.",
            )
        ]
    )

    queue = build_content_work_item_queue_response(
        diagnostics,
        minimum_actionable_candidates=1,
    )

    assert queue.queue_status == "blocked"
    assert queue.actionable_candidate_count == 0
    candidate = queue.candidates[0]
    assert candidate.recommended_mode == "block"
    assert candidate.measurement_readiness.status == "blocked"
    assert {blocker.code for blocker in candidate.blockers} >= {"invalid_final_canonical"}
    assert "Adres podglądu albo dev" in candidate.duplicate_canonical_risk_summary


def test_content_work_item_queue_blocks_primary_decision_on_stale_sources() -> None:
    freshness = ContentFreshnessAssessment(
        state="stale",
        state_label="dane treści wymagają odświeżenia",
        requires_refresh=True,
        stale_connector_ids=["google_search_console", "wordpress_ekologus"],
        connector_labels_requiring_refresh=[
            "Google Search Console",
            "WordPress ekologus.pl",
        ],
        summary="Dane treści są do odświeżenia dla: Google Search Console i WordPress ekologus.pl.",
        next_step="Uruchom odczyt GSC i WordPress przed decyzją contentową.",
    )
    diagnostics = ContentDiagnosticsResponse.model_construct(
        freshness_assessment=freshness,
        decision_queue=[
            ContentDecisionItem(
                id="content_decision_stale_primary",
                decision_type="refresh_or_merge",
                status="ready",
                title="Istniejąca strona do odświeżenia",
                primary_query="ochrona środowiska dla firm",
                priority=1,
                source_public_url="https://www.ekologus.pl/",
                final_canonical_url="https://www.ekologus.pl/",
                source_connectors=["google_search_console", "wordpress_ekologus"],
                evidence_ids=["ev_gsc_stale", "ev_wp_stale"],
                rationale="Istniejąca strona ma sygnał do odświeżenia.",
                next_step="Odśwież źródła przed planem.",
            )
        ],
    )

    queue = build_content_work_item_queue_response(diagnostics, minimum_actionable_candidates=1)

    assert queue.queue_status == "blocked"
    assert queue.actionable_candidate_count == 0
    assert queue.freshness_assessment.state == "stale"
    assert "Źródła tej decyzji wymagają odświeżenia" in {
        blocker.label for blocker in queue.candidates[0].blockers
    }
    assert queue.candidates[0].recommended_mode == "block"
    assert queue.candidates[0].safe_next_step == freshness.next_step
    assert "Dane treści wymagają odświeżenia" in queue.operator_summary
