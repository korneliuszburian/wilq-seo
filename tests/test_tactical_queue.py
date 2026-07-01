from __future__ import annotations

from datetime import UTC, datetime

from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.schemas import MetricFact, OpportunityDomain


def test_tactical_queue_uses_latest_gsc_query_page_identity() -> None:
    page = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    query = "bdo co to"
    old_at = datetime(2026, 6, 28, 8, 0, tzinfo=UTC)
    new_at = datetime(2026, 6, 29, 8, 0, tzinfo=UTC)

    queue = build_tactical_queue(
        use_cache=False,
        facts_by_connector={
            "google_search_console": [
                _gsc_fact("clicks", 1, query, page, "ev_old_gsc", old_at),
                _gsc_fact("impressions", 100, query, page, "ev_old_gsc", old_at),
                _gsc_fact("ctr", 0.01, query, page, "ev_old_gsc", old_at),
                _gsc_fact("average_position", 9.0, query, page, "ev_old_gsc", old_at),
                _gsc_fact("clicks", 10, query, page, "ev_new_gsc", new_at),
                _gsc_fact("impressions", 500, query, page, "ev_new_gsc", new_at),
                _gsc_fact("ctr", 0.02, query, page, "ev_new_gsc", new_at),
                _gsc_fact("average_position", 7.5, query, page, "ev_new_gsc", new_at),
            ],
            "wordpress_ekologus": [
                MetricFact(
                    name="content_object_seen",
                    value=1,
                    period="snapshot",
                    source_connector="wordpress_ekologus",
                    evidence_id="ev_wp",
                    dimensions={
                        "content_url": page,
                        "content_type": "post",
                        "status": "publish",
                        "inventory_source": "public_sitemap",
                    },
                    collected_at=new_at,
                )
            ],
        },
    )

    gsc_items = [item for item in queue.items if item.domain == OpportunityDomain.gsc_seo]

    assert len(gsc_items) == 1
    item = gsc_items[0]
    assert item.dimensions["query"] == query
    assert item.dimensions["page"] == page
    assert "ev_new_gsc" in item.evidence_ids
    assert "ev_old_gsc" not in item.evidence_ids
    new_fact_values = {
        fact.name: fact.value for fact in item.metric_facts if fact.evidence_id == "ev_new_gsc"
    }
    assert new_fact_values == {
        "average_position": 7.5,
        "clicks": 10,
        "ctr": 0.02,
        "impressions": 500,
    }


def _gsc_fact(
    name: str,
    value: float | int,
    query: str,
    page: str,
    evidence_id: str,
    collected_at: datetime,
) -> MetricFact:
    return MetricFact(
        name=name,
        value=value,
        period="2026-06-29",
        source_connector="google_search_console",
        evidence_id=evidence_id,
        dimensions={"query": query, "page": page},
        collected_at=collected_at,
    )
