from __future__ import annotations

from wilq.schemas import ActionObject, ActionRisk


def unsafe_apply_reasons(action: ActionObject, connector_configured: bool) -> list[str]:
    reasons: list[str] = []
    if not action.evidence_ids:
        reasons.append("missing_evidence_ids")
    if not connector_configured:
        reasons.append("connector_not_configured")
    if action.risk in {ActionRisk.high, ActionRisk.critical}:
        reasons.append("high_or_critical_risk_blocked")
    if action.payload.get("destructive") is True:
        reasons.append("destructive_action_blocked")
    return reasons
