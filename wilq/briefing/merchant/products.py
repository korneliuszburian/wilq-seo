from __future__ import annotations

from typing import Literal

from wilq.briefing.merchant_labels import merchant_preview_contract_label
from wilq.schemas import (
    ConnectorRefreshStatus,
    MerchantDecisionItem,
    MerchantIssueCluster,
    MerchantPriceImpactReadiness,
    MerchantProductPerformanceReadiness,
    MerchantProductPerformanceRow,
    MerchantProductSampleReadiness,
    MetricFact,
)
from wilq.storage.metric_store import metric_store

from .labels import (
    _merchant_display_label,
    _merchant_reporting_context_label,
)
from .shared import (
    GA4_CONNECTOR_ID,
    GOOGLE_ADS_CONNECTOR_ID,
    GOOGLE_ADS_PRODUCT_STATE_FACT_NAMES,
    MERCHANT_CONNECTOR_ID,
    MERCHANT_METRIC_FACT_LIMIT,
    MERCHANT_PRICE_IMPACT_PREVIEW_CONTRACT,
    MERCHANT_PRICE_IMPACT_REQUIRED_READ_CONTRACTS,
    MERCHANT_PRODUCT_PERFORMANCE_BLOCKED_CLAIMS,
    MERCHANT_PRODUCT_PERFORMANCE_REQUIRED_READ_CONTRACTS,
    PRODUCT_JOIN_DIMENSION_KEYS,
    _delta_percent_metric_value,
    _dimension_value,
    _float_metric_value,
    _int_delta_metric_value,
    _int_metric_value,
    _int_previous_metric_value,
    _iso_datetime,
    _latest_connector_refresh,
    _metric_fact_by_name,
    _text_metric_value,
    _unique,
)


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
                "Odczyt Merchant zwraca przykładowe produkty dla części problemów. "
                "Tytuły są dostępne tylko wtedy, gdy odczyt produktów je potwierdzi."
            ),
            next_step=(
                "Użyj próbek do sprawdzenia. Dla tytułów, SKU i statusów dodaj "
                "dokładniejszy odczyt produktów z problemami."
            ),
            blocked_claims=[
                "zapis do pliku produktowego",
                "automatyczna zmiana pliku produktowego",
            ],
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
                "zwraca konkretnych produktów, SKU ani tytułów do pracy produkt-po-produkcie."
            ),
            next_step=(
                "Dodać osobny odczyt produktów z problemami, zanim WILQ pokaże "
                "konkretne produkty do poprawy."
            ),
            blocked_claims=[
                "naprawa pojedynczego produktu",
                "zapis do pliku produktowego",
                "automatyczna zmiana pliku produktowego",
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
            "zapis do pliku produktowego",
            "automatyczna zmiana pliku produktowego",
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
        fact for fact in ads_product_facts if fact.name not in GOOGLE_ADS_PRODUCT_STATE_FACT_NAMES
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
            source_connectors=_unique(fact.source_connector for fact in [*ads_facts, *ga4_facts]),
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
            row for row in performance_rows if _has_product_performance_metric(row)
        ]
        if rows_with_metrics:
            status: Literal["ready", "blocked"] = "ready"
            summary = (
                "WILQ ma dopasowane fakty produktu dla części próbek Merchant. "
                "To wspiera przegląd produktu z metrykami Ads/GA4, ale nie oznacza "
                "automatycznej naprawy pliku produktowego ani efektu po zmianie."
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
                "Użyj wierszy stanu produktu tylko do potwierdzenia dopasowania produktów. "
                "Zwrot z reklam "
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
                    *(connector for row in performance_rows for connector in row.source_connectors),
                ]
            ),
            evidence_ids=_unique(
                [
                    *merchant_evidence_ids,
                    *(evidence_id for row in performance_rows for evidence_id in row.evidence_ids),
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
    rows_with_current_price = [row for row in rows if row.ads_product_price_micros is not None]
    rows_with_previous_price = [
        row
        for row in rows_with_current_price
        if row.ads_product_previous_price_micros is not None
        and row.ads_product_previous_price_collected_at is not None
    ]
    rows_with_price_change = [row for row in rows_with_previous_price if _has_price_change(row)]
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
    status: Literal["ready", "blocked"] = "ready" if not missing_read_contracts else "blocked"
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
        change_preview=[
            _merchant_price_impact_change_preview(
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
            "zapis do pliku produktowego",
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
        "WILQ nie ma wystarczających faktów ceny i skuteczności, żeby ocenić wpływ ceny produktu."
    )


def _merchant_price_impact_change_preview(
    *,
    rows: list[MerchantProductPerformanceRow],
    evidence_ids: list[str],
    missing_read_contracts: list[str],
) -> dict[str, object]:
    return {
        "id": "merchant_price_impact_readiness_preview",
        "preview_contract": MERCHANT_PRICE_IMPACT_PREVIEW_CONTRACT,
        "preview_contract_label": merchant_preview_contract_label(
            MERCHANT_PRICE_IMPACT_PREVIEW_CONTRACT
        ),
        "operation_type": "MerchantPriceImpactReadinessReview",
        "products": [
            {
                "product_id": row.product_id,
                "title": row.sample_title or row.ads_product_title,
                "current_price_micros": row.ads_product_price_micros,
                "current_price_collected_at": _iso_datetime(row.ads_product_price_collected_at),
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
            "zapis do pliku produktowego",
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
            "Odczyt Merchant nie daje próbek produktów, więc WILQ nie ma klucza "
            "do połączenia problemów pliku produktowego z Ads/GA4."
        )
    if ads_shopping_contract_ready and not ads_product_facts:
        lookback_label = (
            f" z lookbackiem {ads_shopping_lookback_days} dni"
            if ads_shopping_lookback_days is not None
            else ""
        )
        return (
            "Odczyt Merchant zwraca próbki produktów, GA4 ma fakty produktu, a Ads "
            f"ma gotowy widok skuteczności zakupowej{lookback_label}, ale bieżący "
            "odczyt Ads zwrócił 0 wierszy skuteczności produktu. WILQ nie ma więc "
            "dopasowanych faktów Ads dla próbek Merchant."
        )
    if ga4_product_facts and not ads_product_facts:
        return (
            "Odczyt Merchant zwraca próbki produktów i GA4 ma fakty produktu, ale WILQ "
            "nie ma dopasowanych faktów produktu z Ads dla tych próbek."
        )
    return (
        "Odczyt Merchant zwraca próbki produktów, ale WILQ nie ma dopasowanych "
        "faktów produktu z Ads albo GA4 dla tych próbek."
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
            "Dodać próbki produktów Merchant z kluczem produktu lub SKU, zanim WILQ "
            "spróbuje łączyć plik produktowy ze skutecznością."
        )
    if ads_shopping_contract_ready and not ads_product_facts:
        if ads_shopping_lookback_days is not None and ads_shopping_lookback_days >= 90:
            return (
                "Dodaj aktualny `shopping_product` state read albo mapowanie Merchant "
                "Merchant offer -> produkt Ads, zamiast obiecywać skuteczność produktu "
                "z pustej historii emisji."
            )
        return (
            "Sprawdź, czy produkty miały emisję w Ads w ostatnich 30 dniach; jeśli "
            "nie, dodaj dłuższy lookback albo aktualny `shopping_product` state read "
            "zamiast obiecywać skuteczność produktu."
        )
    if ga4_product_facts and not ads_product_facts:
        return (
            "Dodać albo odświeżyć dane skuteczności produktów z Google Ads "
            "Shopping i Performance Max oraz utrzymać wspólny klucz produktu."
        )
    return (
        "Dodać skuteczność produktu dla Google Ads Shopping, Performance Max "
        "i GA4 ecommerce oraz utrzymać wspólny klucz produktu."
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
