from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.actions.metric_utils import unique_values
from wilq.schemas import ActionConfirmRequest, ActionMode, ActionObject, AuditEvent

AdsTargetBlockers = Callable[[ActionConfirmRequest], list[str]]
HumanConfirmation = Callable[[list[str]], bool]
MutationAdapter = Callable[[ActionObject], str | None]
StringList = Callable[[Any], list[str]]


def action_preview_blockers(
    action: ActionObject,
    preview_items: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if not preview_items:
        blockers.append("payload_preview_missing")
    if action.payload.get("destructive") is True:
        blockers.append("destructive_actions_blocked")
    blockers.extend(action.review_gate.apply_blockers)
    return unique_values(blockers)


def action_confirmation_blockers(
    action: ActionObject,
    request: ActionConfirmRequest,
    latest_preview: AuditEvent | None,
    *,
    ads_target_blockers: AdsTargetBlockers,
) -> list[str]:
    if action.payload.get("action_type") == "confirm_ads_target_guardrails":
        return ads_target_blockers(request)

    blockers: list[str] = []
    if not request.preview_acknowledged:
        blockers.append("preview_acknowledgement_required")
    if latest_preview is None:
        blockers.append("dry_run_preview_required")
    if action.payload.get("destructive") is True:
        blockers.append("destructive_actions_blocked")
    return unique_values(blockers)


def action_impact_check_blockers(
    action: ActionObject,
    latest_confirmation: AuditEvent | None,
) -> list[str]:
    blockers: list[str] = []
    if latest_confirmation is None:
        blockers.append("action_confirmation_required")
    if not action.metrics:
        blockers.append("metric_facts_required")
    if not action.evidence_ids:
        blockers.append("evidence_ids_required")
    if action.payload.get("destructive") is True:
        blockers.append("destructive_actions_blocked")
    return unique_values(blockers)


def action_apply_blockers(
    *,
    action: ActionObject,
    required_checks: list[str],
    apply_allowed: bool,
    confirmation_satisfied: bool,
    impact_sanity_satisfied: bool,
    requires_human_confirmation: HumanConfirmation,
    supported_mutation_adapter: MutationAdapter,
    string_list: StringList,
) -> list[str]:
    blockers: list[str] = []
    if action.mode != ActionMode.apply:
        blockers.append("action_mode_prepare_only")
    if action.validation_status != "valid":
        blockers.append("action_validation_required")
    if not apply_allowed:
        blockers.append("payload_apply_allowed_false")
    if action.payload.get("destructive") is True:
        blockers.append("destructive_actions_blocked")
    if requires_human_confirmation(required_checks) and not confirmation_satisfied:
        blockers.append("human_confirm_before_apply")
    if not impact_sanity_satisfied:
        blockers.append("impact_sanity_check_required")
    if action.mode == ActionMode.apply and supported_mutation_adapter(action) is None:
        blockers.append("vendor_mutation_adapter_required")
    blocked_claims = string_list(action.payload.get("blocked_claims"))
    blockers.extend(f"blocked_claim:{claim}" for claim in blocked_claims[:8])
    return unique_values(blockers)
