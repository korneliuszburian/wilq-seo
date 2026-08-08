from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, cast
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
from wilq.content.workflow.documents.revision_binding import ContentDraftRevisionBinding
from wilq.content.workflow.store.store import WordPressRevisionApplyClaimResult
from wilq.content.workflow.store.store_new_page_apply import new_page_apply_claim_store
from wilq.content.workflow.target.new_page_apply_capability import new_page_apply_binding
from wilq.content.workflow.target.new_page_draft_action import (
    CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE,
)
from wilq.content.workflow.target.new_page_draft_executor import execute_new_page_draft_action
from wilq.content.workflow.target.new_page_revision_binding import ContentNewPageDraftBinding
from wilq.schemas import (
    ActionApplyRequest,
    ActionApplyResult,
    ActionObject,
    ActionReviewGate,
    ActionStatus,
    ActionWordPressDraftApplyBlocker,
    AuditEvent,
)

WordPressApplyCapability = Callable[
    ..., tuple[Any, list[ActionWordPressDraftApplyBlocker]]
]
ExecuteMutationAdapter = Callable[
    [ActionObject, str, ActionApplyRequest | None, Any],
    tuple[dict[str, Any] | None, list[str]],
]


@dataclass(frozen=True)
class _ApplyCapability:
    capability: Any
    blockers: list[ActionWordPressDraftApplyBlocker]
    is_new_page: bool


@dataclass(frozen=True)
class _ApplyClaim:
    wordpress_binding: ContentDraftRevisionBinding | None = None
    new_page_binding: ContentNewPageDraftBinding | None = None


def apply_action(
    action: ActionObject,
    request: ActionApplyRequest | None = None,
    *,
    review_gate: Callable[[ActionObject], ActionReviewGate],
    wordpress_apply_capability: WordPressApplyCapability,
    mutation_adapter: Callable[[ActionObject], str | None],
    execute_mutation_adapter: ExecuteMutationAdapter,
    connector_status: Callable[[str], Any],
    impact_status: Callable[[Any], str | None],
    wordpress_apply_claim: Callable[..., WordPressRevisionApplyClaimResult],
    finish_wordpress_apply_claim: Callable[..., None],
    status_label: Callable[[str], str],
    audit_event_label: Callable[[AuditEvent], AuditEvent],
) -> ActionApplyResult:
    """Run the canonical fail-closed apply lifecycle and preserve mutation audit."""
    errors: list[str] = []
    resolved = _resolve_apply_capability(action, request, wordpress_apply_capability)
    wordpress_revision_blockers = resolved.blockers
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
            wordpress_capability_present=resolved.capability is not None,
            payload_apply_allowed=_payload_apply_allowed,
            payload_api_mutation_ready=_payload_api_mutation_ready,
        )
    )
    claim = _ApplyClaim()
    if not errors and adapter is not None and resolved.capability is not None:
        claim, claim_blocker = _claim_exact_apply(
            action, request, actor, resolved, wordpress_apply_claim
        )
        if claim_blocker is not None:
            wordpress_revision_blockers.append(claim_blocker)
            errors.append(f"{claim_blocker.label}: {claim_blocker.reason}")

    adapter_result: dict[str, Any] | None = None
    claim_final_status: str | None = None
    if not errors and adapter is not None:
        adapter_result, adapter_errors = _execute_apply(
            action, adapter, request, resolved, execute_mutation_adapter
        )
        claim_final_status = "failed" if adapter_errors else "applied"
        errors.extend(adapter_errors)

    audit, mutation_audit = _audit_apply(
        action, request, actor, errors, adapter, adapter_result, wordpress_revision_blockers
    )
    _finish_apply_claim(
        claim,
        claim_final_status,
        finish_wordpress_apply_claim,
        audit,
        mutation_audit,
        adapter_result,
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


def _payload_apply_allowed(payload: dict[str, Any]) -> bool:
    return payload_apply_allowed(payload, payload_preview_items(payload))


def _payload_api_mutation_ready(payload: dict[str, Any]) -> bool:
    return payload_api_mutation_ready(payload, payload_preview_items(payload))


def _audit_apply(
    action: ActionObject,
    request: ActionApplyRequest | None,
    actor: str,
    errors: list[str],
    adapter: str | None,
    adapter_result: dict[str, Any] | None,
    blockers: list[ActionWordPressDraftApplyBlocker],
) -> tuple[AuditEvent, Any]:
    wordpress_binding = request.wordpress_draft if request else None
    new_page_binding = request.new_page_draft if request else None
    audit = build_apply_audit_event(
        action=action,
        audit_id=f"audit_{action.id}_apply_{uuid4().hex[:12]}",
        actor=actor,
        errors=errors,
        wordpress_draft_binding=wordpress_binding,
        new_page_draft_binding=new_page_binding,
    )
    mutation_audit = action_mutation_audit_record(
        action=action,
        audit_event=audit,
        actor=actor,
        errors=errors,
        mutation_adapter=adapter,
        adapter_result=adapter_result,
        wordpress_draft_binding=wordpress_binding,
        new_page_draft_binding=new_page_binding,
        wordpress_revision_blockers=blockers,
    )
    return audit, mutation_audit


def _resolve_apply_capability(
    action: ActionObject,
    request: ActionApplyRequest | None,
    wordpress_apply_capability: WordPressApplyCapability,
) -> _ApplyCapability:
    if action.payload.get("action_type") == CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE:
        capability, blockers = new_page_apply_binding(action, request)
        return _ApplyCapability(capability, blockers, is_new_page=True)
    capability, blockers = wordpress_apply_capability(action, request)
    return _ApplyCapability(capability, blockers, is_new_page=False)


def _claim_exact_apply(
    action: ActionObject,
    request: ActionApplyRequest | None,
    actor: str,
    resolved: _ApplyCapability,
    wordpress_apply_claim: Callable[..., WordPressRevisionApplyClaimResult],
) -> tuple[_ApplyClaim, ActionWordPressDraftApplyBlocker | None]:
    if resolved.is_new_page:
        binding = request.new_page_draft if request is not None else None
        result = (
            "not_current"
            if binding is None
            else new_page_apply_claim_store().claim_new_page_revision_apply(
                binding, action_id=action.id, claimed_by=actor
            )
        )
        if result == "acquired" and binding is not None:
            return _ApplyClaim(new_page_binding=binding), None
        return _ApplyClaim(), _new_page_apply_claim_blocker(result)
    wordpress_binding = request.wordpress_draft if request is not None else None
    if wordpress_binding is None:
        return _ApplyClaim(), _wordpress_apply_claim_blocker("not_current")
    result = wordpress_apply_claim(wordpress_binding, action_id=action.id, claimed_by=actor)
    if result == "acquired":
        return _ApplyClaim(wordpress_binding=wordpress_binding), None
    return _ApplyClaim(), _wordpress_apply_claim_blocker(result)


def _execute_apply(
    action: ActionObject,
    adapter: str,
    request: ActionApplyRequest | None,
    resolved: _ApplyCapability,
    execute_mutation_adapter: ExecuteMutationAdapter,
) -> tuple[dict[str, Any] | None, list[str]]:
    if resolved.is_new_page:
        return execute_new_page_draft_action(action)
    return execute_mutation_adapter(action, adapter, request, resolved.capability)


def _finish_apply_claim(
    claim: _ApplyClaim,
    status: str | None,
    finish_wordpress_apply_claim: Callable[..., None],
    audit: AuditEvent,
    mutation_audit: Any,
    adapter_result: dict[str, Any] | None,
) -> None:
    if claim.wordpress_binding is not None:
        if status is None:
            raise RuntimeError("WordPress apply claim reached audit without an adapter outcome.")
        finish_wordpress_apply_claim(
            claim.wordpress_binding,
            status=status,
            audit_event=audit,
            mutation_audit=mutation_audit,
            adapter_result=adapter_result,
        )
    if claim.new_page_binding is not None:
        if status is None:
            raise RuntimeError("New-page apply claim reached audit without an adapter outcome.")
        if status not in {"applied", "failed"}:
            raise RuntimeError("New-page apply claim received an unsupported adapter outcome.")
        new_page_apply_claim_store().finish_new_page_revision_apply_claim(
            claim.new_page_binding,
            status=cast(Literal["applied", "failed"], status),
            audit_event=audit,
            mutation_audit=mutation_audit,
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


def _new_page_apply_claim_blocker(
    claim_result: str,
) -> ActionWordPressDraftApplyBlocker:
    messages = {
        "in_progress": (
            "new_page_revision_apply_in_progress",
            "Zapis tej nowej strony już trwa",
            "Inne żądanie przejęło tę samą approved rewizję przed adapterem.",
            "Poczekaj na wynik pierwszego zapisu i odśwież stan akcji.",
        ),
        "applied": (
            "new_page_revision_already_applied",
            "Ta rewizja nowej strony została już przekazana do WordPress",
            "Jednorazowa zgoda dla exact rewizji została już wykorzystana.",
            "Użyj odzyskanego szkicu albo przygotuj i zatwierdź nową rewizję.",
        ),
        "failed": (
            "new_page_revision_apply_consent_consumed",
            "Poprzednia próba zużyła zgodę tej rewizji",
            "Nie można powtarzać starej rewizji po nieudanej lub niepewnej próbie.",
            (
                "Zapisz nową wersję, wykonaj nowe review i utwórz nową akcję przed "
                "kolejną próbą."
            ),
        ),
        "uncertain": (
            "new_page_revision_apply_result_uncertain",
            "Wynik poprzedniego zapisu jest niepewny",
            (
                "Claim ma stan applied, ale nie zawiera odzyskiwalnego ID ani linku szkicu. "
                "Ponowienie mogłoby utworzyć duplikat."
            ),
            (
                "Sprawdź WordPress dev i audit tej akcji, rozstrzygnij, czy szkic istnieje, "
                "i nie ponawiaj tej samej exact rewizji."
            ),
        ),
        "not_current": (
            "new_page_revision_not_current_at_apply",
            "Rewizja nowej strony nie jest już aktualna",
            "Binding nie odpowiada najnowszej approved rewizji w lokalnym store.",
            (
                "Odśwież nową stronę, zapisz i zatwierdź aktualną rewizję, potem utwórz "
                "nową akcję."
            ),
        ),
    }
    code, label, reason, next_step = messages.get(claim_result, messages["not_current"])
    return ActionWordPressDraftApplyBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
    )
