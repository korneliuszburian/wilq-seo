from __future__ import annotations

from datetime import UTC, datetime

from wilq.briefing.tactical_queue import _balanced_tactical_items, build_tactical_queue
from wilq.content.planning.ahrefs_overlap import AhrefsCrossSourceMatcher
from wilq.schemas import MetricFact, OpportunityDomain, TacticalQueueItem


def test_tactical_queue_keeps_domain_floor_after_full_content_extraction() -> None:
    items = [
        _tactical_item(f"gsc-{index}", OpportunityDomain.gsc_seo, priority=1)
        for index in range(30)
    ]
    for domain in (
        OpportunityDomain.ga4,
        OpportunityDomain.merchant,
        OpportunityDomain.ahrefs,
    ):
        items.extend(
            _tactical_item(f"{domain.value}-{index}", domain, priority=100)
            for index in range(4)
        )

    balanced = _balanced_tactical_items(items, limit=24)

    assert len(balanced) == 24
    assert {
        domain: sum(item.domain == domain for item in balanced)
        for domain in (OpportunityDomain.ga4, OpportunityDomain.merchant, OpportunityDomain.ahrefs)
    } == {
        OpportunityDomain.ga4: 4,
        OpportunityDomain.merchant: 4,
        OpportunityDomain.ahrefs: 4,
    }


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


def test_tactical_queue_compiles_ahrefs_matcher_once_for_batch(monkeypatch) -> None:
    import wilq.briefing.tactical_ahrefs as tactical_ahrefs

    calls = 0
    original = AhrefsCrossSourceMatcher.from_metric_facts

    class CountingMatcher:
        @classmethod
        def from_metric_facts(cls, **kwargs):
            nonlocal calls
            calls += 1
            return original(**kwargs)

    monkeypatch.setattr(tactical_ahrefs, "AhrefsCrossSourceMatcher", CountingMatcher)
    build_tactical_queue(
        use_cache=False,
        facts_by_connector={
            "ahrefs": [
                MetricFact(
                    name="ahrefs_content_gap_count",
                    value=1,
                    period="ahrefs_gap",
                    source_connector="ahrefs",
                    evidence_id="ev_ahrefs_batch",
                    dimensions={"keyword": "bdo odpady", "competitor_domain": "denios.pl"},
                ),
                MetricFact(
                    name="ahrefs_top_page_gap_count",
                    value=1,
                    period="ahrefs_gap",
                    source_connector="ahrefs",
                    evidence_id="ev_ahrefs_batch_two",
                    dimensions={"keyword": "audyt odpadowy", "competitor_domain": "manutan.pl"},
                ),
            ]
        },
    )
    assert calls == 1


def test_tactical_queue_keeps_weak_ahrefs_overlap_manual_without_action() -> None:
    queue = build_tactical_queue(
        use_cache=False,
        facts_by_connector={
            "ahrefs": [
                MetricFact(
                    name="ahrefs_content_gap_count",
                    value=1,
                    period="ahrefs_gap",
                    source_connector="ahrefs",
                    evidence_id="ev_ahrefs_mieszalnik_ibc",
                    dimensions={
                        "gap_type": "content_gap",
                        "keyword": "mieszalnik IBC",
                        "source_url": "https://denios.pl/mieszalnik-ibc/",
                        "competitor_domain": "denios.pl",
                    },
                )
            ],
            "google_search_console": [
                _gsc_fact(
                    "impressions",
                    120,
                    "kontener IBC odpady",
                    "https://www.ekologus.pl/kontener-ibc/",
                    "ev_gsc_kontener_ibc",
                    datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
                )
            ],
            "wordpress_ekologus": [
                MetricFact(
                    name="content_object_seen",
                    value=1,
                    period="wordpress_inventory",
                    source_connector="wordpress_ekologus",
                    evidence_id="ev_wp_lejek_ibc",
                    dimensions={
                        "title": "Lejek do kontenerów IBC",
                        "content_url": "https://www.ekologus.pl/lejek-do-kontenerow-ibc/",
                    },
                )
            ],
        },
    )

    item = next(item for item in queue.items if item.id.startswith("tq_ahrefs_"))

    assert item.dimensions["gsc_cross_check_strength"] == "weak"
    assert item.dimensions["wordpress_cross_check_strength"] == "weak"
    assert item.dimensions["gsc_demand"] == "missing"
    assert item.dimensions["wordpress_inventory_match"] == "missing"
    assert item.dimensions["gsc_overlap_terms"] == ""
    assert item.dimensions["wordpress_overlap_urls"] == ""
    assert item.action_ids == []
    assert "act_prepare_content_refresh_queue" not in item.action_ids
    assert set(item.source_connectors) == {
        "ahrefs",
        "google_search_console",
        "wordpress_ekologus",
    }
    assert set(item.evidence_ids) == {
        "ev_ahrefs_mieszalnik_ibc",
        "ev_gsc_kontener_ibc",
        "ev_wp_lejek_ibc",
    }
    assert "słabe podobieństwo" in item.diagnosis
    assert "słabe podobieństwo" in item.next_step
    assert "dokładne dopasowanie" not in item.diagnosis


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


def _tactical_item(
    item_id: str,
    domain: OpportunityDomain,
    *,
    priority: int,
) -> TacticalQueueItem:
    intent = {
        OpportunityDomain.gsc_seo: "content_refresh",
        OpportunityDomain.ga4: "landing_page_quality",
        OpportunityDomain.merchant: "merchant_feed_triage",
        OpportunityDomain.ahrefs: "content_create",
    }[domain]
    return TacticalQueueItem(
        id=item_id,
        title=item_id,
        domain=domain,
        intent=intent,
        priority=priority,
        source_connectors=[domain.value],
        evidence_ids=[f"ev_{item_id}"],
        diagnosis="test balance input",
        next_step="review",
    )
