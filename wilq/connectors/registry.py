from __future__ import annotations

from dataclasses import dataclass

from wilq.access_pack.manifest import credential_file_names, variable_available
from wilq.schemas import ConnectorCapability, ConnectorStatus, ConnectorStatusValue, FreshnessState


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


CONNECTOR_DEFINITIONS: tuple[ConnectorDefinition, ...] = (
    ConnectorDefinition(
        "google_ads",
        "Google Ads",
        (
            "GOOGLE_ADS_DEVELOPER_TOKEN",
            "GOOGLE_ADS_CLIENT_ID",
            "GOOGLE_ADS_CLIENT_SECRET",
            "GOOGLE_ADS_REFRESH_TOKEN",
            "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
        ),
        True,
        True,
        (
            "negative_keyword_candidate",
            "campaign_change_review",
            "demand_gen_migration_plan",
            "custom_segment_candidate",
        ),
        "Google Ads API quotas and mutate limits apply.",
        "External API usage may consume Google Ads API quota.",
        "Write actions can affect paid media spend and must be validated.",
        "credential_presence",
    ),
    ConnectorDefinition(
        "google_search_console",
        "Google Search Console",
        ("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_SEARCH_CONSOLE_SITE_URL"),
        True,
        False,
        ("gsc_content_opportunity",),
        "Search Analytics API query limits apply.",
        "No direct API cost expected; quota-limited.",
        "Read-only SEO diagnostics.",
        "credential_presence",
    ),
    ConnectorDefinition(
        "google_analytics_4",
        "Google Analytics 4",
        ("GOOGLE_APPLICATION_CREDENTIALS", "GA4_PROPERTY_ID"),
        True,
        False,
        ("ga4_landing_page_issue", "ga4_tracking_gap"),
        "GA4 Data API quotas apply.",
        "No direct API cost expected; quota-limited.",
        "Measurement gaps must not be misreported as marketing failures.",
        "credential_presence",
    ),
    ConnectorDefinition(
        "google_merchant_center",
        "Google Merchant Center",
        ("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_MERCHANT_CENTER_ACCOUNT_ID"),
        True,
        True,
        ("merchant_feed_issue", "product_feed_edit_candidate"),
        "Merchant API quotas apply.",
        "No direct API cost expected; quota-limited.",
        "Feed writes can affect product visibility and must preserve factual attributes.",
        "credential_presence",
    ),
    ConnectorDefinition(
        "google_sheets",
        "Google Sheets",
        ("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_SHEETS_REVIEW_SPREADSHEET_ID"),
        True,
        True,
        ("export_review_sheet", "import_reviewed_bulk_edits"),
        "Sheets API quotas apply.",
        "No direct API cost expected; quota-limited.",
        "Sheets is collaboration surface, not source of truth.",
        "credential_presence",
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
        "Read-only competitive intelligence.",
        "credential_presence",
    ),
    ConnectorDefinition(
        "localo",
        "Localo",
        ("LOCALO_API_TOKEN",),
        True,
        True,
        ("local_visibility_task", "gbp_post_candidate"),
        "Localo API/MCP limits apply.",
        "Depends on Localo subscription.",
        "Local visibility writes must be audited.",
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
        ("wordpress_content_refresh", "wordpress_draft_update"),
        "WordPress REST API rate limits depend on hosting.",
        "No direct API cost expected.",
        "Content writes can publish client-facing changes.",
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
        "Shop content writes can affect product claims.",
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
        "Publishing requires organization permission and human review.",
        "credential_presence",
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
        "Publishing requires Page permission and human review.",
        "credential_presence",
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
        "Runtime cannot bypass evidence/action validation.",
        "runtime_presence",
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


def connector_status(definition: ConnectorDefinition) -> ConnectorStatus:
    missing = [name for name in definition.required_env if not _credential_available(name)]
    configured = not missing
    return ConnectorStatus(
        id=definition.id,
        label=definition.label,
        status=ConnectorStatusValue.configured
        if configured
        else ConnectorStatusValue.missing_credentials,
        configured=configured,
        missing_credentials=missing,
        error=None,
        freshness=FreshnessState(
            state="unknown" if configured else "missing",
            notes="Credential presence only; no external API call was made.",
        ),
        capabilities=ConnectorCapability(
            read=definition.read,
            write=definition.write,
            operations=list(definition.supported_actions),
        ),
        required_env=list(definition.required_env),
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
