from __future__ import annotations

from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import ActionMode, ActionObject, ActionRisk, ActionStatus, OpportunityDomain


def oauth_repair_action() -> ActionObject:
    return ActionObject(
        id="act_configure_google_ads_env",
        title="Odnow dostęp Google Ads",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=[connector_evidence_id("google_ads")],
        human_diagnosis=(
            "WILQ ma ustawienia dostępu Google Ads, ale obecny token odświeżania "
            "został odrzucony przez Google. Bez ponownej zgody WILQ nie może "
            "odczytać kampanii, wyszukiwanych haseł ani rekomendacji."
        ),
        recommended_reason=(
            "Uruchom ponowną zgodę na właściwym koncie Google operatora, potem "
            "odśwież dane Google Ads w WILQ."
        ),
        payload={
            "action_type": "repair_google_ads_oauth",
            "connector": "google_ads",
            "credential_source": "repo_env",
            "oauth_client_json_path": (
                "$WILQ_GOOGLE_ADS_CLIENT_SECRET_FILE albo lokalna ścieżka do "
                "OAuth desktop client JSON"
            ),
            "oauth_scope": "https://www.googleapis.com/auth/adwords",
            "helper_commands": [
                (
                    "uv run wilq google-ads oauth-url --client-secret-file "
                    "$WILQ_GOOGLE_ADS_CLIENT_SECRET_FILE"
                ),
                (
                    "uv run wilq google-ads oauth-exchange --client-secret-file "
                    "$WILQ_GOOGLE_ADS_CLIENT_SECRET_FILE "
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
