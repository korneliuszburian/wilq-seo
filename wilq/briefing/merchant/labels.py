from __future__ import annotations

from collections.abc import Iterable, Mapping

from wilq.briefing.merchant_labels import (
    merchant_dimension_label,
    merchant_dimension_value_label,
    merchant_display_label,
    merchant_metric_fact_label,
    merchant_metric_snapshot_labels,
    merchant_preview_contract_label,
    merchant_reporting_context_label,
    merchant_resolution_label,
    merchant_severity_label,
)
from wilq.operator_labels import action_count_label
from wilq.schemas import (
    ConnectorRefreshRun,
    MerchantDecisionItem,
    MerchantDiagnosticSection,
    MerchantDiagnosticsResponse,
    MerchantProductPerformanceReadiness,
    MerchantProductPerformanceRow,
    MerchantProductSampleReadiness,
    MetricFact,
    connector_refresh_run_status_label,
)

from .shared import (
    GA4_CONNECTOR_ID,
    GOOGLE_ADS_CONNECTOR_ID,
    MERCHANT_CONNECTOR_ID,
    MERCHANT_DECISION_TYPE_LABELS,
    MERCHANT_REQUIRED_VALIDATION_LABELS,
    MERCHANT_SECTION_LABELS,
    _enum_value,
    _unique,
)


def _merchant_response_with_operator_labels(
    response: MerchantDiagnosticsResponse,
) -> MerchantDiagnosticsResponse:
    response_source_connectors = _unique(
        [
            *(
                connector
                for section in response.sections
                for connector in section.source_connectors
            ),
            *(
                connector
                for cluster in response.issue_clusters
                for connector in cluster.source_connectors
            ),
            *(
                connector
                for decision in response.decision_queue
                for connector in decision.source_connectors
            ),
        ]
    )
    return response.model_copy(
        update={
            "source_connector_labels": _merchant_source_connector_labels(
                response_source_connectors
            ),
            "evidence_summary_label": _merchant_evidence_summary_label(response.evidence_ids),
            "action_summary_label": action_count_label(response.action_ids),
            "freshness_assessment": response.freshness_assessment.model_copy(
                update={
                    "state_label": _merchant_freshness_label(response.freshness_assessment.state),
                }
            ),
            "operator_summary": response.operator_summary.model_copy(
                update={
                    "source_connector_labels": _merchant_source_connector_labels(
                        response.operator_summary.source_connectors
                    ),
                    "evidence_summary_label": _merchant_evidence_summary_label(
                        response.operator_summary.evidence_ids
                    ),
                    "action_summary_label": action_count_label(
                        response.operator_summary.action_ids
                    ),
                    "blocked_claim_labels": _merchant_blocked_claim_labels(
                        response.operator_summary.blocked_claims
                    ),
                }
            ),
            "unknowns": [
                unknown.model_copy(
                    update={
                        "blocked_claim_labels": _merchant_blocked_claim_labels(
                            unknown.blocked_claims
                        ),
                    }
                )
                for unknown in response.unknowns
            ],
            "product_sample_readiness": response.product_sample_readiness.model_copy(
                update={
                    "status_label": _merchant_product_sample_status_label(
                        response.product_sample_readiness
                    ),
                    "sample_summary_label": _merchant_sample_summary_label(
                        response.product_sample_readiness.sample_count
                    ),
                    "sample_title_labels": _merchant_sample_title_labels(
                        response.product_sample_readiness.sample_product_titles
                    ),
                    "blocked_claim_labels": _merchant_blocked_claim_labels(
                        response.product_sample_readiness.blocked_claims
                    ),
                }
            ),
            "product_performance_readiness": (
                _merchant_product_performance_readiness_with_operator_labels(
                    response.product_performance_readiness
                )
            ),
            "price_impact_readiness": response.price_impact_readiness.model_copy(
                update={
                    "status_label": _merchant_price_impact_status_label(
                        response.price_impact_readiness.status
                    ),
                    "source_connector_labels": _merchant_source_connector_labels(
                        response.price_impact_readiness.source_connectors
                    ),
                    "evidence_summary_label": _merchant_evidence_summary_label(
                        response.price_impact_readiness.evidence_ids
                    ),
                    "blocked_claim_labels": _merchant_blocked_claim_labels(
                        response.price_impact_readiness.blocked_claims
                    ),
                }
            ),
            "decision_queue": [
                _merchant_decision_with_operator_labels(decision)
                for decision in response.decision_queue
            ],
            "sections": [
                _merchant_section_with_operator_labels(section) for section in response.sections
            ],
        }
    )


def _merchant_product_performance_readiness_with_operator_labels(
    readiness: MerchantProductPerformanceReadiness,
) -> MerchantProductPerformanceReadiness:
    return readiness.model_copy(
        update={
            "status_label": _merchant_product_performance_status_label(readiness.status),
            "sample_product_summary_label": _merchant_sample_summary_label(
                readiness.merchant_sample_count
            ),
            "source_connector_labels": _merchant_source_connector_labels(
                readiness.source_connectors
            ),
            "evidence_summary_label": _merchant_evidence_summary_label(readiness.evidence_ids),
            "blocked_claim_labels": _merchant_blocked_claim_labels(readiness.blocked_claims),
            "performance_rows": [
                row.model_copy(
                    update={
                        "title_label": _merchant_product_row_title_label(row),
                        "product_reference_label": _merchant_product_reference_label(row),
                        "source_connector_labels": _merchant_source_connector_labels(
                            row.source_connectors
                        ),
                        "evidence_summary_label": _merchant_evidence_summary_label(
                            row.evidence_ids
                        ),
                        "blocked_claim_labels": _merchant_blocked_claim_labels(row.blocked_claims),
                        "ads_product_status_label": _merchant_ads_product_status_label(
                            row.ads_product_status
                        ),
                        "ads_product_availability_label": (
                            _merchant_ads_product_availability_label(row.ads_product_availability)
                        ),
                        "ads_product_price_label": _merchant_micros_price_label(
                            row.ads_product_price_micros,
                            row.ads_product_currency_code,
                            missing_label="cena Ads do potwierdzenia",
                        ),
                        "ads_clicks_label": _merchant_number_label(
                            row.ads_clicks,
                            missing_label="kliknięcia Ads do potwierdzenia",
                        ),
                        "ads_cost_label": _merchant_micros_price_label(
                            row.ads_cost_micros,
                            row.ads_product_currency_code,
                            missing_label="koszt Ads do potwierdzenia",
                        ),
                        "ads_conversions_label": _merchant_number_label(
                            row.ads_conversions,
                            missing_label="konwersje Ads do potwierdzenia",
                        ),
                        "ads_conversion_value_label": _merchant_number_label(
                            row.ads_conversion_value,
                            missing_label="wartość konwersji Ads do potwierdzenia",
                        ),
                        "ga4_ecommerce_purchases_label": _merchant_number_label(
                            row.ga4_ecommerce_purchases,
                            missing_label="zakupy GA4 do potwierdzenia",
                        ),
                        "ga4_purchase_revenue_label": _merchant_number_label(
                            row.ga4_purchase_revenue,
                            missing_label="przychód GA4 do potwierdzenia",
                        ),
                        "missing_metric_labels": _merchant_missing_metric_labels(
                            row.missing_metrics
                        ),
                    }
                )
                for row in readiness.performance_rows
            ],
        }
    )


def _merchant_decision_with_operator_labels(
    decision: MerchantDecisionItem,
) -> MerchantDecisionItem:
    return decision.model_copy(
        update={
            "decision_type_label": MERCHANT_DECISION_TYPE_LABELS.get(
                decision.decision_type,
                _merchant_display_label(decision.decision_type),
            ),
            "status_label": _merchant_status_label(decision.status),
            "source_connector_labels": _merchant_source_connector_labels(
                decision.source_connectors
            ),
            "evidence_summary_label": _merchant_evidence_summary_label(decision.evidence_ids),
            "action_summary_label": action_count_label(decision.action_ids),
            "blocked_claim_labels": _merchant_blocked_claim_labels(decision.blocked_claims),
            "risk_label": _merchant_risk_label(decision.risk),
        }
    )


def _merchant_section_with_operator_labels(
    section: MerchantDiagnosticSection,
) -> MerchantDiagnosticSection:
    return section.model_copy(
        update={
            "label": MERCHANT_SECTION_LABELS.get(section.id, section.title),
            "status_label": _merchant_status_label(section.status),
            "evidence_summary_label": _merchant_evidence_summary_label(section.evidence_ids),
            "action_summary_label": action_count_label(section.action_ids),
            "blocked_claim_labels": _merchant_blocked_claim_labels(section.blocked_claims),
            "risk_label": _merchant_risk_label(section.risk),
        }
    )


def _merchant_connector_status_label(status: object) -> str:
    normalized = _enum_value(status)
    labels = {
        "configured": "dostęp skonfigurowany",
        "missing_credentials": "brakuje dostępu",
        "disabled": "źródło wyłączone",
    }
    return labels.get(normalized, "status źródła do sprawdzenia")


def _merchant_refresh_status_label(run: ConnectorRefreshRun | object) -> str:
    if not isinstance(run, ConnectorRefreshRun):
        return "status odczytu do sprawdzenia"
    return connector_refresh_run_status_label(run)


def _merchant_live_data_status_label(live_data_available: bool) -> str:
    return (
        "metryki pliku produktowego dostępne"
        if live_data_available
        else "metryki pliku produktowego niepotwierdzone"
    )


def _merchant_freshness_label(status: object) -> str:
    normalized = _enum_value(status)
    labels = {
        "fresh": "dane świeże",
        "stale": "dane do odświeżenia",
        "missing": "odczyt niepotwierdzony",
        "blocked": "odczyt zablokowany",
    }
    return labels.get(normalized, "świeżość danych do sprawdzenia")


def _merchant_status_label(status: object) -> str:
    normalized = _enum_value(status)
    labels = {
        "ready": "gotowe",
        "blocked": "zablokowane",
        "missing": "zakres danych Merchant niepotwierdzony",
    }
    return labels.get(normalized, "status sekcji do sprawdzenia")


def _merchant_product_sample_status_label(readiness: MerchantProductSampleReadiness) -> str:
    return (
        "próbki produktów dostępne"
        if readiness.sample_products_available
        else "próbki produktów zablokowane"
    )


def _merchant_product_performance_status_label(status: object) -> str:
    return "dane Ads/GA4 dostępne" if _enum_value(status) == "ready" else "dane Ads/GA4 zablokowane"


def _merchant_sample_summary_label(count: int) -> str:
    if count <= 0:
        return "brak próbek produktów"
    if count == 1:
        return "1 próbka produktu do sprawdzenia"
    if 2 <= count <= 4:
        return f"{count} próbki produktów do sprawdzenia"
    return f"{count} próbek produktów do sprawdzenia"


def _merchant_sample_title_labels(titles: Iterable[str]) -> list[str]:
    return _unique(title.strip() for title in titles if title.strip())[:6]


def _merchant_product_row_title_label(row: MerchantProductPerformanceRow) -> str:
    return row.sample_title or row.ads_product_title or "Produkt Merchant do sprawdzenia"


def _merchant_product_reference_label(row: MerchantProductPerformanceRow) -> str:
    if row.sample_title or row.ads_product_title:
        return "identyfikator produktu dostępny w szczegółach technicznych"
    return "tytuł produktu niedostępny; identyfikator dostępny w szczegółach technicznych"


def _merchant_ads_product_status_label(status: object) -> str:
    labels = {
        "ELIGIBLE": "kwalifikuje się do emisji",
        "LIMITED": "ograniczona emisja",
        "NOT_ELIGIBLE": "nie kwalifikuje się do emisji",
    }
    normalized = _enum_value(status)
    if not normalized:
        return "brak statusu Ads"
    return labels.get(normalized, _merchant_display_label(normalized))


def _merchant_ads_product_availability_label(availability: object) -> str:
    labels = {
        "IN_STOCK": "dostępny",
        "OUT_OF_STOCK": "niedostępny",
        "PREORDER": "przedsprzedaż",
        "BACKORDER": "oczekuje na dostawę",
    }
    normalized = _enum_value(availability)
    if not normalized:
        return "brak dostępności Ads"
    return labels.get(normalized, _merchant_display_label(normalized))


def _merchant_micros_price_label(
    value: int | float | None,
    currency_code: str | None,
    *,
    missing_label: str = "kwota do potwierdzenia",
) -> str:
    if value is None:
        return missing_label
    amount = value / 1_000_000
    currency = currency_code or "PLN"
    return f"{amount:.2f} {currency}"


def _merchant_number_label(value: int | float | None, *, missing_label: str) -> str:
    if value is None:
        return missing_label
    return f"{value:g}"


def _merchant_missing_metric_labels(metrics: Iterable[str]) -> list[str]:
    labels = {
        "ads_clicks": "kliknięcia Ads",
        "ads_cost_micros": "koszt Ads",
        "ads_conversions": "konwersje Ads",
        "ads_conversion_value": "wartość konwersji Ads",
        "ga4_ecommerce_purchases": "zakupy GA4",
        "ga4_purchase_revenue": "przychód GA4",
    }
    return _unique(
        labels.get(str(metric), _merchant_display_label(str(metric))) for metric in metrics
    )


def _merchant_price_impact_status_label(status: object) -> str:
    return (
        "wpływ ceny gotowy do sprawdzenia"
        if _enum_value(status) == "ready"
        else "wpływ ceny zablokowany"
    )


def _merchant_risk_label(risk: object) -> str:
    normalized = _enum_value(risk)
    labels = {
        "low": "niskie ryzyko",
        "medium": "średnie ryzyko",
        "high": "wysokie ryzyko",
        "critical": "ryzyko krytyczne",
    }
    return labels.get(normalized, "ryzyko do sprawdzenia")


def _merchant_blocked_claim_labels(claims: Iterable[str]) -> list[str]:
    return _unique(_merchant_display_label(claim) for claim in claims)


def _merchant_source_connector_labels(connector_ids: Iterable[str]) -> list[str]:
    labels = {
        MERCHANT_CONNECTOR_ID: "Merchant Center",
        GOOGLE_ADS_CONNECTOR_ID: "Google Ads",
        GA4_CONNECTOR_ID: "GA4",
    }
    return _unique(
        labels.get(str(connector_id), _merchant_display_label(str(connector_id)))
        for connector_id in connector_ids
    )


def _merchant_evidence_summary_label(evidence_ids: list[str]) -> str:
    count = len(evidence_ids)
    if count == 0:
        return "Nie ma dowodów źródłowych; nie traktuj tego jako rekomendacji"
    if count == 1:
        return "1 dowód źródłowy"
    if 2 <= count <= 4:
        return f"{count} dowody źródłowe"
    return f"{count} dowodów źródłowych"


def _merchant_change_preview_with_operator_labels(
    preview: dict[str, object],
) -> dict[str, object]:
    checks = preview.get("required_validation")
    if not isinstance(checks, list):
        return preview
    labels = [
        MERCHANT_REQUIRED_VALIDATION_LABELS.get(check, "warunek Merchant do sprawdzenia")
        for check in checks
        if isinstance(check, str)
    ]
    return {
        **preview,
        "preview_contract_label": merchant_preview_contract_label(preview.get("preview_contract")),
        "required_validation_labels": labels,
    }


def _merchant_preview_scope_label(preview: dict[str, object]) -> str:
    for key in ("products", "candidates"):
        rows = preview.get(key)
        if isinstance(rows, list) and rows:
            return _merchant_count_label(len(rows), "wiersz", "wiersze")
    metric_snapshot = preview.get("metric_snapshot")
    if isinstance(metric_snapshot, dict) and metric_snapshot:
        labels = _merchant_metric_snapshot_labels(
            {str(key): value for key, value in metric_snapshot.items() if isinstance(value, int)}
        )
        if labels:
            return ", ".join(labels.values())
    reported = preview.get("reported_issue_occurrences")
    if isinstance(reported, int) and reported > 0:
        return _merchant_count_label(reported, "zgłoszenie", "zgłoszenia")
    return "zakres do ustalenia w review"


def _merchant_preview_required_validation_label(preview: dict[str, object]) -> str:
    labels = preview.get("required_validation_labels")
    if isinstance(labels, list):
        clean_labels = [str(label) for label in labels if str(label).strip()]
        if clean_labels:
            return ", ".join(clean_labels[:4])
    checks = preview.get("required_validation")
    if isinstance(checks, list) and checks:
        return _merchant_count_label(len(checks), "warunek", "warunki")
    return "brak dodatkowych warunków"


def _merchant_preview_apply_state_label(preview: dict[str, object]) -> str:
    if preview.get("apply_allowed") is True:
        return "Zapis możliwy dopiero po potwierdzeniu człowieka."
    return "Zapis zmian jest zablokowany."


def _merchant_preview_system_readiness_label(preview: dict[str, object]) -> str:
    if preview.get("api_mutation_ready") is True:
        return "System ma gotowy kontrakt przygotowania zapisu."
    return "System nie ma gotowego kontraktu zapisu dla tej akcji."


def _merchant_count_label(count: int, one: str, few_or_many: str) -> str:
    if count == 1:
        return f"1 {one}"
    return f"{count} {few_or_many}"


def _merchant_metric_snapshot_labels(metric_snapshot: Mapping[str, object]) -> dict[str, str]:
    return merchant_metric_snapshot_labels(metric_snapshot)


def _merchant_display_label(value: str) -> str:
    return merchant_display_label(value)


def _merchant_reporting_context_label(value: str | None) -> str:
    return merchant_reporting_context_label(value)


def _merchant_severity_label(value: str | None) -> str:
    return merchant_severity_label(value)


def _merchant_resolution_label(value: str | None) -> str:
    return merchant_resolution_label(value)


def _merchant_metric_fact_with_labels(fact: MetricFact) -> MetricFact:
    return fact.model_copy(
        update={
            "metric_label": merchant_metric_fact_label(fact.name),
            "dimension_labels": {key: merchant_dimension_label(key) for key in fact.dimensions},
            "dimension_value_labels": {
                key: merchant_dimension_value_label(key, value)
                for key, value in fact.dimensions.items()
            },
        }
    )
