"""Domain policy for human-recorded Ads execution and observation.

These rules used to live in the FastAPI router. They decide whether a human
report of an out-of-band Ads change is attributable to an exact measurement
plan and whether a later observation may be recorded. They never call Google
Ads and never turn a report into a success or causal claim.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from wilq.actions.service import get_action, persist_action_audit
from wilq.audit.identity import LOCAL_PILOT_AUDIT_IDENTITY
from wilq.evidence.registry import list_evidence_by_ids
from wilq.schemas import (
    AdsExternalExecutionAcknowledgementRequest,
    AdsExternalObservationRequest,
    AuditEvent,
)
from wilq.storage.local_state import local_state_store


class AdsExternalAuditViolation(Exception):
    """A typed domain refusal mapped to an HTTP status by the boundary."""

    def __init__(self, status_code: Literal[404, 409], detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def acknowledge_external_ads_execution(
    action_id: str,
    request: AdsExternalExecutionAcknowledgementRequest,
) -> AuditEvent:
    """Persist attribution of a human Ads change with an exact plan binding."""

    action = get_action(action_id)
    if action is None:
        raise AdsExternalAuditViolation(404, f"Unknown action: {action_id}")
    payload = action.payload
    plan = payload.get("measurement_plan")
    if payload.get("action_type") != "campaign_change_review" or not isinstance(plan, dict):
        raise AdsExternalAuditViolation(409, "Ta akcja nie ma zatwierdzonego planu pomiaru Ads.")
    if request.measurement_plan_id != plan.get("id"):
        raise AdsExternalAuditViolation(409, "Potwierdzenie wskazuje inną wersję planu pomiaru.")
    if plan.get("execution_acknowledgement_required") is not True:
        raise AdsExternalAuditViolation(
            409,
            "Plan pomiaru nie dopuszcza acknowledgement wykonania.",
        )
    event = AuditEvent(
        id=f"ads_external_execution_{uuid4().hex}",
        action_id=action_id,
        event_type="ads_external_execution_acknowledged",
        event_type_label="Ręczna zmiana Ads odnotowana poza WILQ",
        actor=LOCAL_PILOT_AUDIT_IDENTITY.principal_id,
        principal_id=LOCAL_PILOT_AUDIT_IDENTITY.principal_id,
        workspace_id=LOCAL_PILOT_AUDIT_IDENTITY.workspace_id,
        trust_level=LOCAL_PILOT_AUDIT_IDENTITY.trust_level,
        submitted_actor_label=request.acknowledged_by,
        summary=(
            "WILQ zapisał informację człowieka o wykonaniu zmiany poza API; "
            "nie jest to potwierdzenie vendor write ani sukcesu."
        ),
        evidence_ids=list(plan.get("baseline_evidence_ids", [])),
        details={
            "measurement_plan_id": request.measurement_plan_id,
            "execution_status": request.execution_status,
            "executed_at": request.executed_at.isoformat() if request.executed_at else None,
            "notes": request.notes,
            "observation_required": bool(plan.get("observation_required")),
            "success_claim_allowed": False,
            "vendor_write_attempted": False,
        },
    )
    persist_action_audit(event)
    return event


def record_external_ads_observation(
    action_id: str,
    request: AdsExternalObservationRequest,
) -> AuditEvent:
    """Persist a later observation without converting it into causality."""

    action = get_action(action_id)
    if action is None:
        raise AdsExternalAuditViolation(404, f"Unknown action: {action_id}")
    plan = action.payload.get("measurement_plan")
    if not isinstance(plan, dict) or request.measurement_plan_id != plan.get("id"):
        raise AdsExternalAuditViolation(409, "Observation wskazuje nieaktualny plan pomiaru.")
    acknowledgement = next(
        (
            event
            for event in local_state_store().list_audit_events(action_id=action_id)
            if event.id == request.acknowledgement_event_id
            and event.event_type == "ads_external_execution_acknowledged"
            and event.details.get("measurement_plan_id") == request.measurement_plan_id
        ),
        None,
    )
    if acknowledgement is None:
        raise AdsExternalAuditViolation(
            409,
            "Najpierw zapisz acknowledgement ręcznego wykonania dla tego planu.",
        )
    resolved_evidence = list_evidence_by_ids(request.evidence_ids)
    if {evidence.id for evidence in resolved_evidence} != set(request.evidence_ids):
        raise AdsExternalAuditViolation(
            409,
            "Obserwacja wskazuje nieznane identyfikatory dowodów.",
        )
    executed_at = acknowledgement.details.get("executed_at")
    if acknowledgement.details.get("execution_status") == "executed" and executed_at:
        try:
            executed_at_value = datetime.fromisoformat(executed_at)
        except (TypeError, ValueError):
            raise AdsExternalAuditViolation(
                409,
                "Acknowledgement ma nieprawidłowy czas wykonania.",
            ) from None
        if request.observed_at <= executed_at_value:
            raise AdsExternalAuditViolation(
                409,
                "Obserwacja musi nastąpić po zgłoszonym wykonaniu zmiany.",
            )
    event = AuditEvent(
        id=f"ads_external_observation_{uuid4().hex}",
        action_id=action_id,
        event_type="ads_external_observation_recorded",
        event_type_label="Obserwacja Ads odnotowana",
        actor=LOCAL_PILOT_AUDIT_IDENTITY.principal_id,
        principal_id=LOCAL_PILOT_AUDIT_IDENTITY.principal_id,
        workspace_id=LOCAL_PILOT_AUDIT_IDENTITY.workspace_id,
        trust_level=LOCAL_PILOT_AUDIT_IDENTITY.trust_level,
        summary=(
            "WILQ zapisał obserwację po ręcznej zmianie Ads; wynik nie jest "
            "automatycznie sukcesem ani dowodem przyczynowości."
        ),
        evidence_ids=list(request.evidence_ids),
        details={
            "measurement_plan_id": request.measurement_plan_id,
            "acknowledgement_event_id": acknowledgement.id,
            "observation_status": request.observation_status,
            "observed_at": request.observed_at.isoformat(),
            "notes": request.notes,
            "success_claim_allowed": False,
            "causal_claim_allowed": False,
            "vendor_write_attempted": False,
        },
    )
    persist_action_audit(event)
    return event


__all__ = [
    "AdsExternalAuditViolation",
    "acknowledge_external_ads_execution",
    "record_external_ads_observation",
]
