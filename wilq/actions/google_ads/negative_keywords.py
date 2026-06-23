from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from wilq.schemas import MetricFact

NEGATIVE_KEYWORD_ACTION_ID = "act_prepare_negative_keyword_review_queue"
NEGATIVE_KEYWORD_BLOCKED_CLAIMS = [
    "negative keyword apply",
    "search-term waste",
    "conversion loss",
    "CPA",
    "ROAS",
]


def validate_negative_keyword_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not payload.get("terms"):
        errors.append("Negative keyword review payload requires evidence-backed terms.")
    if not payload.get("evidence_ids"):
        errors.append("Negative keyword review payload requires evidence IDs.")
    if payload.get("apply_allowed") is not False:
        errors.append("Negative keyword review payload must keep apply_allowed=false.")
    if payload.get("destructive") is not False:
        errors.append("Negative keyword review payload must be non-destructive.")
    required_validation = payload.get("required_validation")
    if (
        not isinstance(required_validation, list)
        or "90_day_safety_check" not in required_validation
    ):
        errors.append("Negative keyword review payload requires 90_day_safety_check.")
    preview_items = payload.get("payload_preview")
    if not isinstance(preview_items, list) or not preview_items:
        errors.append("Negative keyword review payload requires payload_preview.")
        return errors
    for index, item in enumerate(preview_items):
        if not isinstance(item, dict):
            errors.append(f"Negative keyword payload preview item {index} must be object.")
            continue
        if item.get("match_type") != "EXACT":
            errors.append(
                f"Negative keyword payload preview item {index} must use EXACT match."
            )
        if item.get("apply_allowed") is not False:
            errors.append(
                f"Negative keyword payload preview item {index} must keep apply_allowed=false."
            )
        if item.get("destructive") is not False:
            errors.append(
                f"Negative keyword payload preview item {index} must be non-destructive."
            )
        if item.get("api_mutation_ready") is not False:
            errors.append(
                f"Negative keyword payload preview item {index} must not be API-mutation ready."
            )
        if not item.get("evidence_ids"):
            errors.append(
                f"Negative keyword payload preview item {index} requires evidence IDs."
            )
    return errors


def negative_keyword_payload_from_metric_facts(facts: list[MetricFact]) -> dict[str, Any] | None:
    candidate_groups = _candidate_fact_groups(facts)
    candidate_facts = [fact for group in candidate_groups for fact in group]
    terms = _unique(
        fact.dimensions["search_term"]
        for fact in candidate_facts
        if fact.dimensions.get("search_term")
    )
    if not terms:
        return None
    evidence_ids = _unique(fact.evidence_id for fact in candidate_facts)
    if not evidence_ids:
        return None
    payload_preview = _payload_preview_items(candidate_groups)
    if not payload_preview:
        return None
    keyword_context = _keyword_context_items(facts)
    return {
        "action_type": "negative_keyword_candidate",
        "connector": "google_ads",
        "mode": "prepare_only",
        "terms": terms[:20],
        "source_terms": terms[:20],
        "source_metric_names": _unique(fact.name for fact in candidate_facts),
        "evidence_ids": evidence_ids,
        "preview_contract": "negative_keyword_payload_preview_v1",
        "api_mutation_ready": False,
        "payload_preview": payload_preview[:20],
        "keyword_match_context_available": bool(keyword_context),
        "keyword_match_context": keyword_context[:50],
        "required_validation": [
            "review_search_term_context",
            "check_existing_keywords_and_match_types",
            "90_day_safety_check",
            "negative_keyword_payload_preview",
            "human_confirm_before_apply",
        ],
        "blocked_claims": NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
        "apply_allowed": False,
        "destructive": False,
    }


def _is_search_term_fact(fact: MetricFact) -> bool:
    return fact.source_connector == "google_ads" and fact.name.startswith("search_term_")


def _eligible_source_term(term: str) -> bool:
    normalized = term.strip().lower()
    if len(normalized) < 3:
        return False
    if "ekologus" in normalized:
        return False
    return any(character.isalpha() for character in normalized)


def _fact_supports_review_candidate(fact: MetricFact) -> bool:
    if fact.name not in {"search_term_clicks", "search_term_cost_micros"}:
        return False
    value = fact.value
    return isinstance(value, int | float) and value > 0


def _candidate_fact_groups(facts: list[MetricFact]) -> list[list[MetricFact]]:
    grouped: dict[tuple[str, str | None, str | None], list[MetricFact]] = {}
    for fact in facts:
        if not _is_search_term_fact(fact):
            continue
        term = fact.dimensions.get("search_term", "")
        if not _eligible_source_term(term):
            continue
        key = (
            term,
            fact.dimensions.get("campaign_id"),
            fact.dimensions.get("ad_group_id"),
        )
        grouped.setdefault(key, []).append(fact)

    groups: list[list[MetricFact]] = []
    for group_facts in grouped.values():
        has_activity = any(_fact_supports_review_candidate(fact) for fact in group_facts)
        has_conversion = any(_fact_has_conversion_signal(fact) for fact in group_facts)
        if has_activity and not has_conversion:
            groups.append(group_facts)
    return groups


def _keyword_context_items(facts: list[MetricFact]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str | None, str | None, str | None], list[MetricFact]] = {}
    for fact in facts:
        if fact.name not in {
            "keyword_match_context_available",
            "keyword_match_type",
            "keyword_match_context_negative",
        }:
            continue
        keyword_text = fact.dimensions.get("keyword_text")
        if not keyword_text:
            continue
        key = (
            keyword_text,
            fact.dimensions.get("campaign_id"),
            fact.dimensions.get("ad_group_id"),
            fact.dimensions.get("criterion_id"),
        )
        grouped.setdefault(key, []).append(fact)

    items: list[dict[str, Any]] = []
    for (keyword_text, campaign_id, ad_group_id, criterion_id), group in grouped.items():
        first_dimensions = group[0].dimensions
        match_type = next(
            (
                str(fact.value)
                for fact in group
                if fact.name == "keyword_match_type" and fact.value
            ),
            first_dimensions.get("keyword_match_type", "UNKNOWN"),
        )
        negative = any(
            fact.name == "keyword_match_context_negative"
            and isinstance(fact.value, int | float)
            and fact.value > 0
            for fact in group
        )
        items.append(
            {
                "keyword_text": keyword_text,
                "match_type": match_type,
                "criterion_id": criterion_id,
                "criterion_status": first_dimensions.get("criterion_status"),
                "negative": negative,
                "campaign_id": campaign_id,
                "campaign_name": first_dimensions.get("campaign_name"),
                "ad_group_id": ad_group_id,
                "ad_group_name": first_dimensions.get("ad_group_name"),
                "evidence_ids": _unique(fact.evidence_id for fact in group),
            }
        )
    return sorted(
        items,
        key=lambda item: (
            item.get("campaign_name") or item.get("campaign_id") or "",
            item.get("ad_group_name") or "",
            item["keyword_text"],
        ),
    )


def _fact_has_conversion_signal(fact: MetricFact) -> bool:
    if fact.name not in {
        "search_term_conversions",
        "search_term_conversion_value",
        "search_term_90d_conversions",
        "search_term_90d_conversion_value",
    }:
        return False
    value = fact.value
    return isinstance(value, int | float) and value > 0


def _payload_preview_items(groups: list[list[MetricFact]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for group in groups:
        first_fact = group[0]
        dimensions = first_fact.dimensions
        search_term = dimensions.get("search_term")
        if not search_term:
            continue
        ad_group_id = dimensions.get("ad_group_id")
        campaign_id = dimensions.get("campaign_id")
        evidence_ids = _unique(fact.evidence_id for fact in group)
        if not evidence_ids:
            continue
        preview_id_parts = [
            "negative_keyword_preview",
            campaign_id or "campaign",
            ad_group_id or "ad_group",
            search_term,
        ]
        level = "ad_group" if ad_group_id else "campaign_review_required"
        reason = (
            "Podgląd oceny dokładnego wykluczenia zbudowany z faktów wyszukiwanych haseł "
            "i 90-dniowego odczytu bezpieczeństwa. To nie jest gotowa mutacja API."
        )
        if level == "campaign_review_required":
            reason = (
                "Brak ad_group_id w dowodach, więc WILQ pokazuje tylko podgląd "
                "oceny i wymaga decyzji człowieka o poziomie kampanii/grupy."
            )
        items.append(
            {
                "id": "_".join(_slug(part) for part in preview_id_parts),
                "search_term": search_term,
                "negative_keyword_text": search_term,
                "match_type": "EXACT",
                "level": level,
                "campaign_id": campaign_id,
                "campaign_name": dimensions.get("campaign_name"),
                "ad_group_id": ad_group_id,
                "ad_group_name": dimensions.get("ad_group_name"),
                "reason": reason,
                "evidence_ids": evidence_ids,
                "source_metric_names": _unique(fact.name for fact in group),
                "required_validation": [
                    "review_search_term_context",
                    "check_existing_keywords_and_match_types",
                    "90_day_safety_check",
                    "human_confirm_before_apply",
                ],
                "blocked_claims": NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
                "api_mutation_ready": False,
                "apply_allowed": False,
                "destructive": False,
            }
        )
    return items


def _slug(value: str) -> str:
    return "".join(character.lower() if character.isalnum() else "_" for character in value)[
        :80
    ].strip("_") or "item"


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
