from __future__ import annotations

from wilq.content.enrichment.opportunity import build_content_opportunity_enrichment
from wilq.schemas import ContentDecisionItem


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
