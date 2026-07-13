from __future__ import annotations

from typing import Any


def validate_localo_diagnostics_contract(
    pack: dict[str, Any], action_id: str
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    set[str],
    dict[str, Any],
    list[dict[str, Any]],
]:
    diagnostics = pack.get("localo_diagnostics") or {}
    access_probe = diagnostics.get("access_probe") or {}
    decision_queue = diagnostics.get("decision_queue") or []
    decision_ids = {decision.get("id") for decision in decision_queue}
    if access_probe.get("status") not in {"access_ready", "access_blocked", "unknown"}:
        raise SystemExit(f"Unexpected Localo access status: {access_probe.get('status')}")
    if not diagnostics.get("evidence_ids"):
        raise SystemExit("Localo diagnostics must expose evidence IDs")
    if not decision_queue:
        raise SystemExit("Localo diagnostics must expose a decision queue")
    summary = diagnostics.get("operator_summary") or {}
    if not isinstance(summary, dict):
        raise SystemExit("Localo diagnostics must expose operator_summary")
    if summary.get("review_card_label") != "Karta review Localo":
        raise SystemExit("Localo operator summary must expose review card label")
    required_fields = (
        "review_decision_after_review",
        "review_question_for_operator",
        "review_next_safe_click",
    )
    missing = [field for field in required_fields if not str(summary.get(field) or "").strip()]
    if missing:
        raise SystemExit("Localo operator summary missing review fields: " + ", ".join(missing))
    actions = [
        action
        for action in (pack.get("active_action_objects") or [])
        if action.get("id") == action_id
    ]
    return diagnostics, access_probe, decision_queue, decision_ids, summary, actions


def validate_localo_refresh_contract(
    pack: dict[str, Any],
    diagnostics: dict[str, Any],
    access_probe: dict[str, Any],
    decision_ids: set[str],
    localo_actions: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str, str, dict[str, Any], str | None, list[str]]:
    diagnostics_run = diagnostics.get("latest_refresh")
    if isinstance(diagnostics_run, dict) and diagnostics_run.get("connector_id") == "localo":
        latest_run, source = diagnostics_run, "localo_diagnostics.latest_refresh"
    else:
        runs = [
            run
            for run in pack.get("connector_refresh_runs", [])
            if run.get("connector_id") == "localo"
        ]
        latest_run, source = (
            (runs[0], "context_pack.connector_refresh_runs") if runs else (None, "missing")
        )
    if latest_run is None:
        if access_probe.get("status") != "unknown":
            raise SystemExit("Missing Localo refresh run is allowed only for unknown access status")
        if "localo_fix_access_before_visibility_review" not in decision_ids:
            raise SystemExit("Missing Localo refresh run must expose the access review decision")
        if "localo_block_visibility_claims_without_read_contract" not in decision_ids:
            raise SystemExit("Missing Localo refresh run must keep visibility claims blocked")
        source, status = "clean_runtime_without_refresh", "missing"
    else:
        status = str(latest_run.get("status") or "")
    if status not in {"blocked", "completed", "missing"}:
        raise SystemExit(f"Unexpected Localo refresh status: {status}")
    raw_summary = latest_run.get("metric_summary") if latest_run else {}
    summary = raw_summary if isinstance(raw_summary, dict) else {}
    if summary.get("api") != "localo_mcp_oauth_probe" and status != "missing":
        raise SystemExit("Latest Localo run is not the MCP OAuth probe")
    preview_contract: str | None = None
    preview_metric_names: list[str] = []
    if status == "blocked":
        if summary.get("access_token_present") != 0 or summary.get("mcp_initialize_status") != 401:
            raise SystemExit("Blocked Localo OAuth probe must report token absent and MCP 401")
        if "localo_fix_access_before_visibility_review" not in decision_ids:
            raise SystemExit("Blocked Localo diagnostics must expose the access repair decision")
    if status == "completed":
        preview_contract, preview_metric_names = _validate_completed_run(
            diagnostics, access_probe, decision_ids, localo_actions, summary
        )
    return latest_run, source, status, summary, preview_contract, preview_metric_names


def _validate_completed_run(
    diagnostics: dict[str, Any],
    access_probe: dict[str, Any],
    decision_ids: set[str],
    localo_actions: list[dict[str, Any]],
    summary: dict[str, Any],
) -> tuple[str | None, list[str]]:
    if summary.get("mcp_initialize_status") != 200:
        raise SystemExit("Completed Localo OAuth probe must report MCP initialize 200")
    if access_probe.get("status") != "access_ready":
        raise SystemExit("Completed Localo OAuth probe must produce access_ready diagnostics")
    decision_queue = diagnostics.get("decision_queue") or []
    metric_facts = [
        fact for decision in decision_queue for fact in decision.get("metric_facts", [])
    ]
    if not summary.get("localo_read_contract_count"):
        if "localo_access_ready_wait_for_visibility_facts" not in decision_ids:
            raise SystemExit("Access-ready Localo diagnostics must wait for visibility facts")
        if "localo_block_visibility_claims_without_read_contract" not in decision_ids:
            raise SystemExit("Access-ready Localo diagnostics must block visibility claims")
        if metric_facts:
            raise SystemExit(
                "Localo OAuth probe is not ranking/GBP evidence and must not create metric facts"
            )
        return None, []
    return _validate_value_facts(decision_queue, decision_ids, localo_actions, metric_facts)


def _validate_value_facts(
    decision_queue: list[dict[str, Any]],
    decision_ids: set[str],
    localo_actions: list[dict[str, Any]],
    metric_facts: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    if "localo_review_visibility_facts" not in decision_ids:
        raise SystemExit("Localo value facts must expose a visibility review decision")
    if "localo_block_visibility_claims_without_read_contract" not in decision_ids:
        raise SystemExit("Partial Localo value facts must keep blocked-claim decision")
    review = next(
        (item for item in decision_queue if item.get("id") == "localo_review_visibility_facts"), {}
    )
    if not {"place_inventory", "local_rankings", "reviews"}.issubset(
        set(review.get("allowed_evidence") or [])
    ):
        raise SystemExit("Localo value review is missing aggregate evidence contracts")
    allowed = set(review.get("allowed_evidence") or [])
    missing = set(review.get("missing_read_contracts") or [])
    _validate_missing_contracts(allowed, missing)
    blocked = set(review.get("blocked_claims") or [])
    _validate_blocked_claims(allowed, blocked)
    if not metric_facts or not localo_actions:
        raise SystemExit("Localo value review must expose aggregate facts and review action")
    preview = (localo_actions[0].get("action_plan") or {}).get("preview_items") or []
    if not preview:
        raise SystemExit("Localo review action must expose preview_items")
    first = preview[0]
    if (
        first.get("apply_status_label") != "zablokowane do sprawdzenia"
        or first.get("write_status_label") != "bez zapisu automatycznego"
    ):
        raise SystemExit(
            "Localo review preview must keep apply_allowed=false and api_mutation_ready=false"
        )
    tiles = first.get("metric_tiles") or {}
    if not isinstance(tiles, dict) or not tiles:
        raise SystemExit("Localo review change preview must include metric_snapshot")
    names = [fact.get("name") for fact in metric_facts if fact.get("name") == "[REDACTED]"]
    if names:
        raise SystemExit("Localo metric fact names must not be redacted")
    return "action_plan.preview_items", sorted(str(name) for name in tiles)


def _validate_missing_contracts(allowed: set[str], missing: set[str]) -> None:
    unsupported = {"local_tasks"}
    if "gbp_visibility" not in allowed:
        unsupported.add("gbp_visibility")
    if "competitor_visibility" not in allowed:
        unsupported.add("competitor_visibility")
    if not unsupported.issubset(missing):
        raise SystemExit("Localo value review must keep unsupported contracts missing")


def _validate_blocked_claims(allowed: set[str], blocked: set[str]) -> None:
    unsupported = {"poprawa widoczności lokalnej"}
    if "gbp_visibility" not in allowed:
        unsupported.add("wyniki profilu firmy w Google")
    if "competitor_visibility" not in allowed:
        unsupported.add("widoczność konkurencji")
    if not unsupported.issubset(blocked):
        raise SystemExit("Localo value review must block unsupported marketing claims")
