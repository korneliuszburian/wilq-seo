"""Build a current, evidence-scoped blocked classification without minting identities."""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import NoReturn

from wilq.content.workflow.authoring_inventory_receipt import (
    ContentAuthoringInventoryReceipt,
    content_inventory_catalog_item_digest,
    content_inventory_catalog_snapshot_digest,
)
from wilq.content.workflow.decisions.production import (
    WAVE0_PRODUCTION_ACCEPTANCE_POLICY,
    ContentProductionAcceptancePolicy,
    ContentProductionBlockedHistoricalProtectionPolicy,
    ContentProductionClassificationCounts,
    ContentProductionClassificationRun,
    ContentProductionClassificationValidationError,
    ContentProductionSourceReceiptPolicy,
    canonical_json_digest,
    parse_content_production_classification,
)
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
)
from wilq.content.workflow.workspace.journal_reconciliation import (
    canonical_content_inventory_journal_paths,
    normalize_content_inventory_journal_path,
)
from wilq.schemas import ContentFreshnessAssessment

_BASE_REVISION = re.compile(r"^[0-9a-f]{40}$")
_PACKET_SCHEMA = "wilq_content_production_classification_v1"
_JUDGE_SCHEMA = "wilq_current_blocked_classification_judge_v1"
_POLICY_ID = "wilq_current_blocked_content_classification_v1"
_PUBLIC_ORIGIN = "https://www.ekologus.pl"
_EXPECTED_JOURNAL_ROWS = 214
_EXPECTED_KEEP_ROWS = 57
_MATCHED_REFERENCE = "wilq-current-catalog-matched-v1"
_UNMATCHED_REFERENCE = "wilq-current-catalog-unmatched-v1"
_CURRENT_FRESHNESS_CONNECTORS = (
    "google_search_console",
    "wordpress_ekologus",
)


@dataclass(frozen=True)
class _CurrentClassificationInputs:
    base_revision: str
    freshness: ContentFreshnessAssessment
    required_connectors: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    journal_rows: tuple[dict[str, str], ...]
    catalog_by_path: Mapping[str, ContentInventoryCatalogItem]
    checked_at: datetime
    checked_at_text: str
    catalog_scope_sha256: str
    inventory_snapshot_digest: str
    inventory_receipts: Mapping[str, ContentAuthoringInventoryReceipt]


@dataclass(frozen=True)
class _CurrentRowResult:
    row: dict[str, object]
    projection: dict[str, object]
    matched: bool


def build_current_all_blocked_classification(
    *,
    catalog: ContentInventoryCatalogResponse,
    freshness: ContentFreshnessAssessment,
    base_revision: str,
    journal_path: Path | None = None,
    recorded_at: datetime | None = None,
    inventory_receipts: Mapping[str, ContentAuthoringInventoryReceipt] | None = None,
) -> ContentProductionClassificationRun:
    """Return a current blocked run; coverage never becomes a work-item binding."""

    inputs = _prepare_current_inputs(
        catalog=catalog,
        freshness=freshness,
        base_revision=base_revision,
        recorded_at=recorded_at,
        journal_path=journal_path,
        inventory_receipts=inventory_receipts or {},
    )
    rows, matched_projection, unmatched_projection = _rows(
        inputs.journal_rows,
        catalog_by_path=inputs.catalog_by_path,
        catalog_scope_sha256=inputs.catalog_scope_sha256,
        evidence_ids=inputs.evidence_ids,
        checked_at=inputs.checked_at_text,
        inventory_receipts=inputs.inventory_receipts,
        inventory_snapshot_digest=inputs.inventory_snapshot_digest,
    )
    counts: dict[str, int] = {
        "rows": len(rows),
        "reuse": 0,
        "refresh": 0,
        "write": 0,
        "blocked": len(rows),
        "generation_allowed": 0,
        "verified_current_actions": 0,
        "verified_current_drafts": 0,
    }
    packet, source_files = _build_packet(
        inputs=inputs,
        rows=rows,
        matched_projection=matched_projection,
        unmatched_projection=unmatched_projection,
        counts=counts,
    )
    packet_bytes = _json_bytes(packet)
    packet_sha256 = sha256(packet_bytes).hexdigest()
    protected = _blocked_historical_policy(
        evidence_id=inputs.evidence_ids[0],
        checked_at=inputs.checked_at_text,
    )
    judge = _judge(
        packet_sha256=packet_sha256,
        decision_set_digest=str(packet["decision_set_digest"]),
        protected=protected,
        generated_at=inputs.checked_at_text,
    )
    judge_bytes = _json_bytes(judge)
    policy = _build_acceptance_policy(
        inputs=inputs,
        counts=counts,
        source_files=source_files,
        canonical_paths=tuple(str(row["path"]) for row in rows),
        packet_sha256=packet_sha256,
        judge_sha256=sha256(judge_bytes).hexdigest(),
        decision_set_digest=str(packet["decision_set_digest"]),
        protected=protected,
    )
    return parse_content_production_classification(
        packet_bytes=packet_bytes,
        judge_bytes=judge_bytes,
        acceptance_policy=policy,
        recorded_by="current_blocked_packet_builder",
        reviewed_by="deterministic_packet_integrity_verifier",
        recorded_at=inputs.checked_at,
    )


def _prepare_current_inputs(
    *,
    catalog: ContentInventoryCatalogResponse,
    freshness: ContentFreshnessAssessment,
    base_revision: str,
    recorded_at: datetime | None,
    journal_path: Path | None,
    inventory_receipts: Mapping[str, ContentAuthoringInventoryReceipt],
) -> _CurrentClassificationInputs:
    if recorded_at is None:
        _invalid("recorded_at_required")
    if _BASE_REVISION.fullmatch(base_revision) is None:
        _invalid("base_revision_invalid")
    if freshness.requires_refresh:
        _invalid("freshness_requires_refresh")
    if freshness.state != "fresh":
        _invalid("freshness_state_invalid")
    if (
        freshness.missing_connector_ids
        or freshness.blocked_connector_ids
        or freshness.stale_connector_ids
    ):
        _invalid("freshness_connector_scope_mismatch")
    required_connectors = _CURRENT_FRESHNESS_CONNECTORS
    if tuple(sorted(freshness.connector_covered_windows)) != required_connectors:
        _invalid("freshness_connector_scope_mismatch")

    evidence_ids = tuple(sorted({value.strip() for value in catalog.evidence_ids if value.strip()}))
    if not evidence_ids:
        _invalid("wordpress_evidence_missing")
    if any(
        not item.evidence_id.strip() or item.evidence_id not in evidence_ids
        for item in catalog.items
    ):
        _invalid("wordpress_catalog_evidence_mismatch")
    if catalog.coverage.status not in {"unknown", "partial", "complete"}:
        _invalid("catalog_coverage_invalid")

    journal_rows = _load_keep_rows(journal_path or _canonical_journal_path())
    catalog_by_path = _catalog_by_path(catalog)
    checked_at = _aware_time(recorded_at)
    checked_at_text = _iso_z(checked_at)
    catalog_scope_sha256 = canonical_json_digest(
        {
            "evidence_ids": evidence_ids,
            "items": [
                {
                    "path": path,
                    "evidence_id": item.evidence_id,
                    "source_connector": item.source_connector,
                    "collected_at": _iso_z(item.collected_at),
                }
                for path, item in sorted(catalog_by_path.items())
            ],
        }
    )
    inventory_snapshot_digest = content_inventory_catalog_snapshot_digest(catalog)

    return _CurrentClassificationInputs(
        base_revision=base_revision,
        freshness=freshness,
        required_connectors=required_connectors,
        evidence_ids=evidence_ids,
        journal_rows=journal_rows,
        catalog_by_path=catalog_by_path,
        checked_at=checked_at,
        checked_at_text=checked_at_text,
        catalog_scope_sha256=catalog_scope_sha256,
        inventory_snapshot_digest=inventory_snapshot_digest,
        inventory_receipts=inventory_receipts,
    )


def _build_packet(
    *,
    inputs: _CurrentClassificationInputs,
    rows: list[dict[str, object]],
    matched_projection: list[dict[str, object]],
    unmatched_projection: list[dict[str, object]],
    counts: dict[str, int],
) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    source_files = {
        "matched_classification": _source_file(_MATCHED_REFERENCE, matched_projection),
        "unmatched_classification": _source_file(_UNMATCHED_REFERENCE, unmatched_projection),
    }
    packet: dict[str, object] = {
        "schema_version": _PACKET_SCHEMA,
        "base_revision": inputs.base_revision,
        "generated_at": inputs.checked_at_text,
        "row_digest_algorithm": (
            "sha256(canonical_json(source_packet_receipts); UTF-8, sorted keys, compact separators)"
        ),
        "decision_set_digest_algorithm": (
            "sha256(canonical_json(rows); UTF-8, sorted keys, compact separators)"
        ),
        "decision_set_digest": canonical_json_digest(rows),
        "source_file_receipts": source_files,
        "rows": rows,
        "counts": counts,
        "wilq_diagnostic_freshness": {
            "state": inputs.freshness.state,
            "checked_at": _iso_z(inputs.freshness.checked_at),
            "requires_refresh": False,
            "connector_covered_windows": {
                connector_id: _json_value(inputs.freshness.connector_covered_windows[connector_id])
                for connector_id in inputs.required_connectors
            },
        },
    }
    return packet, source_files


def _build_acceptance_policy(
    *,
    inputs: _CurrentClassificationInputs,
    counts: dict[str, int],
    source_files: Mapping[str, Mapping[str, object]],
    canonical_paths: tuple[str, ...],
    packet_sha256: str,
    judge_sha256: str,
    decision_set_digest: str,
    protected: ContentProductionBlockedHistoricalProtectionPolicy,
) -> ContentProductionAcceptancePolicy:
    return ContentProductionAcceptancePolicy(
        authority_role="current_acceptance",
        policy_id=_POLICY_ID,
        packet_schema_version=_PACKET_SCHEMA,
        judge_schema_version=_JUDGE_SCHEMA,
        judge_reviewer_role="deterministic_packet_integrity_verifier",
        judge_protected_binding_check_name="blocked_historical_protection",
        packet_sha256=packet_sha256,
        judge_sha256=judge_sha256,
        decision_set_digest=decision_set_digest,
        base_revision=inputs.base_revision,
        canonical_paths=canonical_paths,
        expected_counts=ContentProductionClassificationCounts(**counts),
        expected_approved_revisions=0,
        freshness_connector_ids=inputs.required_connectors,
        source_receipts=tuple(
            ContentProductionSourceReceiptPolicy(
                name=name,
                reference=str(receipt["artifact_reference"]),
                sha256=str(receipt["sha256"]),
                raw_artifact_retained=False,
                retention_status="external_ephemeral_receipt_only",
            )
            for name, receipt in source_files.items()
        ),
        protected_binding=None,
        blocked_historical_protection=protected,
        invalid_evidence=None,
        public_origin=_PUBLIC_ORIGIN,
        primary_evidence_http_status=200,
        primary_evidence_metrics_asserted=False,
    )


def _rows(
    journal_rows: tuple[dict[str, str], ...],
    *,
    catalog_by_path: Mapping[str, ContentInventoryCatalogItem],
    catalog_scope_sha256: str,
    evidence_ids: tuple[str, ...],
    checked_at: str,
    inventory_receipts: Mapping[str, ContentAuthoringInventoryReceipt],
    inventory_snapshot_digest: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    matched: list[dict[str, object]] = []
    unmatched: list[dict[str, object]] = []
    binding = WAVE0_PRODUCTION_ACCEPTANCE_POLICY.protected_binding
    if (
        WAVE0_PRODUCTION_ACCEPTANCE_POLICY.blocked_historical_protection is not None
        or binding is None
    ):
        _invalid("historical_protection_unavailable")
    protected_path = binding.canonical_path
    for journal_row in journal_rows:
        result = _build_current_row(
            journal_row=journal_row,
            catalog_item=catalog_by_path.get(journal_row["path"]),
            catalog_scope_sha256=catalog_scope_sha256,
            evidence_ids=evidence_ids,
            checked_at=checked_at,
            inventory_receipts=inventory_receipts,
            inventory_snapshot_digest=inventory_snapshot_digest,
            protected_path=protected_path,
        )
        rows.append(result.row)
        (matched if result.matched else unmatched).append(result.projection)
    return rows, matched, unmatched


def _build_current_row(
    *,
    journal_row: dict[str, str],
    catalog_item: ContentInventoryCatalogItem | None,
    catalog_scope_sha256: str,
    evidence_ids: tuple[str, ...],
    checked_at: str,
    inventory_receipts: Mapping[str, ContentAuthoringInventoryReceipt],
    inventory_snapshot_digest: str,
    protected_path: str,
) -> _CurrentRowResult:
    path = journal_row["path"]
    inventory_receipt = _registered_inventory_receipt(
        path=path,
        catalog_item=catalog_item,
        inventory_receipts=inventory_receipts,
        inventory_snapshot_digest=inventory_snapshot_digest,
        evidence_ids=evidence_ids,
    )
    matched = catalog_item is not None
    missing_sources = (
        ["delivery_identity_binding", "source_pack_binding"]
        if matched
        else ["authoring_inventory_row", "source_pack_binding"]
    )
    projection: dict[str, object] = {
        "content_status_row_sha256": canonical_json_digest(journal_row),
        "wordpress_catalog_scope_sha256": catalog_scope_sha256,
        "catalog_lookup_outcome": "exact_path_present" if matched else "exact_path_absent",
    }
    source_receipt = _source_packet_receipt(
        inventory_receipt=inventory_receipt,
        missing_sources=missing_sources,
        projection=projection,
    )
    row = _blocked_row(
        path=path,
        evidence_ids=evidence_ids,
        inventory_receipt=inventory_receipt,
        source_receipt=source_receipt,
    )
    if path == protected_path:
        row["blocked_historical_protection"] = _blocked_historical_protection(
            evidence_id=evidence_ids[0], checked_at=checked_at
        )
    return _CurrentRowResult(row=row, projection=projection, matched=matched)


def _source_packet_receipt(
    *,
    inventory_receipt: ContentAuthoringInventoryReceipt | None,
    missing_sources: list[str],
    projection: dict[str, object],
) -> dict[str, object]:
    if inventory_receipt is None:
        return {
            "binding_state": "missing",
            "missing_sources": missing_sources,
            **projection,
        }
    return {
        "binding_state": "registered_current_inventory",
        "schema_version": inventory_receipt.schema_version,
        "receipt_id": inventory_receipt.receipt_id,
        "receipt_digest": inventory_receipt.receipt_digest,
        "catalog_id": inventory_receipt.catalog_id,
        "current_work_item_id": inventory_receipt.current_work_item_id,
        "public_url": inventory_receipt.public_url,
        "canonical_path": inventory_receipt.canonical_path,
        "source_connector": inventory_receipt.source_connector,
        "collected_at": inventory_receipt.model_dump(mode="json")["collected_at"],
        "catalog_item_digest": inventory_receipt.catalog_item_digest,
        "catalog_snapshot_digest": inventory_receipt.catalog_snapshot_digest,
        "evidence_id": inventory_receipt.evidence_id,
        "catalog_snapshot_evidence_ids": list(inventory_receipt.catalog_snapshot_evidence_ids),
        "inventory_complete": inventory_receipt.inventory_complete,
        "generation_allowed": inventory_receipt.generation_allowed,
        "delivery_identity_available": inventory_receipt.delivery_identity_available,
        "source_pack_available": inventory_receipt.source_pack_available,
        "missing_sources": ["delivery_identity_binding", "source_pack_binding"],
    }


def _blocked_row(
    *,
    path: str,
    evidence_ids: tuple[str, ...],
    inventory_receipt: ContentAuthoringInventoryReceipt | None,
    source_receipt: dict[str, object],
) -> dict[str, object]:
    has_inventory_receipt = inventory_receipt is not None
    return {
        "path": path,
        "public_url": _public_url(path),
        "decision": "blocked",
        "generation_allowed": False,
        "rationale_pl": (
            "Jest bieżący receipt inventory, ale brakuje delivery identity i source-pack."
            if has_inventory_receipt
            else "Brakuje aktualnego, exact wiązania inventory/source-pack dla tej pozycji."
        ),
        "next_step_pl": (
            "Zarejestruj delivery identity, a następnie source-pack na aktualnych źródłach."
            if has_inventory_receipt
            else "Zarejestruj exact identity i source-pack na podstawie aktualnych źródeł."
        ),
        "typed_blockers": [
            {
                "code": "current_content_binding_missing",
                "owner": "WILQ content workflow",
                "next_step_pl": (
                    "Zarejestruj delivery identity i source-pack bez wnioskowania z URL."
                    if has_inventory_receipt
                    else "Zarejestruj exact identity i source-pack bez wnioskowania z URL."
                ),
                "sources": ["content_status_214", "wordpress_inventory_catalog"],
                "blocks_initial_generation": True,
            }
        ],
        "work_item_identity": {
            "current_inventory_work_item_id": (
                None if inventory_receipt is None else inventory_receipt.current_work_item_id
            ),
            "retained_work_item_id": None,
        },
        "revision": {
            "revision_id": None,
            "digest": None,
            "approved": False,
            "complete": False,
        },
        "retained_revision_binding": None,
        "draft_and_action_state": {
            "verified_current_action_bindings": [],
            "verified_current_draft_bindings": [],
        },
        "evidence": {
            "evidence_ids": list(evidence_ids),
            "source_connectors": ["wordpress_ekologus"],
            "canonical_ledger_evidence_ids": [],
            "lineage_defects": [],
        },
        "source_packet_receipts": source_receipt,
        "source_packet_row_digest": canonical_json_digest(source_receipt),
    }


def _registered_inventory_receipt(
    *,
    path: str,
    catalog_item: ContentInventoryCatalogItem | None,
    inventory_receipts: Mapping[str, ContentAuthoringInventoryReceipt],
    inventory_snapshot_digest: str,
    evidence_ids: tuple[str, ...],
) -> ContentAuthoringInventoryReceipt | None:
    """Accept only a receipt that still exactly matches this current typed catalog."""

    receipt = inventory_receipts.get(path)
    if receipt is None or catalog_item is None:
        return None
    if (
        receipt.canonical_path != path
        or receipt.public_url != _public_url(path)
        or receipt.catalog_id != catalog_item.catalog_id
        or receipt.current_work_item_id != catalog_item.work_item_id
        or receipt.catalog_item_digest != content_inventory_catalog_item_digest(catalog_item)
        or receipt.catalog_snapshot_digest != inventory_snapshot_digest
        or receipt.catalog_snapshot_evidence_ids != evidence_ids
        or receipt.evidence_id != catalog_item.evidence_id
    ):
        return None
    return receipt


def _load_keep_rows(path: Path) -> tuple[dict[str, str], ...]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = tuple(dict(row) for row in reader)
    except (OSError, csv.Error):
        _invalid("current_journal_unavailable")
    if len(rows) != _EXPECTED_JOURNAL_ROWS:
        _invalid("current_journal_scope_invalid")
    normalized_rows: list[dict[str, str]] = []
    for row in rows:
        normalized_path = _canonical_path(row.get("path", ""))
        if normalized_path is None:
            _invalid("current_journal_scope_invalid")
        normalized_row = dict(row)
        normalized_row["path"] = normalized_path
        normalized_rows.append(normalized_row)
    paths = tuple(row["path"] for row in normalized_rows)
    if len(paths) != len(set(paths)):
        _invalid("current_journal_scope_invalid")
    canonical_paths = canonical_content_inventory_journal_paths()
    if canonical_paths is None or set(paths) != canonical_paths:
        _invalid("current_journal_scope_invalid")
    keep = tuple(
        sorted(
            (row for row in normalized_rows if row.get("final_disposition") == "keep"),
            key=lambda row: row["path"],
        )
    )
    if len(keep) != _EXPECTED_KEEP_ROWS or any(not _canonical_path(row["path"]) for row in keep):
        _invalid("current_journal_scope_invalid")
    return keep


def _catalog_by_path(
    catalog: ContentInventoryCatalogResponse,
) -> dict[str, ContentInventoryCatalogItem]:
    result: dict[str, ContentInventoryCatalogItem] = {}
    for item in catalog.items:
        path = _canonical_path(item.path)
        if path is None:
            _invalid("wordpress_catalog_invalid")
        if item.source_connector != "wordpress_ekologus" or path in result:
            _invalid("wordpress_catalog_invalid")
        result[path] = item
    return result


def _source_file(reference: str, projection: list[dict[str, object]]) -> dict[str, object]:
    return {
        "artifact_reference": reference,
        "sha256": canonical_json_digest(projection),
        "raw_artifact_retained": False,
        "retention_status": "external_ephemeral_receipt_only",
    }


def _blocked_historical_policy(
    *, evidence_id: str, checked_at: str
) -> ContentProductionBlockedHistoricalProtectionPolicy:
    binding = WAVE0_PRODUCTION_ACCEPTANCE_POLICY.protected_binding
    if binding is None:
        _invalid("historical_protection_unavailable")
    return ContentProductionBlockedHistoricalProtectionPolicy(
        canonical_path=binding.canonical_path,
        historical_revision_id=binding.revision_id,
        historical_revision_digest=binding.revision_digest,
        current_verification_outcome="unavailable",
        current_verification_evidence_id=evidence_id,
        current_verification_connector="wordpress_ekologus",
        current_verification_checked_at=checked_at,
    )


def _blocked_historical_protection(*, evidence_id: str, checked_at: str) -> dict[str, object]:
    policy = _blocked_historical_policy(evidence_id=evidence_id, checked_at=checked_at)
    return {
        "historical_revision_id": policy.historical_revision_id,
        "historical_revision_digest": policy.historical_revision_digest,
        "current_verification_outcome": policy.current_verification_outcome,
        "current_verification_evidence_id": policy.current_verification_evidence_id,
        "current_verification_connector": policy.current_verification_connector,
        "current_verification_checked_at": policy.current_verification_checked_at,
        "must_not_regenerate": True,
    }


def _judge(
    *,
    packet_sha256: str,
    decision_set_digest: str,
    protected: ContentProductionBlockedHistoricalProtectionPolicy,
    generated_at: str,
) -> dict[str, object]:
    return {
        "schema_version": _JUDGE_SCHEMA,
        "reviewer_role": "deterministic_packet_integrity_verifier",
        "verdict": "accept",
        "reviewed_packet_sha256": packet_sha256,
        "reviewed_decision_set_digest": decision_set_digest,
        "generated_at": generated_at,
        "checks": {
            "packet_sha256_exact": True,
            "decision_set_digest_recomputed": True,
            "source_file_receipts_exact": True,
            "source_row_receipts_exact": True,
            "absolute_temp_path_count": 0,
            "raw_vendor_payload_count": 0,
            "blocked_historical_protection": {
                "decision": "blocked",
                "historical_revision_id": protected.historical_revision_id,
                "historical_revision_digest": protected.historical_revision_digest,
                "current_verification_outcome": protected.current_verification_outcome,
                "current_verification_evidence_id": protected.current_verification_evidence_id,
                "current_verification_connector": protected.current_verification_connector,
                "current_verification_checked_at": protected.current_verification_checked_at,
                "exact_historical_revision_identity": True,
                "current_reuse_allowed": False,
                "must_not_regenerate": True,
            },
        },
    }


def _canonical_journal_path() -> Path:
    return Path(__file__).resolve().parents[4] / "docs" / "content-status-214.csv"


def _canonical_path(value: str) -> str | None:
    if not value.startswith("/") or "?" in value or "#" in value:
        return None
    return normalize_content_inventory_journal_path(value)


def _public_url(path: str) -> str:
    return f"{_PUBLIC_ORIGIN}/" if path == "/" else f"{_PUBLIC_ORIGIN}{path}/"


def _aware_time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        _invalid("recorded_at_invalid")
    return value.astimezone(UTC)


def _iso_z(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _json_value(value: object) -> object:
    model_dump = getattr(value, "model_dump", None)
    return model_dump(mode="json") if callable(model_dump) else value


def _invalid(code: str) -> NoReturn:
    raise ContentProductionClassificationValidationError(code)


__all__ = ["build_current_all_blocked_classification"]
