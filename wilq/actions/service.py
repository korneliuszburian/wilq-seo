from __future__ import annotations

import os
import re
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass
from time import monotonic
from typing import Any, Literal, cast
from urllib.parse import urlparse
from uuid import uuid4

from wilq.actions.content_refresh import (
    content_contract_label,
    content_contract_labels,
    content_payload_with_reviewed_wordpress_draft_previews,
    content_refresh_payload_from_metric_facts,
    content_refresh_queue_action,
    content_url_review_contract,
    post_publication_measurement_plan,
    post_publication_measurement_summary,
)
from wilq.actions.ga4.tracking_quality import (
    ga4_tracking_quality_action,
)
from wilq.actions.google_ads.business_context import (
    ADS_STRATEGY_REVIEW_ACTION_ID,
    ads_business_context_configured,
    ads_business_context_missing_read_contracts,
    ads_strategy_review_payload,
    ads_strategy_review_state,
    business_context_action,
    target_confirmation_action,
)
from wilq.actions.google_ads.campaign_review import (
    campaign_review_action,
    campaign_review_payload_from_metric_facts,
)
from wilq.actions.google_ads.change_history import (
    change_history_impact_action,
    change_history_impact_payload_from_metric_facts,
)
from wilq.actions.google_ads.custom_segments import (
    custom_segment_action,
    custom_segment_payload_from_metric_facts,
)
from wilq.actions.google_ads.demand_gen import (
    DEMAND_GEN_AD_GROUP_AD_ROWS_CONTRACT,
    DEMAND_GEN_AD_READ_ROW_COUNT_FACT,
    DEMAND_GEN_AD_READ_STATUS_FACT,
    DEMAND_GEN_CAMPAIGN_MODE_REVIEW_CONTRACT,
    DEMAND_GEN_CAMPAIGN_ROWS_CONTRACT,
    DEMAND_GEN_CREATIVE_ASSET_ROW_COUNT_FACT,
    DEMAND_GEN_CREATIVE_ASSET_ROWS_CONTRACT,
    DEMAND_GEN_CREATIVE_ASSET_STATUS_FACT,
    DEMAND_GEN_LANDING_QUALITY_CONTRACT,
    DEMAND_GEN_READINESS_AVAILABLE_CONTRACT,
    demand_gen_ad_group_ad_rows_from_facts,
    demand_gen_campaign_mode_review_rows_from_campaigns,
    demand_gen_channel_label,
    demand_gen_contract_has_ready_fact,
    demand_gen_creative_asset_rows_from_facts,
    demand_gen_landing_quality_rows_from_facts,
    demand_gen_readiness_action,
    demand_gen_readiness_review_payload,
)
from wilq.actions.google_ads.keyword_planner import (
    KEYWORD_PLANNER_ACCESS_ACTION_TYPE,
    keyword_planner_access_action,
)
from wilq.actions.google_ads.negative_keywords import (
    negative_keyword_action,
    negative_keyword_payload_from_metric_facts,
)
from wilq.actions.google_ads.recommendations import (
    RECOMMENDATION_REVIEW_ACTION_ID,
    recommendation_review_action,
    recommendation_review_payload_from_metric_facts,
)
from wilq.actions.google_ads.search_term_ngrams import (
    SEARCH_TERM_NGRAM_PREVIEW_CONTRACT,
    search_term_ngram_action,
    search_term_ngram_payload_from_metric_facts,
)
from wilq.actions.localo.visibility import (
    localo_visibility_review_action,
    localo_visibility_review_payload_from_metric_facts,
)
from wilq.actions.merchant import merchant_feed_issue_action
from wilq.actions.payloads import (
    SERVICE_PROFILE_KNOWLEDGE_PROMOTION_ACTION_TYPE,
    SERVICE_PROFILE_PRIVATE_PROPOSAL_PROMOTION_ACTION_TYPE,
    validate_action_payload,
)
from wilq.actions.wordpress_draft import existing_draft_update_action
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
from wilq.connectors.wordpress.client import create_wordpress_draft_post
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.handoff.wordpress import ContentWordPressDraftHandoff
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftWriteAuthorization,
    execute_content_wordpress_draft_handoff,
)
from wilq.content.knowledge.service_profile import content_service_profile_response
from wilq.content.workflow.api import (
    build_content_wordpress_draft_activation_packet_response,
    build_content_wordpress_draft_write_readiness_response,
    build_content_work_item_diagnostics_snapshot_response,
    build_content_work_item_diagnostics_snapshot_response_for_work_item,
)
from wilq.content.workflow.contracts import (
    ContentWordPressDraftActivationPacketResponse,
    ContentWordPressDraftWriteReadinessResponse,
)
from wilq.content.workflow.store import content_workflow_store
from wilq.credentials.runtime import variable_value
from wilq.evidence.registry import SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID, connector_evidence_id
from wilq.operator_labels import (
    blocker_count_label,
    evidence_count_label,
    impact_comparison_summary_label,
    source_connector_labels,
)
from wilq.schemas import (
    ActionApplyRequest,
    ActionApplyResult,
    ActionConfirmRequest,
    ActionConfirmResult,
    ActionImpactCheckRequest,
    ActionImpactCheckResult,
    ActionMode,
    ActionMutationApplyContract,
    ActionMutationAuditRecord,
    ActionMutationReadinessBlocker,
    ActionMutationReadinessRequirement,
    ActionMutationReadinessResponse,
    ActionMutationReadinessSummaryResponse,
    ActionObject,
    ActionPreviewCardViewModel,
    ActionPreviewItemViewModel,
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
SERVICE_PROFILE_PUBLIC_REVIEW_SCOPES = {"public_service_card"}
SERVICE_PROFILE_PRIVATE_REVIEW_SCOPES = {
    "private_service_proposal",
    "private_claim_policy_proposal",
    "private_evidence_policy_proposal",
}
DEFAULT_ACTION_LIST_CACHE_SECONDS = 15.0


@dataclass(frozen=True)
class WordPressDraftApplyCapability:
    handoff: ContentWordPressDraftHandoff
    draft_package: ContentDraftPackage
    write_authorization: ContentWordPressDraftWriteAuthorization


@dataclass(frozen=True)
class ActionListCacheEntry:
    created_at: float
    actions: list[ActionObject]


_cached_action_list: ActionListCacheEntry | None = None


def seed_static_actions() -> dict[str, ActionObject]:
    actions = seed_core_prepare_actions()
    action = ActionObject(
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
                "preview_contract": "recommendation_apply_preview_v1",
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
            title="Przygotuj kolejkę przeglądu pliku produktowego Merchant Center",
            domain=OpportunityDomain.merchant,
            connector="google_merchant_center",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=[connector_evidence_id("google_merchant_center")],
            human_diagnosis=(
                "Merchant Center jest core workflow WILQ. W clean runtime WILQ może "
                "przygotować tylko kolejkę bezpieczną do sprawdzenia, dopóki odczyt nie "
                "dostarczy metryk problemów pliku produktowego."
            ),
            recommended_reason=(
                "Uruchom odczyt danych Merchant albo użyj istniejących evidence, "
                "potem sprawdź w WILQ podgląd zmian przed jakąkolwiek zmianą pliku produktowego."
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
                    "automatyczna zmiana pliku produktowego",
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
                "required_breakdown_labels": [
                    "strona wejścia",
                    "źródło i medium ruchu",
                    "kampania",
                ],
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
                "Treści są jednym z głównych obszarów pracy WILQ. WILQ może "
                "przygotować tylko kolejkę bezpieczną do sprawdzenia, dopóki "
                "GSC, WordPress i GA4 nie dostarczą danych o publicznych URL, "
                "zapytaniach, stronach i zachowaniu użytkowników."
            ),
            recommended_reason=(
                "Zbierz dane GSC dla zapytań i stron oraz spis treści WordPress, "
                "potem klasyfikuj: zachować, odświeżyć, scalić, utworzyć albo "
                "zablokować bez obietnic leadów ani rankingów."
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
                            "Brak danych GSC dla zapytań i stron oraz spisu treści "
                            "WordPress w świeżym odczycie. Najpierw zbierz dane "
                            "źródłowe, potem oceniaj zachowanie, odświeżenie, "
                            "scalenie albo utworzenie treści."
                        ),
                        "wordpress_inventory_match": "missing",
                        "decision_options": ["block"],
                        "metric_snapshot": {},
                        "brief_goal": (
                            "Zablokuj pisanie treści do czasu zebrania danych GSC "
                            "i spisu treści WordPress."
                        ),
                        "intent": "brak intencji do pisania bez danych źródłowych",
                        "content_angle": (
                            "Nie przygotowuj tekstu bez potwierdzonego publicznego URL i dowodów."
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
                            "Nie ustalaj meta description bez potwierdzonego tematu i URL."
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
                            "brak danych GSC dla zapytań i stron",
                            "brak spisu treści WordPress",
                        ],
                        "missing_evidence": [
                            "brak publicznego URL",
                            "brak danych GSC",
                            "brak spisu treści WordPress",
                        ],
                        "forbidden_claims": [
                            "wzrost liczby leadów",
                            "wpływ na przychód",
                            "gwarancja pozycji",
                        ],
                        "required_validation": [
                            "gsc_query_page_check",
                            "wordpress_inventory_check",
                            "content_url_preflight_review",
                            "duplicate_or_cannibalization_check",
                            "human_confirm_before_wordpress_write",
                        ],
                        "blocked_claims": [
                            "wzrost liczby leadów",
                            "wpływ na przychód",
                            "gwarancja pozycji",
                        ],
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
                "blocked_claims": [
                    "wzrost liczby leadów",
                    "wpływ na przychód",
                    "gwarancja pozycji",
                ],
                "destructive": False,
            },
            validation_status="not_validated",
            created_by="system_core_seed",
        ),
    ]
    service_profile_action = _service_profile_knowledge_promotion_action()
    if service_profile_action is not None:
        actions.append(service_profile_action)
    private_proposal_action = _service_profile_private_proposal_promotion_action()
    if private_proposal_action is not None:
        actions.append(private_proposal_action)
    actions.append(_wordpress_existing_draft_update_action())
    return {action.id: action for action in actions}


def _wordpress_existing_draft_update_action() -> ActionObject:
    return existing_draft_update_action()


def _service_profile_knowledge_promotion_action() -> ActionObject | None:
    profile = content_service_profile_response()
    review_actions_by_target = {
        action.target_card_id: action
        for action in profile.review_actions
        if action.review_scope in SERVICE_PROFILE_PUBLIC_REVIEW_SCOPES
        and action.target_card_id
    }
    rows: list[dict[str, Any]] = []
    for section in profile.service_sections:
        review_action = review_actions_by_target.get(section.card_id)
        if review_action is None:
            continue
        if section.status != "source_backed_review_required":
            continue
        if "public_site" not in section.source_connector_labels:
            continue
        rows.append(
            {
                "id": f"knowledge_promotion_{section.card_id}",
                "preview_contract": "service_profile_knowledge_promotion_preview_v1",
                "operation_type": "knowledge_card_promotion_review",
                "target_card_id": section.card_id,
                "target_card_title": section.title,
                "current_lifecycle": section.status,
                "current_lifecycle_label": section.status_label,
                "target_lifecycle": "approved_current",
                "target_lifecycle_label": "zatwierdzone i aktualne po review człowieka",
                "source_fact_ids": section.source_fact_ids,
                "source_connector_labels": section.source_connector_labels,
                "source_lineage_labels": section.source_lineage_labels,
                "review_action_id": review_action.action_id,
                "required_human_role": review_action.required_human_role,
                "blocked_claims": [claim.label for claim in section.forbidden_claims],
                "claims_needing_review": [
                    claim.label for claim in section.claims_needing_review
                ],
                "required_validation": [
                    "public_source_trace_review",
                    "blocked_claims_review",
                    "owner_human_review_record",
                    "separate_audited_promotion_request",
                ],
                "required_validation_labels": [
                    "sprawdź źródła publiczne",
                    "sprawdź zakazane twierdzenia",
                    "zapisz decyzję Wilka/ownera",
                    "przygotuj osobny audyt awansu",
                ],
                "promotion_blocked_reason": (
                    "Ta akcja tylko przygotowuje request po review. Nie edytuje "
                    "source_facts.json, nie zmienia lifecycle i nie odblokowuje "
                    "production-depth."
                ),
                "evidence_ids": [SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID],
                "apply_allowed": False,
                "api_mutation_ready": False,
                "destructive": False,
            }
        )
    if not rows:
        return None
    return ActionObject(
        id="act_prepare_service_profile_knowledge_promotion",
        title="Przygotuj request awansu wiedzy Service Profile",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=[SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID],
        human_diagnosis=(
            "Service Profile ma publiczne karty usługowe ze źródłami, ale nadal "
            "są review-required. WILQ może przygotować audytowalny request awansu "
            "po decyzji Wilka/ownera, bez zmiany wiedzy i bez odblokowania "
            "production-depth."
        ),
        recommended_reason=(
            "Po zebraniu decyzji z review kart usługowych sprawdź, które source "
            "facts mają pełny ślad źródła, review twierdzeń i właściciela decyzji. "
            "Dopiero późniejsza osobna ścieżka audytu może zmienić lifecycle."
        ),
        payload={
            "action_type": SERVICE_PROFILE_KNOWLEDGE_PROMOTION_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "mode": "prepare_only",
            "preview_contract": "service_profile_knowledge_promotion_preview_v1",
            "source_connectors": ["public_site"],
            "source_fact_count": profile.technical_trace.source_fact_count,
            "target_lifecycle": "approved_current",
            "payload_preview": rows,
            "payload_preview_total": len(rows),
            "payload_preview_included": len(rows),
            "required_validation": [
                "public_source_trace_review",
                "blocked_claims_review",
                "owner_human_review_record",
                "separate_audited_promotion_request",
            ],
            "blocked_claims": [
                "automatyczny awans wiedzy",
                "production-depth bez owner review",
                "edycja source_facts.json z tej akcji",
                "publikacja lub szkic finalny na podstawie review-required",
            ],
            "evidence_ids": [SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID],
            "apply_allowed": False,
            "api_mutation_ready": False,
            "destructive": False,
        },
        validation_status="not_validated",
        created_by="system_core_seed",
    )


def _service_profile_private_proposal_promotion_action() -> ActionObject | None:
    profile = content_service_profile_response()
    review_actions_by_target = {
        action.target_card_id: action
        for action in profile.review_actions
        if action.review_scope in SERVICE_PROFILE_PRIVATE_REVIEW_SCOPES
        and action.target_card_id
    }
    rows: list[dict[str, Any]] = []
    for proposal in profile.private_source_proposals:
        review_action = review_actions_by_target.get(proposal.target_card_id)
        if review_action is None:
            continue
        if proposal.review_status != "review_required":
            continue
        rows.append(
            {
                "id": f"private_proposal_promotion_{proposal.proposal_id}",
                "preview_contract": "private_source_proposal_promotion_preview_v1",
                "operation_type": "private_source_proposal_promotion_review",
                "proposal_id": proposal.proposal_id,
                "source_id": proposal.source_id,
                "source_type": proposal.source_type,
                "privacy_class": proposal.privacy_class,
                "scope": proposal.scope,
                "target_card_id": proposal.target_card_id,
                "target_card_title": proposal.target_card_title,
                "review_action_id": review_action.action_id,
                "required_human_role": review_action.required_human_role,
                "support_level": proposal.support_level,
                "risk_tier": proposal.risk_tier,
                "freshness_status": proposal.freshness_status,
                "audience": proposal.audience,
                "data_classes": proposal.data_classes,
                "source_block_refs": proposal.source_block_refs,
                "retention_decision": proposal.retention_decision,
                "deletion_path": proposal.deletion_path,
                "eval_case_ids": proposal.eval_case_ids,
                "confidence_label": proposal.confidence_label,
                "blocked_claims": proposal.blocked_claims,
                "required_validation": [
                    "redacted_source_trace_review",
                    "private_owner_human_review_record",
                    "blocked_claims_review",
                    "separate_source_fact_promotion_request",
                    "focused_eval_before_policy_or_service_use",
                ],
                "required_validation_labels": [
                    "sprawdź redacted źródło",
                    "zapisz decyzję Wilka/ownera",
                    "sprawdź zakazane twierdzenia",
                    "przygotuj osobny request awansu source fact",
                    "uruchom focused eval przed użyciem",
                ],
                "promotion_blocked_reason": (
                    "Ta akcja tylko przygotowuje review prywatnej propozycji. Nie "
                    "edytuje source_facts.json, nie promuje private proposal, nie "
                    "zmienia lifecycle i nie odblokowuje production-depth."
                ),
                "evidence_ids": [SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID],
                "redacted": True,
                "apply_allowed": False,
                "api_mutation_ready": False,
                "destructive": False,
            }
        )
    if not rows:
        return None
    return ActionObject(
        id="act_prepare_service_profile_private_proposal_promotion",
        title="Przygotuj review prywatnych propozycji Service Profile",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=[SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID],
        human_diagnosis=(
            "Service Profile ma redacted propozycje z ekologus-ai dla usług i "
            "claim-policy. WILQ może przygotować ich review, ale nie może "
            "promować prywatnego źródła ani traktować go jako production-depth "
            "bez decyzji człowieka i osobnego audytu."
        ),
        recommended_reason=(
            "Przed użyciem Eko-Opieki, Audytu zgodności, stylu marki albo "
            "legal-safety w treściach sprawdź redacted source trace, blokowane "
            "twierdzenia, rolę review i wymagany follow-up."
        ),
        payload={
            "action_type": SERVICE_PROFILE_PRIVATE_PROPOSAL_PROMOTION_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "mode": "prepare_only",
            "preview_contract": "private_source_proposal_promotion_preview_v1",
            "source_connectors": ["wordpress_ekologus"],
            "private_source_labels": ["ekologus_ai_private_source_catalog"],
            "proposal_count": len(profile.private_source_proposals),
            "payload_preview": rows,
            "payload_preview_total": len(rows),
            "payload_preview_included": len(rows),
            "required_validation": [
                "redacted_source_trace_review",
                "private_owner_human_review_record",
                "blocked_claims_review",
                "separate_source_fact_promotion_request",
                "focused_eval_before_policy_or_service_use",
            ],
            "blocked_claims": [
                "automatyczny awans prywatnej propozycji",
                "production-depth bez owner review",
                "edycja source_facts.json z tej akcji",
                "użycie raw private text w publicznej treści",
                "automatyczna bramka brand/legal-safety bez review",
            ],
            "evidence_ids": [SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID],
            "apply_allowed": False,
            "api_mutation_ready": False,
            "destructive": False,
        },
        validation_status="not_validated",
        created_by="system_core_seed",
    )


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


def list_actions_cached() -> list[ActionObject]:
    """Reuse one action registry build across the dashboard list reads."""
    cached = _read_action_list_cache()
    if cached is not None:
        return cached
    actions = list_actions()
    _write_action_list_cache(actions)
    return actions


def clear_action_list_cache() -> None:
    global _cached_action_list
    _cached_action_list = None


def _read_action_list_cache() -> list[ActionObject] | None:
    cache_seconds = _action_list_cache_seconds()
    if cache_seconds <= 0 or _cached_action_list is None:
        return None
    if monotonic() - _cached_action_list.created_at > cache_seconds:
        return None
    return _cached_action_list.actions


def _write_action_list_cache(actions: list[ActionObject]) -> None:
    global _cached_action_list
    if _action_list_cache_seconds() <= 0:
        return
    _cached_action_list = ActionListCacheEntry(created_at=monotonic(), actions=actions)


def _action_list_cache_seconds() -> float:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return 0.0
    configured = os.getenv("WILQ_ACTION_LIST_CACHE_SECONDS")
    if configured is None:
        return DEFAULT_ACTION_LIST_CACHE_SECONDS
    try:
        return max(0.0, float(configured))
    except ValueError:
        return DEFAULT_ACTION_LIST_CACHE_SECONDS


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
    action = _with_persisted_validation_state(action)
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
    return business_context_action(
        missing_read_contracts=missing_read_contracts,
        evidence_ids=_unique(
            [connector_evidence_id("google_ads"), *latest_run.evidence_ids]
        ),
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
    return target_confirmation_action(
        missing_read_contracts=missing_read_contracts,
        evidence_ids=_unique(
            [connector_evidence_id("google_ads"), *latest_run.evidence_ids]
        ),
    )


def _google_ads_strategy_review_action() -> ActionObject | None:
    latest_run = _latest_google_ads_vendor_read()
    latest_review = ads_strategy_review_state()
    if (
        latest_run is None
        or latest_run.status != ConnectorRefreshStatus.completed
        or not latest_run.vendor_data_collected
        or not ads_business_context_configured()
        or (latest_review is not None and latest_review.outcome == "approved_for_prepare")
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
    return keyword_planner_access_action(
        blocker=blocker,
        evidence_ids=_unique(
            [connector_evidence_id("google_ads"), *latest_run.evidence_ids]
        ),
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
    return "token deweloperski nie ma zatwierdzonego dostępu do Keyword Plannera"


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
        action = _merchant_feed_issue_action(
            merchant_action_metrics=merchant_action_metrics,
            merchant_issue_clusters=merchant_issue_clusters,
            merchant_payload_preview=merchant_payload_preview,
        )
        actions[action.id] = action

    ga4_facts = by_connector.get("google_analytics_4", [])
    ga4_dimensioned_facts = _ga4_dimensioned_metric_facts(ga4_facts)
    if ga4_dimensioned_facts:
        ga4_action_metrics = ga4_dimensioned_facts[:8]
        action = _ga4_tracking_quality_action(
            ga4_action_metrics=ga4_action_metrics,
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
        action = _content_refresh_queue_action(
            content_facts=content_facts,
            content_action_metrics=content_action_metrics,
            content_payload=content_payload,
        )
        actions[action.id] = action
        wordpress_draft_action = _wordpress_draft_handoff_action(
            content_payload=content_payload,
            content_action_metrics=content_action_metrics,
        )
        if wordpress_draft_action is not None:
            actions[wordpress_draft_action.id] = wordpress_draft_action
            wordpress_draft_apply_action = _wordpress_draft_apply_action(
                handoff_action=wordpress_draft_action,
            )
            actions[wordpress_draft_apply_action.id] = wordpress_draft_apply_action

    google_ads_facts = by_connector.get("google_ads", [])
    demand_gen_action = _demand_gen_readiness_review_action(
        google_ads_facts,
        by_connector.get("google_analytics_4", []),
    )
    if demand_gen_action is not None:
        actions[demand_gen_action.id] = demand_gen_action

    campaign_review_payload = campaign_review_payload_from_metric_facts(google_ads_facts)
    if campaign_review_payload is not None:
        action = _campaign_review_action(
            google_ads_facts=google_ads_facts,
            campaign_review_payload=campaign_review_payload,
        )
        actions[action.id] = action

    recommendation_review_payload = recommendation_review_payload_from_metric_facts(
        google_ads_facts
    )
    if recommendation_review_payload is not None:
        action = _recommendation_review_action(
            google_ads_facts=google_ads_facts,
            recommendation_review_payload=recommendation_review_payload,
        )
        actions[action.id] = action

    change_history_payload = change_history_impact_payload_from_metric_facts(google_ads_facts)
    if change_history_payload is not None:
        action = _change_history_impact_action(
            google_ads_facts=google_ads_facts,
            change_history_payload=change_history_payload,
        )
        actions[action.id] = action

    search_term_ngram_payload = search_term_ngram_payload_from_metric_facts(google_ads_facts)
    if search_term_ngram_payload is not None:
        action = _search_term_ngram_action(
            google_ads_facts=google_ads_facts,
            search_term_ngram_payload=search_term_ngram_payload,
        )
        actions[action.id] = action

    custom_segment_payload = custom_segment_payload_from_metric_facts(google_ads_facts)
    if custom_segment_payload is not None:
        action = _custom_segment_action(
            google_ads_facts=google_ads_facts,
            custom_segment_payload=custom_segment_payload,
        )
        actions[action.id] = action

    negative_keyword_payload = negative_keyword_payload_from_metric_facts(google_ads_facts)
    if negative_keyword_payload is not None:
        action = _negative_keyword_action(
            google_ads_facts=google_ads_facts,
            negative_keyword_payload=negative_keyword_payload,
        )
        actions[action.id] = action

    localo_facts = _localo_action_metric_facts(by_connector.get("localo", []))
    localo_visibility_payload = localo_visibility_review_payload_from_metric_facts(localo_facts)
    if localo_visibility_payload is not None:
        action = _localo_visibility_review_action(
            localo_facts=localo_facts,
            localo_visibility_payload=localo_visibility_payload,
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


def _merchant_feed_issue_action(
    *,
    merchant_action_metrics: list[MetricFact],
    merchant_issue_clusters: list[dict[str, Any]],
    merchant_payload_preview: list[dict[str, Any]],
) -> ActionObject:
    return merchant_feed_issue_action(
        merchant_action_metrics=merchant_action_metrics,
        merchant_issue_clusters=merchant_issue_clusters,
        merchant_payload_preview=merchant_payload_preview,
        metric_sentence=_metric_sentence(merchant_action_metrics),
        preview_contract=MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT,
    )


def _ga4_tracking_quality_action(
    *,
    ga4_action_metrics: list[MetricFact],
) -> ActionObject:
    return ga4_tracking_quality_action(
        ga4_action_metrics=ga4_action_metrics,
        metric_sentence=_metric_sentence(ga4_action_metrics),
    )


def _localo_visibility_review_action(
    *,
    localo_facts: list[MetricFact],
    localo_visibility_payload: dict[str, Any],
) -> ActionObject:
    metrics = _prioritize_action_metrics(
        localo_facts,
        required_names={
            "localo_active_place_count",
            "localo_tracked_keyword_count",
            "localo_avg_visibility_current",
            "localo_reviews_count",
        },
    )[:10]
    return localo_visibility_review_action(
        localo_metrics=metrics,
        localo_visibility_payload=localo_visibility_payload,
        metric_sentence=_metric_sentence(metrics),
    )


def _negative_keyword_action(
    *,
    google_ads_facts: list[MetricFact],
    negative_keyword_payload: dict[str, Any],
) -> ActionObject:
    return negative_keyword_action(
        google_ads_facts=google_ads_facts,
        negative_keyword_payload=negative_keyword_payload,
    )


def _custom_segment_action(
    *,
    google_ads_facts: list[MetricFact],
    custom_segment_payload: dict[str, Any],
) -> ActionObject:
    return custom_segment_action(
        google_ads_facts=google_ads_facts,
        custom_segment_payload=custom_segment_payload,
    )


def _search_term_ngram_action(
    *,
    google_ads_facts: list[MetricFact],
    search_term_ngram_payload: dict[str, Any],
) -> ActionObject:
    return search_term_ngram_action(
        google_ads_facts=google_ads_facts,
        search_term_ngram_payload=search_term_ngram_payload,
    )


def _recommendation_review_action(
    *,
    google_ads_facts: list[MetricFact],
    recommendation_review_payload: dict[str, Any],
) -> ActionObject:
    return recommendation_review_action(
        google_ads_facts=google_ads_facts,
        recommendation_review_payload=recommendation_review_payload,
    )


def _change_history_impact_action(
    *,
    google_ads_facts: list[MetricFact],
    change_history_payload: dict[str, Any],
) -> ActionObject:
    return change_history_impact_action(
        google_ads_facts=google_ads_facts,
        change_history_payload=change_history_payload,
    )


def _campaign_review_action(
    *,
    google_ads_facts: list[MetricFact],
    campaign_review_payload: dict[str, Any],
) -> ActionObject:
    return campaign_review_action(
        google_ads_facts=google_ads_facts,
        campaign_review_payload=campaign_review_payload,
    )


def _content_refresh_queue_action(
    *,
    content_facts: list[MetricFact],
    content_action_metrics: list[MetricFact],
    content_payload: dict[str, Any] | None,
) -> ActionObject:
    return content_refresh_queue_action(
        content_facts=content_facts,
        content_action_metrics=content_action_metrics,
        content_payload=content_payload,
        unique_evidence_ids=_unique(fact.evidence_id for fact in content_action_metrics),
        metric_sentence=_metric_sentence(content_facts),
    )


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
        DEMAND_GEN_CAMPAIGN_MODE_REVIEW_CONTRACT,
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
    demand_gen_campaign_mode_review_rows = demand_gen_campaign_mode_review_rows_from_campaigns(
        demand_gen_rows
    )
    if (
        demand_gen_contract_has_ready_fact(
            google_ads_facts,
            status_fact_name=DEMAND_GEN_AD_READ_STATUS_FACT,
            row_count_fact_name=DEMAND_GEN_AD_READ_ROW_COUNT_FACT,
        )
        or demand_gen_ad_group_ad_rows
    ):
        available_read_contracts.append(DEMAND_GEN_AD_GROUP_AD_ROWS_CONTRACT)
        missing_read_contracts = [
            contract
            for contract in missing_read_contracts
            if contract != DEMAND_GEN_AD_GROUP_AD_ROWS_CONTRACT
        ]
    if (
        demand_gen_contract_has_ready_fact(
            google_ads_facts,
            status_fact_name=DEMAND_GEN_CREATIVE_ASSET_STATUS_FACT,
            row_count_fact_name=DEMAND_GEN_CREATIVE_ASSET_ROW_COUNT_FACT,
        )
        or demand_gen_creative_asset_rows
    ):
        available_read_contracts.append(DEMAND_GEN_CREATIVE_ASSET_ROWS_CONTRACT)
        missing_read_contracts = [
            contract
            for contract in missing_read_contracts
            if contract != DEMAND_GEN_CREATIVE_ASSET_ROWS_CONTRACT
        ]
    available_read_contracts.extend(
        [
            DEMAND_GEN_LANDING_QUALITY_CONTRACT,
            DEMAND_GEN_CAMPAIGN_MODE_REVIEW_CONTRACT,
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
        demand_gen_campaign_mode_review_rows=[
            row.model_dump(mode="json") for row in demand_gen_campaign_mode_review_rows
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
    return demand_gen_readiness_action(
        payload=payload,
        evidence_ids=evidence_ids,
        action_metrics=action_metrics,
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
        for fact in metric_store().list_metric_facts_by_evidence_ids(latest_run.evidence_ids)
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
                    int(fact.value) for fact in group_facts if isinstance(fact.value, int | float)
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
                "resolution_label": merchant_resolution_label(cluster.get("resolution")),
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
                    "Podgląd klastra problemów pliku produktowego do sprawdzenia. WILQ może "
                    "przygotować kolejkę przeglądu, ale nie może zmienić pliku produktowego ani "
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
                    "automatyczna zmiana pliku produktowego",
                    "nadpisanie głównego pliku produktowego",
                    "zapis do pliku produktowego",
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
    return "".join(char for char in normalized if char.isalnum())


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
    preview_items = [_wordpress_draft_handoff_preview_item(item) for item in brief_previews[:4]]
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
            "WILQ ma kolejkę treści z GSC, WordPress i Ahrefs i może przygotować "
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
                "wordpress_draft_preview_review",
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


def _wordpress_draft_apply_action(*, handoff_action: ActionObject) -> ActionObject:
    return ActionObject(
        id="act_apply_wordpress_draft_handoff",
        title="Aktywuj zapis szkicu WordPress draft-only",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=handoff_action.evidence_ids,
        metrics=handoff_action.metrics,
        human_diagnosis=(
            "To jest jawna propozycja apply-mode dla pierwszej bezpiecznej klasy "
            "zapisu: utworzenia szkicu WordPress. Nie publikuje i nie aktualizuje "
            "istniejących wpisów."
        ),
        recommended_reason=(
            "Użyj tej akcji do sprawdzania gotowości przyszłego zapisu szkicu. "
            "Dopóki podgląd zmian, review człowieka, potwierdzenie operatora, "
            "audyt wpływu, zgoda środowiska i warstwa wykonania nie są gotowe, "
            "WILQ nie może zapisać szkicu w WordPress."
        ),
        payload={
            "action_type": "wordpress_draft_handoff",
            "connector": "wordpress_ekologus",
            "mode": "apply_blocked",
            "preview_contract": "wordpress_draft_apply_preview_v1",
            "depends_on_action_id": handoff_action.id,
            "allowed_operation": "create_wordpress_draft",
            "apply_contract": _wordpress_draft_apply_contract_payload(handoff_action),
            "source_connectors": handoff_action.payload.get("source_connectors", []),
            "source_metric_names": handoff_action.payload.get("source_metric_names", []),
            "required_input_contracts": handoff_action.payload.get(
                "required_input_contracts",
                [],
            ),
            "payload_preview": handoff_action.payload.get("payload_preview", []),
            "required_validation": [
                "content_url_preflight_review",
                "final_canonical_review",
                "duplicate_or_cannibalization_check",
                "legal_factual_review",
                "content_draft_readiness_review",
                "wordpress_draft_preview_review",
                "human_confirm_before_wordpress_write",
                "wordpress_draft_write_readiness",
            ],
            "blocked_claims": [
                "wordpress_publish",
                "wordpress_update_existing_post",
                "wordpress_delete_post",
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


def _wordpress_draft_apply_contract_payload(
    handoff_action: ActionObject,
) -> dict[str, Any]:
    return {
        "contract": "action_apply_contract_v1",
        "action_id": "act_apply_wordpress_draft_handoff",
        "action_type": "wordpress_draft_handoff",
        "connector": "wordpress_ekologus",
        "allowed_operation": "create_wordpress_draft",
        "required_mode": "apply",
        "draft_only": True,
        "publication_allowed": False,
        "destructive_allowed": False,
        "adapter_status": "not_implemented",
        "required_env_flags": ["WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES"],
        "required_input_contracts": handoff_action.payload.get("required_input_contracts", []),
        "required_audit_events": [
            "action_preview_generated",
            "human_review_*",
            "action_apply_confirmed",
        ],
        "blocked_outputs": [
            "wordpress_publish",
            "wordpress_update_existing_post",
            "wordpress_delete_post",
            "production_publish_ready_claim",
        ],
        "operator_summary": (
            "Ten apply-mode obiekt nadal jest zablokowany. Może w przyszłości "
            "utworzyć tylko szkic WordPress po pełnym preview, review, confirm, "
            "impact check, env readiness i adapterze z audytem."
        ),
    }


def _wordpress_draft_handoff_preview_item(item: dict[str, Any]) -> dict[str, Any]:
    source_public_url = (
        item.get("source_public_url") if isinstance(item.get("source_public_url"), str) else None
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
        "wordpress_draft_handoff_status": "blocked_until_draft_checks_complete",
        "wordpress_draft_handoff_summary": [
            "stan przekazania do WordPress: zablokowany do przejścia kontroli szkicu"
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
    social_source_facts = [fact for fact in social_facts if _is_social_source_metric(fact)]
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
            "require_social_history_duplicate_review",
            "require_human_review_before_apply",
        ],
        "source_inputs": _social_source_inputs(social_metrics),
        "blocked_claims": [
            "zwrot z reklam",
            "przychód",
            "wzrost konwersji",
            "wdrożona poprawka produktu",
            "brak powtórzeń historycznych postów",
        ],
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
                "W procesie social pokaż tylko propozycje szkiców z dowodami. "
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
    if fact.name == "content_object_seen":
        return any(
            isinstance(fact.dimensions.get(key), str) and fact.dimensions.get(key)
            for key in ("final_canonical_url", "source_public_url", "canonical_url")
        )
    return bool(fact.name)


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
        return "Najważniejsze fakty: nie ma potwierdzonych metryk do pokazania"
    samples = ", ".join(f"{_metric_fact_label(fact.name)}: {fact.value}" for fact in facts[:4])
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


def _plain_metric_value_label(
    value: Any,
    *,
    missing_label: str = "wartość niepotwierdzona",
) -> str:
    if isinstance(value, bool):
        return "tak" if value else "nie"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    if isinstance(value, str) and value:
        return value
    return missing_label


def _content_primary_url_label(item: dict[str, Any]) -> str:
    for key in ("final_canonical_url", "intended_final_url", "source_public_url"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return "URL niepotwierdzony"


def _content_metric_snapshot_label(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    parts: list[str] = []
    clicks = value.get("clicks")
    impressions = value.get("impressions")
    ctr = value.get("ctr")
    position = value.get("average_position")
    if isinstance(clicks, int | float):
        parts.append(f"kliknięcia: {_plain_metric_value_label(clicks)}")
    if isinstance(impressions, int | float):
        parts.append(f"wyświetlenia: {_plain_metric_value_label(impressions)}")
    if isinstance(ctr, int | float):
        parts.append(f"CTR: {ctr * 100:.2f}%")
    if isinstance(position, int | float):
        parts.append(f"pozycja: {_plain_metric_value_label(position)}")
    return "; ".join(parts)


def _metric_snapshot_preview_rows(
    metric_snapshot: dict[Any, Any],
    metric_labels: dict[Any, Any],
) -> list[ActionPreviewRowViewModel]:
    rows: list[ActionPreviewRowViewModel] = []
    for key, value in metric_snapshot.items():
        label = metric_labels.get(key)
        if not isinstance(label, str) or not label:
            continue
        rows.append(_preview_row(label, _metric_snapshot_value_label(str(key), value)))
    return rows


def _metric_snapshot_value_label(key: str, value: Any) -> str:
    percent_metric_keys = {
        "engagement_rate",
        "localo_avg_visibility_change",
        "localo_review_reply_rate",
    }
    if key in percent_metric_keys and isinstance(value, int | float):
        return f"{value * 100:.2f}%"
    return _plain_metric_value_label(value)


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
        warnings.append("Akcje o wysokim i krytycznym ryzyku wymagają osobnego wsparcia produktu.")
    valid = not errors
    action.validation_status = "valid" if valid else "invalid"
    if not valid:
        action.status = ActionStatus.validation_failed
    elif action.mode == ActionMode.apply:
        action.status = ActionStatus.ready_to_apply
    else:
        action.status = ActionStatus.ready
    action.review_gate = _action_review_gate(action)
    local_state_store().save_action_validation_state(
        action_id=action.id,
        status=action.status.value,
        validation_status=action.validation_status,
    )
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
    raw_preview_items = _payload_preview_items(action.payload)
    included_items = raw_preview_items[: preview_request.max_items]
    preview_cards = _action_preview_cards(action)
    preview_items = _action_preview_item_view_models(
        action=action,
        raw_items=raw_preview_items,
        preview_cards=preview_cards,
        max_items=preview_request.max_items,
    )
    blockers = _action_preview_blockers(action, raw_preview_items)
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
            preview_items=len(raw_preview_items),
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
        preview_contract=_preview_contract(action.payload, raw_preview_items),
        preview_items=preview_items,
        preview_cards=preview_cards,
        preview_items_total=len(raw_preview_items),
        omitted_items=max(len(raw_preview_items) - len(included_items), 0),
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
    wordpress_capability, capability_errors = _wordpress_draft_apply_capability(action, request)
    errors.extend(capability_errors)
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
    if wordpress_capability is None and not _action_payload_apply_allowed(action.payload):
        errors.append("Payload akcji nie pozwala jeszcze na zapis zmian.")
    if wordpress_capability is None and not _action_payload_api_mutation_ready(action.payload):
        errors.append("Payload akcji nie jest gotowy do mutacji API.")
    if mutation_adapter is None:
        errors.append("Brakuje bezpiecznej ścieżki zapisu zmian dla tej akcji.")
    adapter_result: dict[str, Any] | None = None
    if not errors and mutation_adapter is not None:
        adapter_result, adapter_errors = _execute_supported_mutation_adapter(
            action,
            mutation_adapter,
            request,
            wordpress_capability,
        )
        errors.extend(adapter_errors)

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
        adapter_result=adapter_result,
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
            adapter_result=adapter_result,
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
        adapter_result=adapter_result,
    )


def _wordpress_draft_apply_capability(
    action: ActionObject,
    request: ActionApplyRequest | None,
) -> tuple[WordPressDraftApplyCapability | None, list[str]]:
    if action.id != "act_apply_wordpress_draft_handoff":
        return None, []
    input_contract = request.wordpress_draft if request is not None else None
    if input_contract is None:
        return None, [
            "Apply szkicu WordPress wymaga typed work item, handoff, draft package i target URL."
        ]
    if request is None or not request.confirmed_by:
        return None, ["Apply szkicu WordPress wymaga potwierdzonego aktora operatora."]

    from wilq.briefing.content_diagnostics import build_content_diagnostics_cached

    diagnostics = build_content_diagnostics_cached()
    review = content_workflow_store().latest_human_review(input_contract.work_item_id)
    if review is None:
        return None, ["Brakuje zapisanego review człowieka dla wskazanego work itemu."]
    audit = content_workflow_store().latest_audit_for_review(review.id)
    snapshot = build_content_work_item_diagnostics_snapshot_response_for_work_item(
        diagnostics,
        input_contract.work_item_id,
        human_review=review,
        audit=audit,
    )
    if snapshot is None:
        return None, ["Wskazany work item nie istnieje w aktualnej kolejce WILQ."]
    draft_package = snapshot.draft_package.draft_package_result.draft_package
    handoff = snapshot.wordpress_handoff.handoff_result.handoff
    if draft_package is None or handoff is None:
        return None, ["Brakuje kompletnej paczki szkicu albo handoffu WordPress."]
    if handoff.id != input_contract.handoff_id:
        return None, ["Handoff WordPress nie pasuje do wskazanego ActionObject apply."]
    if draft_package.id != input_contract.draft_package_id:
        return None, ["Paczka szkicu nie pasuje do wskazanego ActionObject apply."]
    if handoff.work_item_id != input_contract.work_item_id:
        return None, ["Handoff nie pasuje do wskazanego work itemu."]
    if handoff.final_canonical_url != input_contract.target_url:
        return None, ["Canonical URL nie pasuje do zatwierdzonego handoffu."]
    target_host = (urlparse(input_contract.target_url).hostname or "").lower()
    if target_host not in {"ekologus.pl", "www.ekologus.pl"}:
        return None, ["Apply szkicu wymaga publicznego canonical URL Ekologus."]
    if handoff.publish_allowed or handoff.destructive_update_allowed:
        return None, ["Handoff WordPress nie jest draft-only."]

    confirmation = _latest_action_confirmation_event(action.audit_events)
    if confirmation is None or confirmation.actor != request.confirmed_by:
        return None, ["Aktor confirm nie pasuje do zapisanego audytu ActionObject."]
    preview = _latest_preview_event(action.audit_events)
    if preview is None:
        return None, ["Brakuje audytu preview ActionObject."]
    return (
        WordPressDraftApplyCapability(
            handoff=handoff,
            draft_package=draft_package,
            write_authorization=ContentWordPressDraftWriteAuthorization(
                action_id=action.id,
                preview_audit_id=preview.id,
                review_audit_id=review.id,
                confirmation_audit_id=confirmation.id,
                confirmed_by=request.confirmed_by,
            ),
        ),
        [],
    )


def mutation_readiness_action(action: ActionObject) -> ActionMutationReadinessResponse:
    action = _with_review_gate(
        _with_persisted_validation_state(action),
        _persisted_audit_events_for_action(action.id),
        _persisted_mutation_audits_for_action(action.id),
    )
    connector = get_connector_status(action.connector)
    mutation_adapter = _supported_mutation_adapter(action)
    latest_preview = _latest_preview_event(action.audit_events)
    latest_confirmation = _latest_action_confirmation_event(action.audit_events)
    latest_impact_check = _latest_action_impact_check_event(action.audit_events)
    latest_mutation_audit = _latest_mutation_audit(
        _persisted_mutation_audits_for_action(action.id)
    )
    wordpress_draft_readiness = _wordpress_draft_write_readiness(action)
    wordpress_activation_packet = _wordpress_draft_activation_packet(action)
    requirements = [
        _mutation_requirement(
            code="valid_action",
            label="Akcja sprawdzona w WILQ",
            satisfied=action.validation_status == "valid",
            evidence=action.validation_status,
        ),
        _mutation_requirement(
            code="apply_mode",
            label="Akcja ma tryb zapisu",
            satisfied=action.mode == ActionMode.apply,
            evidence=action.mode.value,
        ),
        _mutation_requirement(
            code="payload_apply_allowed",
            label="Payload dopuszcza apply",
            satisfied=_action_payload_apply_allowed(action.payload),
            evidence=str(action.payload.get("apply_allowed", False)).lower(),
        ),
        _mutation_requirement(
            code="evidence_present",
            label="Akcja ma dowody źródłowe",
            satisfied=bool(action.evidence_ids),
            evidence=evidence_count_label(action.evidence_ids),
        ),
        _mutation_requirement(
            code="connector_configured",
            label="Connector jest skonfigurowany",
            satisfied=connector is not None and connector.configured,
            evidence=connector.status.value if connector is not None else "missing",
        ),
        _mutation_requirement(
            code="preview_audit",
            label="Podgląd zmian zapisany",
            satisfied=latest_preview is not None,
            evidence=latest_preview.id if latest_preview is not None else None,
        ),
        _mutation_requirement(
            code="confirmation_audit",
            label="Potwierdzenie operatora zapisane",
            satisfied=latest_confirmation is not None,
            evidence=latest_confirmation.id if latest_confirmation is not None else None,
        ),
        _mutation_requirement(
            code="impact_check",
            label="Sprawdzenie efektu zapisane",
            satisfied=_impact_status_from_event(latest_impact_check) == "checked",
            evidence=latest_impact_check.id if latest_impact_check is not None else None,
        ),
        _mutation_requirement(
            code="risk_allowed",
            label="Ryzyko akcji dopuszcza zapis",
            satisfied=action.risk not in {ActionRisk.high, ActionRisk.critical},
            evidence=action.risk.value,
        ),
        _mutation_requirement(
            code="non_destructive",
            label="Akcja nie jest destrukcyjna",
            satisfied=action.payload.get("destructive") is not True,
            evidence=str(action.payload.get("destructive", False)).lower(),
        ),
        _mutation_requirement(
            code="mutation_adapter",
            label="Bezpieczny adapter zapisu istnieje",
            satisfied=mutation_adapter is not None,
            evidence=mutation_adapter,
        ),
    ]
    requirements.extend(
        _wordpress_draft_execution_readiness_requirements(
            action,
            activation_packet=wordpress_activation_packet,
        )
    )
    requirements.extend(
        _wordpress_draft_target_content_readiness_requirements(
            action,
            activation_packet=wordpress_activation_packet,
        )
    )
    requirements.extend(
        _wordpress_draft_write_readiness_requirements(
            action,
            wordpress_draft_readiness=wordpress_draft_readiness,
        )
    )
    blockers = _mutation_readiness_blockers(requirements)
    vendor_write_possible = _vendor_write_possible(action, mutation_adapter)
    ready_to_request_apply = not blockers
    apply_contract = _mutation_apply_contract(action, mutation_adapter)
    target = _mutation_readiness_target(action, activation_packet=wordpress_activation_packet)
    return ActionMutationReadinessResponse(
        action_id=action.id,
        title=action.title,
        connector=action.connector,
        connector_label=action.connector_label,
        mode=action.mode,
        mode_label=action.mode_label,
        risk=action.risk,
        risk_label=action.risk_label,
        validation_status=action.validation_status,
        review_gate_status=action.review_gate.status,
        ready_to_request_apply=ready_to_request_apply,
        vendor_write_possible=vendor_write_possible,
        would_attempt_vendor_write=ready_to_request_apply and vendor_write_possible,
        mutation_adapter=mutation_adapter,
        apply_contract=apply_contract,
        target_candidate_id=target.get("candidate_id"),
        target_label=target.get("label"),
        target_url=target.get("url"),
        write_authorization_status=wordpress_draft_readiness.write_authorization_status
        if wordpress_draft_readiness is not None
        else None,
        missing_audit_event_types=wordpress_draft_readiness.missing_audit_event_types
        if wordpress_draft_readiness is not None
        else [],
        requirements=requirements,
        blockers=blockers,
        operator_next_step=_mutation_readiness_next_step(action, blockers),
        evidence_ids=action.evidence_ids,
        source_connectors=[action.connector],
        latest_mutation_audit_id=latest_mutation_audit.id
        if latest_mutation_audit is not None
        else None,
        latest_mutation_audit_status=latest_mutation_audit.status
        if latest_mutation_audit is not None
        else None,
    )


def _mutation_readiness_target(
    action: ActionObject,
    *,
    activation_packet: ContentWordPressDraftActivationPacketResponse | None = None,
) -> dict[str, str | None]:
    if activation_packet is not None:
        label_parts = [
            part
            for part in [
                activation_packet.topic,
                activation_packet.final_canonical_url,
            ]
            if isinstance(part, str) and part.strip()
        ]
        return {
            "candidate_id": activation_packet.work_item_id,
            "label": " | ".join(label_parts) if label_parts else activation_packet.topic,
            "url": activation_packet.final_canonical_url,
        }
    preview_items = _payload_preview_items(action.payload)
    first = preview_items[0] if preview_items else {}
    candidate_id = first.get("candidate_id")
    topic = first.get("topic")
    url = (
        first.get("final_canonical_url")
        or first.get("intended_final_url")
        or first.get("source_public_url")
    )
    label_parts = [part for part in [topic, url] if isinstance(part, str) and part.strip()]
    return {
        "candidate_id": candidate_id if isinstance(candidate_id, str) else None,
        "label": " | ".join(label_parts) if label_parts else None,
        "url": url if isinstance(url, str) else None,
    }


def mutation_readiness_actions() -> ActionMutationReadinessSummaryResponse:
    items = [mutation_readiness_action(action) for action in list_actions()]
    blocker_counts: dict[str, int] = {}
    for item in items:
        for blocker in item.blockers:
            blocker_counts[blocker.code] = blocker_counts.get(blocker.code, 0) + 1
    first_write_candidate = _first_write_candidate(items)
    top_blockers = [
        code
        for code, _count in sorted(
            blocker_counts.items(),
            key=lambda pair: (-pair[1], pair[0]),
        )[:8]
    ]
    return ActionMutationReadinessSummaryResponse(
        action_count=len(items),
        ready_to_request_apply_count=sum(item.ready_to_request_apply for item in items),
        vendor_write_possible_count=sum(item.vendor_write_possible for item in items),
        would_attempt_vendor_write_count=sum(item.would_attempt_vendor_write for item in items),
        prepare_only_count=sum(item.mode == ActionMode.prepare for item in items),
        missing_adapter_count=blocker_counts.get("missing_mutation_adapter", 0),
        high_risk_blocked_count=blocker_counts.get("missing_risk_allowed", 0),
        top_blockers=top_blockers,
        first_write_candidate=first_write_candidate,
        first_write_candidate_reason=_first_write_candidate_reason(first_write_candidate),
        activation_plan_steps=_activation_plan_steps(first_write_candidate),
        activation_next_step=_activation_next_step(first_write_candidate),
        operator_next_step=_mutation_readiness_summary_next_step(
            items,
            blocker_counts,
            first_write_candidate,
        ),
        items=items,
    )


def _first_write_candidate(
    items: list[ActionMutationReadinessResponse],
) -> ActionMutationReadinessResponse | None:
    if not items:
        return None
    for item in items:
        if item.action_id == "act_apply_wordpress_draft_handoff":
            return item
    for item in items:
        if item.action_id == "act_prepare_wordpress_draft_handoff":
            return item
    candidates = [
        item
        for item in items
        if item.risk in {ActionRisk.low, ActionRisk.medium}
        and item.connector.startswith("wordpress")
    ]
    if candidates:
        return candidates[0]
    low_risk = [item for item in items if item.risk in {ActionRisk.low, ActionRisk.medium}]
    return low_risk[0] if low_risk else items[0]


def _first_write_candidate_reason(
    item: ActionMutationReadinessResponse | None,
) -> str:
    if item is None:
        return "Brak akcji, którą można ocenić jako pierwszą propozycję zapisu."
    if item.action_id in {
        "act_apply_wordpress_draft_handoff",
        "act_prepare_wordpress_draft_handoff",
    }:
        blocker_codes = {blocker.code for blocker in item.blockers}
        if item.mutation_adapter is not None:
            if "missing_wordpress_draft_package_ready" not in blocker_codes:
                return (
                    "Pierwsza propozycja aktywowania zapisu to WordPress draft-only: "
                    "adapter boundary i paczka szkicu już istnieją, ale szkic nadal "
                    "wymaga handoffu, human review, preview/confirm/audit i jawnie "
                    "włączonego env live write. Publikacja i destrukcyjne zmiany są "
                    "zablokowane."
                )
            return (
                "Pierwsza propozycja aktywowania zapisu to WordPress draft-only: "
                "adapter boundary już istnieje, ale szkic nadal wymaga handoffu, "
                "paczki treści, preview/review/confirm/audit i jawnie włączonego "
                "env live write. Publikacja i destrukcyjne zmiany są zablokowane."
            )
        return (
            "Pierwsza propozycja aktywowania zapisu to WordPress draft-only: "
            "najpierw tworzy szkic, nie publikuje, ma osobny readiness endpoint i "
            "wymaga osobnego adaptera wykonania, env i pełnego audit trail."
        )
    return (
        "To najbliższa niskiego/średniego ryzyka akcja do oceny jako przyszły "
        "write adapter; nadal musi przejść readiness, preview, review i confirm."
    )


def _activation_plan_steps(
    item: ActionMutationReadinessResponse | None,
) -> list[str]:
    if item is None:
        return ["Najpierw utwórz bezpieczną propozycję zapisu z dowodami."]
    steps = [
        "Utrzymaj zakres draft-only i brak publikacji/destrukcyjnych zmian.",
    ]
    if item.action_id == "act_apply_wordpress_draft_handoff":
        steps.append("Doprowadź apply-mode ActionObject przez validate, preview, review i confirm.")
    else:
        steps.append("Zbuduj osobny apply-capable ActionObject dla tej klasy zapisu.")
    blocker_codes = {blocker.code for blocker in item.blockers}
    if item.mutation_adapter is not None:
        if "missing_wordpress_draft_package_ready" in blocker_codes:
            steps.append(
                "Nie dodawaj kolejnego adaptera: boundary istnieje, a live write "
                "blokują handoff, paczka szkicu, audyt i env."
            )
        else:
            steps.append(
                "Nie dodawaj kolejnego adaptera: boundary i paczka szkicu istnieją, "
                "a live write blokują handoff, review/confirm/audit i env."
            )
    if "missing_payload_apply_allowed" in blocker_codes:
        steps.append("Odblokuj payload apply dopiero po przejściu review i readiness.")
    if "missing_preview_audit" in blocker_codes:
        steps.append("Wygeneruj i zapisz preview zmian przed jakimkolwiek write.")
    if "missing_confirmation_audit" in blocker_codes:
        steps.append("Zapisz review człowieka i jawne potwierdzenie operatora.")
    if "missing_impact_check" in blocker_codes:
        steps.append("Zapisz impact/readiness sanity check dla planowanej zmiany.")
    if "missing_mutation_adapter" in blocker_codes:
        steps.append("Dopiero potem dodaj adapter wykonania z redacted result i audit.")
    if "missing_wordpress_draft_handoff_ready" in blocker_codes:
        steps.append("Przygotuj zatwierdzony WordPress handoff dla wybranego work itemu.")
    if "missing_wordpress_draft_package_ready" in blocker_codes:
        steps.append(
            "Podepnij zatwierdzoną paczkę szkicu przed próbą podglądu wykonania."
        )
    if "missing_wordpress_draft_target_content_ready" in blocker_codes:
        steps.append(
            "Doprowadź konkretny target przez Claim Ledger, gotowość szkicu i "
            "human review zanim będzie można tworzyć draft."
        )
    if item.vendor_write_possible:
        steps.append("Przed live write wykonaj apply wyłącznie przez ActionObject i audit.")
    return steps


def _activation_next_step(
    item: ActionMutationReadinessResponse | None,
) -> str:
    if item is None:
        return "Brak propozycji zapisu; najpierw wybierz niskiego ryzyka klasę draft-only."
    if item.action_id == "act_apply_wordpress_draft_handoff":
        if item.mutation_adapter is not None:
            blocker_codes = {blocker.code for blocker in item.blockers}
            if "missing_wordpress_draft_package_ready" not in blocker_codes:
                return (
                    "Najbliższy krok: zapisz human review i audit dla gotowej "
                    "paczki szkicu WordPress draft-only, potem przejdź preview/"
                    "confirm/audit ActionObject. Adapter boundary już istnieje; "
                    "live env/write zostaje wyłączony do jawnej decyzji."
                )
            return (
                "Najbliższy krok: przygotuj zatwierdzony handoff i paczkę szkicu "
                "dla WordPress draft-only, potem przejdź preview/review/confirm/"
                "audit. Adapter boundary już istnieje; live env/write zostaje "
                "wyłączony do jawnej decyzji."
            )
        return (
            "Najbliższy krok: doprowadź apply-mode WordPress draft-only do "
            "pełnego preview/review/confirm/audit i dodaj adapter boundary, ale "
            "env live write zostaje wyłączony do jawnej decyzji."
        )
    if item.action_id == "act_prepare_wordpress_draft_handoff":
        return (
            "Najbliższy krok: przygotuj osobny apply-capable ActionObject dla "
            "WordPress draft-only, ale zostaw env write wyłączony i publikację "
            "zablokowaną do czasu pełnego preview/review/confirm/audit."
        )
    return (
        "Najbliższy krok: doprecyzuj kontrakt apply dla tej akcji i utrzymaj "
        "write zablokowany do czasu pełnego readiness."
    )


def _mutation_apply_contract(
    action: ActionObject,
    mutation_adapter: str | None,
) -> ActionMutationApplyContract | None:
    if action.id not in {
        "act_apply_wordpress_draft_handoff",
        "act_prepare_wordpress_draft_handoff",
    }:
        return None
    action_type = action.payload.get("action_type")
    required_input_contracts = [
        value
        for value in action.payload.get("required_input_contracts", [])
        if isinstance(value, str)
    ]
    return ActionMutationApplyContract(
        action_id=action.id,
        action_type=action_type if isinstance(action_type, str) else "wordpress_draft_handoff",
        connector=action.connector,
        allowed_operation="create_wordpress_draft",
        draft_only=True,
        publication_allowed=False,
        destructive_allowed=False,
        adapter_status="implemented" if mutation_adapter is not None else "not_implemented",
        required_env_flags=["WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES"],
        required_input_contracts=required_input_contracts,
        required_audit_events=[
            "action_preview_generated",
            "human_review_*",
            "action_apply_confirmed",
        ],
        blocked_outputs=[
            "wordpress_publish",
            "wordpress_update_existing_post",
            "wordpress_delete_post",
            "production_publish_ready_claim",
        ],
        operator_summary=(
            "Ten kontrakt może w przyszłości zapisać wyłącznie szkic WordPress. "
            "Nie wolno publikować, aktualizować istniejącego wpisu ani omijać "
            "preview, review, confirm i audytu ActionObject."
        ),
    )


def _vendor_write_possible(action: ActionObject, mutation_adapter: str | None) -> bool:
    return (
        mutation_adapter is not None
        and action.mode == ActionMode.apply
        and _action_payload_apply_allowed(action.payload)
        and _action_payload_api_mutation_ready(action.payload)
    )


def _wordpress_draft_write_readiness_requirements(
    action: ActionObject,
    *,
    wordpress_draft_readiness: ContentWordPressDraftWriteReadinessResponse | None = None,
) -> list[ActionMutationReadinessRequirement]:
    if action.id != "act_apply_wordpress_draft_handoff":
        return []
    readiness = wordpress_draft_readiness or build_content_wordpress_draft_write_readiness_response(
        action_id=action.id
    )
    authorization_ready = readiness.suggested_write_authorization is not None
    blocker_codes = ", ".join(blocker.code for blocker in readiness.blockers[:4]) or None
    return [
        _mutation_requirement(
            code="wordpress_draft_write_readiness",
            label="WordPress draft write readiness przechodzi",
            satisfied=readiness.ready,
            evidence=blocker_codes or "ready",
        ),
        _mutation_requirement(
            code="wordpress_draft_live_write_env",
            label="Env pozwala na zapis szkicu WordPress",
            satisfied=readiness.live_write_enabled_by_env,
            evidence=str(readiness.live_write_enabled_by_env).lower(),
        ),
        _mutation_requirement(
            code="wordpress_rest_adapter_configured",
            label="REST adapter WordPress jest skonfigurowany",
            satisfied=readiness.rest_adapter_configured,
            evidence=str(readiness.rest_adapter_configured).lower(),
        ),
        _mutation_requirement(
            code="wordpress_write_authorization",
            label="Autoryzacja write z audytu jest gotowa",
            satisfied=authorization_ready,
            evidence="ready" if authorization_ready else "missing",
        ),
    ]


def _wordpress_draft_write_readiness(
    action: ActionObject,
) -> ContentWordPressDraftWriteReadinessResponse | None:
    if action.id != "act_apply_wordpress_draft_handoff":
        return None
    return build_content_wordpress_draft_write_readiness_response(action_id=action.id)


def _wordpress_draft_activation_packet(
    action: ActionObject,
) -> ContentWordPressDraftActivationPacketResponse | None:
    if action.id != "act_apply_wordpress_draft_handoff":
        return None
    from wilq.briefing.content_diagnostics import build_content_diagnostics

    diagnostics = build_content_diagnostics(actions=[])
    snapshot = build_content_work_item_diagnostics_snapshot_response(diagnostics)
    return build_content_wordpress_draft_activation_packet_response(
        snapshot,
        action_id=action.id,
    )


def _wordpress_draft_execution_readiness_requirements(
    action: ActionObject,
    *,
    activation_packet: ContentWordPressDraftActivationPacketResponse | None = None,
) -> list[ActionMutationReadinessRequirement]:
    if action.id != "act_apply_wordpress_draft_handoff":
        return []
    if activation_packet is not None:
        blocker_evidence = (
            ", ".join(
                [
                    *activation_packet.handoff_blockers,
                    *activation_packet.execution_blockers,
                ]
            )
            or "ready"
        )
        return [
            _mutation_requirement(
                code="wordpress_draft_handoff_ready",
                label="Zatwierdzone przekazanie do WordPress istnieje",
                satisfied=activation_packet.handoff_ready,
                evidence=blocker_evidence,
            ),
            _mutation_requirement(
                code="wordpress_draft_package_ready",
                label="Paczka szkicu WordPress istnieje",
                satisfied=activation_packet.draft_package_ready,
                evidence=activation_packet.draft_package_id or blocker_evidence,
            ),
        ]
    execution = execute_content_wordpress_draft_handoff(
        handoff=None,
        draft_package=None,
        mode="dry_run",
        live_write_enabled=False,
        create_draft=None,
    )
    blocker_codes = {blocker.code for blocker in execution.blockers}
    execution_blocker_evidence: str | None = (
        ", ".join(blocker.code for blocker in execution.blockers) or None
    )
    return [
        _mutation_requirement(
            code="wordpress_draft_handoff_ready",
            label="Zatwierdzone przekazanie do WordPress istnieje",
            satisfied="missing_handoff" not in blocker_codes,
            evidence=execution_blocker_evidence or "ready",
        ),
        _mutation_requirement(
            code="wordpress_draft_package_ready",
            label="Paczka szkicu WordPress istnieje",
            satisfied="missing_draft_package" not in blocker_codes,
            evidence=execution_blocker_evidence or "ready",
        ),
    ]


def _wordpress_draft_target_content_readiness_requirements(
    action: ActionObject,
    *,
    activation_packet: ContentWordPressDraftActivationPacketResponse | None = None,
) -> list[ActionMutationReadinessRequirement]:
    if action.id != "act_apply_wordpress_draft_handoff":
        return []
    if activation_packet is not None:
        evidence_parts = [
            f"draft_package_ready={str(activation_packet.draft_package_ready).lower()}",
            f"human_review_ready={str(activation_packet.human_review_ready).lower()}",
            f"audit_ready={str(activation_packet.audit_ready).lower()}",
            f"dry_run_ready={str(activation_packet.dry_run_ready).lower()}",
        ]
        return [
            _mutation_requirement(
                code="wordpress_draft_target_content_ready",
                label="Target treści przeszedł Claim Ledger i review szkicu",
                satisfied=activation_packet.dry_run_ready,
                evidence="; ".join(evidence_parts),
            )
        ]
    preview_items = _payload_preview_items(action.payload)
    if not preview_items:
        return [
            _mutation_requirement(
                code="wordpress_draft_target_content_ready",
                label="Target treści przeszedł Claim Ledger i review szkicu",
                satisfied=False,
                evidence="missing_payload_preview",
            )
        ]
    first = preview_items[0]
    apply_allowed = first.get("apply_allowed") is True
    api_mutation_ready = first.get("api_mutation_ready") is True
    required_validation = [
        value for value in first.get("required_validation", []) if isinstance(value, str)
    ]
    validation_evidence = ", ".join(required_validation[:4])
    if len(required_validation) > 4:
        validation_evidence = f"{validation_evidence}, +{len(required_validation) - 4}"
    evidence_parts = [
        f"apply_allowed={str(apply_allowed).lower()}",
        f"api_mutation_ready={str(api_mutation_ready).lower()}",
    ]
    if validation_evidence:
        evidence_parts.append(f"required_validation={validation_evidence}")
    return [
        _mutation_requirement(
            code="wordpress_draft_target_content_ready",
            label="Target treści przeszedł Claim Ledger i review szkicu",
            satisfied=apply_allowed and api_mutation_ready,
            evidence="; ".join(evidence_parts),
        )
    ]


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
    adapter_result: dict[str, Any] | None,
) -> ActionMutationAuditRecord:
    status: Literal["blocked", "applied"] = "blocked" if errors else "applied"
    action_type = action.payload.get("action_type")
    adapter_reached = adapter_result is not None
    external_write_attempted = (
        adapter_result.get("external_write_attempted") is True
        if adapter_result is not None
        else False
    )
    return ActionMutationAuditRecord(
        id=f"mutation_{action.id}_{uuid4().hex[:12]}",
        action_id=action.id,
        connector=action.connector,
        action_type=action_type if isinstance(action_type, str) else None,
        status=status,
        status_label=_action_mutation_audit_status_label(status),
        adapter_reached=adapter_reached,
        external_write_attempted=external_write_attempted,
        mutation_attempted=external_write_attempted,
        mutation_adapter=mutation_adapter,
        actor=actor,
        audit_event_id=audit_event.id,
        evidence_ids=action.evidence_ids,
        blockers=errors,
        summary=_mutation_audit_summary(
            errors,
            mutation_adapter,
            adapter_reached=adapter_reached,
            external_write_attempted=external_write_attempted,
        ),
    )


def _mutation_audit_summary(
    errors: list[str],
    mutation_adapter: str | None,
    *,
    adapter_reached: bool,
    external_write_attempted: bool,
) -> str:
    if errors:
        if adapter_reached:
            attempted = (
                "External vendor write was attempted."
                if external_write_attempted
                else "No external vendor write was attempted."
            )
            return (
                "Mutation adapter reached but did not complete successfully. "
                f"{attempted} Blockers: {', '.join(errors)}"
            )
        return f"Mutation blocked before any vendor API call. Blockers: {', '.join(errors)}"
    adapter = mutation_adapter or "unknown"
    if not external_write_attempted:
        return (
            f"Mutation completed through adapter {adapter}, but no external vendor "
            "write was attempted; vendor payload remains redacted."
        )
    return f"Mutation executed through adapter {adapter}; vendor payload remains redacted."


def _supported_mutation_adapter(action: ActionObject) -> str | None:
    if (
        action.id == "act_apply_wordpress_draft_handoff"
        and action.connector == "wordpress_ekologus"
        and action.payload.get("allowed_operation") == "create_wordpress_draft"
    ):
        return "wordpress_draft_execution_boundary"
    return None


def _execute_supported_mutation_adapter(
    action: ActionObject,
    mutation_adapter: str,
    request: ActionApplyRequest | None,
    wordpress_capability: WordPressDraftApplyCapability | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    _ = request
    if mutation_adapter == "wordpress_draft_execution_boundary":
        if wordpress_capability is not None:
            execution = execute_content_wordpress_draft_handoff(
                handoff=wordpress_capability.handoff,
                draft_package=wordpress_capability.draft_package,
                mode="live",
                live_write_enabled=_wordpress_draft_writes_enabled(),
                create_draft=create_wordpress_draft_post,
                action_apply_authorized=True,
                write_authorization=wordpress_capability.write_authorization,
                write_authorization_verified=True,
            )
            return {
                "adapter": mutation_adapter,
                "connector": action.connector,
                "allowed_operation": "create_wordpress_draft",
                "execution_status": execution.status,
                "execution_mode": execution.mode,
                "external_write_attempted": execution.external_write_attempted,
                "execution_result": execution.model_dump(mode="json"),
                "redacted": True,
            }, _wordpress_draft_execution_errors(execution)
        execution = execute_content_wordpress_draft_handoff(
            handoff=None,
            draft_package=None,
            mode="dry_run",
            live_write_enabled=False,
            create_draft=None,
        )
        return {
            "adapter": mutation_adapter,
            "connector": action.connector,
            "allowed_operation": "create_wordpress_draft",
            "execution_status": execution.status,
            "execution_mode": execution.mode,
            "external_write_attempted": execution.external_write_attempted,
            "execution_result": execution.model_dump(mode="json"),
            "redacted": True,
        }, _wordpress_draft_execution_errors(execution)
    return None, [f"Adapter zapisu {mutation_adapter} nie ma implementacji wykonania."]


def _wordpress_draft_writes_enabled() -> bool:
    return (variable_value("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _wordpress_draft_execution_errors(execution: Any) -> list[str]:
    if execution.status in {"dry_run_ready", "created"}:
        return []
    blockers = [
        f"{blocker.label}: {blocker.reason}"
        for blocker in execution.blockers
    ]
    if blockers:
        return blockers
    return ["WordPress draft execution contract blocked the adapter."]


def _mutation_requirement(
    *,
    code: str,
    label: str,
    satisfied: bool,
    evidence: str | None = None,
) -> ActionMutationReadinessRequirement:
    return ActionMutationReadinessRequirement(
        code=code,
        label=label,
        satisfied=satisfied,
        evidence=evidence,
    )


def _mutation_readiness_blockers(
    requirements: list[ActionMutationReadinessRequirement],
) -> list[ActionMutationReadinessBlocker]:
    blocker_copy = {
        "valid_action": (
            "Akcja nie jest jeszcze poprawnie sprawdzona",
            "Przed zapisem trzeba uruchomić walidację ActionObject i usunąć błędy.",
            "Uruchom validate dla tej akcji i wróć do readiness.",
        ),
        "apply_mode": (
            "Akcja jest tylko prepare/review",
            "Ta akcja nie ma kontraktu zapisu do zewnętrznego systemu.",
            "Użyj jej do review albo dodaj osobny apply-capable ActionObject.",
        ),
        "payload_apply_allowed": (
            "Payload nadal blokuje apply",
            "Zakres akcji nie pozwala jeszcze na próbę zapisu.",
            "Najpierw przygotuj bezpieczny payload apply po preview, review i confirm.",
        ),
        "evidence_present": (
            "Brakuje dowodów źródłowych",
            "WILQ nie zapisuje zmian bez identyfikatorów dowodów.",
            "Podepnij dowody źródłowe do akcji przed rozważeniem zapisu.",
        ),
        "connector_configured": (
            "Connector nie jest skonfigurowany",
            "Nie ma bezpiecznej ścieżki do vendor API bez działającego connectora.",
            "Napraw credentials/status connectora i odśwież readiness.",
        ),
        "preview_audit": (
            "Brakuje podglądu zmian",
            "Operator musi zobaczyć preview zanim WILQ dopuści zapis.",
            "Uruchom preview dla tej akcji.",
        ),
        "confirmation_audit": (
            "Brakuje potwierdzenia operatora",
            "WILQ wymaga jawnego confirm przed zapisem.",
            "Zapisz confirm po review i preview.",
        ),
        "impact_check": (
            "Brakuje sprawdzenia efektu",
            "Przed zapisem WILQ wymaga sanity checku wpływu/okna efektu.",
            "Uruchom impact-check lub dodaj odpowiedni kontrakt wpływu.",
        ),
        "risk_allowed": (
            "Ryzyko zapisu jest zbyt wysokie",
            "High/critical writes nie mają jeszcze obsługiwanej ścieżki bezpieczeństwa.",
            "Rozbij akcję na niższe ryzyko albo dodaj osobny model akceptacji.",
        ),
        "non_destructive": (
            "Akcja jest destrukcyjna",
            "Destrukcyjne zmiany są zablokowane do czasu osobnego kontraktu.",
            "Przygotuj niedestrukcyjną alternatywę albo nowy guard dla tej klasy zmian.",
        ),
        "mutation_adapter": (
            "Brakuje adaptera zapisu",
            "WILQ nie ma jeszcze implementacji vendor write dla tej akcji.",
            "Najpierw dodaj read-only preview i bezpieczny adapter podglądu/live dla connectora.",
        ),
        "wordpress_draft_write_readiness": (
            "WordPress draft write readiness blokuje zapis",
            "Osobny kontrakt WordPress draft write readiness nie pozwala jeszcze na live write.",
            "Sprawdź env, REST adapter i audyty w readiness szkicu WordPress.",
        ),
        "wordpress_draft_handoff_ready": (
            "Brakuje zatwierdzonego przekazania do WordPress",
            (
                "Adapter draft-only nie ma jeszcze zatwierdzonego handoffu, "
                "który wolno zamienić na szkic."
            ),
            "Doprowadź wybrany work item przez draft package, human review i WordPress handoff.",
        ),
        "wordpress_draft_package_ready": (
            "Brakuje paczki szkicu WordPress",
            (
                "Adapter nie może tworzyć wpisu z samego ActionObject; "
                "potrzebuje zatwierdzonej paczki treści."
            ),
            (
                "Przygotuj draft package z claim ledgerem, sekcjami i dowodami, "
                "potem wróć do handoffu."
            ),
        ),
        "wordpress_draft_target_content_ready": (
            "Target treści nie przeszedł jeszcze gotowości szkicu",
            (
                "Wybrany URL ma tylko zablokowany podgląd handoffu. Przed draft-only "
                "write musi przejść Claim Ledger, kontrolę wiedzy/twierdzeń, gotowość "
                "szkicu i review człowieka."
            ),
            (
                "Doprowadź ten content item przez Claim Ledger, draft package i "
                "human review; dopiero potem wróć do WordPress handoffu."
            ),
        ),
        "wordpress_draft_live_write_env": (
            "Env nie pozwala na zapis szkicu WordPress",
            "WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES nie jest jawnie włączone.",
            "Zostaw write wyłączony albo włącz env dopiero po pełnym preview/review/confirm.",
        ),
        "wordpress_rest_adapter_configured": (
            "REST adapter WordPress nie jest gotowy",
            "Connector WordPress nie ma pełnej konfiguracji REST do utworzenia szkicu.",
            "Uzupełnij konfigurację WordPress REST i sprawdź authoring profile.",
        ),
        "wordpress_write_authorization": (
            "Brakuje autoryzacji write z audytu",
            "WILQ nie zbudował jeszcze write_authorization z preview, review i confirm.",
            "Przejdź validate, preview, human review i confirm w ActionObject.",
        ),
    }
    blockers: list[ActionMutationReadinessBlocker] = []
    for requirement in requirements:
        if requirement.satisfied:
            continue
        label, reason, next_step = blocker_copy.get(
            requirement.code,
            (
                f"Niespełniony warunek: {requirement.label}",
                "Ten warunek blokuje bezpieczny zapis zmian.",
                "Uzupełnij warunek i sprawdź readiness ponownie.",
            ),
        )
        blockers.append(
            ActionMutationReadinessBlocker(
                code=f"missing_{requirement.code}",
                label=label,
                reason=reason,
                next_step=next_step,
            )
        )
    return blockers


def _mutation_readiness_next_step(
    action: ActionObject,
    blockers: list[ActionMutationReadinessBlocker],
) -> str:
    if not blockers:
        return (
            "Warunki zapisu są spełnione; apply nadal wymaga osobnego POST z "
            "jawnym potwierdzeniem operatora."
        )
    if action.id == "act_apply_wordpress_draft_handoff":
        blocker_codes = {blocker.code for blocker in blockers}
        if {
            "missing_wordpress_draft_handoff_ready",
            "missing_wordpress_draft_package_ready",
        } & blocker_codes:
            return (
                "Najpierw przygotuj zatwierdzony WordPress handoff i paczkę "
                "szkicu dla wybranego content itemu; adapter boundary już "
                "istnieje, ale live write zostaje wyłączony."
            )
        if {
            "missing_preview_audit",
            "missing_confirmation_audit",
            "missing_wordpress_write_authorization",
        } & blocker_codes:
            return (
                "Przejdź preview, human review i confirm w ActionObject, żeby "
                "WILQ mógł zbudować write_authorization; live write nadal stop."
            )
    return blockers[0].next_step


def _mutation_readiness_summary_next_step(
    items: list[ActionMutationReadinessResponse],
    blocker_counts: dict[str, int],
    first_write_candidate: ActionMutationReadinessResponse | None,
) -> str:
    if not items:
        return "Brakuje ActionObjectów do oceny gotowości zapisu."
    if any(item.would_attempt_vendor_write for item in items):
        return (
            "Co najmniej jedna akcja spełnia warunki zapisu; przed apply nadal "
            "wymagane jest jawne potwierdzenie operatora."
        )
    if first_write_candidate is not None and first_write_candidate.action_id == (
        "act_apply_wordpress_draft_handoff"
    ):
        first_blockers = {blocker.code for blocker in first_write_candidate.blockers}
        if {
            "missing_wordpress_draft_handoff_ready",
            "missing_wordpress_draft_package_ready",
        } & first_blockers:
            target = (
                f" dla: {first_write_candidate.target_label}"
                if first_write_candidate.target_label
                else ""
            )
            if "missing_wordpress_draft_package_ready" not in first_blockers:
                return (
                    "Pierwsza propozycja zapisu ma adapter boundary i paczkę szkicu, "
                    f"ale brakuje zatwierdzonego handoffu{target}. Najpierw zapisz "
                    "human review i audit przekazania do WordPress; live write nadal "
                    "zostaje wyłączony."
                )
            return (
                "Pierwsza propozycja zapisu ma adapter boundary, ale brakuje "
                f"zatwierdzonego handoffu i paczki szkicu{target}. Najpierw przejdź "
                "wybrany content item przez draft package, human review i "
                "WordPress handoff; live write nadal zostaje wyłączony."
            )
    if blocker_counts.get("missing_mutation_adapter"):
        return (
            "Najpierw wybierz jedną klasę zapisu i dodaj bezpieczny adapter "
            "podglądu/live; obecnie żaden vendor write nie powinien zostać wykonany."
        )
    if blocker_counts.get("missing_apply_mode"):
        return "Najpierw dodaj apply-capable ActionObject dla wybranej klasy zmian."
    return "Usuń pokazane blokery readiness przed próbą realnego zapisu."


def _with_persisted_review_gates(actions: Iterable[ActionObject]) -> list[ActionObject]:
    action_list = list(actions)
    action_ids = {action.id for action in action_list}
    audit_events_by_action_id = _persisted_audit_events_by_action_id(action_ids)
    mutation_audits_by_action_id = _persisted_mutation_audits_by_action_id(action_ids)
    return [
        _with_review_gate(
            _with_persisted_validation_state(action),
            audit_events_by_action_id.get(action.id, []),
            mutation_audits_by_action_id.get(action.id, []),
        )
        for action in action_list
    ]


def _with_persisted_validation_state(action: ActionObject) -> ActionObject:
    state = local_state_store().get_action_validation_state(action.id)
    if state is None:
        return action
    validation_status = state.get("validation_status")
    status = state.get("status")
    if validation_status in {"valid", "invalid", "not_validated"}:
        action.validation_status = validation_status
    if isinstance(status, str):
        with suppress(ValueError):
            action.status = ActionStatus(status)
    return action


def _with_review_gate(
    action: ActionObject,
    audit_events: list[AuditEvent] | None = None,
    mutation_audits: list[ActionMutationAuditRecord] | None = None,
) -> ActionObject:
    if audit_events is not None:
        action.audit_events = audit_events[:10]
    state_audit_events = [
        event for event in action.audit_events if not _audit_event_has_raw_contract_text(event)
    ]
    action.payload = content_payload_with_reviewed_wordpress_draft_previews(
        action.payload,
        review_event_summaries=(
            event.summary
            for event in state_audit_events
            if event.event_type == "human_review_approved_for_prepare"
        ),
        review_event_details=(
            event.details
            for event in state_audit_events
            if event.event_type == "human_review_approved_for_prepare"
        ),
    )
    action.payload = _payload_with_operator_labels(action.payload)
    review_gate_events = [
        event
        for event in action.audit_events
        if not _is_raw_content_review_audit_event(action.id, event)
    ]
    action.review_gate = _action_review_gate(
        action.model_copy(update={"audit_events": review_gate_events}),
        mutation_audits,
    )
    return _action_with_operator_labels(action)


def _is_raw_content_review_audit_event(action_id: str, event: AuditEvent) -> bool:
    if action_id != "act_prepare_content_refresh_queue":
        return False
    if not event.event_type.startswith("human_review_"):
        return False
    return _audit_event_has_raw_contract_text(event)


def _action_with_operator_labels(action: ActionObject) -> ActionObject:
    connector = get_connector_status(action.connector)
    return action.model_copy(
        update={
            "connector_label": connector.label if connector is not None else "źródło danych",
            "mode_label": _action_mode_label(action.mode),
            "risk_label": _action_risk_label(action.risk),
            "status_label": _action_status_label(action.status),
            "evidence_summary_label": _action_evidence_summary_label(action.evidence_ids),
            "validation_status_label": _action_validation_status_label(action.validation_status),
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
    if action.payload.get("preview_contract") == "change_history_impact_review_v1":
        return _ads_change_history_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "demand_gen_readiness_review_preview_v1":
        return _demand_gen_readiness_preview_cards(action.payload)
    if action.payload.get("preview_contract") == SEARCH_TERM_NGRAM_PREVIEW_CONTRACT:
        return _search_term_ngram_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "ga4_tracking_quality_review_v1":
        return _ga4_tracking_quality_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "local_visibility_review_preview_v1":
        return _local_visibility_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "content_brief_preview_v1":
        return _content_refresh_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "wordpress_draft_handoff_preview_v1":
        return _wordpress_draft_handoff_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "wordpress_draft_apply_preview_v1":
        return _wordpress_draft_handoff_preview_cards(action.payload)
    if (
        action.payload.get("preview_contract")
        == "service_profile_knowledge_promotion_preview_v1"
    ):
        return _service_profile_knowledge_promotion_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "private_source_proposal_promotion_preview_v1":
        return _service_profile_private_proposal_promotion_preview_cards(action.payload)
    if action.payload.get("action_type") == KEYWORD_PLANNER_ACCESS_ACTION_TYPE:
        return _keyword_planner_access_preview_cards(action.payload)
    if action.payload.get("action_type") == "confirm_ads_target_guardrails":
        return _ads_target_guardrail_preview_cards(action.payload)
    if action.payload.get("action_type") == "record_ads_strategy_review":
        return _ads_strategy_review_preview_cards(action.payload)
    if action.payload.get("action_type") in {
        "linkedin_post_candidate",
        "facebook_post_candidate",
    }:
        return _social_draft_input_preview_cards(action.payload)
    return action.preview_cards


def _action_preview_item_view_models(
    *,
    action: ActionObject,
    raw_items: list[dict[str, Any]],
    preview_cards: list[ActionPreviewCardViewModel],
    max_items: int,
) -> list[ActionPreviewItemViewModel]:
    if preview_cards:
        return [
            _preview_item_from_card(
                card=card,
                raw_item=raw_items[index] if index < len(raw_items) else None,
                index=index,
            )
            for index, card in enumerate(preview_cards[:max_items])
        ]
    return [
        _preview_item_from_raw_payload(action, item, index)
        for index, item in enumerate(raw_items[:max_items])
    ]


def _preview_item_from_card(
    *,
    card: ActionPreviewCardViewModel,
    raw_item: dict[str, Any] | None,
    index: int,
) -> ActionPreviewItemViewModel:
    rows = list(card.rows[:4])
    if card.apply_state_label:
        rows.append(_preview_row("Zapis zmian", card.apply_state_label))
    if card.system_readiness_label:
        rows.append(_preview_row("Gotowość systemu", card.system_readiness_label))
    return ActionPreviewItemViewModel(
        id=f"preview_item_{index + 1}",
        preview_contract=_preview_item_contract(raw_item),
        candidate_id=_preview_item_candidate_id(raw_item),
        title_label=card.title_label or f"Pozycja podglądu {index + 1}",
        status_label=card.status_label,
        rows=rows,
    )


def _preview_item_from_raw_payload(
    action: ActionObject,
    item: dict[str, Any],
    index: int,
) -> ActionPreviewItemViewModel:
    rows = _safe_raw_preview_rows(item)
    if not rows:
        rows = [
            _preview_row(
                "Zakres", _preview_contract_label(_preview_contract(action.payload, [item]))
            ),
        ]
    return ActionPreviewItemViewModel(
        id=f"preview_item_{index + 1}",
        preview_contract=_preview_item_contract(item),
        candidate_id=_preview_item_candidate_id(item),
        title_label=_raw_preview_title(item, index),
        status_label=_raw_preview_status(item),
        rows=rows[:6],
    )


def _preview_item_contract(item: dict[str, Any] | None) -> str | None:
    if not item:
        return None
    value = item.get("preview_contract")
    if isinstance(value, str) and value == "wordpress_draft_payload_preview_v1":
        return value
    return None


def _preview_item_candidate_id(item: dict[str, Any] | None) -> str | None:
    if not item:
        return None
    if item.get("preview_contract") != "wordpress_draft_payload_preview_v1":
        return None
    value = item.get("candidate_id")
    return value if isinstance(value, str) and value else None


def _safe_raw_preview_rows(item: dict[str, Any]) -> list[ActionPreviewRowViewModel]:
    rows: list[ActionPreviewRowViewModel] = []
    for label, value in _raw_preview_label_values(item):
        rows.append(_preview_row(label, value))
        if len(rows) >= 4:
            break
    if "apply_allowed" in item:
        rows.append(_preview_row("Zapis zmian", _apply_state_label(item.get("apply_allowed"))))
    if "api_mutation_ready" in item:
        rows.append(
            _preview_row(
                "Gotowość systemu", _system_readiness_label(item.get("api_mutation_ready"))
            )
        )
    return rows


def _raw_preview_label_values(item: dict[str, Any]) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for key, value in item.items():
        if not key.endswith("_label"):
            continue
        if key in {"id_label", "preview_contract_label"}:
            continue
        label = _raw_preview_row_label(key)
        if isinstance(value, str) and value:
            values.append((label, value))
        elif isinstance(value, list):
            values.extend((label, entry) for entry in value if isinstance(entry, str) and entry)
    return values


def _raw_preview_row_label(key: str) -> str:
    labels = {
        "affected_attribute_label": "Atrybut",
        "issue_type_label": "Problem",
        "mode_label": "Tryb",
        "operation_type_label": "Operacja",
        "readiness_label": "Gotowość",
        "recommendation_type_label": "Rekomendacja",
        "reason_label": "Powód",
        "risk_label": "Ryzyko",
        "status_label": "Status",
        "validation_status_label": "Walidacja",
    }
    return labels.get(key, "Szczegół")


def _raw_preview_title(item: dict[str, Any], index: int) -> str:
    for key in (
        "title_label",
        "issue_type_label",
        "recommendation_type_label",
        "operation_type_label",
        "mode_label",
    ):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return f"Pozycja podglądu {index + 1}"


def _raw_preview_status(item: dict[str, Any]) -> str:
    for key in ("status_label", "validation_status_label", "readiness_label"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _preview_contract_label(value: str | None) -> str:
    labels = {
        MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT: "przegląd problemów Merchant",
        "content_brief_preview_v1": "brief treści do sprawdzenia",
        "wordpress_draft_payload_preview_v1": "szkic WordPress do sprawdzenia",
        "local_visibility_review_preview_v1": "widoczność lokalna do sprawdzenia",
        "ga4_tracking_quality_review_v1": "jakość pomiaru GA4 do sprawdzenia",
    }
    return labels.get(value or "", "podgląd zmian do sprawdzenia")


def _content_refresh_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    content_items = [
        item for item in payload.get("content_brief_preview", []) if isinstance(item, dict)
    ]
    draft_items = [
        item
        for item in payload.get("wordpress_draft_payload_preview", [])
        if isinstance(item, dict)
    ]
    cards = [
        _content_brief_preview_card(item, index) for index, item in enumerate(content_items[:3])
    ]
    cards.extend(
        _wordpress_draft_payload_preview_card(item, index)
        for index, item in enumerate(draft_items[:1])
    )
    return cards


def _content_brief_preview_card(
    item: dict[str, Any],
    index: int,
) -> ActionPreviewCardViewModel:
    rows = [
        _preview_row("Temat", str(item.get("topic") or "treść do sprawdzenia")),
        _preview_row("Tryb", str(item.get("mode_label") or "wymaga sprawdzenia")),
        _preview_row(
            "URL publiczny",
            _content_primary_url_label(item),
        ),
    ]
    decision_options = _string_list(item.get("decision_option_labels"))
    if decision_options:
        rows.append(_preview_row("Opcje", ", ".join(decision_options[:4])))
    brief_goal = item.get("brief_goal")
    if isinstance(brief_goal, str) and brief_goal:
        rows.append(_preview_row("Cel planu treści", brief_goal))
    content_angle = item.get("content_angle")
    if isinstance(content_angle, str) and content_angle:
        rows.append(_preview_row("Kąt treści", content_angle))
    h1_direction = item.get("h1_direction")
    if isinstance(h1_direction, str) and h1_direction:
        rows.append(_preview_row("H1", h1_direction))
    cta_direction = item.get("cta_direction")
    if isinstance(cta_direction, str) and cta_direction:
        rows.append(_preview_row("CTA", cta_direction))
    metric_summary = _content_metric_snapshot_label(item.get("metric_snapshot"))
    if metric_summary:
        rows.append(_preview_row("Metryki", metric_summary))
    missing_evidence = _string_list(item.get("missing_evidence"))
    if missing_evidence:
        rows.append(_preview_row("Brakujące dowody", ", ".join(missing_evidence[:3])))
    publication_blockers = _string_list(item.get("publication_blocker_labels"))
    if publication_blockers:
        rows.append(_preview_row("Blokady publikacji", ", ".join(publication_blockers[:4])))
    validation_labels = _string_list(item.get("required_validation_labels"))
    if validation_labels:
        rows.append(_preview_row("Warunki sprawdzenia", ", ".join(validation_labels[:4])))
    return ActionPreviewCardViewModel(
        id=f"content_brief_preview_{index}",
        kind="content_brief_review",
        title_label="Plan treści do sprawdzenia",
        subtitle_label="brief bez pisania i bez publikacji",
        status_label="zapis zmian zablokowany",
        rows=rows,
        apply_state_label=_apply_state_label(item.get("apply_allowed")),
        system_readiness_label=_system_readiness_label(item.get("api_mutation_ready")),
    )


def _wordpress_draft_payload_preview_card(
    item: dict[str, Any],
    index: int,
) -> ActionPreviewCardViewModel:
    draft_payload_value = item.get("draft_payload")
    draft_payload = draft_payload_value if isinstance(draft_payload_value, dict) else {}
    rows = [
        _preview_row("Temat", str(item.get("topic") or "treść do sprawdzenia")),
        _preview_row("Status wpisu", str(item.get("post_status_label") or "szkic")),
        _preview_row(
            "Tytuł szkicu",
            str(draft_payload.get("post_title") or "tytuł do sprawdzenia"),
        ),
        _preview_row("URL publiczny", _content_primary_url_label(item)),
    ]
    for label, key in (
        ("Kontrole treści", "content_gate_status_summary"),
        ("Co blokuje szkic", "draft_blocker_labels"),
        ("Warunki szkicu", "draft_generation_summary"),
        ("Gotowość po sprawdzeniu", "draft_readiness_review_summary"),
        ("Szkic WordPress", "wordpress_draft_handoff_summary"),
        ("Pomiar po publikacji", "post_publication_measurement_summary"),
        ("Warunki sprawdzenia", "required_validation_labels"),
    ):
        values = _string_list(item.get(key))
        if values:
            rows.append(_preview_row(label, ", ".join(values[:3])))
    blocked_claims = _string_list(item.get("blocked_claim_labels"))
    if blocked_claims:
        rows.append(_preview_row("Czego nie wolno twierdzić", ", ".join(blocked_claims[:4])))
    return ActionPreviewCardViewModel(
        id=f"wordpress_draft_payload_preview_{index}",
        kind="wordpress_draft_payload_review",
        title_label="Szkic WordPress do sprawdzenia",
        subtitle_label="szkic bez publikacji",
        status_label="zapis zmian zablokowany",
        rows=rows,
        apply_state_label=_apply_state_label(item.get("apply_allowed")),
        system_readiness_label=_system_readiness_label(item.get("api_mutation_ready")),
    )


def _wordpress_draft_handoff_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    preview_items = [item for item in payload.get("payload_preview", []) if isinstance(item, dict)]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        rows = [
            _preview_row("Temat", str(item.get("topic") or "treść do sprawdzenia")),
            _preview_row(
                "URL publiczny",
                str(
                    item.get("source_public_url")
                    or item.get("final_canonical_url")
                    or "URL publiczny niepotwierdzony"
                ),
            ),
            _preview_row(
                "URL kanoniczny",
                str(item.get("final_canonical_url") or "URL kanoniczny niepotwierdzony"),
            ),
        ]
        preview_url = item.get("preview_url")
        if isinstance(preview_url, str) and preview_url:
            rows.append(_preview_row("Podgląd projektu", preview_url))
        rows.extend(
            [
                _preview_row(
                    "Kontrola URL-a",
                    str(item.get("canonical_gate_status_label") or "wymaga sprawdzenia"),
                ),
                _preview_row(
                    "Duplikaty",
                    str(item.get("duplicate_gate_status_label") or "wymaga sprawdzenia"),
                ),
                _preview_row(
                    "Następny krok",
                    str(item.get("required_next_action_label") or "sprawdzenie szkicu"),
                ),
            ]
        )
        handoff_summary = _string_list(item.get("wordpress_draft_handoff_summary"))
        if handoff_summary:
            rows.append(_preview_row("Szkic WordPress", ", ".join(handoff_summary[:3])))
        measurement_summary = _string_list(item.get("post_publication_measurement_summary"))
        if measurement_summary:
            rows.append(_preview_row("Pomiar po publikacji", ", ".join(measurement_summary[:3])))
        validation_labels = _string_list(item.get("required_validation_labels"))
        if validation_labels:
            rows.append(_preview_row("Warunki sprawdzenia", ", ".join(validation_labels[:4])))
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
                id=f"wordpress_draft_handoff_{index}",
                kind="wordpress_draft_handoff_review",
                title_label="Szkic WordPress do sprawdzenia",
                subtitle_label="podgląd bez zapisu i bez publikacji",
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=_apply_state_label(item.get("apply_allowed")),
                system_readiness_label=_system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def _service_profile_knowledge_promotion_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    preview_items = [item for item in payload.get("payload_preview", []) if isinstance(item, dict)]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:6]):
        source_fact_ids = _string_list(item.get("source_fact_ids"))
        source_connectors = _string_list(item.get("source_connector_labels"))
        required_validation = _string_list(item.get("required_validation_labels"))
        blocked_claims = _string_list(item.get("blocked_claims"))
        rows = [
            _preview_row("Karta", str(item.get("target_card_title") or "karta usługi")),
            _preview_row(
                "Status teraz",
                str(item.get("current_lifecycle_label") or "wymaga review"),
            ),
            _preview_row(
                "Status po decyzji",
                str(item.get("target_lifecycle_label") or "approved-current po review"),
            ),
            _preview_row(
                "Review",
                str(item.get("required_human_role") or "Wilku albo owner wiedzy"),
            ),
        ]
        if source_fact_ids:
            rows.append(_preview_row("Source facts", ", ".join(source_fact_ids[:3])))
        if source_connectors:
            rows.append(_preview_row("Źródła", ", ".join(source_connectors[:3])))
        if required_validation:
            rows.append(_preview_row("Warunki", ", ".join(required_validation[:4])))
        if blocked_claims:
            rows.append(_preview_row("Claimy blokowane", ", ".join(blocked_claims[:3])))
        blocked_reason = item.get("promotion_blocked_reason")
        if isinstance(blocked_reason, str) and blocked_reason:
            rows.append(_preview_row("Blokada", blocked_reason))
        cards.append(
            ActionPreviewCardViewModel(
                id=f"service_profile_knowledge_promotion_{index}",
                kind="service_profile_knowledge_promotion_review",
                title_label="Awans wiedzy Service Profile do sprawdzenia",
                subtitle_label="request po review, bez edycji knowledge base",
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=_apply_state_label(item.get("apply_allowed")),
                system_readiness_label=_system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def _service_profile_private_proposal_promotion_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    preview_items = [item for item in payload.get("payload_preview", []) if isinstance(item, dict)]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:6]):
        required_validation = _string_list(item.get("required_validation_labels"))
        blocked_claims = _string_list(item.get("blocked_claims"))
        rows = [
            _preview_row("Propozycja", str(item.get("target_card_title") or "private proposal")),
            _preview_row("Zakres", str(item.get("scope") or "private source")),
            _preview_row("Ryzyko", str(item.get("risk_tier") or "unknown")),
            _preview_row("Wsparcie", str(item.get("support_level") or "review-required")),
            _preview_row(
                "Aktualność źródła",
                str(item.get("freshness_status") or "do potwierdzenia"),
            ),
            _preview_row(
                "Zakres dostępu",
                str(item.get("audience") or "do potwierdzenia"),
            ),
            _preview_row(
                "Review",
                str(item.get("required_human_role") or "Wilku albo owner wiedzy"),
            ),
            _preview_row("Redakcja", "redacted, bez raw private text"),
        ]
        if required_validation:
            rows.append(_preview_row("Warunki", ", ".join(required_validation[:5])))
        if blocked_claims:
            rows.append(_preview_row("Claimy blokowane", ", ".join(blocked_claims[:4])))
        blocked_reason = item.get("promotion_blocked_reason")
        if isinstance(blocked_reason, str) and blocked_reason:
            rows.append(_preview_row("Blokada", blocked_reason))
        cards.append(
            ActionPreviewCardViewModel(
                id=f"service_profile_private_proposal_promotion_{index}",
                kind="service_profile_private_proposal_promotion_review",
                title_label="Prywatna propozycja Service Profile do sprawdzenia",
                subtitle_label="review redacted źródła, bez promocji i bez zapisu",
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=_apply_state_label(item.get("apply_allowed")),
                system_readiness_label=_system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def _social_draft_input_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    source_inputs = [item for item in payload.get("source_inputs", []) if isinstance(item, dict)]
    connector_label = source_connector_labels([str(payload.get("connector") or "social")])[0]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(source_inputs[:4]):
        rows = [
            _preview_row(
                "Źródło danych",
                _source_connector_labels([str(item.get("source_connector") or "")])[0],
            ),
            _preview_row(
                "Sygnał",
                _metric_fact_label(str(item.get("metric_name") or "")),
            ),
            _preview_row("Wartość", _plain_metric_value_label(item.get("value"))),
            _preview_row(
                "Kontekst",
                str(item.get("context_summary") or "sygnał źródłowy WILQ"),
            ),
        ]
        draft_constraint_labels = _string_list(payload.get("draft_constraint_labels"))
        if draft_constraint_labels:
            rows.append(_preview_row("Ograniczenia", ", ".join(draft_constraint_labels[:4])))
        blocked_claim_labels = _string_list(payload.get("blocked_claim_labels"))
        if not blocked_claim_labels:
            blocked_claim_labels = _string_list(payload.get("blocked_claims"))
        if blocked_claim_labels:
            rows.append(
                _preview_row(
                    "Czego nie wolno twierdzić",
                    ", ".join(blocked_claim_labels[:4]),
                )
            )
        cards.append(
            ActionPreviewCardViewModel(
                id=f"social_draft_input_{index}",
                kind="social_draft_input_review",
                title_label="Materiał do posta do sprawdzenia",
                subtitle_label=f"{connector_label}: źródło do szkicu bez publikacji",
                status_label="publikacja zablokowana",
                rows=rows,
                apply_state_label=_apply_state_label(False),
                system_readiness_label="wymaga sprawdzenia przez człowieka",
            )
        )
    return cards


def _ads_budget_preview_cards(payload: dict[str, Any]) -> list[ActionPreviewCardViewModel]:
    preview_items = [
        item for item in payload.get("budget_payload_preview", []) if isinstance(item, dict)
    ]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        safety_review_value = item.get("safety_review")
        safety_review = safety_review_value if isinstance(safety_review_value, dict) else {}
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
                _micros_money_label(
                    item.get("proposed_budget_amount_micros"),
                    missing_label=(
                        "brak proponowanej kwoty; WILQ pokazuje tylko obecny "
                        "budżet i blokuje zapis"
                    ),
                ),
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
                system_readiness_label=_system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def _ads_recommendation_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    preview_items = [item for item in payload.get("payload_preview", []) if isinstance(item, dict)]
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
                system_readiness_label=_system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def _ads_negative_keyword_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    preview_items = [item for item in payload.get("payload_preview", []) if isinstance(item, dict)]
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
                system_readiness_label=_system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def _ads_custom_segment_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    preview_items = [item for item in payload.get("payload_preview", []) if isinstance(item, dict)]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        targeting_preview = next(
            (target for target in item.get("targeting_preview", []) if isinstance(target, dict)),
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
                id=f"ads_custom_segment_preview_{index}",
                kind="google_ads_custom_segment_review",
                title_label="Segment odbiorców do sprawdzenia",
                subtitle_label="ocena segmentu bez zapisu zmian",
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=_apply_state_label(item.get("apply_allowed")),
                system_readiness_label=_system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def _ads_change_history_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    preview_items = [
        item for item in payload.get("change_history_preview", []) if isinstance(item, dict)
    ]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        changed_fields = _string_list(item.get("changed_fields"))
        rows = [
            _preview_row(
                "Zdarzenie",
                str(item.get("change_event_id") or "zmiana do sprawdzenia"),
            ),
            _preview_row(
                "Data zmiany",
                str(item.get("change_date_time") or "data niepotwierdzona"),
            ),
            _preview_row(
                "Zasób",
                str(item.get("change_resource_type") or "zasób do sprawdzenia"),
            ),
            _preview_row(
                "Operacja",
                str(item.get("resource_change_operation") or "operacja do sprawdzenia"),
            ),
            _preview_row(
                "Pola",
                ", ".join(changed_fields[:4]) if changed_fields else "brak listy pól",
            ),
        ]
        missing_read_contract_labels = _string_list(item.get("missing_read_contract_labels"))
        if not missing_read_contract_labels:
            missing_read_contract_labels = _action_gate_labels(
                _string_list(item.get("missing_read_contracts"))
            )
        if missing_read_contract_labels:
            rows.append(_preview_row("Braki", ", ".join(missing_read_contract_labels[:4])))
        requirement_labels = _string_list(item.get("required_validation_labels"))
        if not requirement_labels:
            requirement_labels = _action_gate_labels(_string_list(item.get("required_validation")))
        if requirement_labels:
            rows.append(_preview_row("Warunki sprawdzenia", ", ".join(requirement_labels[:4])))
        blocked_labels = _string_list(item.get("blocked_claim_labels"))
        if not blocked_labels:
            blocked_labels = operator_blocked_claims(_string_list(item.get("blocked_claims")))
        if blocked_labels:
            rows.append(
                _preview_row(
                    "Czego nie wolno twierdzić",
                    ", ".join(blocked_labels[:4]),
                )
            )
        cards.append(
            ActionPreviewCardViewModel(
                id=str(item.get("id") or f"ads_change_history_preview_{index}"),
                kind="google_ads_change_history_review",
                title_label="Zmiana Google Ads do sprawdzenia",
                subtitle_label="ocena wpływu zmiany bez zapisu zmian",
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=_apply_state_label(item.get("apply_allowed")),
                system_readiness_label=_system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def _demand_gen_readiness_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    preview_items = [item for item in payload.get("payload_preview", []) if isinstance(item, dict)]
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
                "Odczyty jakości stron wejścia",
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
                system_readiness_label=_system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def demand_gen_readiness_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    return _demand_gen_readiness_preview_cards(payload)


def _search_term_ngram_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    preview_items = [item for item in payload.get("ngram_preview", []) if isinstance(item, dict)]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        sample_terms = _string_list(item.get("sample_search_terms"))
        rows = [
            _preview_row("Temat", str(item.get("ngram") or "temat do sprawdzenia")),
            _preview_row("Rozmiar", _plain_metric_value_label(item.get("ngram_size"))),
            _preview_row(
                "Zapytania użytkowników",
                _plain_metric_value_label(item.get("source_search_term_count")),
            ),
            _preview_row(
                "Przykłady",
                ", ".join(sample_terms[:3]) if sample_terms else "brak przykładów",
            ),
            _preview_row("Kliknięcia", _plain_metric_value_label(item.get("clicks"))),
            _preview_row(
                "Wyświetlenia",
                _plain_metric_value_label(item.get("impressions")),
            ),
            _preview_row("Koszt", _micros_money_label(item.get("cost_micros"))),
            _preview_row("Konwersje", _plain_metric_value_label(item.get("conversions"))),
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
                id=str(item.get("id") or f"search_term_ngram_preview_{index}"),
                kind="google_ads_search_term_ngram_review",
                title_label="Temat zapytań do sprawdzenia",
                subtitle_label="ocena intencji zapytań bez zapisu zmian",
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=_apply_state_label(item.get("apply_allowed")),
                system_readiness_label=_system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def _ga4_tracking_quality_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    preview_items = [item for item in payload.get("payload_preview", []) if isinstance(item, dict)]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        metric_snapshot = item.get("metric_snapshot")
        metric_snapshot = metric_snapshot if isinstance(metric_snapshot, dict) else {}
        metric_labels = item.get("metric_snapshot_labels")
        metric_labels = metric_labels if isinstance(metric_labels, dict) else {}
        rows = [
            _preview_row(
                "Strona wejścia",
                str(
                    item.get("landing_page_label")
                    or item.get("landing_page")
                    or "strona wejścia niepotwierdzona"
                ),
            ),
            _preview_row(
                "Źródło",
                str(
                    item.get("source_medium_label")
                    or item.get("source_medium")
                    or "źródło ruchu niepotwierdzone"
                ),
            ),
            _preview_row(
                "Kampania",
                str(
                    item.get("campaign_name_label")
                    or item.get("campaign_name")
                    or "kampania niepotwierdzona"
                ),
            ),
        ]
        rows.extend(_metric_snapshot_preview_rows(metric_snapshot, metric_labels))
        tracking_gap_labels = _string_list(item.get("tracking_dimension_gap_labels"))
        if tracking_gap_labels:
            rows.append(_preview_row("Braki wymiarów", ", ".join(tracking_gap_labels[:4])))
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
                id=str(item.get("id") or f"ga4_tracking_quality_preview_{index}"),
                kind="ga4_tracking_quality_review",
                title_label="Jakość pomiaru GA4 do sprawdzenia",
                subtitle_label=str(
                    item.get("operation_type_label") or "ocena pomiaru bez zapisu zmian"
                ),
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=_apply_state_label(item.get("apply_allowed")),
                system_readiness_label=_system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def _local_visibility_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    preview_items = [item for item in payload.get("payload_preview", []) if isinstance(item, dict)]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        metric_snapshot = item.get("metric_snapshot")
        metric_snapshot = metric_snapshot if isinstance(metric_snapshot, dict) else {}
        metric_labels = item.get("metric_snapshot_labels")
        metric_labels = metric_labels if isinstance(metric_labels, dict) else {}
        rows = _metric_snapshot_preview_rows_for_keys(
            metric_snapshot,
            metric_labels,
            [
                "localo_avg_visibility_current",
                "localo_avg_visibility_change",
                "localo_avg_latest_grid_position",
                "localo_tracked_keyword_count",
                "localo_active_place_count",
                "localo_avg_rating",
                "localo_reviews_count",
                "localo_review_reply_rate",
            ],
        )
        allowed_labels = _string_list(item.get("allowed_contract_labels"))
        if allowed_labels:
            rows.append(_preview_row("Dozwolone odczyty", ", ".join(allowed_labels[:4])))
        missing_labels = _string_list(item.get("missing_read_contract_labels"))
        if missing_labels:
            rows.append(_preview_row("Braki", ", ".join(missing_labels[:4])))
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
                id=str(item.get("id") or f"localo_visibility_preview_{index}"),
                kind="localo_visibility_review",
                title_label="Widoczność lokalna do sprawdzenia",
                subtitle_label="ocena lokalna bez zapisu zmian",
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=_apply_state_label(item.get("apply_allowed")),
                system_readiness_label=_system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def _metric_snapshot_preview_rows_for_keys(
    metric_snapshot: dict[Any, Any],
    metric_labels: dict[Any, Any],
    keys: list[str],
) -> list[ActionPreviewRowViewModel]:
    rows: list[ActionPreviewRowViewModel] = []
    for key in keys:
        if key not in metric_snapshot:
            continue
        label = metric_labels.get(key)
        if not isinstance(label, str) or not label:
            continue
        rows.append(_preview_row(label, _metric_snapshot_value_label(key, metric_snapshot[key])))
    return rows


def _keyword_planner_access_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    rows = [
        _preview_row(
            "Zablokowany dostęp",
            str(payload.get("blocked_api") or "Keyword Planner"),
        ),
        _preview_row(
            "Powód",
            "token deweloperski nie ma zatwierdzonego dostępu do Keyword Plannera",
        ),
    ]
    required_state_labels = _string_list(payload.get("required_google_ads_state_labels"))
    if required_state_labels:
        rows.append(_preview_row("Wymagany stan", ", ".join(required_state_labels[:4])))
    rows.append(
        _preview_row(
            "Następny krok",
            "sprawdź status tokena deweloperskiego w Google Ads, "
            "a po akceptacji ponów odczyt danych",
        )
    )
    requirement_labels = _string_list(payload.get("required_validation_labels"))
    if requirement_labels:
        rows.append(_preview_row("Warunki sprawdzenia", ", ".join(requirement_labels[:4])))
    blocked_claim_labels = _string_list(payload.get("blocked_claim_labels"))
    if blocked_claim_labels:
        rows.append(
            _preview_row(
                "Czego nie wolno twierdzić",
                ", ".join(blocked_claim_labels[:4]),
            )
        )
    return [
        ActionPreviewCardViewModel(
            id="keyword_planner_access_preview",
            kind="google_ads_keyword_planner_access_review",
            title_label="Dostęp do Keyword Plannera do odblokowania",
            subtitle_label="blokada dostępu bez zapisu zmian",
            status_label="zapis zmian zablokowany",
            rows=rows,
            apply_state_label=_apply_state_label(payload.get("apply_allowed")),
            system_readiness_label="wymaga zmiany po stronie Google Ads",
        )
    ]


def _ads_target_guardrail_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    rows = _ads_business_context_preview_rows(payload)
    target_options = _string_list(
        _as_dict(payload.get("target_env_options")).get("target_roas_or_cpa_labels")
    )
    if target_options:
        rows.append(_preview_row("Opcje celu", ", ".join(target_options[:4])))
    missing_labels = _string_list(payload.get("missing_read_contract_labels"))
    if missing_labels:
        rows.append(_preview_row("Braki", ", ".join(missing_labels[:4])))
    allowed_labels = _string_list(payload.get("allowed_uses_after_confirmation_labels"))
    if allowed_labels:
        rows.append(_preview_row("Po potwierdzeniu", ", ".join(allowed_labels[:4])))
    requirement_labels = _string_list(payload.get("required_validation_labels"))
    if requirement_labels:
        rows.append(_preview_row("Warunki sprawdzenia", ", ".join(requirement_labels[:5])))
    blocked_claim_labels = _string_list(payload.get("blocked_claim_labels"))
    if blocked_claim_labels:
        rows.append(
            _preview_row(
                "Czego nie wolno twierdzić",
                ", ".join(blocked_claim_labels[:4]),
            )
        )
    return [
        ActionPreviewCardViewModel(
            id="ads_target_guardrail_review",
            kind="google_ads_target_guardrail_review",
            title_label="Cel Ads do potwierdzenia",
            subtitle_label="ocena celu biznesowego bez zapisu zmian",
            status_label="zapis zmian zablokowany",
            rows=rows,
            apply_state_label=_apply_state_label(payload.get("apply_allowed")),
            system_readiness_label=_system_readiness_label(payload.get("api_mutation_ready")),
        )
    ]


def _ads_strategy_review_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    rows = _ads_business_context_preview_rows(payload)
    rows.append(
        _preview_row(
            "Ostatni przegląd strategii",
            _ads_strategy_review_summary(payload.get("latest_strategy_review")),
        )
    )
    gate_labels = _string_list(payload.get("operator_review_gate_labels"))
    if gate_labels:
        rows.append(_preview_row("Warunki przeglądu", ", ".join(gate_labels[:5])))
    requirement_labels = _string_list(payload.get("required_validation_labels"))
    if requirement_labels:
        rows.append(_preview_row("Warunki sprawdzenia", ", ".join(requirement_labels[:5])))
    blocked_claim_labels = _string_list(payload.get("blocked_claim_labels"))
    if blocked_claim_labels:
        rows.append(
            _preview_row(
                "Czego nie wolno twierdzić",
                ", ".join(blocked_claim_labels[:4]),
            )
        )
    return [
        ActionPreviewCardViewModel(
            id="ads_strategy_review",
            kind="google_ads_strategy_review",
            title_label="Ocena strategii Ads do zapisania",
            subtitle_label="decyzja człowieka bez zapisu zmian w Google Ads",
            status_label="zapis zmian zablokowany",
            rows=rows,
            apply_state_label=_apply_state_label(payload.get("apply_allowed")),
            system_readiness_label=_system_readiness_label(payload.get("api_mutation_ready")),
        )
    ]


def _ads_business_context_preview_rows(
    payload: dict[str, Any],
) -> list[ActionPreviewRowViewModel]:
    context = _as_dict(payload.get("current_context"))
    configured_sources = _string_list(context.get("configured_sources"))
    return [
        _preview_row("Marża", _percentage_label(context.get("profit_margin"))),
        _preview_row("Cel biznesowy", _plain_metric_value_label(context.get("business_goal"))),
        _preview_row("Cel budżetu", _plain_metric_value_label(context.get("budget_goal"))),
        _preview_row(
            "Docelowy zwrot z reklam",
            _plain_metric_value_label(
                context.get("target_roas"),
                missing_label="nie ustawiono; WILQ nie ocenia opłacalności Ads",
            ),
        ),
        _preview_row(
            "Docelowy koszt pozyskania celu",
            _micros_money_label(
                context.get("target_cpa_micros"),
                missing_label="nie ustawiono; WILQ nie ocenia kosztu celu",
            ),
        ),
        _preview_row(
            "Ustawione pola",
            _configured_source_count_label(configured_sources),
        ),
    ]


def _ads_strategy_review_summary(value: Any) -> str:
    if not isinstance(value, dict):
        return "przegląd strategii nie jest zapisany"
    outcome = value.get("outcome")
    labels = {
        "approved_for_prepare": "zatwierdzone do przygotowania",
        "needs_changes": "wymaga poprawek",
        "rejected": "odrzucone",
        "deferred": "odłożone",
    }
    if isinstance(outcome, str):
        return labels.get(outcome, "przegląd zapisany")
    return "przegląd zapisany"


def _configured_source_count_label(values: list[str]) -> str:
    count = len(values)
    if count == 0:
        return "żadne pole nie jest ustawione lokalnie"
    if count == 1:
        return "1 pole ustawione lokalnie"
    if 2 <= count <= 4:
        return f"{count} pola ustawione lokalnie"
    return f"{count} pól ustawionych lokalnie"


def _percentage_label(value: Any) -> str:
    if not isinstance(value, int | float):
        return "wartość procentowa niepotwierdzona"
    numeric_label = f"{value * 100:.2f}".rstrip("0").rstrip(".")
    return f"{numeric_label}%"


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


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
                title_label="Problem pliku produktowego do sprawdzenia",
                subtitle_label=_merchant_preview_subtitle(item),
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=_apply_state_label(item.get("apply_allowed")),
                system_readiness_label=_system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def _merchant_preview_subtitle(item: dict[str, Any]) -> str:
    issue_label = str(item.get("issue_type_label") or "problem pliku produktowego")
    attribute_label = str(item.get("affected_attribute_label") or "").strip()
    if attribute_label and attribute_label not in {"atrybut", "atrybut do sprawdzenia"}:
        return f"{attribute_label} - {issue_label}"
    return issue_label


def _prioritized_merchant_preview_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            0
            if _string_list(item.get("sample_titles"))
            or _string_list(item.get("sample_product_ids"))
            else 1,
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


def _micros_money_label(
    value: Any,
    currency_code: str = "PLN",
    *,
    missing_label: str = "kwota niepotwierdzona",
) -> str:
    if not isinstance(value, int | float):
        return missing_label
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
            "apply_blocker_summary_label": blocker_count_label(
                gate.apply_blocker_labels or gate.apply_blockers
            ),
            "last_mutation_blocker_summary_label": blocker_count_label(
                gate.last_mutation_blocker_labels or gate.last_mutation_blockers
            ),
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
            "last_mutation_attempted_label": _action_mutation_attempted_label(
                gate.last_mutation_attempted
            ),
            "last_mutation_adapter_reached_label": _action_mutation_adapter_reached_label(
                gate.last_mutation_adapter_reached
            ),
            "last_external_write_attempted_label": _action_mutation_attempted_label(
                gate.last_external_write_attempted
            ),
            "last_mutation_adapter_label": _action_mutation_adapter_label(
                gate.last_mutation_adapter
            ),
            "last_mutation_audit_trace_label": _action_mutation_audit_trace_label(
                gate.last_mutation_audit_event_id
            ),
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
    operator_details: dict[str, Any] = {}
    for key, value in details.items():
        if _contains_raw_audit_contract_text(str(key)):
            continue
        clean_value = _audit_detail_value_for_operator(value)
        if clean_value is not None:
            operator_details[str(key)] = clean_value
    checked_items = _string_list(operator_details.get("checked_items"))
    if checked_items:
        operator_details["checked_items"] = [_review_summary_item(item) for item in checked_items]
    blockers = _string_list(operator_details.get("blockers"))
    if blockers:
        operator_details["blockers"] = [_review_blocker_label(item) for item in blockers]
    return operator_details


def _audit_detail_value_for_operator(value: Any) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            if _contains_raw_audit_contract_text(str(key)):
                continue
            clean_item = _audit_detail_value_for_operator(item)
            if clean_item is not None:
                clean[str(key)] = clean_item
        return clean or None
    if isinstance(value, list):
        clean_items = [
            clean_item
            for item in value
            if (clean_item := _audit_detail_value_for_operator(item)) is not None
        ]
        return clean_items or None
    if isinstance(value, str) and _contains_raw_audit_contract_text(value):
        return None
    return value


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
        summary = (
            "Kontrola WILQ potwierdza warunki zapisu; operator nadal musi jawnie "
            "potwierdzić zapis zmian."
        )
    elif action.validation_status == "valid":
        status = "validated_prepare_only"
        summary = (
            "Kontrola WILQ potwierdza warunki przygotowania; zapis zmian nadal "
            "wymaga osobnego kontraktu i zgody operatora."
        )
    else:
        status = "pending_validation"
        summary = "Wymaga sprawdzenia w WILQ; zapis zmian pozostaje zablokowany osobnymi warunkami."
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
        last_review_summary=_operator_audit_summary_text(last_review.summary)
        if last_review is not None
        else None,
        last_confirmation_by=last_confirmation.actor if last_confirmation is not None else None,
        last_confirmation_at=last_confirmation.created_at
        if last_confirmation is not None
        else None,
        last_confirmation_summary=_action_audit_summary_for_operator(last_confirmation)
        if last_confirmation is not None
        else None,
        last_impact_check_status=_impact_status_from_event(last_impact_check),
        last_impact_checked_by=last_impact_check.actor if last_impact_check is not None else None,
        last_impact_checked_at=last_impact_check.created_at
        if last_impact_check is not None
        else None,
        last_impact_check_summary=last_impact_check.summary
        if last_impact_check is not None
        else None,
        last_mutation_audit_id=last_mutation_audit.id if last_mutation_audit is not None else None,
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
        last_mutation_adapter_reached=last_mutation_audit.adapter_reached
        if last_mutation_audit is not None
        else None,
        last_external_write_attempted=last_mutation_audit.external_write_attempted
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
        return f"URL finalny: {content_contract_label(item.removeprefix('url_review_outcome:'))}"
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
        raw_claim = item.removeprefix("blocked_claim:").strip()
        claim_labels = operator_blocked_claims([raw_claim])
        claim_label = claim_labels[0] if claim_labels else raw_claim
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
            f"{', '.join(_action_gate_labels(blockers))}. "
            f"{_operator_note_sentence(request.notes)}"
            "Ten krok nie zapisuje zmian w zewnętrznych systemach."
        )
    return (
        "Potwierdzenie podglądu zapisane. "
        f"{_operator_note_sentence(request.notes)}"
        "Ten krok nie zapisuje zmian w zewnętrznych systemach."
    )


def _ads_target_confirmation_blockers(request: ActionConfirmRequest) -> list[str]:
    blockers: list[str] = []
    target_count = int(request.target_roas is not None) + int(request.target_cpa_micros is not None)
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
            f"{', '.join(_action_gate_labels(blockers))}. "
            f"Notatka: {request.notes}. "
            "Ten krok nie zapisuje zmian w Google Ads."
        )
    if request.target_roas is not None:
        target_summary = f"docelowy zwrot z reklam: {request.target_roas:g}"
    else:
        target_summary = (
            f"docelowy koszt pozyskania celu: {_micros_money_label(request.target_cpa_micros)}"
        )
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
        f"Porównanie sprzed zmiany: {request.pre_window_days} dni.",
        f"Porównanie po zmianie: {request.post_window_days} dni.",
        f"Metryki z dowodami: {metric_fact_count}.",
        "Źródła: "
        + (
            f"{', '.join(_source_connector_labels(source_connectors))}."
            if source_connectors
            else "brak."
        ),
    ]
    if blockers:
        parts.append(f"Blokady: {', '.join(_action_gate_labels(blockers))}.")
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
        if label:
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
        return "Nie ma dowodów źródłowych; nie traktuj tego jako rekomendacji"
    if count == 1:
        return "1 dowód źródłowy"
    if 2 <= count <= 4:
        return f"{count} dowody źródłowe"
    return f"{count} dowodów źródłowych"


def _action_validation_status_label(value: str) -> str:
    labels = {
        "not_validated": "nie sprawdzono w WILQ",
        "valid": "kontrola WILQ poprawna",
        "invalid": "wymaga poprawek",
    }
    return labels.get(value, "status sprawdzenia")


def _action_review_gate_status_label(value: str) -> str:
    labels = {
        "pending_validation": "czeka na sprawdzenie",
        "validated_prepare_only": "kontrola WILQ poprawna",
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
    return labels.get(value or "", "stan zapisu nieustalony")


def _action_mutation_attempted_label(value: bool | None) -> str:
    if value is True:
        return "próbowano zapisu w systemie zewnętrznym"
    if value is False:
        return "nie próbowano zapisu w systemie zewnętrznym"
    return "brak informacji o próbie zapisu"


def _action_mutation_adapter_reached_label(value: bool | None) -> str:
    if value is True:
        return "adapter wykonania został osiągnięty"
    if value is False:
        return "adapter wykonania nie został osiągnięty"
    return "brak informacji o adapterze wykonania"


def _action_mutation_adapter_label(value: str | None) -> str:
    if not value:
        return "brak bezpiecznej ścieżki zapisu"
    labels = source_connector_labels([value])
    return labels[0] if labels else "system zewnętrzny wskazany"


def _action_mutation_audit_trace_label(value: str | None) -> str:
    if value:
        return "ślad bezpieczeństwa zapisany"
    return "ślad bezpieczeństwa niepowiązany"


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
        return _operator_preview_summary_from_audit(event.summary)
    if event.event_type in {"action_apply_confirmed", "action_apply_confirmation_confirmed"}:
        return _operator_audit_summary_text(event.summary) or (
            "Podgląd zmian potwierdzony. Nie zapisano zmian w zewnętrznych systemach."
        )
    if event.event_type in {"action_confirmation_blocked", "action_apply_confirmation_blocked"}:
        return _operator_audit_summary_text(event.summary) or (
            "Potwierdzenie podglądu zablokowane. Nie zapisano zmian w zewnętrznych systemach."
        )
    if event.event_type in {"action_impact_check_completed", "action_impact_check_blocked"}:
        return _operator_impact_summary_from_audit(event.summary)
    if event.event_type == "action_apply_blocked":
        return "Zapis zmian zablokowany przez warunki bezpieczeństwa WILQ."
    if event.event_type == "action_apply_completed":
        return "Zapis zmian wykonany i zapisany w audycie bezpieczeństwa."
    return _operator_audit_summary_text(event.summary)


def _operator_audit_summary_text(summary: str) -> str:
    clean_summary = str(summary or "").strip()
    if _contains_raw_audit_contract_text(clean_summary):
        return "Historyczny ślad bezpieczeństwa. Nie zapisano zmian w zewnętrznych systemach."
    clean_summary = _remove_raw_audit_identifiers(clean_summary)
    return _normalize_operator_summary_text(clean_summary)


RAW_AUDIT_IDENTIFIER_RE = re.compile(r"\baudit_[A-Za-z0-9_:-]+\b")
RAW_AUDIT_REFERENCE_CLAUSE_RE = re.compile(
    r"\s*(Audyt podglądu|ID audytu|Ślad audytu):\s*audit_[A-Za-z0-9_:-]+\.?\s*",
    flags=re.IGNORECASE,
)


def _remove_raw_audit_identifiers(summary: str) -> str:
    if not RAW_AUDIT_IDENTIFIER_RE.search(summary):
        return summary
    without_reference_clause = RAW_AUDIT_REFERENCE_CLAUSE_RE.sub(" ", summary)
    if RAW_AUDIT_IDENTIFIER_RE.search(without_reference_clause):
        return "Zdarzenie audytu zapisane. Szczegóły techniczne są dostępne w audycie."
    return " ".join(without_reference_clause.split())


def _operator_note_sentence(notes: str) -> str:
    note = str(notes or "").strip().rstrip(".")
    note = re.sub(
        r"\s*Ten krok nie zapisuje zmian(?: w zewnętrznych systemach)?\.?$",
        "",
        note,
        flags=re.IGNORECASE,
    ).strip()
    if not note:
        return ""
    return f"Notatka: {note}. "


def _normalize_operator_summary_text(summary: str) -> str:
    compact = " ".join(str(summary or "").split())
    compact = re.sub(r"\.{2,}", ".", compact)
    return re.sub(
        r"Ten krok nie zapisuje zmian\. (?=Ten krok nie zapisuje zmian w zewnętrznych systemach\.)",
        "",
        compact,
    )


def _audit_event_has_raw_contract_text(event: AuditEvent) -> bool:
    if _contains_raw_audit_contract_text(event.summary):
        return True
    return _audit_detail_contains_raw_contract_text(event.details)


def _audit_detail_contains_raw_contract_text(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            _contains_raw_audit_contract_text(str(key))
            or _audit_detail_contains_raw_contract_text(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_audit_detail_contains_raw_contract_text(item) for item in value)
    if isinstance(value, str):
        return _contains_raw_audit_contract_text(value)
    return False


def _contains_raw_audit_contract_text(summary: str) -> bool:
    raw_fragments = (
        "blocked_claim:",
        "candidate:",
        "ekologus.dev.proudsite.pl",
        "mapping_",
        "payload_",
        "source_type:",
        "staging handoff",
        "target" "_site",
        "target" "_site" "_",
        "target" "_site" "_migration",
        "Explicit apply confirmation is required",
        "Action must be validated before apply",
        "Action mode must be apply before external execution",
    )
    return any(fragment in summary for fragment in raw_fragments)


def _operator_preview_summary_from_audit(summary: str) -> str:
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
    return f"Podgląd zmian przygotowany.{item_summary} Nie zapisano zmian w zewnętrznych systemach."


def _operator_impact_summary_from_audit(summary: str) -> str:
    if "status=blocked" in summary or "zablok" in summary:
        prefix = "Sprawdzenie efektu zablokowane."
    else:
        prefix = "Sprawdzenie efektu zapisane."
    window_parts = [
        _operator_impact_summary_part(part.strip())
        for part in summary.split(".")
        if part.strip().startswith(
            (
                "Okno przed zmianą",
                "Okno po zmianie",
                "Porównanie sprzed zmiany",
                "Porównanie po zmianie",
                "Metryki z dowodami",
            )
        )
    ]
    clean_parts = [prefix, *[f"{part}." for part in window_parts]]
    if "Ten krok nie zapisuje zmian" not in " ".join(clean_parts):
        clean_parts.append("Ten krok nie zapisuje zmian w zewnętrznych systemach.")
    return " ".join(clean_parts)


def _operator_impact_summary_part(part: str) -> str:
    return impact_comparison_summary_label(part) or part


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
        "apply_confirmation_missing": "Zapis zmian zablokowany",
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
        "missing": "status niepotwierdzony",
        "pending_validation": "czeka na sprawdzenie",
        "validated_prepare_only": "kontrola WILQ poprawna",
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
    return labels.get(value, "typ rekomendacji do sprawdzenia")


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
        "vendor_mutation_adapter_required": (
            "brak bezpiecznej ścieżki zapisu w zewnętrznym systemie"
        ),
        "validate_action_object": "sprawdzenie akcji",
        "human_review_before_apply": "sprawdzenie przez człowieka przed zapisem",
        "human_confirm_before_apply": "potwierdzenie człowieka przed zapisem",
        "compare_90_day_safety_read": "porównaj z 90-dniową kontrolą bezpieczeństwa",
        "confirm_developer_access_approval": "potwierdź akceptację dostępu deweloperskiego",
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
        "wordpress_draft_preview_review": "podgląd wpisu WordPress",
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
        "review_issue_type_and_attribute": "sprawdź typ problemu i atrybut pliku produktowego",
        "review_reporting_context": "sprawdź kontekst raportowania",
        "group_issue_reasons": "pogrupuj powody problemów",
        "identify_disapproved_products": "ustal produkty i zgłoszenia do sprawdzenia",
        "mutation_audit_required": "wymagany ślad bezpieczeństwa",
        "mutation_audit": "ślad bezpieczeństwa zapisu",
        "negative_keyword_action_validation": "sprawdzenie w WILQ dla wykluczeń",
        "prepare_feed_fix_preview": "przygotuj podgląd zmian pliku produktowego",
        "require_human_confirm_before_apply": "człowiek potwierdza przed zapisem",
        "require_human_confirm_before_any_write": "człowiek potwierdza przed każdym zapisem",
        "reject_brand_or_low_intent_terms": "odrzuć brandowe lub niskointencyjne frazy",
        "rerun_google_ads_data_read": "uruchom ponowny odczyt Google Ads",
        "review_ads_campaign_channel_context": "sprawdź kanały kampanii Ads",
        "review_campaign_goal": "sprawdź cel kampanii",
        "review_campaign_name_dimension": "sprawdź nazwę kampanii",
        "review_conversion_quality": "sprawdź jakość konwersji",
        "review_conversion_or_key_event_mapping": (
            "sprawdź powiązanie konwersji lub zdarzenia kluczowego"
        ),
        "review_budget_context": "sprawdź kontekst budżetu",
        "review_demand_gen_missing_contracts": "sprawdź braki danych Demand Gen",
        "review_ga4_landing_source_campaign_context": (
            "sprawdź stronę wejścia, źródło i kampanię w GA4"
        ),
        "review_human_budget_goal": "sprawdź cel budżetu od człowieka",
        "review_landing_page_dimension": "sprawdź stronę wejścia",
        "review_local_rankings_aggregate": "sprawdź zbiorcze dane lokalnych pozycji",
        "review_ngram_intent": "sprawdź intencję tematu zapytań",
        "review_place_inventory": "sprawdź listę lokalizacji",
        "review_profit_margin_model": "sprawdź model marży",
        "review_reviews_aggregate": "sprawdź zbiorcze dane opinii",
        "review_search_term_context": "sprawdź kontekst wyszukiwanego hasła",
        "review_search_terms_before_budget_decision": (
            "sprawdź wyszukiwane hasła przed decyzją budżetową"
        ),
        "review_source_medium_dimension": "sprawdź źródło i medium ruchu",
        "review_source_search_terms": "sprawdź źródłowe wyszukiwane hasła",
        "review_source_terms": "sprawdź źródłowe hasła",
        "review_target_fit": "sprawdź dopasowanie do celu",
        "review_conversion_tracking": "sprawdź pomiar konwersji",
        "review_pmax_asset_feed_context": "sprawdź kontekst zasobów i pliku produktowego PMax",
        "check_existing_keywords_and_match_types": (
            "sprawdź istniejące słowa kluczowe i dopasowania"
        ),
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
        "ngram_to_negative_keyword_change_preview": (
            "podgląd przejścia z tematu zapytań do wykluczenia"
        ),
        "block_local_tasks_without_contract": "blokuj lokalne zadania bez kontraktu",
        "demand_gen_landing_quality_by_campaign": "jakość stron wejścia Demand Gen według kampanii",
        "demand_gen_campaign_mode_review": "kontrola trybu kampanii Demand Gen",
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
        "no_performance_claims_without_source_metric": (
            "bez obietnic skuteczności bez metryk źródłowych"
        ),
        "no_publishing_without_connector_credentials": (
            "bez publikacji bez danych dostępowych źródła"
        ),
        "require_social_history_duplicate_review": (
            "sprawdź historię postów przed twierdzeniem, że temat się nie powtarza"
        ),
        "require_human_review_before_apply": "człowiek sprawdza przed zapisem",
        "confirm_target_roas_or_cpa": (
            "potwierdź docelowy zwrot z reklam albo koszt pozyskania celu"
        ),
        "target_roas_or_cpa_required": "podaj docelowy zwrot z reklam albo koszt pozyskania celu",
        "exactly_one_target_guardrail_allowed": "podaj tylko jeden cel Ads do sprawdzenia",
        "record_human_strategy_review_outcome": (
            "zapisz wynik sprawdzenia strategii przez człowieka"
        ),
        "WILQ_ADS_TARGET_ROAS": "docelowy zwrot z reklam",
        "WILQ_ADS_TARGET_CPA_MICROS": "docelowy koszt pozyskania celu",
        "target_metrics_review": "przegląd wskaźników względem celu",
        "campaign_review_context": "kontekst przeglądu kampanii",
        "budget_review_context": "kontekst przeglądu budżetu",
        "recommended_budget_missing": "brak proponowanego budżetu",
        "target_roas_or_cpa": "docelowy zwrot z reklam albo koszt pozyskania celu",
        "developer_access_approved_for_keyword_planner": (
            "dostęp deweloperski zatwierdzony dla Keyword Plannera"
        ),
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


def _action_payload_api_mutation_ready(payload: dict[str, Any]) -> bool:
    if payload.get("api_mutation_ready") is True:
        return True
    if payload.get("api_mutation_ready") is False:
        return False
    preview_items = _payload_preview_items(payload)
    if not preview_items:
        return False
    return all(
        item.get("apply_allowed") is True and item.get("api_mutation_ready") is not False
        for item in preview_items
    )


def _action_confirmation_required(required_checks: list[str], mode: ActionMode) -> bool:
    if _requires_human_confirmation(required_checks):
        return True
    return mode in {ActionMode.prepare, ActionMode.apply}


def _requires_human_confirmation(required_checks: list[str]) -> bool:
    return any("human" in check and "confirm" in check for check in required_checks)


def _payload_preview_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in (
        "wordpress_draft_payload_preview",
        "budget_payload_preview",
        "custom_segment_payload_preview",
        "negative_keyword_payload_preview",
        "ngram_preview",
    ):
        preview = payload.get(key)
        if isinstance(preview, list):
            items = [item for item in preview if isinstance(item, dict)]
            if items:
                return items
        if isinstance(preview, dict):
            return [preview]
    preview = payload.get("payload_preview")
    if isinstance(preview, list):
        return [item for item in preview if isinstance(item, dict)]
    if isinstance(preview, dict):
        return [preview]
    preview_items: list[dict[str, Any]] = []
    for value in payload.values():
        if isinstance(value, list):
            preview_items.extend(
                item for item in value if isinstance(item, dict) and "apply_allowed" in item
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
