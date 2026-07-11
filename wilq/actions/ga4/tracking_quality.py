from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, Literal

from wilq.actions.validation_copy import (
    missing,
    no_api_write,
    no_destructive_change,
    no_write,
    row,
    wrong,
)
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    Ga4TrackingQualityPayloadPreview,
    MetricFact,
    OpportunityDomain,
)

GA4_TRACKING_QUALITY_ACTION_TYPE = "ga4_tracking_gap"
GA4_TRACKING_QUALITY_PREVIEW_CONTRACT: Literal["ga4_tracking_quality_review_v1"] = (
    "ga4_tracking_quality_review_v1"
)
GA4_TRACKING_BLOCKED_CLAIMS = [
    "współczynnik konwersji",
    "zwrot z reklam",
    "przychód",
    "opłacalność",
    "spadek konwersji",
    "diagnoza lejka",
    "ocena atrybucji",
    "naprawiony pomiar",
    "zapis w GA4",
]
GA4_TRACKING_METRIC_LABELS = {
    "active_users": "aktywni użytkownicy",
    "sessions": "sesje",
    "event_count": "zdarzenia",
    "screen_page_views": "odsłony",
    "engagement_rate": "zaangażowanie",
    "ecommerce_purchases": "zakupy e-commerce",
    "key_events": "zdarzenia kluczowe",
    "conversions": "konwersje",
    "purchase_revenue": "przychód z zakupu",
    "total_revenue": "przychód razem",
    "transactions": "transakcje",
}
GA4_TRACKING_REQUIRED_VALIDATION = [
    "review_landing_page_dimension",
    "review_source_medium_dimension",
    "review_campaign_name_dimension",
    "review_conversion_or_key_event_mapping",
    "human_confirm_before_tracking_change",
]


def seed_ga4_tracking_quality_action() -> ActionObject:
    evidence_id = connector_evidence_id("google_analytics_4")
    required_breakdowns = ["landing_page", "source_medium", "campaign"]
    required_labels = ["strona wejścia", "źródło i medium ruchu", "kampania"]
    return ActionObject(
        id="act_review_ga4_tracking_quality",
        title="Sprawdź jakość pomiaru GA4 przed oceną kampanii",
        domain=OpportunityDomain.ga4,
        connector="google_analytics_4",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=[evidence_id],
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
            "action_type": GA4_TRACKING_QUALITY_ACTION_TYPE,
            "connector": "google_analytics_4",
            "mode": "prepare_only",
            "preview_contract": GA4_TRACKING_QUALITY_PREVIEW_CONTRACT,
            "source_metric_names": [],
            "required_breakdowns": required_breakdowns,
            "required_breakdown_labels": required_labels,
            "required_validation": GA4_TRACKING_REQUIRED_VALIDATION,
            "blocked_claims": ["conversion_rate", "przychód", "roas"],
            "payload_preview": [
                {
                    "id": "ga4_tracking_review_connector_status",
                    "preview_contract": GA4_TRACKING_QUALITY_PREVIEW_CONTRACT,
                    "operation_type": "tracking_quality_review",
                    "landing_page": None,
                    "landing_page_label": "brak strony wejścia w raporcie",
                    "source_medium": None,
                    "source_medium_label": "brak źródła i medium w raporcie",
                    "campaign_name": None,
                    "campaign_name_label": "brak kampanii w raporcie",
                    "tracking_dimension_gaps": required_breakdowns,
                    "metric_snapshot": {},
                    "metric_snapshot_labels": {},
                    "reason": (
                        "Brak wymiarowych GA4 facts. Najpierw zbierz zestawienie "
                        "strony wejścia, źródła ruchu i kampanii z GA4."
                    ),
                    "required_validation": GA4_TRACKING_REQUIRED_VALIDATION,
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
                    "evidence_ids": [evidence_id],
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
    )


def ga4_tracking_quality_action(
    *,
    ga4_action_metrics: list[MetricFact],
    metric_sentence: str,
) -> ActionObject:
    return ActionObject(
        id="act_review_ga4_tracking_quality",
        title="Sprawdź jakość pomiaru GA4 przed oceną kampanii",
        domain=OpportunityDomain.ga4,
        connector="google_analytics_4",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=list(dict.fromkeys(fact.evidence_id for fact in ga4_action_metrics)),
        metrics=ga4_action_metrics,
        human_diagnosis=(
            "GA4 zwraca wymiarowe fakty strony wejścia, źródła ruchu i kampanii, ale WILQ "
            "nadal nie ma kontraktu na zwrot z reklam, przychód ani werdykt konwersji. "
            f"{metric_sentence}."
        ),
        recommended_reason=(
            "W widoku GA4 przygotuj przegląd pomiaru i jakości ruchu: pokaż "
            "zestawienie strony wejścia, źródła ruchu i kampanii, "
            "sprawdź propozycję w WILQ i nie "
            "oceniaj kampanii bez kontraktu konwersji."
        ),
        payload=ga4_tracking_quality_payload_from_metric_facts(ga4_action_metrics),
        validation_status="not_validated",
        created_by="system_metric_seed",
    )
GA4_TRACKING_REQUIRED_BREAKDOWNS = ["landing_page", "source_medium", "campaign_name"]


def validate_ga4_tracking_quality_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    subject = "Sprawdzenie pomiaru GA4"
    preview = payload.get("payload_preview")
    if not isinstance(preview, list) or not preview:
        errors.append(missing(subject, "podglądu sprawdzenia"))
        return errors
    for index, item in enumerate(preview):
        item_subject = row("Podgląd sprawdzenia GA4", index)
        if not isinstance(item, dict):
            errors.append(wrong(item_subject, "ma nieprawidłową strukturę"))
            continue
        if item.get("preview_contract") != GA4_TRACKING_QUALITY_PREVIEW_CONTRACT:
            errors.append(missing(item_subject, "poprawnego kontraktu podglądu"))
        if not isinstance(item.get("tracking_dimension_gaps"), list):
            errors.append(missing(item_subject, "listy braków w wymiarach pomiaru"))
        metric_snapshot = item.get("metric_snapshot")
        metric_snapshot_labels = item.get("metric_snapshot_labels")
        if (
            isinstance(metric_snapshot, dict)
            and metric_snapshot
            and not isinstance(metric_snapshot_labels, dict)
        ):
            errors.append(missing(item_subject, "etykiet widocznych metryk"))
        if item.get("apply_allowed") is not False:
            errors.append(no_write(item_subject))
        if item.get("api_mutation_ready") is not False:
            errors.append(no_api_write(item_subject))
        if item.get("destructive") is not False:
            errors.append(no_destructive_change(item_subject))
    return errors


def ga4_tracking_quality_payload_from_metric_facts(facts: list[MetricFact]) -> dict[str, Any]:
    review_rows = _review_rows(facts)
    return {
        "action_type": GA4_TRACKING_QUALITY_ACTION_TYPE,
        "connector": "google_analytics_4",
        "mode": "prepare_only",
        "preview_contract": GA4_TRACKING_QUALITY_PREVIEW_CONTRACT,
        "source_metric_names": _unique(fact.name for fact in facts),
        "required_breakdowns": GA4_TRACKING_REQUIRED_BREAKDOWNS,
        "required_breakdown_labels": [
            _tracking_dimension_gap_label(value) for value in GA4_TRACKING_REQUIRED_BREAKDOWNS
        ],
        "required_validation": GA4_TRACKING_REQUIRED_VALIDATION,
        "blocked_claims": GA4_TRACKING_BLOCKED_CLAIMS,
        "payload_preview": review_rows,
        "destructive": False,
    }


def _review_rows(facts: list[MetricFact]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[MetricFact]] = {}
    for fact in facts:
        key = (
            fact.dimensions.get("landing_page") or "",
            fact.dimensions.get("source_medium") or "",
            fact.dimensions.get("campaign_name") or "",
        )
        grouped.setdefault(key, []).append(fact)

    rows: list[dict[str, Any]] = []
    for index, ((landing_page, source_medium, campaign_name), group) in enumerate(
        grouped.items(),
        start=1,
    ):
        dimension_gaps = _dimension_gaps(landing_page, source_medium, campaign_name)
        rows.append(
            Ga4TrackingQualityPayloadPreview(
                id=f"ga4_tracking_review_{index}",
                preview_contract=GA4_TRACKING_QUALITY_PREVIEW_CONTRACT,
                operation_type="tracking_quality_review",
                operation_type_label=_operation_type_label("tracking_quality_review"),
                landing_page=landing_page or None,
                landing_page_label=_dimension_value_label(
                    landing_page,
                    missing_label="brak strony wejścia w raporcie",
                ),
                source_medium=source_medium or None,
                source_medium_label=_dimension_value_label(
                    source_medium,
                    missing_label="brak źródła i medium w raporcie",
                ),
                campaign_name=campaign_name or None,
                campaign_name_label=_dimension_value_label(
                    campaign_name,
                    missing_label="brak kampanii w raporcie",
                ),
                tracking_dimension_gaps=dimension_gaps,
                tracking_dimension_gap_labels=[
                    _tracking_dimension_gap_label(value) for value in dimension_gaps
                ],
                metric_snapshot=_metric_snapshot(group),
                metric_snapshot_labels=_metric_snapshot_labels(group),
                reason=_reason(dimension_gaps),
                required_validation=GA4_TRACKING_REQUIRED_VALIDATION,
                required_validation_labels=[
                    _validation_label(value) for value in GA4_TRACKING_REQUIRED_VALIDATION
                ],
                blocked_claims=GA4_TRACKING_BLOCKED_CLAIMS,
                blocked_claim_labels=[
                    _blocked_claim_label(value) for value in GA4_TRACKING_BLOCKED_CLAIMS
                ],
                evidence_ids=_unique(fact.evidence_id for fact in group),
                evidence_summary_label=_evidence_summary_label(
                    _unique(fact.evidence_id for fact in group)
                ),
                api_mutation_ready=False,
                apply_allowed=False,
                destructive=False,
            ).model_dump(mode="json")
        )
    return rows[:8]


def _dimension_gaps(
    landing_page: str,
    source_medium: str,
    campaign_name: str,
) -> list[Literal["landing_page", "source_medium", "campaign_name"]]:
    gaps: list[Literal["landing_page", "source_medium", "campaign_name"]] = []
    if not landing_page or landing_page == "(not set)":
        gaps.append("landing_page")
    if not source_medium or source_medium == "(not set)":
        gaps.append("source_medium")
    if not campaign_name or campaign_name == "(not set)":
        gaps.append("campaign_name")
    return gaps


def _operation_type_label(value: str) -> str:
    labels = {
        "tracking_quality_review": "ocena jakości pomiaru",
    }
    return labels.get(value, "typ sprawdzenia GA4 do weryfikacji")


def _tracking_dimension_gap_label(value: str) -> str:
    labels = {
        "landing_page": "strona wejścia",
        "source_medium": "źródło i medium ruchu",
        "campaign_name": "kampania",
    }
    return labels.get(value, "wymiar GA4 do sprawdzenia")


def _metric_snapshot(facts: list[MetricFact]) -> dict[str, float | int | str]:
    snapshot: dict[str, float | int | str] = {}
    for fact in facts:
        snapshot[fact.name] = fact.value
    return snapshot


def _metric_snapshot_labels(facts: list[MetricFact]) -> dict[str, str]:
    return {fact.name: GA4_TRACKING_METRIC_LABELS.get(fact.name, "metryka GA4") for fact in facts}


def _dimension_value_label(value: str, *, missing_label: str) -> str:
    if not value or value == "(not set)":
        return missing_label
    return value


def _validation_label(value: str) -> str:
    labels = {
        "review_landing_page_dimension": "sprawdź stronę wejścia",
        "review_source_medium_dimension": "sprawdź źródło i medium ruchu",
        "review_campaign_name_dimension": "sprawdź kampanię",
        "review_conversion_or_key_event_mapping": "sprawdź konwersje i zdarzenia kluczowe",
        "human_confirm_before_tracking_change": "potwierdź sprawdzenie przez człowieka",
    }
    return labels.get(value, "warunek GA4 do sprawdzenia")


def _blocked_claim_label(value: str) -> str:
    labels = {
        "conversion_rate": "współczynnik konwersji",
        "roas": "zwrot z reklam",
        "współczynnik konwersji": "współczynnik konwersji",
        "zwrot z reklam": "zwrot z reklam",
        "przychód": "przychód",
        "opłacalność": "opłacalność",
        "spadek konwersji": "spadek konwersji",
        "diagnoza lejka": "diagnoza lejka",
        "ocena atrybucji": "ocena atrybucji",
        "naprawiony pomiar": "naprawiony pomiar",
        "zapis w GA4": "zapis w GA4",
    }
    return labels.get(value, "wniosek GA4 do sprawdzenia")


def _evidence_summary_label(evidence_ids: Iterable[str]) -> str:
    count = len(list(evidence_ids))
    if count == 0:
        return "Nie ma dowodów źródłowych; nie traktuj tego jako rekomendacji"
    if count == 1:
        return "1 dowód źródłowy"
    if 2 <= count <= 4:
        return f"{count} dowody źródłowe"
    return f"{count} dowodów źródłowych"


def _reason(gaps: Sequence[str]) -> str:
    if gaps:
        return (
            "Checklist brakujących wymiarów GA4 do sprawdzenia w WILQ. To blokuje "
            "wnioski o konwersjach i jakości kampanii do czasu sprawdzenia pomiaru."
        )
    return (
        "Lista sprawdzenia jakości strony wejścia, źródła ruchu i kampanii w WILQ. "
        "To pozwala sprawdzić dopasowanie komunikatu, ale nie odblokowuje obietnic "
        "zwrotu z reklam ani przychodu."
    )


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
