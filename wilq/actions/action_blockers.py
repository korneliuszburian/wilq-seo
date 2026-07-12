from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from wilq.actions.metric_utils import unique_values
from wilq.schemas import (
    ActionConfirmRequest,
    ActionImpactCheckRequest,
    ActionMode,
    ActionObject,
    AuditEvent,
)

AdsTargetBlockers = Callable[[ActionConfirmRequest], list[str]]
HumanConfirmation = Callable[[list[str]], bool]
MutationAdapter = Callable[[ActionObject], str | None]
StringList = Callable[[Any], list[str]]
GateLabels = Callable[[list[str]], list[str]]
OperatorNote = Callable[[str], str]
StatusLabel = Callable[[str], str]
ConnectorLabels = Callable[[list[str]], list[str]]
MoneyLabel = Callable[[Any], str]


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


def action_preview_summary(
    *,
    status: Literal["preview_ready", "blocked"],
    included_items: int,
    preview_items: int,
) -> str:
    if status == "blocked":
        return (
            "Podgląd zmian przygotowany, ale zapis zmian pozostaje zablokowany. "
            f"Pokazano {included_items} z {preview_items} pozycji do sprawdzenia. "
            "Nie zapisano zmian w zewnętrznych systemach."
        )
    return (
        f"Podgląd zmian przygotowany. Pokazano {included_items} z {preview_items} "
        "pozycji do sprawdzenia. Nie zapisano zmian w zewnętrznych systemach."
    )


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


def action_confirmation_event_type(action: ActionObject, confirmed: bool) -> str:
    if action.payload.get("action_type") == "confirm_ads_target_guardrails":
        return (
            "ads_target_guardrail_confirmed"
            if confirmed
            else "ads_target_guardrail_confirmation_blocked"
        )
    return "action_apply_confirmed" if confirmed else "action_confirmation_blocked"


def action_confirmation_summary(
    action: ActionObject,
    request: ActionConfirmRequest,
    blockers: list[str],
    latest_preview: AuditEvent | None,
    *,
    ads_target_summary: Callable[[ActionConfirmRequest, list[str]], str],
    gate_labels: GateLabels,
    operator_note: OperatorNote,
) -> str:
    del latest_preview
    if action.payload.get("action_type") == "confirm_ads_target_guardrails":
        return ads_target_summary(request, blockers)
    if blockers:
        return (
            "Potwierdzenie zapisu zmian zablokowane: "
            f"{', '.join(gate_labels(blockers))}. "
            f"{operator_note(request.notes)}"
            "Ten krok nie zapisuje zmian w zewnętrznych systemach."
        )
    return (
        "Potwierdzenie podglądu zapisane. "
        f"{operator_note(request.notes)}"
        "Ten krok nie zapisuje zmian w zewnętrznych systemach."
    )


def ads_target_confirmation_summary(
    request: ActionConfirmRequest,
    blockers: list[str],
    *,
    gate_labels: GateLabels,
    micros_money_label: MoneyLabel,
) -> str:
    if blockers:
        return (
            "Potwierdzenie celu Ads zablokowane: "
            f"{', '.join(gate_labels(blockers))}. "
            f"Notatka: {request.notes}. "
            "Ten krok nie zapisuje zmian w Google Ads."
        )
    if request.target_roas is not None:
        target_summary = f"docelowy zwrot z reklam: {request.target_roas:g}"
    else:
        target_summary = (
            f"docelowy koszt pozyskania celu: {micros_money_label(request.target_cpa_micros)}"
        )
    return (
        f"Potwierdzono roboczą zasadę bezpieczeństwa celu Ads: {target_summary}. "
        f"Notatka: {request.notes}. "
        "Ten zapis odblokowuje tylko kontekst przeglądu celu; nie zapisuje zmian, "
        "nie potwierdza rentowności i nie skaluje budżetu."
    )


def action_impact_check_summary(
    *,
    request: ActionImpactCheckRequest,
    status: Literal["checked", "blocked"],
    metric_fact_count: int,
    source_connectors: list[str],
    blockers: list[str],
    status_label: StatusLabel,
    connector_labels: ConnectorLabels,
    gate_labels: GateLabels,
) -> str:
    parts = [
        f"Sprawdzenie efektu: {status_label(status)}.",
        f"Porównanie sprzed zmiany: {request.pre_window_days} dni.",
        f"Porównanie po zmianie: {request.post_window_days} dni.",
        f"Metryki z dowodami: {metric_fact_count}.",
        "Źródła: "
        + (
            f"{', '.join(connector_labels(source_connectors))}."
            if source_connectors
            else "brak."
        ),
    ]
    if blockers:
        parts.append(f"Blokady: {', '.join(gate_labels(blockers))}.")
    parts.append(f"Notatka: {request.notes}.")
    parts.append("Ten krok nie zapisuje zmian w zewnętrznych systemach.")
    return " ".join(parts)
