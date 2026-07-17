from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

from wilq.codex.runtime_status import codex_local_runtime_readiness
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
    ConnectorRefreshTriggerPolicy,
    ConnectorRefreshTriggerReason,
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
    read_adapter: str | None = None
    mutation_adapter: str | None = None

    def __post_init__(self) -> None:
        if self.read != (self.read_adapter is not None):
            raise ValueError(f"Connector {self.id} read capability does not match its adapter")
        if self.write != (self.mutation_adapter is not None):
            raise ValueError(f"Connector {self.id} write capability does not match its adapter")


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
        False,
        (
            "negative_keyword_candidate",
            "campaign_change_review",
            "google_ads_recommendation_review",
            "google_ads_change_history_impact_review",
            "google_ads_search_term_ngram_review",
            "google_ads_demand_gen_readiness_review",
            "custom_segment_candidate",
        ),
        "Google Ads API quotas and mutate limits apply.",
        "External API usage may consume Google Ads API quota.",
        "Akcje Ads służą obecnie wyłącznie do przygotowania i sprawdzenia; "
        "brak adaptera zapisu do Google Ads.",
        "credential_presence",
        read_adapter="google_ads_api",
    ),
    ConnectorDefinition(
        "google_search_console",
        "Google Search Console",
        ("GOOGLE_SEARCH_CONSOLE_SITE_URL",),
        True,
        False,
        (),
        "Search Analytics API query limits apply.",
        "No direct API cost expected; quota-limited.",
        "Tylko odczyt do diagnostyki SEO i contentu; nie służy do publikacji ani zapisu zmian.",
        "credential_presence",
        (GOOGLE_CREDENTIAL_ENV_NAMES,),
        read_adapter="search_console_api",
    ),
    ConnectorDefinition(
        "google_analytics_4",
        "Google Analytics 4",
        ("GA4_PROPERTY_ID",),
        True,
        False,
        ("ga4_tracking_gap",),
        "GA4 Data API quotas apply.",
        "No direct API cost expected; quota-limited.",
        "Braki pomiaru nie mogą być raportowane jako porażka kampanii, strony ani SEO.",
        "credential_presence",
        (GOOGLE_CREDENTIAL_ENV_NAMES,),
        read_adapter="ga4_data_api",
    ),
    ConnectorDefinition(
        "google_merchant_center",
        "Google Merchant Center",
        ("GOOGLE_MERCHANT_CENTER_ACCOUNT_ID",),
        True,
        False,
        ("merchant_feed_issue",),
        "Merchant API quotas apply.",
        "No direct API cost expected; quota-limited.",
        "WILQ przygotowuje wyłącznie sprawdzenie problemów feedu; brak adaptera jego zmian.",
        "credential_presence",
        (GOOGLE_CREDENTIAL_ENV_NAMES,),
        read_adapter="merchant_api",
    ),
    ConnectorDefinition(
        "google_sheets",
        "Google Sheets",
        ("GOOGLE_SHEETS_REVIEW_SPREADSHEET_ID",),
        True,
        False,
        (),
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
        read_adapter="sheets_api",
    ),
    ConnectorDefinition(
        "ahrefs",
        "Ahrefs",
        ("AHREFS_API_TOKEN",),
        True,
        False,
        (),
        "Ahrefs API plan and endpoint limits apply.",
        "May consume paid Ahrefs API credits.",
        "Tylko odczyt kontekstu konkurencji; Ahrefs nie zastępuje GSC, WordPress ani claim gate.",
        "credential_presence",
        read_adapter="ahrefs_api",
    ),
    ConnectorDefinition(
        "localo",
        "Localo",
        ("LOCALO_API_TOKEN", "LOCALO_ORGANIZATION_ID", "LOCALO_ACCESS_TOKEN"),
        True,
        False,
        ("local_visibility_task",),
        "Localo API/MCP limits apply.",
        "Depends on Localo subscription.",
        (
            "Localo jest źródłem gotowości i lokalnego kontekstu; sam dostęp nie "
            "potwierdza rankingów ani poprawy widoczności, a zapis GBP nie ma adaptera."
        ),
        "credential_presence",
        read_adapter="localo_mcp_oauth",
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
        read_adapter="wordpress_rest_api",
        mutation_adapter="wordpress_draft_execution_boundary",
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
        False,
        (),
        "WordPress REST API rate limits depend on hosting.",
        "No direct API cost expected.",
        (
            "WordPress sklepu służy obecnie wyłącznie do odczytu inventory; "
            "brak adaptera szkicu, publikacji i nadpisywania produktów."
        ),
        "credential_presence",
        read_adapter="wordpress_rest_api",
    ),
    ConnectorDefinition(
        "linkedin",
        "LinkedIn",
        ("LINKEDIN_ORGANIZATION_ID", "LINKEDIN_ACCESS_TOKEN"),
        False,
        False,
        ("linkedin_post_candidate",),
        "LinkedIn API permissions and organization roles apply.",
        "No direct API cost expected.",
        (
            "WILQ przygotowuje propozycje z własnych dowodów; brak adaptera odczytu "
            "LinkedIn i publikacji w tym kanale."
        ),
        "credential_presence",
        product_scope=ConnectorProductScope.experimental,
        active_for_daily_work=False,
    ),
    ConnectorDefinition(
        "facebook",
        "Facebook Pages",
        ("FACEBOOK_PAGE_ID", "FACEBOOK_PAGE_ACCESS_TOKEN"),
        False,
        False,
        ("facebook_post_candidate",),
        "Meta API permissions and app review apply.",
        "No direct API cost expected.",
        (
            "WILQ przygotowuje propozycje z własnych dowodów; brak adaptera odczytu "
            "Facebooka i publikacji w tym kanale."
        ),
        "credential_presence",
        product_scope=ConnectorProductScope.experimental,
        active_for_daily_work=False,
    ),
    ConnectorDefinition(
        "openai_codex",
        "OpenAI Codex Runtime",
        (),
        True,
        False,
        (),
        "Codex usage limits and model/runtime availability apply.",
        "May consume OpenAI/Codex credits depending on auth path.",
        "Runtime operatorski nie jest produkcyjnym autorem treści i nie omija WILQ API.",
        "local_codex_login",
        product_scope=ConnectorProductScope.runtime,
        active_for_daily_work=False,
        read_adapter="codex_local_runtime_status",
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


def _connector_capability(definition: ConnectorDefinition) -> ConnectorCapability:
    if not definition.enabled:
        action_scope: Literal["read_only", "review_only", "draft_only", "disabled"] = (
            "disabled"
        )
    elif definition.mutation_adapter is not None:
        action_scope = "draft_only"
    elif definition.supported_actions:
        action_scope = "review_only"
    else:
        action_scope = "read_only"
    blockers = (
        ["vendor_write_not_implemented"]
        if definition.supported_actions and definition.mutation_adapter is None
        else []
    )
    return ConnectorCapability(
        read=definition.read,
        write=definition.write,
        read_adapter=definition.read_adapter,
        mutation_adapter=definition.mutation_adapter,
        action_scope=action_scope,
        blockers=blockers,
        operations=list(definition.supported_actions),
    )


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
            capabilities=_connector_capability(definition),
            required_env=required_names,
            supported_actions=list(definition.supported_actions),
            rate_limit_notes=definition.rate_limit_notes,
            cost_notes=definition.cost_notes,
            risk_notes=definition.risk_notes,
            health_check=definition.health_check,
        )
    if definition.id == "openai_codex":
        return _codex_connector_status(definition)
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
        capabilities=_connector_capability(definition),
        required_env=required_names,
        supported_actions=list(definition.supported_actions),
        rate_limit_notes=definition.rate_limit_notes,
        cost_notes=definition.cost_notes,
        risk_notes=definition.risk_notes,
        health_check=definition.health_check,
    )


def _codex_connector_status(definition: ConnectorDefinition) -> ConnectorStatus:
    readiness = codex_local_runtime_readiness()
    configured = readiness.status == "ready"
    status = {
        "ready": ConnectorStatusValue.configured,
        "missing_cli": ConnectorStatusValue.missing_dependency,
        "missing_login": ConnectorStatusValue.auth_error,
    }[readiness.status]
    freshness = FreshnessState(
        state="unknown",
        notes="Stan lokalnego runtime'u; nie jest dowodem ani źródłem metryk marketingowych.",
    )
    return ConnectorStatus(
        id=definition.id,
        label=definition.label,
        status=status,
        product_scope=definition.product_scope,
        active_for_daily_work=definition.active_for_daily_work,
        configured=configured,
        missing_credentials=[],
        available_credential_sources=["local_codex_login"] if configured else [],
        error=readiness.blocker_label,
        freshness=freshness,
        refresh_state=_connector_refresh_state(
            connector_id=definition.id,
            configured=configured,
            read=False,
            freshness_state=freshness.state,
            missing_credentials=[],
        ),
        capabilities=_connector_capability(definition),
        required_env=[],
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
    elif latest_run.status == ConnectorRefreshStatus.queued:
        state = ConnectorRefreshJobState.queued
    elif latest_run.status == ConnectorRefreshStatus.running:
        state = ConnectorRefreshJobState.running
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
    if state in {ConnectorRefreshJobState.queued, ConnectorRefreshJobState.running}:
        refresh_allowed = False
    labels = {
        ConnectorRefreshJobState.queued: "odczyt w kolejce",
        ConnectorRefreshJobState.running: "odczyt trwa",
        ConnectorRefreshJobState.ready: "odświeżone",
        ConnectorRefreshJobState.stale: "wymaga odświeżenia",
        ConnectorRefreshJobState.partial: "odczyt częściowy",
        ConnectorRefreshJobState.failed: "odświeżenie nieudane",
        ConnectorRefreshJobState.blocked: "odczyt zablokowany",
        ConnectorRefreshJobState.unknown: "stan odświeżenia nieznany",
    }
    next_steps = {
        ConnectorRefreshJobState.queued: "Odczyt jest w kolejce; poczekaj na wynik przed decyzją.",
        ConnectorRefreshJobState.running: "Odczyt trwa; poczekaj na wynik przed decyzją.",
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
    automatic_refresh = _connector_refresh_trigger_policy(
        configured=configured,
        read=read,
        missing_credentials=missing_credentials,
        state=state,
        latest_run=latest_run,
    )
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
        automatic_refresh=automatic_refresh,
    )


def _connector_refresh_trigger_policy(
    *,
    configured: bool,
    read: bool,
    missing_credentials: list[str],
    state: ConnectorRefreshJobState,
    latest_run: ConnectorRefreshRun | None,
) -> ConnectorRefreshTriggerPolicy:
    cooldown_seconds = 900
    reason: ConnectorRefreshTriggerReason
    if missing_credentials:
        reason = ConnectorRefreshTriggerReason.missing_credentials
    elif not configured:
        reason = ConnectorRefreshTriggerReason.not_configured
    elif not read:
        reason = ConnectorRefreshTriggerReason.read_unavailable
    elif state in {ConnectorRefreshJobState.queued, ConnectorRefreshJobState.running}:
        reason = ConnectorRefreshTriggerReason.active_run
    elif state == ConnectorRefreshJobState.partial:
        reason = ConnectorRefreshTriggerReason.partial_read
    elif state == ConnectorRefreshJobState.failed:
        reason = ConnectorRefreshTriggerReason.failed_read
    elif state == ConnectorRefreshJobState.blocked:
        reason = ConnectorRefreshTriggerReason.blocked_read
    elif state == ConnectorRefreshJobState.unknown:
        reason = ConnectorRefreshTriggerReason.unknown_state
    elif state != ConnectorRefreshJobState.stale:
        reason = ConnectorRefreshTriggerReason.not_stale
    elif latest_run is not None and latest_run.completed_at is not None:
        elapsed = utc_now() - latest_run.completed_at
        if elapsed < timedelta(seconds=cooldown_seconds):
            reason = ConnectorRefreshTriggerReason.cooldown
        else:
            reason = ConnectorRefreshTriggerReason.eligible_stale
    else:
        reason = ConnectorRefreshTriggerReason.eligible_stale
    labels = {
        ConnectorRefreshTriggerReason.eligible_stale: "Stare źródło kwalifikuje się do odczytu",
        ConnectorRefreshTriggerReason.not_stale: "Źródło nie wymaga automatycznego odczytu",
        ConnectorRefreshTriggerReason.active_run: "Odczyt źródła już trwa",
        ConnectorRefreshTriggerReason.cooldown: "Odczyt źródła był uruchomiony niedawno",
        ConnectorRefreshTriggerReason.missing_credentials: "Brakuje dostępu do źródła",
        ConnectorRefreshTriggerReason.not_configured: "Źródło nie jest skonfigurowane",
        ConnectorRefreshTriggerReason.read_unavailable: "Odczyt źródła jest niedostępny",
        ConnectorRefreshTriggerReason.partial_read: "Ostatni odczyt źródła był częściowy",
        ConnectorRefreshTriggerReason.failed_read: "Ostatni odczyt źródła zakończył się błędem",
        ConnectorRefreshTriggerReason.blocked_read: "Odczyt źródła jest zablokowany",
        ConnectorRefreshTriggerReason.unknown_state: "Stan źródła jest nieznany",
    }
    next_steps = {
        ConnectorRefreshTriggerReason.eligible_stale: "Można bezpiecznie zlecić read-only refresh.",
        ConnectorRefreshTriggerReason.not_stale: (
            "Użyj ostatniego odczytu zgodnie z jego świeżością."
        ),
        ConnectorRefreshTriggerReason.active_run: "Poczekaj na zakończenie aktywnego odczytu.",
        ConnectorRefreshTriggerReason.cooldown: (
            "Poczekaj do końca okna ochronnego przed kolejnym odczytem."
        ),
        ConnectorRefreshTriggerReason.missing_credentials: "Uzupełnij credentials przed odczytem.",
        ConnectorRefreshTriggerReason.not_configured: "Skonfiguruj źródło przed odczytem.",
        ConnectorRefreshTriggerReason.read_unavailable: "Pozostaw automatyczny odczyt wyłączony.",
        ConnectorRefreshTriggerReason.partial_read: (
            "Zweryfikuj częściowy odczyt i uruchom go ręcznie."
        ),
        ConnectorRefreshTriggerReason.failed_read: "Sprawdź błąd i uruchom odczyt po naprawie.",
        ConnectorRefreshTriggerReason.blocked_read: "Usuń blocker dostępu przed odczytem.",
        ConnectorRefreshTriggerReason.unknown_state: "Najpierw potwierdź stan źródła read-only.",
    }
    return ConnectorRefreshTriggerPolicy(
        eligible=reason == ConnectorRefreshTriggerReason.eligible_stale,
        reason=reason,
        reason_label=labels[reason],
        safe_next_step=next_steps[reason],
        cooldown_seconds=cooldown_seconds,
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
