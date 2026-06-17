from __future__ import annotations

from collections.abc import Iterable

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
    MetricFact,
    OpportunityDomain,
)
from wilq.storage.metric_store import metric_store


def seed_static_actions() -> dict[str, ActionObject]:
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


_STATIC_ACTIONS = seed_static_actions()


def list_actions() -> list[ActionObject]:
    actions = {**_STATIC_ACTIONS, **seed_metric_action_candidates()}
    return list(actions.values())


def get_action(action_id: str) -> ActionObject | None:
    return {**_STATIC_ACTIONS, **seed_metric_action_candidates()}.get(action_id)


def seed_metric_action_candidates() -> dict[str, ActionObject]:
    facts = [
        fact
        for fact in metric_store().list_metric_facts(limit=120)
        if not _is_probe_only_fact(fact)
    ]
    by_connector = _facts_by_connector(facts)
    actions: dict[str, ActionObject] = {}

    merchant_facts = by_connector.get("google_merchant_center", [])
    if merchant_facts:
        action = ActionObject(
            id="act_review_merchant_feed_issues",
            title="Przygotuj kolejkę przeglądu feedu Merchant Center",
            domain=OpportunityDomain.merchant,
            connector="google_merchant_center",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=_unique(fact.evidence_id for fact in merchant_facts),
            metrics=merchant_facts[:8],
            human_diagnosis=(
                "Merchant Center ma realne metryki produktu/feedu w WILQ API. "
                f"{_metric_sentence(merchant_facts)}. To uzasadnia kolejkę review, "
                "ale nie automatyczną zmianę danych produktu."
            ),
            recommended_reason=(
                "Na /merchant pokaż produkty/feed jako prepare-only queue: sprawdź "
                "disapproved_products, przygotuj payload preview i walidację przed "
                "jakąkolwiek zmianą feedu."
            ),
            payload={
                "action_type": "merchant_feed_issue",
                "connector": "google_merchant_center",
                "mode": "prepare_only",
                "source_metric_names": _unique(fact.name for fact in merchant_facts),
                "review_steps": [
                    "identify_disapproved_products",
                    "group_issue_reasons",
                    "prepare_feed_fix_preview",
                    "require_human_confirm_before_apply",
                ],
                "destructive": False,
            },
            validation_status="not_validated",
            created_by="system_metric_seed",
        )
        actions[action.id] = action

    ga4_facts = by_connector.get("google_analytics_4", [])
    if ga4_facts:
        action = ActionObject(
            id="act_review_ga4_tracking_quality",
            title="Sprawdź jakość pomiaru GA4 przed oceną kampanii",
            domain=OpportunityDomain.ga4,
            connector="google_analytics_4",
            mode=ActionMode.prepare,
            risk=ActionRisk.low,
            status=ActionStatus.needs_validation,
            evidence_ids=_unique(fact.evidence_id for fact in ga4_facts),
            metrics=ga4_facts[:8],
            human_diagnosis=(
                "GA4 zwraca realne metryki ruchu, ale bieżący brief nie ma jeszcze "
                f"dowodu konwersji ani ścieżki landing page. {_metric_sentence(ga4_facts)}."
            ),
            recommended_reason=(
                "Na /ga4 przygotuj tracking-gap review: pokaż sessions/active_users, "
                "oznacz brak konwersji jako blocker i nie oceniaj jakości kampanii bez "
                "landing/source/campaign breakdown."
            ),
            payload={
                "action_type": "ga4_tracking_gap",
                "connector": "google_analytics_4",
                "mode": "prepare_only",
                "source_metric_names": _unique(fact.name for fact in ga4_facts),
                "required_breakdowns": ["landing_page", "source_medium", "campaign"],
                "blocked_claims": ["conversion_rate", "revenue", "roas"],
                "destructive": False,
            },
            validation_status="not_validated",
            created_by="system_metric_seed",
        )
        actions[action.id] = action

    content_facts = [
        *by_connector.get("wordpress_ekologus", []),
        *by_connector.get("google_search_console", []),
        *by_connector.get("ahrefs", []),
    ]
    if content_facts and by_connector.get("wordpress_ekologus"):
        action = ActionObject(
            id="act_prepare_content_refresh_queue",
            title="Przygotuj kolejkę odświeżenia treści ekologus.pl",
            domain=OpportunityDomain.content,
            connector="wordpress_ekologus",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=_unique(fact.evidence_id for fact in content_facts),
            metrics=content_facts[:10],
            human_diagnosis=(
                "WordPress inventory istnieje w WILQ API i można go zestawić z GSC/Ahrefs, "
                "żeby planować refresh zamiast duplikować treści. "
                f"{_metric_sentence(content_facts)}."
            ),
            recommended_reason=(
                "Na /content-planner przygotuj queue refresh/create/merge/block. "
                "Nie twórz nowych tematów bez query/page evidence i sprawdzenia inventory."
            ),
            payload={
                "action_type": "wordpress_content_refresh",
                "connector": "wordpress_ekologus",
                "mode": "prepare_only",
                "source_connectors": _unique(fact.source_connector for fact in content_facts),
                "source_metric_names": _unique(fact.name for fact in content_facts),
                "queue_steps": [
                    "join_wordpress_inventory_with_gsc",
                    "classify_refresh_create_merge_block",
                    "prepare_brief_preview",
                    "require_human_confirm_before_wordpress_write",
                ],
                "destructive": False,
            },
            validation_status="not_validated",
            created_by="system_metric_seed",
        )
        actions[action.id] = action

    return actions


def _facts_by_connector(facts: list[MetricFact]) -> dict[str, list[MetricFact]]:
    grouped: dict[str, list[MetricFact]] = {}
    for fact in facts:
        grouped.setdefault(fact.source_connector, []).append(fact)
    return grouped


def _metric_sentence(facts: list[MetricFact]) -> str:
    sample = ", ".join(f"{fact.name}={fact.value}" for fact in facts[:4])
    return f"Najważniejsze fakty: {sample}"


def _is_probe_only_fact(fact: MetricFact) -> bool:
    if (
        fact.source_connector == "localo"
        and fact.name == "api"
        and fact.value == "localo_mcp_oauth_probe"
    ):
        return True
    return fact.source_connector == "localo" and fact.name in {
        "access_token_present",
        "authorization_code_supported",
        "pkce_s256_supported",
        "mcp_initialize_status",
    }


def _unique(items: Iterable[str]) -> list[str]:
    unique_items: list[str] = []
    for item in items:
        if item and item not in unique_items:
            unique_items.append(item)
    return unique_items


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
