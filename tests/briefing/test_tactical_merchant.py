from wilq.briefing.tactical_merchant import build_merchant_feed_items
from wilq.schemas import MetricFact


def test_merchant_issue_without_required_severity_or_destination_is_not_fix_now() -> None:
    items = build_merchant_feed_items(
        facts=[
            MetricFact(
                name="issue_product_count",
                value=4,
                period="latest_refresh",
                source_connector="google_merchant_center",
                evidence_id="ev_merchant_missing_issue_context",
                dimensions={"issue_type": "price", "country": "PL"},
            )
        ],
        action_ids={"google_merchant_center": ["act_review_merchant_feed_issues"]},
    )

    assert items == []
