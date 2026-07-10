from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
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
