from __future__ import annotations

from wilq.actions.payloads import validate_action_payload
from wilq.connectors.registry import get_connector_status
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionApplyResult,
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    ActionValidationResult,
    AuditEvent,
    OpportunityDomain,
)


def seed_actions() -> dict[str, ActionObject]:
    action = ActionObject(
        id="act_configure_google_ads_env",
        title="Odnow Google Ads OAuth refresh token",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=[connector_evidence_id("google_ads")],
        human_diagnosis=(
            "Google Ads credentials are present, but the current refresh token is rejected "
            "by Google's OAuth endpoint with oauth_error=invalid_grant for the adwords scope."
        ),
        recommended_reason=(
            "A fresh marketing@rekurencja.com consent flow is required before WILQ can "
            "collect real Google Ads campaign, search-term and recommendation evidence."
        ),
        payload={
            "action_type": "repair_google_ads_oauth",
            "connector": "google_ads",
            "credential_source": "repo_env",
            "oauth_client_json_path": (
                "/home/krn/.local/wilq/"
                "client_secret_504856024095-"
                "0r6gpqoln9u6uvv474rqmeifk2urqgb7.apps.googleusercontent.com.json"
            ),
            "oauth_scope": "https://www.googleapis.com/auth/adwords",
            "helper_commands": [
                (
                    "uv run wilq google-ads oauth-url --client-secret-file "
                    "/home/krn/.local/wilq/client_secret_504856024095-"
                    "0r6gpqoln9u6uvv474rqmeifk2urqgb7.apps.googleusercontent.com.json"
                ),
                (
                    "uv run wilq google-ads oauth-exchange --client-secret-file "
                    "/home/krn/.local/wilq/client_secret_504856024095-"
                    "0r6gpqoln9u6uvv474rqmeifk2urqgb7.apps.googleusercontent.com.json "
                    "--redirect-url '<final localhost URL>' --write-env"
                ),
                (
                    "uv run wilq connectors refresh google_ads --mode vendor_read "
                    '--reason "Goal 001 Google Ads live data proof"'
                ),
            ],
            "required_env": [
                "GOOGLE_ADS_DEVELOPER_TOKEN",
                "GOOGLE_ADS_CLIENT_ID",
                "GOOGLE_ADS_CLIENT_SECRET",
                "GOOGLE_ADS_REFRESH_TOKEN",
                "GOOGLE_ADS_CUSTOMER_ID",
                "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
            ],
        },
        validation_status="not_validated",
        created_by="system_seed",
    )
    return {action.id: action}


_ACTIONS = seed_actions()


def list_actions() -> list[ActionObject]:
    return list(_ACTIONS.values())


def get_action(action_id: str) -> ActionObject | None:
    return _ACTIONS.get(action_id)


def validate_action(action: ActionObject) -> ActionValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    connector = get_connector_status(action.connector)
    if not action.evidence_ids:
        errors.append("ActionObject requires at least one evidence ID.")
    if connector is None:
        errors.append(f"Unknown connector: {action.connector}")
    elif action.mode == ActionMode.apply and not connector.configured:
        errors.append(f"Connector {action.connector} is not configured.")
    errors.extend(validate_action_payload(action.connector, action.payload))
    if action.risk in {ActionRisk.high, ActionRisk.critical}:
        warnings.append("High and critical risk actions require explicit product support.")
    valid = not errors
    action.validation_status = "valid" if valid else "invalid"
    if not valid:
        action.status = ActionStatus.validation_failed
    elif action.mode == ActionMode.apply:
        action.status = ActionStatus.ready_to_apply
    else:
        action.status = ActionStatus.ready
    return ActionValidationResult(
        action_id=action.id,
        valid=valid,
        status="valid" if valid else "invalid",
        errors=errors,
        warnings=warnings,
    )


def apply_action(action: ActionObject) -> ActionApplyResult:
    errors: list[str] = []
    connector = get_connector_status(action.connector)
    if action.validation_status != "valid":
        errors.append("Action must be validated before apply.")
    if action.mode != ActionMode.apply:
        errors.append("Action mode must be apply before external execution.")
    if not action.evidence_ids:
        errors.append("Action cannot apply without evidence IDs.")
    if connector is None or not connector.configured:
        errors.append("Connector is not configured for apply.")
    if action.risk in {ActionRisk.high, ActionRisk.critical}:
        errors.append("High and critical risk applies are blocked in Goal 001.")
    if action.payload.get("destructive") is True:
        errors.append("Destructive write actions are not implemented in Goal 001.")

    audit = AuditEvent(
        id=f"audit_{action.id}_{len(action.audit_events) + 1}",
        action_id=action.id,
        event_type="apply_blocked" if errors else "apply_succeeded",
        actor="wilq_api",
        summary="; ".join(errors) if errors else "Action applied through validated API path.",
        evidence_ids=action.evidence_ids,
    )
    action.audit_events.append(audit)
    if errors:
        action.status = ActionStatus.blocked
        return ActionApplyResult(
            action_id=action.id,
            applied=False,
            status="blocked",
            audit_event=audit,
            errors=errors,
        )
    action.status = ActionStatus.applied
    return ActionApplyResult(action_id=action.id, applied=True, status="applied", audit_event=audit)
