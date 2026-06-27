from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal, cast
from urllib.parse import urlparse
from uuid import uuid4

from wilq.actions.content_refresh import (
    content_contract_label,
    content_contract_labels,
    content_payload_with_reviewed_wordpress_draft_previews,
    content_refresh_payload_from_metric_facts,
    content_url_review_contract,
    post_publication_measurement_plan,
    post_publication_measurement_summary,
)
from wilq.actions.ga4.tracking_quality import ga4_tracking_quality_payload_from_metric_facts
from wilq.actions.google_ads.business_context import (
    ADS_BUSINESS_CONTEXT_ACTION_ID,
    ADS_STRATEGY_REVIEW_ACTION_ID,
    ADS_TARGET_CONFIRMATION_ACTION_ID,
    ads_business_context_configured,
    ads_business_context_missing_read_contracts,
    ads_business_context_payload,
    ads_strategy_review_payload,
    ads_strategy_review_state,
    ads_target_confirmation_payload,
)
from wilq.actions.google_ads.campaign_review import (
    CAMPAIGN_REVIEW_ACTION_ID,
    campaign_review_payload_from_metric_facts,
)
from wilq.actions.google_ads.change_history import (
    CHANGE_HISTORY_IMPACT_ACTION_ID,
    change_history_impact_payload_from_metric_facts,
)
from wilq.actions.google_ads.custom_segments import (
    CUSTOM_SEGMENT_ACTION_ID,
    custom_segment_payload_from_metric_facts,
)
from wilq.actions.google_ads.demand_gen import (
    DEMAND_GEN_AD_GROUP_AD_ROWS_CONTRACT,
    DEMAND_GEN_AD_READ_ROW_COUNT_FACT,
    DEMAND_GEN_AD_READ_STATUS_FACT,
    DEMAND_GEN_CAMPAIGN_ROWS_CONTRACT,
    DEMAND_GEN_CREATIVE_ASSET_ROW_COUNT_FACT,
    DEMAND_GEN_CREATIVE_ASSET_ROWS_CONTRACT,
    DEMAND_GEN_CREATIVE_ASSET_STATUS_FACT,
    DEMAND_GEN_LANDING_QUALITY_CONTRACT,
    DEMAND_GEN_READINESS_AVAILABLE_CONTRACT,
    DEMAND_GEN_READINESS_REVIEW_ACTION_ID,
    DEMAND_GEN_TRANSITION_CONSTRAINTS_CONTRACT,
    demand_gen_ad_group_ad_rows_from_facts,
    demand_gen_channel_label,
    demand_gen_contract_has_ready_fact,
    demand_gen_creative_asset_rows_from_facts,
    demand_gen_landing_quality_rows_from_facts,
    demand_gen_readiness_review_payload,
    demand_gen_transition_constraint_rows_from_campaigns,
)
from wilq.actions.google_ads.keyword_planner import (
    KEYWORD_PLANNER_ACCESS_ACTION_ID,
    keyword_planner_access_payload,
)
from wilq.actions.google_ads.negative_keywords import (
    NEGATIVE_KEYWORD_ACTION_ID,
    negative_keyword_payload_from_metric_facts,
)
from wilq.actions.google_ads.recommendations import (
    RECOMMENDATION_REVIEW_ACTION_ID,
    recommendation_review_payload_from_metric_facts,
)
from wilq.actions.google_ads.search_term_ngrams import (
    SEARCH_TERM_NGRAM_ACTION_ID,
    search_term_ngram_payload_from_metric_facts,
)
from wilq.actions.localo.visibility import (
    LOCALO_VISIBILITY_REVIEW_ACTION_ID,
    localo_visibility_review_payload_from_metric_facts,
)
from wilq.actions.payloads import validate_action_payload
from wilq.briefing.blocked_claim_labels import operator_blocked_claims
from wilq.briefing.merchant_labels import (
    merchant_display_label,
    merchant_metric_snapshot_labels,
    merchant_preview_contract_label,
    merchant_reporting_context_label,
    merchant_resolution_label,
    merchant_severity_label,
)
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.evidence.registry import connector_evidence_id
from wilq.operator_labels import evidence_count_label, source_connector_labels
from wilq.schemas import (
    ActionApplyRequest,
    ActionApplyResult,
    ActionConfirmRequest,
    ActionConfirmResult,
    ActionImpactCheckRequest,
    ActionImpactCheckResult,
    ActionMode,
    ActionMutationAuditRecord,
    ActionObject,
    ActionPreviewCardViewModel,
    ActionPreviewRequest,
    ActionPreviewResult,
    ActionPreviewRowViewModel,
    ActionReviewGate,
    ActionReviewOutcome,
    ActionReviewRequest,
    ActionReviewResult,
    ActionRisk,
    ActionStatus,
    ActionValidationResult,
    AuditEvent,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MetricFact,
    OpportunityDomain,
)
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store

MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT = "merchant_feed_issue_review_preview_v1"


def seed_static_actions() -> dict[str, ActionObject]:
    actions = seed_core_prepare_actions()
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
    actions[action.id] = action
    return actions


def seed_core_prepare_actions() -> dict[str, ActionObject]:
    actions = [
        ActionObject(
            id=RECOMMENDATION_REVIEW_ACTION_ID,
            title="Przygotuj sprawdzenie rekomendacji Google Ads",
            domain=OpportunityDomain.google_ads,
            connector="google_ads",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=[connector_evidence_id("google_ads")],
            human_diagnosis=(
                "Rekomendacje Google Ads są core workflow WILQ. WILQ utrzymuje "
                "kontrakt sprawdzenia, ale nie może akceptować ani odrzucać "
                "rekomendacji bez danych rekomendacji w WILQ."
            ),
            recommended_reason=(
                "Zbierz odczyt rekomendacji Google Ads, potem sprawdź typ "
                "rekomendacji, wpływ, powiązane kampanie i strategię przed "
                "jakimkolwiek zapisem zmian."
            ),
            payload={
                "action_type": "google_ads_recommendation_review",
                "connector": "google_ads",
                "mode": "prepare_only",
                "source_metric_names": ["connector_status"],
                "recommendations": [
                    {
                        "recommendation_id": "google_ads_recommendations_read_required",
                        "recommendation_type": "read_required",
                        "campaign_id": None,
                        "review_reason": (
                            "Najpierw odśwież dane rekomendacji Google Ads; bez "
                            "nich WILQ nie ocenia wpływu ani nie przygotowuje "
                            "zapisu zmian."
                        ),
                        "evidence_ids": [connector_evidence_id("google_ads")],
                        "source_metric_names": ["connector_status"],
                    }
                ],
                "recommendations_total": 1,
                "recommendations_included": 1,
                "payload_preview": [
                    {
                        "operation_type": "ApplyRecommendationOperation",
                        "recommendation_id": "google_ads_recommendations_read_required",
                        "recommendation_type": "read_required",
                        "apply_allowed": False,
                        "api_mutation_ready": False,
                        "destructive": False,
                        "evidence_ids": [connector_evidence_id("google_ads")],
                    }
                ],
                "payload_preview_total": 1,
                "payload_preview_included": 1,
                "evidence_ids": [connector_evidence_id("google_ads")],
                "required_validation": [
                    "review_recommendation_type",
                    "review_impact_metrics",
                    "review_change_history",
                    "review_business_goal",
                    "recommendation_apply_preview",
                    "google_ads_rmf_compliance_review",
                    "human_confirm_before_apply",
                ],
                "blocked_claims": [
                    "zapis rekomendacji",
                    "automatyczne przyjęcie rekomendacji",
                    "zmiana budżetu",
                    "zapis zmian kampanii",
                    "obietnica poprawy wyniku",
                ],
                "apply_allowed": False,
                "api_mutation_ready": False,
                "destructive": False,
            },
            validation_status="not_validated",
            created_by="system_core_seed",
        ),
        ActionObject(
            id="act_review_merchant_feed_issues",
            title="Przygotuj kolejkę przeglądu feedu Merchant Center",
            domain=OpportunityDomain.merchant,
            connector="google_merchant_center",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=[connector_evidence_id("google_merchant_center")],
            human_diagnosis=(
                "Merchant Center jest core workflow WILQ. W clean runtime WILQ może "
                "przygotować tylko kolejkę bezpieczną do sprawdzenia, dopóki odczyt nie "
                "dostarczy metryk problemów feedu."
            ),
            recommended_reason=(
                "Uruchom odczyt danych Merchant albo użyj istniejących evidence, "
                "potem sprawdź w WILQ podgląd zmian przed jakąkolwiek zmianą feedu."
            ),
            payload={
                "action_type": "merchant_feed_issue",
                "connector": "google_merchant_center",
                "mode": "prepare_only",
                "source_metric_names": [],
                "review_steps": [
                    "collect_merchant_issue_facts",
                    "group_issue_reasons",
                    "prepare_feed_fix_preview",
                    "require_human_confirm_before_apply",
                ],
                "blocked_claims": [
                    "ponowne zatwierdzenie produktu",
                    "odzyskany przychód",
                    "automatyczna zmiana feedu",
                ],
                "destructive": False,
            },
            validation_status="not_validated",
            created_by="system_core_seed",
        ),
        ActionObject(
            id="act_review_ga4_tracking_quality",
            title="Sprawdź jakość pomiaru GA4 przed oceną kampanii",
            domain=OpportunityDomain.ga4,
            connector="google_analytics_4",
            mode=ActionMode.prepare,
            risk=ActionRisk.low,
            status=ActionStatus.needs_validation,
            evidence_ids=[connector_evidence_id("google_analytics_4")],
            human_diagnosis=(
                "GA4 jest głównym procesem pracy WILQ. W czystym runtime WILQ może tylko "
                "przygotować przegląd pomiaru i zablokować twierdzenia o zwrocie z reklam "
                "oraz przychodzie, dopóki nie ma faktów metrycznych ze stroną wejścia, "
                "źródłem ruchu i kampanią."
            ),
            recommended_reason=(
                "Zbierz zestawienie GA4 ze stroną wejścia, źródłem ruchu i kampanią, "
                "potem sprawdź pomiar i dopasowanie komunikatu bez oceniania kampanii "
                "po niepełnych danych."
            ),
            payload={
                "action_type": "ga4_tracking_gap",
                "connector": "google_analytics_4",
                "mode": "prepare_only",
                "preview_contract": "ga4_tracking_quality_review_v1",
                "source_metric_names": [],
                "required_breakdowns": ["landing_page", "source_medium", "campaign"],
                "required_validation": [
                    "review_landing_page_dimension",
                    "review_source_medium_dimension",
                    "review_campaign_name_dimension",
                    "review_conversion_or_key_event_mapping",
                    "human_confirm_before_tracking_change",
                ],
                "blocked_claims": ["conversion_rate", "przychód", "roas"],
                "payload_preview": [
                    {
                        "id": "ga4_tracking_review_connector_status",
                        "preview_contract": "ga4_tracking_quality_review_v1",
                        "operation_type": "tracking_quality_review",
                        "landing_page": None,
                        "landing_page_label": "brak strony wejścia w raporcie",
                        "source_medium": None,
                        "source_medium_label": "brak źródła i medium w raporcie",
                        "campaign_name": None,
                        "campaign_name_label": "brak kampanii w raporcie",
                        "tracking_dimension_gaps": [
                            "landing_page",
                            "source_medium",
                            "campaign_name",
                        ],
                        "metric_snapshot": {},
                        "metric_snapshot_labels": {},
                        "reason": (
                            "Brak wymiarowych GA4 facts. Najpierw zbierz "
                            "zestawienie strony wejścia, źródła ruchu i kampanii z GA4."
                        ),
                        "required_validation": [
                            "review_landing_page_dimension",
                            "review_source_medium_dimension",
                            "review_campaign_name_dimension",
                            "review_conversion_or_key_event_mapping",
                            "human_confirm_before_tracking_change",
                        ],
                        "required_validation_labels": [
                            "sprawdź stronę wejścia",
                            "sprawdź źródło i medium ruchu",
                            "sprawdź kampanię",
                            "sprawdź konwersje i zdarzenia kluczowe",
                            "potwierdź sprawdzenie przez człowieka",
                        ],
                        "blocked_claims": ["conversion_rate", "przychód", "roas"],
                        "blocked_claim_labels": [
                            "współczynnik konwersji",
                            "przychód",
                            "zwrot z reklam",
                        ],
                        "evidence_ids": [connector_evidence_id("google_analytics_4")],
                        "evidence_summary_label": "1 dowód źródłowy",
                        "api_mutation_ready": False,
                        "apply_allowed": False,
                        "destructive": False,
                    }
                ],
                "destructive": False,
            },
            validation_status="not_validated",
            created_by="system_core_seed",
        ),
        ActionObject(
            id="act_prepare_content_refresh_queue",
            title="Przygotuj kolejkę odświeżenia treści ekologus.pl",
            domain=OpportunityDomain.content,
            connector="wordpress_ekologus",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=[
                connector_evidence_id("wordpress_ekologus"),
                connector_evidence_id("google_search_console"),
            ],
            human_diagnosis=(
                "Content jest core workflow WILQ. W clean runtime WILQ może "
                "przygotować tylko kolejkę bezpieczną do sprawdzenia, dopóki GSC/WordPress/GA4 "
                "nie dostarczą URL/query evidence."
            ),
            recommended_reason=(
                "Zbierz GSC query/page i spis treści WordPress, potem klasyfikuj "
                "zachowanie, odświeżenie, scalenie, nową treść albo blokadę bez "
                "obietnic leadów ani rankingów."
            ),
            payload={
                "action_type": "wordpress_content_refresh",
                "connector": "wordpress_ekologus",
                "mode": "prepare_only",
                "source_connectors": ["google_search_console", "wordpress_ekologus"],
                "source_metric_names": [],
                "queue_steps": [
                    "collect_gsc_query_page_facts",
                    "join_wordpress_inventory_with_gsc",
                    "classify_refresh_create_merge_block",
                    "review_public_final_url",
                    "require_human_confirm_before_wordpress_write",
                ],
                "content_url_review_contract": content_url_review_contract(),
                "content_brief_preview": [
                    {
                        "preview_contract": "content_brief_preview_v1",
                        "candidate_id": "content_brief_empty_state",
                        "source_type": "empty_state",
                        "mode": "block",
                        "topic": "brak potwierdzonego tematu",
                        "source_public_url": None,
                        "preview_url": None,
                        "intended_final_url": None,
                        "final_canonical_url": None,
                        "inventory_gate_status": "blocked_until_inventory_review",
                        "canonical_gate_status": "blocked_until_inventory_review",
                        "duplicate_gate_status": "create_blocked_until_duplicate_check",
                        "content_gate_summary": (
                            "Brak query/page i spisu treści WordPress w świeżym runtime. "
                            "Najpierw zbierz dane źródłowe, potem oceniaj zachowanie, "
                            "odświeżenie, scalenie albo utworzenie treści."
                        ),
                        "wordpress_inventory_match": "missing",
                        "decision_options": ["block"],
                        "metric_snapshot": {},
                        "brief_goal": (
                            "Zablokuj pisanie treści do czasu zebrania GSC "
                            "i WordPress inventory."
                        ),
                        "intent": "brak intencji do pisania bez danych źródłowych",
                        "content_angle": (
                            "Nie przygotowuj tekstu bez potwierdzonego "
                            "publicznego URL i dowodów."
                        ),
                        "audience": (
                            "Marketer Ekologus sprawdzający gotowość danych "
                            "przed pracą nad treścią."
                        ),
                        "key_objections": [
                            "brak potwierdzonego tematu",
                            "brak publicznego URL",
                            "brak kontroli duplikacji",
                        ],
                        "h1_direction": "Nie ustalaj H1 bez potwierdzonego tematu i URL.",
                        "seo_title_direction": "Nie ustalaj title bez potwierdzonego tematu i URL.",
                        "meta_description_direction": (
                            "Nie ustalaj meta description bez potwierdzonego "
                            "tematu i URL."
                        ),
                        "h2_direction": ["najpierw zbierz dane GSC i WordPress"],
                        "faq_direction": ["najpierw zbierz dane GSC i WordPress"],
                        "schema_direction": "Nie planuj schema bez zatwierdzonego briefu.",
                        "cta_direction": "Nie ustalaj CTA bez dopasowania usługi i intencji.",
                        "internal_link_direction": ["najpierw potwierdź istniejące URL-e"],
                        "legal_review_notes": [
                            "brak treści do oceny prawnej przed zebraniem danych"
                        ],
                        "brand_voice_notes": ["brak szkicu do oceny tonu przed zebraniem danych"],
                        "publication_readiness_status": "blocked_until_review",
                        "publication_blockers": [
                            "content_url_preflight_review",
                            "canonical_review",
                            "duplicate_or_cannibalization_check",
                            "legal_factual_review",
                            "human_confirm_before_wordpress_write",
                        ],
                        "source_facts": [
                            "brak GSC query/page facts",
                            "brak WordPress inventory facts",
                        ],
                        "missing_evidence": [
                            "brak publicznego URL",
                            "brak danych GSC",
                            "brak spisu treści WordPress",
                        ],
                        "forbidden_claims": ["wzrost liczby leadów", "wpływ na przychód", "gwarancja pozycji"],
                        "required_validation": [
                            "gsc_query_page_check",
                            "wordpress_inventory_check",
                            "content_url_preflight_review",
                            "duplicate_or_cannibalization_check",
                            "human_confirm_before_wordpress_write",
                        ],
                        "blocked_claims": ["wzrost liczby leadów", "wpływ na przychód", "gwarancja pozycji"],
                        "source_connectors": ["google_search_console", "wordpress_ekologus"],
                        "evidence_ids": [
                            connector_evidence_id("wordpress_ekologus"),
                            connector_evidence_id("google_search_console"),
                        ],
                        "apply_allowed": False,
                        "api_mutation_ready": False,
                        "destructive": False,
                    }
                ],
                "blocked_claims": ["wzrost liczby leadów", "wpływ na przychód", "gwarancja pozycji"],
                "destructive": False,
            },
            validation_status="not_validated",
            created_by="system_core_seed",
        ),
    ]
    return {action.id: action for action in actions}


_STATIC_ACTIONS = seed_static_actions()
ACTION_METRIC_CONNECTORS = (
    "google_ads",
    "google_merchant_center",
    "google_analytics_4",
    "google_search_console",
    "wordpress_ekologus",
    "ahrefs",
    "localo",
)
ACTION_METRIC_FACT_LIMIT = 500
ACTION_METRIC_FACT_LIMITS = {
    "google_ads": ACTION_METRIC_FACT_LIMIT,
    "google_analytics_4": ACTION_METRIC_FACT_LIMIT,
    "google_merchant_center": ACTION_METRIC_FACT_LIMIT,
    "google_search_console": ACTION_METRIC_FACT_LIMIT,
    "wordpress_ekologus": ACTION_METRIC_FACT_LIMIT,
    "ahrefs": ACTION_METRIC_FACT_LIMIT,
    "localo": ACTION_METRIC_FACT_LIMIT,
}


def list_actions() -> list[ActionObject]:
    actions = {**_STATIC_ACTIONS, **seed_metric_action_candidates()}
    if _google_ads_live_data_available():
        actions.pop("act_configure_google_ads_env", None)
        business_context_action = _google_ads_business_context_action()
        if business_context_action is not None:
            actions[business_context_action.id] = business_context_action
        target_confirmation_action = _google_ads_target_confirmation_action()
        if target_confirmation_action is not None:
            actions[target_confirmation_action.id] = target_confirmation_action
        strategy_review_action = _google_ads_strategy_review_action()
        if strategy_review_action is not None:
            actions[strategy_review_action.id] = strategy_review_action
        keyword_planner_action = _google_ads_keyword_planner_access_action()
        if keyword_planner_action is not None:
            actions[keyword_planner_action.id] = keyword_planner_action
    return _with_persisted_review_gates(actions.values())


def get_action(action_id: str) -> ActionObject | None:
    actions = {**_STATIC_ACTIONS, **seed_metric_action_candidates()}
    business_context_action = _google_ads_business_context_action()
    if business_context_action is not None:
        actions[business_context_action.id] = business_context_action
    target_confirmation_action = _google_ads_target_confirmation_action()
    if target_confirmation_action is not None:
        actions[target_confirmation_action.id] = target_confirmation_action
    strategy_review_action = _google_ads_strategy_review_action()
    if strategy_review_action is not None:
        actions[strategy_review_action.id] = strategy_review_action
    keyword_planner_action = _google_ads_keyword_planner_access_action()
    if keyword_planner_action is not None:
        actions[keyword_planner_action.id] = keyword_planner_action
    action = actions.get(action_id)
    if action is None:
        return None
    return _with_review_gate(
        action,
        _persisted_audit_events_for_action(action.id),
        _persisted_mutation_audits_for_action(action.id),
    )


def _google_ads_live_data_available() -> bool:
    latest_run = _latest_google_ads_vendor_read()
    if latest_run is None:
        return False
    return (
        latest_run.status == ConnectorRefreshStatus.completed
        and latest_run.vendor_data_collected is True
    )


def _latest_google_ads_vendor_read() -> ConnectorRefreshRun | None:
    runs = [
        run
        for run in list_connector_refresh_runs(connector_id="google_ads")
        if run.mode == ConnectorRefreshMode.vendor_read
    ]
    if not runs:
        return None
    return max(runs, key=_connector_refresh_recency_key)


def _connector_refresh_recency_key(run: ConnectorRefreshRun) -> tuple[str, str]:
    timestamp = run.completed_at or run.started_at
    return (timestamp.isoformat(), run.id)


def _google_ads_business_context_action() -> ActionObject | None:
    latest_run = _latest_google_ads_vendor_read()
    if (
        latest_run is None
        or latest_run.status != ConnectorRefreshStatus.completed
        or not latest_run.vendor_data_collected
        or ads_business_context_configured()
    ):
        return None
    missing_read_contracts = ads_business_context_missing_read_contracts()
    return ActionObject(
        id=ADS_BUSINESS_CONTEXT_ACTION_ID,
        title="Uzupełnij kontekst biznesowy Google Ads",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=_unique(
            [
                connector_evidence_id("google_ads"),
                *latest_run.evidence_ids,
            ]
        ),
        human_diagnosis=(
            "Google Ads ma live metryki, ale WILQ nie ma nie-sekretnych celów "
            "biznesowych Ekologus: marży, celu biznesowego, celu budżetu oraz "
            "docelowego zwrotu z reklam albo kosztu pozyskania celu."
        ),
        recommended_reason=(
            "Uzupełnij repo-local .env wartościami biznesowymi, potem sprawdź "
            "kontekst biznesowy Ads. Do tego czasu WILQ blokuje obietnice "
            "o rentowności, zmarnowanym budżecie i skalowaniu."
        ),
        payload=ads_business_context_payload(missing_read_contracts),
        validation_status="not_validated",
        created_by="system_business_context_seed",
    )


def _google_ads_target_confirmation_action() -> ActionObject | None:
    latest_run = _latest_google_ads_vendor_read()
    missing_read_contracts = ads_business_context_missing_read_contracts()
    if (
        latest_run is None
        or latest_run.status != ConnectorRefreshStatus.completed
        or not latest_run.vendor_data_collected
        or not ads_business_context_configured()
        or "target_roas_or_cpa" not in missing_read_contracts
    ):
        return None
    return ActionObject(
        id=ADS_TARGET_CONFIRMATION_ACTION_ID,
        title="Potwierdź docelowy zwrot z reklam albo koszt pozyskania celu dla Ads",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=_unique(
            [
                connector_evidence_id("google_ads"),
                *latest_run.evidence_ids,
            ]
        ),
        human_diagnosis=(
            "Google Ads ma live metryki oraz lokalny kontekst biznesowy, ale brakuje "
            "potwierdzonego zwrotu z reklam albo kosztu pozyskania celu. WILQ może robić ocenę kampanii, "
            "ale nie może wydać werdyktu KPI ani uruchamiać zapisu zmian budżetu lub rekomendacji."
        ),
        recommended_reason=(
            "Potwierdź jedną zasadę bezpieczeństwa celu w repo-local .env. To nadal jest "
            "krok bez zapisu zmian: bez mutacji Google Ads, bez automatycznego "
            "skalowania i bez werdyktu rentowności."
        ),
        payload=ads_target_confirmation_payload(missing_read_contracts),
        validation_status="not_validated",
        created_by="system_ads_target_confirmation_seed",
    )


def _google_ads_strategy_review_action() -> ActionObject | None:
    latest_run = _latest_google_ads_vendor_read()
    latest_review = ads_strategy_review_state()
    if (
        latest_run is None
        or latest_run.status != ConnectorRefreshStatus.completed
        or not latest_run.vendor_data_collected
        or not ads_business_context_configured()
        or (
            latest_review is not None
            and latest_review.outcome == "approved_for_prepare"
        )
    ):
        return None
    return ActionObject(
        id=ADS_STRATEGY_REVIEW_ACTION_ID,
        title="Zapisz ocenę strategii Ads przez człowieka",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=_unique(
            [
                connector_evidence_id("google_ads"),
                *latest_run.evidence_ids,
            ]
        ),
        human_diagnosis=(
            "Google Ads ma live metryki i lokalny kontekst biznesowy, ale brakuje "
            "zapisanego wyniku ludzkiej oceny strategii. WILQ nie powinien "
            "traktować celu ani KPI jako decyzji operacyjnej bez tego zapisu."
        ),
        recommended_reason=(
            "Zapisz wynik oceny: zatwierdzone do dalszego przygotowania, wymaga "
            "poprawek, odrzucone albo odłożone. To nadal nie wykonuje zapisu zmian ani "
            "mutacji Google Ads."
        ),
        payload=ads_strategy_review_payload(),
        validation_status="not_validated",
        created_by="system_ads_strategy_review_seed",
    )


def _google_ads_keyword_planner_access_action() -> ActionObject | None:
    latest_run = _latest_google_ads_vendor_read()
    if (
        latest_run is None
        or latest_run.status != ConnectorRefreshStatus.completed
        or not latest_run.vendor_data_collected
    ):
        return None
    blocker = _keyword_planner_access_blocker(latest_run)
    if blocker is None:
        return None
    return ActionObject(
        id=KEYWORD_PLANNER_ACCESS_ACTION_ID,
        title="Odblokuj Keyword Planner dla Google Ads",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=_unique(
            [
                connector_evidence_id("google_ads"),
                *latest_run.evidence_ids,
            ]
        ),
        human_diagnosis=(
            "Google Ads live read działa, ale wzbogacenie Keyword Planner jest "
            f"zablokowany przez Google Ads API: {blocker}. WILQ może używać "
            "oceny haseł źródłowych, ale nie może twierdzić nic o prognozie ani "
            "rozmiarze odbiorców."
        ),
        recommended_reason=(
            "Dopóki token deweloperski nie ma zatwierdzonego dostępu Keyword Planner, "
            "segmenty zostają bez prognozy i wzbogacenia. To jest zewnętrzny "
            "access blocker, nie brak promptu."
        ),
        payload=keyword_planner_access_payload(blocker),
        validation_status="not_validated",
        created_by="system_keyword_planner_access_seed",
    )


def _keyword_planner_access_blocker(run: ConnectorRefreshRun) -> str | None:
    status = str(run.metric_summary.get("keyword_planner_status") or "").lower()
    blocker = str(run.metric_summary.get("keyword_planner_blocker") or "").strip()
    http_status = str(run.metric_summary.get("keyword_planner_http_status") or "").strip()
    if status != "blocked":
        return None
    blocker_text = " ".join(part for part in (blocker, http_status) if part)
    if not blocker_text:
        return None
    normalized = blocker_text.lower()
    if (
        "developer_token_not_approved" not in normalized
        and "permission_denied" not in normalized
        and http_status != "403"
    ):
        return None
    return blocker_text


def seed_metric_action_candidates() -> dict[str, ActionObject]:
    facts = _action_metric_facts()
    by_connector = _facts_by_connector(facts)
    actions: dict[str, ActionObject] = {}

    merchant_facts = by_connector.get("google_merchant_center", [])
    merchant_issue_facts = _merchant_issue_metric_facts(merchant_facts)
    if merchant_issue_facts:
        merchant_action_metrics = merchant_issue_facts[:8]
        merchant_issue_clusters = _merchant_issue_clusters_payload(merchant_facts)
        merchant_payload_preview = _merchant_issue_payload_preview(merchant_issue_clusters)
        action = ActionObject(
            id="act_review_merchant_feed_issues",
            title="Przygotuj kolejkę przeglądu feedu Merchant Center",
            domain=OpportunityDomain.merchant,
            connector="google_merchant_center",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=_unique(fact.evidence_id for fact in merchant_action_metrics),
            metrics=merchant_action_metrics,
            human_diagnosis=(
                "Merchant Center ma dane o problemach feedu w WILQ. "
                f"{_metric_sentence(merchant_action_metrics)}. To uzasadnia "
                "kolejkę przeglądu problemów feedu, ale nie automatyczną zmianę "
                "danych produktu."
            ),
            recommended_reason=(
                "Na /merchant pokaż grupy problemów jako kolejkę przygotowawczą: "
                "sprawdź typ problemu, atrybut, kraj, podgląd zmian i sprawdzenie "
                "przed jakąkolwiek zmianą feedu."
            ),
            payload={
                "action_type": "merchant_feed_issue",
                "connector": "google_merchant_center",
                "mode": "prepare_only",
                "source_metric_names": _unique(fact.name for fact in merchant_action_metrics),
                "issue_clusters": merchant_issue_clusters,
                "preview_contract": MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT,
                "payload_preview": merchant_payload_preview,
                "review_steps": [
                    "identify_disapproved_products",
                    "group_issue_reasons",
                    "prepare_feed_fix_preview",
                    "require_human_confirm_before_apply",
                ],
                "blocked_claims": [
                    "ponowne zatwierdzenie produktu",
                    "odzyskany przychód",
                    "automatyczna zmiana feedu",
                    "nadpisanie głównego feedu",
                    "zapis do feedu",
                    "zmiana danych produktu",
                    "automatyczna naprawa zatwierdzenia",
                ],
                "apply_allowed": False,
                "destructive": False,
            },
            validation_status="not_validated",
            created_by="system_metric_seed",
        )
        actions[action.id] = action

    ga4_facts = by_connector.get("google_analytics_4", [])
    ga4_dimensioned_facts = _ga4_dimensioned_metric_facts(ga4_facts)
    if ga4_dimensioned_facts:
        ga4_action_metrics = ga4_dimensioned_facts[:8]
        action = ActionObject(
            id="act_review_ga4_tracking_quality",
            title="Sprawdź jakość pomiaru GA4 przed oceną kampanii",
            domain=OpportunityDomain.ga4,
            connector="google_analytics_4",
            mode=ActionMode.prepare,
            risk=ActionRisk.low,
            status=ActionStatus.needs_validation,
            evidence_ids=_unique(fact.evidence_id for fact in ga4_action_metrics),
            metrics=ga4_action_metrics,
            human_diagnosis=(
                "GA4 zwraca wymiarowe fakty strony wejścia, źródła ruchu i kampanii, ale WILQ "
                "nadal nie ma kontraktu na zwrot z reklam, przychód ani werdykt konwersji. "
                f"{_metric_sentence(ga4_action_metrics)}."
            ),
            recommended_reason=(
                "Na /ga4 przygotuj przegląd pomiaru i jakości ruchu: pokaż "
                "zestawienie strony wejścia, źródła ruchu i kampanii, sprawdź propozycję w WILQ i nie "
                "oceniaj kampanii bez kontraktu konwersji."
            ),
            payload=ga4_tracking_quality_payload_from_metric_facts(ga4_action_metrics),
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
        content_action_metrics = _prioritize_action_metrics(
            content_facts,
            required_names={"content_object_count", "clicks", "domain_rating"},
        )[:10]
        content_payload = content_refresh_payload_from_metric_facts(content_facts)
        action = ActionObject(
            id="act_prepare_content_refresh_queue",
            title="Przygotuj kolejkę odświeżenia treści ekologus.pl",
            domain=OpportunityDomain.content,
            connector="wordpress_ekologus",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=_unique(fact.evidence_id for fact in content_action_metrics),
            metrics=content_action_metrics,
            human_diagnosis=(
                "Spis treści WordPress istnieje w WILQ i można go zestawić z GSC/Ahrefs, "
                "żeby planować odświeżenie zamiast duplikować treści. "
                f"{_metric_sentence(content_facts)}."
            ),
            recommended_reason=(
                "Na /content-planner przygotuj kolejkę zachowania, odświeżenia, scalenia, "
                "nowej treści albo blokady. "
                "Traktuj plan treści jako materiał do sprawdzenia: GSC/WordPress może dać "
                "odświeżenie albo scalenie, a Ahrefs tylko tematy do oceny po "
                "dodatkowym sprawdzeniu popytu z GSC i spisu treści."
            ),
            payload=content_payload
            if content_payload is not None
            else {
                "action_type": "wordpress_content_refresh",
                "connector": "wordpress_ekologus",
                "mode": "prepare_only",
                "source_connectors": _unique(fact.source_connector for fact in content_facts),
                "source_metric_names": _unique(fact.name for fact in content_facts),
                "content_url_review_contract": content_url_review_contract(),
                "queue_steps": [
                    "join_wordpress_inventory_with_gsc",
                    "classify_refresh_create_merge_block",
                    "review_public_final_url",
                    "prepare_brief_preview",
                    "require_human_confirm_before_wordpress_write",
                ],
                "required_validation": [
                    "gsc_query_page_check",
                    "wordpress_inventory_check",
                    "content_url_preflight_review",
                    "duplicate_or_cannibalization_check",
                    "human_confirm_before_wordpress_write",
                ],
                "destructive": False,
            },
            validation_status="not_validated",
            created_by="system_metric_seed",
        )
        actions[action.id] = action
        wordpress_draft_action = _wordpress_draft_handoff_action(
            content_payload=content_payload,
            content_action_metrics=content_action_metrics,
        )
        if wordpress_draft_action is not None:
            actions[wordpress_draft_action.id] = wordpress_draft_action

    google_ads_facts = by_connector.get("google_ads", [])
    demand_gen_action = _demand_gen_readiness_review_action(
        google_ads_facts,
        by_connector.get("google_analytics_4", []),
    )
    if demand_gen_action is not None:
        actions[demand_gen_action.id] = demand_gen_action

    campaign_review_payload = campaign_review_payload_from_metric_facts(google_ads_facts)
    if campaign_review_payload is not None:
        campaign_review_metric_names = set(campaign_review_payload["source_metric_names"])
        campaign_review_evidence_ids = set(campaign_review_payload["evidence_ids"])
        campaign_review_keys = {
            (candidate.get("campaign_id"), candidate.get("campaign_name"))
            for candidate in campaign_review_payload["campaign_candidates"][:4]
            if isinstance(candidate, dict)
        }
        campaign_review_metrics = [
            fact
            for fact in google_ads_facts
            if fact.name in campaign_review_metric_names
            and fact.evidence_id in campaign_review_evidence_ids
            and (
                fact.dimensions.get("campaign_id"),
                fact.dimensions.get("campaign_name"),
            )
            in campaign_review_keys
        ][:12]
        action = ActionObject(
            id=CAMPAIGN_REVIEW_ACTION_ID,
            title="Przygotuj kolejkę przeglądu kampanii Google Ads",
            domain=OpportunityDomain.google_ads,
            connector="google_ads",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=campaign_review_payload["evidence_ids"],
            metrics=campaign_review_metrics,
            human_diagnosis=(
                "Google Ads ma aktualne metryki kampanii. WILQ może przygotować "
                "kolejkę przeglądu kampanii ze wskaźnikami policzonymi z dowodów, ale nadal "
                "blokuje decyzje budżetowe bez pacingu, historii zmian, rekomendacji "
                "i modelu wartości."
            ),
            recommended_reason=(
                "Na /ads-doctor przejrzyj kampanie z największym kosztem i ruchem. "
                "Traktuj podgląd jako materiał do sprawdzenia: bez pauzowania, "
                "skalowania budżetu ani obietnic rentowności."
            ),
            payload=campaign_review_payload,
            validation_status="not_validated",
            created_by="system_metric_seed",
        )
        actions[action.id] = action

    recommendation_review_payload = recommendation_review_payload_from_metric_facts(
        google_ads_facts
    )
    if recommendation_review_payload is not None:
        recommendation_metric_names = set(
            recommendation_review_payload["source_metric_names"]
        )
        recommendation_evidence_ids = set(recommendation_review_payload["evidence_ids"])
        recommendation_ids = {
            recommendation.get("recommendation_id")
            for recommendation in recommendation_review_payload["recommendations"][:6]
            if isinstance(recommendation, dict)
        }
        recommendation_metrics = [
            fact
            for fact in google_ads_facts
            if fact.name in recommendation_metric_names
            and fact.evidence_id in recommendation_evidence_ids
            and fact.dimensions.get("recommendation_id") in recommendation_ids
        ][:12]
        action = ActionObject(
            id=RECOMMENDATION_REVIEW_ACTION_ID,
            title="Przygotuj ocenę rekomendacji Google Ads",
            domain=OpportunityDomain.google_ads,
            connector="google_ads",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=recommendation_review_payload["evidence_ids"],
            metrics=recommendation_metrics,
            human_diagnosis=(
                "Google Ads ma aktywne fakty rekomendacji. WILQ może pokazać "
                "podgląd zmian do sprawdzenia, ale nie może akceptować "
                "rekomendacji bez strategii, oceny RMF/compliance, potwierdzenia "
                "i audytu."
            ),
            recommended_reason=(
                "Na /ads-doctor przejrzyj typ rekomendacji, podgląd wpływu i "
                "powiązane kampanie. Traktuj podgląd jako materiał do decyzji, "
                "nie zgodę na zapis zmian."
            ),
            payload=recommendation_review_payload,
            validation_status="not_validated",
            created_by="system_metric_seed",
        )
        actions[action.id] = action

    change_history_payload = change_history_impact_payload_from_metric_facts(google_ads_facts)
    if change_history_payload is not None:
        change_event_ids = {
            preview.get("change_event_id")
            for preview in change_history_payload["change_history_preview"][:6]
            if isinstance(preview, dict)
        }
        change_history_metrics = [
            fact
            for fact in google_ads_facts
            if fact.name in change_history_payload["source_metric_names"]
            and fact.evidence_id in change_history_payload["evidence_ids"]
            and fact.dimensions.get("change_event_id") in change_event_ids
        ][:12]
        action = ActionObject(
            id=CHANGE_HISTORY_IMPACT_ACTION_ID,
            title="Przygotuj ocenę wpływu zmian Google Ads",
            domain=OpportunityDomain.google_ads,
            connector="google_ads",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=change_history_payload["evidence_ids"],
            metrics=change_history_metrics,
            human_diagnosis=(
                "Google Ads ma fakty change_event. WILQ może przygotować kolejkę "
                "oceny wpływu zmian, ale nie może twierdzić nic o wpływie na wynik bez "
                "okna przed/po i ręcznej oceny."
            ),
            recommended_reason=(
                "Na /ads-doctor sprawdź co zmieniono, na jakim zasobie i które "
                "pola ruszono. Traktuj podgląd jako materiał do sprawdzenia: bez "
                "zapisu zmian, bez skalowania i bez obietnic poprawy wyniku."
            ),
            payload=change_history_payload,
            validation_status="not_validated",
            created_by="system_metric_seed",
        )
        actions[action.id] = action

    search_term_ngram_payload = search_term_ngram_payload_from_metric_facts(
        google_ads_facts
    )
    if search_term_ngram_payload is not None:
        ngram_source_terms = {
            term
            for preview in search_term_ngram_payload["ngram_preview"][:8]
            if isinstance(preview, dict)
            for term in preview.get("sample_search_terms", [])
            if isinstance(term, str)
        }
        ngram_metrics = [
            fact
            for fact in google_ads_facts
            if fact.name in search_term_ngram_payload["source_metric_names"]
            and fact.evidence_id in search_term_ngram_payload["evidence_ids"]
            and fact.dimensions.get("search_term") in ngram_source_terms
        ][:12]
        action = ActionObject(
            id=SEARCH_TERM_NGRAM_ACTION_ID,
            title="Przygotuj ocenę tematów z n-gramów wyszukiwanych haseł",
            domain=OpportunityDomain.google_ads,
            connector="google_ads",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=search_term_ngram_payload["evidence_ids"],
            metrics=ngram_metrics,
            human_diagnosis=(
                "Google Ads ma fakty wyszukiwanych haseł, które tworzą powtarzające się "
                "tematy n-gram. WILQ może przygotować kolejkę oceny intencji, ale "
                "nie może traktować n-gramów jako gotowych wykluczeń ani obiecywać "
                "zmarnowanego budżetu bez sprawdzenia."
            ),
            recommended_reason=(
                "Na /ads-doctor przejrzyj n-gramy z kosztem, kliknięciami i "
                "przykładowymi wyszukiwanymi hasłami. Dopiero po ręcznej ocenie intencji wróć "
                "do negative keyword queue."
            ),
            payload=search_term_ngram_payload,
            validation_status="not_validated",
            created_by="system_metric_seed",
        )
        actions[action.id] = action

    custom_segment_payload = custom_segment_payload_from_metric_facts(google_ads_facts)
    if custom_segment_payload is not None:
        custom_segment_metrics = [
            fact
            for fact in google_ads_facts
            if fact.name.startswith("search_term_")
            and fact.dimensions.get("search_term") in custom_segment_payload["terms"]
        ][:12]
        action = ActionObject(
            id=CUSTOM_SEGMENT_ACTION_ID,
            title="Przygotuj propozycje segmentów z wyszukiwanych haseł",
            domain=OpportunityDomain.google_ads,
            connector="google_ads",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=custom_segment_payload["evidence_ids"],
            metrics=custom_segment_metrics,
            human_diagnosis=(
                "Google Ads ma realne fakty z wyszukiwanych haseł. WILQ może przygotować "
                "propozycje segmentów wyłącznie z tych terminów, ale nie może "
                "twierdzić nic o rozmiarze odbiorców, zwrocie z reklam ani skuteczności bez "
                "dodatkowych kontraktów."
            ),
            recommended_reason=(
                "Na /ads-doctor przejrzyj hasła źródłowe, odrzuć brandowe i "
                "niskointencyjne frazy, dodaj wzbogacenie Keyword Planner i sprawdź w WILQ "
                "podgląd zmian przed zapisem zmian."
            ),
            payload=custom_segment_payload,
            validation_status="not_validated",
            created_by="system_metric_seed",
        )
        actions[action.id] = action

    negative_keyword_payload = negative_keyword_payload_from_metric_facts(google_ads_facts)
    if negative_keyword_payload is not None:
        negative_keyword_metrics = [
            fact
            for fact in google_ads_facts
            if fact.name.startswith("search_term_")
            and fact.dimensions.get("search_term") in negative_keyword_payload["terms"]
        ][:12]
        action = ActionObject(
            id=NEGATIVE_KEYWORD_ACTION_ID,
            title="Przygotuj kolejkę oceny wykluczeń z wyszukiwanych haseł",
            domain=OpportunityDomain.google_ads,
            connector="google_ads",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=negative_keyword_payload["evidence_ids"],
            metrics=negative_keyword_metrics,
            human_diagnosis=(
                "Google Ads ma fakty z wyszukiwanych haseł, które mogą zasilić ocenę "
                "potencjalnych wykluczeń. WILQ nie może jednak twierdzić nic o "
                "przepalonym budżecie ani wdrażać wykluczających słów bez "
                "90-dniowej kontroli bezpieczeństwa i ręcznej sprawdzenia."
            ),
            recommended_reason=(
                "Na /ads-doctor przejrzyj terminy z kosztem/kliknięciami i zerową "
                "konwersją w bieżącym evidence, ale potraktuj je wyłącznie jako "
                "kolejkę oceny przed 90-dniową kontrolą bezpieczeństwa."
            ),
            payload=negative_keyword_payload,
            validation_status="not_validated",
            created_by="system_metric_seed",
        )
        actions[action.id] = action

    localo_facts = _localo_action_metric_facts(by_connector.get("localo", []))
    localo_visibility_payload = localo_visibility_review_payload_from_metric_facts(
        localo_facts
    )
    if localo_visibility_payload is not None:
        localo_metrics = _prioritize_action_metrics(
            localo_facts,
            required_names={
                "localo_active_place_count",
                "localo_tracked_keyword_count",
                "localo_avg_visibility_current",
                "localo_reviews_count",
            },
        )[:10]
        action = ActionObject(
            id=LOCALO_VISIBILITY_REVIEW_ACTION_ID,
            title="Przygotuj przegląd widoczności lokalnej Localo",
            domain=OpportunityDomain.localo,
            connector="localo",
            mode=ActionMode.prepare,
            risk=ActionRisk.low,
            status=ActionStatus.needs_validation,
            evidence_ids=_unique(fact.evidence_id for fact in localo_metrics),
            metrics=localo_metrics,
            human_diagnosis=(
                "Localo ma agregaty miejsc, fraz, widoczności i recenzji z odczytu danych. "
                f"{_metric_sentence(localo_metrics)}. To wystarcza do sprawdzenia lokalnej "
                "widoczności, ale nie do twierdzeń o GBP, konkurencji ani poprawie wyniku."
            ),
            recommended_reason=(
                "Na /localo przygotuj przegląd agregatów i zostaw wyniki profilu firmy, "
                "zapis zmian i poprawę widoczności zablokowane do czasu osobnych kontraktów Localo."
            ),
            payload=localo_visibility_payload,
            validation_status="not_validated",
            created_by="system_metric_seed",
        )
        actions[action.id] = action

    social_facts = [
        *by_connector.get("google_search_console", []),
        *by_connector.get("google_merchant_center", []),
        *by_connector.get("wordpress_ekologus", []),
        *by_connector.get("google_analytics_4", []),
    ]
    if social_facts:
        actions.update(_social_draft_actions(social_facts))

    return actions


def _demand_gen_readiness_review_action(
    google_ads_facts: list[MetricFact],
    ga4_facts: list[MetricFact],
) -> ActionObject | None:
    evidence_ids = _unique(
        [
            connector_evidence_id("google_ads"),
            connector_evidence_id("google_analytics_4"),
            *_latest_vendor_read_evidence_ids("google_ads"),
            *_latest_vendor_read_evidence_ids("google_analytics_4"),
            *[fact.evidence_id for fact in google_ads_facts[:12]],
            *[fact.evidence_id for fact in ga4_facts[:8]],
        ]
    )
    available_read_contracts = [
        "google_ads_campaign_activity",
        "google_ads_budget_context",
        "google_ads_impression_share_context",
        "ga4_landing_source_campaign_quality",
        DEMAND_GEN_READINESS_AVAILABLE_CONTRACT,
    ]
    campaign_rows = _campaign_context_rows_from_metric_facts(google_ads_facts)
    channel_counts = _campaign_channel_counts_from_context_rows(campaign_rows)
    if campaign_rows:
        available_read_contracts.append(DEMAND_GEN_CAMPAIGN_ROWS_CONTRACT)
    missing_read_contracts = [
        DEMAND_GEN_AD_GROUP_AD_ROWS_CONTRACT,
        DEMAND_GEN_CREATIVE_ASSET_ROWS_CONTRACT,
        DEMAND_GEN_LANDING_QUALITY_CONTRACT,
        DEMAND_GEN_TRANSITION_CONSTRAINTS_CONTRACT,
    ]
    if not campaign_rows:
        missing_read_contracts.insert(0, DEMAND_GEN_CAMPAIGN_ROWS_CONTRACT)
    demand_gen_rows = [
        row
        for row in campaign_rows
        if str(row.get("advertising_channel_type") or "").strip().upper()
        in {"DEMAND_GEN", "DISCOVERY"}
    ][:8]
    demand_gen_ad_group_ad_rows = demand_gen_ad_group_ad_rows_from_facts(
        google_ads_facts,
    )
    demand_gen_creative_asset_rows = demand_gen_creative_asset_rows_from_facts(
        google_ads_facts,
    )
    demand_gen_landing_quality_rows = demand_gen_landing_quality_rows_from_facts(
        ga4_facts,
        demand_gen_rows,
    )
    demand_gen_transition_constraint_rows = (
        demand_gen_transition_constraint_rows_from_campaigns(demand_gen_rows)
    )
    if demand_gen_contract_has_ready_fact(
        google_ads_facts,
        status_fact_name=DEMAND_GEN_AD_READ_STATUS_FACT,
        row_count_fact_name=DEMAND_GEN_AD_READ_ROW_COUNT_FACT,
    ) or demand_gen_ad_group_ad_rows:
        available_read_contracts.append(DEMAND_GEN_AD_GROUP_AD_ROWS_CONTRACT)
        missing_read_contracts = [
            contract
            for contract in missing_read_contracts
            if contract != DEMAND_GEN_AD_GROUP_AD_ROWS_CONTRACT
        ]
    if demand_gen_contract_has_ready_fact(
        google_ads_facts,
        status_fact_name=DEMAND_GEN_CREATIVE_ASSET_STATUS_FACT,
        row_count_fact_name=DEMAND_GEN_CREATIVE_ASSET_ROW_COUNT_FACT,
    ) or demand_gen_creative_asset_rows:
        available_read_contracts.append(DEMAND_GEN_CREATIVE_ASSET_ROWS_CONTRACT)
        missing_read_contracts = [
            contract
            for contract in missing_read_contracts
            if contract != DEMAND_GEN_CREATIVE_ASSET_ROWS_CONTRACT
        ]
    available_read_contracts.extend(
        [
            DEMAND_GEN_LANDING_QUALITY_CONTRACT,
            DEMAND_GEN_TRANSITION_CONSTRAINTS_CONTRACT,
        ]
    )
    payload = demand_gen_readiness_review_payload(
        campaign_rows_evaluated=len(campaign_rows),
        campaign_channel_counts=channel_counts,
        demand_gen_campaign_rows=demand_gen_rows,
        demand_gen_ad_group_ad_rows=[
            row.model_dump(mode="json") for row in demand_gen_ad_group_ad_rows
        ],
        demand_gen_creative_asset_rows=[
            row.model_dump(mode="json") for row in demand_gen_creative_asset_rows
        ],
        demand_gen_landing_quality_rows=[
            row.model_dump(mode="json") for row in demand_gen_landing_quality_rows
        ],
        demand_gen_transition_constraint_rows=[
            row.model_dump(mode="json") for row in demand_gen_transition_constraint_rows
        ],
        available_read_contracts=available_read_contracts,
        missing_read_contracts=missing_read_contracts,
        source_connectors=["google_ads", "google_analytics_4"],
        evidence_ids=evidence_ids,
    )
    if payload is None:
        return None
    action_metrics = _prioritize_action_metrics(
        [*google_ads_facts, *ga4_facts],
        required_names={"clicks", "impressions", "cost_micros", "active_users", "sessions"},
    )[:10]
    return ActionObject(
        id=DEMAND_GEN_READINESS_REVIEW_ACTION_ID,
        title="Przygotuj przegląd gotowości Demand Gen",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=evidence_ids[:12],
        metrics=action_metrics,
        human_diagnosis=(
            "WILQ ma kontekst Google Ads i GA4 do wstępnego przeglądu Demand Gen, "
            "ale nadal blokuje uruchomienie, przejście kampanii, werdykty kreatywne "
            "i zapis zmian bez osobnych odczytów assetów, kreacji, jakości "
            "stron wejścia i ograniczeń przejścia."
        ),
        recommended_reason=(
            "Na /ads-doctor/demand-gen sprawdź w WILQ materiał do sprawdzenia, sprawdź "
            "kanały kampanii i listę brakujących kontraktów. Nie przygotowuj "
            "kampanii ani przejścia kampanii bez kolejnych read contracts."
        ),
        payload=payload,
        validation_status="not_validated",
        created_by="system_metric_seed",
    )


def _latest_vendor_read_evidence_ids(connector_id: str) -> list[str]:
    for run in list_connector_refresh_runs(connector_id=connector_id):
        if run.mode == ConnectorRefreshMode.vendor_read:
            return run.evidence_ids
    return []


def _campaign_context_rows_from_metric_facts(facts: list[MetricFact]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str | None, str], list[MetricFact]] = {}
    for fact in facts:
        campaign_id = fact.dimensions.get("campaign_id")
        campaign_name = fact.dimensions.get("campaign_name")
        if not campaign_id and not campaign_name:
            continue
        grouped.setdefault((campaign_id, campaign_name or f"campaign {campaign_id}"), []).append(
            fact
        )
    rows: list[dict[str, Any]] = []
    for (campaign_id, campaign_name), group_facts in grouped.items():
        first_dimensions = group_facts[0].dimensions
        rows.append(
            {
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "campaign_status": first_dimensions.get("campaign_status"),
                "advertising_channel_type": first_dimensions.get("advertising_channel_type"),
                "clicks": _numeric_metric(group_facts, "clicks"),
                "impressions": _numeric_metric(group_facts, "impressions"),
                "cost_micros": _numeric_metric(group_facts, "cost_micros"),
                "conversions": _numeric_metric(group_facts, "conversions"),
                "conversion_value": _numeric_metric(group_facts, "conversion_value"),
                "evidence_ids": _unique(fact.evidence_id for fact in group_facts),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            str(row.get("advertising_channel_type") or ""),
            str(row.get("campaign_name") or ""),
        ),
    )


def _campaign_channel_counts_from_context_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        channel = str(row.get("advertising_channel_type") or "UNKNOWN").strip() or "UNKNOWN"
        counts[channel] = counts.get(channel, 0) + 1
    return dict(sorted(counts.items()))


def _numeric_metric(facts: list[MetricFact], name: str) -> float | int | None:
    value = next((fact.value for fact in facts if fact.name == name), None)
    if isinstance(value, int | float):
        return value
    return None


def _localo_action_metric_facts(facts: list[MetricFact]) -> list[MetricFact]:
    value_facts = [fact for fact in facts if not _is_probe_only_fact(fact)]
    if value_facts:
        return value_facts
    for run in list_connector_refresh_runs(connector_id="localo"):
        if run.status != ConnectorRefreshStatus.completed or not run.vendor_data_collected:
            continue
        facts_by_evidence = metric_store().list_metric_facts_by_evidence_ids(run.evidence_ids)
        value_facts = [
            fact
            for fact in facts_by_evidence
            if fact.source_connector == "localo" and not _is_probe_only_fact(fact)
        ]
        if value_facts:
            return value_facts
    return []


def _action_metric_facts() -> list[MetricFact]:
    facts: list[MetricFact] = []
    facts_by_connector = metric_store().list_latest_metric_facts_by_connector_limits(
        {
            connector_id: ACTION_METRIC_FACT_LIMITS.get(
                connector_id,
                ACTION_METRIC_FACT_LIMIT,
            )
            for connector_id in ACTION_METRIC_CONNECTORS
        },
    )
    google_ads_latest_facts = _latest_google_ads_metric_facts()
    if google_ads_latest_facts:
        facts_by_connector["google_ads"] = google_ads_latest_facts
    for connector_id in ACTION_METRIC_CONNECTORS:
        facts.extend(
            fact
            for fact in facts_by_connector.get(connector_id, [])
            if not _is_probe_only_fact(fact)
        )
    return _latest_metric_facts_by_identity(facts)


def _latest_google_ads_metric_facts() -> list[MetricFact]:
    latest_run = _latest_google_ads_vendor_read()
    if (
        latest_run is None
        or latest_run.status != ConnectorRefreshStatus.completed
        or not latest_run.vendor_data_collected
        or not latest_run.evidence_ids
    ):
        return []
    return [
        fact
        for fact in metric_store().list_metric_facts_by_evidence_ids(
            latest_run.evidence_ids
        )
        if fact.source_connector == "google_ads"
    ]


def _merchant_issue_clusters_payload(facts: list[MetricFact]) -> list[dict[str, Any]]:
    issue_facts = [
        fact
        for fact in facts
        if fact.name == "issue_product_count" and fact.dimensions.get("issue_type")
    ]
    grouped: dict[tuple[str, str, str, str, str, str], list[MetricFact]] = {}
    for fact in issue_facts:
        dimensions = fact.dimensions
        key = (
            dimensions.get("issue_type", "unknown_issue"),
            dimensions.get("affected_attribute", ""),
            dimensions.get("country", ""),
            dimensions.get("reporting_context", ""),
            dimensions.get("severity", "UNKNOWN"),
            dimensions.get("resolution", ""),
        )
        grouped.setdefault(key, []).append(fact)
    clusters: list[dict[str, Any]] = []
    for key, group_facts in grouped.items():
        issue_type, affected_attribute, country, reporting_context, severity, resolution = key
        sample_product_ids = _merchant_sample_values_for_cluster(
            facts,
            key,
            fact_name="sample_product_id",
        )
        sample_titles = _merchant_sample_values_for_cluster(
            facts,
            key,
            fact_name="sample_product_title",
        )
        clusters.append(
            {
                "issue_type": issue_type,
                "affected_attribute": affected_attribute or None,
                "country": country or None,
                "reporting_context": reporting_context or None,
                "severity": severity,
                "resolution": resolution or None,
                "product_count": sum(
                    int(fact.value)
                    for fact in group_facts
                    if isinstance(fact.value, int | float)
                ),
                "evidence_ids": _unique(fact.evidence_id for fact in group_facts),
                "sample_products_available": bool(sample_product_ids),
                "sample_product_ids": sample_product_ids,
                "sample_titles": sample_titles,
            }
        )
    return sorted(
        clusters,
        key=lambda cluster: (
            _merchant_severity_rank(str(cluster["severity"])),
            -int(cluster["product_count"]),
            str(cluster["issue_type"]),
        ),
    )[:10]


def _merchant_issue_payload_preview(
    issue_clusters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    preview_items: list[dict[str, Any]] = []
    for cluster in issue_clusters[:8]:
        product_count = int(cluster.get("product_count") or 0)
        cluster_id = _merchant_issue_cluster_id(cluster)
        preview_items.append(
            {
                "id": f"merchant_feed_issue_review_{cluster_id}",
                "preview_contract": MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT,
                "preview_contract_label": merchant_preview_contract_label(
                    MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT
                ),
                "operation_type": "MerchantIssueClusterReview",
                "cluster_id": cluster_id,
                "issue_type": cluster.get("issue_type"),
                "issue_type_label": merchant_display_label(cluster.get("issue_type")),
                "affected_attribute": cluster.get("affected_attribute"),
                "affected_attribute_label": merchant_display_label(
                    cluster.get("affected_attribute")
                ),
                "country": cluster.get("country"),
                "reporting_context": cluster.get("reporting_context"),
                "reporting_context_label": merchant_reporting_context_label(
                    cluster.get("reporting_context")
                ),
                "severity": cluster.get("severity"),
                "severity_label": merchant_severity_label(cluster.get("severity")),
                "resolution": cluster.get("resolution"),
                "resolution_label": merchant_resolution_label(
                    cluster.get("resolution")
                ),
                "metric_snapshot": {"issue_product_count": product_count},
                "metric_snapshot_labels": merchant_metric_snapshot_labels(
                    {"issue_product_count": product_count}
                ),
                "sample_products_available": bool(cluster.get("sample_product_ids")),
                "sample_product_ids": cluster.get("sample_product_ids", []),
                "sample_titles": cluster.get("sample_titles", []),
                "sample_unavailable_reason": None
                if cluster.get("sample_product_ids")
                else (
                    "Obecny kontrakt Merchant zwraca wymiary problemu i liczbę "
                    "wystąpień, ale nie zwraca przykładowych produktów ani tytułów."
                ),
                "reason": (
                    "Podgląd klastra problemów feedu do sprawdzenia. WILQ może "
                    "przygotować kolejkę przeglądu, ale nie może zmienić feedu ani "
                    "obiecać przywrócenia zatwierdzenia bez osobnego kontraktu zapisu i audytu."
                ),
                "required_validation": [
                    "review_issue_type_and_attribute",
                    "review_reporting_context",
                    "prepare_feed_fix_preview",
                    "human_confirm_before_apply",
                    "mutation_audit_required",
                ],
                "blocked_claims": [
                    "ponowne zatwierdzenie produktu",
                    "odzyskany przychód",
                    "automatyczna zmiana feedu",
                    "nadpisanie głównego feedu",
                    "zapis do feedu",
                    "zmiana danych produktu",
                    "automatyczna naprawa zatwierdzenia",
                ],
                "evidence_ids": cluster.get("evidence_ids", []),
                "api_mutation_ready": False,
                "apply_allowed": False,
                "destructive": False,
            }
        )
    return preview_items


def _merchant_sample_values_for_cluster(
    facts: list[MetricFact],
    key: tuple[str, str, str, str, str, str],
    *,
    fact_name: str,
) -> list[str]:
    issue_type, affected_attribute, country, reporting_context, severity, resolution = key
    values = [
        str(fact.value)
        for fact in sorted(
            facts,
            key=lambda fact: fact.dimensions.get("sample_index", ""),
        )
        if fact.name == fact_name
        and fact.dimensions.get("issue_type") == issue_type
        and _merchant_attribute_matches(
            fact.dimensions.get("affected_attribute"),
            affected_attribute,
        )
        and (fact.dimensions.get("country") or "") == country
        and (fact.dimensions.get("reporting_context") or "") == reporting_context
        and fact.dimensions.get("severity") == severity
        and (fact.dimensions.get("resolution") or "") == resolution
        and isinstance(fact.value, str)
    ]
    return _unique(values)[:10]


def _merchant_attribute_matches(left: str | None, right: str | None) -> bool:
    return _merchant_attribute_key(left) == _merchant_attribute_key(right)


def _merchant_attribute_key(value: str | None) -> str:
    normalized = (value or "").removeprefix("n:").strip().lower()
    return normalized.replace("_", " ")


def _merchant_issue_cluster_id(cluster: dict[str, Any]) -> str:
    return (
        f"merchant_issue_{_stable_slug(str(cluster.get('country') or 'global'))}_"
        f"{_stable_slug(str(cluster.get('severity') or 'UNKNOWN'))}_"
        f"{_stable_slug(str(cluster.get('issue_type') or 'unknown_issue'))}_"
        f"{_stable_slug(str(cluster.get('affected_attribute') or 'attribute_unknown'))}_"
        f"{_stable_slug(str(cluster.get('reporting_context') or 'all_contexts'))}_"
        f"{_stable_slug(str(cluster.get('resolution') or 'resolution_unknown'))}"
    )


def _stable_slug(value: str) -> str:
    lowered = value.lower()
    chars = [char if char.isalnum() else "_" for char in lowered]
    return "_".join("".join(chars).split("_")) or "unknown"


def _merchant_issue_metric_facts(facts: list[MetricFact]) -> list[MetricFact]:
    return [
        fact
        for fact in facts
        if fact.name == "issue_product_count" and fact.dimensions.get("issue_type")
    ]


def _ga4_dimensioned_metric_facts(facts: list[MetricFact]) -> list[MetricFact]:
    return [
        fact
        for fact in facts
        if fact.dimensions.get("landing_page")
        or fact.dimensions.get("source_medium")
        or fact.dimensions.get("campaign_name")
    ]


def _merchant_severity_rank(severity: str) -> int:
    return {"DISAPPROVED": 0, "DEMOTED": 1, "NOT_IMPACTED": 2}.get(severity, 3)


def _latest_metric_facts_by_identity(metric_facts: list[MetricFact]) -> list[MetricFact]:
    latest_by_key: dict[tuple[str, str, tuple[tuple[str, str], ...]], MetricFact] = {}
    for fact in metric_facts:
        key = (
            fact.source_connector,
            fact.name,
            tuple(sorted(fact.dimensions.items())),
        )
        current = latest_by_key.get(key)
        if current is None or _metric_fact_sort_time(fact) > _metric_fact_sort_time(current):
            latest_by_key[key] = fact
    return sorted(
        latest_by_key.values(),
        key=lambda fact: _metric_fact_sort_time(fact),
        reverse=True,
    )


def _metric_fact_sort_time(fact: MetricFact) -> str:
    if fact.collected_at is None:
        return ""
    return fact.collected_at.isoformat()


def _wordpress_draft_handoff_action(
    *,
    content_payload: dict[str, Any] | None,
    content_action_metrics: list[MetricFact],
) -> ActionObject | None:
    if content_payload is None:
        return None
    brief_previews = [
        item
        for item in content_payload.get("content_brief_preview", [])
        if isinstance(item, dict) and isinstance(item.get("candidate_id"), str)
    ]
    if not brief_previews:
        return None
    preview_items = [
        _wordpress_draft_handoff_preview_item(item)
        for item in brief_previews[:4]
    ]
    return ActionObject(
        id="act_prepare_wordpress_draft_handoff",
        title="Przygotuj zablokowany podgląd szkicu WordPress",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=_unique(fact.evidence_id for fact in content_action_metrics),
        metrics=content_action_metrics,
        human_diagnosis=(
            "WILQ ma kolejkę treści z GSC/WordPress/Ahrefs i może przygotować "
            "wyłącznie zablokowany podgląd szkicu WordPress. To nie jest zapis "
            "ani publikacja."
        ),
        recommended_reason=(
            "Użyj tej akcji jako checklisty przed przyszłym szkicem WordPress: "
            "najpierw finalny URL, canonical, duplicate/cannibalization, legal/factual "
            "i przegląd człowieka. Bez tych bramek szkic pozostaje zablokowany."
        ),
        payload={
            "action_type": "wordpress_draft_handoff",
            "connector": "wordpress_ekologus",
            "mode": "prepare_only",
            "preview_contract": "wordpress_draft_handoff_preview_v1",
            "depends_on_action_id": "act_prepare_content_refresh_queue",
            "source_connectors": content_payload.get("source_connectors", []),
            "source_metric_names": content_payload.get("source_metric_names", []),
            "required_input_contracts": [
                "content_brief_preview_v1",
                "content_draft_generation_v1",
                "content_draft_readiness_review_v1",
                "wordpress_draft_handoff_v1",
                "post_publication_measurement_plan_v1",
            ],
            "payload_preview": preview_items,
            "required_validation": [
                "content_url_preflight_review",
                "final_canonical_review",
                "duplicate_or_cannibalization_check",
                "legal_factual_review",
                "content_draft_readiness_review",
                "wordpress_draft_payload_preview",
                "human_confirm_before_wordpress_write",
            ],
            "blocked_claims": [
                "wordpress_draft_write",
                "wordpress_publish",
                "production_wordpress_write",
                "publish_ready_claim",
                "obietnica wzrostu pozycji albo leadów",
            ],
            "apply_allowed": False,
            "api_mutation_ready": False,
            "destructive": False,
        },
        validation_status="not_validated",
        created_by="system_metric_seed",
    )


def _wordpress_draft_handoff_preview_item(item: dict[str, Any]) -> dict[str, Any]:
    source_public_url = (
        item.get("source_public_url")
        if isinstance(item.get("source_public_url"), str)
        else item.get("source_url")
        if isinstance(item.get("source_url"), str)
        else item.get("target_url")
    )
    intended_final_url = (
        item.get("intended_final_url")
        if isinstance(item.get("intended_final_url"), str)
        else source_public_url
    )
    final_canonical_url = (
        item.get("final_canonical_url")
        if isinstance(item.get("final_canonical_url"), str)
        else intended_final_url
    )
    required_validation = [
        "content_url_preflight_review",
        "final_canonical_review",
        "duplicate_or_cannibalization_check",
        "legal_factual_review",
        "content_draft_readiness_review",
        "human_confirm_before_wordpress_write",
    ]
    blocked_claims = [
        "wordpress_draft_write",
        "wordpress_publish",
        "publish_ready_claim",
        "obietnica wzrostu pozycji albo leadów",
    ]
    measurement_plan = post_publication_measurement_plan(
        final_canonical_url=str(final_canonical_url) if final_canonical_url else None,
    )
    return {
        "preview_contract": "wordpress_draft_handoff_preview_v1",
        "operation_type": "wordpress_draft_handoff_review",
        "candidate_id": item.get("candidate_id"),
        "topic": item.get("topic"),
        "source_url": item.get("target_url"),
        "source_public_url": source_public_url,
        "intended_final_url": intended_final_url,
        "final_canonical_url": final_canonical_url,
        "preview_url": item.get("preview_url")
        if isinstance(item.get("preview_url"), str)
        else None,
        "canonical_gate_status": item.get("canonical_gate_status"),
        "canonical_gate_status_label": content_contract_label(
            str(item.get("canonical_gate_status") or "")
        ),
        "duplicate_gate_status": item.get("duplicate_gate_status"),
        "duplicate_gate_status_label": content_contract_label(
            str(item.get("duplicate_gate_status") or "")
        ),
        "wordpress_draft_handoff_status": "blocked_until_draft_gates_pass",
        "wordpress_draft_handoff_summary": [
            "status: zablokowany do przejścia kontroli szkicu"
        ],
        "required_next_action_contract": "wordpress_draft_handoff_v1",
        "required_next_action_label": content_contract_label("wordpress_draft_handoff_v1"),
        "post_publication_measurement_plan": measurement_plan,
        "post_publication_measurement_summary": post_publication_measurement_summary(
            measurement_plan
        ),
        "required_validation": required_validation,
        "required_validation_labels": content_contract_labels(required_validation),
        "blocked_claims": blocked_claims,
        "blocked_claim_labels": content_contract_labels(blocked_claims),
        "apply_allowed": False,
        "api_mutation_ready": False,
        "destructive": False,
    }


def _social_draft_actions(social_facts: list[MetricFact]) -> dict[str, ActionObject]:
    actions: dict[str, ActionObject] = {}
    social_source_facts = [
        fact for fact in social_facts if _is_social_source_metric(fact)
    ]
    social_metrics = _prioritize_action_metrics(
        social_source_facts,
        required_names={
            "clicks",
            "impressions",
            "issue_product_count",
            "active_users",
            "content_object_seen",
        },
    )[:10]
    evidence_ids = _unique(
        [
            *[fact.evidence_id for fact in social_metrics],
            connector_evidence_id("linkedin"),
            connector_evidence_id("facebook"),
        ]
    )
    common_payload = {
        "mode": "prepare_only",
        "source_connectors": _unique(fact.source_connector for fact in social_source_facts),
        "source_metric_names": _unique(fact.name for fact in social_source_facts),
        "draft_constraints": [
            "use_only_wilq_evidence",
            "write_in_polish",
            "no_performance_claims_without_source_metric",
            "no_publishing_without_connector_credentials",
            "require_human_review_before_apply",
        ],
        "source_inputs": _social_source_inputs(social_metrics),
        "blocked_claims": ["zwrot z reklam", "przychód", "wzrost konwersji", "wdrożona poprawka produktu"],
        "destructive": False,
    }
    for connector_id, action_type, title in (
        (
            "linkedin",
            "linkedin_post_candidate",
            "Przygotuj propozycje postów LinkedIn z dowodów WILQ",
        ),
        (
            "facebook",
            "facebook_post_candidate",
            "Przygotuj propozycje postów Facebook z dowodów WILQ",
        ),
    ):
        action = ActionObject(
            id=f"act_prepare_{connector_id}_social_drafts",
            title=title,
            domain=OpportunityDomain.social,
            connector=connector_id,
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=evidence_ids,
            metrics=social_metrics,
            human_diagnosis=(
                "WILQ ma realne dane GSC/GA4/Merchant/WordPress, które można "
                "przełożyć na bezpieczne do sprawdzenia kierunki postów. Brak uprawnień social "
                "blokuje publikację, ale nie blokuje przygotowania materiału do oceny."
            ),
            recommended_reason=(
                "Na /social-publisher pokaż tylko propozycje szkiców z dowodami. "
                "Nie publikuj, nie planuj wysyłki i nie dopisuj obietnic bez metryk."
            ),
            payload={
                **common_payload,
                "action_type": action_type,
                "connector": connector_id,
            },
            validation_status="not_validated",
            created_by="system_metric_seed",
        )
        actions[action.id] = action
    return actions


def _is_social_source_metric(fact: MetricFact) -> bool:
    if fact.name != "content_object_seen":
        return True
    content_url = fact.dimensions.get("content_url")
    if not isinstance(content_url, str) or not content_url:
        return True
    host = urlparse(content_url).netloc.lower()
    if not host:
        return True
    return "dev.proudsite.pl" not in host


def _social_source_inputs(facts: list[MetricFact]) -> list[dict[str, object]]:
    inputs: list[dict[str, object]] = []
    for fact in facts[:8]:
        inputs.append(
            {
                "source_connector": fact.source_connector,
                "metric_name": fact.name,
                "value": fact.value,
                "context_summary": _social_source_context_summary(fact),
                "evidence_id": fact.evidence_id,
            }
        )
    return inputs


def _social_source_context_summary(fact: MetricFact) -> str:
    dimensions = fact.dimensions
    if fact.source_connector == "google_merchant_center":
        return "zgłoszenie problemu danych produktowych Merchant Center"
    if fact.source_connector == "wordpress_ekologus":
        title = dimensions.get("title_or_h1")
        url = dimensions.get("canonical_url") or dimensions.get("content_url")
        parts = [str(value) for value in (title, url) if isinstance(value, str) and value]
        return " | ".join(parts[:2]) or "wpis lub strona z publicznego spisu treści"
    if fact.source_connector == "google_search_console":
        query = dimensions.get("query")
        page = dimensions.get("page")
        parts = [str(value) for value in (query, page) if isinstance(value, str) and value]
        return " | ".join(parts[:2]) or "sygnał z Google Search Console"
    if fact.source_connector == "google_analytics_4":
        page = dimensions.get("landing_page") or dimensions.get("page_path")
        source = dimensions.get("session_source_medium") or dimensions.get("source_medium")
        parts = [str(value) for value in (page, source) if isinstance(value, str) and value]
        return " | ".join(parts[:2]) or "sygnał z GA4"
    return "sygnał źródłowy WILQ"


def _facts_by_connector(facts: list[MetricFact]) -> dict[str, list[MetricFact]]:
    grouped: dict[str, list[MetricFact]] = {}
    for fact in facts:
        grouped.setdefault(fact.source_connector, []).append(fact)
    return grouped


def _metric_sentence(facts: list[MetricFact]) -> str:
    if not facts:
        return "Najważniejsze fakty: brak metryk do pokazania"
    samples = ", ".join(
        f"{_metric_fact_label(fact.name)}: {fact.value}" for fact in facts[:4]
    )
    if len(facts) > 4:
        return f"Najważniejsze fakty: {samples} i kolejne sygnały w dowodach"
    return f"Najważniejsze fakty: {samples}"


def _metric_fact_label(name: str) -> str:
    labels = {
        "issue_product_count": "zgłoszenia problemów",
        "sample_product_id": "przykładowe produkty",
        "active_users": "aktywni użytkownicy",
        "engagement_rate": "zaangażowanie",
        "ecommerce_purchases": "zakupy e-commerce",
        "key_events": "zdarzenia kluczowe",
        "clicks": "kliknięcia",
        "impressions": "wyświetlenia",
        "ctr": "CTR",
        "position": "średnia pozycja",
        "content_gap_count": "luki treści",
        "keyword_count": "liczba fraz",
        "visibility_score": "widoczność",
    }
    return labels.get(name, "metryka źródłowa")


def _prioritize_action_metrics(
    facts: list[MetricFact],
    *,
    required_names: set[str],
) -> list[MetricFact]:
    required: list[MetricFact] = []
    remaining: list[MetricFact] = []
    seen_required: set[str] = set()
    for fact in facts:
        if fact.name in required_names and fact.name not in seen_required:
            required.append(fact)
            seen_required.add(fact.name)
        else:
            remaining.append(fact)
    return [*required, *remaining]


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
        errors.append("Akcja wymaga co najmniej jednego dowodu źródłowego.")
    if connector is None:
        errors.append(f"Nieznany łącznik danych: {action.connector}")
    elif action.mode == ActionMode.apply and not connector.configured:
        errors.append(f"Łącznik danych {action.connector} nie jest skonfigurowany.")
    errors.extend(validate_action_payload(action.connector, action.payload))
    if action.risk in {ActionRisk.high, ActionRisk.critical}:
        warnings.append(
            "Akcje o wysokim i krytycznym ryzyku wymagają osobnego wsparcia produktu."
        )
    valid = not errors
    action.validation_status = "valid" if valid else "invalid"
    if not valid:
        action.status = ActionStatus.validation_failed
    elif action.mode == ActionMode.apply:
        action.status = ActionStatus.ready_to_apply
    else:
        action.status = ActionStatus.ready
    action.review_gate = _action_review_gate(action)
    return ActionValidationResult(
        action_id=action.id,
        valid=valid,
        status="valid" if valid else "invalid",
        status_label=_action_result_status_label("valid" if valid else "invalid"),
        errors=errors,
        warnings=warnings,
    )


def record_action_review(
    action: ActionObject,
    request: ActionReviewRequest,
) -> ActionReviewResult:
    audit = AuditEvent(
        id=f"audit_{action.id}_human_review_{uuid4().hex[:12]}",
        action_id=action.id,
        event_type=f"human_review_{request.outcome}",
        event_type_label=_action_audit_event_label(f"human_review_{request.outcome}"),
        actor=request.reviewed_by,
        summary=_action_review_summary(request),
        evidence_ids=action.evidence_ids,
        details=_action_review_details(request),
    )
    action.audit_events = [audit, *action.audit_events]
    action.review_gate = _action_review_gate(action)
    return ActionReviewResult(
        action_id=action.id,
        status="recorded",
        status_label=_action_result_status_label("recorded"),
        audit_event=_audit_event_with_operator_label(audit),
        review_gate=_review_gate_with_operator_labels(action.review_gate),
    )


def preview_action(
    action: ActionObject,
    request: ActionPreviewRequest | None = None,
) -> ActionPreviewResult:
    preview_request = request or ActionPreviewRequest()
    action.review_gate = _action_review_gate(action)
    preview_items = _payload_preview_items(action.payload)
    included_items = preview_items[: preview_request.max_items]
    blockers = _action_preview_blockers(action, preview_items)
    status: Literal["preview_ready", "blocked"] = "blocked" if blockers else "preview_ready"
    audit = AuditEvent(
        id=f"audit_{action.id}_preview_{uuid4().hex[:12]}",
        action_id=action.id,
        event_type="action_preview_generated",
        event_type_label=_action_audit_event_label("action_preview_generated"),
        actor=preview_request.requested_by or "wilq_api",
        summary=_action_preview_summary(
            status=status,
            included_items=len(included_items),
            preview_items=len(preview_items),
        ),
        evidence_ids=action.evidence_ids,
    )
    action.audit_events = [audit, *action.audit_events]
    return ActionPreviewResult(
        action_id=action.id,
        status=status,
        status_label=_action_result_status_label(status),
        dry_run=True,
        mutation_allowed=False,
        preview_contract=_preview_contract(action.payload, preview_items),
        preview_items=included_items,
        preview_items_total=len(preview_items),
        omitted_items=max(len(preview_items) - len(included_items), 0),
        blockers=blockers,
        blocker_labels=_action_gate_labels(blockers),
        audit_event=_audit_event_with_operator_label(audit),
        review_gate=_review_gate_with_operator_labels(action.review_gate),
    )


def confirm_action(
    action: ActionObject,
    request: ActionConfirmRequest,
) -> ActionConfirmResult:
    action.review_gate = _action_review_gate(action)
    latest_preview = _latest_preview_event(action.audit_events)
    blockers = _action_confirmation_blockers(action, request, latest_preview)
    confirmed = not blockers
    audit = AuditEvent(
        id=f"audit_{action.id}_confirm_{uuid4().hex[:12]}",
        action_id=action.id,
        event_type=_action_confirmation_event_type(action, confirmed),
        event_type_label=_action_audit_event_label(
            _action_confirmation_event_type(action, confirmed)
        ),
        actor=request.confirmed_by,
        summary=_action_confirmation_summary(action, request, blockers, latest_preview),
        evidence_ids=action.evidence_ids,
    )
    action.audit_events = [audit, *action.audit_events]
    action.review_gate = _action_review_gate(action)
    return ActionConfirmResult(
        action_id=action.id,
        confirmed=confirmed,
        status="confirmed" if confirmed else "blocked",
        status_label=_action_result_status_label("confirmed" if confirmed else "blocked"),
        blockers=blockers,
        blocker_labels=_action_gate_labels(blockers),
        audit_event=_audit_event_with_operator_label(audit),
        review_gate=_review_gate_with_operator_labels(action.review_gate),
    )


def impact_check_action(
    action: ActionObject,
    request: ActionImpactCheckRequest,
) -> ActionImpactCheckResult:
    action.review_gate = _action_review_gate(action)
    latest_confirmation = _latest_action_confirmation_event(action.audit_events)
    blockers = _action_impact_check_blockers(action, latest_confirmation)
    status: Literal["checked", "blocked"] = "blocked" if blockers else "checked"
    evidence_ids = _unique([*action.evidence_ids, *(fact.evidence_id for fact in action.metrics)])
    source_connectors = _unique(
        [fact.source_connector for fact in action.metrics if fact.source_connector]
    )
    if not source_connectors:
        source_connectors = [action.connector]
    audit = AuditEvent(
        id=f"audit_{action.id}_impact_{uuid4().hex[:12]}",
        action_id=action.id,
        event_type="action_impact_check_completed"
        if status == "checked"
        else "action_impact_check_blocked",
        event_type_label=_action_audit_event_label(
            "action_impact_check_completed"
            if status == "checked"
            else "action_impact_check_blocked"
        ),
        actor=request.checked_by,
        summary=_action_impact_check_summary(
            request=request,
            status=status,
            metric_fact_count=len(action.metrics),
            source_connectors=source_connectors,
            blockers=blockers,
        ),
        evidence_ids=evidence_ids,
    )
    action.audit_events = [audit, *action.audit_events]
    action.review_gate = _action_review_gate(action)
    return ActionImpactCheckResult(
        action_id=action.id,
        status=status,
        status_label=_action_result_status_label(status),
        pre_window_days=request.pre_window_days,
        post_window_days=request.post_window_days,
        metric_fact_count=len(action.metrics),
        source_connectors=source_connectors,
        source_connector_labels=source_connector_labels(source_connectors),
        evidence_ids=evidence_ids,
        evidence_summary_label=evidence_count_label(evidence_ids),
        blockers=blockers,
        blocker_labels=_action_gate_labels(blockers),
        audit_event=_audit_event_with_operator_label(audit),
        review_gate=_review_gate_with_operator_labels(action.review_gate),
    )


def apply_action(
    action: ActionObject,
    request: ActionApplyRequest | None = None,
) -> ActionApplyResult:
    errors: list[str] = []
    connector = get_connector_status(action.connector)
    latest_preview = _latest_preview_event(action.audit_events)
    latest_confirmation = _latest_action_confirmation_event(action.audit_events)
    latest_impact_check = _latest_action_impact_check_event(action.audit_events)
    mutation_adapter = _supported_mutation_adapter(action)
    if request is None or request.confirm is not True:
        errors.append("Wymagane jest jawne potwierdzenie zapisu zmian.")
    if request is not None and request.confirm is True and not request.confirmed_by:
        errors.append("Brakuje osoby potwierdzającej zapis zmian.")
    if latest_preview is None:
        errors.append("Przed zapisem zmian wymagany jest podgląd zmian.")
    if latest_confirmation is None:
        errors.append("Przed zapisem zmian wymagany jest zapis audytu potwierdzenia.")
    if _impact_status_from_event(latest_impact_check) != "checked":
        errors.append("Przed zapisem zmian wymagane jest sprawdzenie efektu.")
    if action.validation_status != "valid":
        errors.append("Akcja musi być sprawdzona w WILQ przed zapisem zmian.")
    if action.mode != ActionMode.apply:
        errors.append("Akcja nie ma trybu zapisu zmian w zewnętrznym systemie.")
    if not action.evidence_ids:
        errors.append("Akcja nie może zapisać zmian bez dowodów źródłowych.")
    if connector is None or not connector.configured:
        errors.append("Brakuje skonfigurowanego źródła danych do zapisu zmian.")
    if action.risk in {ActionRisk.high, ActionRisk.critical}:
        errors.append("Zapisy zmian o wysokim i krytycznym ryzyku są zablokowane w Goal 001.")
    if action.payload.get("destructive") is True:
        errors.append("Destrukcyjne zmiany nie są zaimplementowane w Goal 001.")
    if mutation_adapter is None:
        errors.append("Brakuje bezpiecznej ścieżki zapisu zmian dla tej akcji.")

    actor = request.confirmed_by if request and request.confirmed_by else "wilq_api"
    audit = AuditEvent(
        id=f"audit_{action.id}_{len(action.audit_events) + 1}",
        action_id=action.id,
        event_type=_apply_audit_event_type(errors),
        event_type_label=_action_audit_event_label(_apply_audit_event_type(errors)),
        actor=actor,
        summary="; ".join(errors) if errors else "Zmiany zapisane przez sprawdzoną ścieżkę API.",
        evidence_ids=action.evidence_ids,
    )
    mutation_audit = _action_mutation_audit_record(
        action=action,
        audit_event=audit,
        actor=actor,
        errors=errors,
        mutation_adapter=mutation_adapter,
    )
    action.audit_events.append(audit)
    if errors:
        action.status = ActionStatus.blocked
        action.review_gate = _action_review_gate(action)
        return ActionApplyResult(
            action_id=action.id,
            applied=False,
            status="blocked",
            status_label=_action_result_status_label("blocked"),
            audit_event=_audit_event_with_operator_label(audit),
            mutation_audit=mutation_audit,
            errors=errors,
        )
    action.status = ActionStatus.applied
    action.review_gate = _action_review_gate(action)
    return ActionApplyResult(
        action_id=action.id,
        applied=True,
        status="applied",
        status_label=_action_result_status_label("applied"),
        audit_event=_audit_event_with_operator_label(audit),
        mutation_audit=mutation_audit,
    )


def _apply_audit_event_type(errors: list[str]) -> str:
    if not errors:
        return "apply_succeeded"
    confirmation_errors = {
        "Wymagane jest jawne potwierdzenie zapisu zmian.",
        "Brakuje osoby potwierdzającej zapis zmian.",
    }
    if any(error in confirmation_errors for error in errors):
        return "apply_confirmation_missing"
    return "apply_blocked"


def _action_mutation_audit_record(
    *,
    action: ActionObject,
    audit_event: AuditEvent,
    actor: str,
    errors: list[str],
    mutation_adapter: str | None,
) -> ActionMutationAuditRecord:
    status: Literal["blocked", "applied"] = "blocked" if errors else "applied"
    action_type = action.payload.get("action_type")
    return ActionMutationAuditRecord(
        id=f"mutation_{action.id}_{uuid4().hex[:12]}",
        action_id=action.id,
        connector=action.connector,
        action_type=action_type if isinstance(action_type, str) else None,
        status=status,
        status_label=_action_mutation_audit_status_label(status),
        mutation_attempted=status == "applied",
        mutation_adapter=mutation_adapter,
        actor=actor,
        audit_event_id=audit_event.id,
        evidence_ids=action.evidence_ids,
        blockers=errors,
        summary=_mutation_audit_summary(errors, mutation_adapter),
    )


def _mutation_audit_summary(errors: list[str], mutation_adapter: str | None) -> str:
    if errors:
        return (
            "Mutation blocked before any vendor API call. "
            f"Blockers: {', '.join(errors)}"
        )
    adapter = mutation_adapter or "unknown"
    return f"Mutation executed through adapter {adapter}; vendor payload remains redacted."


def _supported_mutation_adapter(action: ActionObject) -> str | None:
    return None


def _with_persisted_review_gates(actions: Iterable[ActionObject]) -> list[ActionObject]:
    action_list = list(actions)
    action_ids = {action.id for action in action_list}
    audit_events_by_action_id = _persisted_audit_events_by_action_id(action_ids)
    mutation_audits_by_action_id = _persisted_mutation_audits_by_action_id(action_ids)
    return [
        _with_review_gate(
            action,
            audit_events_by_action_id.get(action.id, []),
            mutation_audits_by_action_id.get(action.id, []),
        )
        for action in action_list
    ]


def _with_review_gate(
    action: ActionObject,
    audit_events: list[AuditEvent] | None = None,
    mutation_audits: list[ActionMutationAuditRecord] | None = None,
) -> ActionObject:
    if audit_events is not None:
        action.audit_events = [
            event for event in audit_events[:10] if not _is_obsolete_content_review_event(event)
        ]
    action.payload = content_payload_with_reviewed_wordpress_draft_previews(
        action.payload,
        review_event_summaries=(
            event.summary
            for event in action.audit_events
            if event.event_type == "human_review_approved_for_prepare"
        ),
        review_event_details=(
            event.details
            for event in action.audit_events
            if event.event_type == "human_review_approved_for_prepare"
        ),
    )
    action.payload = _payload_with_operator_labels(action.payload)
    action.review_gate = _action_review_gate(action, mutation_audits)
    return _action_with_operator_labels(action)


def _action_with_operator_labels(action: ActionObject) -> ActionObject:
    connector = get_connector_status(action.connector)
    return action.model_copy(
        update={
            "connector_label": connector.label if connector is not None else "źródło danych",
            "mode_label": _action_mode_label(action.mode),
            "risk_label": _action_risk_label(action.risk),
            "status_label": _action_status_label(action.status),
            "evidence_summary_label": _action_evidence_summary_label(
                action.evidence_ids
            ),
            "validation_status_label": _action_validation_status_label(
                action.validation_status
            ),
            "review_gate": _review_gate_with_operator_labels(action.review_gate),
            "preview_cards": _action_preview_cards(action),
            "audit_events": [
                _audit_event_with_operator_label(event) for event in action.audit_events
            ],
        }
    )


def _action_preview_cards(action: ActionObject) -> list[ActionPreviewCardViewModel]:
    if action.payload.get("preview_contract") == MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT:
        return _merchant_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "budget_apply_preview_v1":
        return _ads_budget_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "recommendation_apply_preview_v1":
        return _ads_recommendation_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "custom_segment_change_preview_v1":
        return _ads_custom_segment_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "negative_keyword_change_preview_v1":
        return _ads_negative_keyword_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "demand_gen_readiness_review_preview_v1":
        return _demand_gen_readiness_preview_cards(action.payload)
    return []


def _ads_budget_preview_cards(payload: dict[str, Any]) -> list[ActionPreviewCardViewModel]:
    preview_items = [
        item
        for item in payload.get("budget_payload_preview", [])
        if isinstance(item, dict)
    ]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        safety_review = item.get("safety_review") if isinstance(item.get("safety_review"), dict) else {}
        rows = [
            _preview_row("Kampania", str(item.get("campaign_name") or "kampania do sprawdzenia")),
            _preview_row(
                "Budżet",
                str(item.get("campaign_budget_name") or "budżet kampanii do sprawdzenia"),
            ),
            _preview_row(
                "Obecny budżet",
                _micros_money_label(item.get("current_budget_amount_micros")),
            ),
            _preview_row(
                "Propozycja",
                _micros_money_label(item.get("proposed_budget_amount_micros")),
            ),
            _preview_row(
                "Bezpieczeństwo",
                str(safety_review.get("status_label") or "wymaga sprawdzenia"),
            ),
        ]
        missing_requirement_labels = _string_list(safety_review.get("missing_requirement_labels"))
        if missing_requirement_labels:
            rows.append(_preview_row("Braki", ", ".join(missing_requirement_labels[:4])))
        requirement_labels = _string_list(item.get("required_validation_labels"))
        if requirement_labels:
            rows.append(_preview_row("Warunki sprawdzenia", ", ".join(requirement_labels[:4])))
        blocked_claim_labels = _string_list(item.get("blocked_claim_labels"))
        if blocked_claim_labels:
            rows.append(
                _preview_row(
                    "Czego nie wolno twierdzić",
                    ", ".join(blocked_claim_labels[:4]),
                )
            )
        cards.append(
            ActionPreviewCardViewModel(
                id=f"ads_budget_preview_{index}",
                kind="google_ads_budget_review",
                title_label="Budżet kampanii do sprawdzenia",
                subtitle_label=str(
                    item.get("operation_type_label") or "ocena budżetu bez zapisu zmian"
                ),
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=_apply_state_label(item.get("apply_allowed")),
                system_readiness_label=_system_readiness_label(
                    item.get("api_mutation_ready")
                ),
            )
        )
    return cards


def _ads_recommendation_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    preview_items = [
        item
        for item in payload.get("payload_preview", [])
        if isinstance(item, dict)
    ]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        rows = [
            _preview_row(
                "Typ rekomendacji",
                str(item.get("recommendation_type_label") or "rekomendacja do sprawdzenia"),
            ),
            _preview_row(
                "Kampania",
                "powiązana kampania do sprawdzenia"
                if item.get("campaign_id")
                else "brak powiązanej kampanii",
            ),
            _preview_row(
                "Budżet kampanii",
                "powiązany budżet do sprawdzenia"
                if item.get("campaign_budget_id")
                else "brak powiązanego budżetu",
            ),
        ]
        requirement_labels = _string_list(item.get("required_validation_labels"))
        if requirement_labels:
            rows.append(_preview_row("Warunki sprawdzenia", ", ".join(requirement_labels[:4])))
        blocked_claim_labels = _string_list(item.get("blocked_claim_labels"))
        if blocked_claim_labels:
            rows.append(
                _preview_row(
                    "Czego nie wolno twierdzić",
                    ", ".join(blocked_claim_labels[:4]),
                )
            )
        cards.append(
            ActionPreviewCardViewModel(
                id=str(item.get("id") or f"ads_recommendation_preview_{index}"),
                kind="google_ads_recommendation_review",
                title_label="Rekomendacja Google Ads do sprawdzenia",
                subtitle_label=str(
                    item.get("operation_type_label") or "ocena rekomendacji bez zapisu zmian"
                ),
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=_apply_state_label(item.get("apply_allowed")),
                system_readiness_label=_system_readiness_label(
                    item.get("api_mutation_ready")
                ),
            )
        )
    return cards


def _ads_negative_keyword_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    preview_items = [
        item
        for item in payload.get("payload_preview", [])
        if isinstance(item, dict)
    ]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        rows = [
            _preview_row("Hasło", str(item.get("search_term") or "hasło do sprawdzenia")),
            _preview_row(
                "Wykluczenie",
                str(item.get("negative_keyword_text") or "wykluczenie do sprawdzenia"),
            ),
            _preview_row(
                "Dopasowanie",
                str(item.get("match_type_label") or "dopasowanie do sprawdzenia"),
            ),
            _preview_row("Poziom", str(item.get("level_label") or "poziom do sprawdzenia")),
            _preview_row(
                "Kampania",
                str(item.get("campaign_name") or "kampania do sprawdzenia"),
            ),
            _preview_row(
                "Grupa reklam",
                str(item.get("ad_group_name") or "grupa reklam do sprawdzenia"),
            ),
        ]
        requirement_labels = _string_list(item.get("required_validation_labels"))
        if requirement_labels:
            rows.append(_preview_row("Warunki sprawdzenia", ", ".join(requirement_labels[:4])))
        blocked_claim_labels = _string_list(item.get("blocked_claim_labels"))
        if blocked_claim_labels:
            rows.append(
                _preview_row(
                    "Czego nie wolno twierdzić",
                    ", ".join(blocked_claim_labels[:4]),
                )
            )
        cards.append(
            ActionPreviewCardViewModel(
                id=f"ads_negative_keyword_preview_{index}",
                kind="google_ads_negative_keyword_review",
                title_label="Wykluczenie słowa do sprawdzenia",
                subtitle_label="ocena intencji zapytania bez zapisu zmian",
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=_apply_state_label(item.get("apply_allowed")),
                system_readiness_label=_system_readiness_label(
                    item.get("api_mutation_ready")
                ),
            )
        )
    return cards


def _ads_custom_segment_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    preview_items = [
        item
        for item in payload.get("payload_preview", [])
        if isinstance(item, dict)
    ]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        targeting_preview = next(
            (
                target
                for target in item.get("targeting_preview", [])
                if isinstance(target, dict)
            ),
            {},
        )
        safety_review = item.get("safety_review")
        safety_review = safety_review if isinstance(safety_review, dict) else {}
        source_terms = _string_list(item.get("source_terms"))
        rows = [
            _preview_row(
                "Nazwa",
                str(item.get("custom_segment_name") or "segment do sprawdzenia"),
            ),
            _preview_row(
                "Typ odbiorców",
                str(item.get("member_type_label") or "typ odbiorców do sprawdzenia"),
            ),
            _preview_row(
                "Hasła źródłowe",
                ", ".join(source_terms[:4]) if source_terms else "brak haseł",
            ),
            _preview_row(
                "Kampania do sprawdzenia",
                str(targeting_preview.get("campaign_name") or "kampania do sprawdzenia"),
            ),
            _preview_row(
                "Bezpieczeństwo",
                str(safety_review.get("status_label") or "wymaga sprawdzenia"),
            ),
        ]
        missing_requirement_labels = _string_list(
            safety_review.get("missing_requirement_labels")
        )
        if missing_requirement_labels:
            rows.append(_preview_row("Braki", ", ".join(missing_requirement_labels[:4])))
        requirement_labels = _string_list(item.get("required_validation_labels"))
        if requirement_labels:
            rows.append(_preview_row("Warunki sprawdzenia", ", ".join(requirement_labels[:4])))
        blocked_claim_labels = _string_list(item.get("blocked_claim_labels"))
        if blocked_claim_labels:
            rows.append(
                _preview_row(
                    "Czego nie wolno twierdzić",
                    ", ".join(blocked_claim_labels[:4]),
                )
            )
        cards.append(
            ActionPreviewCardViewModel(
                id=f"ads_custom_segment_preview_{index}",
                kind="google_ads_custom_segment_review",
                title_label="Segment odbiorców do sprawdzenia",
                subtitle_label="ocena segmentu bez zapisu zmian",
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=_apply_state_label(item.get("apply_allowed")),
                system_readiness_label=_system_readiness_label(
                    item.get("api_mutation_ready")
                ),
            )
        )
    return cards


def _demand_gen_readiness_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    preview_items = [
        item
        for item in payload.get("payload_preview", [])
        if isinstance(item, dict)
    ]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        channel_counts = item.get("campaign_channel_counts")
        channel_counts = channel_counts if isinstance(channel_counts, dict) else {}
        channel_summary = ", ".join(
            f"{demand_gen_channel_label(str(channel))}: {value}"
            for channel, value in sorted(channel_counts.items())
        )
        rows = [
            _preview_row(
                "Kampanie ocenione",
                str(item.get("campaign_rows_evaluated") or 0),
            ),
            _preview_row("Kanały kampanii", channel_summary or "brak kanałów"),
            _preview_row(
                "Kampanie Demand Gen",
                str(item.get("demand_gen_campaign_row_count") or 0),
            ),
            _preview_row(
                "Grupy reklam Demand Gen",
                str(item.get("demand_gen_ad_group_ad_row_count") or 0),
            ),
            _preview_row(
                "Kreacje i zasoby",
                str(item.get("demand_gen_creative_asset_row_count") or 0),
            ),
            _preview_row(
                "Wiersze jakości stron wejścia",
                str(item.get("demand_gen_landing_quality_row_count") or 0),
            ),
        ]
        missing_read_contract_labels = _string_list(item.get("missing_read_contract_labels"))
        if missing_read_contract_labels:
            rows.append(_preview_row("Braki", ", ".join(missing_read_contract_labels[:4])))
        requirement_labels = _string_list(item.get("required_validation_labels"))
        if requirement_labels:
            rows.append(_preview_row("Warunki sprawdzenia", ", ".join(requirement_labels[:4])))
        blocked_claim_labels = _string_list(item.get("blocked_claim_labels"))
        if blocked_claim_labels:
            rows.append(
                _preview_row(
                    "Czego nie wolno twierdzić",
                    ", ".join(blocked_claim_labels[:4]),
                )
            )
        cards.append(
            ActionPreviewCardViewModel(
                id=f"demand_gen_readiness_preview_{index}",
                kind="google_ads_demand_gen_readiness_review",
                title_label="Gotowość Demand Gen do sprawdzenia",
                subtitle_label="ocena gotowości bez zapisu zmian",
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=_apply_state_label(item.get("apply_allowed")),
                system_readiness_label=_system_readiness_label(
                    item.get("api_mutation_ready")
                ),
            )
        )
    return cards


def _merchant_preview_cards(payload: dict[str, Any]) -> list[ActionPreviewCardViewModel]:
    preview_items = [
        item
        for item in payload.get("payload_preview", [])
        if isinstance(item, dict)
        and item.get("preview_contract") == MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT
    ]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(_prioritized_merchant_preview_items(preview_items)[:4]):
        sample_titles = _string_list(item.get("sample_titles"))
        rows = [
            _preview_row("Problem", str(item.get("issue_type_label") or "problem do sprawdzenia")),
            _preview_row(
                "Atrybut",
                str(item.get("affected_attribute_label") or "atrybut do sprawdzenia"),
            ),
            _preview_row(
                "Zgłoszenia",
                _merchant_issue_count_label(item.get("metric_snapshot")),
            ),
            _preview_row(
                "Próbki produktów",
                _merchant_sample_summary(item),
            ),
        ]
        if sample_titles:
            rows.append(_preview_row("Tytuły próbek", ", ".join(sample_titles[:2])))
        cards.append(
            ActionPreviewCardViewModel(
                id=str(item.get("id") or f"merchant_preview_{index}"),
                kind="merchant_feed_issue_review",
                title_label="Problem feedu do sprawdzenia",
                subtitle_label=(
                    f"{item.get('issue_type_label') or 'problem'} / "
                    f"{item.get('affected_attribute_label') or 'atrybut'}"
                ),
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=_apply_state_label(item.get("apply_allowed")),
                system_readiness_label=_system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def _prioritized_merchant_preview_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            0 if _string_list(item.get("sample_titles")) or _string_list(item.get("sample_product_ids")) else 1,
            str(item.get("id") or ""),
        ),
    )


def _preview_row(label: str, value: str) -> ActionPreviewRowViewModel:
    return ActionPreviewRowViewModel(label=label, value=value)


def _merchant_issue_count_label(value: Any) -> str:
    if isinstance(value, dict):
        issue_count = value.get("issue_product_count")
        if isinstance(issue_count, int | float):
            count = int(issue_count)
            if count == 1:
                return "1 zgłoszenie problemu"
            if 2 <= count <= 4:
                return f"{count} zgłoszenia problemu"
            return f"{count} zgłoszeń problemu"
    return "brak liczby zgłoszeń"


def _micros_money_label(value: Any, currency_code: str = "PLN") -> str:
    if not isinstance(value, int | float):
        return "brak"
    return f"{value / 1_000_000:.2f} {currency_code}"


def _merchant_sample_summary(item: dict[str, Any]) -> str:
    titles = _string_list(item.get("sample_titles"))
    product_ids = _string_list(item.get("sample_product_ids"))
    if titles:
        count = len(titles)
        if count == 1:
            return "1 próbka z nazwą produktu"
        if 2 <= count <= 4:
            return f"{count} próbki z nazwami produktów"
        return f"{count} próbek z nazwami produktów"
    if product_ids:
        count = len(product_ids)
        if count == 1:
            return "1 próbka produktu bez nazwy"
        if 2 <= count <= 4:
            return f"{count} próbki produktów bez nazw"
        return f"{count} próbek produktów bez nazw"
    reason = item.get("sample_unavailable_reason_label") or item.get("sample_unavailable_reason")
    if isinstance(reason, str) and reason:
        return reason
    return "brak próbek produktów"


def _apply_state_label(value: Any) -> str:
    return "zapis zmian dopuszczony" if value is True else "zapis zmian zablokowany"


def _system_readiness_label(value: Any) -> str:
    return "system gotowy do zapisu" if value is True else "system zablokowany przed zapisem"


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _review_gate_with_operator_labels(gate: ActionReviewGate) -> ActionReviewGate:
    return gate.model_copy(
        update={
            "status_label": _action_review_gate_status_label(gate.status),
            "last_review_outcome_label": _review_outcome_label(gate.last_review_outcome)
            if gate.last_review_outcome
            else None,
            "last_impact_check_status_label": _action_result_status_label(
                gate.last_impact_check_status
            )
            if gate.last_impact_check_status
            else None,
            "last_mutation_audit_status_label": _action_mutation_audit_status_label(
                gate.last_mutation_audit_status
            )
            if gate.last_mutation_audit_status
            else None,
        }
    )


def _audit_event_with_operator_label(event: AuditEvent) -> AuditEvent:
    return event.model_copy(
        update={
            "event_type_label": event.event_type_label
            or _action_audit_event_label(event.event_type),
            "summary": _action_audit_summary_for_operator(event),
            "details": _audit_details_for_operator(event.details),
        }
    )


def _audit_details_for_operator(details: dict[str, Any]) -> dict[str, Any]:
    operator_details = dict(details)
    checked_items = _string_list(operator_details.get("checked_items"))
    if checked_items:
        operator_details["checked_items"] = [
            _review_summary_item(item) for item in checked_items
        ]
    blockers = _string_list(operator_details.get("blockers"))
    if blockers:
        operator_details["blockers"] = [_review_blocker_label(item) for item in blockers]
    return operator_details


def _is_obsolete_content_review_event(event: AuditEvent) -> bool:
    details = event.details
    obsolete_review_key = "_".join(("target", "site", "mapping", "review"))
    return event.event_type == "human_review_approved_for_prepare" and isinstance(
        details.get(obsolete_review_key), dict
    )


def _action_review_gate(
    action: ActionObject,
    mutation_audits: list[ActionMutationAuditRecord] | None = None,
) -> ActionReviewGate:
    status: Literal[
        "pending_validation",
        "validated_prepare_only",
        "ready_to_apply",
        "blocked_apply",
    ]
    required_checks = _action_required_checks(action.payload)
    operator_checklist = _action_operator_checklist(action.payload)
    apply_allowed = _action_payload_apply_allowed(action.payload)
    last_review = _latest_human_review_event(action.audit_events)
    last_confirmation = _latest_action_confirmation_event(action.audit_events)
    last_impact_check = _latest_action_impact_check_event(action.audit_events)
    last_mutation_audit = _latest_mutation_audit(mutation_audits or [])
    apply_blockers = _action_apply_blockers(
        action=action,
        required_checks=required_checks,
        apply_allowed=apply_allowed,
        confirmation_satisfied=last_confirmation is not None,
        impact_sanity_satisfied=_impact_status_from_event(last_impact_check) == "checked",
    )
    contract_apply_allowed = (
        apply_allowed and action.mode == ActionMode.apply and not apply_blockers
    )
    if action.validation_status == "invalid":
        status = "blocked_apply"
        summary = "Akcja ma błędne sprawdzenie; zapis zmian pozostaje zablokowany."
    elif (
        action.mode == ActionMode.apply
        and action.validation_status == "valid"
        and apply_allowed
        and apply_blockers
    ):
        status = "blocked_apply"
        summary = (
            "Akcja ma przygotowany zakres zapisu zmian, ale blokery bezpieczeństwa nadal "
            "zatrzymują zapis."
        )
    elif action.mode == ActionMode.apply and action.validation_status == "valid" and apply_allowed:
        status = "ready_to_apply"
        summary = "Akcja jest sprawdzona w WILQ i wymaga jawnego potwierdzenia zapisu zmian."
    elif action.validation_status == "valid":
        status = "validated_prepare_only"
        summary = (
            "Akcja jest sprawdzona w WILQ do przygotowania; zapis zmian nadal "
            "wymaga osobnego kontraktu."
        )
    else:
        status = "pending_validation"
        summary = (
            "Wymaga sprawdzenia w WILQ; zapis zmian pozostaje zablokowany osobnymi "
            "warunkami."
        )
    return ActionReviewGate(
        status=status,
        summary=summary,
        required_checks=required_checks,
        required_check_labels=_action_gate_labels(required_checks),
        operator_checklist=operator_checklist,
        operator_checklist_labels=_action_gate_labels(operator_checklist),
        apply_blockers=apply_blockers,
        apply_blocker_labels=_action_gate_labels(apply_blockers),
        confirmation_required=_action_confirmation_required(required_checks, action.mode),
        apply_allowed=contract_apply_allowed,
        last_review_outcome=_review_outcome_from_event(last_review),
        last_reviewed_by=last_review.actor if last_review is not None else None,
        last_reviewed_at=last_review.created_at if last_review is not None else None,
        last_review_summary=last_review.summary if last_review is not None else None,
        last_confirmation_by=last_confirmation.actor if last_confirmation is not None else None,
        last_confirmation_at=last_confirmation.created_at
        if last_confirmation is not None
        else None,
        last_confirmation_summary=last_confirmation.summary
        if last_confirmation is not None
        else None,
        last_impact_check_status=_impact_status_from_event(last_impact_check),
        last_impact_checked_by=last_impact_check.actor
        if last_impact_check is not None
        else None,
        last_impact_checked_at=last_impact_check.created_at
        if last_impact_check is not None
        else None,
        last_impact_check_summary=last_impact_check.summary
        if last_impact_check is not None
        else None,
        last_mutation_audit_id=last_mutation_audit.id
        if last_mutation_audit is not None
        else None,
        last_mutation_audit_status=last_mutation_audit.status
        if last_mutation_audit is not None
        else None,
        last_mutation_audit_actor=last_mutation_audit.actor
        if last_mutation_audit is not None
        else None,
        last_mutation_audit_at=last_mutation_audit.created_at
        if last_mutation_audit is not None
        else None,
        last_mutation_audit_summary=last_mutation_audit.summary
        if last_mutation_audit is not None
        else None,
        last_mutation_attempted=last_mutation_audit.mutation_attempted
        if last_mutation_audit is not None
        else None,
        last_mutation_adapter=last_mutation_audit.mutation_adapter
        if last_mutation_audit is not None
        else None,
        last_mutation_audit_event_id=last_mutation_audit.audit_event_id
        if last_mutation_audit is not None
        else None,
        last_mutation_blockers=last_mutation_audit.blockers
        if last_mutation_audit is not None
        else [],
        last_mutation_blocker_labels=_action_gate_labels(last_mutation_audit.blockers)
        if last_mutation_audit is not None
        else [],
    )


def _persisted_audit_events_by_action_id(action_ids: set[str]) -> dict[str, list[AuditEvent]]:
    if not action_ids:
        return {}
    events_by_action_id: dict[str, list[AuditEvent]] = {action_id: [] for action_id in action_ids}
    for event in local_state_store().list_audit_events():
        if event.action_id not in action_ids:
            continue
        action_events = events_by_action_id.setdefault(event.action_id, [])
        if len(action_events) < 10:
            action_events.append(event)
    return events_by_action_id


def _persisted_audit_events_for_action(action_id: str) -> list[AuditEvent]:
    return local_state_store().list_audit_events(action_id=action_id)[:10]


def _persisted_mutation_audits_by_action_id(
    action_ids: set[str],
) -> dict[str, list[ActionMutationAuditRecord]]:
    if not action_ids:
        return {}
    audits_by_action_id: dict[str, list[ActionMutationAuditRecord]] = {
        action_id: [] for action_id in action_ids
    }
    for audit in local_state_store().list_action_mutation_audits():
        if audit.action_id not in action_ids:
            continue
        action_audits = audits_by_action_id.setdefault(audit.action_id, [])
        if len(action_audits) < 10:
            action_audits.append(audit)
    return audits_by_action_id


def _persisted_mutation_audits_for_action(
    action_id: str,
) -> list[ActionMutationAuditRecord]:
    return local_state_store().list_action_mutation_audits(action_id=action_id)[:10]


def _action_review_summary(request: ActionReviewRequest) -> str:
    parts = [
        f"Wynik przeglądu: {_review_outcome_label(request.outcome)}.",
        f"Notatka: {request.notes}",
    ]
    if request.checked_items:
        parts.append(
            "Sprawdzone: "
            f"{', '.join(_review_summary_item(item) for item in request.checked_items[:8])}."
        )
    if request.blockers:
        parts.append(
            f"Blokady: {', '.join(_review_blocker_label(item) for item in request.blockers[:8])}."
        )
    parts.append("Ten krok nie zapisuje zmian w zewnętrznych systemach.")
    return " ".join(parts)


def _review_summary_item(item: str) -> str:
    if item.startswith("candidate:"):
        return "wybrano pozycję do sprawdzenia"
    if item.startswith("source_type:"):
        return f"źródło: {_review_source_type_label(item.removeprefix('source_type:'))}"
    if item.startswith("mode:"):
        return f"tryb: {content_contract_label(item.removeprefix('mode:'))}"
    if item.startswith("url_review_outcome:"):
        return (
            "URL finalny: "
            f"{content_contract_label(item.removeprefix('url_review_outcome:'))}"
        )
    if item.startswith("reviewed_url:"):
        return "sprawdzony URL zapisany w szczegółach audytu"
    if item.startswith("review_notes:"):
        return "notatka URL zapisana w szczegółach audytu"
    if item.startswith("draft_readiness_notes:"):
        return "notatka gotowości szkicu zapisana w szczegółach audytu"
    if ":" in item:
        key, value = item.split(":", 1)
        label = content_contract_label(key)
        value_label = content_contract_label(_canonical_contract_key(value))
        return f"{label}: {value_label}"
    return item


def _review_blocker_label(item: str) -> str:
    if item.startswith("blocked_claim:"):
        claim = _canonical_contract_key(item.removeprefix("blocked_claim:"))
        claim_label = content_contract_label(claim)
        return f"nie wolno twierdzić: {claim_label}"
    return _action_gate_label(_canonical_contract_key(item)) or content_contract_label(
        _canonical_contract_key(item)
    )


def _review_source_type_label(value: str) -> str:
    labels = {
        "gsc_query_page": "GSC i publiczny URL",
        "ahrefs_content_gap": "Ahrefs jako sygnał do sprawdzenia",
        "wordpress_inventory": "spis treści WordPress",
    }
    return labels.get(value, content_contract_label(value))


def _canonical_contract_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _action_review_details(request: ActionReviewRequest) -> dict[str, Any]:
    details: dict[str, Any] = {
        "review_outcome": request.outcome,
        "reviewed_by": request.reviewed_by,
        "checked_items": request.checked_items,
        "blockers": request.blockers,
    }
    url_review = _content_url_review_details_from_checked_items(request.checked_items)
    if url_review:
        details["content_url_review"] = url_review
    draft_readiness_review = _draft_readiness_review_details_from_checked_items(
        request.checked_items
    )
    if draft_readiness_review:
        details["content_draft_readiness_review"] = draft_readiness_review
    return details


def _content_url_review_details_from_checked_items(
    checked_items: list[str],
) -> dict[str, str]:
    tokens: dict[str, str] = {}
    allowed_keys = {
        "candidate",
        "url_review_outcome",
        "reviewed_url",
        "review_notes",
    }
    for item in checked_items:
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in allowed_keys and value:
            tokens[key] = value
    return tokens


def _draft_readiness_review_details_from_checked_items(
    checked_items: list[str],
) -> dict[str, str]:
    tokens: dict[str, str] = {}
    allowed_keys = {
        "candidate",
        "draft_readiness_outcome",
        "canonical_review_outcome",
        "duplicate_review_outcome",
        "legal_factual_review_outcome",
        "human_review_outcome",
        "draft_readiness_notes",
    }
    for item in checked_items:
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in allowed_keys and value:
            tokens[key] = value
    return tokens


def _review_outcome_label(outcome: str) -> str:
    labels = {
        "approved_for_prepare": "zatwierdzone do dalszego przygotowania",
        "needs_changes": "wymaga poprawek",
        "rejected": "odrzucone",
        "deferred": "odłożone",
    }
    return labels.get(outcome, outcome)


def _latest_human_review_event(events: list[AuditEvent]) -> AuditEvent | None:
    for event in sorted(events, key=lambda item: item.created_at, reverse=True):
        if event.event_type.startswith("human_review_"):
            return event
    return None


def _review_outcome_from_event(event: AuditEvent | None) -> ActionReviewOutcome | None:
    if event is None:
        return None
    outcome = event.event_type.removeprefix("human_review_")
    if outcome in {"approved_for_prepare", "needs_changes", "rejected", "deferred"}:
        return cast(ActionReviewOutcome, outcome)
    return None


def _action_preview_blockers(
    action: ActionObject,
    preview_items: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if not preview_items:
        blockers.append("payload_preview_missing")
    if action.payload.get("destructive") is True:
        blockers.append("destructive_actions_blocked")
    blockers.extend(action.review_gate.apply_blockers)
    return _unique(blockers)


def _action_confirmation_blockers(
    action: ActionObject,
    request: ActionConfirmRequest,
    latest_preview: AuditEvent | None,
) -> list[str]:
    if action.payload.get("action_type") == "confirm_ads_target_guardrails":
        return _ads_target_confirmation_blockers(request)

    blockers: list[str] = []
    if not request.preview_acknowledged:
        blockers.append("preview_acknowledgement_required")
    if latest_preview is None:
        blockers.append("dry_run_preview_required")
    if action.payload.get("destructive") is True:
        blockers.append("destructive_actions_blocked")
    return _unique(blockers)


def _action_confirmation_event_type(action: ActionObject, confirmed: bool) -> str:
    if action.payload.get("action_type") == "confirm_ads_target_guardrails":
        return (
            "ads_target_guardrail_confirmed"
            if confirmed
            else "ads_target_guardrail_confirmation_blocked"
        )
    return "action_apply_confirmed" if confirmed else "action_confirmation_blocked"


def _action_confirmation_summary(
    action: ActionObject,
    request: ActionConfirmRequest,
    blockers: list[str],
    latest_preview: AuditEvent | None,
) -> str:
    if action.payload.get("action_type") == "confirm_ads_target_guardrails":
        return _ads_target_confirmation_summary(request, blockers)

    if blockers:
        return (
            "Potwierdzenie zapisu zmian zablokowane: "
            f"{', '.join(blockers)}. "
            f"Notatka: {request.notes}. "
            "Ten krok nie zapisuje zmian w zewnętrznych systemach."
        )
    preview_ref = latest_preview.id if latest_preview is not None else "missing"
    return (
        f"Potwierdzenie podglądu zapisane. Audyt podglądu: {preview_ref}. "
        f"Notatka: {request.notes}. "
        "Ten krok nie zapisuje zmian w zewnętrznych systemach."
    )


def _ads_target_confirmation_blockers(request: ActionConfirmRequest) -> list[str]:
    blockers: list[str] = []
    target_count = int(request.target_roas is not None) + int(
        request.target_cpa_micros is not None
    )
    if target_count == 0:
        blockers.append("target_roas_or_cpa_required")
    if target_count > 1:
        blockers.append("exactly_one_target_guardrail_allowed")
    return blockers


def _ads_target_confirmation_summary(
    request: ActionConfirmRequest,
    blockers: list[str],
) -> str:
    if blockers:
        return (
            "Potwierdzenie celu Ads zablokowane: "
            f"{', '.join(blockers)}. "
            f"Notatka: {request.notes}. "
            "Ten krok nie zapisuje zmian w Google Ads."
        )
    if request.target_roas is not None:
        target_summary = f"target_roas={request.target_roas}"
    else:
        target_summary = f"target_cpa_micros={request.target_cpa_micros}"
    return (
        f"Potwierdzono roboczą zasadę bezpieczeństwa celu Ads: {target_summary}. "
        f"Notatka: {request.notes}. "
        "Ten zapis odblokowuje tylko kontekst przeglądu celu; nie zapisuje zmian, "
        "nie potwierdza rentowności i nie skaluje budżetu."
    )


def _action_impact_check_blockers(
    action: ActionObject,
    latest_confirmation: AuditEvent | None,
) -> list[str]:
    blockers: list[str] = []
    if latest_confirmation is None:
        blockers.append("action_confirmation_required")
    if not action.metrics:
        blockers.append("metric_facts_required")
    if not action.evidence_ids:
        blockers.append("evidence_ids_required")
    if action.payload.get("destructive") is True:
        blockers.append("destructive_actions_blocked")
    return _unique(blockers)


def _action_impact_check_summary(
    *,
    request: ActionImpactCheckRequest,
    status: Literal["checked", "blocked"],
    metric_fact_count: int,
    source_connectors: list[str],
    blockers: list[str],
) -> str:
    parts = [
        f"Sprawdzenie efektu: {_action_result_status_label(status)}.",
        f"Okno przed zmianą: {request.pre_window_days} dni.",
        f"Okno po zmianie: {request.post_window_days} dni.",
        f"Metryki z dowodami: {metric_fact_count}.",
        "Źródła: "
        f"{', '.join(_source_connector_labels(source_connectors)) if source_connectors else 'brak'}.",
    ]
    if blockers:
        parts.append(f"Blokady: {', '.join(blockers)}.")
    parts.append(f"Notatka: {request.notes}.")
    parts.append("Ten krok nie zapisuje zmian w zewnętrznych systemach.")
    return " ".join(parts)


def _preview_contract(payload: dict[str, Any], preview_items: list[dict[str, Any]]) -> str | None:
    if isinstance(payload.get("preview_contract"), str):
        return str(payload["preview_contract"])
    for item in preview_items:
        contract = item.get("preview_contract")
        if isinstance(contract, str):
            return contract
    return None


def _action_required_checks(payload: dict[str, Any]) -> list[str]:
    checks = _string_list(payload.get("required_validation"))
    if checks:
        return checks
    preview_checks: list[str] = []
    for preview in _payload_preview_items(payload):
        preview_checks.extend(_string_list(preview.get("required_validation")))
    if preview_checks:
        return _unique(preview_checks)
    for key in ("review_steps", "queue_steps", "draft_constraints"):
        values = _string_list(payload.get(key))
        if values:
            return values
    return ["validate_action_object", "human_review_before_apply"]


def _action_operator_checklist(payload: dict[str, Any]) -> list[str]:
    checklist = _string_list(payload.get("operator_review_gates"))
    if checklist:
        return checklist
    for key in ("review_steps", "queue_steps"):
        values = _string_list(payload.get(key))
        if values:
            return values
    return _action_required_checks(payload)


def _action_apply_blockers(
    *,
    action: ActionObject,
    required_checks: list[str],
    apply_allowed: bool,
    confirmation_satisfied: bool,
    impact_sanity_satisfied: bool,
) -> list[str]:
    blockers: list[str] = []
    if action.mode != ActionMode.apply:
        blockers.append("action_mode_prepare_only")
    if action.validation_status != "valid":
        blockers.append("action_validation_required")
    if not apply_allowed:
        blockers.append("payload_apply_allowed_false")
    if action.payload.get("destructive") is True:
        blockers.append("destructive_actions_blocked")
    if _requires_human_confirmation(required_checks) and not confirmation_satisfied:
        blockers.append("human_confirm_before_apply")
    if not impact_sanity_satisfied:
        blockers.append("impact_sanity_check_required")
    if action.mode == ActionMode.apply and _supported_mutation_adapter(action) is None:
        blockers.append("vendor_mutation_adapter_required")
    blocked_claims = _string_list(action.payload.get("blocked_claims"))
    blockers.extend(f"blocked_claim:{claim}" for claim in blocked_claims[:8])
    return _unique(blockers)


def _action_gate_labels(values: Iterable[str]) -> list[str]:
    labels: list[str] = []
    for value in values:
        label = _action_gate_label(value)
        if label and label not in labels:
            labels.append(label)
    return labels


def _action_mode_label(value: ActionMode | str) -> str:
    labels = {
        "suggest": "propozycja",
        "prepare": "przygotowanie",
        "apply": "zapis zmian",
    }
    return labels.get(str(value), "tryb akcji")


def _action_risk_label(value: ActionRisk | str) -> str:
    labels = {
        "low": "niskie ryzyko",
        "medium": "średnie ryzyko",
        "high": "wysokie ryzyko",
        "critical": "krytyczne ryzyko",
    }
    return labels.get(str(value), "ryzyko do sprawdzenia")


def _action_status_label(value: ActionStatus | str) -> str:
    labels = {
        "new": "nowa",
        "ready": "gotowa do sprawdzenia",
        "needs_validation": "wymaga sprawdzenia w WILQ",
        "validation_failed": "sprawdzenie wykazało problem",
        "ready_to_apply": "gotowa do potwierdzenia zapisu",
        "applying": "zapis zmian w toku",
        "applied": "zmiany zapisane",
        "failed": "błąd zapisu",
        "dismissed": "odrzucona",
        "blocked": "zablokowana",
    }
    return labels.get(str(value), "status akcji do sprawdzenia")


def _action_evidence_summary_label(evidence_ids: list[str]) -> str:
    count = len(evidence_ids)
    if count == 0:
        return "brak dowodów źródłowych"
    if count == 1:
        return "1 dowód źródłowy"
    if 2 <= count <= 4:
        return f"{count} dowody źródłowe"
    return f"{count} dowodów źródłowych"


def _action_validation_status_label(value: str) -> str:
    labels = {
        "not_validated": "nie sprawdzono w WILQ",
        "valid": "sprawdzone w WILQ",
        "invalid": "wymaga poprawek",
    }
    return labels.get(value, "status sprawdzenia")


def _action_review_gate_status_label(value: str) -> str:
    labels = {
        "pending_validation": "czeka na sprawdzenie",
        "validated_prepare_only": "sprawdzone w WILQ",
        "ready_to_apply": "gotowe do potwierdzenia",
        "blocked_apply": "zapis zmian zablokowany",
    }
    return labels.get(value, "status warunków")


def _action_mutation_audit_status_label(value: str | None) -> str:
    labels = {
        "blocked": "zablokowany",
        "applied": "zapisany",
        "failed": "błąd",
    }
    return labels.get(value or "", "brak")


def _action_result_status_label(value: str | None) -> str:
    labels = {
        "preview_ready": "podgląd gotowy",
        "generated": "wygenerowany",
        "confirmed": "potwierdzony",
        "recorded": "zapisane",
        "completed": "zapisane",
        "checked": "sprawdzone",
        "valid": "poprawna",
        "invalid": "wymaga poprawek",
        "applied": "zapisane",
        "blocked": "zablokowany",
        "failed": "błąd",
    }
    return labels.get(value or "", "zapisane")


def _source_connector_label(connector_id: str) -> str:
    connector = get_connector_status(connector_id)
    return connector.label if connector is not None and connector.label else "źródło danych"


def _source_connector_labels(connector_ids: Iterable[str]) -> list[str]:
    labels: list[str] = []
    for connector_id in connector_ids:
        label = _source_connector_label(connector_id)
        if label not in labels:
            labels.append(label)
    return labels


def _action_preview_summary(
    *,
    status: Literal["preview_ready", "blocked"],
    included_items: int,
    preview_items: int,
) -> str:
    if status == "blocked":
        return (
            f"Podgląd zmian przygotowany, ale zapis zmian pozostaje zablokowany. "
            f"Pokazano {included_items} z {preview_items} pozycji do sprawdzenia. "
            "Nie zapisano zmian w zewnętrznych systemach."
        )
    return (
        f"Podgląd zmian przygotowany. Pokazano {included_items} z {preview_items} "
        "pozycji do sprawdzenia. Nie zapisano zmian w zewnętrznych systemach."
    )


def _action_audit_summary_for_operator(event: AuditEvent) -> str:
    if event.event_type == "action_preview_generated":
        return _legacy_or_current_preview_summary(event.summary)
    if event.event_type in {"action_apply_confirmed", "action_apply_confirmation_confirmed"}:
        return "Podgląd zmian potwierdzony. Nie zapisano zmian w zewnętrznych systemach."
    if event.event_type in {"action_confirmation_blocked", "action_apply_confirmation_blocked"}:
        return "Potwierdzenie podglądu zablokowane. Nie zapisano zmian w zewnętrznych systemach."
    if event.event_type in {"action_impact_check_completed", "action_impact_check_blocked"}:
        return _legacy_or_current_impact_summary(event.summary)
    if event.event_type == "action_apply_blocked":
        return "Zapis zmian zablokowany przez warunki bezpieczeństwa WILQ."
    if event.event_type == "action_apply_completed":
        return "Zapis zmian wykonany i zapisany w audycie bezpieczeństwa."
    return _operator_audit_summary_text(event.summary)


def _operator_audit_summary_text(summary: str) -> str:
    clean_summary = str(summary or "")
    legacy_ranking_claim = " ".join(("ranking", "guarantee"))
    legacy_blocked_ranking_claim = f"blocked_claim:{legacy_ranking_claim}"
    replacements = {
        "payload_apply_allowed_false": _review_blocker_label("payload_apply_allowed_false"),
        "wordpress_write_not_requested": _review_blocker_label("wordpress_write_not_requested"),
        legacy_blocked_ranking_claim: _review_blocker_label(legacy_blocked_ranking_claim),
        "blocked_claim:gwarancja pozycji": _review_blocker_label(
            "blocked_claim:gwarancja pozycji"
        ),
        legacy_ranking_claim: content_contract_label("ranking_guarantee"),
        "source_type:gsc_query_page": "źródło: GSC i publiczny URL",
        "mode:refresh": f"tryb: {content_contract_label('refresh')}",
    }
    for raw, label in replacements.items():
        clean_summary = clean_summary.replace(raw, label)
    if "candidate:" in clean_summary:
        clean_summary = _replace_candidate_fragment(clean_summary)
    return clean_summary


def _replace_candidate_fragment(summary: str) -> str:
    parts = summary.split("candidate:")
    clean = parts[0]
    for part in parts[1:]:
        suffix = part
        for delimiter in (",", "."):
            if delimiter in suffix:
                suffix = suffix.split(delimiter, 1)[1]
                clean += f"wybrano pozycję do sprawdzenia{delimiter}{suffix}"
                break
        else:
            clean += "wybrano pozycję do sprawdzenia"
    return clean


def _legacy_or_current_preview_summary(summary: str) -> str:
    item_summary = ""
    if "pozycje=" in summary:
        item_fragment = summary.split("pozycje=", 1)[1].split(",", 1)[0].split(".", 1)[0]
        if item_fragment:
            item_summary = f" Pokazano {item_fragment} pozycji do sprawdzenia."
    if "blocked" in summary or "zablokowany" in summary:
        return (
            "Podgląd zmian przygotowany, ale zapis zmian pozostaje zablokowany."
            f"{item_summary} Nie zapisano zmian w zewnętrznych systemach."
        )
    return (
        "Podgląd zmian przygotowany."
        f"{item_summary} Nie zapisano zmian w zewnętrznych systemach."
    )


def _legacy_or_current_impact_summary(summary: str) -> str:
    if "status=blocked" in summary or "zablok" in summary:
        prefix = "Sprawdzenie efektu zablokowane."
    else:
        prefix = "Sprawdzenie efektu zapisane."
    window_parts = [
        part.strip()
        for part in summary.split(".")
        if part.strip().startswith(("Okno przed zmianą", "Okno po zmianie", "Metryki z dowodami"))
    ]
    clean_parts = [prefix, *[f"{part}." for part in window_parts]]
    if "Ten krok nie zapisuje zmian" not in " ".join(clean_parts):
        clean_parts.append("Ten krok nie zapisuje zmian w zewnętrznych systemach.")
    return " ".join(clean_parts)


def _action_audit_event_label(event_type: str) -> str:
    labels = {
        "action_preview_generated": "Podgląd zmian wygenerowany",
        "human_review_approved_for_prepare": "Przegląd operatora zapisany",
        "human_review_needs_changes": "Przegląd wymaga poprawek",
        "human_review_rejected": "Przegląd odrzucony",
        "human_review_deferred": "Przegląd odłożony",
        "action_apply_confirmed": "Podgląd potwierdzony",
        "action_confirmation_blocked": "Potwierdzenie zablokowane",
        "action_apply_confirmation_blocked": "Potwierdzenie zablokowane",
        "action_impact_check_completed": "Sprawdzenie efektu zapisane",
        "action_impact_check_blocked": "Sprawdzenie efektu zablokowane",
        "action_apply_blocked": "Zapis zmian zablokowany",
        "action_apply_completed": "Zapis zmian wykonany",
    }
    return labels.get(event_type, "Zdarzenie audytu")


def _payload_with_operator_labels(payload: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(payload)
    _hydrate_operator_labels_recursive(enriched)
    return enriched


def _hydrate_operator_labels_recursive(value: Any) -> None:
    if isinstance(value, dict):
        _hydrate_operator_label_fields(value)
        for item in value.values():
            _hydrate_operator_labels_recursive(item)
    elif isinstance(value, list):
        for item in value:
            _hydrate_operator_labels_recursive(item)


def _hydrate_operator_label_fields(item: dict[str, Any]) -> None:
    if item.get("status_label") in (None, "") and isinstance(item.get("status"), str):
        item["status_label"] = _operator_state_label(item["status"])
    if item.get("post_status_label") in (None, "") and isinstance(item.get("post_status"), str):
        item["post_status_label"] = _wordpress_post_status_label(item["post_status"])
    label_fields = {
        "required_validation": "required_validation_labels",
        "operator_review_gates": "operator_review_gate_labels",
        "human_review_gates": "human_review_gate_labels",
        "draft_constraints": "draft_constraint_labels",
        "missing_read_contracts": "missing_read_contract_labels",
        "missing_requirements": "missing_requirement_labels",
        "required_google_ads_state": "required_google_ads_state_labels",
        "allowed_uses_after_confirmation": "allowed_uses_after_confirmation_labels",
        "allowed_contracts": "allowed_contract_labels",
        "target_roas_or_cpa": "target_roas_or_cpa_labels",
        "blocked_claims": "blocked_claim_labels",
    }
    for source_key, label_key in label_fields.items():
        existing_labels = _string_list(item.get(label_key))
        if existing_labels:
            continue
        source_values = _string_list(item.get(source_key))
        if source_values:
            item[label_key] = _action_gate_labels(source_values)
    if item.get("recommendation_type_label") in (None, "") and isinstance(
        item.get("recommendation_type"),
        str,
    ):
        item["recommendation_type_label"] = _ads_recommendation_type_label(
            item["recommendation_type"]
        )
    if item.get("match_type_label") in (None, "") and isinstance(
        item.get("match_type"),
        str,
    ):
        item["match_type_label"] = _ads_keyword_match_type_label(item["match_type"])
    if item.get("level_label") in (None, "") and isinstance(item.get("level"), str):
        item["level_label"] = _ads_negative_keyword_level_label(item["level"])


def _operator_state_label(value: str) -> str:
    labels = {
        "blocked": "zablokowane",
        "ready": "gotowe",
        "allowed": "dopuszczone",
        "missing": "brak",
        "pending_validation": "czeka na sprawdzenie",
        "validated_prepare_only": "sprawdzone w WILQ",
        "ready_to_apply": "gotowe do potwierdzenia",
        "blocked_apply": "zapis zmian zablokowany",
    }
    return labels.get(value, "do sprawdzenia")


def _ads_recommendation_type_label(value: str) -> str:
    labels = {
        "CAMPAIGN_BUDGET": "budżet kampanii",
        "KEYWORD": "słowa kluczowe",
        "RESPONSIVE_SEARCH_AD": "elastyczna reklama w wyszukiwarce",
        "TARGET_CPA_OPT_IN": "strategia kosztu pozyskania celu",
        "TARGET_ROAS_OPT_IN": "strategia zwrotu z reklam",
        "MAXIMIZE_CONVERSIONS_OPT_IN": "maksymalizacja konwersji",
        "MAXIMIZE_CONVERSION_VALUE_OPT_IN": "maksymalizacja wartości konwersji",
        "IMPROVE_PERFORMANCE_MAX_AD_STRENGTH": "jakość zasobów Performance Max",
        "DISPLAY_EXPANSION_OPT_IN": "rozszerzenie kampanii na sieć reklamową",
        "DYNAMIC_IMAGE_EXTENSION_OPT_IN": "dynamiczne rozszerzenia graficzne",
        "SEARCH_PARTNERS_OPT_IN": "rozszerzenie kampanii na partnerów wyszukiwania",
        "UNKNOWN": "typ rekomendacji nieznany",
        "UNSPECIFIED": "typ rekomendacji nieokreślony",
    }
    return labels.get(value, value.replace("_", " ").lower())


def _ads_keyword_match_type_label(value: str) -> str:
    labels = {
        "BROAD": "dopasowanie przybliżone",
        "PHRASE": "dopasowanie do wyrażenia",
        "EXACT": "dopasowanie ścisłe",
        "UNKNOWN": "dopasowanie nieznane",
        "UNSPECIFIED": "dopasowanie nieokreślone",
    }
    return labels.get(value, "dopasowanie do sprawdzenia")


def _ads_negative_keyword_level_label(value: str) -> str:
    labels = {
        "ad_group": "grupa reklam",
        "campaign_review_required": "poziom kampanii wymaga sprawdzenia",
    }
    return labels.get(value, "poziom do sprawdzenia")


def _wordpress_post_status_label(value: str) -> str:
    labels = {
        "draft": "szkic",
        "pending": "czeka na sprawdzenie",
        "private": "prywatny",
        "publish": "opublikowany",
    }
    return labels.get(value, "status wpisu do sprawdzenia")


def _action_gate_label(value: str) -> str | None:
    if value.startswith("blocked_claim:"):
        claim_labels = operator_blocked_claims([value.removeprefix("blocked_claim:")])
        claim_label = claim_labels[0] if claim_labels else "ryzykowna obietnica"
        return f"nie wolno twierdzić: {claim_label}"
    labels = {
        "action_mode_prepare_only": "tryb przygotowania bez zapisu zmian",
        "action_validation_required": "wymagane sprawdzenie w WILQ",
        "payload_apply_allowed_false": "podgląd zmian nie pozwala na zapis",
        "destructive_actions_blocked": "destrukcyjne zmiany zablokowane",
        "preview_acknowledgement_required": "wymagane potwierdzenie podglądu zmian",
        "dry_run_preview_required": "wymagany wcześniejszy podgląd zmian",
        "action_confirmation_required": "wymagane potwierdzenie podglądu zmian",
        "metric_facts_required": "wymagane metryki z dowodami",
        "evidence_ids_required": "wymagane dowody źródłowe",
        "impact_sanity_check_required": "wymagane sprawdzenie efektu",
        "vendor_mutation_adapter_required": "brak bezpiecznej ścieżki zapisu w zewnętrznym systemie",
        "validate_action_object": "sprawdzenie akcji",
        "human_review_before_apply": "sprawdzenie przez człowieka przed zapisem",
        "human_confirm_before_apply": "potwierdzenie człowieka przed zapisem",
        "compare_90_day_safety_read": "porównaj z 90-dniową kontrolą bezpieczeństwa",
        "confirm_developer_token_approval": "potwierdź akceptację tokena deweloperskiego",
        "review_campaign_activity": "sprawdź aktywność kampanii",
        "verify_account_currency": "sprawdź walutę konta",
        "budget_pacing": "sprawdź tempo wydawania budżetu",
        "impression_share": "sprawdź udział w wyświetleniach",
        "budget_apply_preview": "sprawdź podgląd zmiany budżetu",
        "campaign_budget_apply_safety": "sprawdź bezpieczeństwo zmiany budżetu",
        "campaign_budget_operation_preview": "sprawdź operację budżetu",
        "budget_delta_limit_30_percent": "sprawdź limit zmiany budżetu do 30%",
        "budget_delta_percent": "sprawdź procent zmiany budżetu",
        "budget_target_or_seasonality": "sprawdź cel budżetu albo sezonowość",
        "human_budget_goal": "potwierdź cel budżetu",
        "content_url_preflight_review": "potwierdzenie publicznego URL-a",
        "final_canonical_review": "kontrola URL-a kanonicznego",
        "canonical_review": "kontrola URL-a kanonicznego",
        "canonical_review_outcome": "wynik kontroli URL-a kanonicznego",
        "duplicate_or_cannibalization_check": "kontrola duplikacji i kanibalizacji",
        "duplicate_review_outcome": "wynik kontroli duplikacji",
        "legal_factual_review": "kontrola prawna i faktograficzna",
        "legal_factual_review_outcome": "wynik kontroli prawnej i faktograficznej",
        "content_draft_readiness_review": "kontrola gotowości szkicu",
        "wordpress_draft_payload_preview": "podgląd wpisu WordPress",
        "human_confirm_before_wordpress_write": "potwierdzenie człowieka przed zapisem WordPress",
        "gsc_query_page_check": "sprawdzenie zapytań i URL-i z GSC",
        "wordpress_inventory_check": "sprawdzenie spisu treści WordPress",
        "review_recommendation_type": "sprawdź typ rekomendacji",
        "review_impact_metrics": "sprawdź metryki wpływu",
        "review_change_history": "sprawdź historię zmian",
        "review_business_goal": "sprawdź cel biznesowy",
        "recommendation_apply_preview": "sprawdź podgląd rekomendacji",
        "recommendations": "sprawdź rekomendacje Google Ads",
        "profit_margin_or_value_model": "sprawdź marżę albo model wartości",
        "google_ads_rmf_compliance_review": "sprawdź zgodność Google Ads",
        "review_issue_type_and_attribute": "sprawdź typ problemu i atrybut feedu",
        "review_reporting_context": "sprawdź kontekst raportowania",
        "group_issue_reasons": "pogrupuj powody problemów",
        "identify_disapproved_products": "ustal produkty i zgłoszenia do sprawdzenia",
        "mutation_audit_required": "wymagany ślad bezpieczeństwa",
        "mutation_audit": "ślad bezpieczeństwa zapisu",
        "negative_keyword_action_validation": "sprawdzenie w WILQ dla wykluczeń",
        "prepare_feed_fix_preview": "przygotuj podgląd zmian feedu",
        "require_human_confirm_before_apply": "człowiek potwierdza przed zapisem",
        "require_human_confirm_before_any_write": "człowiek potwierdza przed każdym zapisem",
        "reject_brand_or_low_intent_terms": "odrzuć brandowe lub niskointencyjne frazy",
        "rerun_google_ads_data_read": "uruchom ponowny odczyt Google Ads",
        "review_ads_campaign_channel_context": "sprawdź kanały kampanii Ads",
        "review_campaign_goal": "sprawdź cel kampanii",
        "review_campaign_name_dimension": "sprawdź nazwę kampanii",
        "review_conversion_quality": "sprawdź jakość konwersji",
        "review_conversion_or_key_event_mapping": "sprawdź powiązanie konwersji lub zdarzenia kluczowego",
        "review_budget_context": "sprawdź kontekst budżetu",
        "review_demand_gen_missing_contracts": "sprawdź braki danych Demand Gen",
        "review_ga4_landing_source_campaign_context": "sprawdź stronę wejścia, źródło i kampanię w GA4",
        "review_human_budget_goal": "sprawdź cel budżetu od człowieka",
        "review_landing_page_dimension": "sprawdź stronę wejścia",
        "review_local_rankings_aggregate": "sprawdź zbiorcze dane lokalnych pozycji",
        "review_ngram_intent": "sprawdź intencję tematu zapytań",
        "review_place_inventory": "sprawdź listę lokalizacji",
        "review_profit_margin_model": "sprawdź model marży",
        "review_reviews_aggregate": "sprawdź zbiorcze dane opinii",
        "review_search_term_context": "sprawdź kontekst wyszukiwanego hasła",
        "review_search_terms_before_budget_decision": "sprawdź wyszukiwane hasła przed decyzją budżetową",
        "review_source_medium_dimension": "sprawdź źródło i medium ruchu",
        "review_source_search_terms": "sprawdź źródłowe wyszukiwane hasła",
        "review_source_terms": "sprawdź źródłowe hasła",
        "review_target_fit": "sprawdź dopasowanie do celu",
        "review_conversion_tracking": "sprawdź pomiar konwersji",
        "review_pmax_asset_feed_context": "sprawdź kontekst zasobów i feedu PMax",
        "check_existing_keywords_and_match_types": "sprawdź istniejące słowa kluczowe i dopasowania",
        "90_day_safety_check": "sprawdź bezpieczeństwo z 90 dni",
        "negative_keyword_change_preview": "sprawdź podgląd wykluczenia słowa",
        "change_history": "sprawdź historię zmian",
        "forecast_or_audience_size": "sprawdź prognozę albo wielkość odbiorców",
        "custom_segment_operation_preview": "sprawdź podgląd segmentu odbiorców",
        "google_ads_mutation_audit": "sprawdzenie zapisu zmian w Google Ads",
        "human_strategy_review": "człowiek sprawdza strategię",
        "human_intent_review": "człowiek sprawdza intencję",
        "human_confirm_before_tracking_change": "człowiek potwierdza przed zmianą pomiaru",
        "keyword_planner_enrichment": "wzbogać dane przez Keyword Planner",
        "ngram_to_negative_keyword_change_preview": "podgląd przejścia z tematu zapytań do wykluczenia",
        "block_local_tasks_without_contract": "blokuj lokalne zadania bez kontraktu",
        "demand_gen_landing_quality_by_campaign": "jakość stron wejścia Demand Gen według kampanii",
        "demand_gen_transition_constraints": "ograniczenia przejścia na Demand Gen",
        "demand_gen_ad_group_ad_rows": "wiersze grup reklam Demand Gen",
        "demand_gen_creative_asset_rows": "wiersze kreacji i zasobów Demand Gen",
        "place_inventory": "lista lokalizacji",
        "local_tasks": "lokalne zadania do wykonania",
        "local_rankings": "lokalne pozycje",
        "reviews": "opinie",
        "gbp_visibility": "widoczność Google Business Profile",
        "competitor_visibility": "widoczność konkurencji",
        "use_only_wilq_evidence": "użyj tylko dowodów z WILQ",
        "write_in_polish": "pisz po polsku",
        "no_performance_claims_without_source_metric": "bez obietnic skuteczności bez metryk źródłowych",
        "no_publishing_without_connector_credentials": "bez publikacji bez danych dostępowych źródła",
        "require_human_review_before_apply": "człowiek sprawdza przed zapisem",
        "confirm_target_roas_or_cpa": "potwierdź docelowy zwrot z reklam albo koszt pozyskania celu",
        "record_human_strategy_review_outcome": "zapisz wynik sprawdzenia strategii przez człowieka",
        "WILQ_ADS_TARGET_ROAS": "docelowy zwrot z reklam",
        "WILQ_ADS_TARGET_CPA_MICROS": "docelowy koszt pozyskania celu",
        "target_metrics_review": "przegląd wskaźników względem celu",
        "campaign_review_context": "kontekst przeglądu kampanii",
        "budget_review_context": "kontekst przeglądu budżetu",
        "recommended_budget_missing": "brak proponowanego budżetu",
        "target_roas_or_cpa": "docelowy zwrot z reklam albo koszt pozyskania celu",
        "developer_token_approved_for_keyword_planner": "token deweloperski zatwierdzony dla Keyword Plannera",
        "keyword_planner_generate_ideas_allowed": "Keyword Planner może generować propozycje",
        "verify_keyword_planner_idea_rows": "sprawdź wiersze Keyword Planner",
    }
    if value in labels:
        return labels[value]
    if " " in value and "_" not in value:
        return value
    return None


def _action_payload_apply_allowed(payload: dict[str, Any]) -> bool:
    if payload.get("apply_allowed") is True:
        return True
    preview_items = _payload_preview_items(payload)
    if not preview_items:
        return False
    return all(item.get("apply_allowed") is True for item in preview_items)


def _action_confirmation_required(required_checks: list[str], mode: ActionMode) -> bool:
    if _requires_human_confirmation(required_checks):
        return True
    return mode in {ActionMode.prepare, ActionMode.apply}


def _requires_human_confirmation(required_checks: list[str]) -> bool:
    return any("human" in check and "confirm" in check for check in required_checks)


def _payload_preview_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    preview = payload.get("payload_preview")
    if isinstance(preview, list):
        return [item for item in preview if isinstance(item, dict)]
    if isinstance(preview, dict):
        return [preview]
    preview_items: list[dict[str, Any]] = []
    for value in payload.values():
        if isinstance(value, list):
            preview_items.extend(
                item
                for item in value
                if isinstance(item, dict) and "apply_allowed" in item
            )
    return preview_items


def _latest_preview_event(events: list[AuditEvent]) -> AuditEvent | None:
    for event in sorted(events, key=lambda item: item.created_at, reverse=True):
        if event.event_type == "action_preview_generated":
            return event
    return None


def _latest_action_confirmation_event(events: list[AuditEvent]) -> AuditEvent | None:
    for event in sorted(events, key=lambda item: item.created_at, reverse=True):
        if event.event_type in {
            "action_apply_confirmed",
            "ads_target_guardrail_confirmed",
        }:
            return event
    return None


def _latest_action_impact_check_event(events: list[AuditEvent]) -> AuditEvent | None:
    for event in sorted(events, key=lambda item: item.created_at, reverse=True):
        if event.event_type in {"action_impact_check_completed", "action_impact_check_blocked"}:
            return event
    return None


def _latest_mutation_audit(
    audits: list[ActionMutationAuditRecord],
) -> ActionMutationAuditRecord | None:
    if not audits:
        return None
    return sorted(audits, key=lambda item: item.created_at, reverse=True)[0]


def _impact_status_from_event(event: AuditEvent | None) -> Literal["checked", "blocked"] | None:
    if event is None:
        return None
    if event.event_type == "action_impact_check_completed":
        return "checked"
    if event.event_type == "action_impact_check_blocked":
        return "blocked"
    return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]
