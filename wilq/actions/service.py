from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from wilq.actions.google_ads.business_context import (
    ADS_BUSINESS_CONTEXT_ACTION_ID,
    ads_business_context_configured,
    ads_business_context_missing_read_contracts,
    ads_business_context_payload,
)
from wilq.actions.google_ads.campaign_review import (
    CAMPAIGN_REVIEW_ACTION_ID,
    campaign_review_payload_from_metric_facts,
)
from wilq.actions.google_ads.custom_segments import (
    CUSTOM_SEGMENT_ACTION_ID,
    custom_segment_payload_from_metric_facts,
)
from wilq.actions.google_ads.negative_keywords import (
    NEGATIVE_KEYWORD_ACTION_ID,
    negative_keyword_payload_from_metric_facts,
)
from wilq.actions.google_ads.recommendations import (
    RECOMMENDATION_REVIEW_ACTION_ID,
    recommendation_review_payload_from_metric_facts,
)
from wilq.actions.payloads import validate_action_payload
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionApplyRequest,
    ActionApplyResult,
    ActionMode,
    ActionObject,
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
from wilq.storage.metric_store import metric_store


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
                "przygotować tylko review-safe kolejkę, dopóki read-only refresh nie "
                "dostarczy issue-level metric facts."
            ),
            recommended_reason=(
                "Uruchom read-only Merchant refresh albo użyj istniejących evidence, "
                "potem waliduj payload preview przed jakąkolwiek zmianą feedu."
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
                    "approval restored",
                    "revenue recovered",
                    "automatic feed edit",
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
                "GA4 jest core workflow WILQ. W clean runtime WILQ może tylko "
                "przygotować tracking review i zablokować claimy o ROAS/revenue, "
                "dopóki nie ma metric facts z landing/source/campaign."
            ),
            recommended_reason=(
                "Zbierz read-only GA4 breakdown, potem sprawdź tracking i message "
                "match bez oceniania kampanii po niepełnych danych."
            ),
            payload={
                "action_type": "ga4_tracking_gap",
                "connector": "google_analytics_4",
                "mode": "prepare_only",
                "source_metric_names": [],
                "required_breakdowns": ["landing_page", "source_medium", "campaign"],
                "blocked_claims": ["conversion_rate", "revenue", "roas"],
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
                "przygotować tylko review-safe kolejkę, dopóki GSC/WordPress/GA4 "
                "nie dostarczą URL/query evidence."
            ),
            recommended_reason=(
                "Zbierz GSC query/page i WordPress inventory, potem klasyfikuj "
                "refresh/merge/create/block bez obietnic leadów ani rankingów."
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
                    "require_human_confirm_before_wordpress_write",
                ],
                "blocked_claims": ["lead uplift", "revenue impact", "ranking guarantee"],
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
)
ACTION_METRIC_FACT_LIMIT = 120
ACTION_METRIC_FACT_LIMITS = {
    "google_ads": 2000,
    "google_analytics_4": 2000,
    "google_merchant_center": 2000,
}


def list_actions() -> list[ActionObject]:
    actions = {**_STATIC_ACTIONS, **seed_metric_action_candidates()}
    if _google_ads_live_data_available():
        actions.pop("act_configure_google_ads_env", None)
        business_context_action = _google_ads_business_context_action()
        if business_context_action is not None:
            actions[business_context_action.id] = business_context_action
    return list(actions.values())


def get_action(action_id: str) -> ActionObject | None:
    actions = {**_STATIC_ACTIONS, **seed_metric_action_candidates()}
    business_context_action = _google_ads_business_context_action()
    if business_context_action is not None:
        actions[business_context_action.id] = business_context_action
    return actions.get(action_id)


def _google_ads_live_data_available() -> bool:
    latest_run = _latest_google_ads_vendor_read()
    if latest_run is None:
        return False
    return (
        latest_run.status == ConnectorRefreshStatus.completed
        and latest_run.vendor_data_collected is True
    )


def _latest_google_ads_vendor_read() -> ConnectorRefreshRun | None:
    latest_run = None
    for run in list_connector_refresh_runs(connector_id="google_ads"):
        if run.mode == ConnectorRefreshMode.vendor_read:
            latest_run = run
            break
    return latest_run


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
            "targetu ROAS albo CPA."
        ),
        recommended_reason=(
            "Uzupełnij repo-local .env wartościami biznesowymi, potem sprawdź "
            "business_context_read_contract. Do tego czasu WILQ blokuje claimy "
            "o rentowności, zmarnowanym budżecie i skalowaniu."
        ),
        payload=ads_business_context_payload(missing_read_contracts),
        validation_status="not_validated",
        created_by="system_business_context_seed",
    )


def seed_metric_action_candidates() -> dict[str, ActionObject]:
    facts = _action_metric_facts()
    by_connector = _facts_by_connector(facts)
    actions: dict[str, ActionObject] = {}

    merchant_facts = by_connector.get("google_merchant_center", [])
    merchant_issue_facts = _merchant_issue_metric_facts(merchant_facts)
    if merchant_issue_facts:
        merchant_action_metrics = merchant_issue_facts[:8]
        merchant_issue_clusters = _merchant_issue_clusters_payload(merchant_issue_facts)
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
                "Merchant Center ma wymiarowe issue facts z WILQ API. "
                f"{_metric_sentence(merchant_action_metrics)}. To uzasadnia "
                "kolejkę review problemów feedu, ale nie automatyczną zmianę "
                "danych produktu."
            ),
            recommended_reason=(
                "Na /merchant pokaż issue clusters jako prepare-only queue: "
                "sprawdź typ problemu, atrybut, kraj, payload preview i walidację "
                "przed jakąkolwiek zmianą feedu."
            ),
            payload={
                "action_type": "merchant_feed_issue",
                "connector": "google_merchant_center",
                "mode": "prepare_only",
                "source_metric_names": _unique(fact.name for fact in merchant_action_metrics),
                "issue_clusters": merchant_issue_clusters,
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
                "GA4 zwraca wymiarowe landing/source/campaign facts, ale WILQ "
                "nadal nie ma kontraktu na ROAS, revenue ani werdykt konwersji. "
                f"{_metric_sentence(ga4_action_metrics)}."
            ),
            recommended_reason=(
                "Na /ga4 przygotuj review pomiaru i jakości ruchu: pokaż "
                "landing/source/campaign breakdown, waliduj ActionObject i nie "
                "oceniaj kampanii bez kontraktu konwersji."
            ),
            payload={
                "action_type": "ga4_tracking_gap",
                "connector": "google_analytics_4",
                "mode": "prepare_only",
                "source_metric_names": _unique(fact.name for fact in ga4_action_metrics),
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
        content_action_metrics = _prioritize_action_metrics(
            content_facts,
            required_names={"content_object_count", "clicks", "domain_rating"},
        )[:10]
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

    google_ads_facts = by_connector.get("google_ads", [])
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
                "Google Ads ma realne campaign metric facts. WILQ może przygotować "
                "kolejkę przeglądu kampanii z KPI policzonymi z evidence, ale nadal "
                "blokuje decyzje budżetowe bez pacingu, historii zmian, rekomendacji "
                "i modelu wartości."
            ),
            recommended_reason=(
                "Na /ads-doctor przejrzyj kampanie z największym kosztem i ruchem. "
                "Traktuj payload jako review-only: bez pause, budget scaling ani "
                "claimów o rentowności."
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
            title="Przygotuj review rekomendacji Google Ads",
            domain=OpportunityDomain.google_ads,
            connector="google_ads",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=recommendation_review_payload["evidence_ids"],
            metrics=recommendation_metrics,
            human_diagnosis=(
                "Google Ads ma aktywne recommendation facts. WILQ może pokazać "
                "review-only apply payload preview, ale nie może akceptować "
                "rekomendacji bez strategii, RMF/compliance review, potwierdzenia "
                "i audytu."
            ),
            recommended_reason=(
                "Na /ads-doctor przejrzyj typ rekomendacji, impact preview i "
                "powiązane kampanie. Traktuj payload jako podgląd operacji, nie "
                "zgodę na apply."
            ),
            payload=recommendation_review_payload,
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
            title="Przygotuj kandydatów custom segments z search terms",
            domain=OpportunityDomain.google_ads,
            connector="google_ads",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=custom_segment_payload["evidence_ids"],
            metrics=custom_segment_metrics,
            human_diagnosis=(
                "Google Ads ma realne search-term metric facts. WILQ może przygotować "
                "kandydatów custom segments wyłącznie z tych terminów, ale nie może "
                "twierdzić audience size, ROAS ani performance bez dodatkowych kontraktów."
            ),
            recommended_reason=(
                "Na /ads-doctor przejrzyj source terms, odrzuć brand/low-intent terms, "
                "dodaj Keyword Planner enrichment i waliduj payload preview przed apply."
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
            title="Przygotuj kolejkę review wykluczeń z search terms",
            domain=OpportunityDomain.google_ads,
            connector="google_ads",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=negative_keyword_payload["evidence_ids"],
            metrics=negative_keyword_metrics,
            human_diagnosis=(
                "Google Ads ma search-term metric facts, które mogą zasilić review "
                "potencjalnych wykluczeń. WILQ nie może jednak twierdzić waste ani "
                "wdrażać negative keywords bez 90-dniowego safety checku i ręcznej "
                "walidacji."
            ),
            recommended_reason=(
                "Na /ads-doctor przejrzyj terminy z kosztem/kliknięciami i zerową "
                "konwersją w bieżącym evidence, ale potraktuj je wyłącznie jako "
                "kolejkę review przed 90-day safety check."
            ),
            payload=negative_keyword_payload,
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


def _action_metric_facts() -> list[MetricFact]:
    facts: list[MetricFact] = []
    for connector_id in ACTION_METRIC_CONNECTORS:
        facts.extend(
            fact
            for fact in metric_store().list_metric_facts(
                connector_id=connector_id,
                limit=ACTION_METRIC_FACT_LIMITS.get(connector_id, ACTION_METRIC_FACT_LIMIT),
            )
            if not _is_probe_only_fact(fact)
        )
    return _latest_metric_facts_by_identity(facts)


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
                "sample_products_available": False,
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


def _social_draft_actions(social_facts: list[MetricFact]) -> dict[str, ActionObject]:
    actions: dict[str, ActionObject] = {}
    social_metrics = _prioritize_action_metrics(
        social_facts,
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
        "source_connectors": _unique(fact.source_connector for fact in social_facts),
        "source_metric_names": _unique(fact.name for fact in social_facts),
        "draft_constraints": [
            "use_only_wilq_evidence",
            "write_in_polish",
            "no_performance_claims_without_source_metric",
            "no_publishing_without_connector_credentials",
            "require_human_review_before_apply",
        ],
        "candidate_inputs": _social_candidate_inputs(social_metrics),
        "blocked_claims": ["ROAS", "revenue", "conversion uplift", "product fix applied"],
        "destructive": False,
    }
    for connector_id, action_type, title in (
        (
            "linkedin",
            "linkedin_post_candidate",
            "Przygotuj kandydaty postów LinkedIn z dowodów WILQ",
        ),
        (
            "facebook",
            "facebook_post_candidate",
            "Przygotuj kandydaty postów Facebook z dowodów WILQ",
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
                "przełożyć na review-safe kierunki postów. Brak uprawnień social "
                "blokuje publikację, ale nie blokuje przygotowania briefu do oceny."
            ),
            recommended_reason=(
                "Na /social-publisher pokaż tylko kandydaty draftów z evidence IDs. "
                "Nie publikuj, nie planuj wysyłki i nie dopisuj claimów bez metryk."
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


def _social_candidate_inputs(facts: list[MetricFact]) -> list[dict[str, object]]:
    inputs: list[dict[str, object]] = []
    for fact in facts[:8]:
        inputs.append(
            {
                "source_connector": fact.source_connector,
                "metric_name": fact.name,
                "value": fact.value,
                "dimensions": fact.dimensions,
                "evidence_id": fact.evidence_id,
            }
        )
    return inputs


def _facts_by_connector(facts: list[MetricFact]) -> dict[str, list[MetricFact]]:
    grouped: dict[str, list[MetricFact]] = {}
    for fact in facts:
        grouped.setdefault(fact.source_connector, []).append(fact)
    return grouped


def _metric_sentence(facts: list[MetricFact]) -> str:
    sample = ", ".join(f"{fact.name}={fact.value}" for fact in facts[:4])
    return f"Najważniejsze fakty: {sample}"


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


def apply_action(
    action: ActionObject,
    request: ActionApplyRequest | None = None,
) -> ActionApplyResult:
    errors: list[str] = []
    connector = get_connector_status(action.connector)
    if request is None or request.confirm is not True:
        errors.append("Explicit apply confirmation is required.")
    if request is not None and request.confirm is True and not request.confirmed_by:
        errors.append("confirmed_by is required for explicit apply confirmation.")
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
        event_type=_apply_audit_event_type(errors),
        actor=request.confirmed_by if request and request.confirmed_by else "wilq_api",
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


def _apply_audit_event_type(errors: list[str]) -> str:
    if not errors:
        return "apply_succeeded"
    if any("confirmation" in error for error in errors):
        return "apply_confirmation_missing"
    return "apply_blocked"
