from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from wilq.actions.validation_copy import (
    missing,
    missing_evidence,
    missing_review_check,
    no_api_write,
    no_destructive_change,
    no_write,
    row,
    wrong,
)
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    MetricFact,
    OpportunityDomain,
)

SEARCH_TERM_NGRAM_ACTION_ID = "act_review_ads_search_term_ngrams"
SEARCH_TERM_NGRAM_ACTION_TYPE = "google_ads_search_term_ngram_review"
SEARCH_TERM_NGRAM_PREVIEW_CONTRACT = "search_term_ngram_review_v1"
SEARCH_TERM_NGRAM_OPERATION_TYPE = "SearchTermNgramReview"


def search_term_ngram_action(
    *,
    google_ads_facts: list[MetricFact],
    search_term_ngram_payload: dict[str, Any],
) -> ActionObject:
    source_terms = {
        term
        for preview in search_term_ngram_payload["ngram_preview"][:8]
        if isinstance(preview, dict)
        for term in preview.get("sample_search_terms", [])
        if isinstance(term, str)
    }
    metrics = [
        fact
        for fact in google_ads_facts
        if fact.name in search_term_ngram_payload["source_metric_names"]
        and fact.evidence_id in search_term_ngram_payload["evidence_ids"]
        and fact.dimensions.get("search_term") in source_terms
    ][:12]
    return ActionObject(
        id=SEARCH_TERM_NGRAM_ACTION_ID,
        title="Przygotuj ocenę tematów z n-gramów wyszukiwanych haseł",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=search_term_ngram_payload["evidence_ids"],
        metrics=metrics,
        human_diagnosis=(
            "Google Ads ma fakty wyszukiwanych haseł, które tworzą powtarzające się "
            "tematy n-gram. WILQ może przygotować kolejkę oceny intencji, ale "
            "nie może traktować n-gramów jako gotowych wykluczeń ani obiecywać "
            "zmarnowanego budżetu bez sprawdzenia."
        ),
        recommended_reason=(
            "W widoku Google Ads przejrzyj n-gramy z kosztem, kliknięciami i "
            "przykładowymi wyszukiwanymi hasłami. Dopiero po ręcznej ocenie intencji wróć "
            "do kolejki sprawdzenia wykluczeń."
        ),
        payload=search_term_ngram_payload,
        validation_status="not_validated",
        created_by="system_metric_seed",
    )


def search_term_ngram_action_from_metric_facts(
    google_ads_facts: list[MetricFact],
) -> ActionObject | None:
    payload = search_term_ngram_payload_from_metric_facts(google_ads_facts)
    if payload is None:
        return None
    return search_term_ngram_action(
        google_ads_facts=google_ads_facts,
        search_term_ngram_payload=payload,
    )
SEARCH_TERM_NGRAM_REQUIRED_VALIDATION = [
    "review_ngram_intent",
    "review_source_search_terms",
    "compare_90_day_safety_read",
    "negative_keyword_action_validation",
    "human_confirm_before_apply",
]
SEARCH_TERM_NGRAM_BLOCKED_CLAIMS = [
    "marnowanie budżetu na zapytaniach",
    "dodanie wykluczających słów kluczowych",
    "utrata konwersji",
    "koszt pozyskania celu",
    "zwrot z reklam",
]
SEARCH_TERM_NGRAM_STOPWORDS = {
    "a",
    "albo",
    "bez",
    "dla",
    "do",
    "i",
    "lub",
    "na",
    "od",
    "oraz",
    "po",
    "s",
    "sa",
    "sp",
    "w",
    "we",
    "z",
    "za",
}


def search_term_ngram_payload_from_metric_facts(
    facts: list[MetricFact],
) -> dict[str, Any] | None:
    groups = _ngram_fact_groups(facts)
    if not groups:
        return None
    preview_items = [
        _ngram_preview(ngram, ngram_size, group_facts)
        for (ngram, ngram_size), group_facts in groups.items()
    ]
    previews = sorted(
        preview_items,
        key=lambda preview: (
            -int(preview.get("cost_micros") or 0),
            -int(preview.get("clicks") or 0),
            -int(preview.get("source_search_term_count") or 0),
            int(preview.get("ngram_size") or 99),
            str(preview.get("ngram") or ""),
        ),
    )[:8]
    evidence_ids = _unique(
        evidence_id for preview in previews for evidence_id in preview.get("evidence_ids", [])
    )
    if not evidence_ids:
        return None
    return {
        "action_type": SEARCH_TERM_NGRAM_ACTION_TYPE,
        "connector": "google_ads",
        "mode": "prepare_only",
        "preview_contract": SEARCH_TERM_NGRAM_PREVIEW_CONTRACT,
        "operation_type": SEARCH_TERM_NGRAM_OPERATION_TYPE,
        "ngram_preview": previews,
        "source_metric_names": _unique(
            metric_name
            for preview in previews
            for metric_name in preview.get("source_metric_names", [])
        ),
        "source_search_terms": _unique(
            term for preview in previews for term in preview.get("sample_search_terms", [])
        ),
        "evidence_ids": evidence_ids,
        "missing_read_contracts": [
            "human_intent_review",
            "ngram_to_negative_keyword_change_preview",
        ],
        "required_validation": SEARCH_TERM_NGRAM_REQUIRED_VALIDATION,
        "blocked_claims": SEARCH_TERM_NGRAM_BLOCKED_CLAIMS,
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
    }


def validate_search_term_ngram_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    subject = "Przegląd grup wyszukiwanych haseł"
    if not payload.get("evidence_ids"):
        errors.append(missing_evidence(subject))
    if payload.get("preview_contract") != SEARCH_TERM_NGRAM_PREVIEW_CONTRACT:
        errors.append(missing(subject, "poprawnego kontraktu podglądu"))
    if payload.get("operation_type") != SEARCH_TERM_NGRAM_OPERATION_TYPE:
        errors.append(missing(subject, "poprawnego typu operacji"))
    if payload.get("apply_allowed") is not False:
        errors.append(no_write(subject))
    if payload.get("destructive") is not False:
        errors.append(no_destructive_change(subject))
    if payload.get("api_mutation_ready") is not False:
        errors.append(no_api_write(subject))
    required_validation = payload.get("required_validation")
    if not isinstance(required_validation, list):
        errors.append(missing(subject, "listy wymaganych sprawdzeń"))
    else:
        for required_check in SEARCH_TERM_NGRAM_REQUIRED_VALIDATION:
            if required_check not in required_validation:
                errors.append(missing_review_check(subject))
    previews = payload.get("ngram_preview")
    if not isinstance(previews, list) or not previews:
        errors.append(missing(subject, "podglądu grup haseł"))
        return errors
    for index, preview in enumerate(previews):
        preview_subject = row("Podgląd grupy haseł", index)
        if not isinstance(preview, dict):
            errors.append(wrong(preview_subject, "ma nieprawidłową strukturę"))
            continue
        if preview.get("operation_type") != SEARCH_TERM_NGRAM_OPERATION_TYPE:
            errors.append(missing(preview_subject, "poprawnego typu operacji"))
        if not preview.get("ngram"):
            errors.append(missing(preview_subject, "grupy haseł"))
        if not preview.get("sample_search_terms"):
            errors.append(missing(preview_subject, "przykładowych wyszukiwanych haseł"))
        if not preview.get("evidence_ids"):
            errors.append(missing_evidence(preview_subject))
        if preview.get("api_mutation_ready") is not False:
            errors.append(no_api_write(preview_subject))
        if preview.get("apply_allowed") is not False:
            errors.append(no_write(preview_subject))
        if preview.get("destructive") is not False:
            errors.append(no_destructive_change(preview_subject))
    return errors


def _ngram_fact_groups(
    facts: list[MetricFact],
) -> dict[tuple[str, int], list[MetricFact]]:
    grouped_by_search_term: dict[tuple[str, str | None, str | None], list[MetricFact]] = {}
    for fact in facts:
        if fact.source_connector != "google_ads" or not fact.name.startswith("search_term_"):
            continue
        search_term = fact.dimensions.get("search_term")
        if not search_term:
            continue
        key = (
            search_term,
            fact.dimensions.get("campaign_id"),
            fact.dimensions.get("ad_group_id"),
        )
        grouped_by_search_term.setdefault(key, []).append(fact)

    grouped_by_ngram: dict[tuple[str, int], list[MetricFact]] = {}
    for (search_term, _, _), group_facts in grouped_by_search_term.items():
        if not _has_positive_signal(group_facts):
            continue
        tokens = _search_term_tokens(search_term)
        for ngram_size in (1, 2, 3):
            if len(tokens) < ngram_size:
                continue
            seen_for_term: set[tuple[str, int]] = set()
            for index in range(0, len(tokens) - ngram_size + 1):
                ngram = " ".join(tokens[index : index + ngram_size])
                ngram_key = (ngram, ngram_size)
                if ngram_key in seen_for_term:
                    continue
                seen_for_term.add(ngram_key)
                grouped_by_ngram.setdefault(ngram_key, []).extend(group_facts)
    return grouped_by_ngram


def _ngram_preview(
    ngram: str,
    ngram_size: int,
    facts: list[MetricFact],
) -> dict[str, Any]:
    search_terms = _unique(
        fact.dimensions.get("search_term") for fact in facts if fact.dimensions.get("search_term")
    )
    return {
        "id": f"search_term_ngram_review_{_slug(ngram)}_{ngram_size}",
        "ngram": ngram,
        "ngram_size": ngram_size,
        "source_search_term_count": len(search_terms),
        "sample_search_terms": search_terms[:5],
        "clicks": _sum_metric(facts, "search_term_clicks"),
        "impressions": _sum_metric(facts, "search_term_impressions"),
        "cost_micros": _sum_metric(facts, "search_term_cost_micros"),
        "conversions": _sum_metric(facts, "search_term_conversions"),
        "conversion_value": _sum_metric(facts, "search_term_conversion_value"),
        "operation_type": SEARCH_TERM_NGRAM_OPERATION_TYPE,
        "reason": (
            "Podgląd powtarzającego się tematu w wyszukiwanych hasłach do sprawdzenia w WILQ. "
            "To skraca analizę intencji, ale nie jest gotowym wykluczeniem."
        ),
        "missing_read_contracts": [
            "human_intent_review",
            "ngram_to_negative_keyword_change_preview",
        ],
        "required_validation": SEARCH_TERM_NGRAM_REQUIRED_VALIDATION,
        "blocked_claims": SEARCH_TERM_NGRAM_BLOCKED_CLAIMS,
        "source_metric_names": _unique(fact.name for fact in facts),
        "evidence_ids": _unique(fact.evidence_id for fact in facts),
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
    }


def _search_term_tokens(search_term: str) -> list[str]:
    tokens = re.findall(r"[\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+", search_term.lower())
    return [
        token for token in tokens if len(token) > 1 and token not in SEARCH_TERM_NGRAM_STOPWORDS
    ]


def _has_positive_signal(facts: list[MetricFact]) -> bool:
    return any(
        fact.name
        in {
            "search_term_clicks",
            "search_term_impressions",
            "search_term_cost_micros",
            "search_term_conversions",
            "search_term_conversion_value",
        }
        and isinstance(fact.value, int | float)
        and fact.value > 0
        for fact in facts
    )


def _sum_metric(facts: list[MetricFact], name: str) -> int | float:
    values = [
        fact.value for fact in facts if fact.name == name and isinstance(fact.value, int | float)
    ]
    total = sum(values)
    return int(total) if float(total).is_integer() else round(float(total), 6)


def _slug(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value).strip("_")


def _unique(values: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
