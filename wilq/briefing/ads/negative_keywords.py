from __future__ import annotations

from typing import Literal, cast

from wilq.actions.google_ads.negative_keywords import (
    NEGATIVE_KEYWORD_ACTION_ID,
    NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
)
from wilq.operator_labels import (
    blocked_claim_count_label,
    missing_contract_count_label,
)
from wilq.schemas import (
    ActionPreviewCardViewModel,
    AdsKeywordMatchContextReadContract,
    AdsKeywordMatchContextRow,
    AdsNegativeKeywordCandidate,
    AdsNegativeKeywordPayloadPreview,
    AdsNegativeKeywordsReadContract,
    AdsSearchTermMetricRow,
    AdsSearchTermSafetyReadContract,
    AdsSearchTermSafetyRow,
    AdsSearchTermsReadContract,
)

from .labels import (
    _ads_missing_read_contract_labels,
    _ads_review_gate_labels,
    _ads_validation_status_label,
)
from .shared import (
    ADS_SEARCH_TERM_ROW_LIMIT_90D,
    ADS_SUMMARY_VIEW_ROW_LIMIT,
    GOOGLE_ADS_CONNECTOR_ID,
    _ads_preview_card_id,
    _ads_preview_row,
    _copy_limited_model,
    _format_float,
    _format_micros,
    _keyword_match_context_key,
    _safety_row_has_conversion_signal,
    _search_term_coverage,
    _search_term_row_sort_key,
    _search_term_safety_key,
    _slug,
    _unique,
)


def _compact_negative_keyword_candidate(
    candidate: AdsNegativeKeywordCandidate,
) -> AdsNegativeKeywordCandidate:
    return cast(
        AdsNegativeKeywordCandidate,
        _copy_limited_model(
            candidate,
            metric_facts=ADS_SUMMARY_VIEW_ROW_LIMIT,
            safety_metric_facts=ADS_SUMMARY_VIEW_ROW_LIMIT,
            keyword_context_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
        ),
    )


def _negative_keywords_read_contract(
    search_terms_read_contract: AdsSearchTermsReadContract,
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract,
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract,
    action_ids: list[str],
) -> AdsNegativeKeywordsReadContract:
    if not search_terms_read_contract.search_term_rows:
        return _negative_keywords_missing_search_terms_contract(
            search_terms_read_contract,
            keyword_match_context_read_contract,
        )

    candidates = _negative_keyword_candidates(
        search_terms_read_contract.search_term_rows,
        search_term_safety_read_contract.safety_rows,
        keyword_match_context_read_contract.context_rows,
    )
    has_safe_preview = any(candidate.payload_preview is not None for candidate in candidates)
    negative_keyword_action_ids = (
        [action_id for action_id in action_ids if action_id == NEGATIVE_KEYWORD_ACTION_ID]
        if has_safe_preview
        else []
    )
    if not candidates:
        return _negative_keywords_no_candidates_contract(
            search_terms_read_contract,
            search_term_safety_read_contract,
            keyword_match_context_read_contract,
        )

    missing_read_contracts = (
        [] if keyword_match_context_read_contract.status == "ready" else ["keyword match context"]
    )
    if any(candidate.safety_status != "read_ready_needs_human_review" for candidate in candidates):
        missing_read_contracts.insert(1, "90_day_safety_check")

    # A mixed queue is not safe to expose as a ready review action.  A payload
    # preview is only meaningful when every candidate has the exact matched
    # 90-day safety row; otherwise the operator could mistake the ready subset
    # for a complete, serviceable exclusion queue.  Keep the candidates and
    # their per-row status visible, but fail closed at the contract boundary.
    contract_status: Literal["ready", "blocked"] = "blocked" if missing_read_contracts else "ready"
    safe_payload_preview = (
        [
            candidate.payload_preview
            for candidate in candidates
            if candidate.payload_preview is not None
        ]
        if contract_status == "ready"
        else []
    )
    safe_action_ids = negative_keyword_action_ids if contract_status == "ready" else []

    return AdsNegativeKeywordsReadContract(
        status=contract_status,
        title="Ocena wykluczeń z wyszukiwanych haseł",
        summary=(
            f"WILQ ma {len(candidates)} terminów do oceny: mają koszt lub kliknięcia, "
            "zero konwersji w bieżących dowodach i są sprawdzone przez dostępny "
            "90-dniowy odczyt, jeśli WILQ ma pasujący wiersz."
        ),
        candidates=candidates,
        payload_preview=safe_payload_preview,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_unique(
            evidence_id
            for candidate in candidates
            for evidence_id in [
                *candidate.evidence_ids,
                *candidate.safety_evidence_ids,
                *candidate.keyword_context_evidence_ids,
            ]
        ),
        coverage=[*search_terms_read_contract.coverage, *search_term_safety_read_contract.coverage],
        missing_read_contracts=missing_read_contracts,
        blocked_claims=NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
        action_ids=safe_action_ids,
        next_step=(
            "Przejrzyj propozycje do sprawdzenia. Przed jakimkolwiek zapisem "
            "zmian wymagaj kontekstu dopasowania, podglądu zmian i sprawdzenia "
            "w WILQ."
        ),
    )


def _negative_keywords_missing_search_terms_contract(
    search_terms_read_contract: AdsSearchTermsReadContract,
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract,
) -> AdsNegativeKeywordsReadContract:
    return AdsNegativeKeywordsReadContract(
        status="blocked",
        title="Ocena wykluczeń z wyszukiwanych haseł",
        summary="Brak wierszy wyszukiwanych haseł do kolejki oceny wykluczeń.",
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=search_terms_read_contract.evidence_ids,
        coverage=[
            *search_terms_read_contract.coverage,
            _search_term_coverage(
                window="search_term_safety_90d",
                returned_row_count=0,
                requested_row_limit=ADS_SEARCH_TERM_ROW_LIMIT_90D,
                blocked=True,
            ),
        ],
        missing_read_contracts=[
            "search_term_view",
            *(
                []
                if keyword_match_context_read_contract.status == "ready"
                else ["keyword match context"]
            ),
            "90_day_safety_check",
        ],
        blocked_claims=NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
        action_ids=[],
        next_step=(
            "Najpierw zbierz fakty Google Ads z `search_term_view`. Nie twórz "
            "wykluczeń bez wyszukiwanych haseł, kontekstu dopasowania i kontroli "
            "bezpieczeństwa."
        ),
    )


def _negative_keywords_no_candidates_contract(
    search_terms_read_contract: AdsSearchTermsReadContract,
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract,
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract,
) -> AdsNegativeKeywordsReadContract:
    return AdsNegativeKeywordsReadContract(
        status="blocked",
        title="Ocena wykluczeń z wyszukiwanych haseł",
        summary=(
            "Wiersze wyszukiwanych haseł istnieją, ale WILQ nie znalazł terminów z kosztem lub "
            "kliknięciami i zerową konwersją w bieżących dowodach."
        ),
        source_connectors=search_terms_read_contract.source_connectors,
        evidence_ids=search_terms_read_contract.evidence_ids,
        coverage=[*search_terms_read_contract.coverage, *search_term_safety_read_contract.coverage],
        missing_read_contracts=[
            "zero_conversion_search_terms",
            *(
                []
                if keyword_match_context_read_contract.status == "ready"
                else ["keyword match context"]
            ),
            *(
                []
                if search_term_safety_read_contract.status == "ready"
                else ["90_day_safety_check"]
            ),
        ],
        blocked_claims=NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
        action_ids=[],
        next_step=(
            "Kontynuuj ocenę wyszukiwanych haseł bez zapisu zmian. Nie twórz "
            "propozycji wykluczeń, jeśli bieżące dowody nie pokazują zerowej "
            "konwersji."
        ),
    )


def _negative_keyword_candidates(
    rows: list[AdsSearchTermMetricRow],
    safety_rows: list[AdsSearchTermSafetyRow],
    keyword_context_rows: list[AdsKeywordMatchContextRow],
) -> list[AdsNegativeKeywordCandidate]:
    candidates: list[AdsNegativeKeywordCandidate] = []
    safety_by_key, keyword_context_by_key = _negative_keyword_context_indexes(
        safety_rows,
        keyword_context_rows,
    )
    for row in sorted(rows, key=_search_term_row_sort_key):
        if not _is_negative_keyword_review_candidate(row):
            continue
        safety_row = safety_by_key.get(_search_term_safety_key(row))
        if safety_row is not None and _safety_row_has_conversion_signal(safety_row):
            continue
        metric_facts = row.metric_facts[:12]
        safety_metric_facts = safety_row.metric_facts[:12] if safety_row else []
        safety_status: Literal["needs_90_day_review", "read_ready_needs_human_review"]
        if safety_row is None:
            safety_status = "needs_90_day_review"
        else:
            safety_status = "read_ready_needs_human_review"
        row_keyword_context = keyword_context_by_key.get(
            (row.campaign_id, row.ad_group_id),
            [],
        )[:8]
        payload_preview = (
            _negative_keyword_change_preview(row, safety_row) if safety_row is not None else None
        )
        review_score = _negative_keyword_review_score(
            row,
            safety_row,
            row_keyword_context,
        )
        candidates.append(
            AdsNegativeKeywordCandidate(
                id=(
                    "ads_negative_keyword_review_"
                    f"{_slug(row.campaign_id or row.campaign_name or 'campaign')}_"
                    f"{_slug(row.ad_group_id or row.ad_group_name or 'ad_group')}_"
                    f"{_slug(row.search_term)}"
                ),
                search_term=row.search_term,
                review_priority=_negative_keyword_review_priority(review_score),
                review_score=review_score,
                review_reason=_negative_keyword_review_reason(
                    row,
                    safety_row,
                    row_keyword_context,
                ),
                human_review_gates=[
                    "sprawdź intencję zapytania",
                    "porównaj z istniejącymi słowami kluczowymi i typami dopasowania",
                    "sprawdź 90-dniowy odczyt bezpieczeństwa",
                    "zatwierdź poziom wykluczenia przed zapisem zmian",
                ],
                campaign_id=row.campaign_id,
                campaign_name=row.campaign_name,
                ad_group_id=row.ad_group_id,
                ad_group_name=row.ad_group_name,
                clicks=row.clicks,
                impressions=row.impressions,
                cost_micros=row.cost_micros,
                conversions=row.conversions,
                conversion_value=row.conversion_value,
                clicks_90d=safety_row.clicks_90d if safety_row else None,
                impressions_90d=safety_row.impressions_90d if safety_row else None,
                cost_micros_90d=safety_row.cost_micros_90d if safety_row else None,
                conversions_90d=safety_row.conversions_90d if safety_row else None,
                conversion_value_90d=(safety_row.conversion_value_90d if safety_row else None),
                evidence_ids=row.evidence_ids,
                safety_evidence_ids=safety_row.evidence_ids if safety_row else [],
                keyword_context_evidence_ids=_unique(
                    evidence_id
                    for context_row in row_keyword_context
                    for evidence_id in context_row.evidence_ids
                ),
                metric_facts=metric_facts,
                safety_metric_facts=safety_metric_facts,
                keyword_context_rows=row_keyword_context,
                payload_preview=payload_preview,
                required_checks=[
                    "review_search_term_context",
                    "check_existing_keywords_and_match_types",
                    "90_day_safety_check",
                    "negative_keyword_change_preview",
                    "human_confirm_before_apply",
                ],
                safety_status=safety_status,
                validation_status="pending_validation",
                blocked_claims=NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
                next_step=(
                    "Sprawdź intencję terminu, istniejące słowa kluczowe, typy dopasowań i "
                    "90-dniową historię przed jakimkolwiek wykluczeniem."
                ),
            )
        )
    return candidates[:12]


def _negative_keyword_context_indexes(
    safety_rows: list[AdsSearchTermSafetyRow],
    keyword_context_rows: list[AdsKeywordMatchContextRow],
) -> tuple[
    dict[tuple[str, str | None, str | None], AdsSearchTermSafetyRow],
    dict[tuple[str | None, str | None], list[AdsKeywordMatchContextRow]],
]:
    safety_by_key: dict[
        tuple[str, str | None, str | None],
        AdsSearchTermSafetyRow,
    ] = {_search_term_safety_key(row): row for row in safety_rows}
    keyword_context_by_key: dict[
        tuple[str | None, str | None],
        list[AdsKeywordMatchContextRow],
    ] = {}
    for context_row in keyword_context_rows:
        keyword_context_by_key.setdefault(
            _keyword_match_context_key(context_row),
            [],
        ).append(context_row)
    return safety_by_key, keyword_context_by_key


def _negative_keyword_review_score(
    row: AdsSearchTermMetricRow,
    safety_row: AdsSearchTermSafetyRow | None,
    keyword_context_rows: list[AdsKeywordMatchContextRow],
) -> int:
    current_cost = (row.cost_micros or 0) / 1_000_000
    safety_cost = ((safety_row.cost_micros_90d if safety_row else 0) or 0) / 1_000_000
    current_clicks = row.clicks or 0
    safety_clicks = (safety_row.clicks_90d if safety_row else 0) or 0
    score = min(current_cost * 2, 40)
    score += min(safety_cost, 25)
    score += min(max(current_clicks, safety_clicks) * 5, 20)
    if safety_row is not None:
        score += 10
    if keyword_context_rows:
        score += 5
    return min(100, int(round(score)))


def _negative_keyword_review_priority(
    review_score: int,
) -> Literal["pilne", "wysokie", "normalne", "niski sygnał"]:
    if review_score >= 70:
        return "pilne"
    if review_score >= 45:
        return "wysokie"
    if review_score >= 15:
        return "normalne"
    return "niski sygnał"


def _negative_keyword_review_reason(
    row: AdsSearchTermMetricRow,
    safety_row: AdsSearchTermSafetyRow | None,
    keyword_context_rows: list[AdsKeywordMatchContextRow],
) -> str:
    current_cost = _format_micros(row.cost_micros)
    safety_cost = _format_micros(safety_row.cost_micros_90d if safety_row else None)
    current_conversions = _format_float(float(row.conversions or 0))
    safety_conversions_value = safety_row.conversions_90d if safety_row is not None else 0
    safety_conversions = _format_float(float(safety_conversions_value or 0))
    safety_part = (
        f"90 dni: {safety_row.clicks_90d or 0} kliknięć, koszt {safety_cost or '0'}, "
        f"{safety_conversions} konwersji"
        if safety_row is not None
        else "brak dopasowanego 90-dniowego odczytu bezpieczeństwa"
    )
    context_part = (
        f"{len(keyword_context_rows)} wierszy kontekstu dopasowań słów kluczowych"
        if keyword_context_rows
        else "brak kontekstu dopasowań słów kluczowych dla tej grupy"
    )
    return (
        f"Bieżący odczyt: {row.clicks or 0} kliknięć, koszt {current_cost or '0'}, "
        f"{current_conversions} konwersji; {safety_part}; {context_part}. "
        "To jest kolejność oceny, nie ocena zmarnowanego budżetu."
    )


def _negative_keyword_change_preview(
    row: AdsSearchTermMetricRow,
    safety_row: AdsSearchTermSafetyRow,
) -> AdsNegativeKeywordPayloadPreview:
    safety_evidence_ids = safety_row.evidence_ids
    evidence_ids = _unique([*row.evidence_ids, *safety_evidence_ids])
    safety_metric_names = [fact.name for fact in safety_row.metric_facts]
    source_metric_names = _unique([*(fact.name for fact in row.metric_facts), *safety_metric_names])
    level: Literal["ad_group", "campaign_review_required"] = (
        "ad_group" if row.ad_group_id else "campaign_review_required"
    )
    reason = (
        "Podgląd oceny dokładnego wykluczenia zbudowany z 30-dniowych wyszukiwanych haseł "
        "i 90-dniowego odczytu bezpieczeństwa. To nie jest gotowa mutacja API."
    )
    if level == "campaign_review_required":
        reason = (
            "Brak ad_group_id w dowodach, więc WILQ pokazuje tylko podgląd oceny "
            "i wymaga decyzji człowieka o poziomie kampanii lub grupy reklam."
        )
    return AdsNegativeKeywordPayloadPreview(
        id=(
            "negative_keyword_preview_"
            f"{_slug(row.campaign_id or row.campaign_name or 'campaign')}_"
            f"{_slug(row.ad_group_id or row.ad_group_name or 'ad_group')}_"
            f"{_slug(row.search_term)}"
        ),
        search_term=row.search_term,
        negative_keyword_text=row.search_term,
        match_type="EXACT",
        level=level,
        campaign_id=row.campaign_id,
        campaign_name=row.campaign_name,
        ad_group_id=row.ad_group_id,
        ad_group_name=row.ad_group_name,
        reason=reason,
        evidence_ids=evidence_ids,
        safety_evidence_ids=safety_evidence_ids,
        source_metric_names=source_metric_names,
        required_validation=[
            "review_search_term_context",
            "check_existing_keywords_and_match_types",
            "90_day_safety_check",
            "human_confirm_before_apply",
        ],
        blocked_claims=NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
    )


def _is_negative_keyword_review_candidate(row: AdsSearchTermMetricRow) -> bool:
    if not _eligible_negative_keyword_term(row.search_term):
        return False
    has_activity = bool((row.clicks or 0) > 0 or (row.cost_micros or 0) > 0)
    has_conversions = bool((row.conversions or 0) > 0 or (row.conversion_value or 0) > 0)
    return has_activity and not has_conversions


def _eligible_negative_keyword_term(term: str) -> bool:
    normalized = term.strip().lower()
    if len(normalized) < 3:
        return False
    if "ekologus" in normalized:
        return False
    return any(character.isalpha() for character in normalized)


def _hydrate_negative_keywords_marketer_labels(
    contract: AdsNegativeKeywordsReadContract,
) -> None:
    contract.missing_read_contract_labels = _ads_missing_read_contract_labels(
        contract.missing_read_contracts
    )
    contract.missing_read_contract_summary_label = missing_contract_count_label(
        contract.missing_read_contracts
    )
    contract.blocked_claim_labels = _unique(contract.blocked_claims)
    contract.blocked_claim_summary_label = blocked_claim_count_label(
        contract.blocked_claim_labels or contract.blocked_claims
    )
    for candidate in contract.candidates:
        candidate.required_check_labels = _ads_review_gate_labels(candidate.required_checks)
        candidate.safety_status_label = _ads_negative_keyword_safety_status_label(
            candidate.safety_status
        )
        candidate.validation_status_label = _ads_validation_status_label(
            candidate.validation_status
        )
        candidate.blocked_claim_labels = _unique(candidate.blocked_claims)
        for row in candidate.keyword_context_rows:
            _hydrate_keyword_match_context_row_labels(row)
        if candidate.payload_preview is not None:
            _hydrate_negative_keyword_payload_preview_labels(candidate.payload_preview)
            candidate.preview_card = _negative_keyword_preview_card(candidate.payload_preview)
    for preview in contract.payload_preview:
        _hydrate_negative_keyword_payload_preview_labels(preview)


def _hydrate_negative_keyword_payload_preview_labels(
    preview: AdsNegativeKeywordPayloadPreview,
) -> None:
    preview.match_type_label = _ads_keyword_match_type_label(preview.match_type)
    preview.level_label = _ads_negative_keyword_level_label(preview.level)
    preview.required_validation_labels = _ads_review_gate_labels(preview.required_validation)
    preview.blocked_claim_labels = _unique(preview.blocked_claims)


def _negative_keyword_preview_card(
    preview: AdsNegativeKeywordPayloadPreview,
) -> ActionPreviewCardViewModel:
    rows = [
        _ads_preview_row("Hasło", preview.search_term),
        _ads_preview_row("Wykluczenie", preview.negative_keyword_text),
        _ads_preview_row("Dopasowanie", preview.match_type_label or "dopasowanie do sprawdzenia"),
        _ads_preview_row("Poziom", preview.level_label or "poziom do sprawdzenia"),
        _ads_preview_row("Kampania", preview.campaign_label or "kampania do sprawdzenia"),
        _ads_preview_row("Grupa reklam", preview.ad_group_label or "grupa reklam do sprawdzenia"),
    ]
    if preview.required_validation_labels:
        rows.append(
            _ads_preview_row(
                "Warunki sprawdzenia",
                ", ".join(preview.required_validation_labels[:4]),
            )
        )
    if preview.blocked_claim_labels:
        rows.append(
            _ads_preview_row(
                "Czego nie wolno twierdzić",
                ", ".join(preview.blocked_claim_labels[:4]),
            )
        )
    return ActionPreviewCardViewModel(
        id=_ads_preview_card_id("google_ads_negative_keyword_review", preview.id),
        kind="google_ads_negative_keyword_review",
        title_label="Wykluczenie słowa do sprawdzenia",
        subtitle_label="ocena intencji zapytania bez zapisu zmian",
        status_label="zapis zmian zablokowany",
        rows=rows,
        apply_state_label=(
            "możliwy zapis po sprawdzeniu" if preview.apply_allowed else "zapis zmian zablokowany"
        ),
        system_readiness_label=(
            "system gotowy do zapisu" if preview.api_mutation_ready else "wymaga kontroli"
        ),
    )


def _hydrate_keyword_match_context_marketer_labels(
    contract: AdsKeywordMatchContextReadContract,
) -> None:
    for row in contract.context_rows:
        _hydrate_keyword_match_context_row_labels(row)


def _hydrate_keyword_match_context_row_labels(row: AdsKeywordMatchContextRow) -> None:
    row.match_type_label = _ads_keyword_match_type_label(row.match_type)
    row.criterion_status_label = _ads_keyword_criterion_status_label(row.criterion_status)
    row.negative_label = "wykluczające" if row.negative else "aktywne"


def _ads_negative_keyword_safety_status_label(status: object) -> str:
    labels = {
        "needs_90_day_review": "wymaga 90-dniowej kontroli",
        "read_ready_needs_human_review": "90-dniowy odczyt gotowy",
        "blocked": "zablokowane",
    }
    value = str(status)
    return labels.get(value, "status bezpieczeństwa wykluczenia do sprawdzenia")


def _ads_negative_keyword_level_label(level: object) -> str:
    labels = {
        "ad_group": "grupa reklam",
        "campaign_review_required": "poziom do decyzji człowieka",
    }
    value = str(level)
    return labels.get(value, "poziom wykluczenia do sprawdzenia")


def _ads_keyword_match_type_label(match_type: object) -> str:
    labels = {
        "EXACT": "dopasowanie ścisłe",
        "PHRASE": "dopasowanie do wyrażenia",
        "BROAD": "dopasowanie przybliżone",
        "UNKNOWN": "typ dopasowania nieznany",
        "UNSPECIFIED": "typ dopasowania nieokreślony",
    }
    value = str(match_type)
    return labels.get(value, "typ dopasowania słowa do sprawdzenia")


def _ads_keyword_criterion_status_label(status: object | None) -> str:
    labels = {
        "ENABLED": "aktywne",
        "PAUSED": "wstrzymane",
        "REMOVED": "usunięte",
        "UNKNOWN": "status nieznany",
        "UNSPECIFIED": "status nieokreślony",
    }
    if status is None or str(status) == "":
        return "status słowa niepotwierdzony"
    value = str(status)
    return labels.get(value, "status słowa do sprawdzenia")
