from __future__ import annotations

from datetime import UTC, datetime

import wilq.briefing.content_diagnostics as content_diagnostics_module
import wilq.content.workflow.workspace.api as workflow_api
from wilq.briefing.content_diagnostics import (
    build_content_diagnostics,
    build_content_diagnostics_cached,
)
from wilq.briefing.tactical_queue import build_gsc_content_tactical_items
from wilq.connectors.vendor import VendorMetricFact
from wilq.content.workflow.pipeline_steps.queue import (
    build_content_work_item_queue_candidate,
    build_content_work_item_queue_response,
)
from wilq.schemas import (
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ContentDecisionItem,
    ContentDiagnosticsResponse,
    ContentFreshnessAssessment,
    MetricFact,
)
from wilq.storage.metric_store import metric_store


def test_content_work_item_queue_exposes_api_owned_candidates() -> None:
    queue = build_content_work_item_queue_response(build_content_diagnostics_cached())

    assert queue.queue_status in {"ready", "blocked"}
    assert queue.candidate_count >= 1
    assert queue.actionable_candidate_count >= 0
    assert queue.freshness_assessment.state in {"fresh", "stale", "missing", "blocked"}
    assert queue.freshness_assessment.next_step
    assert "Gotowe do pracy:" in queue.operator_summary
    assert "WILQ widzi" not in queue.operator_summary

    for candidate in queue.candidates:
        assert candidate.work_item_id.startswith("content_work_item_")
        assert candidate.decision_id.startswith("content_decision_")
        assert candidate.recommended_mode in {
            "preserve",
            "refresh",
            "merge",
            "create",
            "block",
        }
        assert candidate.evidence_ids
        assert candidate.source_connectors
        if candidate.recommended_mode != "block":
            assert "act_prepare_content_refresh_queue" in candidate.action_ids
            assert candidate.action_summary_label
        assert candidate.preflight_status in {
            "blocked",
            "plan_allowed",
            "brief_allowed",
            "draft_allowed",
            "handoff_allowed",
        }
        assert candidate.recommended_mode_label
        assert candidate.status_label
        assert candidate.duplicate_canonical_risk_summary
        assert candidate.measurement_readiness.label
        assert candidate.safe_next_step
        assert candidate.freshness_assessment.state in {
            "fresh",
            "stale",
            "missing",
            "blocked",
        }
        assert "ekologus.dev.proudsite.pl" not in str(candidate.final_canonical_url)

    blocked_without_final_url = [
        candidate for candidate in queue.candidates if candidate.final_canonical_url is None
    ]
    assert blocked_without_final_url
    assert blocked_without_final_url[0].recommended_mode == "block"
    assert {blocker.code for blocker in blocked_without_final_url[0].blockers} >= {
        "missing_final_canonical"
    }


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
        "wilq.content.workflow.pipeline_steps.queue.inventory_decision_for_work_item",
        lambda work_item_id, **_kwargs: selected_decision if work_item_id == inventory_id else None,
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


def test_queue_projection_uses_the_content_when_inventory_heading_is_sentence_like() -> None:
    decision = ContentDecisionItem(
        id="inventory_sentence_heading",
        decision_type="refresh_or_merge",
        status="ready",
        title="Informacja o opakowaniach",
        primary_query="gospodarka opakowaniami",
        priority=10,
        source_public_url="https://www.ekologus.pl/opakowania/",
        final_canonical_url="https://www.ekologus.pl/opakowania/",
        wordpress_section_headings=[
            "Obowiązki wynikające z ustawy dotyczą wyłącznie przedsiębiorców w rozumieniu "
            "przepisów ustawy z dnia 2 lipca 2004 r. o swobodzie działalności gospodarczej."
        ],
        wordpress_section_inventory_status="available",
        wordpress_content_inventory_status="available",
        wordpress_content_text="Pełny materiał istniejącej strony.",
        source_connectors=["google_search_console", "wordpress_ekologus"],
        evidence_ids=["ev_gsc_sentence", "ev_wp_sentence"],
        rationale="Istniejąca treść wymaga przeglądu.",
        next_step="Przejdź do planu.",
    )

    candidate = build_content_work_item_queue_candidate(
        decision,
        ContentFreshnessAssessment(
            state="fresh",
            state_label="dane treści świeże",
            requires_refresh=False,
            summary="Dane są świeże.",
            next_step="Można przejść do decyzji.",
        ),
    )

    assert candidate.page_inventory.section_headings == []
    assert candidate.page_inventory.section_count == 0
    assert candidate.page_inventory.section_inventory_status == "missing"
    assert candidate.page_inventory.content_inventory_status == "available"
    assert "the_content" in (candidate.page_inventory.acf_section_inventory_note or "")


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


def test_queue_ga4_projection_keeps_only_exact_landing_facts() -> None:
    decision = ContentDecisionItem(
        id="content_decision_ga4_exact",
        decision_type="refresh_or_merge",
        status="ready",
        title="Doradztwo środowiskowe",
        primary_query="doradztwo środowiskowe",
        priority=10,
        source_public_url="https://www.ekologus.pl/oferta/doradztwo/",
        final_canonical_url="https://www.ekologus.pl/oferta/doradztwo/",
        source_connectors=["google_search_console", "google_analytics_4"],
        evidence_ids=["ev_gsc_exact", "ev_ga4_exact", "ev_ga4_other"],
        metric_facts=[
            MetricFact(
                name="sessions",
                value=42,
                period="2026-07-01/2026-07-07",
                source_connector="google_analytics_4",
                evidence_id="ev_ga4_exact",
                dimensions={"landing_page": "/oferta/doradztwo/", "host_name": "www.ekologus.pl"},
                freshness_state="fresh",
            ),
            MetricFact(
                name="sessions",
                value=999,
                period="2026-07-01/2026-07-07",
                source_connector="google_analytics_4",
                evidence_id="ev_ga4_other",
                dimensions={"landing_page": "/inna-strona/", "host_name": "www.ekologus.pl"},
                freshness_state="fresh",
            ),
        ],
        rationale="Exact landing page metric projection.",
        next_step="Przejdź do planu.",
    )

    candidate = build_content_work_item_queue_candidate(
        decision,
        ContentFreshnessAssessment(
            state="fresh",
            state_label="dane treści świeże",
            requires_refresh=False,
            summary="Dane są świeże.",
            next_step="Można przejść do decyzji.",
        ),
    )

    assert candidate.ga4_metrics.status == "available"
    assert [
        (fact.name, fact.value, fact.evidence_id) for fact in candidate.ga4_metrics.metrics
    ] == [("sessions", 42, "ev_ga4_exact")]
    assert candidate.ga4_metrics.evidence_ids == ["ev_ga4_exact"]


def test_gsc_decision_queue_attaches_exact_ga4_landing_fact_from_metric_store(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "metrics.duckdb"))
    monkeypatch.setattr(
        content_diagnostics_module,
        "_primary_content_data_available",
        lambda *_args: True,
    )
    page = "https://www.ekologus.pl/oferta/doradztwo-srodowiskowe/"
    collected_at = datetime(2026, 8, 1, 8, 0, tzinfo=UTC)
    ga4_evidence_id = "ev_ga4_exact_landing_decision"
    metric_store().save_connector_refresh_metrics(
        ConnectorRefreshRun(
            id="ga4_exact_landing_decision",
            connector_id="google_analytics_4",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            started_at=collected_at,
            completed_at=collected_at,
            evidence_ids=[ga4_evidence_id],
            summary="Exact GA4 landing fact for the GSC decision queue.",
        ),
        detailed_facts=[
            VendorMetricFact(
                name="sessions",
                value=42,
                period="2026-07-01/2026-07-31",
                dimensions={"landing_page": "/oferta/doradztwo-srodowiskowe/"},
            )
        ],
    )
    gsc_and_wordpress_facts = [
        MetricFact(
            name="impressions",
            value=240,
            period="2026-07-01/2026-07-31",
            source_connector="google_search_console",
            evidence_id="ev_gsc_exact_landing_decision",
            dimensions={"query": "doradztwo środowiskowe", "page": page},
            collected_at=collected_at,
        ),
        MetricFact(
            name="content_object_seen",
            value=1,
            period="connector_refresh",
            source_connector="wordpress_ekologus",
            evidence_id="ev_wp_exact_landing_decision",
            dimensions={
                "content_url": page,
                "content_type": "pages",
                "status": "publish",
                "title_or_h1": "Doradztwo środowiskowe",
            },
            collected_at=collected_at,
        ),
    ]
    stored_ga4_facts = metric_store().list_metric_facts(
        connector_id="google_analytics_4"
    )
    all_metric_facts = [*gsc_and_wordpress_facts, *stored_ga4_facts]
    tactical_items = build_gsc_content_tactical_items(all_metric_facts)

    diagnostics = build_content_diagnostics(
        tactical_items=tactical_items,
        actions=[],
        metric_facts=all_metric_facts,
    )
    decision = next(item for item in diagnostics.decision_queue if item.page == page)
    candidate = build_content_work_item_queue_candidate(
        decision,
        ContentFreshnessAssessment(
            state="fresh",
            state_label="dane treści świeże",
            requires_refresh=False,
            summary="Dane są świeże.",
            next_step="Można przejść do decyzji.",
        ),
    )

    assert candidate.ga4_metrics.status == "available"
    assert ga4_evidence_id in candidate.ga4_metrics.evidence_ids


def test_selected_snapshot_rebuilds_candidate_inventory_from_fresh_binding(monkeypatch) -> None:
    work_item_id = "content_work_item_inventory_fresh_projection"
    stale_queue_decision = ContentDecisionItem(
        id="inventory_fresh_projection",
        decision_type="refresh_or_merge",
        status="ready",
        title="Stary rzut inventory",
        primary_query="gospodarka opakowaniami",
        priority=10,
        source_public_url="https://www.ekologus.pl/opakowania/",
        final_canonical_url="https://www.ekologus.pl/opakowania/",
        wordpress_section_headings=["Stara sekcja"],
        wordpress_section_inventory_status="available",
        wordpress_content_inventory_status="available",
        wordpress_content_summary="Stary skrót",
        source_connectors=["google_search_console", "wordpress_ekologus"],
        evidence_ids=["ev_gsc_old", "ev_wp_old"],
        rationale="Stara kolejka.",
        next_step="Odśwież.",
    )
    fresh_inventory_decision = stale_queue_decision.model_copy(
        update={
            "title": "Świeży odczyt inventory",
            "wordpress_section_headings": ["Hero", "Usługa", "CTA"],
            "wordpress_section_count": 3,
            "wordpress_acf_section_headings": ["Hero", "Usługa", "CTA"],
            "wordpress_acf_section_count": 3,
            "wordpress_acf_section_inventory_status": "available",
            "wordpress_acf_section_inventory_note": None,
            "wordpress_content_summary": "Świeży skrót",
        }
    )
    diagnostics = ContentDiagnosticsResponse.model_construct(
        freshness_assessment=ContentFreshnessAssessment(
            state="fresh",
            state_label="dane treści świeże",
            requires_refresh=False,
            summary="Świeże.",
            next_step="Można przejść dalej.",
        ),
        decision_queue=[stale_queue_decision],
    )
    monkeypatch.setattr(
        workflow_api,
        "inventory_decision_for_work_item",
        lambda selected_id, **_kwargs: (
            fresh_inventory_decision if selected_id == work_item_id else None
        ),
    )
    captured: dict[str, object] = {}

    def capture_snapshot(decision, **kwargs):
        captured["candidate"] = kwargs["candidate"]
        return None

    monkeypatch.setattr(
        workflow_api,
        "_build_content_work_item_diagnostics_snapshot_response_from_decision",
        capture_snapshot,
    )

    workflow_api.build_content_work_item_diagnostics_snapshot_response_for_work_item(
        diagnostics,
        work_item_id,
    )

    candidate = captured["candidate"]
    assert candidate.page_inventory.section_count == 3
    assert candidate.page_inventory.section_headings == ["Hero", "Usługa", "CTA"]
    assert candidate.page_inventory.acf_section_inventory_status == "available"
    assert candidate.page_inventory.acf_section_inventory_note is None


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
        ],
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


def test_content_work_item_queue_blocks_stale_evidence_without_changing_disposition() -> None:
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
                inventory_gate_status="confirmed_current_inventory",
                canonical_gate_status="resolved",
                duplicate_gate_status="existing_public_content_requires_refresh_or_merge",
                source_connectors=["google_search_console", "wordpress_ekologus"],
                evidence_ids=["ev_gsc_stale", "ev_wp_stale"],
                rationale="Istniejąca strona ma sygnał do odświeżenia.",
                next_step="Odśwież źródła przed planem.",
            )
        ],
    )

    queue = build_content_work_item_queue_response(diagnostics, minimum_actionable_candidates=1)

    assert queue.queue_status == "blocked"
    assert queue.actionable_candidate_count == 1
    assert queue.freshness_assessment.state == "stale"
    assert "Źródła tej decyzji wymagają odświeżenia" in {
        blocker.label for blocker in queue.candidates[0].blockers
    }
    assert queue.candidates[0].recommended_mode == "refresh"
    assert queue.candidates[0].safe_next_step == freshness.next_step
    assert "Dane treści wymagają odświeżenia" in queue.operator_summary
