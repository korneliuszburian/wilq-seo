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
    return errors


def negative_keyword_payload_from_metric_facts(facts: list[MetricFact]) -> dict[str, Any] | None:
    candidate_facts = [
        fact for group in _candidate_fact_groups(facts) for fact in group
    ]
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
    return {
        "action_type": "negative_keyword_candidate",
        "connector": "google_ads",
        "mode": "prepare_only",
        "terms": terms[:20],
        "source_terms": terms[:20],
        "source_metric_names": _unique(fact.name for fact in candidate_facts),
        "evidence_ids": evidence_ids,
        "required_validation": [
            "review_search_term_context",
            "check_existing_keywords_and_match_types",
            "90_day_safety_check",
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


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
