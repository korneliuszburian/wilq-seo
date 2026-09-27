"""Synthetic builders shared by current-acceptance contract tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from wilq.content.knowledge.cards import ContentKnowledgeCard
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.workflow.current_acceptance_contracts import (
    CurrentAcceptanceAttempt,
    CurrentAcceptanceSnapshot,
    current_acceptance_scope_coverage_digest,
)
from wilq.content.workflow.current_inventory_reconciliation import (
    CurrentInventoryScopeCounts,
    CurrentInventoryScopeResponse,
    CurrentInventoryScopeRow,
)
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    ContentInventoryCoverage,
)
from wilq.schemas import ContentFreshnessAssessment
from wilq.schemas.core import ConnectorCoveredWindow


def _queued_attempt(
    snapshot: CurrentAcceptanceSnapshot,
    *,
    run_id: str,
    request_id: str,
    created_at: datetime | None = None,
    input_digest: str = "a" * 64,
) -> CurrentAcceptanceAttempt:
    attempt_time = created_at if created_at is not None else snapshot.captured_at
    return CurrentAcceptanceAttempt(
        run_id=run_id,
        request_id=request_id,
        input_digest=input_digest,
        source_snapshot_digest=snapshot.source_snapshot_digest,
        inventory_evidence_ids=snapshot.scope.inventory_evidence_ids,
        wordpress_evidence_ids=snapshot.wordpress_evidence_ids,
        scope_row_count=len(snapshot.scope.rows),
        scope_row_digest=current_acceptance_scope_coverage_digest(
            (row.canonical_path, row.disposition) for row in snapshot.scope.rows
        ),
        status="queued",
        created_at=attempt_time,
        updated_at=attempt_time,
    )


def _snapshot(
    *,
    source_facts: tuple[ContentSourceFact, ...] | None = None,
    cards: tuple[ContentKnowledgeCard, ...] | None = None,
    page_status: Literal["reviewed_material_current", "observed_material_current"] = (
        "observed_material_current"
    ),
) -> tuple[CurrentAcceptanceSnapshot, CurrentInventoryScopeRow, CurrentPageEvidenceResponse]:
    checked_at = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
    row, scope, catalog = _inventory_fixture(checked_at)
    freshness = ContentFreshnessAssessment(
        state="fresh",
        checked_at=checked_at,
        stale_after_hours=48,
        requires_refresh=False,
        connector_refresh_run_ids={"wordpress_ekologus": "refresh_wordpress_test"},
        connector_covered_windows={
            "wordpress_ekologus": ConnectorCoveredWindow(
                snapshot_date=checked_at.date().isoformat(),
                completeness="complete",
                coverage_scope="exact test inventory",
                coverage_count=1,
                requested_count=1,
                covered_count=1,
            )
        },
        summary="Synthetic exact WordPress freshness.",
        next_step="Read exact page material.",
    )
    snapshot = CurrentAcceptanceSnapshot(
        scope=scope,
        catalog=catalog,
        wordpress_evidence_ids=("ev_wp_run",),
        freshness_state="fresh",
        freshness_assessment=freshness,
        source_facts=source_facts if source_facts is not None else (_approved_fact(),),
        knowledge_cards=cards if cards is not None else (_exact_page_card(),),
        captured_at=checked_at,
        source_snapshot_digest=canonical_json_digest(
            {"scope": "test-scope", "catalog": "test-catalog", "registry": "test-registry"}
        ),
    )
    page = CurrentPageEvidenceResponse(
        status=page_status,
        decision="Exact current page material was observed.",
        work_item_id="wi_current_acceptance",
        page_url="https://www.ekologus.pl/candidates/",
        material_meaning_digest="a" * 64,
        current_evidence_ids=["ev_current_material"],
        catalog_evidence_ids=["ev_wp_run"],
        safe_next_step="Review page-bound source facts.",
    )
    return snapshot, row, page


def _inventory_fixture(
    checked_at: datetime,
) -> tuple[
    CurrentInventoryScopeRow,
    CurrentInventoryScopeResponse,
    ContentInventoryCatalogResponse,
]:
    public_url = "https://www.ekologus.pl/candidates/"
    work_item_id = "wi_current_acceptance"
    row = CurrentInventoryScopeRow(
        canonical_path="/candidates",
        public_url=public_url,
        disposition="eligible",
        current_work_item_id=work_item_id,
        source_evidence_ids=("ev_wp_run",),
        catalog_evidence_ids=("ev_wp_run",),
        safe_next_step="Sprawdź dokładny materiał.",
    )
    scope = CurrentInventoryScopeResponse(
        checked_at=checked_at,
        inventory_evidence_ids=("ev_wp_run", "ev_wp_status"),
        counts=CurrentInventoryScopeCounts(rows=1, eligible=1, excluded=0, blocked=0),
        rows=(row,),
    )
    catalog_item = ContentInventoryCatalogItem(
        catalog_id="catalog_candidates",
        work_item_id=work_item_id,
        url=public_url,
        path="/candidates",
        content_type="post",
        material_status="ready",
        source_connector="wordpress_ekologus",
        evidence_id="ev_wp_run",
        collected_at=checked_at,
    )
    catalog = ContentInventoryCatalogResponse(
        status="ready",
        total_count=1,
        ready_count=1,
        items=[catalog_item],
        source_connectors=["wordpress_ekologus"],
        evidence_ids=["ev_wp_run"],
        coverage=ContentInventoryCoverage(
            status="complete",
            source_count=1,
            returned_count=1,
            public_sitemap_source_count=1,
            public_sitemap_returned_count=1,
            public_sitemap_limit=1,
            public_sitemap_truncated=False,
            limit=1,
            truncated=False,
        ),
    )
    return row, scope, catalog


def _approved_fact() -> ContentSourceFact:
    return ContentSourceFact(
        source_id="synthetic_official_fact",
        source_type="legal_update",
        privacy_class="commit_safe",
        source_url_or_path="https://example.gov/exact-source",
        extracted_fact="Synthetic approved fact for the exact page.",
        scope="claim_policy",
        freshness_date="2026-09-24",
        confidence=0.9,
        review_status="approved",
        reviewer="synthetic_wilku",
        evidence_ids=["ev_official_fact"],
        source_connectors=["official_regulatory_review"],
        target_card_id="synthetic_profile",
        target_card_type="regulatory_source",
        target_card_title="Synthetic profile",
        official_source=True,
        regulatory_profile_id="synthetic_profile",
        regulatory_profile_version="synthetic-v1",
        regulatory_requirement_ids=["requirement_exact"],
        applicable_canonical_paths=["/candidates"],
    )


def _exact_page_card() -> ContentKnowledgeCard:
    return ContentKnowledgeCard(
        id="synthetic_profile",
        card_type="service",
        title="Synthetic exact service card",
        summary="Exact page binding for scope validation.",
        service_binding_urls=["https://www.ekologus.pl/candidates/"],
        source_fact_ids=["synthetic_official_fact"],
        evidence_ids=["ev_service_card"],
        source_connectors=["synthetic_card_connector"],
        lifecycle_status="approved_current",
        confidence=0.9,
        freshness="2026-09-24",
    )
