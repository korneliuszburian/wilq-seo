from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from wilq.schemas import (
    ActionObject,
    ActionPreviewCardViewModel,
    ActionPreviewItemViewModel,
    ActionPreviewRequest,
    ActionPreviewResult,
    ActionReviewGate,
    AuditEvent,
)


def preview_action(
    action: ActionObject,
    request: ActionPreviewRequest | None = None,
    *,
    review_gate: Callable[[ActionObject], ActionReviewGate],
    payload_preview_items: Callable[[dict[str, Any]], list[dict[str, Any]]],
    preview_cards: Callable[[ActionObject], list[ActionPreviewCardViewModel]],
    preview_item_view_models: Callable[..., list[ActionPreviewItemViewModel]],
    preview_blockers: Callable[[ActionObject, list[dict[str, Any]]], list[str]],
    preview_summary: Callable[..., str],
    build_preview_audit: Callable[..., AuditEvent],
    preview_contract: Callable[[dict[str, Any], list[dict[str, Any]]], str | None],
    status_label: Callable[[str], str],
    gate_labels: Callable[[list[str]], list[str]],
    audit_event_label: Callable[[AuditEvent], AuditEvent],
    review_gate_labels: Callable[[ActionReviewGate], ActionReviewGate],
    preview_row: Callable[[str, str], Any],
    apply_state_label: Callable[[Any], str],
    system_readiness_label: Callable[[Any], str],
    preview_contract_label: Callable[[str | None], str],
) -> ActionPreviewResult:
    """Build and audit a preview without allowing mutation."""
    preview_request = request or ActionPreviewRequest()
    action.review_gate = review_gate(action)
    raw_preview_items = payload_preview_items(action.payload)
    included_items = raw_preview_items[: preview_request.max_items]
    cards = preview_cards(action)
    preview_items = preview_item_view_models(
        action=action,
        raw_items=raw_preview_items,
        preview_cards=cards,
        max_items=preview_request.max_items,
        preview_row=preview_row,
        apply_state_label=apply_state_label,
        system_readiness_label=system_readiness_label,
        preview_contract_label=preview_contract_label,
    )
    blockers = preview_blockers(action, raw_preview_items)
    status: Literal["preview_ready", "blocked"] = "blocked" if blockers else "preview_ready"
    audit = build_preview_audit(
        action=action,
        actor=preview_request.requested_by or "wilq_api",
        summary=preview_summary(
            status=status,
            included_items=len(included_items),
            preview_items=len(raw_preview_items),
        ),
    )
    action.audit_events = [audit, *action.audit_events]
    return ActionPreviewResult(
        action_id=action.id,
        status=status,
        status_label=status_label(status),
        dry_run=True,
        mutation_allowed=False,
        preview_contract=preview_contract(action.payload, raw_preview_items),
        preview_items=preview_items,
        preview_cards=cards,
        preview_items_total=len(raw_preview_items),
        omitted_items=max(len(raw_preview_items) - len(included_items), 0),
        blockers=blockers,
        blocker_labels=gate_labels(blockers),
        audit_event=audit_event_label(audit),
        review_gate=review_gate_labels(action.review_gate),
    )
