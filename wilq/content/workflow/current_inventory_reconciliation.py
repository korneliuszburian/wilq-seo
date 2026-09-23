"""Fail-closed preflight for the public current inventory reconciliation route."""

from __future__ import annotations

from wilq.content.workflow.workspace.catalog import (
    build_content_inventory_catalog,
    latest_wordpress_vendor_read_evidence_ids,
)

_INCOMPLETE_COVERAGE = "inventory_coverage_incomplete"
_ELIGIBLE_SCOPE_POLICY_UNAVAILABLE = "current_eligible_scope_policy_unavailable"
_SOURCE_EVIDENCE_MISSING = "inventory_source_evidence_missing"


class CurrentInventoryReconciliationBlocked(ValueError):
    """Typed blocker raised before reconciliation can write current state."""

    def __init__(self, detail: str, coverage_status: str, evidence_ids: list[str]) -> None:
        super().__init__(detail)
        self.detail = detail
        self.coverage_status = coverage_status
        self.evidence_ids = evidence_ids


def preflight_current_inventory_reconciliation() -> None:
    """Block until complete coverage and current eligible-scope policy exist."""

    catalog = build_content_inventory_catalog()
    coverage_status = catalog.coverage.status
    latest_source_evidence_ids = latest_wordpress_vendor_read_evidence_ids()
    if not latest_source_evidence_ids:
        raise CurrentInventoryReconciliationBlocked(
            _SOURCE_EVIDENCE_MISSING,
            coverage_status,
            [],
        )
    evidence_ids = sorted(set(catalog.evidence_ids) | set(latest_source_evidence_ids))
    if coverage_status != "complete":
        raise CurrentInventoryReconciliationBlocked(
            _INCOMPLETE_COVERAGE,
            coverage_status,
            evidence_ids,
        )
    raise CurrentInventoryReconciliationBlocked(
        _ELIGIBLE_SCOPE_POLICY_UNAVAILABLE,
        coverage_status,
        evidence_ids,
    )


__all__ = [
    "CurrentInventoryReconciliationBlocked",
    "preflight_current_inventory_reconciliation",
]
