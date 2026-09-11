"""Read-only preflight that prevents duplicate content generation on dev."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    parsed = urlparse(value.strip())
    return parsed.path.rstrip("/") or "/"


def _binding_key(binding: object) -> tuple[str, str, str] | None:
    if not isinstance(binding, dict):
        return None
    work_item = binding.get("work_item_id")
    revision = binding.get("revision_id")
    if not isinstance(work_item, str) or not isinstance(revision, str):
        return None
    return work_item, revision, _path(binding.get("final_canonical_url"))


def _load_recovery(journal_path: Path, source: object) -> list[dict[str, Any]]:
    if not isinstance(source, dict):
        return []
    path = source.get("path")
    if not isinstance(path, str) or not path.strip():
        return []
    recovery_path = Path(path)
    if not recovery_path.is_absolute():
        recovery_path = journal_path.parent / recovery_path
    if not recovery_path.is_file():
        return []
    payload = json.loads(recovery_path.read_text(encoding="utf-8"))
    rows = payload.get("rows") if isinstance(payload, dict) else None
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _binding_matches_row(
    key: tuple[str, str, str],
    *,
    work_item_id: object,
    revision_id: object,
    path: str,
) -> bool:
    key_work_item, key_revision, key_path = key
    if isinstance(work_item_id, str) and work_item_id:
        if key_work_item != work_item_id:
            return False
    elif not key_path or key_path != path:
        return False
    if isinstance(revision_id, str) and revision_id and key_revision != revision_id:
        return False
    return not key_path or key_path == path


def _applied_bindings(
    audits: list[dict[str, Any]], recovery: list[dict[str, Any]]
) -> dict[tuple[str, str, str], list[str]]:
    applied_by_key: dict[tuple[str, str, str], list[str]] = {}
    for audit in [*audits, *recovery]:
        if audit.get("status") not in {None, "applied"} and "action_payload_binding" not in audit:
            continue
        for binding in (audit.get("binding"), audit.get("action_payload_binding")):
            key = _binding_key(binding)
            action_id = audit.get("action_id") or audit.get("id")
            if key is not None and isinstance(action_id, str):
                applied_by_key.setdefault(key, []).append(action_id)
    return applied_by_key


def _draft_refs_by_path(drafts: list[dict[str, Any]]) -> dict[str, list[str]]:
    refs: dict[str, list[str]] = {}
    for draft in drafts:
        path = _path(draft.get("path"))
        post_id = draft.get("post_id")
        if path and isinstance(post_id, str):
            refs.setdefault(path, []).append(f"posts/{post_id}")
    return refs


def _applied_actions_for_row(
    row: dict[str, Any],
    *,
    path: str,
    applied_by_key: dict[tuple[str, str, str], list[str]],
) -> list[str]:
    return sorted(
        {
            action_id
            for key, action_ids in applied_by_key.items()
            if _binding_matches_row(
                key,
                work_item_id=row.get("planning_probe_work_item_id"),
                revision_id=row.get("current_revision_id"),
                path=path,
            )
            for action_id in action_ids
        }
    )


def _decision_for_row(
    row: dict[str, Any],
    *,
    draft_refs_by_path: dict[str, list[str]],
    applied_by_key: dict[tuple[str, str, str], list[str]],
) -> dict[str, Any]:
    path = _path(row.get("path") or row.get("url"))
    draft_refs = sorted(
        set(filter(None, [row.get("dev_draft_ref"), *draft_refs_by_path.get(path, [])]))
    )
    revision_id = row.get("current_revision_id")
    applied = _applied_actions_for_row(row, path=path, applied_by_key=applied_by_key)
    if row.get("final_disposition") != "keep":
        state, allowed, reason = "audit_only", False, "Non-keep URL is not a generation target."
    elif draft_refs:
        state, allowed, reason = (
            "existing_dev_draft",
            False,
            "An existing dev draft is already indexed.",
        )
    elif revision_id:
        state, allowed, reason = (
            "existing_current_revision",
            False,
            "A current revision is already indexed.",
        )
    elif applied:
        state, allowed, reason = (
            "existing_action_binding",
            False,
            "An applied action binding already exists.",
        )
    elif row.get("blocker_codes") or not row.get("planning_probe_work_item_id"):
        state, allowed, reason = (
            "blocked",
            False,
            "The row has a typed blocker or no exact work-item.",
        )
    else:
        state, allowed, reason = (
            "eligible_candidate",
            True,
            "No existing draft, revision or applied action is indexed.",
        )
    return {
        "path": path,
        "generation_allowed": allowed,
        "state": state,
        "reason": reason,
        "existing_draft_refs": draft_refs,
        "current_revision_id": revision_id,
        "applied_action_ids": applied,
        "blocker_codes": row.get("blocker_codes", []),
    }


def evaluate_journal(journal_path: Path) -> dict[str, Any]:
    payload = json.loads(journal_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "dev_content_state_journal_v1":
        raise ValueError("Unsupported dev state journal schema.")
    url_rows = [row for row in payload.get("urls", []) if isinstance(row, dict)]
    drafts = [row for row in payload.get("drafts", []) if isinstance(row, dict)]
    audits = [row for row in payload.get("mutation_audits", []) if isinstance(row, dict)]
    recovery = _load_recovery(
        journal_path,
        (payload.get("sources") or {}).get("action_binding_recovery"),
    )
    applied_by_key = _applied_bindings(audits, recovery)
    drafts_by_path = _draft_refs_by_path(drafts)
    decisions = [
        _decision_for_row(
            row,
            draft_refs_by_path=drafts_by_path,
            applied_by_key=applied_by_key,
        )
        for row in url_rows
    ]
    counts: dict[str, int] = {}
    for decision in decisions:
        state = decision["state"]
        counts[state] = counts.get(state, 0) + 1
    return {
        "schema_version": "dev_content_state_preflight_v1",
        "journal": str(journal_path),
        "read_only": True,
        "generation_performed": False,
        "counts": counts,
        "decisions": decisions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(evaluate_journal(args.journal), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
