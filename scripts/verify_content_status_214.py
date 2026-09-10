#!/usr/bin/env python3
"""Validate the canonical, read-only per-URL content status journal."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

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
        ("", "dev_draft_verified"),
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


@dataclass(frozen=True, slots=True)
class DbExecution:
    revision_id: str
    digest: str
    post_id: str | None


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
    with sqlite3.connect(f"file:{state_db}?mode=ro", uri=True) as connection:
        revisions = _db_revisions(connection)
        reviews = _db_reviews(connection)
        semantic = _db_semantic_reviews(connection)
        executions = _db_executions(connection)
    errors: list[str] = []
    for row in rows:
        scope = row["revision_scope"]
        if scope == "none":
            continue
        revision = revisions.get(row["revision_id"])
        if revision is None or revision.digest != row["revision_digest"]:
            errors.append(f"{row['path']}: revision binding does not match state DB")
            continue
        if revision.path != row["path"]:
            errors.append(f"{row['path']}: revision URL path does not match state DB")
        if (
            row["revision_review_decision"]
            and reviews.get(row["revision_id"]) != row["revision_review_decision"]
        ):
            errors.append(f"{row['path']}: revision approval does not match state DB")
        if scope == "current":
            errors.extend(_current_revision_errors(row, revision, revisions, reviews, semantic))
        if row["delivery_status"] == "dev_draft_verified":
            errors.extend(_execution_errors(row, executions))
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
    parsed = urlsplit(row["url"])
    try:
        port = parsed.port
    except ValueError:
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
    if semantic not in {"zero_findings", "unavailable", "not_generated", "not_required"}:
        errors.append(f"{path}: invalid semantic review status")
    if review not in {"", "approved", "needs_changes", "rejected"}:
        errors.append(f"{path}: invalid revision review decision")
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
    if len(approved_keep) != 18 or len(zero_findings) != 17:
        errors.append("expected 18 approved keep rows with 17 zero-findings semantic reviews")
    if len(dev_rows) != 8:
        errors.append("expected eight verified dev-draft rows")
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
        payload = json.loads(payload_json)
        result[revision_id] = DbRevision(
            work_item_id=work_item_id,
            revision_number=number,
            digest=digest,
            path=_path(payload.get("final_canonical_url")),
        )
    return result


def _db_reviews(connection: sqlite3.Connection) -> dict[str, str]:
    rows = connection.execute(
        "SELECT revision_id, decision, decision_number FROM content_draft_revision_reviews "
        "ORDER BY revision_id, decision_number"
    )
    return {revision_id: decision for revision_id, decision, _number in rows}


def _db_semantic_reviews(connection: sqlite3.Connection) -> dict[str, tuple[str, int]]:
    rows = connection.execute("SELECT revision_id, payload_json FROM content_semantic_reviews")
    result: dict[str, tuple[str, int]] = {}
    for revision_id, payload_json in rows:
        payload = json.loads(payload_json)
        findings = payload.get("findings", [])
        high_count = sum(
            1
            for finding in findings
            if isinstance(finding, dict) and finding.get("severity") == "high"
        )
        result[revision_id] = (str(payload.get("status", "")), high_count)
    return result


def _db_executions(connection: sqlite3.Connection) -> dict[str, DbExecution]:
    rows = connection.execute(
        "SELECT handoff_id, revision_id, revision_digest, payload_json "
        "FROM content_wordpress_draft_execution_history"
    )
    result: dict[str, DbExecution] = {}
    for handoff_id, revision_id, digest, payload_json in rows:
        payload = json.loads(payload_json)
        post_id = payload.get("wordpress_post_id")
        result[handoff_id] = DbExecution(
            revision_id=revision_id,
            digest=digest,
            post_id=post_id if isinstance(post_id, str) else None,
        )
    return result


def _current_revision_errors(
    row: dict[str, str],
    revision: DbRevision,
    revisions: dict[str, DbRevision],
    reviews: dict[str, str],
    semantic: dict[str, tuple[str, int]],
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
    semantic_record = semantic.get(row["revision_id"])
    if status == "zero_findings" and semantic_record != ("reviewable", 0):
        errors.append(f"{row['path']}: semantic zero-findings status does not match state DB")
    if status == "unavailable" and semantic_record is not None:
        errors.append(f"{row['path']}: unavailable semantic review exists in state DB")
    return errors


def _execution_errors(row: dict[str, str], executions: dict[str, DbExecution]) -> list[str]:
    execution = executions.get(row["dev_execution_handoff_id"])
    if execution is None or (
        execution.revision_id != row["revision_id"]
        or execution.digest != row["revision_digest"]
        or execution.post_id != row["dev_draft_post_id"]
    ):
        return [f"{row['path']}: dev execution receipt does not match state DB"]
    return []


def _path(value: object) -> str:
    if not isinstance(value, str):
        return ""
    parsed = urlsplit(value)
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
