#!/usr/bin/env python3
"""Read-only smoke for the current marketer-facing content operator seams."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from scripts.skill_smoke_harness import request_json


def as_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must be an object")
    return value


def as_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise SystemExit(f"{label} must be a list")
    return value


def validate_entry(
    entry: dict[str, Any], *, allow_empty: bool = False
) -> dict[str, Any] | None:
    if entry.get("response_type") != "content_workflow_entry":
        raise SystemExit("Workflow entry response_type mismatch")
    recommendations = [
        item
        for item in as_list(entry.get("recommendations"), "recommendations")
        if isinstance(item, dict)
    ]
    if not recommendations:
        if allow_empty:
            return None
        raise SystemExit("No evidence-bound recommendation is available")
    selected = recommendations[0]
    if not selected.get("work_item_id") or not selected.get("url"):
        raise SystemExit("Recommendation requires exact work_item_id and public URL")
    return selected


def read_entry(api_base: str, *, allow_empty: bool = False) -> dict[str, Any] | None:
    return validate_entry(
        as_dict(request_json(api_base, "GET", "/api/content/workflow-entry"), "workflow entry"),
        allow_empty=allow_empty,
    )


def validate_workspace(workspace: dict[str, Any], work_item_id: str) -> dict[str, Any]:
    if workspace.get("response_type") != "content_document_workspace":
        raise SystemExit("Document workspace response_type mismatch")
    if (
        workspace.get("work_item_id") != work_item_id
        or workspace.get("work_kind") != "refresh_existing"
    ):
        raise SystemExit("Document workspace identity mismatch")
    source = as_dict(workspace.get("source_snapshot"), "source snapshot")
    if source.get("status") not in {"available", "partial", "unavailable"}:
        raise SystemExit("Source snapshot has an unknown status")
    if source.get("status") == "available" and not source.get("evidence_ids"):
        raise SystemExit("Available source needs evidence IDs")
    document = as_dict(workspace.get("canonical_document"), "canonical document")
    document_statuses = {
        "not_created",
        "unreviewed",
        "needs_changes",
        "approved",
        "rejected",
        "deferred",
    }
    if document.get("status") not in document_statuses:
        raise SystemExit("Canonical document has an unknown status")
    if document.get("revision") is not None and (
        document.get("revision_id") != document["revision"].get("revision_id")
        or document.get("content_digest") != document["revision"].get("content_digest")
    ):
        raise SystemExit("Workspace revision is not exact-bound")
    return workspace


def validate_selected_workspace(response: dict[str, Any], work_item_id: str) -> dict[str, Any]:
    if response.get("response_type") != "content_selected_workspace":
        raise SystemExit("Selected workspace response_type mismatch")
    if response.get("work_item_id") != work_item_id:
        raise SystemExit("Selected workspace identity mismatch")
    if response.get("status") != "ready":
        raise SystemExit("Selected workspace is not ready for the exact work item")
    workspace = as_dict(response.get("workspace"), "selected workspace")
    return validate_workspace(workspace, work_item_id)


def read_workspace(api_base: str, work_item_id: str) -> dict[str, Any]:
    encoded = urllib.parse.quote(work_item_id, safe="")
    return validate_selected_workspace(
        as_dict(
            request_json(api_base, "GET", f"/api/content/work-items/{encoded}/selected-workspace"),
            "selected workspace",
        ),
        work_item_id,
    )


def validate_planning(status: dict[str, Any], work_item_id: str) -> dict[str, Any]:
    if status.get("work_item_id") != work_item_id:
        raise SystemExit("Planning status work_item_id mismatch")
    planning_statuses = {
        "not_generated",
        "generating",
        "created",
        "idempotent",
        "ready",
        "stale",
        "blocked",
        "failed",
    }
    if status.get("status") not in planning_statuses:
        raise SystemExit("Unknown planning status")
    if status.get("publish_ready") is not False:
        raise SystemExit("Planning must never be publish-ready")
    proposal = status.get("proposal")
    if status.get("status") in {"created", "idempotent", "ready"}:
        proposal = as_dict(proposal, "ready planning proposal")
        if not all(
            (
                proposal.get("proposal_id"),
                proposal.get("planning_digest"),
                proposal.get("planning_input_digest"),
            )
        ):
            raise SystemExit("Ready planning proposal lacks exact identity")
        if proposal.get("planning_input_digest") != status.get("planning_input_digest"):
            raise SystemExit("Planning input digest mismatch")
    return status


def read_planning(api_base: str, work_item_id: str) -> dict[str, Any]:
    encoded = urllib.parse.quote(work_item_id, safe="")
    return validate_planning(
        as_dict(
            request_json(api_base, "GET", f"/api/content/work-items/{encoded}/planning-proposals"),
            "planning status",
        ),
        work_item_id,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke current WILQ Content Operator read seams")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Accept an empty workflow entry only as a read-only no-evidence blocker.",
    )
    args = parser.parse_args()

    health = as_dict(request_json(args.api_base, "GET", "/api/health"), "health")
    if health.get("status") != "ok":
        raise SystemExit("WILQ API health is not ok")
    selected = read_entry(args.api_base, allow_empty=args.allow_empty)
    if selected is None:
        print(
            json.dumps(
                {
                    "skill": "wilq-content-operator",
                    "mode": "read_only",
                    "status": "blocked_no_evidence",
                    "publish_ready": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    work_item_id = str(selected["work_item_id"])
    workspace = read_workspace(args.api_base, work_item_id)
    planning = read_planning(args.api_base, work_item_id)

    print(
        json.dumps(
            {
                "skill": "wilq-content-operator",
                "mode": "read_only",
                "work_item_id": work_item_id,
                "source_status": workspace["source_snapshot"]["status"],
                "document_status": workspace["canonical_document"]["status"],
                "next_action": workspace["next_action"]["kind"],
                "planning_status": planning["status"],
                "proposal_id": (planning.get("proposal") or {}).get("proposal_id"),
                "publish_ready": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
