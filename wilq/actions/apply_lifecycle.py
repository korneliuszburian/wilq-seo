from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import uuid4

from wilq.actions.action_blockers import action_apply_preflight_blockers
from wilq.actions.audit_store import (
    action_mutation_audit_record,
    build_apply_audit_event,
    latest_action_confirmation_event,
    latest_action_impact_check_event,
    latest_preview_event,
)
from wilq.actions.payload_readiness import (
    payload_api_mutation_ready,
    payload_apply_allowed,
    payload_preview_items,
)
from wilq.content.workflow.revision_binding import ContentDraftRevisionBinding
from wilq.content.workflow.store import WordPressRevisionApplyClaimResult
from wilq.schemas import (
    ActionApplyRequest,
    ActionApplyResult,
    ActionObject,
    ActionReviewGate,
    ActionStatus,
    ActionWordPressDraftApplyBlocker,
    AuditEvent,
)


def apply_action(
    action: ActionObject,
    request: ActionApplyRequest | None = None,
    *,
    review_gate: Callable[[ActionObject], ActionReviewGate],
    wordpress_apply_capability: Callable[
        ..., tuple[Any, list[ActionWordPressDraftApplyBlocker]]
    ],
    mutation_adapter: Callable[[ActionObject], str | None],
    execute_mutation_adapter: Callable[
        [ActionObject, str, ActionApplyRequest | None, Any],
        tuple[dict[str, Any] | None, list[str]],
    ],
    connector_status: Callable[[str], Any],
    impact_status: Callable[[Any], str | None],
    wordpress_apply_claim: Callable[..., WordPressRevisionApplyClaimResult],
    finish_wordpress_apply_claim: Callable[..., None],
    status_label: Callable[[str], str],
    audit_event_label: Callable[[AuditEvent], AuditEvent],
) -> ActionApplyResult:
    """Run the canonical fail-closed apply lifecycle and preserve mutation audit."""
    errors: list[str] = []

    def action_payload_apply_allowed(payload: dict[str, Any]) -> bool:
        return payload_apply_allowed(payload, payload_preview_items(payload))

    def action_payload_api_mutation_ready(payload: dict[str, Any]) -> bool:
        return payload_api_mutation_ready(payload, payload_preview_items(payload))
    wordpress_capability, wordpress_revision_blockers = wordpress_apply_capability(
        action, request
    )
    errors.extend(
        f"{blocker.label}: {blocker.reason}" for blocker in wordpress_revision_blockers
    )
    actor = request.confirmed_by if request and request.confirmed_by else "wilq_api"
    connector = connector_status(action.connector)
    preview = latest_preview_event(action.audit_events)
    confirmation = latest_action_confirmation_event(action.audit_events)
    impact_check = latest_action_impact_check_event(action.audit_events)
    adapter = mutation_adapter(action)
    errors.extend(
        action_apply_preflight_blockers(
            action=action,
            request=request,
            connector_configured=connector is not None and connector.configured,
            preview_present=preview is not None,
            confirmation_present=confirmation is not None,
            impact_checked=impact_status(impact_check) == "checked",
            mutation_adapter=adapter,
            wordpress_capability_present=wordpress_capability is not None,
            payload_apply_allowed=action_payload_apply_allowed,
            payload_api_mutation_ready=action_payload_api_mutation_ready,
        )
    )
    claimed_binding: ContentDraftRevisionBinding | None = None
    if not errors and adapter is not None and wordpress_capability is not None:
        binding = request.wordpress_draft if request is not None else None
        if binding is None:
            claim_blocker = _wordpress_apply_claim_blocker("not_current")
            wordpress_revision_blockers.append(claim_blocker)
            errors.append(f"{claim_blocker.label}: {claim_blocker.reason}")
        else:
            claim_result = wordpress_apply_claim(
                binding,
                action_id=action.id,
                claimed_by=actor,
            )
            if claim_result == "acquired":
                claimed_binding = binding
            else:
                claim_blocker = _wordpress_apply_claim_blocker(claim_result)
                wordpress_revision_blockers.append(claim_blocker)
                errors.append(f"{claim_blocker.label}: {claim_blocker.reason}")

    adapter_result: dict[str, Any] | None = None
    claim_final_status: str | None = None
    if not errors and adapter is not None:
        adapter_result, adapter_errors = execute_mutation_adapter(
            action,
            adapter,
            request,
            wordpress_capability,
        )
        claim_final_status = "failed" if adapter_errors else "applied"
        errors.extend(adapter_errors)

    audit = build_apply_audit_event(
        action=action,
        audit_id=f"audit_{action.id}_apply_{uuid4().hex[:12]}",
        actor=actor,
        errors=errors,
        wordpress_draft_binding=(request.wordpress_draft if request else None),
    )
    mutation_audit = action_mutation_audit_record(
        action=action,
        audit_event=audit,
        actor=actor,
        errors=errors,
        mutation_adapter=adapter,
        adapter_result=adapter_result,
        wordpress_draft_binding=(request.wordpress_draft if request else None),
        wordpress_revision_blockers=wordpress_revision_blockers,
    )
    if claimed_binding is not None:
        if claim_final_status is None:
            raise RuntimeError("WordPress apply claim reached audit without an adapter outcome.")
        finish_wordpress_apply_claim(
            claimed_binding,
            status=claim_final_status,
            audit_event=audit,
            mutation_audit=mutation_audit,
            adapter_result=adapter_result,
        )
    action.audit_events.append(audit)
    if errors:
        action.status = ActionStatus.blocked
        action.review_gate = review_gate(action)
        return ActionApplyResult(
            action_id=action.id,
            applied=False,
            status="blocked",
            status_label=status_label("blocked"),
            audit_event=audit_event_label(audit),
            mutation_audit=mutation_audit,
            errors=errors,
            wordpress_revision_blockers=wordpress_revision_blockers,
            adapter_result=adapter_result,
        )
    action.status = ActionStatus.applied
    action.review_gate = review_gate(action)
    return ActionApplyResult(
        action_id=action.id,
        applied=True,
        status="applied",
        status_label=status_label("applied"),
        audit_event=audit_event_label(audit),
        mutation_audit=mutation_audit,
        wordpress_revision_blockers=wordpress_revision_blockers,
        adapter_result=adapter_result,
    )


def _wordpress_apply_claim_blocker(
    claim_result: WordPressRevisionApplyClaimResult,
) -> ActionWordPressDraftApplyBlocker:
    if claim_result == "in_progress":
        return ActionWordPressDraftApplyBlocker(
            code="wordpress_revision_apply_in_progress",
            label="Zapis tej wersji już trwa",
            reason="Inne żądanie przejęło dokładnie tę wersję przed adapterem WordPress.",
            next_step="Poczekaj na wynik pierwszego zapisu i odśwież stan akcji.",
        )
    if claim_result == "applied":
        return ActionWordPressDraftApplyBlocker(
            code="wordpress_revision_already_applied",
            label="Ta wersja została już przekazana do WordPress",
            reason="Jednorazowa zgoda dla tego bindingu została już wykorzystana.",
            next_step="Użyj utworzonego szkicu albo zapisz i zatwierdź nową wersję treści.",
        )
    if claim_result == "failed":
        return ActionWordPressDraftApplyBlocker(
            code="wordpress_revision_apply_consent_consumed",
            label="Poprzednia próba zużyła zgodę tej wersji",
            reason="Nie można ponawiać starego bindingu po nieudanej lub niepewnej próbie zapisu.",
            next_step="Zapisz nową wersję, wykonaj nowe review i ponów pełny łańcuch akcji.",
        )
    return ActionWordPressDraftApplyBlocker(
        code="wordpress_revision_not_current_at_apply",
        label="Zatwierdzona wersja zmieniła się przed zapisem",
        reason="Binding nie jest już najnowszą zatwierdzoną wersją w kanonicznym store.",
        next_step="Odśwież Treści i SEO i uruchom akcję dla aktualnej zatwierdzonej wersji.",
    )
