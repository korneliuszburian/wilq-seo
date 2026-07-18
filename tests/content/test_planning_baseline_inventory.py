from wilq.content.briefs.sales import (
    ContentSalesBrief,
    ContentSalesBriefMeasurementPlan,
    ContentSalesBriefOperationsContext,
    ContentSalesBriefSignalQuality,
)
from wilq.content.workflow.planning import _baseline_inventory_disposition


def _brief(mode: str) -> ContentSalesBrief:
    return ContentSalesBrief(
        id="brief_test",
        work_item_id="work_item_test",
        topic="test",
        operations_context=ContentSalesBriefOperationsContext(
            enrichment_id="enrichment_test",
            intent_label="test",
            recommended_mode=mode,
            safe_next_step="test",
        ),
        target_reader="test",
        buyer_problem="test",
        buyer_trigger="test",
        search_intent="test",
        service_fit="test",
        final_canonical_url="https://www.ekologus.pl/test/",
        existing_content_plan="test",
        h1_direction="test",
        cta_direction="test",
        signal_quality=ContentSalesBriefSignalQuality(
            status="review_required",
            status_label="test",
            reason="test",
            evidence_id_count=1,
            source_connector_count=1,
            source_fact_count=1,
            missing_evidence_count=0,
            knowledge_constraint_count=0,
            review_required_knowledge_card_count=0,
            measurement_baseline_ready=True,
            safe_next_step="test",
        ),
        measurement_plan=ContentSalesBriefMeasurementPlan(
            measurement_window_id="window_test",
            metrics_to_watch=["impressions"],
            measurement_readiness_label="test",
            measurement_readiness_reason="test",
            earliest_verdict_note="test",
            success_claim_rule="test",
        ),
    )


def test_baseline_disposition_does_not_call_existing_refresh_sections_new() -> None:
    assert _baseline_inventory_disposition(_brief("refresh")) == "rewrite"
    assert _baseline_inventory_disposition(_brief("merge")) == "merge"
    assert _baseline_inventory_disposition(_brief("preserve")) == "preserve"
    assert _baseline_inventory_disposition(_brief("create")) == "create"
