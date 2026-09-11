#!/usr/bin/env python3
"""Validate the canonical, read-only per-URL content status journal."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote, urlsplit

from wilq.content.workflow.target.target_mapping_persistence import (
    ContentTargetMappingPersistedRecord,
    ContentTargetMappingPersistenceError,
    decode_content_target_mapping_payload,
)

CSV_COLUMNS = (
    "record_role",
    "schema_version",
    "as_of",
    "source_authorities",
    "path",
    "url",
    "wordpress_type",
    "content_kind",
    "final_disposition",
    "content_state",
    "revision_scope",
    "revision_id",
    "revision_digest",
    "revision_review_decision",
    "semantic_review_status",
    "target_mapping_status",
    "delivery_status",
    "dev_execution_handoff_id",
    "dev_draft_post_id",
    "robot_ready",
    "blocker_codes",
    "next_action",
)
RECORD_ROLE = "current_state"
SCHEMA_VERSION = "content_status_214_v1"
SUPPORTED_SCHEMA_VERSIONS = frozenset({SCHEMA_VERSION})
AS_OF = "2026-09-10T12:00:00+02:00"
SOURCE_AUTHORITIES = (
    "WILQ SQLite;canonical content ledger;dev execution readback;dev sitemap inventory"
)
ROW_COUNT = 214
DEV_ORIGIN = "https://ekologus.dev.proudsite.pl"
HISTORICAL_JOURNAL_SIDECAR = "content-dev-state-journal-20260828.README.md"
HISTORICAL_JOURNAL_MARKERS = (
    "artifact_role=historical/reference",
    "generated_snapshot_date=2026-08-28",
    "superseded_current_state_authority=docs/content-status-214.csv",
    "does_not_supersede=WILQ typed runtime/CSV",
)
REACH_PATH = (
    "/obowiazki-przedsiebiorstw-w-zakresie-rozporzadzenia-reach-i-clp-"
    "ze-szczegolnym-uwzglednieniem-zmian-w-kartach-charakterystyki"
)
BLOCKER_CODES = frozenset(
    {
        "acf_mapping_blocked",
        "acf_mapping_observation_only",
        "blocked_acf_write_profile_unavailable",
        "blocked_human_mapping",
        "content_flag_guarantee",
        "content_flag_historic_date",
        "content_flag_product_scope",
        "cta_target_verification_required",
        "current_context_rebase_required",
        "current_revision_missing",
        "current_work_item_missing",
        "exact_base_source_context_missing",
        "existing_verified_draft_or_applied_action",
        "gsc_query_metric_context_absent",
        "historical_revision_not_reusable",
        "internal_link_verification_required",
        "no_exact_gsc_page_facts",
        "non_survivor_noindex",
        "non_survivor_redirect",
        "non_survivor_remove",
        "owner_review_required",
        "page_asset_owner_review_required",
        "planning_read_error",
        "product_sales_scope_review_required",
        "ready_for_human_mapping_all_components",
        "refresh_preparation_service_unavailable",
        "runtime_revision_historical_plan",
        "semantic_review_work_item_unavailable",
        "seo_meta_duplicate_split_required",
        "seo_meta_owner_mapping_missing",
        "service_binding_missing",
        "source_claim_review_required",
        "source_pack_work_item_binding_unverified",
        "target_mapping_confirmation_required",
        "target_mapping_observation_only",
        "target_unavailable",
        "typed_target_context_absent",
        "unknown_service_card",
        "update_only_readback_contract_missing",
        "work_item_identity_fork",
    }
)
NEXT_ACTIONS = frozenset(
    {
        "audit_current_legal_freshness_and_readback",
        "complete_approved_service_card_lineage_then_refresh_preparation",
        "configure_wordpress_dev_rest_and_retry_target_discovery",
        "configure_wordpress_dev_rest_then_create_action_and_readback",
        "confirm_exact_target_mapping",
        "execute_noindex_policy",
        "execute_redirect_policy",
        "execute_remove_policy",
        "fetch_full_public_source_and_resolve_service_binding",
        "prepare_evidence_bound_revision",
        "repair_current_work_item_identity",
        "repair_identity_and_prepare_current_service_bound_revision",
        "restore_gated_work_item_then_semantic_review_and_dev_readback",
    }
)
WORDPRESS_TYPES = frozenset({"", "page", "post", "uslugi"})
CONTENT_KINDS = frozenset({"editorial", "landing_or_hub", "service", "taxonomy_or_system"})
TYPE_KIND_PAIRS = frozenset(
    {
        ("page", "landing_or_hub"),
        ("post", "editorial"),
        ("uslugi", "service"),
        ("", "taxonomy_or_system"),
    }
)
TARGET_MAPPING_STATUSES = frozenset(
    {
        "",
        "acf_mapping_blocked",
        "blocked_acf_write_profile_unavailable",
        "blocked_human_mapping",
        "blocked_target_unavailable",
        "confirmed_the_content",
        "ready_for_human_mapping_all_components",
    }
)
DELIVERY_STATUSES = frozenset(
    {
        "acf_mapping_blocked",
        "audit_only_no_content",
        "blocked_acf_write_profile_unavailable",
        "blocked_human_mapping",
        "blocked_review_and_target_unavailable",
        "blocked_target_unavailable",
        "candidate_blocked",
        "dev_draft_verified",
        "ready_for_human_mapping_all_components",
    }
)
TARGET_DELIVERY_PAIRS = frozenset(
    {
        ("", "audit_only_no_content"),
        ("", "candidate_blocked"),
        ("acf_mapping_blocked", "acf_mapping_blocked"),
        ("blocked_acf_write_profile_unavailable", "blocked_acf_write_profile_unavailable"),
        ("blocked_human_mapping", "blocked_human_mapping"),
        ("blocked_target_unavailable", "blocked_target_unavailable"),
        ("confirmed_the_content", "blocked_review_and_target_unavailable"),
        ("confirmed_the_content", "blocked_target_unavailable"),
        ("confirmed_the_content", "dev_draft_verified"),
        ("ready_for_human_mapping_all_components", "ready_for_human_mapping_all_components"),
    }
)
HISTORICAL_KEEP_BLOCKERS = frozenset(
    {
        "historical_revision_not_reusable",
        "runtime_revision_historical_plan",
        "current_revision_missing",
        "current_work_item_missing",
    }
)
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_REVISION = re.compile(r"^content_revision_[0-9a-f]{32}$")


@dataclass(frozen=True, slots=True)
class DbRevision:
    work_item_id: str
    revision_number: int
    digest: str
    path: str
    payload_identity_matches: bool
    draft_package_id: str | None
    draft_package_digest: str | None
    planning_digest: str | None
    final_canonical_url: str | None


@dataclass(frozen=True, slots=True)
class DbReview:
    decision_id: str
    work_item_id: str
    digest: str
    decision: str
    decision_number: int
    payload_identity_matches: bool


@dataclass(frozen=True, slots=True)
class DbExecution:
    work_item_id: str
    handoff_id: str
    revision_id: str
    digest: str
    post_id: str | None
    status: str
    mode: str
    external_write_attempted: bool
    expected_content_digest: str | None
    observed_content_digest: str | None
    expected_title_digest: str | None
    observed_title_digest: str | None
    expected_acf_digest: str | None
    observed_acf_digest: str | None
    authoring_mode: str | None
    binding_work_item_id: str | None
    binding_revision_id: str | None
    binding_digest: str | None
    binding_handoff_id: str | None
    binding_draft_package_id: str | None
    binding_draft_package_digest: str | None
    binding_planning_digest: str | None
    binding_approval_decision_id: str | None
    binding_final_canonical_url: str | None
    live_write_enabled: bool
    live_adapter_configured: bool
    publish_allowed: bool | None
    destructive_update_allowed: bool | None
    endpoint: str | None


@dataclass(frozen=True, slots=True)
class DbSemanticReview:
    work_item_id: str
    digest: str
    criteria_version: str
    status: str
    finding_count: int
    payload_identity_matches: bool


@dataclass(frozen=True, slots=True)
class DbMapping:
    work_item_id: str
    revision_id: str
    digest: str
    target_path: str
    delivery_scope: str


def load_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def validate_rows(
    columns: list[str],
    rows: list[dict[str, str]],
    *,
    expected_count: int = ROW_COUNT,
) -> list[str]:
    errors = _shape_errors(columns, rows)
    if errors:
        return errors
    if len(rows) != expected_count:
        errors.append(f"expected {expected_count} rows, found {len(rows)}")
    urls = [row.get("url", "") for row in rows]
    if len(urls) != len(set(urls)):
        errors.append("URLs must be unique")
    paths = [row.get("path", "") for row in rows]
    if len(paths) != len(set(paths)):
        errors.append("paths must be unique")
    for row in rows:
        errors.extend(_row_errors(row))
    errors.extend(_journal_errors(rows, expected_count=expected_count))
    return errors


def validate_csv(csv_path: Path, state_db: Path | None = None) -> list[str]:
    columns, rows = load_rows(csv_path)
    errors = validate_rows(columns, rows)
    errors.extend(validate_historical_journal_sidecar(csv_path.parent / HISTORICAL_JOURNAL_SIDECAR))
    if errors or state_db is None:
        return errors
    return validate_state_db(rows, state_db)


def validate_historical_journal_sidecar(path: Path) -> list[str]:
    if not path.is_file():
        return ["historical journal sidecar is missing"]
    text = path.read_text(encoding="utf-8")
    return [
        "historical journal sidecar is missing required marker"
        for marker in HISTORICAL_JOURNAL_MARKERS
        if marker not in text
    ]


def validate_state_db(rows: Iterable[dict[str, str]], state_db: Path) -> list[str]:
    state_db_uri = f"file:{quote(str(state_db.resolve()), safe='/')}?mode=ro"
    with sqlite3.connect(state_db_uri, uri=True) as connection:
        revisions = _db_revisions(connection)
        reviews = _db_reviews(connection)
        semantic = _db_semantic_reviews(connection)
        executions = _db_executions(connection)
        mappings = _db_mappings(connection)
    errors: list[str] = []
    for row in rows:
        scope = row["revision_scope"]
        if scope == "none":
            continue
        revision = revisions.get(row["revision_id"])
        if revision is None or revision.digest != row["revision_digest"]:
            errors.append(f"{row['path']}: revision binding does not match state DB")
            continue
        if not revision.payload_identity_matches:
            errors.append(f"{row['path']}: revision payload does not match state DB")
        if revision.path != row["path"]:
            errors.append(f"{row['path']}: revision URL path does not match state DB")
        errors.extend(_review_errors(row, revision, reviews))
        if scope == "current":
            errors.extend(_current_revision_errors(row, revision, revisions, reviews, semantic))
        if row.get("target_mapping_status", "") == "confirmed_the_content":
            errors.extend(_mapping_errors(row, revision, mappings))
        if row["delivery_status"] == "dev_draft_verified":
            errors.extend(_execution_errors(row, revision, reviews, executions))
    return errors


def _column_errors(columns: list[str]) -> list[str]:
    return [] if tuple(columns) == CSV_COLUMNS else ["CSV columns do not match contract"]


def _shape_errors(columns: list[str], rows: list[dict[str, str]]) -> list[str]:
    errors = _column_errors(columns)
    if errors:
        return errors
    expected = set(CSV_COLUMNS)
    for index, row in enumerate(rows, start=2):
        if set(row) != expected or any(value is None for value in row.values()):
            errors.append(f"row {index}: CSV row does not match contract columns")
    schema_versions = {row.get("schema_version", "") for row in rows}
    unsupported = schema_versions.difference(SUPPORTED_SCHEMA_VERSIONS)
    if unsupported:
        errors.append("CSV uses an unsupported schema version")
    return errors


def _row_errors(row: dict[str, str]) -> list[str]:
    path = row.get("path", "<missing path>")
    errors: list[str] = []
    for field, expected in (
        ("record_role", RECORD_ROLE),
        ("schema_version", SCHEMA_VERSION),
        ("as_of", AS_OF),
        ("source_authorities", SOURCE_AUTHORITIES),
    ):
        if row.get(field) != expected:
            errors.append(f"{path}: {field} does not match journal metadata")
    try:
        datetime.fromisoformat(row["as_of"])
    except (KeyError, ValueError):
        errors.append(f"{path}: as_of is not ISO-8601")
    blockers = _blockers(row.get("blocker_codes", ""))
    if blockers != sorted(blockers):
        errors.append(f"{path}: blocker codes are not sorted")
    unknown = set(blockers).difference(BLOCKER_CODES)
    if unknown:
        errors.append(f"{path}: unregistered blocker code")
    if row.get("next_action") not in NEXT_ACTIONS:
        errors.append(f"{path}: unregistered next action")
    errors.extend(_url_errors(row))
    errors.extend(_vocabulary_errors(row))
    errors.extend(_state_errors(row, blockers))
    return errors


def _url_errors(row: dict[str, str]) -> list[str]:
    path = row["path"]
    try:
        parsed = urlsplit(row["url"])
        port = parsed.port
    except (TypeError, ValueError):
        return [f"{path}: URL has an invalid port"]
    if (
        parsed.scheme != "https"
        or parsed.hostname != "ekologus.dev.proudsite.pl"
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or parsed.fragment
    ):
        return [f"{path}: URL must use the canonical dev origin without URL extras"]
    if path != _path(path) or _path(row["url"]) != path:
        return [f"{path}: URL path does not match canonical row path"]
    return []


def _vocabulary_errors(row: dict[str, str]) -> list[str]:
    path = row["path"]
    wordpress_type = row["wordpress_type"]
    content_kind = row["content_kind"]
    errors: list[str] = []
    if wordpress_type not in WORDPRESS_TYPES:
        errors.append(f"{path}: invalid wordpress type")
    if content_kind not in CONTENT_KINDS:
        errors.append(f"{path}: invalid content kind")
    if not _type_kind_allowed(row):
        errors.append(f"{path}: incompatible wordpress type and content kind")
    if row["target_mapping_status"] not in TARGET_MAPPING_STATUSES:
        errors.append(f"{path}: invalid target mapping status")
    if row["delivery_status"] not in DELIVERY_STATUSES:
        errors.append(f"{path}: invalid delivery status")
    if (row["target_mapping_status"], row["delivery_status"]) not in TARGET_DELIVERY_PAIRS:
        errors.append(f"{path}: incompatible target mapping and delivery status")
    return errors


def _type_kind_allowed(row: dict[str, str]) -> bool:
    wordpress_type = row["wordpress_type"]
    content_kind = row["content_kind"]
    return (wordpress_type, content_kind) in TYPE_KIND_PAIRS or (
        wordpress_type == ""
        and content_kind == "service"
        and row["final_disposition"] != "keep"
    )


def _state_errors(row: dict[str, str], blockers: list[str]) -> list[str]:
    path = row["path"]
    disposition = row["final_disposition"]
    state = row["content_state"]
    scope = row["revision_scope"]
    semantic = row["semantic_review_status"]
    review = row["revision_review_decision"]
    errors: list[str] = []
    if disposition not in {"keep", "noindex", "redirect", "remove"}:
        errors.append(f"{path}: invalid final disposition")
    if state not in {"not_required", "not_written", "written_approved"}:
        errors.append(f"{path}: invalid content state")
    if scope not in {"current", "historical", "none"}:
        errors.append(f"{path}: invalid revision scope")
    if scope == "none" and row["target_mapping_status"] in {
        "confirmed_the_content",
        "ready_for_human_mapping_all_components",
    }:
        errors.append(f"{path}: target mapping status requires a bound revision")
    if semantic not in {"zero_findings", "unavailable", "not_generated", "not_required"}:
        errors.append(f"{path}: invalid semantic review status")
    if review not in {"", "approved", "needs_changes", "rejected"}:
        errors.append(f"{path}: invalid revision review decision")
    if row["robot_ready"] not in {"true", "false"}:
        errors.append(f"{path}: robot_ready must be true or false")
    errors.extend(_revision_scope_errors(row))
    if disposition != "keep":
        if state != "not_required" or semantic != "not_required":
            errors.append(f"{path}: non-keep row must be not_required")
        if row["next_action"] != f"execute_{disposition}_policy":
            errors.append(f"{path}: non-keep row has the wrong next action")
    if state == "not_written" and semantic != "not_generated":
        errors.append(f"{path}: not-written row must have not-generated semantic status")
    if state == "written_approved":
        if scope != "current" or review != "approved":
            errors.append(f"{path}: approved row must bind the current approved revision")
        if semantic not in {"zero_findings", "unavailable"}:
            errors.append(f"{path}: approved row has an invalid semantic status")
    errors.extend(_reach_errors(row, blockers))
    errors.extend(_historical_errors(row, blockers))
    errors.extend(_execution_contract_errors(row))
    return errors


def _historical_errors(row: dict[str, str], blockers: list[str]) -> list[str]:
    if row["revision_scope"] != "historical":
        return []
    if row["final_disposition"] == "keep":
        if not set(blockers).intersection(HISTORICAL_KEEP_BLOCKERS):
            return [f"{row['path']}: historical keep row lacks a stale-revision blocker"]
        return []
    expected = f"non_survivor_{row['final_disposition']}"
    if expected not in blockers:
        return [f"{row['path']}: historical non-keep row lacks its survivor blocker"]
    return []


def _revision_scope_errors(row: dict[str, str]) -> list[str]:
    has_revision = bool(row["revision_id"] or row["revision_digest"])
    if row["revision_scope"] == "none":
        return [] if not has_revision and not row["revision_review_decision"] else [
            f"{row['path']}: none scope cannot carry revision fields"
        ]
    if not (_REVISION.fullmatch(row["revision_id"]) and _DIGEST.fullmatch(row["revision_digest"])):
        return [f"{row['path']}: revision scope requires exact revision ID and digest"]
    if row["revision_scope"] == "historical" and row["content_state"] == "written_approved":
        return [f"{row['path']}: approved revision cannot be historical"]
    return []


def _reach_errors(row: dict[str, str], blockers: list[str]) -> list[str]:
    if row["path"] != REACH_PATH:
        return []
    if row["semantic_review_status"] != "unavailable":
        return ["REACH row must record semantic review as unavailable"]
    if "semantic_review_work_item_unavailable" not in blockers:
        return ["REACH row must carry the semantic-review availability blocker"]
    return []


def _execution_contract_errors(row: dict[str, str]) -> list[str]:
    dev_verified = row["delivery_status"] == "dev_draft_verified"
    has_receipt = bool(row["dev_execution_handoff_id"] or row["dev_draft_post_id"])
    if dev_verified and (
        row["revision_scope"] != "current"
        or row["content_state"] != "written_approved"
        or row["revision_review_decision"] != "approved"
        or not row["dev_execution_handoff_id"]
        or not row["dev_draft_post_id"]
    ):
        return [f"{row['path']}: verified dev draft requires exact current execution receipt"]
    if not dev_verified and has_receipt:
        return [f"{row['path']}: only verified dev draft rows may carry execution receipt"]
    return []


def _journal_errors(rows: list[dict[str, str]], *, expected_count: int) -> list[str]:
    if len(rows) != expected_count:
        return []
    approved_keep = [
        row
        for row in rows
        if row["final_disposition"] == "keep" and row["content_state"] == "written_approved"
    ]
    zero_findings = [
        row for row in approved_keep if row["semantic_review_status"] == "zero_findings"
    ]
    dev_rows = [row for row in rows if row["delivery_status"] == "dev_draft_verified"]
    errors: list[str] = []
    expected_dispositions = {"keep": 57, "noindex": 87, "redirect": 46, "remove": 24}
    disposition_counts = Counter(row["final_disposition"] for row in rows)
    if disposition_counts != expected_dispositions:
        errors.append("expected final disposition counts 57/87/46/24")
    if any(row["robot_ready"] == "true" for row in rows):
        errors.append("robot-ready rows are not allowed before the final delivery gate")
    if len(approved_keep) != 18 or len(zero_findings) != 17:
        errors.append("expected 18 approved keep rows with 17 zero-findings semantic reviews")
    if len(dev_rows) != 7:
        errors.append("expected seven verified dev-draft rows")
    return errors


def _blockers(value: str) -> list[str]:
    return [] if not value else value.split(";")


def _db_revisions(connection: sqlite3.Connection) -> dict[str, DbRevision]:
    rows = connection.execute(
        "SELECT revision_id, work_item_id, revision_number, content_digest, payload_json "
        "FROM content_draft_revisions"
    )
    result: dict[str, DbRevision] = {}
    for revision_id, work_item_id, number, digest, payload_json in rows:
        try:
            payload = json.loads(payload_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        final_url = payload.get("final_canonical_url")
        draft_package_id = payload.get("draft_package_id")
        draft_package_digest = _optional_digest(payload.get("draft_package_digest"))
        planning_digest = _optional_digest(payload.get("planning_digest"))
        result[revision_id] = DbRevision(
            work_item_id=work_item_id,
            revision_number=number,
            digest=digest,
            path=_path(final_url),
            payload_identity_matches=(
                payload.get("revision_id") == revision_id
                and payload.get("work_item_id") == work_item_id
                and payload.get("revision_number") == number
                and payload.get("content_digest") == digest
                and payload.get("schema_version")
                in {"wilq_content_draft_revision_v1", "wilq_content_draft_revision_v2"}
                and payload.get("publish_ready") is False
                and isinstance(draft_package_id, str)
                and bool(draft_package_id)
                and draft_package_digest is not None
            ),
            draft_package_id=draft_package_id if isinstance(draft_package_id, str) else None,
            draft_package_digest=draft_package_digest,
            planning_digest=planning_digest,
            final_canonical_url=final_url if isinstance(final_url, str) else None,
        )
    return result


def _db_reviews(connection: sqlite3.Connection) -> dict[str, tuple[DbReview, ...]]:
    rows = connection.execute(
        "SELECT decision_id, work_item_id, revision_id, revision_digest, decision_number, "
        "decision, payload_json FROM content_draft_revision_reviews "
        "ORDER BY revision_id, decision_number, decision_id"
    )
    result: dict[str, list[DbReview]] = {}
    for (
        decision_id,
        work_item_id,
        revision_id,
        digest,
        decision_number,
        decision,
        payload_json,
    ) in rows:
        try:
            payload = json.loads(payload_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = None
        if not isinstance(payload, dict):
            payload = {}
        result.setdefault(revision_id, []).append(
            DbReview(
                decision_id=decision_id,
                work_item_id=work_item_id,
                digest=digest,
                decision=decision,
                decision_number=decision_number,
                payload_identity_matches=(
                    payload.get("decision_id") == decision_id
                    and payload.get("work_item_id") == work_item_id
                    and payload.get("revision_id") == revision_id
                    and payload.get("revision_digest") == digest
                    and payload.get("decision_number") == decision_number
                    and payload.get("decision") == decision
                ),
            )
        )
    return {revision_id: tuple(records) for revision_id, records in result.items()}


def _db_semantic_reviews(
    connection: sqlite3.Connection,
) -> dict[str, tuple[DbSemanticReview, ...]]:
    rows = connection.execute(
        "SELECT revision_id, work_item_id, revision_digest, criteria_version, payload_json "
        "FROM content_semantic_reviews ORDER BY revision_id, created_at, review_id"
    )
    result: dict[str, list[DbSemanticReview]] = {}
    for revision_id, work_item_id, digest, criteria_version, payload_json in rows:
        try:
            payload = json.loads(payload_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = None
        if not isinstance(payload, dict):
            payload = {}
        findings = payload.get("findings", [])
        finding_count = len(findings) if isinstance(findings, list) else -1
        result.setdefault(revision_id, []).append(
            DbSemanticReview(
                work_item_id=work_item_id,
                digest=digest,
                criteria_version=criteria_version,
                status=str(payload.get("status", "")),
                finding_count=finding_count,
                payload_identity_matches=(
                    payload.get("work_item_id") == work_item_id
                    and payload.get("revision_id") == revision_id
                    and payload.get("revision_digest") == digest
                    and payload.get("criteria_version") == criteria_version
                ),
            )
        )
    return {revision_id: tuple(records) for revision_id, records in result.items()}


def _db_executions(
    connection: sqlite3.Connection,
) -> dict[tuple[str, str], tuple[DbExecution, ...]]:
    rows = connection.execute(
        "SELECT work_item_id, handoff_id, revision_id, revision_digest, payload_json "
        "FROM content_wordpress_draft_execution_history"
    )
    result: dict[tuple[str, str], list[DbExecution]] = {}
    for work_item_id, handoff_id, revision_id, digest, payload_json in rows:
        try:
            payload = json.loads(payload_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = None
        if not isinstance(payload, dict):
            payload = {}
        post_id = payload.get("wordpress_post_id")
        boundary = payload.get("boundary")
        if not isinstance(boundary, dict):
            boundary = {}
        binding = payload.get("revision_binding")
        if not isinstance(binding, dict):
            binding = {}
        result.setdefault((work_item_id, handoff_id), []).append(
            DbExecution(
            work_item_id=work_item_id,
            handoff_id=handoff_id,
            revision_id=revision_id,
            digest=digest,
            post_id=post_id if isinstance(post_id, str) else None,
            status=str(payload.get("status", "")),
            mode=str(payload.get("mode", "")),
            external_write_attempted=payload.get("external_write_attempted") is True,
            expected_content_digest=_optional_digest(payload.get("expected_content_digest")),
            observed_content_digest=_optional_digest(payload.get("observed_content_digest")),
            expected_title_digest=_optional_digest(payload.get("expected_title_digest")),
            observed_title_digest=_optional_digest(payload.get("observed_title_digest")),
            expected_acf_digest=_optional_digest(payload.get("expected_acf_digest")),
            observed_acf_digest=_optional_digest(payload.get("observed_acf_digest")),
            authoring_mode=(
                payload.get("payload", {}).get("authoring_mode")
                if isinstance(payload.get("payload"), dict)
                else None
            ),
            binding_work_item_id=(
                binding.get("work_item_id")
                if isinstance(binding.get("work_item_id"), str)
                else None
            ),
            binding_revision_id=(
                binding.get("revision_id") if isinstance(binding.get("revision_id"), str) else None
            ),
            binding_digest=_optional_digest(binding.get("content_digest")),
            binding_handoff_id=(
                binding.get("handoff_id") if isinstance(binding.get("handoff_id"), str) else None
            ),
            binding_draft_package_id=(
                binding.get("draft_package_id")
                if isinstance(binding.get("draft_package_id"), str)
                else None
            ),
            binding_draft_package_digest=_optional_digest(binding.get("draft_package_digest")),
            binding_planning_digest=_optional_digest(binding.get("planning_digest")),
            binding_approval_decision_id=(
                binding.get("approval_decision_id")
                if isinstance(binding.get("approval_decision_id"), str)
                else None
            ),
            binding_final_canonical_url=(
                binding.get("final_canonical_url")
                if isinstance(binding.get("final_canonical_url"), str)
                else None
            ),
            live_write_enabled=boundary.get("live_write_enabled") is True,
            live_adapter_configured=boundary.get("live_adapter_configured") is True,
            publish_allowed=(
                boundary.get("publish_allowed")
                if type(boundary.get("publish_allowed")) is bool
                else None
            ),
            destructive_update_allowed=(
                boundary.get("destructive_update_allowed")
                if type(boundary.get("destructive_update_allowed")) is bool
                else None
            ),
            endpoint=payload.get("endpoint") if isinstance(payload.get("endpoint"), str) else None,
            )
        )
    return {key: tuple(records) for key, records in result.items()}


def _db_mappings(connection: sqlite3.Connection) -> set[DbMapping]:
    try:
        rows = connection.execute(
            "SELECT confirmation_id, work_item_id, revision_id, revision_digest, "
            "target_contract_digest, binding_digest, confirmation_number, "
            "confirmation_digest, created_at, payload_json "
            "FROM content_target_mapping_confirmations "
            "ORDER BY work_item_id, revision_id, revision_digest, "
            "created_at DESC, confirmation_id DESC"
        )
    except sqlite3.OperationalError:
        return set()
    result: set[DbMapping] = set()
    latest_keys: set[tuple[object, object, object]] = set()
    for (
        confirmation_id,
        work_item_id,
        revision_id,
        digest,
        sql_target_digest,
        sql_binding_digest,
        sql_confirmation_number,
        sql_confirmation_digest,
        sql_created_at,
        payload_json,
    ) in rows:
        mapping_key = (work_item_id, revision_id, digest)
        if mapping_key in latest_keys:
            continue
        latest_keys.add(mapping_key)
        try:
            decoded = decode_content_target_mapping_payload(
                payload_json,
                sql_scalars={
                    "confirmation_id": confirmation_id,
                    "work_item_id": work_item_id,
                    "revision_id": revision_id,
                    "revision_digest": digest,
                    "target_contract_digest": sql_target_digest,
                    "binding_digest": sql_binding_digest,
                    "confirmation_number": sql_confirmation_number,
                    "confirmation_digest": sql_confirmation_digest,
                    "created_at": sql_created_at,
                },
            )
            if not isinstance(decoded, ContentTargetMappingPersistedRecord):
                continue
            target = decoded.preview_snapshot.target
            if target is None or not _is_canonical_dev_url(target.target_contract.url):
                continue
        except (
            ContentTargetMappingPersistenceError,
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            continue
        result.add(
            DbMapping(
                work_item_id=work_item_id,
                revision_id=revision_id,
                digest=digest,
                target_path=_path(target.target_contract.url),
                delivery_scope=decoded.confirmation.delivery_scope,
            )
        )
    return result


def _current_revision_errors(
    row: dict[str, str],
    revision: DbRevision,
    revisions: dict[str, DbRevision],
    reviews: dict[str, tuple[DbReview, ...]],
    semantic: dict[str, tuple[DbSemanticReview, ...]],
) -> list[str]:
    errors: list[str] = []
    latest_number = max(
        candidate.revision_number
        for candidate in revisions.values()
        if candidate.work_item_id == revision.work_item_id
    )
    if revision.revision_number != latest_number:
        errors.append(f"{row['path']}: current revision is not latest in state DB")
    status = row["semantic_review_status"]
    semantic_records_all = tuple(
        record
        for record in semantic.get(row["revision_id"], ())
        if record.work_item_id == revision.work_item_id
        and record.digest == revision.digest
        and record.criteria_version == "wilq_semantic_content_review_v1"
    )
    semantic_records = tuple(
        record for record in semantic_records_all if record.payload_identity_matches
    )
    if status == "zero_findings" and (
        len(semantic_records_all) != 1
        or len(semantic_records) != 1
        or semantic_records[0].status != "reviewable"
        or semantic_records[0].finding_count != 0
    ):
        errors.append(f"{row['path']}: semantic zero-findings status does not match state DB")
    if status == "unavailable" and semantic_records_all:
        errors.append(f"{row['path']}: unavailable semantic review exists in state DB")
    return errors


def _review_errors(
    row: dict[str, str],
    revision: DbRevision,
    reviews: dict[str, tuple[DbReview, ...]],
) -> list[str]:
    expected = row["revision_review_decision"]
    if not expected:
        return []
    exact = tuple(
        review
        for review in reviews.get(row["revision_id"], ())
        if review.work_item_id == revision.work_item_id
        and review.digest == revision.digest
    )
    latest_number = max((review.decision_number for review in exact), default=0)
    latest = tuple(review for review in exact if review.decision_number == latest_number)
    if (
        not latest
        or len(latest) != 1
        or not latest[0].payload_identity_matches
        or latest[0].decision != expected
    ):
        return [f"{row['path']}: revision approval does not match state DB"]
    return []


def _execution_errors(
    row: dict[str, str],
    revision: DbRevision,
    reviews: dict[str, tuple[DbReview, ...]],
    executions: dict[tuple[str, str], tuple[DbExecution, ...]],
) -> list[str]:
    execution_records = executions.get(
        (revision.work_item_id, row["dev_execution_handoff_id"]), ()
    )
    if len(execution_records) != 1:
        return [f"{row['path']}: dev execution receipt does not match state DB"]
    execution = execution_records[0]
    exact_reviews = tuple(
        review
        for review in reviews.get(row["revision_id"], ())
        if review.work_item_id == revision.work_item_id
        and review.digest == revision.digest
    )
    latest_number = max((review.decision_number for review in exact_reviews), default=0)
    latest_reviews = tuple(
        review for review in exact_reviews if review.decision_number == latest_number
    )
    latest_review = (
        latest_reviews[0]
        if (
            len(latest_reviews) == 1
            and latest_reviews[0].payload_identity_matches
            and latest_reviews[0].decision == "approved"
        )
        else None
    )
    if execution is None or (
        execution.work_item_id != revision.work_item_id
        or execution.handoff_id != row["dev_execution_handoff_id"]
        or execution.revision_id != row["revision_id"]
        or execution.digest != row["revision_digest"]
        or execution.post_id != row["dev_draft_post_id"]
    ):
        return [f"{row['path']}: dev execution receipt does not match state DB"]
    if (
        execution.status != "created"
        or execution.mode != "live"
        or not execution.external_write_attempted
        or execution.binding_work_item_id != revision.work_item_id
        or execution.binding_revision_id != row["revision_id"]
        or execution.binding_digest != row["revision_digest"]
        or execution.binding_handoff_id != row["dev_execution_handoff_id"]
        or revision.draft_package_id is None
        or revision.draft_package_digest is None
        or revision.planning_digest is None
        or execution.binding_draft_package_id is None
        or execution.binding_draft_package_digest is None
        or execution.binding_planning_digest is None
        or execution.binding_draft_package_id != revision.draft_package_id
        or execution.binding_draft_package_digest != revision.draft_package_digest
        or execution.binding_planning_digest != revision.planning_digest
        or latest_review is None
        or execution.binding_approval_decision_id != latest_review.decision_id
        or execution.binding_final_canonical_url != revision.final_canonical_url
        or execution.endpoint
        != {"post": "posts", "page": "pages", "uslugi": "uslugi"}.get(
            row.get("wordpress_type", "post")
        )
        or not execution.live_write_enabled
        or not execution.live_adapter_configured
        or execution.publish_allowed is not False
        or execution.destructive_update_allowed is not False
        or execution.expected_content_digest is None
        or execution.expected_content_digest != execution.observed_content_digest
        or execution.expected_title_digest is None
        or execution.expected_title_digest != execution.observed_title_digest
        or (
            execution.expected_acf_digest is not None
            and execution.expected_acf_digest != execution.observed_acf_digest
        )
        or (
            execution.expected_acf_digest is None
            and execution.observed_acf_digest is not None
        )
        or (
            execution.authoring_mode == "acf_flexible_content"
            and (
                execution.expected_acf_digest is None
                or execution.expected_acf_digest != execution.observed_acf_digest
            )
        )
        or (
            row.get("wordpress_type") == "uslugi"
            or row.get("content_kind") == "service"
        )
        and (
            execution.authoring_mode != "acf_flexible_content"
            or execution.expected_acf_digest is None
            or execution.expected_acf_digest != execution.observed_acf_digest
        )
    ):
        return [f"{row['path']}: dev execution is not an exact verified draft creation"]
    return []


def _mapping_errors(
    row: dict[str, str],
    revision: DbRevision,
    mappings: set[DbMapping],
) -> list[str]:
    if any(
        mapping.work_item_id == revision.work_item_id
        and mapping.revision_id == row["revision_id"]
        and mapping.digest == row["revision_digest"]
        and mapping.target_path == row["path"]
        and mapping.delivery_scope == "full_document"
        for mapping in mappings
    ):
        return []
    return [f"{row['path']}: confirmed content mapping does not match state DB"]


def _optional_digest(value: object) -> str | None:
    return value if isinstance(value, str) and _DIGEST.fullmatch(value) else None


def _canonical_digest(value: object) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _is_canonical_dev_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError):
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname == "ekologus.dev.proudsite.pl"
        and parsed.username is None
        and parsed.password is None
        and port is None
        and not parsed.query
        and not parsed.fragment
    )


def _path(value: object) -> str:
    if not isinstance(value, str):
        return ""
    try:
        parsed = urlsplit(value)
    except (TypeError, ValueError):
        return ""
    return parsed.path.rstrip("/") or "/"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=Path("docs/content-status-214.csv"))
    parser.add_argument("--state-db", type=Path)
    args = parser.parse_args()
    columns, rows = load_rows(args.csv)
    errors = validate_csv(args.csv, args.state_db)
    if errors:
        for error in errors:
            print(f"invalid: {error}")
        return 1
    checked = "with_state_db" if args.state_db is not None else "without_state_db"
    print(f"content_status_214_valid rows={len(rows)} {checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
