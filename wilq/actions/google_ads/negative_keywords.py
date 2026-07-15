from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from wilq.actions.validation_copy import (
    missing,
    missing_evidence,
    no_api_write,
    no_destructive_change,
    no_write,
    row,
    wrong,
)
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionPreviewCardViewModel,
    ActionPreviewRowViewModel,
    ActionRisk,
    ActionStatus,
    MetricFact,
    OpportunityDomain,
)

NEGATIVE_KEYWORD_ACTION_ID = "act_prepare_negative_keyword_review_queue"
NEGATIVE_KEYWORD_BLOCKED_CLAIMS = [
    "dodanie wykluczających słów kluczowych",
    "marnowanie budżetu na zapytaniach",
    "utrata konwersji",
    "koszt pozyskania celu",
    "zwrot z reklam",
]

PreviewRow = Callable[[str, str], ActionPreviewRowViewModel]
StringList = Callable[[Any], list[str]]
StateLabel = Callable[[Any], str]


def negative_keyword_preview_cards(
    payload: dict[str, Any],
    *,
    preview_row: PreviewRow,
    string_list: StringList,
    apply_state_label: StateLabel,
    system_readiness_label: StateLabel,
) -> list[ActionPreviewCardViewModel]:
    """Render safe keyword-exclusion review cards without vendor IDs."""
    preview_items = [item for item in payload.get("payload_preview", []) if isinstance(item, dict)]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        rows = [
            preview_row("Hasło", str(item.get("search_term") or "hasło do sprawdzenia")),
            preview_row(
                "Wykluczenie",
                str(item.get("negative_keyword_text") or "wykluczenie do sprawdzenia"),
            ),
            preview_row(
                "Dopasowanie",
                str(item.get("match_type_label") or "dopasowanie do sprawdzenia"),
            ),
            preview_row("Poziom", str(item.get("level_label") or "poziom do sprawdzenia")),
            preview_row(
                "Kampania",
                str(item.get("campaign_name") or "kampania do sprawdzenia"),
            ),
            preview_row(
                "Grupa reklam",
                str(item.get("ad_group_name") or "grupa reklam do sprawdzenia"),
            ),
        ]
        requirement_labels = string_list(item.get("required_validation_labels"))
        if requirement_labels:
            rows.append(preview_row("Warunki sprawdzenia", ", ".join(requirement_labels[:4])))
        blocked_claim_labels = string_list(item.get("blocked_claim_labels"))
        if blocked_claim_labels:
            rows.append(
                preview_row(
                    "Czego nie wolno twierdzić",
                    ", ".join(blocked_claim_labels[:4]),
                )
            )
        cards.append(
            ActionPreviewCardViewModel(
                id=f"ads_negative_keyword_preview_{index}",
                kind="google_ads_negative_keyword_review",
                title_label="Wykluczenie słowa do sprawdzenia",
                subtitle_label="ocena intencji zapytania bez zapisu zmian",
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=apply_state_label(item.get("apply_allowed")),
                system_readiness_label=system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def negative_keyword_action(
    *,
    google_ads_facts: list[MetricFact],
    negative_keyword_payload: dict[str, Any],
) -> ActionObject:
    metrics = [
        fact
        for fact in google_ads_facts
        if fact.name.startswith("search_term_")
        and fact.dimensions.get("search_term") in negative_keyword_payload["terms"]
    ][:12]
    return ActionObject(
        id=NEGATIVE_KEYWORD_ACTION_ID,
        title="Przygotuj kolejkę oceny wykluczeń z wyszukiwanych haseł",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=list(dict.fromkeys(fact.evidence_id for fact in metrics)),
        metrics=metrics,
        human_diagnosis=(
            "Google Ads ma fakty z wyszukiwanych haseł, które mogą zasilić ocenę "
            "potencjalnych wykluczeń. WILQ nie może jednak twierdzić nic o "
            "przepalonym budżecie ani wdrażać wykluczających słów bez "
            "90-dniowej kontroli bezpieczeństwa i ręcznej sprawdzenia."
        ),
        recommended_reason=(
            "W widoku Google Ads przejrzyj terminy z kosztem/kliknięciami i zerową "
            "konwersją w bieżących dowodach, ale potraktuj je wyłącznie jako "
            "kolejkę oceny przed 90-dniową kontrolą bezpieczeństwa."
        ),
        payload=negative_keyword_payload,
        validation_status="not_validated",
        created_by="system_metric_seed",
    )


def negative_keyword_action_from_metric_facts(
    google_ads_facts: list[MetricFact],
) -> ActionObject | None:
    payload = negative_keyword_payload_from_metric_facts(google_ads_facts)
    if payload is None:
        return None
    return negative_keyword_action(
        google_ads_facts=google_ads_facts,
        negative_keyword_payload=payload,
    )


def validate_negative_keyword_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    subject = "Przegląd wykluczających słów kluczowych"
    if not payload.get("terms"):
        errors.append(missing(subject, "haseł opartych na dowodach"))
    if not payload.get("evidence_ids"):
        errors.append(missing_evidence(subject))
    if payload.get("apply_allowed") is not False:
        errors.append(no_write(subject))
    if payload.get("destructive") is not False:
        errors.append(no_destructive_change(subject))
    required_validation = payload.get("required_validation")
    if (
        not isinstance(required_validation, list)
        or "90_day_safety_check" not in required_validation
    ):
        errors.append(missing(subject, "sprawdzenia danych z ostatnich 90 dni"))
    preview_items = payload.get("payload_preview")
    if not isinstance(preview_items, list) or not preview_items:
        errors.append(missing(subject, "podglądu zmian"))
        return errors
    for index, item in enumerate(preview_items):
        item_subject = row("Podgląd wykluczającego słowa kluczowego", index)
        if not isinstance(item, dict):
            errors.append(wrong(item_subject, "ma nieprawidłową strukturę"))
            continue
        if item.get("match_type") != "EXACT":
            errors.append(wrong(item_subject, "musi używać dopasowania ścisłego"))
        if item.get("apply_allowed") is not False:
            errors.append(no_write(item_subject))
        if item.get("destructive") is not False:
            errors.append(no_destructive_change(item_subject))
        if item.get("api_mutation_ready") is not False:
            errors.append(no_api_write(item_subject))
        evidence_ids = item.get("evidence_ids")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            errors.append(missing_evidence(item_subject))
        safety_evidence_ids = item.get("safety_evidence_ids")
        if not isinstance(safety_evidence_ids, list) or not safety_evidence_ids:
            errors.append(missing(item_subject, "pasującego dowodu z ostatnich 90 dni"))
        elif not isinstance(evidence_ids, list) or not set(safety_evidence_ids).issubset(
            evidence_ids
        ):
            errors.append(wrong(item_subject, "dowód 90-dniowy nie należy do tej pozycji"))
    return errors


def negative_keyword_payload_from_metric_facts(facts: list[MetricFact]) -> dict[str, Any] | None:
    candidate_groups = [
        group
        for group in _candidate_fact_groups(facts)
        if any(fact.name.startswith("search_term_90d_") for fact in group)
    ]
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
        "preview_contract": "negative_keyword_change_preview_v1",
        "api_mutation_ready": False,
        "payload_preview": payload_preview[:20],
        "keyword_match_context_available": bool(keyword_context),
        "keyword_match_context": keyword_context[:50],
        "required_validation": [
            "review_search_term_context",
            "check_existing_keywords_and_match_types",
            "90_day_safety_check",
            "negative_keyword_change_preview",
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
            (str(fact.value) for fact in group if fact.name == "keyword_match_type" and fact.value),
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
        safety_evidence_ids = _unique(
            fact.evidence_id for fact in group if fact.name.startswith("search_term_90d_")
        )
        if not safety_evidence_ids:
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
                "safety_evidence_ids": safety_evidence_ids,
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
    return (
        "".join(character.lower() if character.isalnum() else "_" for character in value)[
            :80
        ].strip("_")
        or "item"
    )


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
