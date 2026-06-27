from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Literal

from wilq.actions.service import MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT, list_actions
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.briefing.merchant_labels import (
    MERCHANT_ATTRIBUTE_LABELS,
    MERCHANT_ISSUE_LABELS,
    MERCHANT_REPORTING_CONTEXT_LABELS,
    MERCHANT_RESOLUTION_LABELS,
    MERCHANT_SEVERITY_LABELS,
)
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
    MerchantPriceImpactReadiness,
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
    "zwrot z reklam na poziomie produktu",
    "odzyskany przychód produktu",
    "efekt naprawy produktu",
    "skalowanie produktu w Shopping/PMax",
    "ponowne zatwierdzenie produktu",
    "zapis do feedu",
]
MERCHANT_KNOWLEDGE_CARD_IDS = [
    "card_merchant_feed_optimization_playbook",
    "card_google_ads_pmax_playbook",
]
MERCHANT_EXPERT_RULE_IDS = [
    "merchant_feed_rules_v1",
    "merchant_product_diagnostics_v1",
]
MERCHANT_PRODUCT_STATE_REVIEW_PREVIEW_CONTRACT = (
    "merchant_product_state_review_preview_v1"
)
MERCHANT_SUPPLEMENTAL_FEED_REVIEW_PREVIEW_CONTRACT = (
    "merchant_supplemental_feed_review_preview_v1"
)
MERCHANT_PRICE_IMPACT_PREVIEW_CONTRACT = "merchant_price_impact_readiness_preview_v1"
MERCHANT_PRICE_IMPACT_REQUIRED_READ_CONTRACTS = [
    "google_ads_shopping_product_current_price",
    "google_ads_shopping_product_price_history",
    "merchant_price_change_event_or_snapshot",
    "google_ads_or_ga4_product_performance_window",
]
MERCHANT_REQUIRED_VALIDATION_LABELS = {
    "confirm_before_after_performance_window": "potwierdź okno porównania sprzed i po zmianie",
    "confirm_price_change_date": "potwierdź datę zmiany ceny",
    "confirm_price_snapshot_history": "potwierdź historię ceny",
    "confirm_source_of_truth_values": "potwierdź wartości ze źródła prawdy",
    "exclude_stock_or_approval_confounders": "wyklucz wpływ stanu magazynu lub zatwierdzenia",
    "human_confirm_before_apply": "człowiek potwierdza przed zapisem",
    "human_review_before_action": "człowiek sprawdza przed działaniem",
    "mutation_audit_required": "wymagany audyt zapisu",
    "prepare_feed_fix_preview": "przygotuj podgląd zmian feedu",
    "prepare_supplemental_feed_draft_preview": "przygotuj podgląd uzupełnienia feedu",
    "prepare_supplemental_feed_preview_before_any_mutation": (
        "przygotuj podgląd uzupełnienia feedu przed zapisem"
    ),
    "review_ads_product_status": "sprawdź status produktu z Google Ads",
    "review_issue_type_and_attribute": "sprawdź typ problemu i atrybut",
    "review_merchant_issue_context": "sprawdź kontekst problemu Merchant",
    "review_product_identity_mapping": "sprawdź powiązanie produktu",
    "review_reporting_context": "sprawdź kontekst raportowania",
    "require_human_confirm_before_apply": "człowiek potwierdza przed zapisem",
    "validate_change_values": "sprawdź wartości przed zapisem",
}
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
GOOGLE_ADS_PRODUCT_STATE_FACT_NAMES = {
    "shopping_product_state_available",
    "shopping_product_status",
    "shopping_product_availability",
    "shopping_product_price_micros",
}
MERCHANT_HEALTH_METRIC_NAMES = {
    "total_products",
    "active_products",
    "disapproved_products",
    "expiring_products",
    "item_level_issue_count",
    "merchant_action_issue_count",
}
MERCHANT_STALE_AFTER_HOURS = 48

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
    price_impact_readiness = _merchant_price_impact_readiness(
        product_performance_readiness
    )
    price_impact_readiness = price_impact_readiness.model_copy(
        update={
            "payload_preview": [
                _merchant_payload_preview_with_operator_labels(preview)
                for preview in price_impact_readiness.payload_preview
            ]
        }
    )
    decision_queue = _merchant_decisions_with_product_state_review(
        decision_queue,
        product_performance_readiness,
        action_ids,
    )
    decision_queue = _merchant_decisions_with_price_impact_review(
        decision_queue,
        price_impact_readiness,
        action_ids,
    )
    decision_queue = _merchant_decisions_with_lineage(decision_queue)
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
        price_impact_readiness=price_impact_readiness,
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
    return _latest_connector_refresh(MERCHANT_CONNECTOR_ID)


def _latest_connector_refresh(connector_id: str) -> ConnectorRefreshRun | None:
    runs = list_connector_refresh_runs(connector_id=connector_id)
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
            summary="Brak zapisanego odczytu danych Merchant Center.",
            next_step="Uruchom odczyt danych Merchant przed oceną aktualnego stanu feedu.",
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
                "Napraw blocker odczytu i uruchom ponownie odczyt danych Merchant przed "
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
                f"Ostatni odczyt danych Merchant ma około {age_hours:.1f}h. "
                "To wystarcza do przeglądu nieświeżych danych, ale nie do obietnic o bieżącym stanie feedu."
            ),
            next_step=(
                "Uruchom odczyt danych Merchant, jeśli pytanie dotyczy "
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
            f"Ostatni odczyt danych Merchant ma około {age_hours:.1f}h i mieści się "
            f"w progu {MERCHANT_STALE_AFTER_HOURS}h."
        ),
        next_step="Można użyć danych do kolejki sprawdzenia bez dodatkowego odświeżenia.",
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
                        "WILQ może przygotować kolejkę sprawdzenia po klastrach, ale nie listę "
                        "konkretnych produktów do edycji."
                    ),
                    next_step=(
                        "Dodać osobny read contract dla bezpiecznych przykładów produktów "
                        "albo otworzyć Merchant Center podczas sprawdzenia."
                    ),
                    blocked_claims=[
                        "naprawa pojedynczego produktu",
                        "zapis do feedu",
                        "automatyczna zmiana feedu",
                    ],
                )
            )
        unknowns.append(
            MerchantUnknownFact(
                id="merchant_unique_product_count_unknown",
                title="Zgłoszenia raportowe nie są liczbą unikalnych produktów",
                reason=(
                    "Ten sam problem może wystąpić w kilku kontekstach raportowania, "
                    "więc suma raportów może liczyć ten sam produkt więcej niż raz."
                ),
                impact=(
                    "Kolejka decyzji musi używać największej liczby zgłoszeń jako skali i traktować "
                    "sumę raportów wyłącznie jako szczegóły raportowania."
                ),
                next_step=(
                    "Grupować decyzje po kolejce decyzji, a klastry problemów pokazywać "
                    "jako szczegóły raportowania."
                ),
                blocked_claims=[
                    "liczba unikalnych produktów",
                    "ponowne zatwierdzenie produktu",
                ],
            )
        )
    if product_performance_readiness.status == "blocked":
        unknowns.append(
            MerchantUnknownFact(
                id="merchant_product_performance_join_missing",
                title="Brak połączenia produktów Merchant z Ads/GA4",
                reason=(
                    "WILQ ma próbki ID produktów Merchant albo kolejkę problemów feedu, "
                    "ale nie ma dopasowanych faktów Ads/GA4 z ID produktu dla "
                    "tych produktów."
                ),
                impact=(
                    "Można prowadzić przegląd problemów feedu, ale nie wolno twierdzić, "
                    "które produkty mają zwrot z reklam, przychód, koszt albo efekt naprawy."
                ),
                next_step=(
                    "Dodać kontrakty odczytu skuteczności produktu dla Google Ads "
                    "Shopping/PMax i GA4 ecommerce, z jawnie wspólnym kluczem produktu."
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
                "Odczyt Merchant zwraca przykładowe ID produktów dla części problemów. "
                "Tytuły są dostępne tylko wtedy, gdy wzbogacenie products.list je zwróci."
            ),
            next_step=(
                "Użyj próbek do sprawdzenia. Dla tytułów/SKU/statusów dodaj odczyt "
                "products.list/productStatus albo reports.search product_view."
            ),
            blocked_claims=["zapis do feedu", "automatyczna zmiana feedu"],
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
                "Obecny kontrakt odczytu Merchant daje zagregowaną kolejkę problemów, ale nie "
                "zwraca ID produktów, SKU ani tytułów do pracy produkt-po-produkcie."
            ),
            next_step=(
                "Dodać osobny kontrakt odczytu przez products.list/productStatus "
                "albo reports.search product_view z filtrem issue, zanim WILQ pokaże "
                "konkretne produkty do poprawy."
            ),
            blocked_claims=[
                "naprawa pojedynczego produktu",
                "zapis do feedu",
                "automatyczna zmiana feedu",
            ],
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
        next_step="Najpierw uruchom odczyt danych Merchant.",
        blocked_claims=[
            "naprawa pojedynczego produktu",
            "zapis do feedu",
            "automatyczna zmiana feedu",
        ],
    )


def _merchant_product_performance_readiness(
    *,
    issue_clusters: list[MerchantIssueCluster],
    product_sample_readiness: MerchantProductSampleReadiness,
    product_metric_facts_by_connector: dict[str, list[MetricFact]] | None = None,
) -> MerchantProductPerformanceReadiness:
    sample_product_ids = product_sample_readiness.sample_product_ids
    sample_title_map = _merchant_sample_title_map(issue_clusters)
    sample_context_map = _merchant_sample_context_map(issue_clusters)
    merchant_evidence_ids = _unique(
        evidence_id for cluster in issue_clusters for evidence_id in cluster.evidence_ids
    )
    use_live_contract_status = product_metric_facts_by_connector is None
    product_metric_facts_by_connector = (
        product_metric_facts_by_connector
        if product_metric_facts_by_connector is not None
        else _product_performance_metric_facts_by_connector(sample_product_ids)
    )
    ads_shopping_contract_ready, ads_shopping_lookback_days = (
        _google_ads_shopping_product_read_contract_status()
        if use_live_contract_status
        else (False, None)
    )
    ads_product_facts = _product_scoped_metric_facts(
        product_metric_facts_by_connector.get(GOOGLE_ADS_CONNECTOR_ID, [])
    )
    ads_product_state_facts = [
        fact for fact in ads_product_facts if fact.name in GOOGLE_ADS_PRODUCT_STATE_FACT_NAMES
    ]
    ads_product_performance_facts = [
        fact
        for fact in ads_product_facts
        if fact.name not in GOOGLE_ADS_PRODUCT_STATE_FACT_NAMES
    ]
    ga4_product_facts = _product_scoped_metric_facts(
        product_metric_facts_by_connector.get(GA4_CONNECTOR_ID, [])
    )
    ads_facts_by_product_id = _metric_facts_by_product_id(ads_product_facts)
    ga4_facts_by_product_id = _metric_facts_by_product_id(ga4_product_facts)

    performance_rows: list[MerchantProductPerformanceRow] = []
    for product_id in sample_product_ids:
        ads_facts = _facts_for_product_id(ads_facts_by_product_id, product_id)
        ga4_facts = _facts_for_product_id(ga4_facts_by_product_id, product_id)
        if not ads_facts and not ga4_facts:
            continue
        sample_context = _sample_context_for_product_id(sample_context_map, product_id)
        price_fact = _metric_fact_by_name(ads_facts, ["shopping_product_price_micros"])
        row = MerchantProductPerformanceRow(
            product_id=product_id,
            sample_title=sample_title_map.get(product_id),
            issue_type=sample_context.issue_type if sample_context is not None else None,
            issue_type_label=_merchant_display_label(sample_context.issue_type)
            if sample_context is not None
            else None,
            affected_attribute=(
                sample_context.affected_attribute if sample_context is not None else None
            ),
            affected_attribute_label=_merchant_display_label(
                sample_context.affected_attribute or "atrybut nieznany"
            )
            if sample_context is not None
            else None,
            country=sample_context.country if sample_context is not None else None,
            reporting_context=(
                sample_context.reporting_context if sample_context is not None else None
            ),
            reporting_context_label=_merchant_reporting_context_label(
                sample_context.reporting_context
            )
            if sample_context is not None
            else None,
            source_connectors=_unique(
                fact.source_connector for fact in [*ads_facts, *ga4_facts]
            ),
            evidence_ids=_unique(fact.evidence_id for fact in [*ads_facts, *ga4_facts]),
            ads_product_title=_dimension_value(ads_facts, ["product_title"]),
            ads_product_status=_text_metric_value(
                ads_facts,
                ["shopping_product_status"],
            )
            or _dimension_value(ads_facts, ["product_status"]),
            ads_product_availability=_text_metric_value(
                ads_facts,
                ["shopping_product_availability"],
            )
            or _dimension_value(ads_facts, ["product_availability"]),
            ads_product_price_micros=_int_metric_value(
                ads_facts,
                ["shopping_product_price_micros"],
            ),
            ads_product_currency_code=_dimension_value(ads_facts, ["currency_code"]),
            ads_product_price_collected_at=(
                price_fact.collected_at if price_fact is not None else None
            ),
            ads_product_previous_price_micros=_int_previous_metric_value(price_fact),
            ads_product_previous_price_collected_at=(
                price_fact.previous_collected_at if price_fact is not None else None
            ),
            ads_product_previous_price_evidence_id=(
                price_fact.previous_evidence_id if price_fact is not None else None
            ),
            ads_product_price_delta_micros=_int_delta_metric_value(price_fact),
            ads_product_price_delta_percent=_delta_percent_metric_value(price_fact),
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
                    "blocked_claims": MERCHANT_PRODUCT_PERFORMANCE_BLOCKED_CLAIMS,
                }
            )
        )

    current_read_contracts = ["merchant_aggregate_product_statuses"]
    if ads_product_performance_facts:
        current_read_contracts.append("google_ads_product_metric_facts")
    if ads_product_state_facts:
        current_read_contracts.append("google_ads_shopping_product_state")
    elif ads_shopping_contract_ready:
        current_read_contracts.append("google_ads_shopping_product_performance")
    if ga4_product_facts:
        current_read_contracts.append("ga4_item_metric_facts")
    missing_read_contracts = _merchant_product_performance_missing_read_contracts(
        sample_product_ids=sample_product_ids,
        current_read_contracts=current_read_contracts,
    )

    if performance_rows:
        rows_with_metrics = [
            row
            for row in performance_rows
            if _has_product_performance_metric(row)
        ]
        if rows_with_metrics:
            status: Literal["ready", "blocked"] = "ready"
            summary = (
                "WILQ ma dopasowane fakty produktu dla części próbek Merchant. "
                "To wspiera przegląd produktu z metrykami Ads/GA4, ale nie oznacza "
                "automatycznej naprawy feedu ani efektu po zmianie."
            )
            next_step = (
                "Użyj wierszy produktu do ustalenia kolejności przeglądu. Do obietnic o efekcie "
                "naprawy potrzebny jest osobny audyt sprzed i po zmianie."
            )
        else:
            status = "blocked"
            summary = (
                "WILQ ma dopasowany stan produktu z Ads dla części próbek Merchant, "
                "ale nie ma jeszcze metryk skuteczności Ads/GA4 dla tych produktów."
            )
            next_step = (
                "Użyj wierszy stanu produktu tylko do potwierdzenia mapowania ID. Zwrot z reklam "
                "na poziomie produktu, odzyskany przychód i efekt naprawy pozostają zablokowane "
                "do czasu metryk skuteczności albo audytu sprzed i po zmianie."
            )
        return MerchantProductPerformanceReadiness(
            status=status,
            joined_product_count=len(performance_rows),
            merchant_sample_count=len(sample_product_ids),
            ads_product_fact_count=len(ads_product_facts),
            ga4_product_fact_count=len(ga4_product_facts),
            current_read_contracts=current_read_contracts,
            required_read_contracts=MERCHANT_PRODUCT_PERFORMANCE_REQUIRED_READ_CONTRACTS,
            missing_read_contracts=missing_read_contracts,
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
            summary=summary,
            next_step=next_step,
            blocked_claims=MERCHANT_PRODUCT_PERFORMANCE_BLOCKED_CLAIMS,
        )

    blocked_reason = _product_performance_blocked_reason(
        sample_product_ids=sample_product_ids,
        ads_product_facts=ads_product_facts,
        ga4_product_facts=ga4_product_facts,
        ads_shopping_contract_ready=ads_shopping_contract_ready,
        ads_shopping_lookback_days=ads_shopping_lookback_days,
    )
    next_step = _product_performance_next_step(
        sample_product_ids=sample_product_ids,
        ads_product_facts=ads_product_facts,
        ga4_product_facts=ga4_product_facts,
        ads_shopping_contract_ready=ads_shopping_contract_ready,
        ads_shopping_lookback_days=ads_shopping_lookback_days,
    )
    return MerchantProductPerformanceReadiness(
        status="blocked",
        joined_product_count=0,
        merchant_sample_count=len(sample_product_ids),
        ads_product_fact_count=len(ads_product_facts),
        ga4_product_fact_count=len(ga4_product_facts),
        current_read_contracts=current_read_contracts,
        required_read_contracts=MERCHANT_PRODUCT_PERFORMANCE_REQUIRED_READ_CONTRACTS,
        missing_read_contracts=missing_read_contracts,
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
        next_step=next_step,
        blocked_claims=MERCHANT_PRODUCT_PERFORMANCE_BLOCKED_CLAIMS,
    )


def _merchant_product_performance_missing_read_contracts(
    *,
    sample_product_ids: list[str],
    current_read_contracts: list[str],
) -> list[str]:
    missing_contracts: list[str] = []
    if not sample_product_ids:
        missing_contracts.append("merchant_product_id_join_key")
    if not any(
        contract in current_read_contracts
        for contract in (
            "google_ads_product_metric_facts",
            "google_ads_shopping_product_performance",
        )
    ):
        missing_contracts.append("google_ads_shopping_product_performance")
    if "ga4_item_metric_facts" not in current_read_contracts:
        missing_contracts.append("ga4_item_product_performance")
    return missing_contracts


def _merchant_price_impact_readiness(
    product_performance_readiness: MerchantProductPerformanceReadiness,
) -> MerchantPriceImpactReadiness:
    rows = product_performance_readiness.performance_rows
    rows_with_current_price = [
        row for row in rows if row.ads_product_price_micros is not None
    ]
    rows_with_previous_price = [
        row
        for row in rows_with_current_price
        if row.ads_product_previous_price_micros is not None
        and row.ads_product_previous_price_collected_at is not None
    ]
    rows_with_price_change = [
        row for row in rows_with_previous_price if _has_price_change(row)
    ]
    rows_with_unchanged_price_history = [
        row for row in rows_with_previous_price if not _has_price_change(row)
    ]
    rows_with_performance = [row for row in rows if _has_product_performance_metric(row)]
    current_read_contracts = _merchant_price_impact_current_read_contracts(
        rows_with_current_price=rows_with_current_price,
        rows_with_previous_price=rows_with_previous_price,
        rows_with_price_change=rows_with_price_change,
        rows_with_performance=rows_with_performance,
    )
    missing_read_contracts = [
        contract
        for contract in MERCHANT_PRICE_IMPACT_REQUIRED_READ_CONTRACTS
        if contract not in current_read_contracts
    ]
    status: Literal["ready", "blocked"] = (
        "ready" if not missing_read_contracts else "blocked"
    )
    summary = _merchant_price_impact_summary(
        status=status,
        rows_with_current_price=len(rows_with_current_price),
        rows_with_previous_price=len(rows_with_previous_price),
        rows_with_price_change=len(rows_with_price_change),
        rows_with_unchanged_price_history=len(rows_with_unchanged_price_history),
        rows_with_performance=len(rows_with_performance),
    )
    next_step = (
        "Jeżeli produkt ma cenę bieżącą, historię ceny i metryki skuteczności, "
        "przygotuj porównanie sprzed i po zmianie. W przeciwnym razie pokaż brakujące "
        "kontrakty i nie oceniaj wpływu ceny."
    )
    return MerchantPriceImpactReadiness(
        status=status,
        products_with_current_price=len(rows_with_current_price),
        products_with_previous_price=len(rows_with_previous_price),
        products_with_price_change=len(rows_with_price_change),
        products_with_unchanged_price_history=len(rows_with_unchanged_price_history),
        products_with_performance_metrics=len(rows_with_performance),
        current_read_contracts=current_read_contracts,
        required_read_contracts=MERCHANT_PRICE_IMPACT_REQUIRED_READ_CONTRACTS,
        missing_read_contracts=missing_read_contracts,
        payload_preview=[
            _merchant_price_impact_payload_preview(
                rows=rows_with_current_price[:8],
                evidence_ids=product_performance_readiness.evidence_ids,
                missing_read_contracts=missing_read_contracts,
            )
        ],
        source_connectors=product_performance_readiness.source_connectors,
        evidence_ids=product_performance_readiness.evidence_ids,
        summary=summary,
        next_step=next_step,
        blocked_claims=[
            "wpływ zmiany ceny",
            "zwrot z reklam na poziomie produktu",
            "opłacalność produktu",
            "odzyskany przychód",
            "ponowne zatwierdzenie produktu",
            "zapis do feedu",
        ],
    )


def _merchant_price_impact_current_read_contracts(
    *,
    rows_with_current_price: list[MerchantProductPerformanceRow],
    rows_with_previous_price: list[MerchantProductPerformanceRow],
    rows_with_price_change: list[MerchantProductPerformanceRow],
    rows_with_performance: list[MerchantProductPerformanceRow],
) -> list[str]:
    contracts: list[str] = []
    if rows_with_current_price:
        contracts.append("google_ads_shopping_product_current_price")
    if rows_with_previous_price:
        contracts.append("google_ads_shopping_product_price_history")
    if rows_with_price_change:
        contracts.append("merchant_price_change_event_or_snapshot")
    if rows_with_performance:
        contracts.append("google_ads_or_ga4_product_performance_window")
    return contracts


def _merchant_price_impact_summary(
    *,
    status: Literal["ready", "blocked"],
    rows_with_current_price: int,
    rows_with_previous_price: int,
    rows_with_price_change: int,
    rows_with_unchanged_price_history: int,
    rows_with_performance: int,
) -> str:
    if status == "ready":
        return (
            "WILQ ma bieżącą cenę, historię ceny i metryki skuteczności dla "
            "części produktów Merchant. To pozwala przygotować przegląd "
            "sprzed i po zmianie, ale nadal bez automatycznej obietnicy wpływu ceny."
        )
    if rows_with_current_price and not rows_with_previous_price:
        return (
            f"WILQ widzi bieżącą cenę Ads dla {rows_with_current_price} "
            "zmapowanych produktów, ale nie ma historii ceny ani zdarzenia "
            "zmiany ceny. Price impact pozostaje zablokowany."
        )
    if rows_with_previous_price and not rows_with_price_change:
        return (
            f"WILQ widzi historię ceny dla {rows_with_previous_price} produktów, "
            f"w tym {rows_with_unchanged_price_history} bez wykrytej zmiany ceny. "
            "Wpływ ceny pozostaje zablokowany do czasu faktycznego zdarzenia "
            "zmiany ceny i okna skuteczności."
        )
    if rows_with_previous_price and not rows_with_performance:
        return (
            f"WILQ widzi zmianę ceny dla {rows_with_price_change} produktów, "
            "ale nie ma dopasowanych metryk skuteczności w oknie sprzed i po zmianie."
        )
    return (
        "WILQ nie ma wystarczających faktów ceny i skuteczności, żeby ocenić wpływ "
        "ceny produktu."
    )


def _merchant_price_impact_payload_preview(
    *,
    rows: list[MerchantProductPerformanceRow],
    evidence_ids: list[str],
    missing_read_contracts: list[str],
) -> dict[str, object]:
    return {
        "id": "merchant_price_impact_readiness_preview",
        "preview_contract": MERCHANT_PRICE_IMPACT_PREVIEW_CONTRACT,
        "operation_type": "MerchantPriceImpactReadinessReview",
        "products": [
            {
                "product_id": row.product_id,
                "title": row.sample_title or row.ads_product_title,
                "current_price_micros": row.ads_product_price_micros,
                "current_price_collected_at": _iso_datetime(
                    row.ads_product_price_collected_at
                ),
                "previous_price_micros": row.ads_product_previous_price_micros,
                "previous_price_collected_at": _iso_datetime(
                    row.ads_product_previous_price_collected_at
                ),
                "previous_price_evidence_id": row.ads_product_previous_price_evidence_id,
                "price_delta_micros": row.ads_product_price_delta_micros,
                "price_delta_percent": row.ads_product_price_delta_percent,
                "currency_code": row.ads_product_currency_code,
                "has_price_snapshot_history": (
                    row.ads_product_previous_price_micros is not None
                    and row.ads_product_previous_price_collected_at is not None
                ),
                "has_price_change": _has_price_change(row),
                "has_product_performance_metrics": _has_product_performance_metric(row),
                "issue_type": row.issue_type,
                "affected_attribute": row.affected_attribute,
            }
            for row in rows
        ],
        "missing_read_contracts": missing_read_contracts,
        "reason": (
            "Readiness preview dla price-impact. To nie jest rekomendacja zmiany "
            "ceny ani dowód wpływu na sprzedaż."
        ),
        "required_validation": [
            "confirm_price_snapshot_history",
            "confirm_price_change_date",
            "confirm_before_after_performance_window",
            "exclude_stock_or_approval_confounders",
            "human_review_before_action",
        ],
        "blocked_claims": [
            "wpływ zmiany ceny",
            "zwrot z reklam na poziomie produktu",
            "opłacalność produktu",
            "odzyskany przychód",
            "ponowne zatwierdzenie produktu",
            "zapis do feedu",
        ],
        "evidence_ids": evidence_ids,
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
    }


def _google_ads_shopping_product_read_contract_status() -> tuple[bool, int | None]:
    latest_refresh = _latest_connector_refresh(GOOGLE_ADS_CONNECTOR_ID)
    if latest_refresh is None or latest_refresh.status != ConnectorRefreshStatus.completed:
        return False, None
    if latest_refresh.metric_summary.get("shopping_product_performance_status") != "ready":
        return False, None
    lookback = latest_refresh.metric_summary.get("shopping_product_performance_lookback_days")
    return True, int(lookback) if isinstance(lookback, int | float) else None


def _product_performance_blocked_reason(
    *,
    sample_product_ids: list[str],
    ads_product_facts: list[MetricFact],
    ga4_product_facts: list[MetricFact],
    ads_shopping_contract_ready: bool,
    ads_shopping_lookback_days: int | None,
) -> str:
    if not sample_product_ids:
        return (
            "Odczyt Merchant nie daje próbek ID produktów, więc WILQ nie ma klucza "
            "do połączenia problemów feedu z Ads/GA4."
        )
    if ads_shopping_contract_ready and not ads_product_facts:
        lookback_label = (
            f" z lookbackiem {ads_shopping_lookback_days} dni"
            if ads_shopping_lookback_days is not None
            else ""
        )
        return (
            "Odczyt Merchant zwraca próbki ID produktów, GA4 ma fakty produktu, a Ads "
            f"ma gotowy widok skuteczności zakupowej{lookback_label}, ale bieżący "
            "odczyt Ads zwrócił 0 wierszy skuteczności produktu. WILQ nie ma więc "
            "dopasowanych faktów Ads dla próbek Merchant."
        )
    if ga4_product_facts and not ads_product_facts:
        return (
            "Odczyt Merchant zwraca próbki ID produktów i GA4 ma fakty produktu, ale WILQ "
            "nie ma dopasowanych faktów produktu z Ads dla tych ID."
        )
    return (
        "Odczyt Merchant zwraca próbki ID produktów, ale WILQ nie ma dopasowanych "
        "faktów produktu z Ads albo GA4 dla tych ID."
    )


def _product_performance_next_step(
    *,
    sample_product_ids: list[str],
    ads_product_facts: list[MetricFact],
    ga4_product_facts: list[MetricFact],
    ads_shopping_contract_ready: bool,
    ads_shopping_lookback_days: int | None,
) -> str:
    if not sample_product_ids:
        return (
            "Dodać próbki produktów Merchant z ID produktu lub SKU, zanim WILQ "
            "spróbuje łączyć feed ze skutecznością."
        )
    if ads_shopping_contract_ready and not ads_product_facts:
        if ads_shopping_lookback_days is not None and ads_shopping_lookback_days >= 90:
            return (
                "Dodaj aktualny `shopping_product` state read albo mapowanie Merchant "
                "offer ID -> Ads product_item_id, zamiast obiecywać skuteczność produktu "
                "z pustej historii emisji."
            )
        return (
            "Sprawdź, czy produkty miały emisję w Ads w ostatnich 30 dniach; jeśli "
            "nie, dodaj dłuższy lookback albo aktualny `shopping_product` state read "
            "zamiast obiecywać skuteczność produktu."
        )
    if ga4_product_facts and not ads_product_facts:
        return (
            "Dodać albo odświeżyć Ads Shopping/PMax product facts oraz utrzymać "
            "wspólny product_id/item_id jako join key."
        )
    return (
        "Dodać skuteczność produktu dla Google Ads Shopping/PMax i GA4 "
        "item ecommerce oraz utrzymać wspólny product_id/item_id jako join key."
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


def _merchant_sample_context_map(
    issue_clusters: list[MerchantIssueCluster],
) -> dict[str, MerchantIssueCluster]:
    context_by_product_id: dict[str, MerchantIssueCluster] = {}
    for cluster in issue_clusters:
        for product_id in cluster.sample_product_ids:
            for alias in _product_id_aliases(product_id):
                context_by_product_id.setdefault(alias, cluster)
    return context_by_product_id


def _sample_context_for_product_id(
    context_by_product_id: dict[str, MerchantIssueCluster],
    product_id: str,
) -> MerchantIssueCluster | None:
    for alias in _product_id_aliases(product_id):
        context = context_by_product_id.get(alias)
        if context is not None:
            return context
    return None


def _product_scoped_metric_facts(facts: list[MetricFact]) -> list[MetricFact]:
    return [fact for fact in facts if _metric_fact_product_id(fact) is not None]


def _metric_facts_by_product_id(
    facts: list[MetricFact],
) -> dict[str, list[MetricFact]]:
    facts_by_product_id: dict[str, list[MetricFact]] = {}
    for fact in facts:
        for product_id in _metric_fact_product_id_aliases(fact):
            facts_by_product_id.setdefault(product_id, []).append(fact)
    return facts_by_product_id


def _facts_for_product_id(
    facts_by_product_id: dict[str, list[MetricFact]],
    product_id: str,
) -> list[MetricFact]:
    facts: list[MetricFact] = []
    seen: set[tuple[str, str, str]] = set()
    for alias in _product_id_aliases(product_id):
        for fact in facts_by_product_id.get(alias, []):
            key = (fact.name, fact.evidence_id, repr(sorted(fact.dimensions.items())))
            if key in seen:
                continue
            seen.add(key)
            facts.append(fact)
    return facts


def _metric_fact_product_id(fact: MetricFact) -> str | None:
    aliases = _metric_fact_product_id_aliases(fact)
    return aliases[0] if aliases else None


def _metric_fact_product_id_aliases(fact: MetricFact) -> list[str]:
    aliases: list[str] = []
    for key in PRODUCT_JOIN_DIMENSION_KEYS:
        value = fact.dimensions.get(key)
        if value and value.strip():
            aliases.extend(_product_id_aliases(value))
    return _unique(aliases)


def _product_id_aliases(value: str) -> list[str]:
    stripped = value.strip()
    if not stripped:
        return []
    resource_id = stripped.rsplit("/", 1)[-1].strip()
    aliases = [stripped, resource_id]
    if "~" in resource_id:
        aliases.append(resource_id.rsplit("~", 1)[-1].strip())
    return [alias for alias in _unique(aliases) if alias]


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


def _metric_fact_by_name(
    facts: list[MetricFact],
    names: list[str],
) -> MetricFact | None:
    accepted_names = set(names)
    for fact in facts:
        if fact.name in accepted_names:
            return fact
    return None


def _int_previous_metric_value(fact: MetricFact | None) -> int | None:
    if fact is None or not isinstance(fact.previous_value, int | float):
        return None
    return int(fact.previous_value)


def _int_delta_metric_value(fact: MetricFact | None) -> int | None:
    if fact is None or not isinstance(fact.delta, int | float):
        return None
    return int(fact.delta)


def _delta_percent_metric_value(fact: MetricFact | None) -> float | None:
    if fact is None or not isinstance(fact.delta_percent, int | float):
        return None
    return float(fact.delta_percent)


def _iso_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _text_metric_value(facts: list[MetricFact], names: list[str]) -> str | None:
    accepted_names = set(names)
    for fact in facts:
        if fact.name in accepted_names and isinstance(fact.value, str):
            value = fact.value.strip()
            if value:
                return value
    return None


def _dimension_value(facts: list[MetricFact], keys: list[str]) -> str | None:
    for fact in facts:
        for key in keys:
            value = fact.dimensions.get(key)
            if value and value.strip():
                return value.strip()
    return None


def _has_product_performance_metric(row: MerchantProductPerformanceRow) -> bool:
    return any(
        value is not None
        for value in (
            row.ads_clicks,
            row.ads_cost_micros,
            row.ads_conversions,
            row.ads_conversion_value,
            row.ga4_ecommerce_purchases,
            row.ga4_purchase_revenue,
        )
    )


def _has_price_change(row: MerchantProductPerformanceRow) -> bool:
    if (
        row.ads_product_price_micros is None
        or row.ads_product_previous_price_micros is None
        or row.ads_product_previous_price_collected_at is None
    ):
        return False
    if row.ads_product_price_delta_micros is not None:
        return row.ads_product_price_delta_micros != 0
    return row.ads_product_price_micros != row.ads_product_previous_price_micros


def _has_ads_product_state(row: MerchantProductPerformanceRow) -> bool:
    return any(
        value is not None
        for value in (
            row.ads_product_title,
            row.ads_product_status,
            row.ads_product_availability,
            row.ads_product_price_micros,
        )
    )


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
                "WILQ nie ma aktualnych metryk Merchant, więc nie może ocenić "
                "liczby produktów, liczby zgłoszeń problemów ani stanu feedu."
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
            "sprawdzonej akcji i audytu."
        ),
        next_step="Przejdź do kolejki problemów i grupuj je po typie oraz atrybucie.",
        source_connectors=[MERCHANT_CONNECTOR_ID],
        evidence_ids=_unique(fact.evidence_id for fact in product_facts or facts),
        metric_facts=(product_facts or facts)[:10],
        action_ids=action_ids,
        blocked_claims=[
            "ponowne zatwierdzenie produktu",
            "odzyskany przychód",
            "wzrost zysku",
        ],
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
            next_step="Odśwież dane Merchant i sprawdź aggregateProductStatuses.",
            source_connectors=[MERCHANT_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            action_ids=action_ids,
            blocked_claims=["propozycja naprawy feedu", "naprawa pojedynczego produktu"],
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
            "Otwórz akcję `act_review_merchant_feed_issues` i przygotuj "
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
        blocked_claims=[
            "automatyczna zmiana feedu",
            "nadpisanie głównego feedu",
            "ponowne zatwierdzenie produktu",
        ],
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
                issue_type_label=_merchant_display_label(issue_type),
                severity=severity,
                severity_label=_merchant_severity_label(severity),
                resolution=resolution or None,
                resolution_label=_merchant_resolution_label(resolution or None),
                affected_attribute=affected_attribute or None,
                affected_attribute_label=_merchant_display_label(
                    affected_attribute or "atrybut nieznany"
                ),
                country=country or None,
                reporting_context=reporting_context or None,
                reporting_context_label=_merchant_reporting_context_label(
                    reporting_context or None
                ),
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
                blocked_claims=[
                    "ponowne zatwierdzenie produktu",
                    "odzyskany przychód",
                    "automatyczna zmiana feedu",
                ],
                action_id=action_id,
                risk=_merchant_cluster_risk(severity, resolution),
                next_step=(
                    "Przejrzyj tę grupę problemu przez akcję do sprawdzenia; "
                    "najpierw przygotuj podgląd zmian, bez automatycznej zmiany feedu."
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
            "przeglądu: można przygotować decyzje i podgląd zmian, ale nie wolno "
            "obiecać ponownego zatwierdzenia produktu ani automatycznie nadpisać feedu."
        ),
        next_step=(
            "Przejdź przez top decyzje lub klastry problemów, przygotuj przegląd "
            "akcji i nie zapisuj zmian feedu bez sprawdzenia w WILQ oraz zgody operatora."
        ),
        top_decision_ids=[decision.id for decision in decisions[:4]],
        top_issue_cluster_ids=[cluster.id for cluster in issue_clusters[:4]],
        top_tactical_item_ids=[item.id for item in top_issue_items],
        reported_issue_occurrences=reported_issue_occurrences,
        issue_types=_unique(
            [
                *(
                    cluster.issue_type_label or _merchant_display_label(cluster.issue_type)
                    for cluster in issue_clusters
                ),
                *(
                    _merchant_display_label(item.dimensions.get("issue_type") or "problem feedu")
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
                    "WILQ nie ma aktualnych metryk Merchant, więc nie może "
                    "uczciwie zbudować kolejki problemów feedu ani ocenić stanu produktów."
                ),
                next_step="Uruchom odczyt danych Merchant, potem wróć do /merchant.",
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


def _merchant_decisions_with_product_state_review(
    decisions: list[MerchantDecisionItem],
    product_performance_readiness: MerchantProductPerformanceReadiness,
    action_ids: list[str],
) -> list[MerchantDecisionItem]:
    product_state_decision = _merchant_product_state_review_decision(
        product_performance_readiness,
        action_ids,
    )
    if product_state_decision is None:
        return decisions
    merged = [product_state_decision, *decisions]
    return sorted(merged, key=lambda decision: (decision.priority, decision.id))


def _merchant_decisions_with_price_impact_review(
    decisions: list[MerchantDecisionItem],
    price_impact_readiness: MerchantPriceImpactReadiness,
    action_ids: list[str],
) -> list[MerchantDecisionItem]:
    price_decision = _merchant_price_impact_review_decision(
        price_impact_readiness,
        action_ids,
    )
    if price_decision is None:
        return decisions
    merged = [price_decision, *decisions]
    return sorted(merged, key=lambda decision: (decision.priority, decision.id))


def _merchant_decisions_with_lineage(
    decisions: list[MerchantDecisionItem],
) -> list[MerchantDecisionItem]:
    return [
        decision.model_copy(
            update={
                "payload_preview": [
                    _merchant_payload_preview_with_operator_labels(preview)
                    for preview in decision.payload_preview
                ],
                "knowledge_card_ids": _unique(
                    [*decision.knowledge_card_ids, *MERCHANT_KNOWLEDGE_CARD_IDS]
                ),
                "expert_rule_ids": _unique(
                    [*decision.expert_rule_ids, *MERCHANT_EXPERT_RULE_IDS]
                ),
            }
        )
        for decision in decisions
    ]


def _merchant_payload_preview_with_operator_labels(
    preview: dict[str, object],
) -> dict[str, object]:
    checks = preview.get("required_validation")
    if not isinstance(checks, list):
        return preview
    labels = [
        MERCHANT_REQUIRED_VALIDATION_LABELS.get(check, check)
        for check in checks
        if isinstance(check, str)
    ]
    return {**preview, "required_validation_labels": labels}


def _merchant_price_impact_review_decision(
    price_impact_readiness: MerchantPriceImpactReadiness,
    action_ids: list[str],
) -> MerchantDecisionItem | None:
    return MerchantDecisionItem(
        id="merchant_decision_review_price_impact_readiness",
        decision_type="review_price_impact_readiness",
        status=price_impact_readiness.status,
        title="Merchant: sprawdź gotowość analizy wpływu ceny",
        summary=price_impact_readiness.summary,
        priority=60,
        metric_tiles=_clean_merchant_metric_tiles(
            {
                "ceny bieżące": price_impact_readiness.products_with_current_price,
                "historia ceny": price_impact_readiness.products_with_previous_price,
                "zmiany ceny": price_impact_readiness.products_with_price_change,
                "performance": (
                    price_impact_readiness.products_with_performance_metrics
                ),
            }
        ),
        payload_preview=price_impact_readiness.payload_preview,
        source_connectors=price_impact_readiness.source_connectors,
        evidence_ids=price_impact_readiness.evidence_ids,
        action_ids=action_ids,
        blocked_claims=price_impact_readiness.blocked_claims,
        rationale=(
            "To jest decyzja gotowości price-impact. WILQ może pokazać bieżące "
            "ceny, historię ceny i brakujące kontrakty, ale nie może oceniać "
            "wpływu ceny bez zdarzenia zmiany ceny oraz okna performance."
        ),
        next_step=price_impact_readiness.next_step,
        risk=ActionRisk.medium,
    )


def _merchant_product_state_review_decision(
    product_performance_readiness: MerchantProductPerformanceReadiness,
    action_ids: list[str],
) -> MerchantDecisionItem | None:
    state_rows = [
        row
        for row in product_performance_readiness.performance_rows
        if _has_ads_product_state(row) and not _has_product_performance_metric(row)
    ]
    if not state_rows:
        return None
    visible_rows = state_rows[:8]
    not_eligible_count = sum(
        1 for row in state_rows if row.ads_product_status == "NOT_ELIGIBLE"
    )
    out_of_stock_count = sum(
        1 for row in state_rows if row.ads_product_availability == "OUT_OF_STOCK"
    )
    return MerchantDecisionItem(
        id="merchant_decision_review_ads_product_state_mapping",
        decision_type="review_product_state_mapping",
        status="ready",
        title="Merchant: sprawdź powiązanie produktów ze statusem w Google Ads",
        summary=(
            f"WILQ połączył {len(state_rows)} próbek Merchant ze statusem produktów "
            "w Google Ads. To pokazuje status, dostępność i cenę z Ads, "
            "ale nie zawiera kliknięć, kosztu, przychodu ani efektu naprawy."
        ),
        issue_cluster_ids=[],
        priority=20,
        metric_tiles=_clean_merchant_metric_tiles(
            {
                "powiązane produkty": len(state_rows),
                "NOT_ELIGIBLE": not_eligible_count,
                "OUT_OF_STOCK": out_of_stock_count,
            }
        ),
        sample_product_ids=[row.product_id for row in visible_rows],
        sample_titles=_unique(
            title
            for row in visible_rows
            for title in [row.sample_title or row.ads_product_title]
            if title
        ),
        payload_preview=[
            _merchant_product_state_review_payload_preview(
                visible_rows,
                product_performance_readiness.evidence_ids,
            ),
            _merchant_supplemental_feed_review_payload_preview(
                visible_rows,
                product_performance_readiness.evidence_ids,
            ),
        ],
        source_connectors=product_performance_readiness.source_connectors,
        evidence_ids=product_performance_readiness.evidence_ids,
        action_ids=action_ids,
        blocked_claims=MERCHANT_PRODUCT_PERFORMANCE_BLOCKED_CLAIMS,
        rationale=(
            "To jest decyzja powiązania i sprawdzenia, nie decyzja o wynikach produktu. "
            "Wiersze samego statusu potwierdzają, że próbka Merchant ma odpowiednik w "
            "produktach Google Ads, ale bez metryk emisji i sprzedaży nie wolno "
            "wyciągać wniosków o zwrot z reklam, odzyskanym przychód ani skutku naprawy."
        ),
        next_step=(
            "Sprawdź powiązane produkty: status Ads, dostępność, cenę, "
            "powiązany problem Merchant i podgląd uzupełnienia feedu. "
            "Główny feed, zapis zmian i wpływ na zatwierdzenie pozostają zablokowane."
        ),
        risk=ActionRisk.medium,
    )


def _merchant_product_state_review_payload_preview(
    rows: list[MerchantProductPerformanceRow],
    evidence_ids: list[str],
) -> dict[str, object]:
    return {
        "id": "merchant_product_state_review_preview",
        "preview_contract": MERCHANT_PRODUCT_STATE_REVIEW_PREVIEW_CONTRACT,
        "operation_type": "MerchantProductStateReview",
        "products": [
            {
                "product_id": row.product_id,
                "title": row.sample_title or row.ads_product_title,
                "issue_type": row.issue_type,
                "affected_attribute": row.affected_attribute,
                "ads_product_status": row.ads_product_status,
                "ads_product_availability": row.ads_product_availability,
                "ads_product_price_micros": row.ads_product_price_micros,
                "ads_product_currency_code": row.ads_product_currency_code,
            }
            for row in rows
        ],
        "reason": (
            "Do sprawdzenia: podgląd powiązania próbek Merchant ze statusem "
            "produktów w Google Ads. To nie jest gotowa zmiana feedu."
        ),
        "required_validation": [
            "review_product_identity_mapping",
            "review_ads_product_status",
            "review_merchant_issue_context",
            "prepare_supplemental_feed_preview_before_any_mutation",
            "human_confirm_before_apply",
            "mutation_audit_required",
        ],
        "blocked_claims": MERCHANT_PRODUCT_PERFORMANCE_BLOCKED_CLAIMS,
        "evidence_ids": evidence_ids,
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
    }


def _merchant_supplemental_feed_review_payload_preview(
    rows: list[MerchantProductPerformanceRow],
    evidence_ids: list[str],
) -> dict[str, object]:
    candidates = [
        _merchant_supplemental_feed_candidate(row)
        for row in rows
        if row.issue_type or row.affected_attribute or row.ads_product_status
    ]
    return {
        "id": "merchant_supplemental_feed_review_preview",
        "preview_contract": MERCHANT_SUPPLEMENTAL_FEED_REVIEW_PREVIEW_CONTRACT,
        "operation_type": "MerchantSupplementalFeedCandidateReview",
        "feed_target": "supplemental_feed_check_only",
        "primary_feed_mutation_allowed": False,
        "candidates": candidates,
        "reason": (
            "Do sprawdzenia: propozycje do supplemental feed. WILQ pokazuje pola do "
            "sprawdzenia i źródła sprawdzenia, ale nie wylicza docelowych wartości "
            "feedu i nie wykonuje mutacji."
        ),
        "required_validation": [
            "review_product_identity_mapping",
            "review_merchant_issue_context",
            "confirm_source_of_truth_values",
            "prepare_supplemental_feed_draft_preview",
            "validate_change_values",
            "human_confirm_before_apply",
            "mutation_audit_required",
        ],
        "blocked_claims": _unique(
            [
                *MERCHANT_PRODUCT_PERFORMANCE_BLOCKED_CLAIMS,
                "nadpisanie głównego feedu",
                "zapis do feedu uzupełniającego",
                "zmiana danych produktu",
                "automatyczna naprawa zatwierdzenia",
            ]
        ),
        "evidence_ids": evidence_ids,
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
    }


def _merchant_supplemental_feed_candidate(
    row: MerchantProductPerformanceRow,
) -> dict[str, object]:
    review_fields = _merchant_supplemental_feed_review_fields(row)
    value_sources = [
        "Merchant Center issue context",
        "Google Ads product status",
        "operator-confirmed product source of truth",
    ]
    return {
        "product_id": row.product_id,
        "title": row.sample_title or row.ads_product_title,
        "issue_type": row.issue_type,
        "affected_attribute": row.affected_attribute,
        "country": row.country,
        "reporting_context": row.reporting_context,
        "ads_product_status": row.ads_product_status,
        "ads_product_availability": row.ads_product_availability,
        "ads_product_price_micros": row.ads_product_price_micros,
        "ads_product_currency_code": row.ads_product_currency_code,
        "review_fields": review_fields,
        "value_sources_required": value_sources,
        "candidate_status": "requires_human_value_confirmation",
        "allowed_next_step": (
            "Przygotuj supplemental-feed draft dopiero po potwierdzeniu wartości "
            "w źródle produktu. Nie nadpisuj primary feed."
        ),
    }


def _merchant_supplemental_feed_review_fields(
    row: MerchantProductPerformanceRow,
) -> list[str]:
    attribute = (row.affected_attribute or "").removeprefix("n:").strip()
    fields = [attribute] if attribute else []
    if row.ads_product_availability:
        fields.append("availability")
    if row.ads_product_price_micros is not None:
        fields.append("price")
    return _unique(field for field in fields if field)


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
        cluster.reporting_context_label
        or _merchant_reporting_context_label(cluster.reporting_context)
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
        issue_type_label=display_issue_type,
        severity=primary_cluster.severity,
        severity_label=primary_cluster.severity_label
        or _merchant_severity_label(primary_cluster.severity),
        resolution=primary_cluster.resolution,
        resolution_label=primary_cluster.resolution_label
        or _merchant_resolution_label(primary_cluster.resolution),
        affected_attribute=primary_cluster.affected_attribute,
        affected_attribute_label=display_attribute,
        country=primary_cluster.country,
        reporting_context=None,
        reporting_context_label="wiele kontekstów",
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
            "status i wymagana ścieżka rozwiązania są takie same. Konteksty "
            "raportowania są detalem przeglądu. Suma raportów nie jest liczbą "
            "unikalnych produktów ani gotową zmianą feedu."
        ),
        next_step=(
            "Przejrzyj problem przez akcję do sprawdzenia, sprawdź konteksty "
            "raportowania i przygotuj podgląd zmian bez automatycznej zmiany feedu."
        ),
        risk=max((cluster.risk for cluster in clusters), key=_action_risk_rank),
    )


def _merchant_decision_from_cluster(
    cluster: MerchantIssueCluster,
    facts: list[MetricFact],
    action_ids: list[str],
) -> MerchantDecisionItem:
    context = cluster.reporting_context_label or _merchant_reporting_context_label(
        cluster.reporting_context
    )
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
            f"{cluster.product_count} zgłoszeń problemu "
            f"{cluster.severity_label or _merchant_severity_label(cluster.severity)}"
            f" / {cluster.resolution_label or _merchant_resolution_label(cluster.resolution)} "
            f"dla {cluster.country or 'global'}"
            f" / {context}."
        ),
        cluster_id=cluster.id,
        issue_cluster_ids=[cluster.id],
        issue_type=issue_type,
        issue_type_label=display_issue_type,
        severity=cluster.severity,
        severity_label=cluster.severity_label or _merchant_severity_label(cluster.severity),
        resolution=cluster.resolution,
        resolution_label=cluster.resolution_label
        or _merchant_resolution_label(cluster.resolution),
        affected_attribute=cluster.affected_attribute,
        affected_attribute_label=display_attribute,
        country=cluster.country,
        reporting_context=cluster.reporting_context,
        reporting_context_label=context,
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
            "To jest klaster problemu Merchant do ręcznego sprawdzenia. Liczba oznacza "
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
        issue_type_label=display_issue_type,
        severity=severity,
        severity_label=_merchant_severity_label(severity),
        resolution=item.dimensions.get("resolution"),
        resolution_label=_merchant_resolution_label(item.dimensions.get("resolution")),
        affected_attribute=item.dimensions.get("affected_attribute"),
        affected_attribute_label=display_attribute,
        country=item.dimensions.get("country"),
        reporting_context=item.dimensions.get("reporting_context"),
        reporting_context_label=_merchant_reporting_context_label(
            item.dimensions.get("reporting_context")
        ),
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
        "issue_type_label": cluster.issue_type_label
        or _merchant_display_label(cluster.issue_type),
        "affected_attribute": cluster.affected_attribute,
        "affected_attribute_label": cluster.affected_attribute_label
        or _merchant_display_label(cluster.affected_attribute or "atrybut nieznany"),
        "country": cluster.country,
        "reporting_context": cluster.reporting_context,
        "reporting_context_label": cluster.reporting_context_label
        or _merchant_reporting_context_label(cluster.reporting_context),
        "severity": cluster.severity,
        "severity_label": cluster.severity_label
        or _merchant_severity_label(cluster.severity),
        "resolution": cluster.resolution,
        "resolution_label": cluster.resolution_label
        or _merchant_resolution_label(cluster.resolution),
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
            "Do sprawdzenia: podgląd konkretnej decyzji Merchant. WILQ może przygotować "
            "kolejkę oceny, ale nie może zmienić feedu ani obiecać przywrócenia "
            "zatwierdzenia bez osobnego kontraktu zapisu i audytu."
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
        blocked_claims=[
            "ponowne zatwierdzenie produktu",
            "odzyskany przychód",
            "automatyczna zmiana feedu",
        ],
        rationale=(
            "Merchant ma aggregate product/feed facts, ale bieżący odczyt nie "
            "dostarcza wymiarowych issue clusters. Marketer może rozpocząć review "
            "akcji, ale nie wolno twierdzić, który konkretny atrybut lub "
            "produkt został naprawiony."
        ),
        next_step=(
            "Otwórz `act_review_merchant_feed_issues`, sprawdź podgląd zmian i "
            "zatrzymaj zapis zmian do czasu sprawdzenia w WILQ."
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


def _merchant_reporting_context_label(value: str | None) -> str:
    if not value:
        return "wszystkie konteksty"
    return MERCHANT_REPORTING_CONTEXT_LABELS.get(value, _merchant_display_label(value))


def _merchant_severity_label(value: str | None) -> str:
    if not value:
        return "status nieznany"
    return MERCHANT_SEVERITY_LABELS.get(value, _merchant_display_label(value))


def _merchant_resolution_label(value: str | None) -> str:
    if not value:
        return "brak wymaganej ścieżki rozwiązania"
    return MERCHANT_RESOLUTION_LABELS.get(value, _merchant_display_label(value))


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
            "Akcje Merchant pozostają w trybie przygotowania do czasu sprawdzenia w WILQ "
            "zakresu zmian i audytu."
        ),
        diagnosis=(
            "Zmiany feedu lub produktów mogą wpływać na widoczność i sprzedaż. WILQ "
            "może przygotować kolejkę przeglądu, ale nie może zmieniać głównego feedu ani "
            "twierdzić, że naprawił produkty bez obsługi zapisu zmian."
        ),
        next_step=(
            "Sprawdź propozycję w WILQ, pokaż podgląd zmian i zatrzymaj zapis zmian "
            "do jawnego potwierdzenia."
        ),
        source_connectors=[MERCHANT_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        action_ids=action_ids,
        blocked_claims=[
            "zapis do feedu",
            "zmiana danych produktu",
            "automatyczna naprawa zatwierdzenia",
        ],
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
    return "Brak wykonanego odczytu danych Merchant."


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
