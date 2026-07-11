from __future__ import annotations

from collections.abc import Callable

from wilq.schemas import (
    ActionMode,
    ActionMutationReadinessRequirement,
    ActionObject,
    ActionRisk,
    AuditEvent,
)

PayloadApplyAllowed = Callable[[dict[str, object]], bool]
ImpactStatus = Callable[[AuditEvent | None], str | None]
EvidenceLabel = Callable[[list[str]], str]


def base_mutation_readiness_requirements(
    *,
    action: ActionObject,
    connector_configured: bool,
    connector_evidence: str,
    mutation_adapter: str | None,
    latest_preview: AuditEvent | None,
    latest_confirmation: AuditEvent | None,
    latest_impact_check: AuditEvent | None,
    payload_apply_allowed: PayloadApplyAllowed,
    impact_status: ImpactStatus,
    evidence_label: EvidenceLabel,
) -> list[ActionMutationReadinessRequirement]:
    return [
        _requirement(
            code="valid_action",
            label="Akcja sprawdzona w WILQ",
            satisfied=action.validation_status == "valid",
            evidence=action.validation_status,
        ),
        _requirement(
            code="apply_mode",
            label="Akcja ma tryb zapisu",
            satisfied=action.mode == ActionMode.apply,
            evidence=action.mode.value,
        ),
        _requirement(
            code="payload_apply_allowed",
            label="Payload dopuszcza apply",
            satisfied=payload_apply_allowed(action.payload),
            evidence=str(action.payload.get("apply_allowed", False)).lower(),
        ),
        _requirement(
            code="evidence_present",
            label="Akcja ma dowody źródłowe",
            satisfied=bool(action.evidence_ids),
            evidence=evidence_label(action.evidence_ids),
        ),
        _requirement(
            code="connector_configured",
            label="Connector jest skonfigurowany",
            satisfied=connector_configured,
            evidence=connector_evidence,
        ),
        _requirement(
            code="preview_audit",
            label="Podgląd zmian zapisany",
            satisfied=latest_preview is not None,
            evidence=latest_preview.id if latest_preview is not None else None,
        ),
        _requirement(
            code="confirmation_audit",
            label="Potwierdzenie operatora zapisane",
            satisfied=latest_confirmation is not None,
            evidence=latest_confirmation.id if latest_confirmation is not None else None,
        ),
        _requirement(
            code="impact_check",
            label="Sprawdzenie efektu zapisane",
            satisfied=impact_status(latest_impact_check) == "checked",
            evidence=latest_impact_check.id if latest_impact_check is not None else None,
        ),
        _requirement(
            code="risk_allowed",
            label="Ryzyko akcji dopuszcza zapis",
            satisfied=action.risk not in {ActionRisk.high, ActionRisk.critical},
            evidence=action.risk.value,
        ),
        _requirement(
            code="non_destructive",
            label="Akcja nie jest destrukcyjna",
            satisfied=action.payload.get("destructive") is not True,
            evidence=str(action.payload.get("destructive", False)).lower(),
        ),
        _requirement(
            code="mutation_adapter",
            label="Bezpieczny adapter zapisu istnieje",
            satisfied=mutation_adapter is not None,
            evidence=mutation_adapter,
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
