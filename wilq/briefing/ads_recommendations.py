from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from wilq.actions.google_ads.recommendations import (
    RECOMMENDATION_REVIEW_ACTION_ID,
    RECOMMENDATION_REVIEW_BLOCKED_CLAIMS,
    RECOMMENDATION_REVIEW_REQUIRED_VALIDATION,
)
from wilq.schemas import (
    AdsRecommendationApplyPreview,
    AdsRecommendationRow,
    AdsRecommendationsReadContract,
    MetricFact,
)

GOOGLE_ADS_CONNECTOR_ID = "google_ads"
ADS_RECOMMENDATION_HUMAN_REVIEW_GATE = "human_strategy_review"


def build_recommendations_read_contract(
    metric_facts: list[MetricFact],
    *,
    read_attempted: bool,
    fallback_evidence_ids: list[str],
) -> AdsRecommendationsReadContract:
    rows = _recommendation_rows(metric_facts)
    impact_row_count = sum(1 for row in rows if row.impact_available)
    payload_preview = [
        row.payload_preview for row in rows if row.payload_preview is not None
    ]
    action_ids = [RECOMMENDATION_REVIEW_ACTION_ID] if payload_preview else []
    missing_read_contracts = [
        "change_history",
        "impression_share",
        "recommendation_apply_preview",
    ]
    if impact_row_count == 0:
        missing_read_contracts.insert(0, "recommendation_impact_preview")
    if payload_preview:
        missing_read_contracts = _remove_missing_contract_names(
            missing_read_contracts,
            "recommendation_apply_preview",
        )
    blocked_claims = [
        "zapis rekomendacji",
        "automatyczne przyjęcie rekomendacji",
        "zmiana budżetu",
        "zapis zmian kampanii",
        "obietnica poprawy wyniku",
    ]
    if rows or read_attempted:
        if rows:
            types = _unique(
                row.recommendation_type_label
                or _recommendation_type_label(row.recommendation_type)
                for row in rows
            )
            summary = (
                f"WILQ ma {len(rows)} aktywnych rekomendacji Google Ads do sprawdzenia. "
                f"Typy: {', '.join(types[:5])}. Podgląd wpływu dostępny dla "
                f"{impact_row_count}; podgląd zmian dla "
                f"{len(payload_preview)}."
            )
        else:
            summary = (
                "WILQ odczytał rekomendacje Google Ads; Google Ads zwrócił "
                "0 aktywnych rekomendacji."
            )
        return AdsRecommendationsReadContract(
            status="ready",
            title="Google Ads: rekomendacje do sprawdzenia",
            summary=summary,
            allowed_metrics=[
                "recommendation_available",
                "recommendation_campaign_count",
                "recommendation_impact_base_clicks",
                "recommendation_impact_potential_clicks",
                "recommendation_impact_base_impressions",
                "recommendation_impact_potential_impressions",
                "recommendation_impact_base_cost_micros",
                "recommendation_impact_potential_cost_micros",
                "recommendation_impact_base_conversions",
                "recommendation_impact_potential_conversions",
                "recommendation_impact_base_conversion_value",
                "recommendation_impact_potential_conversion_value",
            ],
            missing_read_contracts=missing_read_contracts,
            operator_review_gates=_recommendation_operator_review_gates(
                rows_available=bool(rows),
                payload_preview_ready=bool(payload_preview),
            ),
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(
                [*(evidence_id for row in rows for evidence_id in row.evidence_ids)]
                or fallback_evidence_ids
            ),
            recommendation_rows=rows,
            payload_preview=payload_preview,
            action_ids=action_ids,
            next_step=(
                "Potraktuj rekomendacje Google jako materiał do sprawdzenia, nie jako gotową "
                "strategię. Przed zapisem zmian wymagaj celu biznesowego, oceny zgodności, "
                "potwierdzenia człowieka, audytu i osobnej ścieżki zapisu zmian."
            ),
        )
    return AdsRecommendationsReadContract(
        status="blocked",
        title="Google Ads: brak kontraktu rekomendacji",
        summary="WILQ nie ma jeszcze odczytu rekomendacji Google Ads.",
        allowed_metrics=[],
        missing_read_contracts=["recommendations", *missing_read_contracts],
        operator_review_gates=[],
        blocked_claims=["rekomendacje Google Ads", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=fallback_evidence_ids,
        recommendation_rows=[],
        payload_preview=[],
        action_ids=[],
        next_step=(
            "Uruchom odczyt danych Google Ads z polami rekomendacji. Nie przyjmuj "
            "ani nie odrzucaj rekomendacji bez osobnej akcji do sprawdzenia."
        ),
    )


def _recommendation_operator_review_gates(
    *,
    rows_available: bool,
    payload_preview_ready: bool,
) -> list[str]:
    if not rows_available:
        return []
    return _unique(
        [
            ADS_RECOMMENDATION_HUMAN_REVIEW_GATE,
            *(
                gate
                for gate in RECOMMENDATION_REVIEW_REQUIRED_VALIDATION
                if gate != "recommendation_apply_preview" or payload_preview_ready
            ),
        ]
    )


def _recommendation_rows(metric_facts: list[MetricFact]) -> list[AdsRecommendationRow]:
    grouped_facts: dict[tuple[str | None, str], list[MetricFact]] = {}
    seen_metric_keys: set[tuple[str | None, str, str]] = set()
    supported_metric_names = {
        "recommendation_available",
        "recommendation_campaign_count",
        "recommendation_impact_base_clicks",
        "recommendation_impact_potential_clicks",
        "recommendation_impact_base_impressions",
        "recommendation_impact_potential_impressions",
        "recommendation_impact_base_cost_micros",
        "recommendation_impact_potential_cost_micros",
        "recommendation_impact_base_conversions",
        "recommendation_impact_potential_conversions",
        "recommendation_impact_base_conversion_value",
        "recommendation_impact_potential_conversion_value",
    }
    for fact in metric_facts:
        if fact.name not in supported_metric_names:
            continue
        recommendation_type = fact.dimensions.get("recommendation_type")
        recommendation_id = fact.dimensions.get("recommendation_id")
        if not recommendation_type and not recommendation_id:
            continue
        row_key = (
            recommendation_id,
            recommendation_type or f"recommendation {recommendation_id}",
        )
        metric_key = (recommendation_id, row_key[1], fact.name)
        if metric_key in seen_metric_keys:
            continue
        seen_metric_keys.add(metric_key)
        grouped_facts.setdefault(row_key, []).append(fact)

    rows = [
        _recommendation_row(recommendation_id, recommendation_type, facts)
        for (recommendation_id, recommendation_type), facts in grouped_facts.items()
    ]
    return sorted(rows, key=_recommendation_row_sort_key)


def _recommendation_row(
    recommendation_id: str | None,
    recommendation_type: str,
    facts: list[MetricFact],
) -> AdsRecommendationRow:
    facts_by_name = {fact.name: fact for fact in facts}
    first_dimensions = facts[0].dimensions if facts else {}
    expected_metrics = ["recommendation_available", "recommendation_campaign_count"]
    impact_fact_names = {
        "recommendation_impact_base_clicks",
        "recommendation_impact_potential_clicks",
        "recommendation_impact_base_impressions",
        "recommendation_impact_potential_impressions",
        "recommendation_impact_base_cost_micros",
        "recommendation_impact_potential_cost_micros",
        "recommendation_impact_base_conversions",
        "recommendation_impact_potential_conversions",
        "recommendation_impact_base_conversion_value",
        "recommendation_impact_potential_conversion_value",
    }
    impact_available = any(name in facts_by_name for name in impact_fact_names)
    base_clicks = _int_metric_value(facts_by_name.get("recommendation_impact_base_clicks"))
    potential_clicks = _int_metric_value(
        facts_by_name.get("recommendation_impact_potential_clicks")
    )
    base_impressions = _int_metric_value(
        facts_by_name.get("recommendation_impact_base_impressions")
    )
    potential_impressions = _int_metric_value(
        facts_by_name.get("recommendation_impact_potential_impressions")
    )
    base_cost_micros = _int_metric_value(
        facts_by_name.get("recommendation_impact_base_cost_micros")
    )
    potential_cost_micros = _int_metric_value(
        facts_by_name.get("recommendation_impact_potential_cost_micros")
    )
    base_conversions = _float_metric_value(
        facts_by_name.get("recommendation_impact_base_conversions")
    )
    potential_conversions = _float_metric_value(
        facts_by_name.get("recommendation_impact_potential_conversions")
    )
    base_conversion_value = _float_metric_value(
        facts_by_name.get("recommendation_impact_base_conversion_value")
    )
    potential_conversion_value = _float_metric_value(
        facts_by_name.get("recommendation_impact_potential_conversion_value")
    )
    delta_clicks = _int_metric_delta(base_clicks, potential_clicks)
    delta_impressions = _int_metric_delta(base_impressions, potential_impressions)
    delta_cost_micros = _int_metric_delta(base_cost_micros, potential_cost_micros)
    delta_conversions = _float_metric_delta(base_conversions, potential_conversions)
    delta_conversion_value = _float_metric_delta(
        base_conversion_value,
        potential_conversion_value,
    )
    missing_metrics = [name for name in expected_metrics if name not in facts_by_name]
    if not impact_available:
        missing_metrics.append("recommendation_impact")
    recommendation_resource_name = first_dimensions.get("recommendation_resource_name")
    campaign_id = first_dimensions.get("campaign_id")
    campaign_budget_id = first_dimensions.get("campaign_budget_id")
    row_evidence_ids = _unique(fact.evidence_id for fact in facts)
    source_metric_names = _unique(fact.name for fact in facts)
    payload_preview = _recommendation_apply_preview(
        recommendation_id=recommendation_id,
        recommendation_resource_name=recommendation_resource_name,
        recommendation_type=recommendation_type,
        campaign_id=campaign_id,
        campaign_budget_id=campaign_budget_id,
        evidence_ids=row_evidence_ids,
        source_metric_names=source_metric_names,
    )
    review_score = _recommendation_review_score(
        recommendation_type=recommendation_type,
        campaign_id=campaign_id,
        campaign_count=_int_metric_value(
            facts_by_name.get("recommendation_campaign_count")
        ),
        impact_available=impact_available,
        delta_clicks=delta_clicks,
        delta_cost_micros=delta_cost_micros,
        delta_conversions=delta_conversions,
        payload_preview=payload_preview,
        missing_metrics=missing_metrics,
    )
    return AdsRecommendationRow(
        recommendation_id=recommendation_id,
        recommendation_resource_name=recommendation_resource_name,
        recommendation_type=recommendation_type,
        review_priority=_recommendation_review_priority(review_score),
        review_score=review_score,
        review_reason=_recommendation_review_reason(
            recommendation_type=recommendation_type,
            impact_available=impact_available,
            delta_clicks=delta_clicks,
            delta_cost_micros=delta_cost_micros,
            delta_conversions=delta_conversions,
            missing_metrics=missing_metrics,
        ),
        human_review_gates=[
            "sprawdź typ rekomendacji",
            "sprawdź metryki wpływu",
            "porównaj z historią zmian",
            "porównaj z celem biznesowym",
            "zweryfikuj RMF/compliance",
            "potwierdź człowiekiem przed zapisem",
        ],
        dismissed=first_dimensions.get("dismissed") == "true",
        campaign_id=campaign_id,
        campaign_budget_id=campaign_budget_id,
        campaign_count=_int_metric_value(
            facts_by_name.get("recommendation_campaign_count")
        ),
        impact_available=impact_available,
        base_clicks=base_clicks,
        potential_clicks=potential_clicks,
        delta_clicks=delta_clicks,
        base_impressions=base_impressions,
        potential_impressions=potential_impressions,
        delta_impressions=delta_impressions,
        base_cost_micros=base_cost_micros,
        potential_cost_micros=potential_cost_micros,
        delta_cost_micros=delta_cost_micros,
        base_conversions=base_conversions,
        potential_conversions=potential_conversions,
        delta_conversions=delta_conversions,
        base_conversion_value=base_conversion_value,
        potential_conversion_value=potential_conversion_value,
        delta_conversion_value=delta_conversion_value,
        evidence_ids=row_evidence_ids,
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        payload_preview=payload_preview,
        missing_metrics=missing_metrics,
        blocked_claims=[
            "zapis rekomendacji",
            "automatyczne przyjęcie rekomendacji",
            "zmiana budżetu",
            "zapis zmian kampanii",
        ],
    )


def _recommendation_review_score(
    *,
    recommendation_type: str,
    campaign_id: str | None,
    campaign_count: int | None,
    impact_available: bool,
    delta_clicks: int | None,
    delta_cost_micros: int | None,
    delta_conversions: float | None,
    payload_preview: AdsRecommendationApplyPreview | None,
    missing_metrics: list[str],
) -> int:
    score = 0.0
    if payload_preview is not None:
        score += 10
    if campaign_id:
        score += 10
    if campaign_count:
        score += min(campaign_count * 3, 10)
    if impact_available:
        score += 20
    score += min(abs(delta_cost_micros or 0) / 1_000_000, 20)
    score += min(abs(delta_clicks or 0) * 3, 15)
    score += min(abs(delta_conversions or 0) * 10, 15)
    if recommendation_type in {
        "CAMPAIGN_BUDGET",
        "IMPROVE_PERFORMANCE_MAX_AD_STRENGTH",
        "SEARCH_PARTNERS_OPT_IN",
    }:
        score += 10
    if "recommendation_impact" in missing_metrics:
        score = min(score, 35)
    return min(100, int(round(score)))


def _recommendation_review_priority(
    review_score: int,
) -> Literal["pilne", "wysokie", "normalne", "niski sygnał"]:
    if review_score >= 70:
        return "pilne"
    if review_score >= 45:
        return "wysokie"
    if review_score >= 15:
        return "normalne"
    return "niski sygnał"


def _recommendation_review_reason(
    *,
    recommendation_type: str,
    impact_available: bool,
    delta_clicks: int | None,
    delta_cost_micros: int | None,
    delta_conversions: float | None,
    missing_metrics: list[str],
) -> str:
    if impact_available:
        impact_part = (
            f"podgląd wpływu: zmiana kliknięć {_format_signed_number(delta_clicks)}, "
            f"zmiana kosztu {_format_micros(delta_cost_micros) or '0'}, "
            f"zmiana konwersji {_format_signed_number(delta_conversions)}"
        )
    else:
        impact_part = (
            "brak metryk wpływu; wymagane ręczne sprawdzenie typu rekomendacji "
            f"i brakujących metryk: {_missing_metric_labels(missing_metrics) or 'brak'}"
        )
    return (
        f"Rekomendacja: {_recommendation_type_label(recommendation_type)}. {impact_part}. "
        "To jest kolejność przeglądu rekomendacji, nie zgoda na zapis zmian ani obietnica "
        "poprawy wyniku."
    )


def _recommendation_apply_preview(
    *,
    recommendation_id: str | None,
    recommendation_resource_name: str | None,
    recommendation_type: str,
    campaign_id: str | None,
    campaign_budget_id: str | None,
    evidence_ids: list[str],
    source_metric_names: list[str],
) -> AdsRecommendationApplyPreview | None:
    if not evidence_ids:
        return None
    return AdsRecommendationApplyPreview(
        id=f"recommendation_apply_preview_{recommendation_id or recommendation_type}",
        recommendation_id=recommendation_id,
        recommendation_resource_name=recommendation_resource_name,
        recommendation_type=recommendation_type,
        campaign_id=campaign_id,
        campaign_budget_id=campaign_budget_id,
        reason=(
            "Podgląd rekomendacji Google Ads do sprawdzenia w WILQ. WILQ nie może "
            "zapisać zmian bez strategii, oceny zgodności, potwierdzenia "
            "człowieka i audytu."
        ),
        evidence_ids=evidence_ids,
        source_metric_names=source_metric_names,
        required_validation=RECOMMENDATION_REVIEW_REQUIRED_VALIDATION,
        blocked_claims=RECOMMENDATION_REVIEW_BLOCKED_CLAIMS,
        api_mutation_ready=False,
        apply_allowed=False,
        destructive=False,
    )


def _recommendation_row_sort_key(row: AdsRecommendationRow) -> tuple[str, str]:
    return (row.recommendation_type, row.recommendation_id or "")


def _recommendation_type_label(recommendation_type: object) -> str:
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
    value = str(recommendation_type)
    return labels.get(value, "typ rekomendacji do sprawdzenia")


def _missing_metric_labels(missing_metrics: list[str]) -> str:
    labels = {
        "recommendation_impact": "podgląd wpływu rekomendacji",
    }
    return ", ".join(
        labels.get(metric, "brakująca metryka rekomendacji do sprawdzenia")
        for metric in missing_metrics
    )


def _remove_missing_contract_names(
    missing_read_contracts: list[str],
    *contract_names: str,
) -> list[str]:
    removals = set(contract_names)
    return [contract for contract in missing_read_contracts if contract not in removals]


def _int_metric_value(fact: MetricFact | None) -> int | None:
    if fact is None:
        return None
    try:
        return int(float(fact.value))
    except (TypeError, ValueError):
        return None


def _float_metric_value(fact: MetricFact | None) -> float | None:
    if fact is None:
        return None
    try:
        return float(fact.value)
    except (TypeError, ValueError):
        return None


def _int_metric_delta(base: int | None, potential: int | None) -> int | None:
    if base is None or potential is None:
        return None
    return potential - base


def _float_metric_delta(base: float | None, potential: float | None) -> float | None:
    if base is None or potential is None:
        return None
    return potential - base


def _format_signed_number(value: int | float | None) -> str:
    if value is None:
        return "brak danych"
    if isinstance(value, float) and not value.is_integer():
        formatted = f"{value:+.2f}"
    else:
        formatted = f"{int(value):+d}"
    return formatted


def _format_micros(value: float | None) -> str | None:
    if value is None:
        return None
    return f"{value / 1_000_000:.2f}"


def _unique(values: Iterable[object]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value)
        if text in seen:
            continue
        seen.add(text)
        unique_values.append(text)
    return unique_values
