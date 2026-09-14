"""Persist current inventory receipts before a deliberately blocked classification."""

from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from wilq.briefing.content_diagnostics import build_content_freshness_assessment_fast
from wilq.content.canonical.urls import content_normalized_path
from wilq.content.workflow.authoring_inventory_receipt import (
    ContentAuthoringInventoryReceipt,
    ContentAuthoringInventoryReceiptRecordResult,
    _build_content_authoring_inventory_receipt_from_catalog,
)
from wilq.content.workflow.decisions.current_blocked import (
    build_current_all_blocked_classification,
)
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationRecordResult,
    ContentProductionClassificationRun,
    ContentProductionRegisteredInventoryReceipt,
    canonical_json_digest,
)
from wilq.content.workflow.store.store import content_workflow_store
from wilq.content.workflow.workspace.catalog import build_content_inventory_catalog

_REQUIRED_CONNECTORS = ("google_search_console", "wordpress_ekologus")
_RECORDED_BY = "current_inventory_reconciler"


class _CurrentInventoryReconciliationStore(Protocol):
    def record_content_authoring_inventory_receipt(
        self, receipt: ContentAuthoringInventoryReceipt
    ) -> ContentAuthoringInventoryReceiptRecordResult: ...


class CurrentInventoryReconciliationResult(BaseModel):
    """Safe local write result; it contains no authoring or delivery authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    registered_inventory_count: int = Field(ge=0)
    missing_inventory_count: int = Field(ge=0)
    receipt_status_counts: dict[str, int]
    classification: ContentProductionClassificationRecordResult


def reconcile_current_authoring_inventory() -> CurrentInventoryReconciliationResult:
    """Reconcile only material-bearing keep rows, then persist their blocked packet."""

    catalog = build_content_inventory_catalog()
    freshness = build_content_freshness_assessment_fast(relevant_connector_ids=_REQUIRED_CONNECTORS)
    recorded_at = freshness.checked_at
    candidate_receipts = {
        content_normalized_path(item.path): _build_content_authoring_inventory_receipt_from_catalog(
            item=item,
            catalog=catalog,
            recorded_by=_RECORDED_BY,
            recorded_at=recorded_at,
        )
        for item in catalog.items
        if item.material_status in {"content_summary", "content_and_structure", "structure_only"}
    }
    run = build_current_all_blocked_classification(
        catalog=catalog,
        freshness=freshness,
        base_revision=_current_checkout_revision(),
        recorded_at=recorded_at,
        inventory_receipts=candidate_receipts,
    )
    accepted_receipts = {
        row.canonical_path: candidate_receipts[row.canonical_path]
        for row in run.rows
        if isinstance(row.source_receipt, ContentProductionRegisteredInventoryReceipt)
    }
    store = content_workflow_store()
    receipt_results = [
        _record_receipt_with_retry_idempotency(store, receipt)
        for _, receipt in sorted(accepted_receipts.items())
    ]
    if any(result.status == "conflict" for result in receipt_results):
        raise ValueError("Current inventory receipt conflicts with its append-only record.")
    existing = store.load_latest_production_classification()
    classification = (
        ContentProductionClassificationRecordResult(status="idempotent", run=existing)
        if existing is not None and _same_current_snapshot(existing, run)
        else store.record_production_classification(run)
    )
    return CurrentInventoryReconciliationResult(
        registered_inventory_count=len(accepted_receipts),
        missing_inventory_count=len(run.rows) - len(accepted_receipts),
        receipt_status_counts=_receipt_status_counts(receipt_results),
        classification=classification,
    )


def _record_receipt_with_retry_idempotency(
    store: _CurrentInventoryReconciliationStore,
    receipt: ContentAuthoringInventoryReceipt,
) -> ContentAuthoringInventoryReceiptRecordResult:
    result = store.record_content_authoring_inventory_receipt(receipt)
    if result.status != "conflict" or not _same_inventory_snapshot(result.receipt, receipt):
        return result
    return result.model_copy(update={"status": "idempotent"})


def _same_inventory_snapshot(
    existing: ContentAuthoringInventoryReceipt,
    candidate: ContentAuthoringInventoryReceipt,
) -> bool:
    existing_payload = existing.model_dump(mode="json")
    candidate_payload = candidate.model_dump(mode="json")
    for payload in (existing_payload, candidate_payload):
        payload.pop("recorded_by", None)
        payload.pop("recorded_at", None)
    return existing_payload == candidate_payload


def _receipt_status_counts(
    results: list[ContentAuthoringInventoryReceiptRecordResult],
) -> dict[str, int]:
    counts: Counter[str] = Counter(result.status for result in results)
    return {status: counts[status] for status in ("created", "idempotent", "conflict")}


def _same_current_snapshot(
    existing: ContentProductionClassificationRun,
    candidate: ContentProductionClassificationRun,
) -> bool:
    """Ignore assessment timestamps, never evidence, when deciding retry idempotency."""

    return _current_snapshot_digest(existing) == _current_snapshot_digest(candidate)


def _current_snapshot_digest(run: ContentProductionClassificationRun) -> str:
    rows = []
    for row in run.rows:
        value = row.model_dump(mode="json")
        historical_protection = value.get("blocked_historical_protection")
        if isinstance(historical_protection, dict):
            historical_protection.pop("current_verification_checked_at", None)
        rows.append(value)
    freshness = run.freshness.model_dump(mode="json")
    freshness.pop("checked_at", None)
    return canonical_json_digest(
        {
            "policy_id": run.input.policy_id,
            "packet_schema_version": run.input.packet_schema_version,
            "base_revision": run.input.base_revision,
            "freshness": freshness,
            "source_receipts": [item.model_dump(mode="json") for item in run.source_receipts],
            "rows": rows,
        }
    )


def _current_checkout_revision() -> str:
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    revision = result.stdout.strip()
    if result.returncode != 0 or len(revision) != 40:
        raise ValueError("Current checkout revision is unavailable.")
    return revision


__all__ = [
    "CurrentInventoryReconciliationResult",
    "reconcile_current_authoring_inventory",
]
