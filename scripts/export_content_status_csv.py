#!/usr/bin/env python3
"""Export one canonical, human-readable status row for every dev sitemap URL."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit


def _path(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    raw = parsed.path if parsed.scheme else value
    return raw.rstrip("/") or "/"


def _latest_payloads(connection: sqlite3.Connection, table: str, order: str) -> list[dict]:
    rows = connection.execute(
        f"SELECT payload_json FROM {table} ORDER BY {order}"  # noqa: S608
    ).fetchall()
    return [json.loads(row[0]) for row in rows]


def _content_kind(post_type: str | None, sitemaps: list[str]) -> str:
    if post_type == "post" or "post-sitemap.xml" in sitemaps:
        return "editorial"
    if post_type == "uslugi" or "uslugi-sitemap.xml" in sitemaps:
        return "service"
    if post_type == "page" or "page-sitemap.xml" in sitemaps:
        return "landing_or_hub"
    return "taxonomy_or_system"


def _content_state(disposition: str, revision: dict | None, review: dict | None) -> str:
    if disposition != "keep":
        return "not_required"
    if revision is None:
        return "not_written"
    decision = None if review is None else review.get("decision")
    if decision == "approved":
        return "written_approved"
    if decision in {"needs_changes", "rejected"}:
        return "written_needs_changes"
    return "written_unreviewed"


def _next_action(state: str, row: dict) -> str:
    if state == "not_required":
        return f"execute_{row['final_disposition']}_policy"
    if state == "not_written":
        return "prepare_evidence_bound_revision"
    if state == "written_needs_changes":
        return "create_child_revision_from_findings"
    if state == "written_unreviewed":
        return "run_independent_review"
    if row.get("target_mapping_status") != "confirmed":
        return "confirm_exact_target_mapping"
    if not row.get("dev_draft_ref"):
        return "prepare_dev_draft_action"
    return "verify_dev_draft_readback"


def export(args: argparse.Namespace) -> int:
    journal = json.loads(args.journal.read_text(encoding="utf-8"))
    sitemap = json.loads(args.sitemap.read_text(encoding="utf-8"))
    acf = json.loads(args.acf_inventory.read_text(encoding="utf-8"))
    sitemap_by_path = {
        row["path"]: row for row in sitemap["rows"] if row.get("dev_sitemaps")
    }
    object_by_path = {row["path"]: row for row in acf["objects"]}

    connection = sqlite3.connect(args.state_db)
    try:
        revisions = _latest_payloads(
            connection, "content_draft_revisions", "created_at DESC, revision_number DESC"
        )
        reviews = _latest_payloads(
            connection,
            "content_draft_revision_reviews",
            "created_at DESC, decision_number DESC",
        )
    finally:
        connection.close()

    revision_by_path: dict[str, dict] = {}
    for revision in revisions:
        canonical_path = _path(revision.get("final_canonical_url"))
        if canonical_path in sitemap_by_path and canonical_path not in revision_by_path:
            revision_by_path[canonical_path] = revision
    review_by_revision: dict[str, dict] = {}
    for review in reviews:
        revision_id = review.get("revision_id")
        if revision_id and revision_id not in review_by_revision:
            review_by_revision[revision_id] = review

    fields = [
        "path",
        "url",
        "wordpress_type",
        "content_kind",
        "final_disposition",
        "content_state",
        "revision_id",
        "revision_digest",
        "review_decision",
        "target_mapping_status",
        "delivery_status",
        "dev_draft_post_id",
        "robot_ready",
        "blocker_codes",
        "next_action",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in sorted(journal["urls"], key=lambda item: item["path"]):
            path = row["path"]
            revision = revision_by_path.get(path)
            review = None if revision is None else review_by_revision.get(revision["revision_id"])
            sitemap_row = sitemap_by_path[path]
            wp_object = object_by_path.get(path)
            post_type = None if wp_object is None else wp_object.get("type")
            state = _content_state(row["final_disposition"], revision, review)
            draft_ref = row.get("dev_draft_ref") or ""
            draft_post_id = draft_ref.rsplit("/", 1)[-1] if draft_ref else ""
            blockers = [
                code
                for code in row.get("blocker_codes", [])
                if not (revision is not None and code == "current_revision_missing")
            ]
            if state == "written_needs_changes" and "revision_needs_changes" not in blockers:
                blockers.append("revision_needs_changes")
            writer.writerow(
                {
                    "path": path,
                    "url": row["url"],
                    "wordpress_type": post_type or "",
                    "content_kind": _content_kind(post_type, sitemap_row["dev_sitemaps"]),
                    "final_disposition": row["final_disposition"],
                    "content_state": state,
                    "revision_id": "" if revision is None else revision["revision_id"],
                    "revision_digest": "" if revision is None else revision["content_digest"],
                    "review_decision": "" if review is None else review["decision"],
                    "target_mapping_status": row.get("target_mapping_status") or "",
                    "delivery_status": row.get("delivery_status") or "",
                    "dev_draft_post_id": draft_post_id,
                    "robot_ready": str(bool(row.get("robot_ready"))).lower(),
                    "blocker_codes": ";".join(sorted(blockers)),
                    "next_action": _next_action(state, row),
                }
            )
    return len(journal["urls"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--sitemap", type=Path, required=True)
    parser.add_argument("--acf-inventory", type=Path, required=True)
    parser.add_argument("--state-db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count = export(args)
    print(f"exported_rows={count}")


if __name__ == "__main__":
    main()
