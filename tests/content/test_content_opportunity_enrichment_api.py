from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from wilq.content.enrichment.opportunity import build_content_opportunity_enrichment
from wilq.schemas import ContentDecisionItem


def test_content_work_item_enrichment_exposes_evidence_bound_operating_context() -> None:
    client = TestClient(app)
    queue = client.get("/api/content/work-items/queue").json()
    candidate = next(item for item in queue["candidates"] if item["source_public_url"])

    response = client.get(f"/api/content/work-items/{candidate['work_item_id']}/enrichment")

    assert response.status_code == 200
    data = response.json()
    enrichment = data["enrichment"]
    assert enrichment["work_item_id"] == candidate["work_item_id"]
    assert enrichment["decision_id"] == candidate["decision_id"]
    expected_status = "blocked" if candidate["recommended_mode"] == "block" else "ready"
    assert enrichment["status"] == expected_status
    assert enrichment["recommended_mode"] == candidate["recommended_mode"]
    assert enrichment["intent_label"]
    assert enrichment["buyer_problem"]
    assert enrichment["buyer_trigger"]
    assert enrichment["service_fit"]
    assert enrichment["cta_hypothesis"]
    assert enrichment["source_facts"]
    assert enrichment["evidence_ids"]
    assert enrichment["source_connectors"]
    assert enrichment["measurement_baseline"]["metrics_to_watch"]
    assert enrichment["measurement_baseline"]["source_connectors"]
    if candidate["recommended_mode"] == "block":
        assert "content_sources_require_refresh" in {
            blocker["code"] for blocker in enrichment["blockers"]
        }
    assert "score" not in enrichment
    assert "ekologus.dev.proudsite.pl" not in str(enrichment.get("final_canonical_url"))


def test_content_opportunity_enrichment_keeps_source_fact_lineage_per_connector() -> None:
    enrichment = build_content_opportunity_enrichment(
        ContentDecisionItem(
            id="content_decision_bdo",
            decision_type="refresh_or_merge",
            status="ready",
            title="BDO",
            primary_query="bdo co to",
            queries=["bdo co to"],
            total_impressions=120,
            total_clicks=3,
            wordpress_match="found",
            wordpress_match_label="spis potwierdzony",
            final_canonical_url="https://ekologus.pl/bdo/",
            source_public_url="https://ekologus.pl/bdo/",
            source_connectors=["google_search_console", "wordpress_ekologus"],
            evidence_ids=[
                "ev_refresh_refresh_google_search_console_abc",
                "ev_refresh_refresh_wordpress_ekologus_def",
            ],
            rationale="Test lineage.",
            next_step="Odśwież.",
        )
    )

    for fact in enrichment.source_facts:
        if fact.source_connectors == ["google_search_console"]:
            assert fact.evidence_ids == ["ev_refresh_refresh_google_search_console_abc"]
        if fact.source_connectors == ["wordpress_ekologus"]:
            assert fact.evidence_ids == ["ev_refresh_refresh_wordpress_ekologus_def"]


def test_content_work_item_enrichment_returns_typed_blocker_for_unknown_item() -> None:
    response = TestClient(app).get("/api/content/work-items/content_work_item_missing/enrichment")

    assert response.status_code == 200
    data = response.json()
    assert data["enrichment"] is None
    assert [blocker["code"] for blocker in data["blockers"]] == ["missing_work_item"]


def test_content_opportunity_enrichment_blocks_without_evidence_or_source_connector() -> None:
    enrichment = build_content_opportunity_enrichment(
        ContentDecisionItem(
            id="content_decision_no_evidence",
            decision_type="inventory_check_before_create",
            status="ready",
            title="Temat bez dowodów",
            final_canonical_url="https://ekologus.pl/temat/",
            rationale="Nie ma dowodów.",
            next_step="Odśwież źródła.",
        )
    )

    assert enrichment.status == "blocked"
    assert {blocker.code for blocker in enrichment.blockers} >= {
        "missing_evidence",
        "missing_source_connector",
    }
    assert enrichment.source_facts == []
    assert enrichment.measurement_baseline.status == "blocked"


def test_content_opportunity_enrichment_blocks_dev_canonical() -> None:
    enrichment = build_content_opportunity_enrichment(
        ContentDecisionItem(
            id="content_decision_dev",
            decision_type="inventory_check_before_create",
            status="ready",
            title="BDO dev",
            primary_query="bdo",
            final_canonical_url="https://ekologus.dev.proudsite.pl/bdo/",
            preview_url="https://ekologus.dev.proudsite.pl/bdo/",
            source_connectors=["google_search_console", "wordpress_ekologus"],
            evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
            rationale="Dev nie jest canonicalem.",
            next_step="Ustaw publiczny adres.",
        )
    )

    assert enrichment.status == "blocked"
    assert {blocker.code for blocker in enrichment.blockers} >= {"invalid_final_canonical"}
    assert enrichment.intent == "compliance_risk"
    assert enrichment.service_fit == "obsługa środowiskowa i zgodność obowiązków"
