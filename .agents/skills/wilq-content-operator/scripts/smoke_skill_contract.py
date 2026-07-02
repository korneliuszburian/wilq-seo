#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import date
from typing import Any

SKILL_NAME = "wilq-content-operator"
DEV_HOST = "ekologus.dev.proudsite.pl"
MIN_SMOKE_ITEMS = 1
MIN_UAT_ITEMS = 3


def request_json(
    api_base: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    timeout: int = 180,
) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"HTTP {exc.code} from {path}: {message}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach WILQ API at {api_base}: {exc.reason}") from exc


def assert_false_everywhere(value: Any, forbidden_key: str, context: str) -> None:
    if isinstance(value, dict):
        if value.get(forbidden_key) is True:
            raise SystemExit(f"{context} must not expose {forbidden_key}=true")
        for child in value.values():
            assert_false_everywhere(child, forbidden_key, context)
    elif isinstance(value, list):
        for child in value:
            assert_false_everywhere(child, forbidden_key, context)


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must be an object")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise SystemExit(f"{label} must be a list")
    return value


def first_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    for candidate in candidates:
        if candidate.get("recommended_mode") != "block":
            return candidate
    return candidates[0]


def validate_queue(queue: dict[str, Any], *, min_candidates: int) -> dict[str, Any]:
    candidates = [
        candidate
        for candidate in require_list(queue.get("candidates"), "content queue candidates")
        if isinstance(candidate, dict)
    ]
    if len(candidates) < min_candidates:
        raise SystemExit(
            f"{SKILL_NAME} needs at least {min_candidates} content candidates for this smoke; "
            f"got {len(candidates)}"
        )
    if queue.get("candidate_count") != len(candidates):
        raise SystemExit("Content queue candidate_count must match candidates length")

    for candidate in candidates:
        work_item_id = candidate.get("work_item_id")
        if not work_item_id:
            raise SystemExit("Every content queue candidate must expose work_item_id")
        blockers = candidate.get("blockers") or []
        if not candidate.get("evidence_ids") and not blockers:
            raise SystemExit(f"{work_item_id}: candidate needs evidence IDs or typed blockers")
        if not candidate.get("source_connectors") and not blockers:
            raise SystemExit(f"{work_item_id}: candidate needs source connectors or typed blockers")
        final_url = candidate.get("final_canonical_url") or candidate.get("intended_final_url")
        if final_url and DEV_HOST in final_url:
            raise SystemExit(f"{work_item_id}: dev URL cannot be final canonical")
        if candidate.get("preview_url") and candidate.get("preview_url") == final_url:
            raise SystemExit(f"{work_item_id}: preview URL cannot equal final canonical")
        if not candidate.get("safe_next_step"):
            raise SystemExit(f"{work_item_id}: candidate needs safe_next_step")
        if candidate.get("recommended_mode") != "block" and not candidate.get("action_ids"):
            raise SystemExit(f"{work_item_id}: actionable candidate needs action_ids")

    return first_candidate(candidates)


def validate_selected_actions(api_base: str, selected: dict[str, Any]) -> list[str]:
    action_ids = [str(action_id) for action_id in selected.get("action_ids") or []]
    if selected.get("recommended_mode") == "block":
        return []
    if not action_ids:
        raise SystemExit("Selected non-block content candidate needs action_ids")
    validated_action_ids: list[str] = []
    for action_id in action_ids:
        validation = require_dict(
            request_json(api_base, "POST", f"/api/actions/{action_id}/validate"),
            f"action validation response for {action_id}",
        )
        if validation.get("valid") is not True:
            raise SystemExit(f"Selected action {action_id} did not validate")
        validated_action_ids.append(action_id)
    return validated_action_ids


def validate_snapshot(snapshot: dict[str, Any], work_item_id: str) -> dict[str, Any]:
    for section in (
        "preflight",
        "sales_brief",
        "draft_package",
        "structured_generation",
        "human_review",
        "wordpress_handoff",
        "measurement_window",
        "operator_steps",
    ):
        if section not in snapshot:
            raise SystemExit(f"Snapshot missing {section}")
    item = require_dict(snapshot["preflight"].get("item"), "snapshot preflight item")
    if item.get("id") != work_item_id:
        raise SystemExit("Selected snapshot work_item_id mismatch")
    if not item.get("evidence_ids"):
        raise SystemExit("Selected snapshot item must expose evidence IDs")
    if not item.get("source_connectors"):
        raise SystemExit("Selected snapshot item must expose source connectors")
    if item.get("final_canonical_url") and DEV_HOST in item["final_canonical_url"]:
        raise SystemExit("Selected snapshot cannot use dev URL as final canonical")

    assert_false_everywhere(snapshot, "publish_ready", "content workflow snapshot")
    assert_false_everywhere(snapshot, "publish_allowed", "content workflow snapshot")
    assert_false_everywhere(snapshot, "destructive_update_allowed", "content workflow snapshot")
    return item


def validate_enrichment(api_base: str, work_item_id: str) -> dict[str, Any]:
    enrichment = require_dict(
        request_json(api_base, "GET", f"/api/content/work-items/{work_item_id}/enrichment"),
        "content enrichment response",
    )
    if enrichment.get("work_item_id") not in {None, work_item_id}:
        raise SystemExit("Enrichment work_item_id mismatch")
    assert_false_everywhere(enrichment, "publish_ready", "content enrichment")
    return enrichment


def validate_knowledge_cards(api_base: str) -> dict[str, Any]:
    cards = require_dict(
        request_json(api_base, "GET", "/api/content/knowledge-cards"),
        "content knowledge cards response",
    )
    card_items = cards.get("cards") or cards.get("knowledge_cards") or []
    if not isinstance(card_items, list) or not card_items:
        raise SystemExit("Content operator needs typed content knowledge cards")
    return cards


def compact_brief_items(brief: dict[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    sections = brief.get("sections")
    if not isinstance(sections, list):
        return items
    for section in sections:
        if not isinstance(section, dict):
            continue
        for raw_item in section.get("items") or []:
            if not isinstance(raw_item, dict):
                continue
            items.append(
                {
                    "id": raw_item.get("id"),
                    "title": raw_item.get("title"),
                    "kind": raw_item.get("kind"),
                    "source_connectors": raw_item.get("source_connectors") or [],
                    "evidence_ids": raw_item.get("evidence_ids") or [],
                }
            )
            if len(items) >= limit:
                return items
    return items


def validate_wordpress_boundary(api_base: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    handoff = (
        snapshot.get("wordpress_handoff", {})
        .get("handoff_result", {})
        .get("handoff")
    )
    draft_package = (
        snapshot.get("draft_package", {})
        .get("draft_package_result", {})
        .get("draft_package")
    )
    execution = require_dict(
        request_json(
            api_base,
            "POST",
            "/api/content/work-items/wordpress-draft-execution",
            {"handoff": handoff, "draft_package": draft_package, "mode": "dry_run"},
        ),
        "wordpress draft execution response",
    )
    assert_false_everywhere(execution, "publish_allowed", "wordpress draft execution")
    assert_false_everywhere(execution, "destructive_update_allowed", "wordpress draft execution")
    assert_false_everywhere(execution, "external_write_attempted", "wordpress draft execution")
    return execution


def validate_wordpress_authoring_preview(
    api_base: str,
    selected: dict[str, Any],
    *,
    evidence_ids: list[str],
) -> dict[str, Any]:
    work_item_id = str(selected.get("work_item_id") or "content_work_item_preview")
    title = str(selected.get("title") or selected.get("topic") or "WILQ content preview")
    final_url = str(
        selected.get("final_canonical_url")
        or selected.get("intended_final_url")
        or "https://www.ekologus.pl/"
    )
    if DEV_HOST in final_url:
        final_url = "https://www.ekologus.pl/"
    clean_evidence_ids = [str(evidence_id) for evidence_id in evidence_ids if evidence_id]
    if not clean_evidence_ids:
        clean_evidence_ids = [f"ev_{work_item_id}_authoring_preview"]
    primary_evidence_ids = clean_evidence_ids[:2]
    draft_package = {
        "id": f"draft_package_{work_item_id}_authoring_preview",
        "work_item_id": work_item_id,
        "brief_id": f"sales_brief_{work_item_id}",
        "claim_ledger_id": f"claim_ledger_{work_item_id}",
        "title": title,
        "sections": [
            {
                "heading": str(selected.get("topic") or title),
                "purpose": str(
                    selected.get("safe_next_step")
                    or "Przygotuj review-only sekcję do szkicu WordPress."
                ),
                "evidence_ids": primary_evidence_ids,
                "draft_notes": [
                    "WordPress authoring preview pozostaje dry-run i nie zapisuje zmian."
                ],
            }
        ],
        "section_to_evidence_map": [
            {
                "section_heading": str(selected.get("topic") or title),
                "evidence_ids": primary_evidence_ids,
            }
        ],
        "claims_used": [],
        "publish_ready": False,
    }
    handoff = {
        "id": f"wordpress_draft_handoff_{work_item_id}_authoring_preview",
        "work_item_id": work_item_id,
        "draft_package_id": draft_package["id"],
        "human_review_id": f"human_review_{work_item_id}",
        "audit_id": f"audit_{work_item_id}",
        "title": title,
        "final_canonical_url": final_url,
        "evidence_ids": clean_evidence_ids,
        "publish_allowed": False,
        "destructive_update_allowed": False,
    }
    response = require_dict(
        request_json(
            api_base,
            "POST",
            "/api/content/work-items/wordpress-authoring-payload-preview",
            {"handoff": handoff, "draft_package": draft_package},
        ),
        "wordpress authoring payload preview response",
    )
    preview = require_dict(response.get("preview_result"), "wordpress authoring preview")
    assert_false_everywhere(preview, "publish_allowed", "wordpress authoring preview")
    assert_false_everywhere(preview, "destructive_update_allowed", "wordpress authoring preview")
    assert_false_everywhere(preview, "external_write_attempted", "wordpress authoring preview")
    row_candidates = _authoring_row_candidates(preview)
    if preview.get("status") == "ready" and not row_candidates:
        raise SystemExit("WordPress authoring preview needs at least one ACF row candidate")
    first_candidate = row_candidates[0] if row_candidates else {}
    return {
        "status": preview.get("status"),
        "layout": preview.get("layout"),
        "mode": preview.get("mode"),
        "row_candidate_count": len(row_candidates),
        "first_row_label": first_candidate.get("row_label"),
        "first_row_review_status": first_candidate.get("review_status"),
        "first_row_fields": [
            field.get("field_name")
            for field in first_candidate.get("field_values", [])
            if isinstance(field, dict) and field.get("field_name")
        ],
        "evidence_ids": first_candidate.get("evidence_ids") or [],
        "publish_allowed": preview.get("publish_allowed"),
        "destructive_update_allowed": preview.get("destructive_update_allowed"),
        "external_write_attempted": preview.get("external_write_attempted"),
    }


def _authoring_row_candidates(preview: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for section in preview.get("sections") or []:
        if isinstance(section, dict):
            candidates.extend(_field_row_candidates(section.get("field_previews") or []))
    return candidates


def _field_row_candidates(fields: list[Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        candidates.extend(
            candidate
            for candidate in field.get("row_candidates") or []
            if isinstance(candidate, dict)
        )
        candidates.extend(_field_row_candidates(field.get("nested_values") or []))
    return candidates


def validate_measurement_outcome(api_base: str, snapshot: dict[str, Any]) -> dict[str, Any] | None:
    window = (
        snapshot.get("measurement_window", {})
        .get("measurement_window_result", {})
        .get("window")
    )
    if not isinstance(window, dict):
        return None
    outcome = require_dict(
        request_json(
            api_base,
            "POST",
            "/api/content/work-items/measurement-outcome",
            {
                "window": window,
                "observed_metrics": [],
                "as_of": date.today().isoformat(),
            },
        ),
        "measurement outcome response",
    )
    status = require_dict(outcome.get("outcome"), "measurement outcome").get("status")
    if status == "measured_success":
        raise SystemExit("Measurement outcome cannot claim success without observed evidence")
    return outcome


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Smoke test {SKILL_NAME} WILQ API contract")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--require-uat-queue",
        action="store_true",
        help="Require the 3+ item queue expected for a full Wilku UAT packet.",
    )
    args = parser.parse_args()

    health = require_dict(request_json(args.api_base, "GET", "/api/health"), "health response")
    if health.get("status") != "ok":
        raise SystemExit(f"WILQ API health is not ok: {health}")

    brief = request_json(args.api_base, "GET", "/api/marketing/brief")
    brief = require_dict(brief, "marketing brief response")
    brief_items = compact_brief_items(brief)

    queue = require_dict(
        request_json(args.api_base, "GET", "/api/content/work-items/queue"),
        "content queue response",
    )
    selected = validate_queue(
        queue,
        min_candidates=MIN_UAT_ITEMS if args.require_uat_queue else MIN_SMOKE_ITEMS,
    )
    work_item_id = str(selected["work_item_id"])
    selected_validated_action_ids = validate_selected_actions(args.api_base, selected)
    knowledge_cards = validate_knowledge_cards(args.api_base)
    authoring_preview = validate_wordpress_authoring_preview(
        args.api_base,
        selected,
        evidence_ids=queue.get("evidence_ids") or selected.get("evidence_ids") or [],
    )
    if (
        queue.get("queue_status") == "blocked"
        or int(queue.get("actionable_candidate_count") or 0) == 0
        or selected.get("recommended_mode") == "block"
    ):
        summary = {
            "skill": SKILL_NAME,
            "queue_status": queue.get("queue_status"),
            "candidate_count": queue.get("candidate_count"),
            "actionable_candidate_count": queue.get("actionable_candidate_count"),
            "uat_queue_ready": int(queue.get("candidate_count") or 0) >= MIN_UAT_ITEMS,
            "uat_min_candidate_count": MIN_UAT_ITEMS,
            "selected_work_item_id": work_item_id,
            "selected_mode": selected.get("recommended_mode"),
            "selected_action_ids": selected.get("action_ids") or [],
            "selected_validated_action_ids": selected_validated_action_ids,
            "workflow_blocked": True,
            "blocker_count": len(queue.get("blockers") or []),
            "evidence_ids": queue.get("evidence_ids") or [],
            "source_connectors": queue.get("source_connectors") or [],
            "knowledge_card_count": len(knowledge_cards.get("cards") or []),
            "safe_next_step": selected.get("safe_next_step"),
            "brief_items": brief_items,
            "wordpress_authoring_preview": authoring_preview,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    snapshot = require_dict(
        request_json(args.api_base, "GET", f"/api/content/work-items/{work_item_id}/snapshot"),
        "content workflow snapshot response",
    )
    item = validate_snapshot(snapshot, work_item_id)
    enrichment = validate_enrichment(args.api_base, work_item_id)
    execution = validate_wordpress_boundary(args.api_base, snapshot)
    outcome = validate_measurement_outcome(args.api_base, snapshot)

    summary = {
        "skill": SKILL_NAME,
        "queue_status": queue.get("queue_status"),
        "candidate_count": queue.get("candidate_count"),
        "uat_queue_ready": int(queue.get("candidate_count") or 0) >= MIN_UAT_ITEMS,
        "uat_min_candidate_count": MIN_UAT_ITEMS,
        "selected_work_item_id": work_item_id,
        "selected_mode": selected.get("recommended_mode"),
        "selected_action_ids": selected.get("action_ids") or [],
        "selected_validated_action_ids": selected_validated_action_ids,
        "evidence_ids": item.get("evidence_ids", []),
        "source_connectors": item.get("source_connectors", []),
        "enrichment_keys": sorted(enrichment.keys()),
        "knowledge_card_count": len(knowledge_cards.get("cards") or []),
        "wordpress_execution_status": execution.get("execution_result", {}).get("status"),
        "measurement_outcome_status": None
        if outcome is None
        else outcome.get("outcome", {}).get("status"),
        "publish_blocked": True,
        "destructive_update_blocked": True,
        "success_claim_blocked_until_measurement": True,
        "wordpress_authoring_preview": authoring_preview,
        "brief_items": brief_items,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
