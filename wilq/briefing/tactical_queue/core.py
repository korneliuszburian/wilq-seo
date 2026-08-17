"""Decomposed tactical_queue core implementation."""

from __future__ import annotations

import os
from time import monotonic

from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.briefing.tactical_merchant import build_merchant_feed_items
from wilq.briefing.tactical_queue.items import (
    _ahrefs_gap_items,
    _balanced_tactical_items,
    _compact_tactical_groups,
    _ga4_quality_items,
    _tactical_action_ids_by_connector,
    build_gsc_content_tactical_items,
)
from wilq.briefing.tactical_queue.metrics import (
    _is_probe_only_fact,
    _tactical_metric_facts,
    _wordpress_content_index,
)
from wilq.briefing.tactical_queue.shared import (
    DEFAULT_TACTICAL_QUEUE_CACHE_SECONDS,
    TACTICAL_QUEUE_LIMIT,
    TacticalQueueCacheEntry,
)
from wilq.content.operator_copy import unique
from wilq.schemas import MetricFact, TacticalQueueResponse

_cached_tactical_queue: TacticalQueueCacheEntry | None = None


def build_tactical_queue(
    use_cache: bool = True,
    facts_by_connector: dict[str, list[MetricFact]] | None = None,
) -> TacticalQueueResponse:
    if use_cache and facts_by_connector is None:
        cached_queue = _read_tactical_queue_cache()
        if cached_queue is not None:
            return cached_queue
    queue = _build_tactical_queue(facts_by_connector=facts_by_connector)
    if use_cache and facts_by_connector is None:
        _write_tactical_queue_cache(queue)
    return queue


def clear_tactical_queue_cache() -> None:
    global _cached_tactical_queue
    _cached_tactical_queue = None


def _read_tactical_queue_cache() -> TacticalQueueResponse | None:
    cache_seconds = _cache_seconds()
    if cache_seconds <= 0:
        return None
    if _cached_tactical_queue is None:
        return None
    if monotonic() - _cached_tactical_queue.created_at > cache_seconds:
        return None
    return _cached_tactical_queue.queue


def _write_tactical_queue_cache(queue: TacticalQueueResponse) -> None:
    global _cached_tactical_queue
    if _cache_seconds() <= 0:
        return
    _cached_tactical_queue = TacticalQueueCacheEntry(created_at=monotonic(), queue=queue)


def _cache_seconds() -> float:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return 0.0
    configured = os.getenv("WILQ_TACTICAL_QUEUE_CACHE_SECONDS")
    if configured is None:
        return DEFAULT_TACTICAL_QUEUE_CACHE_SECONDS
    try:
        return max(0.0, float(configured))
    except ValueError:
        return DEFAULT_TACTICAL_QUEUE_CACHE_SECONDS


def _build_tactical_queue(
    facts_by_connector: dict[str, list[MetricFact]] | None = None,
) -> TacticalQueueResponse:
    facts = [
        fact
        for fact in _tactical_metric_facts(facts_by_connector=facts_by_connector)
        if fact.dimensions and not _is_probe_only_fact(fact)
    ]
    action_ids_by_connector = _tactical_action_ids_by_connector()
    wordpress_index = _wordpress_content_index(facts)
    gsc_cross_check_facts = [
        fact for fact in facts if fact.source_connector == "google_search_console"
    ]
    wordpress_cross_check_facts = [
        fact for fact in facts if fact.source_connector.startswith("wordpress")
    ]
    items = [
        *build_gsc_content_tactical_items(
            facts,
            wordpress_action_ids=action_ids_by_connector.get("wordpress_ekologus", []),
        ),
        *_ga4_quality_items(facts, action_ids_by_connector, wordpress_index),
        *build_merchant_feed_items(facts=facts, action_ids=action_ids_by_connector),
        *_ahrefs_gap_items(
            facts,
            action_ids_by_connector,
            gsc_cross_check_facts,
            wordpress_cross_check_facts,
        ),
    ]
    items = _balanced_tactical_items(items, limit=TACTICAL_QUEUE_LIMIT)
    return TacticalQueueResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        items=items,
        compact_groups=_compact_tactical_groups(items),
        evidence_ids=unique(evidence_id for item in items for evidence_id in item.evidence_ids),
        action_ids=unique(action_id for item in items for action_id in item.action_ids),
    )
