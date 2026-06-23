from __future__ import annotations

from collections.abc import Iterable

from wilq.actions.service import MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT, list_actions
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionObject,
    ActionRisk,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MerchantDecisionItem,
    MerchantDiagnosticSection,
    MerchantDiagnosticsResponse,
    MerchantFreshnessAssessment,
    MerchantIssueCluster,
    MerchantOperatorSummary,
    MerchantProductPerformanceReadiness,
    MerchantProductPerformanceRow,
    MerchantProductSampleReadiness,
    MerchantUnknownFact,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
    utc_now,
)
from wilq.storage.metric_store import metric_store

MERCHANT_CONNECTOR_ID = "google_merchant_center"
GOOGLE_ADS_CONNECTOR_ID = "google_ads"
GA4_CONNECTOR_ID = "google_analytics_4"
MERCHANT_METRIC_FACT_LIMIT = 2000
MERCHANT_PRODUCT_PERFORMANCE_REQUIRED_READ_CONTRACTS = [
    "merchant_product_id_join_key",
    "google_ads_shopping_product_performance",
    "ga4_item_product_performance",
]
MERCHANT_PRODUCT_PERFORMANCE_BLOCKED_CLAIMS = [
    "product ROAS",
    "product revenue recovery",
    "product fix impact",
    "Shopping/PMax product scaling",
    "approval restored",
    "feed write",
]
PRODUCT_JOIN_DIMENSION_KEYS = [
    "product_id",
    "item_id",
    "offer_id",
    "merchant_product_id",
    "shopping_product_id",
    "product_item_id",
    "sku",
    "item_sku",
]
MERCHANT_HEALTH_METRIC_NAMES = {
    "total_products",
    "active_products",
    "disapproved_products",
    "expiring_products",
    "item_level_issue_count",
    "merchant_action_issue_count",
}
MERCHANT_STALE_AFTER_HOURS = 48
MERCHANT_ISSUE_LABELS = {
    "availability_updated": "zmiana dostępności do sprawdzenia",
    "missing_potentially_required_attribute": "brak potencjalnie wymaganego atrybutu",
    "problem feedu": "problem feedu",
}
MERCHANT_ATTRIBUTE_LABELS = {
    "n:availability": "dostępność",
    "n:unit_pricing_measure": "miara ceny jednostkowej",
    "atrybut": "atrybut",
    "atrybut nieznany": "atrybut nieznany",
}


def build_merchant_diagnostics(
    *,
    tactical_items: list[TacticalQueueItem] | None = None,
    actions: list[ActionObject] | None = None,
    metric_facts: list[MetricFact] | None = None,
) -> MerchantDiagnosticsResponse:
    connector = get_connector_status(MERCHANT_CONNECTOR_ID)
    if connector is None:
        raise RuntimeError("Merchant Center connector is not registered.")
    latest_refresh = _latest_merchant_refresh()
    metric_facts = (
        metric_facts
        if metric_facts is not None
        else metric_store().list_metric_facts(
            connector_id=MERCHANT_CONNECTOR_ID,
            limit=MERCHANT_METRIC_FACT_LIMIT,
        )
    )
    live_data_available = bool(metric_facts) and (
        latest_refresh is None
        or (
            latest_refresh.status == ConnectorRefreshStatus.completed
            and latest_refresh.vendor_data_collected
        )
    )
    trusted_facts = metric_facts if live_data_available else []
    tactical_items = [
        item
        for item in (
            tactical_items if tactical_items is not None else build_tactical_queue().items
        )
        if item.domain == OpportunityDomain.merchant
    ]
    current_issue_facts = _current_facts_for_refresh(latest_refresh, trusted_facts)
    current_tactical_items = _current_tactical_items_for_refresh(latest_refresh, tactical_items)
    actions = actions if actions is not None else list_actions()
    action_ids = _merchant_action_ids(actions)
    issue_clusters = _merchant_issue_clusters(current_issue_facts, action_ids)
    sections = [
        _feed_health_section(latest_refresh, trusted_facts, action_ids),
        _issue_queue_section(
            latest_refresh,
            current_issue_facts,
            current_tactical_items,
            issue_clusters,
            action_ids,
        ),
        _product_action_safety_section(
            latest_refresh,
            trusted_facts,
            current_tactical_items,
            action_ids,
        ),
    ]
    decision_queue = _merchant_decision_queue(
        latest_refresh=latest_refresh,
        facts=current_issue_facts,
        tactical_items=current_tactical_items,
        issue_clusters=issue_clusters,
        action_ids=action_ids,
    )
    freshness_assessment = _merchant_freshness_assessment(latest_refresh)
    product_sample_readiness = _merchant_product_sample_readiness(
        issue_clusters,
        decision_queue,
    )
    product_performance_readiness = _merchant_product_performance_readiness(
        issue_clusters=issue_clusters,
        product_sample_readiness=product_sample_readiness,
    )
    return MerchantDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector=connector,
        latest_refresh=latest_refresh,
        live_data_available=live_data_available,
        product_count=_numeric_metric_or_refresh_summary(
            trusted_facts,
            latest_refresh,
            "total_products",
        ),
        issue_count=_numeric_metric_or_refresh_summary(
            trusted_facts,
            latest_refresh,
            "item_level_issue_count",
        ),
        freshness_assessment=freshness_assessment,
        unknowns=_merchant_unknowns(
            issue_clusters,
            decision_queue,
            product_performance_readiness,
        ),
        product_sample_readiness=product_sample_readiness,
        product_performance_readiness=product_performance_readiness,
        operator_summary=_operator_summary(
            decision_queue,
            issue_clusters,
            sections,
            action_ids,
        ),
        issue_clusters=issue_clusters,
        decision_queue=decision_queue,
        sections=sections,
        evidence_ids=_unique(
            [
                *(evidence_id for section in sections for evidence_id in section.evidence_ids),
                *(
                    evidence_id
                    for decision in decision_queue
                    for evidence_id in decision.evidence_ids
                ),
            ]
        ),
        action_ids=_unique(
            [
                *(action_id for section in sections for action_id in section.action_ids),
                *(action_id for decision in decision_queue for action_id in decision.action_ids),
            ]
        ),
        blocker_count=sum(1 for section in sections if section.status == "blocked"),
    )


def _latest_merchant_refresh() -> ConnectorRefreshRun | None:
    runs = list_connector_refresh_runs(connector_id=MERCHANT_CONNECTOR_ID)
    return runs[0] if runs else None


def _merchant_freshness_assessment(
    latest_refresh: ConnectorRefreshRun | None,
) -> MerchantFreshnessAssessment:
    if latest_refresh is None:
        return MerchantFreshnessAssessment(
            state="missing",
            latest_refresh_id=None,
            latest_refresh_completed_at=None,
            age_hours=None,
            stale_after_hours=MERCHANT_STALE_AFTER_HOURS,
            requires_refresh=True,
            summary="Brak zapisanego read-only vendor_read Merchant Center.",
            next_step="Uruchom Merchant vendor_read przed oceną aktualnego stanu feedu.",
        )

    completed_at = latest_refresh.completed_at or latest_refresh.started_at
    age_hours = round((utc_now() - completed_at).total_seconds() / 3600, 2)
    if latest_refresh.status != ConnectorRefreshStatus.completed:
        return MerchantFreshnessAssessment(
            state="blocked",
            latest_refresh_id=latest_refresh.id,
            latest_refresh_completed_at=completed_at,
            age_hours=age_hours,
            stale_after_hours=MERCHANT_STALE_AFTER_HOURS,
            requires_refresh=True,
            summary=(
                "Ostatni odczyt Merchant nie zakończył się statusem completed, "
                f"tylko {latest_refresh.status.value}."
            ),
            next_step=(
                "Napraw blocker odczytu i uruchom read-only vendor_read przed "
                "budowaniem kolejki feedu."
            ),
        )

    if age_hours > MERCHANT_STALE_AFTER_HOURS:
        return MerchantFreshnessAssessment(
            state="stale",
            latest_refresh_id=latest_refresh.id,
            latest_refresh_completed_at=completed_at,
            age_hours=age_hours,
            stale_after_hours=MERCHANT_STALE_AFTER_HOURS,
            requires_refresh=True,
            summary=(
                f"Ostatni Merchant vendor_read ma około {age_hours:.1f}h. "
                "To wystarcza do stale review, ale nie do claimów o bieżącym stanie feedu."
            ),
            next_step=(
                "Uruchom read-only Merchant vendor_read, jeśli pytanie dotyczy "
                "aktualnego stanu produktów."
            ),
        )

    return MerchantFreshnessAssessment(
        state="fresh",
        latest_refresh_id=latest_refresh.id,
        latest_refresh_completed_at=completed_at,
        age_hours=age_hours,
        stale_after_hours=MERCHANT_STALE_AFTER_HOURS,
        requires_refresh=False,
        summary=(
            f"Ostatni Merchant vendor_read ma około {age_hours:.1f}h i mieści się "
            f"w progu {MERCHANT_STALE_AFTER_HOURS}h."
        ),
        next_step="Można użyć danych do kolejki review bez dodatkowego refreshu.",
    )


def _merchant_unknowns(
    issue_clusters: list[MerchantIssueCluster],
    decisions: list[MerchantDecisionItem],
    product_performance_readiness: MerchantProductPerformanceReadiness,
) -> list[MerchantUnknownFact]:
    unknowns: list[MerchantUnknownFact] = []
    if issue_clusters or decisions:
        sample_ids = _unique(
            sample_id for cluster in issue_clusters for sample_id in cluster.sample_product_ids
        )
        if not sample_ids:
            unknowns.append(
                MerchantUnknownFact(
                    id="merchant_product_examples_missing",
                    title="Brak przykładowych produktów/SKU w kontrakcie odczytu",
                    reason=(
                        "Merchant diagnostics ma typ problemu, atrybut, kraj, kontekst "
                        "raportowania i licznik, ale nie zwraca product IDs, SKU ani tytułów."
                    ),
                    impact=(
                        "WILQ może przygotować kolejkę review po klastrach, ale nie listę "
                        "konkretnych produktów do edycji."
                    ),
                    next_step=(
                        "Dodać osobny read contract dla bezpiecznych przykładów produktów "
                        "albo otworzyć Merchant Center podczas review."
                    ),
                    blocked_claims=["product-level fix", "feed write", "automatic feed edit"],
                )
            )
        unknowns.append(
            MerchantUnknownFact(
                id="merchant_unique_product_count_unknown",
                title="Zgłoszenia raportowe nie są liczbą unikalnych produktów",
                reason=(
                    "Ten sam problem może wystąpić w ALL_CONTEXTS, FREE_LISTINGS i "
                    "SHOPPING_ADS, więc suma raportów może liczyć ten sam produkt więcej "
                    "niż raz."
                ),
                impact=(
                    "Decision queue musi używać max zgłoszeń jako skali i traktować "
                    "sumę raportów wyłącznie jako drilldown."
                ),
                next_step=(
                    "Grupować decyzje po decision_queue, a issue_clusters pokazywać "
                    "jako szczegóły raportowania."
                ),
                blocked_claims=["unique product count", "approval restored"],
            )
        )
    if product_performance_readiness.status == "blocked":
        unknowns.append(
            MerchantUnknownFact(
                id="merchant_product_performance_join_missing",
                title="Brak joinu produktów Merchant z Ads/GA4",
                reason=(
                    "WILQ ma Merchant sample product IDs albo kolejkę problemów feedu, "
                    "ale nie ma dopasowanych faktów Ads/GA4 z product_id/item_id dla "
                    "tych produktów."
                ),
                impact=(
                    "Można prowadzić review problemów feedu, ale nie wolno twierdzić, "
                    "które produkty mają ROAS, przychód, koszt albo efekt naprawy."
                ),
                next_step=(
                    "Dodać read-only kontrakty product performance dla Google Ads "
                    "Shopping/PMax i GA4 item ecommerce, z jawnie wspólnym kluczem produktu."
                ),
                blocked_claims=product_performance_readiness.blocked_claims,
            )
        )
    return unknowns


def _merchant_product_sample_readiness(
    issue_clusters: list[MerchantIssueCluster],
    decisions: list[MerchantDecisionItem],
) -> MerchantProductSampleReadiness:
    sample_product_ids = _unique(
        sample_id for cluster in issue_clusters for sample_id in cluster.sample_product_ids
    )
    sample_product_titles = _unique(
        title for cluster in issue_clusters for title in cluster.sample_titles
    )
    if sample_product_ids:
        return MerchantProductSampleReadiness(
            status="ready",
            sample_products_available=True,
            sample_count=len(sample_product_ids),
            sample_product_ids=sample_product_ids[:20],
            sample_product_titles=sample_product_titles[:20],
            required_read_contracts=[
                "merchant_products_list_product_status",
                "merchant_reports_product_view_issue_filter",
            ],
            source_endpoint="aggregateProductStatuses",
            summary=(
                "Merchant read zwraca przykładowe product IDs dla części problemów. "
                "Tytuły są dostępne tylko wtedy, gdy products.list enrichment je zwróci."
            ),
            next_step=(
                "Użyj próbek do review. Dla tytułów/SKU/statusów dodaj read-only "
                "products.list/productStatus albo reports.search product_view."
            ),
            blocked_claims=["feed write", "automatic feed edit"],
        )

    if issue_clusters or decisions:
        return MerchantProductSampleReadiness(
            status="blocked",
            sample_products_available=False,
            sample_count=0,
            required_read_contracts=[
                "merchant_products_list_product_status",
                "merchant_reports_product_view_issue_filter",
            ],
            source_endpoint="aggregateProductStatuses",
            summary=(
                "Obecny Merchant read contract daje aggregate issue queue, ale nie "
                "zwraca product IDs, SKU ani tytułów do pracy produkt-po-produkcie."
            ),
            next_step=(
                "Dodać osobny read-only contract przez products.list/productStatus "
                "albo reports.search product_view z filtrem issue, zanim WILQ pokaże "
                "konkretne produkty do poprawy."
            ),
            blocked_claims=["product-level fix", "feed write", "automatic feed edit"],
        )

    return MerchantProductSampleReadiness(
        status="blocked",
        sample_products_available=False,
        sample_count=0,
        required_read_contracts=[
            "merchant_products_list_product_status",
            "merchant_reports_product_view_issue_filter",
        ],
        source_endpoint="aggregateProductStatuses",
        summary="Brak Merchant issue queue, więc nie ma też próbek produktów.",
        next_step="Najpierw uruchom read-only Merchant vendor_read.",
        blocked_claims=["product-level fix", "feed write", "automatic feed edit"],
    )


def _merchant_product_performance_readiness(
    *,
    issue_clusters: list[MerchantIssueCluster],
    product_sample_readiness: MerchantProductSampleReadiness,
    product_metric_facts_by_connector: dict[str, list[MetricFact]] | None = None,
) -> MerchantProductPerformanceReadiness:
    sample_product_ids = product_sample_readiness.sample_product_ids
    sample_title_map = _merchant_sample_title_map(issue_clusters)
    merchant_evidence_ids = _unique(
        evidence_id for cluster in issue_clusters for evidence_id in cluster.evidence_ids
    )
    product_metric_facts_by_connector = (
        product_metric_facts_by_connector
        if product_metric_facts_by_connector is not None
        else _product_performance_metric_facts_by_connector(sample_product_ids)
    )
    ads_product_facts = _product_scoped_metric_facts(
        product_metric_facts_by_connector.get(GOOGLE_ADS_CONNECTOR_ID, [])
    )
    ga4_product_facts = _product_scoped_metric_facts(
        product_metric_facts_by_connector.get(GA4_CONNECTOR_ID, [])
    )
    ads_facts_by_product_id = _metric_facts_by_product_id(ads_product_facts)
    ga4_facts_by_product_id = _metric_facts_by_product_id(ga4_product_facts)

    performance_rows: list[MerchantProductPerformanceRow] = []
    for product_id in sample_product_ids:
        ads_facts = ads_facts_by_product_id.get(product_id, [])
        ga4_facts = ga4_facts_by_product_id.get(product_id, [])
        if not ads_facts and not ga4_facts:
            continue
        row = MerchantProductPerformanceRow(
            product_id=product_id,
            sample_title=sample_title_map.get(product_id),
            source_connectors=_unique(
                fact.source_connector for fact in [*ads_facts, *ga4_facts]
            ),
            evidence_ids=_unique(fact.evidence_id for fact in [*ads_facts, *ga4_facts]),
            ads_clicks=_int_metric_value(
                ads_facts,
                ["clicks", "product_clicks", "shopping_product_clicks"],
            ),
            ads_cost_micros=_int_metric_value(
                ads_facts,
                ["cost_micros", "product_cost_micros", "shopping_product_cost_micros"],
            ),
            ads_conversions=_float_metric_value(
                ads_facts,
                ["conversions", "product_conversions", "shopping_product_conversions"],
            ),
            ads_conversion_value=_float_metric_value(
                ads_facts,
                [
                    "conversion_value",
                    "conversions_value",
                    "product_conversion_value",
                    "shopping_product_conversion_value",
                ],
            ),
            ga4_ecommerce_purchases=_float_metric_value(
                ga4_facts,
                ["ecommerce_purchases", "item_purchases", "item_purchase_quantity"],
            ),
            ga4_purchase_revenue=_float_metric_value(
                ga4_facts,
                ["purchase_revenue", "item_revenue", "item_purchase_revenue"],
            ),
        )
        missing_metrics = _missing_product_performance_metrics(row)
        performance_rows.append(
            row.model_copy(
                update={
                    "missing_metrics": missing_metrics,
                    "blocked_claims": [
                        "product fix impact",
                        "approval restored",
                        "feed write",
                    ],
                }
            )
        )

    current_read_contracts = ["merchant_aggregate_product_statuses"]
    if ads_product_facts:
        current_read_contracts.append("google_ads_product_metric_facts")
    if ga4_product_facts:
        current_read_contracts.append("ga4_item_metric_facts")

    if performance_rows:
        return MerchantProductPerformanceReadiness(
            status="ready",
            joined_product_count=len(performance_rows),
            merchant_sample_count=len(sample_product_ids),
            ads_product_fact_count=len(ads_product_facts),
            ga4_product_fact_count=len(ga4_product_facts),
            current_read_contracts=current_read_contracts,
            required_read_contracts=MERCHANT_PRODUCT_PERFORMANCE_REQUIRED_READ_CONTRACTS,
            join_key_candidates=PRODUCT_JOIN_DIMENSION_KEYS,
            sample_product_ids=sample_product_ids[:20],
            performance_rows=performance_rows[:20],
            source_connectors=_unique(
                [
                    MERCHANT_CONNECTOR_ID,
                    *(
                        connector
                        for row in performance_rows
                        for connector in row.source_connectors
                    ),
                ]
            ),
            evidence_ids=_unique(
                [
                    *merchant_evidence_ids,
                    *(
                        evidence_id
                        for row in performance_rows
                        for evidence_id in row.evidence_ids
                    ),
                ]
            ),
            summary=(
                "WILQ ma dopasowane product-level facts dla części Merchant sample IDs. "
                "To wspiera review produktu z metrykami Ads/GA4, ale nie oznacza "
                "automatycznej naprawy feedu ani efektu po zmianie."
            ),
            next_step=(
                "Użyj performance_rows do priorytetyzacji review. Do claimów o efekcie "
                "naprawy potrzebny jest osobny before/after audit."
            ),
            blocked_claims=[
                "product fix impact",
                "approval restored",
                "feed write",
            ],
        )

    blocked_reason = (
        "Merchant read zwraca sample product IDs, ale WILQ nie ma dopasowanych "
        "product-level facts z Ads albo GA4 dla tych IDs."
        if sample_product_ids
        else (
            "Merchant read nie daje sample product IDs, więc WILQ nie ma klucza "
            "do połączenia problemów feedu z Ads/GA4."
        )
    )
    return MerchantProductPerformanceReadiness(
        status="blocked",
        joined_product_count=0,
        merchant_sample_count=len(sample_product_ids),
        ads_product_fact_count=len(ads_product_facts),
        ga4_product_fact_count=len(ga4_product_facts),
        current_read_contracts=current_read_contracts,
        required_read_contracts=MERCHANT_PRODUCT_PERFORMANCE_REQUIRED_READ_CONTRACTS,
        join_key_candidates=PRODUCT_JOIN_DIMENSION_KEYS,
        sample_product_ids=sample_product_ids[:20],
        source_connectors=_unique(
            [
                MERCHANT_CONNECTOR_ID,
                *(fact.source_connector for fact in ads_product_facts),
                *(fact.source_connector for fact in ga4_product_facts),
            ]
        ),
        evidence_ids=_unique(
            [
                *merchant_evidence_ids,
                *(fact.evidence_id for fact in ads_product_facts),
                *(fact.evidence_id for fact in ga4_product_facts),
            ]
        ),
        summary=blocked_reason,
        next_step=(
            "Dodać read-only product performance dla Google Ads Shopping/PMax i GA4 "
            "item ecommerce oraz utrzymać wspólny product_id/item_id jako join key."
        ),
        blocked_claims=MERCHANT_PRODUCT_PERFORMANCE_BLOCKED_CLAIMS,
    )


def _product_performance_metric_facts_by_connector(
    sample_product_ids: list[str],
) -> dict[str, list[MetricFact]]:
    if not sample_product_ids:
        return {
            GOOGLE_ADS_CONNECTOR_ID: [],
            GA4_CONNECTOR_ID: [],
        }
    return metric_store().list_metric_facts_by_connector(
        [GOOGLE_ADS_CONNECTOR_ID, GA4_CONNECTOR_ID],
        limit_per_connector=MERCHANT_METRIC_FACT_LIMIT,
    )


def _merchant_sample_title_map(
    issue_clusters: list[MerchantIssueCluster],
) -> dict[str, str]:
    titles_by_product_id: dict[str, str] = {}
    for cluster in issue_clusters:
        for index, product_id in enumerate(cluster.sample_product_ids):
            if index < len(cluster.sample_titles):
                titles_by_product_id.setdefault(product_id, cluster.sample_titles[index])
    return titles_by_product_id


def _product_scoped_metric_facts(facts: list[MetricFact]) -> list[MetricFact]:
    return [fact for fact in facts if _metric_fact_product_id(fact) is not None]


def _metric_facts_by_product_id(
    facts: list[MetricFact],
) -> dict[str, list[MetricFact]]:
    facts_by_product_id: dict[str, list[MetricFact]] = {}
    for fact in facts:
        product_id = _metric_fact_product_id(fact)
        if product_id is None:
            continue
        facts_by_product_id.setdefault(product_id, []).append(fact)
    return facts_by_product_id


def _metric_fact_product_id(fact: MetricFact) -> str | None:
    for key in PRODUCT_JOIN_DIMENSION_KEYS:
        value = fact.dimensions.get(key)
        if value and value.strip():
            return value.strip()
    return None


def _int_metric_value(facts: list[MetricFact], names: list[str]) -> int | None:
    value = _numeric_metric_value(facts, names)
    if value is None:
        return None
    return int(value)


def _float_metric_value(facts: list[MetricFact], names: list[str]) -> float | None:
    value = _numeric_metric_value(facts, names)
    if value is None:
        return None
    return float(value)


def _numeric_metric_value(
    facts: list[MetricFact],
    names: list[str],
) -> int | float | None:
    accepted_names = set(names)
    for fact in facts:
        if fact.name in accepted_names and isinstance(fact.value, int | float):
            return fact.value
    return None


def _missing_product_performance_metrics(
    row: MerchantProductPerformanceRow,
) -> list[str]:
    missing_metrics: list[str] = []
    if row.ads_clicks is None:
        missing_metrics.append("ads_clicks")
    if row.ads_cost_micros is None:
        missing_metrics.append("ads_cost_micros")
    if row.ads_conversions is None:
        missing_metrics.append("ads_conversions")
    if row.ads_conversion_value is None:
        missing_metrics.append("ads_conversion_value")
    if row.ga4_ecommerce_purchases is None:
        missing_metrics.append("ga4_ecommerce_purchases")
    if row.ga4_purchase_revenue is None:
        missing_metrics.append("ga4_purchase_revenue")
    return missing_metrics


def _merchant_action_ids(actions: list[ActionObject]) -> list[str]:
    return [action.id for action in actions if action.connector == MERCHANT_CONNECTOR_ID]


def _current_facts_for_refresh(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
) -> list[MetricFact]:
    if latest_refresh is None or not latest_refresh.evidence_ids:
        return facts
    evidence_ids = set(latest_refresh.evidence_ids)
    return [fact for fact in facts if fact.evidence_id in evidence_ids]


def _current_tactical_items_for_refresh(
    latest_refresh: ConnectorRefreshRun | None,
    items: list[TacticalQueueItem],
) -> list[TacticalQueueItem]:
    if latest_refresh is None or not latest_refresh.evidence_ids:
        return items
    evidence_ids = set(latest_refresh.evidence_ids)
    return [
        item
        for item in items
        if any(evidence_id in evidence_ids for evidence_id in item.evidence_ids)
    ]


def _feed_health_section(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    action_ids: list[str],
) -> MerchantDiagnosticSection:
    if not facts:
        return MerchantDiagnosticSection(
            id="merchant_feed_health",
            title="Merchant Center: brak aktualnych metryk feedu",
            status="blocked",
            summary=_merchant_blocker_reason(latest_refresh),
            diagnosis=(
                "WILQ nie ma aktualnych Merchant metric facts, więc nie może ocenić "
                "liczby produktów, issue count ani stanu feedu."
            ),
            next_step=(
                "Uruchom odczyt Merchant w trybie vendor_read i dopiero potem "
                "twórz kolejkę feedu."
            ),
            source_connectors=[MERCHANT_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            action_ids=action_ids,
            blocked_claims=["feed health", "product approval", "issue count"],
            risk=ActionRisk.medium,
        )

    product_facts = _merchant_health_metric_facts(latest_refresh, facts)
    return MerchantDiagnosticSection(
        id="merchant_feed_health",
        title="Merchant Center: stan produktów i feedu",
        status="ready",
        summary=_metric_sentence(product_facts or facts),
        diagnosis=(
            "WILQ ma metryki Merchant z odczytu. Można ocenić skalę feedu i liczbę "
            "zgłoszonych problemów, ale nie wolno twierdzić, że produkt został naprawiony bez "
            "ActionObject, walidacji i audytu."
        ),
        next_step="Przejdź do kolejki problemów i grupuj je po typie oraz atrybucie.",
        source_connectors=[MERCHANT_CONNECTOR_ID],
        evidence_ids=_unique(fact.evidence_id for fact in product_facts or facts),
        metric_facts=(product_facts or facts)[:10],
        action_ids=action_ids,
        blocked_claims=["approval restored", "revenue recovered", "profit uplift"],
        risk=ActionRisk.medium,
    )


def _issue_queue_section(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    issue_clusters: list[MerchantIssueCluster],
    action_ids: list[str],
) -> MerchantDiagnosticSection:
    issue_facts = [
        fact
        for fact in facts
        if fact.name == "issue_product_count" or "issue_type" in fact.dimensions
    ]
    if not issue_facts and not tactical_items:
        return MerchantDiagnosticSection(
            id="merchant_issue_queue",
            title="Merchant Center: brak kolejki problemów feedu",
            status="missing",
            summary="Brak metryk problemów i pozycji kolejki Merchant.",
            diagnosis=(
                "Nie ma bezpiecznego materiału do kolejki feed triage. WILQ musi "
                "najpierw zebrać typ problemu, atrybut albo metryki statusu produktu."
            ),
            next_step="Odśwież Merchant vendor_read i sprawdź aggregateProductStatuses.",
            source_connectors=[MERCHANT_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            action_ids=action_ids,
            blocked_claims=["feed fix candidate", "product-level fix"],
            risk=ActionRisk.medium,
        )

    cluster_count = _pl_count(
        len(issue_clusters),
        "grupę problemów feedu",
        "grupy problemów feedu",
        "grup problemów feedu",
    )
    tactical_count = _pl_count(
        len(tactical_items),
        "taktykę Merchant",
        "taktyki Merchant",
        "taktyk Merchant",
    )
    issue_fact_count = _pl_count(
        len(issue_facts),
        "metrykę problemu",
        "metryki problemu",
        "metryk problemu",
    )

    return MerchantDiagnosticSection(
        id="merchant_issue_queue",
        title="Merchant Center: kolejka problemów feedu",
        status="ready",
        summary=(
            f"WILQ ma {cluster_count}, {tactical_count} i {issue_fact_count}. "
            "Liczby w grupach są wystąpieniami problemu w raportach, nie gwarancją "
            "unikalnych produktów."
        ),
        diagnosis=(
            "Najbezpieczniejsza praca dla marketera to review problemów po typie "
            "problemu, atrybucie i kontekście widoczności. WILQ nadal nie pokazuje "
            "surowych list produktów."
        ),
        next_step=(
            "Otwórz ActionObject `act_review_merchant_feed_issues` i przygotuj "
            "kolejkę przeglądu."
        ),
        source_connectors=[MERCHANT_CONNECTOR_ID],
        evidence_ids=_unique(
            [
                *(fact.evidence_id for fact in issue_facts),
                *(evidence_id for item in tactical_items for evidence_id in item.evidence_ids),
            ]
        ),
        metric_facts=issue_facts[:10],
        tactical_items=tactical_items[:6],
        action_ids=action_ids,
        blocked_claims=["automatic feed edit", "primary feed overwrite", "approval restored"],
        risk=ActionRisk.medium,
    )


def _merchant_issue_clusters(
    facts: list[MetricFact],
    action_ids: list[str],
) -> list[MerchantIssueCluster]:
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

    clusters: list[MerchantIssueCluster] = []
    action_id = action_ids[0] if action_ids else None
    for key, group_facts in grouped.items():
        issue_type, affected_attribute, country, reporting_context, severity, resolution = key
        product_count = sum(
            int(fact.value)
            for fact in group_facts
            if isinstance(fact.value, int | float)
        )
        sample_product_ids = _sample_product_ids_for_cluster(facts, key)
        sample_titles = _sample_titles_for_cluster(facts, key)
        clusters.append(
            MerchantIssueCluster(
                id=(
                    f"merchant_issue_{_stable_slug(country or 'global')}_"
                    f"{_stable_slug(severity)}_{_stable_slug(issue_type)}_"
                    f"{_stable_slug(affected_attribute or 'attribute_unknown')}_"
                    f"{_stable_slug(reporting_context or 'all_contexts')}_"
                    f"{_stable_slug(resolution or 'resolution_unknown')}"
                ),
                issue_type=issue_type,
                severity=severity,
                resolution=resolution or None,
                affected_attribute=affected_attribute or None,
                country=country or None,
                reporting_context=reporting_context or None,
                product_count=product_count,
                sample_product_ids=sample_product_ids,
                sample_titles=sample_titles,
                sample_unavailable_reason=None
                if sample_product_ids
                else (
                    "Obecny kontrakt odczytu Merchant zwraca wymiary problemu i liczbę "
                    "wystąpień problemu w raportach, ale nie zwraca przykładowych ID "
                    "produktów ani tytułów."
                ),
                source_connectors=[MERCHANT_CONNECTOR_ID],
                evidence_ids=_unique(fact.evidence_id for fact in group_facts),
                blocked_claims=["approval restored", "revenue recovered", "automatic feed edit"],
                action_id=action_id,
                risk=_merchant_cluster_risk(severity, resolution),
                next_step=(
                    "Przejrzyj tę grupę problemu przez ActionObject review; "
                    "najpierw przygotuj podgląd payloadu, bez automatycznej zmiany feedu."
                ),
            )
        )
    return sorted(
        clusters,
        key=lambda cluster: (
            _merchant_severity_rank(cluster.severity),
            -cluster.product_count,
            cluster.issue_type,
        ),
    )


def _sample_product_ids_for_cluster(
    facts: list[MetricFact],
    key: tuple[str, str, str, str, str, str],
) -> list[str]:
    issue_type, affected_attribute, country, reporting_context, severity, resolution = key
    sample_ids = [
        str(fact.value)
        for fact in sorted(
            facts,
            key=lambda fact: fact.dimensions.get("sample_index", ""),
        )
        if fact.name == "sample_product_id"
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
    return _unique(sample_ids)[:10]


def _sample_titles_for_cluster(
    facts: list[MetricFact],
    key: tuple[str, str, str, str, str, str],
) -> list[str]:
    issue_type, affected_attribute, country, reporting_context, severity, resolution = key
    sample_titles = [
        str(fact.value)
        for fact in sorted(
            facts,
            key=lambda fact: fact.dimensions.get("sample_index", ""),
        )
        if fact.name == "sample_product_title"
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
    return _unique(sample_titles)[:10]


def _merchant_attribute_matches(left: str | None, right: str | None) -> bool:
    return _merchant_attribute_key(left) == _merchant_attribute_key(right)


def _merchant_attribute_key(value: str | None) -> str:
    normalized = (value or "").removeprefix("n:").strip().lower()
    return normalized.replace("_", " ")


def _operator_summary(
    decisions: list[MerchantDecisionItem],
    issue_clusters: list[MerchantIssueCluster],
    sections: list[MerchantDiagnosticSection],
    action_ids: list[str],
) -> MerchantOperatorSummary:
    issue_items = [item for section in sections for item in section.tactical_items]
    issue_metric_facts = [
        fact
        for section in sections
        for fact in section.metric_facts
        if fact.name == "issue_product_count"
    ]
    reported_issue_occurrences = (
        sum(cluster.product_count for cluster in issue_clusters)
        if issue_clusters
        else sum(
            int(fact.value)
            for fact in issue_metric_facts
            if isinstance(fact.value, int | float)
        )
    )
    top_issue_items = sorted(
        issue_items,
        key=lambda item: (-item.priority, item.id),
    )[:3]
    return MerchantOperatorSummary(
        title="Co marketer ma zrobić teraz z feedem",
        summary=(
            "WILQ grupuje problemy Merchant po typie i atrybucie. To jest kolejka "
            "przeglądu: można przygotować decyzje i podgląd payloadu, ale nie wolno "
            "obiecać ponownego zatwierdzenia produktu ani automatycznie nadpisać feedu."
        ),
        next_step=(
            "Przejdź przez top decyzje lub klastry problemów, przygotuj review "
            "ActionObject i nie wykonuj zmian feedu bez walidacji oraz zgody operatora."
        ),
        top_decision_ids=[decision.id for decision in decisions[:4]],
        top_issue_cluster_ids=[cluster.id for cluster in issue_clusters[:4]],
        top_tactical_item_ids=[item.id for item in top_issue_items],
        reported_issue_occurrences=reported_issue_occurrences,
        issue_types=_unique(
            [
                *(cluster.issue_type for cluster in issue_clusters),
                *(
                    item.dimensions.get("issue_type")
                    for item in issue_items
                    if item.dimensions.get("issue_type")
                ),
            ]
        ),
        source_connectors=_unique(
            connector for decision in decisions[:4] for connector in decision.source_connectors
        )
        or [MERCHANT_CONNECTOR_ID],
        evidence_ids=_unique(
            [
                *(
                    evidence_id
                    for decision in decisions[:4]
                    for evidence_id in decision.evidence_ids
                ),
                *(
                    evidence_id
                    for cluster in issue_clusters[:4]
                    for evidence_id in cluster.evidence_ids
                ),
            ]
        ),
        action_ids=action_ids,
        blocked_claims=_unique(
            claim for section in sections for claim in section.blocked_claims
        ),
    )


def _merchant_decision_queue(
    *,
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    issue_clusters: list[MerchantIssueCluster],
    action_ids: list[str],
) -> list[MerchantDecisionItem]:
    if not facts and not tactical_items:
        return [
            MerchantDecisionItem(
                id="merchant_block_vendor_read",
                decision_type="block_until_vendor_read",
                status="blocked",
                title="Merchant: odczyt feedu wymagany przed decyzją",
                summary=_merchant_blocker_reason(latest_refresh),
                priority=5,
                metric_tiles={"blockery": 1},
                source_connectors=[MERCHANT_CONNECTOR_ID],
                evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
                action_ids=action_ids,
                blocked_claims=["feed health", "product approval", "issue count"],
                rationale=(
                    "WILQ nie ma aktualnych Merchant metric facts, więc nie może "
                    "uczciwie zbudować kolejki problemów feedu ani ocenić stanu produktów."
                ),
                next_step="Uruchom read-only Merchant vendor_read, potem wróć do /merchant.",
                risk=ActionRisk.medium,
            )
        ]

    decisions = [
        _merchant_decision_from_cluster_group(cluster_group, facts, action_ids)
        for cluster_group in _merchant_decision_cluster_groups(issue_clusters)[:8]
    ]
    if decisions:
        return decisions

    tactical_decisions = [
        _merchant_decision_from_tactical_item(item, action_ids)
        for item in tactical_items[:6]
    ]
    if tactical_decisions:
        return tactical_decisions

    aggregate_decision = _merchant_aggregate_feed_status_decision(
        latest_refresh,
        facts,
        action_ids,
    )
    return [aggregate_decision] if aggregate_decision is not None else []


def _merchant_decision_cluster_groups(
    issue_clusters: list[MerchantIssueCluster],
) -> list[list[MerchantIssueCluster]]:
    grouped: dict[tuple[str, str | None, str | None, str, str | None], list[MerchantIssueCluster]]
    grouped = {}
    for cluster in issue_clusters:
        key = (
            cluster.issue_type,
            cluster.affected_attribute,
            cluster.country,
            cluster.severity,
            cluster.resolution,
        )
        grouped.setdefault(key, []).append(cluster)
    return list(grouped.values())


def _merchant_decision_from_cluster_group(
    clusters: list[MerchantIssueCluster],
    facts: list[MetricFact],
    action_ids: list[str],
) -> MerchantDecisionItem:
    if len(clusters) == 1:
        return _merchant_decision_from_cluster(clusters[0], facts, action_ids)

    primary_cluster = clusters[0]
    attribute = primary_cluster.affected_attribute or "atrybut nieznany"
    issue_type = primary_cluster.issue_type or "unknown_issue"
    display_issue_type = _merchant_display_label(issue_type)
    display_attribute = _merchant_display_label(attribute)
    context_labels = [
        cluster.reporting_context or "ALL_CONTEXTS"
        for cluster in sorted(clusters, key=lambda cluster: cluster.reporting_context or "")
    ]
    max_reported_count = max(cluster.product_count for cluster in clusters)
    reported_occurrences = sum(cluster.product_count for cluster in clusters)
    group_facts = _facts_for_cluster_group(facts, clusters)
    return MerchantDecisionItem(
        id=(
            f"merchant_decision_{_stable_slug(primary_cluster.country or 'global')}_"
            f"{_stable_slug(primary_cluster.severity)}_{_stable_slug(issue_type)}_"
            f"{_stable_slug(attribute)}_"
            f"{_stable_slug(primary_cluster.resolution or 'resolution_unknown')}"
        ),
        decision_type="review_issue_cluster",
        status="ready",
        title=f"Merchant: sprawdź {display_issue_type} / {display_attribute}",
        summary=(
            f"Ten sam problem Merchant występuje w {len(clusters)} raportach: "
            f"{', '.join(context_labels)}. Największy raport pokazuje "
            f"{max_reported_count} zgłoszeń, a suma wystąpień raportowych to "
            f"{reported_occurrences}; to nie jest liczba unikalnych produktów."
        ),
        cluster_id=primary_cluster.id,
        issue_cluster_ids=[cluster.id for cluster in clusters],
        issue_type=issue_type,
        severity=primary_cluster.severity,
        resolution=primary_cluster.resolution,
        affected_attribute=primary_cluster.affected_attribute,
        country=primary_cluster.country,
        reporting_context=None,
        product_count=max_reported_count,
        issue_count=reported_occurrences,
        priority=_merchant_issue_priority(
            primary_cluster.severity,
            primary_cluster.resolution,
            max_reported_count,
        ),
        metric_tiles={
            "max zgłoszeń": max_reported_count,
            "raporty razem": reported_occurrences,
            "konteksty": len(clusters),
        },
        sample_product_ids=_unique(
            sample_id for cluster in clusters for sample_id in cluster.sample_product_ids
        )[:10],
        sample_titles=_unique(
            title for cluster in clusters for title in cluster.sample_titles
        )[:10],
        payload_preview=[
            _merchant_decision_payload_preview(
                cluster=primary_cluster,
                product_count=max_reported_count,
                reported_issue_occurrences=reported_occurrences,
                metric_snapshot={
                    "max_issue_product_count": max_reported_count,
                    "reported_issue_occurrences": reported_occurrences,
                    "reporting_contexts": len(clusters),
                },
                sample_product_ids=_unique(
                    sample_id
                    for cluster in clusters
                    for sample_id in cluster.sample_product_ids
                )[:10],
                sample_titles=_unique(
                    title for cluster in clusters for title in cluster.sample_titles
                )[:10],
                evidence_ids=_unique(
                    evidence_id
                    for cluster in clusters
                    for evidence_id in cluster.evidence_ids
                ),
            )
        ],
        source_connectors=_unique(
            connector for cluster in clusters for connector in cluster.source_connectors
        ),
        evidence_ids=_unique(
            evidence_id for cluster in clusters for evidence_id in cluster.evidence_ids
        ),
        metric_facts=group_facts[:6],
        action_ids=action_ids
        or _unique(cluster.action_id for cluster in clusters if cluster.action_id),
        blocked_claims=_unique(
            claim for cluster in clusters for claim in cluster.blocked_claims
        ),
        rationale=(
            "To jest jedna decyzja operatorska, bo typ problemu, atrybut, kraj, "
            "severity i resolution są takie same. Konteksty raportowania są detalem "
            "triage. Suma raportów nie jest liczbą unikalnych produktów ani gotową "
            "zmianą feedu."
        ),
        next_step=(
            "Przejrzyj problem przez ActionObject review, sprawdź konteksty "
            "raportowania i przygotuj payload preview bez automatycznej zmiany feedu."
        ),
        risk=max((cluster.risk for cluster in clusters), key=_action_risk_rank),
    )


def _merchant_decision_from_cluster(
    cluster: MerchantIssueCluster,
    facts: list[MetricFact],
    action_ids: list[str],
) -> MerchantDecisionItem:
    context = cluster.reporting_context or "wszystkie konteksty"
    attribute = cluster.affected_attribute or "atrybut nieznany"
    issue_type = cluster.issue_type or "unknown_issue"
    display_issue_type = _merchant_display_label(issue_type)
    display_attribute = _merchant_display_label(attribute)
    cluster_facts = _facts_for_cluster(facts, cluster)
    return MerchantDecisionItem(
        id=f"merchant_decision_{cluster.id}",
        decision_type="review_issue_cluster",
        status="ready",
        title=f"Merchant: sprawdź {display_issue_type} / {display_attribute}",
        summary=(
            f"{cluster.product_count} zgłoszeń problemu {cluster.severity}"
            f"/{cluster.resolution or 'brak resolution'} dla {cluster.country or 'global'}"
            f" / {context}."
        ),
        cluster_id=cluster.id,
        issue_cluster_ids=[cluster.id],
        issue_type=issue_type,
        severity=cluster.severity,
        resolution=cluster.resolution,
        affected_attribute=cluster.affected_attribute,
        country=cluster.country,
        reporting_context=cluster.reporting_context,
        product_count=cluster.product_count,
        issue_count=cluster.product_count,
        priority=_merchant_issue_priority(
            cluster.severity,
            cluster.resolution,
            cluster.product_count,
        ),
        metric_tiles={"zgłoszenia": cluster.product_count},
        sample_product_ids=cluster.sample_product_ids,
        sample_titles=cluster.sample_titles,
        payload_preview=[
            _merchant_decision_payload_preview(
                cluster=cluster,
                product_count=cluster.product_count,
                metric_snapshot={"issue_product_count": cluster.product_count},
                sample_product_ids=cluster.sample_product_ids,
                sample_titles=cluster.sample_titles,
                evidence_ids=cluster.evidence_ids,
            )
        ],
        source_connectors=cluster.source_connectors,
        evidence_ids=cluster.evidence_ids,
        metric_facts=cluster_facts[:6],
        action_ids=action_ids or ([cluster.action_id] if cluster.action_id else []),
        blocked_claims=cluster.blocked_claims,
        rationale=(
            "To jest klaster problemu Merchant do ręcznego review. Liczba oznacza "
            "wystąpienia problemu w raportach, nie gwarantowaną liczbę unikalnych "
            "produktów ani gotową zmianę feedu. Przykładowe produkty służą tylko do "
            "ręcznego sprawdzenia problemu."
        ),
        next_step=cluster.next_step,
        risk=cluster.risk,
    )


def _merchant_decision_from_tactical_item(
    item: TacticalQueueItem,
    action_ids: list[str],
) -> MerchantDecisionItem:
    issue_type = item.dimensions.get("issue_type")
    severity = item.dimensions.get("severity")
    product_count = _numeric_metric(item.metric_facts, "issue_product_count")
    display_issue_type = _merchant_display_label(issue_type or "problem feedu")
    display_attribute = _merchant_display_label(
        item.dimensions.get("affected_attribute") or "atrybut"
    )
    return MerchantDecisionItem(
        id=f"merchant_decision_{item.id}",
        decision_type="review_feed_status",
        status="ready",
        title=f"Merchant: sprawdź {display_issue_type} / {display_attribute}",
        summary=item.diagnosis,
        issue_cluster_ids=[],
        issue_type=issue_type,
        severity=severity,
        resolution=item.dimensions.get("resolution"),
        affected_attribute=item.dimensions.get("affected_attribute"),
        country=item.dimensions.get("country"),
        reporting_context=item.dimensions.get("reporting_context"),
        product_count=product_count,
        issue_count=product_count,
        priority=max(1, min(100, item.priority)),
        metric_tiles=_clean_merchant_metric_tiles({"zgłoszenia": product_count}),
        source_connectors=item.source_connectors,
        evidence_ids=item.evidence_ids,
        metric_facts=item.metric_facts[:6],
        action_ids=item.action_ids or action_ids,
        blocked_claims=item.blocked_claims,
        rationale=item.diagnosis,
        next_step=item.next_step,
        risk=item.risk,
    )


def _merchant_decision_payload_preview(
    *,
    cluster: MerchantIssueCluster,
    product_count: int,
    reported_issue_occurrences: int | None = None,
    metric_snapshot: dict[str, int],
    sample_product_ids: list[str],
    sample_titles: list[str],
    evidence_ids: list[str],
) -> dict[str, object]:
    reported_issue_occurrences = reported_issue_occurrences or product_count
    return {
        "id": f"merchant_feed_issue_review_{cluster.id}",
        "preview_contract": MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT,
        "operation_type": "MerchantIssueClusterReview",
        "cluster_id": cluster.id,
        "issue_type": cluster.issue_type,
        "affected_attribute": cluster.affected_attribute,
        "country": cluster.country,
        "reporting_context": cluster.reporting_context,
        "severity": cluster.severity,
        "resolution": cluster.resolution,
        "metric_snapshot": metric_snapshot,
        "sample_products_available": bool(sample_product_ids),
        "sample_product_ids": sample_product_ids,
        "sample_titles": sample_titles,
        "sample_unavailable_reason": None
        if sample_product_ids
        else cluster.sample_unavailable_reason
        or (
            "Obecny kontrakt Merchant zwraca wymiary problemu i liczbę wystąpień, "
            "ale nie zwraca przykładowych ID produktów ani tytułów."
        ),
        "reason": (
            "Review-only podgląd konkretnej decyzji Merchant. WILQ może przygotować "
            "kolejkę review, ale nie może zmienić feedu ani obiecać przywrócenia "
            "approval bez osobnego write/audit contract."
        ),
        "required_validation": [
            "review_issue_type_and_attribute",
            "review_reporting_context",
            "prepare_feed_fix_preview",
            "human_confirm_before_apply",
            "mutation_audit_required",
        ],
        "blocked_claims": [
            "approval restored",
            "revenue recovered",
            "automatic feed edit",
            "primary feed overwrite",
            "feed write",
            "product data mutation",
            "automatic approval fix",
        ],
        "evidence_ids": evidence_ids,
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
        "count_semantics": "reported_issue_occurrences",
        "reported_issue_occurrences": reported_issue_occurrences,
    }


def _merchant_aggregate_feed_status_decision(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    action_ids: list[str],
) -> MerchantDecisionItem | None:
    product_count = _numeric_metric_or_refresh_summary(
        facts,
        latest_refresh,
        "total_products",
    )
    if product_count is None:
        product_count = _numeric_metric_or_refresh_summary(
            facts,
            latest_refresh,
            "active_products",
        )
    issue_count = _numeric_metric_or_refresh_summary(
        facts,
        latest_refresh,
        "item_level_issue_count",
    )
    if issue_count is None:
        issue_count = _numeric_metric_or_refresh_summary(
            facts,
            latest_refresh,
            "merchant_action_issue_count",
        )
    if issue_count is None:
        issue_count = _numeric_metric_or_refresh_summary(
            facts,
            latest_refresh,
            "disapproved_products",
        )
    if product_count is None and issue_count is None:
        return None
    metric_facts = _merchant_health_metric_facts(latest_refresh, facts)
    return MerchantDecisionItem(
        id="merchant_decision_feed_status_review",
        decision_type="review_feed_status",
        status="ready",
        title="Merchant: przejrzyj zgłoszenia problemów feedu",
        summary=(
            f"WILQ widzi {product_count or 0} produktów i {issue_count or 0} "
            "zgłoszeń problemów feedu. Brakuje wymiarowego klastra problemów, "
            "więc to jest kolejka agregatowego review."
        ),
        issue_cluster_ids=[],
        product_count=product_count,
        issue_count=issue_count,
        priority=45,
        metric_tiles=_clean_merchant_metric_tiles(
            {
                "produkty": product_count,
                "zgłoszenia": issue_count,
            }
        ),
        source_connectors=[MERCHANT_CONNECTOR_ID],
        evidence_ids=_unique(
            [
                *(fact.evidence_id for fact in metric_facts),
                *_refresh_or_connector_evidence_ids(latest_refresh),
            ]
        ),
        metric_facts=metric_facts[:6],
        action_ids=action_ids,
        blocked_claims=["approval restored", "revenue recovered", "automatic feed edit"],
        rationale=(
            "Merchant ma aggregate product/feed facts, ale bieżący odczyt nie "
            "dostarcza wymiarowych issue clusters. Marketer może rozpocząć review "
            "ActionObject, ale nie wolno twierdzić, który konkretny atrybut lub "
            "produkt został naprawiony."
        ),
        next_step=(
            "Otwórz `act_review_merchant_feed_issues`, sprawdź payload preview i "
            "zatrzymaj apply do czasu walidacji."
        ),
        risk=ActionRisk.medium,
    )


def _facts_for_cluster(
    facts: list[MetricFact],
    cluster: MerchantIssueCluster,
) -> list[MetricFact]:
    return [
        fact
        for fact in facts
        if fact.name == "issue_product_count"
        and fact.dimensions.get("issue_type") == cluster.issue_type
        and fact.dimensions.get("severity") == cluster.severity
        and (fact.dimensions.get("affected_attribute") or None)
        == cluster.affected_attribute
        and (fact.dimensions.get("country") or None) == cluster.country
        and (fact.dimensions.get("reporting_context") or None)
        == cluster.reporting_context
    ]


def _facts_for_cluster_group(
    facts: list[MetricFact],
    clusters: list[MerchantIssueCluster],
) -> list[MetricFact]:
    return [
        fact
        for cluster in clusters
        for fact in _facts_for_cluster(facts, cluster)
    ]


def _action_risk_rank(risk: ActionRisk) -> int:
    return {
        ActionRisk.low: 0,
        ActionRisk.medium: 1,
        ActionRisk.high: 2,
        ActionRisk.critical: 3,
    }[risk]


def _merchant_display_label(value: str) -> str:
    if value in MERCHANT_ISSUE_LABELS:
        return MERCHANT_ISSUE_LABELS[value]
    if value in MERCHANT_ATTRIBUTE_LABELS:
        return MERCHANT_ATTRIBUTE_LABELS[value]
    return " ".join(value.replace("_", " ").split())


def _merchant_cluster_risk(severity: str, resolution: str | None) -> ActionRisk:
    if severity == "DISAPPROVED":
        return ActionRisk.high
    if resolution == "MERCHANT_ACTION":
        return ActionRisk.medium
    return ActionRisk.low


def _merchant_severity_rank(severity: str) -> int:
    return {"DISAPPROVED": 0, "DEMOTED": 1, "NOT_IMPACTED": 2}.get(severity, 3)


def _merchant_issue_priority(
    severity: str,
    resolution: str | None,
    product_count: int,
) -> int:
    base_priority = {"DISAPPROVED": 10, "DEMOTED": 16, "NOT_IMPACTED": 28}.get(
        severity,
        40,
    )
    if resolution == "MERCHANT_ACTION":
        base_priority -= 4
    if product_count >= 1000:
        base_priority -= 6
    elif product_count >= 100:
        base_priority -= 3
    elif product_count >= 10:
        base_priority -= 1
    return max(5, min(100, base_priority))


def _clean_merchant_metric_tiles(
    values: dict[str, int | float | str | None],
) -> dict[str, int | float | str]:
    return {
        key: value
        for key, value in values.items()
        if value is not None and value != ""
    }


def _stable_slug(value: str) -> str:
    lowered = value.lower()
    chars = [char if char.isalnum() else "_" for char in lowered]
    return "_".join("".join(chars).split("_")) or "unknown"


def _product_action_safety_section(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> MerchantDiagnosticSection:
    return MerchantDiagnosticSection(
        id="merchant_action_safety",
        title="Merchant Center: bezpieczne akcje",
        status="ready" if facts or tactical_items else "blocked",
        summary=(
            "Akcje Merchant pozostają w trybie przygotowania do czasu walidacji "
            "payloadu i audytu."
        ),
        diagnosis=(
            "Zmiany feedu lub produktów mogą wpływać na widoczność i sprzedaż. WILQ "
            "może przygotować kolejkę przeglądu, ale nie może zmieniać głównego feedu ani "
            "twierdzić, że naprawił produkty bez obsługi apply."
        ),
        next_step=(
            "Waliduj ActionObject, pokaż podgląd payloadu i zatrzymaj apply "
            "do jawnego potwierdzenia."
        ),
        source_connectors=[MERCHANT_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        action_ids=action_ids,
        blocked_claims=["feed write", "product data mutation", "automatic approval fix"],
        risk=ActionRisk.medium,
    )


def _facts_by_names(facts: list[MetricFact], names: set[str]) -> list[MetricFact]:
    return [fact for fact in facts if fact.name in names]


def _merchant_health_metric_facts(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
) -> list[MetricFact]:
    summary_facts = _metric_facts_from_refresh_summary(
        latest_refresh,
        MERCHANT_HEALTH_METRIC_NAMES,
    )
    if summary_facts:
        return summary_facts
    return _dedupe_metric_facts(_facts_by_names(facts, MERCHANT_HEALTH_METRIC_NAMES))


def _metric_facts_from_refresh_summary(
    latest_refresh: ConnectorRefreshRun | None,
    names: set[str],
) -> list[MetricFact]:
    if latest_refresh is None:
        return []
    evidence_id = (
        latest_refresh.evidence_ids[-1]
        if latest_refresh.evidence_ids
        else connector_evidence_id(MERCHANT_CONNECTOR_ID)
    )
    facts: list[MetricFact] = []
    for name in names:
        value = latest_refresh.metric_summary.get(name)
        if value is None:
            continue
        facts.append(
            MetricFact(
                name=name,
                value=value,
                period="connector_refresh",
                source_connector=MERCHANT_CONNECTOR_ID,
                evidence_id=evidence_id,
            )
        )
    return sorted(facts, key=lambda fact: fact.name)


def _dedupe_metric_facts(facts: list[MetricFact]) -> list[MetricFact]:
    seen: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
    result: list[MetricFact] = []
    for fact in facts:
        key = (fact.name, tuple(sorted(fact.dimensions.items())))
        if key in seen:
            continue
        seen.add(key)
        result.append(fact)
    return result


def _numeric_metric(facts: list[MetricFact], name: str) -> int | None:
    for fact in facts:
        if fact.name == name and isinstance(fact.value, int | float):
            return int(fact.value)
    return None


def _numeric_metric_or_refresh_summary(
    facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
    name: str,
) -> int | None:
    value = _numeric_metric(facts, name)
    if value is not None:
        return value
    if latest_refresh is None:
        return None
    summary_value = latest_refresh.metric_summary.get(name)
    if isinstance(summary_value, int | float):
        return int(summary_value)
    return None


def _merchant_blocker_reason(latest_refresh: ConnectorRefreshRun | None) -> str:
    if latest_refresh and latest_refresh.errors:
        return latest_refresh.errors[0]
    if latest_refresh and latest_refresh.summary:
        return latest_refresh.summary
    return "Brak wykonanego Merchant vendor_read."


def _refresh_or_connector_evidence_ids(latest_refresh: ConnectorRefreshRun | None) -> list[str]:
    if latest_refresh:
        return latest_refresh.evidence_ids
    return [connector_evidence_id(MERCHANT_CONNECTOR_ID)]


def _metric_sentence(facts: list[MetricFact]) -> str:
    samples = ", ".join(f"{fact.name}={fact.value}" for fact in facts[:6])
    return f"Metryki Merchant: {samples}."


def _pl_count(count: int, one: str, few: str, many: str) -> str:
    absolute = abs(count)
    last_digit = absolute % 10
    last_two_digits = absolute % 100
    if absolute == 1:
        form = one
    elif 2 <= last_digit <= 4 and not 12 <= last_two_digits <= 14:
        form = few
    else:
        form = many
    return f"{count} {form}"


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values
