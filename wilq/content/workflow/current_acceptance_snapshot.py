"""Build and revalidate the pinned source snapshot for a current-acceptance run."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from wilq.connectors.registry import get_connector_status
from wilq.content.canonical.urls import content_normalized_path
from wilq.content.knowledge.cards import ContentKnowledgeCard, ekologus_content_knowledge_cards
from wilq.content.knowledge.source_facts import ContentSourceFact, ekologus_source_facts
from wilq.content.workflow.current_acceptance_contracts import (
    CurrentAcceptanceBlocked,
    CurrentAcceptanceSnapshot,
)
from wilq.content.workflow.current_inventory_reconciliation import (
    CurrentInventoryScopeResponse,
    build_current_inventory_scope,
)
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    build_content_inventory_catalog,
    latest_wordpress_vendor_read_evidence_ids,
)
from wilq.schemas import ContentFreshnessAssessment
from wilq.schemas.core import ConnectorCoveredWindow, utc_now


def build_current_acceptance_snapshot(
    *,
    scope_loader: Callable[[], CurrentInventoryScopeResponse] = build_current_inventory_scope,
    catalog_loader: Callable[[], ContentInventoryCatalogResponse] = build_content_inventory_catalog,
    wordpress_evidence_loader: Callable[[], tuple[str, ...]] = (
        latest_wordpress_vendor_read_evidence_ids
    ),
    freshness_loader: Callable[[], str | None] | None = None,
    source_facts_loader: Callable[[], tuple[ContentSourceFact, ...]] = ekologus_source_facts,
    knowledge_cards_loader: Callable[[], tuple[ContentKnowledgeCard, ...]] = (
        ekologus_content_knowledge_cards
    ),
    now: datetime | None = None,
) -> CurrentAcceptanceSnapshot:
    """Pin one complete inventory, WordPress run, and reviewed source registry."""
    scope = scope_loader()
    catalog = catalog_loader()
    wordpress_ids = tuple(sorted(set(wordpress_evidence_loader())))
    freshness_state = (freshness_loader or _wordpress_freshness_state)()
    _validate_inventory_sources(scope, catalog, wordpress_ids, freshness_state)
    _require_exact_catalog_join(scope, catalog)
    captured_at = _aware_time(now or utc_now())
    source_facts = source_facts_loader()
    knowledge_cards = knowledge_cards_loader()
    refresh_ids = tuple(item for item in wordpress_ids if item.startswith("ev_refresh_"))
    if len(refresh_ids) != 1:
        raise CurrentAcceptanceBlocked(
            "current_acceptance_refresh_run_ambiguous",
            "WILQ WordPress connector",
            "Zidentyfikuj dokładnie jeden ukończony vendor_read WordPress dla inventory.",
        )
    freshness = _freshness_assessment(scope, refresh_ids[0])
    source_digest = _source_snapshot_digest(
        scope, catalog, wordpress_ids, source_facts, knowledge_cards
    )
    return CurrentAcceptanceSnapshot(
        scope=scope,
        catalog=catalog,
        wordpress_evidence_ids=wordpress_ids,
        freshness_state=freshness_state or "missing",
        freshness_assessment=freshness,
        source_facts=source_facts,
        knowledge_cards=knowledge_cards,
        captured_at=captured_at,
        source_snapshot_digest=source_digest,
    )


def current_acceptance_snapshot_is_current(snapshot: CurrentAcceptanceSnapshot) -> bool:
    try:
        scope = build_current_inventory_scope()
        catalog = build_content_inventory_catalog()
        facts = ekologus_source_facts()
        cards = ekologus_content_knowledge_cards()
        evidence_ids = tuple(sorted(set(latest_wordpress_vendor_read_evidence_ids())))
    except Exception:
        return False
    return (
        current_acceptance_scope_digest(scope) == current_acceptance_scope_digest(snapshot.scope)
        and _catalog_snapshot_digest(catalog) == _catalog_snapshot_digest(snapshot.catalog)
        and _registry_snapshot_digest(facts, cards)
        == _registry_snapshot_digest(snapshot.source_facts, snapshot.knowledge_cards)
        and _wordpress_freshness_state() == "fresh"
        and evidence_ids == snapshot.wordpress_evidence_ids
    )


def current_acceptance_scope_digest(scope: CurrentInventoryScopeResponse) -> str:
    return canonical_json_digest(
        {
            "inventory_evidence_ids": list(scope.inventory_evidence_ids),
            "rows": [
                {
                    "canonical_path": row.canonical_path,
                    "public_url": row.public_url,
                    "disposition": row.disposition,
                    "current_work_item_id": row.current_work_item_id,
                    "source_evidence_ids": list(row.source_evidence_ids),
                    "catalog_evidence_ids": list(row.catalog_evidence_ids),
                    "reason_code": row.reason_code,
                    "blocker_code": row.blocker_code,
                }
                for row in scope.rows
            ],
        }
    )


def _validate_inventory_sources(
    scope: CurrentInventoryScopeResponse,
    catalog: ContentInventoryCatalogResponse,
    wordpress_ids: tuple[str, ...],
    freshness_state: str | None,
) -> None:
    if scope.coverage_status != "complete" or catalog.coverage.status != "complete":
        raise CurrentAcceptanceBlocked(
            "current_acceptance_inventory_incomplete",
            "WILQ WordPress connector",
            "Ukończ kompletny bieżący odczyt inventory i ponów kwalifikację.",
        )
    if freshness_state != "fresh" or not wordpress_ids:
        raise CurrentAcceptanceBlocked(
            "current_acceptance_wordpress_freshness_blocked",
            "WILQ WordPress connector",
            "Odśwież bieżący odczyt WordPress przed kwalifikacją URL-i.",
        )
    if not set(catalog.evidence_ids).issubset(wordpress_ids):
        raise CurrentAcceptanceBlocked(
            "current_acceptance_catalog_snapshot_mismatch",
            "WILQ content workflow",
            "Odczytaj ponownie katalog z dokładnego bieżącego snapshotu WordPress.",
        )
    if not set(wordpress_ids).issubset(scope.inventory_evidence_ids):
        raise CurrentAcceptanceBlocked(
            "current_acceptance_inventory_snapshot_mismatch",
            "WILQ content workflow",
            "Odczytaj ponownie bieżący zakres inventory i katalog WordPress.",
        )


def _require_exact_catalog_join(
    scope: CurrentInventoryScopeResponse,
    catalog: ContentInventoryCatalogResponse,
) -> None:
    by_path: dict[str, list[ContentInventoryCatalogItem]] = {}
    for item in catalog.items:
        by_path.setdefault(content_normalized_path(item.url), []).append(item)
    seen_work_items: set[str] = set()
    for row in scope.rows:
        if row.disposition != "eligible":
            continue
        matches = by_path.get(row.canonical_path, [])
        if (
            len(matches) != 1
            or matches[0].url != row.public_url
            or matches[0].work_item_id != row.current_work_item_id
            or matches[0].evidence_id not in row.catalog_evidence_ids
            or row.current_work_item_id in seen_work_items
        ):
            raise CurrentAcceptanceBlocked(
                "current_acceptance_catalog_binding_mismatch",
                "WILQ content workflow",
                "Napraw exact powiązanie eligible sitemap URL-a z katalogiem i work-itemem.",
            )
        assert row.current_work_item_id is not None
        seen_work_items.add(row.current_work_item_id)


def _freshness_assessment(
    scope: CurrentInventoryScopeResponse,
    refresh_evidence_id: str,
) -> ContentFreshnessAssessment:
    return ContentFreshnessAssessment(
        state="fresh",
        checked_at=scope.checked_at,
        stale_after_hours=48,
        requires_refresh=False,
        connector_refresh_run_ids={
            "wordpress_ekologus": refresh_evidence_id.removeprefix("ev_")
        },
        connector_covered_windows={
            "wordpress_ekologus": ConnectorCoveredWindow(
                snapshot_date=scope.checked_at.date().isoformat(),
                completeness="complete",
                coverage_scope="exact current public sitemap and WordPress catalog",
                coverage_count=scope.counts.rows,
                requested_count=scope.counts.rows,
                covered_count=scope.counts.rows,
            )
        },
        summary="Kompletny, świeży snapshot WordPress przypięty do bieżącego inventory.",
        next_step="Użyj wyłącznie exact evidence tego snapshotu.",
    )


def _source_snapshot_digest(
    scope: CurrentInventoryScopeResponse,
    catalog: ContentInventoryCatalogResponse,
    wordpress_ids: tuple[str, ...],
    source_facts: tuple[ContentSourceFact, ...],
    knowledge_cards: tuple[ContentKnowledgeCard, ...],
) -> str:
    return canonical_json_digest(
        {
            "scope_digest": current_acceptance_scope_digest(scope),
            "catalog_digest": _catalog_snapshot_digest(catalog),
            "wordpress_evidence_ids": list(wordpress_ids),
            "source_registry_digest": _registry_snapshot_digest(source_facts, knowledge_cards),
        }
    )


def _catalog_snapshot_digest(catalog: ContentInventoryCatalogResponse) -> str:
    items = sorted(
        (
            {
                "work_item_id": item.work_item_id,
                "url": item.url,
                "canonical_path": content_normalized_path(item.url),
                "content_type": item.content_type,
                "source_connector": item.source_connector,
                "evidence_id": item.evidence_id,
                "collected_at": item.collected_at.isoformat(),
            }
            for item in catalog.items
        ),
        key=lambda item: (item["canonical_path"], item["work_item_id"]),
    )
    return canonical_json_digest(
        {"items": items, "evidence_ids": sorted(set(catalog.evidence_ids))}
    )


def _registry_snapshot_digest(
    facts: tuple[ContentSourceFact, ...],
    cards: tuple[ContentKnowledgeCard, ...],
) -> str:
    return canonical_json_digest(
        {
            "source_facts": [
                fact.model_dump(mode="json")
                for fact in sorted(facts, key=lambda item: item.source_id)
            ],
            "knowledge_cards": [
                card.model_dump(mode="json") for card in sorted(cards, key=lambda item: item.id)
            ],
        }
    )


def _aware_time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Current acceptance snapshot time must be timezone-aware.")
    return value.astimezone(UTC)


def _wordpress_freshness_state() -> str | None:
    status = get_connector_status("wordpress_ekologus")
    return None if status is None else str(status.freshness.state)


__all__ = [
    "build_current_acceptance_snapshot",
    "current_acceptance_scope_digest",
    "current_acceptance_snapshot_is_current",
]
