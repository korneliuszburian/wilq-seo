from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from wilq.actions.validation_copy import (
    missing,
    missing_evidence,
    no_api_write,
    no_write,
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

CUSTOM_SEGMENT_ACTION_ID = "act_prepare_custom_segments_from_search_terms"
CUSTOM_SEGMENT_BLOCKED_CLAIMS = [
    "rozmiar odbiorców",
    "wzrost konwersji",
    "zwrot z reklam",
    "zapis kierowania reklam",
    "skuteczność kampanii",
]
CUSTOM_SEGMENT_APPLY_SAFETY_CONTRACT = "custom_segment_apply_safety_v1"
CUSTOM_SEGMENT_APPLY_SAFETY_REQUIRED_VALIDATION = [
    "review_source_terms",
    "reject_brand_or_low_intent_terms",
    "keyword_planner_enrichment",
    "forecast_or_audience_size",
    "custom_segment_operation_preview",
    "google_ads_mutation_audit",
    "human_confirm_before_apply",
]


def custom_segment_action(
    *,
    google_ads_facts: list[MetricFact],
    custom_segment_payload: dict[str, Any],
) -> ActionObject:
    metrics = [
        fact
        for fact in google_ads_facts
        if fact.name.startswith("search_term_")
        and fact.dimensions.get("search_term") in custom_segment_payload["terms"]
    ][:12]
    return ActionObject(
        id=CUSTOM_SEGMENT_ACTION_ID,
        title="Przygotuj propozycje segmentów z wyszukiwanych haseł",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=list(dict.fromkeys(fact.evidence_id for fact in metrics)),
        metrics=metrics,
        human_diagnosis=(
            "Google Ads ma realne fakty z wyszukiwanych haseł. WILQ może przygotować "
            "propozycje segmentów wyłącznie z tych terminów, ale nie może "
            "twierdzić nic o rozmiarze odbiorców, zwrocie z reklam ani skuteczności bez "
            "dodatkowych kontraktów."
        ),
        recommended_reason=(
            "W widoku Google Ads przejrzyj hasła źródłowe, odrzuć brandowe i "
            "niskointencyjne frazy, dodaj wzbogacenie Keyword Planner i sprawdź w WILQ "
            "podgląd zmian przed zapisem zmian."
        ),
        payload=custom_segment_payload,
        validation_status="not_validated",
        created_by="system_metric_seed",
    )


def custom_segment_action_from_metric_facts(
    google_ads_facts: list[MetricFact],
) -> ActionObject | None:
    payload = custom_segment_payload_from_metric_facts(google_ads_facts)
    if payload is None:
        return None
    return custom_segment_action(
        google_ads_facts=google_ads_facts,
        custom_segment_payload=payload,
    )


def validate_custom_segment_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    subject = "Segment niestandardowy Google Ads"
    if not payload.get("terms"):
        errors.append(missing(subject, "haseł opartych na dowodach"))
    if payload.get("invented_terms") is True:
        errors.append(wrong(subject, "nie może zawierać wymyślonych haseł"))
    if not payload.get("evidence_ids"):
        errors.append(missing_evidence(subject))
    preview = payload.get("payload_preview")
    if not isinstance(preview, list) or not preview:
        errors.append(missing(subject, "bezpiecznego podglądu zmian"))
    elif any(item.get("apply_allowed") is not False for item in preview if isinstance(item, dict)):
        errors.append(no_write(f"{subject}, podgląd zmian"))
    else:
        for item in preview:
            if not isinstance(item, dict):
                continue
            targeting_preview = item.get("targeting_preview")
            safety_review = item.get("safety_review")
            if not isinstance(safety_review, dict):
                errors.append(missing(f"{subject}, podgląd zmian", "sprawdzenia bezpieczeństwa"))
            else:
                if safety_review.get("apply_allowed") is not False:
                    errors.append(no_write(f"{subject}, sprawdzenie bezpieczeństwa"))
                if safety_review.get("api_mutation_ready") is not False:
                    errors.append(no_api_write(f"{subject}, sprawdzenie bezpieczeństwa"))
                if safety_review.get("safety_contract") != (CUSTOM_SEGMENT_APPLY_SAFETY_CONTRACT):
                    errors.append(
                        missing(
                            f"{subject}, sprawdzenie bezpieczeństwa", "poprawnej kontroli segmentu"
                        )
                    )
            if not isinstance(targeting_preview, list) or not targeting_preview:
                errors.append(missing(f"{subject}, podgląd zmian", "sprawdzenia kierowania"))
                continue
            if any(
                target.get("apply_allowed") is not False
                for target in targeting_preview
                if isinstance(target, dict)
            ):
                errors.append(no_write(f"{subject}, sprawdzenie kierowania"))
            if any(
                target.get("api_mutation_ready") is not False
                for target in targeting_preview
                if isinstance(target, dict)
            ):
                errors.append(no_api_write(f"{subject}, sprawdzenie kierowania"))
    return errors


def custom_segment_payload_from_metric_facts(facts: list[MetricFact]) -> dict[str, Any] | None:
    terms = _source_terms_from_metric_facts(facts)
    if not terms:
        return None
    eligible_facts = [
        fact
        for fact in facts
        if _is_search_term_fact(fact)
        and fact.dimensions.get("search_term") in terms
        and _fact_has_positive_signal(fact)
    ]
    evidence_ids = _unique(fact.evidence_id for fact in eligible_facts)
    if not evidence_ids:
        return None
    campaign_name = _first_dimension(eligible_facts, "campaign_name")
    custom_segment_name = (
        f"Wyszukiwane hasła: {campaign_name}" if campaign_name else "Segment z wyszukiwanych haseł"
    )
    return {
        "action_type": "custom_segment_candidate",
        "connector": "google_ads",
        "mode": "prepare_only",
        "terms": terms[:20],
        "source_terms": terms[:20],
        "preview_contract": "custom_segment_change_preview_v1",
        "payload_preview": [
            {
                "id": "custom_segment_preview_google_ads_search_terms",
                "custom_segment_name": custom_segment_name,
                "member_type": "KEYWORD",
                "member_type_label": "słowa kluczowe",
                "source_terms": terms[:20],
                "reason": (
                    "Do sprawdzenia: słowa kluczowe segmentu odbiorców z Google Ads "
                    "na podstawie dowodów z wyszukiwanych haseł."
                ),
                "evidence_ids": evidence_ids,
                "source_metric_names": _unique(fact.name for fact in eligible_facts),
                "required_validation": [
                    "review_source_terms",
                    "reject_brand_or_low_intent_terms",
                    "keyword_planner_enrichment",
                    "forecast_or_audience_size",
                    "human_confirm_before_apply",
                ],
                "blocked_claims": CUSTOM_SEGMENT_BLOCKED_CLAIMS,
                "targeting_preview": [
                    _custom_segment_targeting_preview(
                        preview_id="custom_segment_preview_google_ads_search_terms",
                        campaign_id=_first_dimension(eligible_facts, "campaign_id"),
                        campaign_name=campaign_name,
                    )
                ],
                "safety_review": custom_segment_apply_safety_review(
                    preview_id="custom_segment_preview_google_ads_search_terms",
                    evidence_ids=evidence_ids,
                    keyword_planner_enriched=False,
                    forecast_available=False,
                ),
                "api_mutation_ready": False,
                "apply_allowed": False,
                "destructive": False,
            }
        ],
        "source_metric_names": _unique(fact.name for fact in eligible_facts),
        "evidence_ids": evidence_ids,
        "required_validation": [
            "review_source_terms",
            "reject_brand_or_low_intent_terms",
            "keyword_planner_enrichment",
            "forecast_or_audience_size",
            "human_confirm_before_apply",
        ],
        "blocked_claims": CUSTOM_SEGMENT_BLOCKED_CLAIMS,
        "invented_terms": False,
        "destructive": False,
    }


def custom_segment_apply_safety_review(
    *,
    preview_id: str,
    evidence_ids: list[str],
    keyword_planner_enriched: bool,
    forecast_available: bool,
) -> dict[str, Any]:
    missing_requirements = ["google_ads_mutation_audit", "human_confirm_before_apply"]
    if not keyword_planner_enriched:
        missing_requirements.insert(0, "keyword_planner_enrichment")
    if not forecast_available:
        missing_requirements.insert(0, "forecast_or_audience_size")
    return {
        "id": f"{preview_id}_safety",
        "custom_segment_preview_id": preview_id,
        "safety_contract": CUSTOM_SEGMENT_APPLY_SAFETY_CONTRACT,
        "status": "blocked",
        "status_label": "zablokowane",
        "reason": (
            "Zapis zmian w custom segment zablokowany: podgląd jest "
            "do sprawdzenia. WILQ wymaga danych z Keyword Planner albo prognozy "
            "rozmiaru odbiorców, audytu zmiany Google Ads i potwierdzenia "
            "człowieka przed zapisem zmian."
        ),
        "missing_requirements": missing_requirements,
        "required_validation": CUSTOM_SEGMENT_APPLY_SAFETY_REQUIRED_VALIDATION,
        "blocked_claims": CUSTOM_SEGMENT_BLOCKED_CLAIMS,
        "evidence_ids": evidence_ids,
        "audit_required": True,
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
    }


def _source_terms_from_metric_facts(facts: list[MetricFact]) -> list[str]:
    terms: list[str] = []
    for fact in facts:
        if not _is_search_term_fact(fact):
            continue
        term = fact.dimensions.get("search_term")
        if term and _eligible_source_term(term) and _fact_has_positive_signal(fact):
            terms.append(term)
    return _unique(terms)


def _is_search_term_fact(fact: MetricFact) -> bool:
    return fact.source_connector == "google_ads" and fact.name.startswith("search_term_")


def _eligible_source_term(term: str) -> bool:
    normalized = term.strip().lower()
    if len(normalized) < 3:
        return False
    if "ekologus" in normalized:
        return False
    return any(character.isalpha() for character in normalized)


def _fact_has_positive_signal(fact: MetricFact) -> bool:
    if fact.name not in {
        "search_term_clicks",
        "search_term_impressions",
        "search_term_cost_micros",
        "search_term_conversions",
        "search_term_conversion_value",
    }:
        return False
    value = fact.value
    return isinstance(value, int | float) and value > 0


def _custom_segment_targeting_preview(
    preview_id: str,
    campaign_id: str | None,
    campaign_name: str | None,
) -> dict[str, Any]:
    return {
        "id": f"targeting_{preview_id}",
        "custom_segment_preview_id": preview_id,
        "target_scope": "campaign_context_review",
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "operation_type": "custom_segment_targeting_review",
        "reason": (
            "Do sprawdzenia: podgląd kampanii, do której można wrócić po sprawdzeniu "
            "segmentu. To nie jest targetowanie ani mutacja Google Ads."
        ),
        "required_validation": [
            "keyword_planner_enrichment",
            "forecast_or_audience_size",
            "human_confirm_before_apply",
            "mutation_audit_required",
        ],
        "blocked_claims": CUSTOM_SEGMENT_BLOCKED_CLAIMS,
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
    }


def _first_dimension(facts: list[MetricFact], key: str) -> str | None:
    for fact in facts:
        value = fact.dimensions.get(key)
        if value:
            return value
    return None


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
