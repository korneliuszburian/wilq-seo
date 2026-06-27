from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, Literal

from wilq.schemas import Ga4TrackingQualityPayloadPreview, MetricFact

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
GA4_TRACKING_REQUIRED_VALIDATION = [
    "review_landing_page_dimension",
    "review_source_medium_dimension",
    "review_campaign_name_dimension",
    "review_conversion_or_key_event_mapping",
    "human_confirm_before_tracking_change",
]


def validate_ga4_tracking_quality_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    preview = payload.get("payload_preview")
    if not isinstance(preview, list) or not preview:
        errors.append("GA4 tracking payload requires payload_preview list.")
        return errors
    for item in preview:
        if not isinstance(item, dict):
            errors.append("GA4 tracking payload_preview items must be objects.")
            continue
        if item.get("preview_contract") != GA4_TRACKING_QUALITY_PREVIEW_CONTRACT:
            errors.append("GA4 tracking podgląd zmian_contract is invalid.")
        if not isinstance(item.get("tracking_dimension_gaps"), list):
            errors.append("GA4 tracking payload requires tracking_dimension_gaps list.")
        if item.get("apply_allowed") is not False:
            errors.append("GA4 tracking podgląd zmian must keep apply_allowed=false.")
        if item.get("api_mutation_ready") is not False:
            errors.append("GA4 tracking podgląd zmian must keep api_mutation_ready=false.")
        if item.get("destructive") is not False:
            errors.append("GA4 tracking podgląd zmian must keep destructive=false.")
    return errors


def ga4_tracking_quality_payload_from_metric_facts(facts: list[MetricFact]) -> dict[str, Any]:
    review_rows = _review_rows(facts)
    return {
        "action_type": GA4_TRACKING_QUALITY_ACTION_TYPE,
        "connector": "google_analytics_4",
        "mode": "prepare_only",
        "preview_contract": GA4_TRACKING_QUALITY_PREVIEW_CONTRACT,
        "source_metric_names": _unique(fact.name for fact in facts),
        "required_breakdowns": ["landing_page", "source_medium", "campaign_name"],
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
                landing_page=landing_page or None,
                source_medium=source_medium or None,
                campaign_name=campaign_name or None,
                tracking_dimension_gaps=dimension_gaps,
                metric_snapshot=_metric_snapshot(group),
                reason=_reason(dimension_gaps),
                required_validation=GA4_TRACKING_REQUIRED_VALIDATION,
                blocked_claims=GA4_TRACKING_BLOCKED_CLAIMS,
                evidence_ids=_unique(fact.evidence_id for fact in group),
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


def _metric_snapshot(facts: list[MetricFact]) -> dict[str, float | int | str]:
    snapshot: dict[str, float | int | str] = {}
    for fact in facts:
        snapshot[fact.name] = fact.value
    return snapshot


def _reason(gaps: Sequence[str]) -> str:
    if gaps:
        return (
            "Checklist brakujących wymiarów GA4 do sprawdzenia w WILQ. To blokuje "
            "wnioski o konwersjach i jakości kampanii do czasu sprawdzenia pomiaru."
        )
    return (
        "Lista sprawdzenia jakości strony wejścia, źródła ruchu i kampanii w WILQ. To pozwala "
        "sprawdzić dopasowanie komunikatu, ale nie odblokowuje obietnic zwrotu z reklam ani przychodu."
    )


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
