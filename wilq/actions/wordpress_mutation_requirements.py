from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from wilq.connectors.wordpress.client import create_wordpress_draft_post
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.handoff.wordpress import ContentWordPressDraftHandoff
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftSectionOverride,
    ContentWordPressDraftWriteAuthorization,
    execute_content_wordpress_draft_handoff,
    wordpress_draft_execution_errors,
)
from wilq.content.planning.generated_proposal import read_content_planning_proposal
from wilq.content.planning.generated_proposal_store import content_planning_proposal_store
from wilq.content.workflow.contracts import (
    ContentWordPressDraftActivationPacketResponse,
    ContentWordPressDraftWriteReadinessResponse,
)
from wilq.content.workflow.revision_binding import ContentDraftRevisionBinding
from wilq.content.workflow.stage_write_readiness import (
    wordpress_draft_binding_from_audit_event,
    wordpress_draft_write_authorization_verified,
)
from wilq.credentials.runtime import variable_value
from wilq.schemas import (
    ActionApplyRequest,
    ActionMutationReadinessRequirement,
    ActionObject,
    ActionWordPressDraftApplyBlocker,
    AuditEvent,
)

PreviewItems = Callable[[dict[str, Any]], list[dict[str, Any]]]
WordPressDraftActionChain = tuple[AuditEvent, AuditEvent, AuditEvent, AuditEvent]


@dataclass(frozen=True)
class WordPressDraftApplyCapability:
    handoff: ContentWordPressDraftHandoff
    draft_package: ContentDraftPackage
    write_authorization: ContentWordPressDraftWriteAuthorization
    section_overrides: list[ContentWordPressDraftSectionOverride]


def wordpress_draft_apply_capability(
    action: ActionObject,
    request: ActionApplyRequest | None,
) -> tuple[
    WordPressDraftApplyCapability | None,
    list[ActionWordPressDraftApplyBlocker],
]:
    if action.id != "act_apply_wordpress_draft_handoff":
        return None, []
    binding = request.wordpress_draft if request is not None else None
    if binding is None:
        return None, [
            _apply_blocker(
                "wordpress_revision_binding_required",
                "Brakuje dokładnej wersji treści",
                "Apply WordPress wymaga identyfikatorów zapisanej wersji, paczki i decyzji.",
                "Wróć do zatwierdzonej wersji w Treści i SEO i ponów podgląd akcji.",
            )
        ]
    if request is None or not request.confirmed_by:
        return None, [
            _apply_blocker(
                "wordpress_action_actor_required",
                "Brakuje operatora potwierdzającego",
                "Apply szkicu wymaga jawnego aktora zgodnego z audytem confirm.",
                "Potwierdź podgląd jako zalogowany operator.",
            )
        ]

    from wilq.briefing.content_diagnostics import build_content_diagnostics_cached
    from wilq.content.workflow.api import (
        build_content_work_item_diagnostics_snapshot_response_for_work_item,
    )
    from wilq.content.workflow.store import content_workflow_store

    diagnostics = build_content_diagnostics_cached()
    workflow_store = content_workflow_store()
    revision_state = workflow_store.load_draft_revision_state(binding.work_item_id)
    planning_decisions = workflow_store.load_planning_decisions(binding.work_item_id)
    snapshot = build_content_work_item_diagnostics_snapshot_response_for_work_item(
        diagnostics,
        binding.work_item_id,
        revision_state=revision_state,
        planning_decisions=planning_decisions,
    )
    if snapshot is None:
        return None, [
            _apply_blocker(
                "wordpress_revision_not_current",
                "Wersja nie należy do aktualnej kolejki",
                "Wskazany work item nie istnieje w bieżącym workflow WILQ.",
                "Odśwież Treści i SEO i wybierz aktualny work item.",
            )
        ]
    # The action registry is intentionally shared across the dashboard, but
    # the apply boundary must reconstruct the selected work item's exact
    # generated proposal before validating its revision context. Without this
    # second projection, the first snapshot can use the queue baseline while
    # the persisted v2 revision is bound to the generated planning digest.
    try:
        planning_response = read_content_planning_proposal(
            snapshot=snapshot,
            store=content_planning_proposal_store(),
        )
    except Exception as exc:
        return None, [
            _apply_blocker(
                "wordpress_planning_reconstruction_failed",
                "Nie udało się odtworzyć planu treści",
                f"Odczyt zapisanego planu zakończył się błędem: {type(exc).__name__}.",
                "Odśwież workflow i wygeneruj aktualny plan przed handoffem.",
            )
        ]
    if planning_response.status not in {"ready", "idempotent", "created"}:
        return None, [
            _apply_blocker(
                "wordpress_planning_reconstruction_failed",
                "Plan treści nie jest gotowy do handoffu",
                "Nie można zweryfikować wersji WordPress bez aktualnego, zapisanego planu.",
                "Wygeneruj i zatwierdź aktualny plan, a następnie ponów handoff.",
            )
        ]
    generated_planning_proposal = planning_response.proposal
    if generated_planning_proposal is None:
        return None, [
            _apply_blocker(
                "wordpress_planning_reconstruction_failed",
                "Brakuje zapisanego planu treści",
                "Plan został oznaczony jako gotowy, ale nie zawiera propozycji do weryfikacji.",
                "Wygeneruj nową wersję planu i ponów handoff.",
            )
        ]
    snapshot = build_content_work_item_diagnostics_snapshot_response_for_work_item(
        diagnostics,
        binding.work_item_id,
        revision_state=revision_state,
        planning_decisions=planning_decisions,
        generated_planning_proposal=generated_planning_proposal,
    )
    if snapshot is None:
        return None, [
            _apply_blocker(
                "wordpress_planning_reconstruction_failed",
                "Nie udało się odtworzyć planu treści",
                "Nie udało się odtworzyć aktualnego planu dla zapisanej wersji.",
                "Odśwież workflow i zapisz nową wersję dla aktualnego planu sekcji.",
            )
        ]
    draft_package = snapshot.draft_package.draft_package_result.draft_package
    handoff_result = snapshot.wordpress_handoff.handoff_result
    handoff = handoff_result.handoff
    if draft_package is None or handoff is None:
        if handoff_result.blockers:
            return None, [
                _apply_blocker(
                    blocker.code,
                    blocker.label,
                    blocker.reason,
                    blocker.next_step,
                )
                for blocker in handoff_result.blockers
            ]
        return None, [
            _apply_blocker(
                "wordpress_revision_not_current",
                "Brakuje aktualnego handoffu wersji",
                "Nie udało się odtworzyć paczki i handoffu dla zatwierdzonej wersji.",
                "Odśwież workflow i zapisz nową wersję dla aktualnego planu sekcji.",
            )
        ]
    if handoff.revision_binding is None or handoff.revision_binding != binding:
        return None, [
            _apply_blocker(
                "wordpress_revision_binding_mismatch",
                "Wersja akcji nie pasuje do bieżącego handoffu",
                "Co najmniej jeden identyfikator wersji, paczki, decyzji albo adresu się zmienił.",
                "Wygeneruj nowy podgląd dla aktualnej zatwierdzonej wersji.",
            )
        ]
    target_host = (urlparse(binding.final_canonical_url).hostname or "").lower()
    if target_host not in {"ekologus.pl", "www.ekologus.pl"}:
        return None, [
            _apply_blocker(
                "wordpress_revision_canonical_invalid",
                "Canonical nie prowadzi do Ekologus",
                "Apply szkicu wymaga publicznego canonical URL Ekologus.",
                "Ustaw aktualny publiczny adres Ekologus i zapisz nową wersję.",
            )
        ]
    if handoff.publish_allowed or handoff.destructive_update_allowed:
        return None, [
            _apply_blocker(
                "wordpress_handoff_not_draft_only",
                "Handoff nie jest draft-only",
                "Ta ścieżka nie może publikować ani aktualizować istniejącej treści.",
                "Wróć do bezpiecznego handoffu create-draft-only.",
            )
        ]

    chain, chain_blockers = _revision_bound_action_chain(
        action.audit_events,
        binding=binding,
        confirmed_by=request.confirmed_by,
    )
    if chain is None:
        return None, chain_blockers
    preview, review, confirmation, impact = chain
    section_overrides = [
        ContentWordPressDraftSectionOverride(
            heading=section.heading,
            body_markdown=section.body_markdown,
            evidence_ids=section.evidence_ids,
        )
        for section in handoff.revision_sections
    ]
    authorization = ContentWordPressDraftWriteAuthorization(
        action_id=action.id,
        preview_audit_id=preview.id,
        review_audit_id=review.id,
        confirmation_audit_id=confirmation.id,
        impact_audit_id=impact.id,
        confirmed_by=request.confirmed_by,
        wordpress_draft_binding=binding,
    )
    if not wordpress_draft_write_authorization_verified(authorization):
        return None, [
            _apply_blocker(
                "wordpress_write_authorization_invalid",
                "Ślad akcji nie zgadza się z zapisanym audytem",
                "Preview, review, confirm i impact muszą istnieć w audycie dla jednej wersji.",
                "Ponów kroki ActionObject dla aktualnego handoffu.",
            )
        ]
    return (
        WordPressDraftApplyCapability(
            handoff=handoff,
            draft_package=draft_package,
            write_authorization=authorization,
            section_overrides=section_overrides,
        ),
        [],
    )


def _revision_bound_action_chain(
    events: list[AuditEvent],
    *,
    binding: ContentDraftRevisionBinding,
    confirmed_by: str,
) -> tuple[
    WordPressDraftActionChain | None,
    list[ActionWordPressDraftApplyBlocker],
]:
    latest_events = sorted(events, key=lambda event: event.created_at, reverse=True)
    preview = _latest_event(latest_events, {"action_preview_generated"})
    review = next(
        (event for event in latest_events if event.event_type.startswith("human_review_")),
        None,
    )
    confirmation = _latest_event(
        latest_events,
        {
            "action_apply_confirmed",
            "action_confirmation_blocked",
            "action_apply_confirmation_blocked",
        },
    )
    impact = _latest_event(
        latest_events,
        {"action_impact_check_completed", "action_impact_check_blocked"},
    )
    chain_events = [preview, review, confirmation, impact]
    if any(event is None for event in chain_events):
        return None, [
            _apply_blocker(
                "wordpress_action_chain_incomplete",
                "Brakuje pełnego śladu akcji",
                "Apply wymaga preview, approved review, confirm i impact dla tej wersji.",
                "Przejdź po kolei przez cztery kroki ActionObject.",
            )
        ]
    resolved_events = [event for event in chain_events if event is not None]
    if any(
        wordpress_draft_binding_from_audit_event(event) != binding
        for event in resolved_events
    ):
        return None, [
            _apply_blocker(
                "wordpress_action_chain_binding_mismatch",
                "Ślad akcji dotyczy innej wersji",
                "Najnowsze preview, review, confirm i impact muszą mieć identyczny binding.",
                "Ponów cały łańcuch ActionObject dla aktualnej zatwierdzonej wersji.",
            )
        ]
    if review is None or review.event_type != "human_review_approved_for_prepare":
        return None, [
            _apply_blocker(
                "wordpress_action_review_not_approved",
                "Review ActionObject nie zatwierdza wersji",
                "Najnowsza decyzja ActionObject dla tej wersji nie jest approved_for_prepare.",
                "Sprawdź wersję i zapisz zatwierdzające review ActionObject.",
            )
        ]
    if confirmation is None or confirmation.event_type != "action_apply_confirmed":
        return None, [
            _apply_blocker(
                "wordpress_action_confirmation_invalid",
                "Brakuje ważnego potwierdzenia",
                "Najnowsze potwierdzenie tej wersji jest zablokowane albo nie istnieje.",
                "Potwierdź aktualny podgląd jako operator.",
            )
        ]
    if impact is None or impact.event_type != "action_impact_check_completed":
        return None, [
            _apply_blocker(
                "wordpress_action_impact_invalid",
                "Sprawdzenie efektu jest zablokowane",
                "Apply wymaga zakończonego impact check dla tej samej wersji.",
                "Uzupełnij dowody i ponów impact check.",
            )
        ]
    if confirmation.actor != confirmed_by:
        return None, [
            _apply_blocker(
                "wordpress_action_actor_mismatch",
                "Operator nie pasuje do potwierdzenia",
                "Osoba wywołująca apply musi być osobą, która potwierdziła podgląd.",
                "Wykonaj apply jako operator zapisany w confirm.",
            )
        ]
    if preview is None:
        raise RuntimeError("Preview disappeared after complete ActionObject chain check.")
    if not (
        preview.created_at <= review.created_at
        <= confirmation.created_at
        <= impact.created_at
    ):
        return None, [
            _apply_blocker(
                "wordpress_action_chain_order_invalid",
                "Kroki akcji są nieaktualne",
                "Preview, review, confirm i impact nie zostały wykonane w wymaganej kolejności.",
                "Ponów cały łańcuch ActionObject od podglądu.",
            )
        ]
    return (preview, review, confirmation, impact), []


def _latest_event(
    events: list[AuditEvent],
    event_types: set[str],
) -> AuditEvent | None:
    return next((event for event in events if event.event_type in event_types), None)


def _apply_blocker(
    code: str,
    label: str,
    reason: str,
    next_step: str,
) -> ActionWordPressDraftApplyBlocker:
    return ActionWordPressDraftApplyBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
    )


def wordpress_draft_writes_enabled() -> bool:
    return (variable_value("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def execute_supported_wordpress_mutation_adapter(
    action: ActionObject,
    mutation_adapter: str,
    wordpress_capability: WordPressDraftApplyCapability | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    if mutation_adapter != "wordpress_draft_execution_boundary":
        return None, [f"Adapter zapisu {mutation_adapter} nie ma implementacji wykonania."]
    if wordpress_capability is not None:
        execution = execute_content_wordpress_draft_handoff(
            handoff=wordpress_capability.handoff,
            draft_package=wordpress_capability.draft_package,
            mode="live",
            live_write_enabled=wordpress_draft_writes_enabled(),
            create_draft=create_wordpress_draft_post,
            action_apply_authorized=True,
            write_authorization=wordpress_capability.write_authorization,
            write_authorization_verified=wordpress_draft_write_authorization_verified(
                wordpress_capability.write_authorization
            ),
            section_overrides=wordpress_capability.section_overrides,
            require_exact_section_overrides=True,
        )
    else:
        execution = execute_content_wordpress_draft_handoff(
            handoff=None,
            draft_package=None,
            mode="dry_run",
            live_write_enabled=False,
            create_draft=None,
        )
    return {
        "adapter": mutation_adapter,
        "connector": action.connector,
        "allowed_operation": "create_wordpress_draft",
        "execution_status": execution.status,
        "execution_mode": execution.mode,
        "external_write_attempted": execution.external_write_attempted,
        "execution_result": execution.model_dump(mode="json"),
        "redacted": True,
    }, wordpress_draft_execution_errors(execution)


def wordpress_draft_write_readiness(
    action: ActionObject,
) -> ContentWordPressDraftWriteReadinessResponse | None:
    if action.id != "act_apply_wordpress_draft_handoff":
        return None
    from wilq.content.workflow.api import build_content_wordpress_draft_write_readiness_response

    return build_content_wordpress_draft_write_readiness_response(action_id=action.id)


def wordpress_draft_activation_packet(
    action: ActionObject,
) -> ContentWordPressDraftActivationPacketResponse | None:
    if action.id != "act_apply_wordpress_draft_handoff":
        return None
    from wilq.briefing.content_diagnostics import build_content_diagnostics_cached
    from wilq.content.workflow.api import (
        build_content_wordpress_draft_activation_packet_response,
        build_content_work_item_diagnostics_snapshot_response,
    )
    from wilq.content.workflow.store import content_workflow_store

    diagnostics = build_content_diagnostics_cached()
    initial_snapshot = build_content_work_item_diagnostics_snapshot_response(diagnostics)
    work_item_id = initial_snapshot.preflight.item.id
    workflow_store = content_workflow_store()
    snapshot = build_content_work_item_diagnostics_snapshot_response(
        diagnostics,
        revision_state=workflow_store.load_draft_revision_state(work_item_id),
        planning_decisions=workflow_store.load_planning_decisions(work_item_id),
    )
    return build_content_wordpress_draft_activation_packet_response(
        snapshot,
        action_id=action.id,
    )


def wordpress_draft_execution_readiness_requirements(
    action: ActionObject,
    *,
    activation_packet: ContentWordPressDraftActivationPacketResponse | None = None,
) -> list[ActionMutationReadinessRequirement]:
    if action.id != "act_apply_wordpress_draft_handoff":
        return []
    if activation_packet is not None:
        blocker_evidence = (
            ", ".join(
                [
                    *activation_packet.handoff_blockers,
                    *activation_packet.execution_blockers,
                ]
            )
            or "ready"
        )
        return [
            _requirement(
                code="wordpress_draft_handoff_ready",
                label="Zatwierdzone przekazanie do WordPress istnieje",
                satisfied=activation_packet.handoff_ready,
                evidence=blocker_evidence,
            ),
            _requirement(
                code="wordpress_draft_package_ready",
                label="Paczka szkicu WordPress istnieje",
                satisfied=activation_packet.draft_package_ready,
                evidence=activation_packet.draft_package_id or blocker_evidence,
            ),
        ]
    execution = execute_content_wordpress_draft_handoff(
        handoff=None,
        draft_package=None,
        mode="dry_run",
        live_write_enabled=False,
        create_draft=None,
    )
    blocker_codes = {blocker.code for blocker in execution.blockers}
    execution_blocker_evidence: str | None = (
        ", ".join(blocker.code for blocker in execution.blockers) or None
    )
    return [
        _requirement(
            code="wordpress_draft_handoff_ready",
            label="Zatwierdzone przekazanie do WordPress istnieje",
            satisfied="missing_handoff" not in blocker_codes,
            evidence=execution_blocker_evidence or "ready",
        ),
        _requirement(
            code="wordpress_draft_package_ready",
            label="Paczka szkicu WordPress istnieje",
            satisfied="missing_draft_package" not in blocker_codes,
            evidence=execution_blocker_evidence or "ready",
        ),
    ]


def wordpress_draft_target_content_readiness_requirements(
    action: ActionObject,
    *,
    activation_packet: ContentWordPressDraftActivationPacketResponse | None = None,
    preview_items: PreviewItems,
) -> list[ActionMutationReadinessRequirement]:
    if action.id != "act_apply_wordpress_draft_handoff":
        return []
    if activation_packet is not None:
        evidence_parts = [
            f"draft_package_ready={str(activation_packet.draft_package_ready).lower()}",
            f"human_review_ready={str(activation_packet.human_review_ready).lower()}",
            f"audit_ready={str(activation_packet.audit_ready).lower()}",
            f"dry_run_ready={str(activation_packet.dry_run_ready).lower()}",
        ]
        return [
            _requirement(
                code="wordpress_draft_target_content_ready",
                label="Target treści przeszedł Claim Ledger i review szkicu",
                satisfied=activation_packet.dry_run_ready,
                evidence="; ".join(evidence_parts),
            )
        ]
    items = preview_items(action.payload)
    if not items:
        return [
            _requirement(
                code="wordpress_draft_target_content_ready",
                label="Target treści przeszedł Claim Ledger i review szkicu",
                satisfied=False,
                evidence="missing_payload_preview",
            )
        ]
    first = items[0]
    apply_allowed = first.get("apply_allowed") is True
    api_mutation_ready = first.get("api_mutation_ready") is True
    required_validation = [
        value for value in first.get("required_validation", []) if isinstance(value, str)
    ]
    validation_evidence = ", ".join(required_validation[:4])
    if len(required_validation) > 4:
        validation_evidence = f"{validation_evidence}, +{len(required_validation) - 4}"
    evidence_parts = [
        f"apply_allowed={str(apply_allowed).lower()}",
        f"api_mutation_ready={str(api_mutation_ready).lower()}",
    ]
    if validation_evidence:
        evidence_parts.append(f"required_validation={validation_evidence}")
    return [
        _requirement(
            code="wordpress_draft_target_content_ready",
            label="Target treści przeszedł Claim Ledger i review szkicu",
            satisfied=apply_allowed and api_mutation_ready,
            evidence="; ".join(evidence_parts),
        )
    ]


def wordpress_draft_write_readiness_requirements(
    action: ActionObject,
    *,
    wordpress_draft_readiness: ContentWordPressDraftWriteReadinessResponse | None = None,
) -> list[ActionMutationReadinessRequirement]:
    if action.id != "act_apply_wordpress_draft_handoff":
        return []
    readiness = wordpress_draft_readiness
    if readiness is None:
        from wilq.content.workflow.api import build_content_wordpress_draft_write_readiness_response

        readiness = build_content_wordpress_draft_write_readiness_response(action_id=action.id)
    authorization_ready = readiness.suggested_write_authorization is not None
    blocker_codes = ", ".join(blocker.code for blocker in readiness.blockers[:4]) or None
    return [
        _requirement(
            code="wordpress_draft_write_readiness",
            label="WordPress draft write readiness przechodzi",
            satisfied=readiness.ready,
            evidence=blocker_codes or "ready",
        ),
        _requirement(
            code="wordpress_draft_live_write_env",
            label="Env pozwala na zapis szkicu WordPress",
            satisfied=readiness.live_write_enabled_by_env,
            evidence=str(readiness.live_write_enabled_by_env).lower(),
        ),
        _requirement(
            code="wordpress_rest_adapter_configured",
            label="REST adapter WordPress jest skonfigurowany",
            satisfied=readiness.rest_adapter_configured,
            evidence=str(readiness.rest_adapter_configured).lower(),
        ),
        _requirement(
            code="wordpress_write_authorization",
            label="Autoryzacja write z audytu jest gotowa",
            satisfied=authorization_ready,
            evidence="ready" if authorization_ready else "missing",
        ),
    ]
def _requirement(
    *,
    code: str,
    label: str,
    satisfied: bool,
    evidence: str | None = None,
) -> ActionMutationReadinessRequirement:
    return ActionMutationReadinessRequirement(
        code=code,
        label=label,
        satisfied=satisfied,
        evidence=evidence,
    )
