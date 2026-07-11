from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

from wilq.connectors.google_auth import (
    GOOGLE_CREDENTIAL_ENV_NAMES,
    google_credentials_available,
    google_credentials_diagnostic,
)
from wilq.credentials.runtime import (
    credential_file_names,
    credential_source_summary,
    variable_available,
)
from wilq.schemas import (
    ConnectorCapability,
    ConnectorProductScope,
    ConnectorRefreshJobState,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshState,
    ConnectorRefreshStatus,
    ConnectorStatus,
    ConnectorStatusValue,
    FreshnessState,
    connector_refresh_has_live_data,
    utc_now,
)
from wilq.storage.local_state import local_state_store

CONNECTOR_FRESH_AFTER_HOURS = 48


@dataclass(frozen=True)
class ConnectorDefinition:
    id: str
    label: str
    required_env: tuple[str, ...]
    read: bool
    write: bool
    supported_actions: tuple[str, ...]
    rate_limit_notes: str
    cost_notes: str
    risk_notes: str
    health_check: str
    required_credential_groups: tuple[tuple[str, ...], ...] = ()
    enabled: bool = True
    product_scope: ConnectorProductScope = ConnectorProductScope.production
    active_for_daily_work: bool = True


CONNECTOR_DEFINITIONS: tuple[ConnectorDefinition, ...] = (
    ConnectorDefinition(
        "google_ads",
        "Google Ads",
        (
            "GOOGLE_ADS_DEVELOPER_TOKEN",
            "GOOGLE_ADS_CLIENT_ID",
            "GOOGLE_ADS_CLIENT_SECRET",
            "GOOGLE_ADS_REFRESH_TOKEN",
            "GOOGLE_ADS_CUSTOMER_ID",
            "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
        ),
        True,
        True,
        (
            "negative_keyword_candidate",
            "campaign_change_review",
            "google_ads_recommendation_review",
            "google_ads_change_history_impact_review",
            "google_ads_search_term_ngram_review",
            "google_ads_demand_gen_readiness_review",
            "demand_gen_mode_review_plan",
            "custom_segment_candidate",
        ),
        "Google Ads API quotas and mutate limits apply.",
        "External API usage may consume Google Ads API quota.",
        "Zapis zmian może wpływać na wydatki reklamowe i wymaga walidacji.",
        "credential_presence",
    ),
    ConnectorDefinition(
        "google_search_console",
        "Google Search Console",
        ("GOOGLE_SEARCH_CONSOLE_SITE_URL",),
        True,
        False,
        ("gsc_content_opportunity",),
        "Search Analytics API query limits apply.",
        "No direct API cost expected; quota-limited.",
        "Tylko odczyt do diagnostyki SEO i contentu; nie służy do publikacji ani zapisu zmian.",
        "credential_presence",
        (GOOGLE_CREDENTIAL_ENV_NAMES,),
    ),
    ConnectorDefinition(
        "google_analytics_4",
        "Google Analytics 4",
        ("GA4_PROPERTY_ID",),
        True,
        False,
        ("ga4_landing_page_issue", "ga4_tracking_gap"),
        "GA4 Data API quotas apply.",
        "No direct API cost expected; quota-limited.",
        "Braki pomiaru nie mogą być raportowane jako porażka kampanii, strony ani SEO.",
        "credential_presence",
        (GOOGLE_CREDENTIAL_ENV_NAMES,),
    ),
    ConnectorDefinition(
        "google_merchant_center",
        "Google Merchant Center",
        ("GOOGLE_MERCHANT_CENTER_ACCOUNT_ID",),
        True,
        True,
        ("merchant_feed_issue", "product_feed_edit_candidate"),
        "Merchant API quotas apply.",
        "No direct API cost expected; quota-limited.",
        "Zmiany feedu mogą wpływać na widoczność produktów i wymagają zachowania faktów.",
        "credential_presence",
        (GOOGLE_CREDENTIAL_ENV_NAMES,),
    ),
    ConnectorDefinition(
        "google_sheets",
        "Google Sheets",
        ("GOOGLE_SHEETS_REVIEW_SPREADSHEET_ID",),
        True,
        True,
        ("export_review_sheet", "import_reviewed_bulk_edits"),
        "Sheets API quotas apply.",
        "No direct API cost expected; quota-limited.",
        (
            "Opcjonalny eksport/współpraca, nie źródło prawdy. Wyłączone w aktualnym "
            "zakresie Ekologus, dopóki nie wrócą workflowy arkuszy do review."
        ),
        "disabled_optional",
        (GOOGLE_CREDENTIAL_ENV_NAMES,),
        False,
        ConnectorProductScope.optional_disabled,
        False,
    ),
    ConnectorDefinition(
        "ahrefs",
        "Ahrefs",
        ("AHREFS_API_TOKEN",),
        True,
        False,
        ("content_gap", "backlink_gap", "competitor_gap"),
        "Ahrefs API plan and endpoint limits apply.",
        "May consume paid Ahrefs API credits.",
        "Tylko odczyt kontekstu konkurencji; Ahrefs nie zastępuje GSC, WordPress ani claim gate.",
        "credential_presence",
    ),
    ConnectorDefinition(
        "localo",
        "Localo",
        ("LOCALO_API_TOKEN", "LOCALO_ORGANIZATION_ID", "LOCALO_ACCESS_TOKEN"),
        True,
        True,
        ("local_visibility_task", "gbp_post_candidate"),
        "Localo API/MCP limits apply.",
        "Depends on Localo subscription.",
        (
            "Localo jest źródłem gotowości i lokalnego kontekstu; sam dostęp nie "
            "potwierdza rankingów, zapisu GBP ani poprawy widoczności."
        ),
        "credential_presence",
    ),
    ConnectorDefinition(
        "wordpress_ekologus",
        "WordPress ekologus.pl",
        (
            "WORDPRESS_EKOLOGUS_URL",
            "WORDPRESS_EKOLOGUS_USERNAME",
            "WORDPRESS_EKOLOGUS_APP_PASSWORD",
        ),
        True,
        True,
        (
            "wordpress_content_refresh",
            "wordpress_draft_update",
            "wordpress_draft_handoff",
            "service_profile_knowledge_promotion_review",
            "service_profile_private_proposal_promotion_review",
        ),
        "WordPress REST API rate limits depend on hosting.",
        "No direct API cost expected.",
        (
            "WordPress ekologus.pl służy do inventory i przekazania szkicu; "
            "publikacja i destrukcyjne aktualizacje pozostają zablokowane poza "
            "osobnym modelem review/audit."
        ),
        "credential_presence",
    ),
    ConnectorDefinition(
        "wordpress_sklep",
        "WordPress sklep.ekologus.pl",
        (
            "WORDPRESS_SKLEP_URL",
            "WORDPRESS_SKLEP_USERNAME",
            "WORDPRESS_SKLEP_APP_PASSWORD",
        ),
        True,
        True,
        ("product_content_refresh", "product_draft_update"),
        "WordPress REST API rate limits depend on hosting.",
        "No direct API cost expected.",
        (
            "WordPress sklepu służy do inventory i pracy na szkicach produktowych; "
            "publikacja i nadpisywanie wymagają osobnego modelu review/audit."
        ),
        "credential_presence",
    ),
    ConnectorDefinition(
        "linkedin",
        "LinkedIn",
        ("LINKEDIN_ORGANIZATION_ID", "LINKEDIN_ACCESS_TOKEN"),
        True,
        True,
        ("linkedin_post_candidate",),
        "LinkedIn API permissions and organization roles apply.",
        "No direct API cost expected.",
        (
            "Social publishing jest poza bieżącym content workflow; wymaga osobnych "
            "uprawnień, review i akcji publikacji."
        ),
        "credential_presence",
        product_scope=ConnectorProductScope.experimental,
        active_for_daily_work=False,
    ),
    ConnectorDefinition(
        "facebook",
        "Facebook Pages",
        ("FACEBOOK_PAGE_ID", "FACEBOOK_PAGE_ACCESS_TOKEN"),
        True,
        True,
        ("facebook_post_candidate",),
        "Meta API permissions and app review apply.",
        "No direct API cost expected.",
        (
            "Social publishing jest poza bieżącym content workflow; wymaga osobnych "
            "uprawnień, review i akcji publikacji."
        ),
        "credential_presence",
        product_scope=ConnectorProductScope.experimental,
        active_for_daily_work=False,
    ),
    ConnectorDefinition(
        "openai_codex",
        "OpenAI Codex Runtime",
        ("CODEX_API_KEY",),
        True,
        False,
        ("codex_context_pack", "codex_exec_schema_smoke"),
        "Codex usage limits and model/runtime availability apply.",
        "May consume OpenAI/Codex credits depending on auth path.",
        "Runtime operatorski nie jest produkcyjnym autorem treści i nie omija WILQ API.",
        "runtime_presence",
        product_scope=ConnectorProductScope.runtime,
        active_for_daily_work=False,
    ),
)

CONNECTOR_IDS = tuple(connector.id for connector in CONNECTOR_DEFINITIONS)
_DEFINITIONS_BY_ID = {connector.id: connector for connector in CONNECTOR_DEFINITIONS}


def _credential_available(name: str) -> bool:
    if variable_available(name):
        return True
    if name == "GOOGLE_APPLICATION_CREDENTIALS":
        return bool(credential_file_names())
    return False


def _required_credential_names(definition: ConnectorDefinition) -> list[str]:
    names = list(definition.required_env)
    for group in definition.required_credential_groups:
        for name in group:
            if name not in names:
                names.append(name)
    return names


def _credential_group_available(group: tuple[str, ...]) -> bool:
    if group == GOOGLE_CREDENTIAL_ENV_NAMES:
        return google_credentials_available()
    return any(_credential_available(name) for name in group)


def _missing_credential_groups(definition: ConnectorDefinition) -> list[str]:
    missing: list[str] = []
    for group in definition.required_credential_groups:
        if not _credential_group_available(group):
            missing.append("|".join(group))
    return missing


def _connector_error(missing: list[str]) -> str | None:
    if "|".join(GOOGLE_CREDENTIAL_ENV_NAMES) in missing:
        diagnostic = google_credentials_diagnostic()
        if diagnostic == "missing_google_credentials":
            return "Google credentials are missing."
        return f"Google credentials are invalid: {diagnostic}."
    return None


def connector_status(definition: ConnectorDefinition) -> ConnectorStatus:
    required_names = _required_credential_names(definition)
    if not definition.enabled:
        return ConnectorStatus(
            id=definition.id,
            label=definition.label,
            status=ConnectorStatusValue.disabled,
            product_scope=definition.product_scope,
            active_for_daily_work=definition.active_for_daily_work,
            configured=False,
            missing_credentials=[],
            available_credential_sources=credential_source_summary(required_names),
            error="Connector disabled by current product scope.",
            freshness=FreshnessState(
                state="missing",
                notes="Optional connector disabled by current Ekologus operator scope.",
            ),
            refresh_state=_connector_refresh_state(
                connector_id=definition.id,
                configured=False,
                read=definition.read,
                freshness_state="missing",
                missing_credentials=[],
            ),
            capabilities=ConnectorCapability(
                read=definition.read,
                write=definition.write,
                operations=list(definition.supported_actions),
            ),
            required_env=required_names,
            supported_actions=list(definition.supported_actions),
            rate_limit_notes=definition.rate_limit_notes,
            cost_notes=definition.cost_notes,
            risk_notes=definition.risk_notes,
            health_check=definition.health_check,
        )
    missing = [
        name for name in definition.required_env if not _credential_available(name)
    ] + _missing_credential_groups(definition)
    configured = not missing
    latest_success = _latest_successful_vendor_read(definition.id) if configured else None
    latest_incomplete = _latest_incomplete_vendor_read(definition.id) if configured else None
    freshness = _connector_freshness(
        configured=configured,
        latest_success=latest_success,
        latest_incomplete=latest_incomplete,
    )
    return ConnectorStatus(
        id=definition.id,
        label=definition.label,
        status=ConnectorStatusValue.configured
        if configured
        else ConnectorStatusValue.missing_credentials,
        product_scope=definition.product_scope,
        active_for_daily_work=definition.active_for_daily_work,
        configured=configured,
        missing_credentials=missing,
        available_credential_sources=credential_source_summary(required_names),
        error=_connector_error(missing),
        last_success_at=latest_success.completed_at if latest_success else None,
        freshness=freshness,
        refresh_state=_connector_refresh_state(
            connector_id=definition.id,
            configured=configured,
            read=definition.read,
            freshness_state=freshness.state,
            missing_credentials=missing,
        ),
        capabilities=ConnectorCapability(
            read=definition.read,
            write=definition.write,
            operations=list(definition.supported_actions),
        ),
        required_env=required_names,
        supported_actions=list(definition.supported_actions),
        rate_limit_notes=definition.rate_limit_notes,
        cost_notes=definition.cost_notes,
        risk_notes=definition.risk_notes,
        health_check=definition.health_check,
    )


def list_connector_statuses() -> list[ConnectorStatus]:
    return [connector_status(definition) for definition in CONNECTOR_DEFINITIONS]


def get_connector_status(connector_id: str) -> ConnectorStatus | None:
    definition = _DEFINITIONS_BY_ID.get(connector_id)
    if definition is None:
        return None
    return connector_status(definition)


def _latest_successful_vendor_read(connector_id: str) -> ConnectorRefreshRun | None:
    for run in local_state_store().list_connector_refresh_runs(connector_id=connector_id):
        if run.mode == ConnectorRefreshMode.vendor_read and connector_refresh_has_live_data(run):
            return run
    return None


def _latest_vendor_read(connector_id: str) -> ConnectorRefreshRun | None:
    for run in local_state_store().list_connector_refresh_runs(connector_id=connector_id):
        if run.mode == ConnectorRefreshMode.vendor_read:
            return run
    return None


def _connector_refresh_state(
    *,
    connector_id: str,
    configured: bool,
    read: bool,
    freshness_state: str,
    missing_credentials: list[str],
) -> ConnectorRefreshState:
    latest_run = _latest_vendor_read(connector_id) if configured else None
    refresh_allowed = configured and read and not missing_credentials
    affected_decisions = {
        "google_analytics_4": ["ga4_diagnostics", "command_center"],
        "google_merchant_center": ["merchant_diagnostics", "command_center"],
        "google_ads": ["ads_diagnostics", "command_center"],
    }.get(connector_id, ["command_center"])
    if latest_run is None:
        state = (
            ConnectorRefreshJobState.stale
            if freshness_state == "stale"
            else ConnectorRefreshJobState.unknown
        )
    elif latest_run.status == ConnectorRefreshStatus.failed:
        state = ConnectorRefreshJobState.failed
    elif latest_run.status == ConnectorRefreshStatus.blocked:
        state = ConnectorRefreshJobState.blocked
    elif not latest_run.metrics_persisted or not latest_run.vendor_data_collected:
        state = ConnectorRefreshJobState.partial
    elif freshness_state == "stale":
        state = ConnectorRefreshJobState.stale
    else:
        state = ConnectorRefreshJobState.ready
    labels = {
        ConnectorRefreshJobState.ready: "odświeżone",
        ConnectorRefreshJobState.stale: "wymaga odświeżenia",
        ConnectorRefreshJobState.partial: "odczyt częściowy",
        ConnectorRefreshJobState.failed: "odświeżenie nieudane",
        ConnectorRefreshJobState.blocked: "odczyt zablokowany",
        ConnectorRefreshJobState.unknown: "stan odświeżenia nieznany",
    }
    next_steps = {
        ConnectorRefreshJobState.ready: (
            "Źródło ma ostatni udany odczyt; użyj go zgodnie ze świeżością."
        ),
        ConnectorRefreshJobState.stale: (
            "Uruchom bezpieczny odczyt źródła przed wnioskiem z danych."
        ),
        ConnectorRefreshJobState.partial: (
            "Odczyt nie utrwalił pełnych metryk; odśwież ponownie przed decyzją."
        ),
        ConnectorRefreshJobState.failed: (
            "Sprawdź ostatni odczyt i uruchom go ponownie po usunięciu błędu."
        ),
        ConnectorRefreshJobState.blocked: (
            "Usuń blocker dostępu lub konfiguracji, potem uruchom odczyt ponownie."
        ),
        ConnectorRefreshJobState.unknown: "Uruchom bezpieczny odczyt, aby potwierdzić stan źródła.",
    }
    return ConnectorRefreshState(
        state=state,
        state_label=labels[state],
        refresh_allowed=refresh_allowed,
        last_run_id=latest_run.id if latest_run is not None else None,
        last_run_status=latest_run.status if latest_run is not None else None,
        last_run_started_at=latest_run.started_at if latest_run is not None else None,
        last_run_completed_at=latest_run.completed_at if latest_run is not None else None,
        safe_next_step=next_steps[state],
        affected_decisions=affected_decisions,
    )


def _latest_incomplete_vendor_read(connector_id: str) -> ConnectorRefreshRun | None:
    for run in local_state_store().list_connector_refresh_runs(connector_id=connector_id):
        if (
            run.mode == ConnectorRefreshMode.vendor_read
            and run.status == ConnectorRefreshStatus.completed
            and run.vendor_data_collected
            and not run.metrics_persisted
        ):
            return run
    return None


def _connector_freshness(
    *,
    configured: bool,
    latest_success: ConnectorRefreshRun | None,
    latest_incomplete: ConnectorRefreshRun | None,
) -> FreshnessState:
    if not configured:
        return FreshnessState(
            state="missing",
            notes="Brakuje dostępu do źródła danych.",
        )
    if latest_success is None and latest_incomplete is not None:
        incomplete_at = latest_incomplete.completed_at or latest_incomplete.started_at
        return FreshnessState(
            state="unknown",
            notes=(
                "Ostatni odczyt danych zewnętrznych jest niepełny - metryki nieutrwalone. "
                f"Czas odczytu: {incomplete_at.isoformat()}. Uruchom odczyt ponownie przed "
                "wnioskami z metryk."
            ),
        )
    if latest_success is None:
        return FreshnessState(
            state="unknown",
            notes=(
                "Dostęp jest skonfigurowany, ale WILQ nie ma jeszcze udanego "
                "odczytu danych zewnętrznych."
            ),
        )
    completed_at = latest_success.completed_at
    if completed_at is None:
        return FreshnessState(
            state="unknown",
            notes="WILQ ma odczyt źródła danych bez czasu zakończenia.",
        )
    age = utc_now() - completed_at
    state: Literal["fresh", "stale"] = (
        "fresh" if age <= timedelta(hours=CONNECTOR_FRESH_AFTER_HOURS) else "stale"
    )
    freshness_label = "świeży" if state == "fresh" else "do odświeżenia"
    return FreshnessState(
        state=state,
        last_success_at=completed_at,
        notes=(
            f"Ostatni udany odczyt danych zewnętrznych: {completed_at.isoformat()}; "
            f"status: {freshness_label}."
        ),
    )
