from __future__ import annotations

from wilq.schemas import AuditEvent, RecommendationLogRecord
from wilq.storage.local_state import local_state_store

# Product workspace label used across the daily-check/dossier surfaces. This is
# deliberately distinct from the local audit identity (``ekologus_local_pilot``),
# which only stamps ActionObject audit records.
_ACTIVE_PRODUCT_WORKSPACE_ID = "ekologus"


def assert_active_recommendation_workspace(workspace_id: str) -> None:
    """Reject recommendation logs outside the active product workspace."""

    if workspace_id != _ACTIVE_PRODUCT_WORKSPACE_ID:
        raise ValueError(
            "Recommendation log workspace is outside the active WILQ workspace."
        )


def save_recommendation_log(record: RecommendationLogRecord) -> RecommendationLogRecord:
    assert_active_recommendation_workspace(record.workspace_id)
    event = AuditEvent(
        id=f"audit_recommendation_{record.id}",
        event_type="recommendation_recorded",
        event_type_label="Rekomendacja zapisana",
        actor=record.recorded_by,
        summary=record.reason,
        evidence_ids=record.evidence_ids,
        details={"recommendation": record.model_dump(mode="json")},
    )
    saved_event = local_state_store().save_audit_event(event)
    payload = saved_event.details.get("recommendation")
    if not isinstance(payload, dict):
        raise RuntimeError("Recommendation audit event lost its redacted record.")
    return RecommendationLogRecord.model_validate(payload)


def list_recommendation_logs(workspace_id: str) -> list[RecommendationLogRecord]:
    records: list[RecommendationLogRecord] = []
    for event in local_state_store().list_audit_events():
        if event.event_type != "recommendation_recorded":
            continue
        payload = event.details.get("recommendation")
        if not isinstance(payload, dict) or payload.get("workspace_id") != workspace_id:
            continue
        records.append(RecommendationLogRecord.model_validate(payload))
    return records
