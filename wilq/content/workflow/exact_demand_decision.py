from __future__ import annotations

from wilq.content.planning.decisions import (
    content_decision_metric_tiles,
    content_decision_metrics,
    content_decision_summary,
    content_decision_title,
)
from wilq.schemas import ContentDecisionItem, MetricFact


def content_decision_with_exact_demand(
    decision: ContentDecisionItem,
    *,
    gsc_facts: list[MetricFact],
    ads_facts: list[MetricFact],
) -> ContentDecisionItem:
    queries = list(dict.fromkeys(fact.dimensions["query"] for fact in gsc_facts))
    metrics = content_decision_metrics(gsc_facts, queries)
    wordpress_match = decision.wordpress_match or "missing"
    retained_facts = [
        fact
        for fact in decision.metric_facts
        if fact.source_connector not in {"google_search_console", "google_ads"}
    ]
    return decision.model_copy(
        update={
            "title": content_decision_title(
                decision.decision_type,
                decision.page or decision.normalized_page_path or "",
                len(queries),
                metrics,
            ),
            "summary": content_decision_summary(
                decision.decision_type,
                metrics,
                wordpress_match,
                wordpress_title_or_h1=decision.wordpress_title_or_h1,
                wordpress_section_headings=decision.wordpress_section_headings,
            ),
            "metric_tiles": content_decision_metric_tiles(
                decision.decision_type,
                metrics,
                len(queries),
                wordpress_match,
                wordpress_section_count=decision.wordpress_section_count,
                wordpress_section_inventory_status=(
                    decision.wordpress_section_inventory_status
                ),
            ),
            "queries": queries,
            "query_count": len(queries),
            "primary_query": metrics.primary_query,
            "total_clicks": metrics.total_clicks,
            "total_impressions": metrics.total_impressions,
            "aggregate_ctr": metrics.aggregate_ctr,
            "best_average_position": metrics.best_average_position,
            "metric_facts": [*gsc_facts, *ads_facts, *retained_facts],
            "evidence_ids": list(
                dict.fromkeys(
                    [
                        *decision.evidence_ids,
                        *(fact.evidence_id for fact in ads_facts),
                        *(fact.evidence_id for fact in retained_facts),
                    ]
                )
            ),
            "source_connectors": list(
                dict.fromkeys(
                    [
                        *decision.source_connectors,
                        *(fact.source_connector for fact in ads_facts),
                        *(fact.source_connector for fact in retained_facts),
                    ]
                )
            ),
        }
    )
