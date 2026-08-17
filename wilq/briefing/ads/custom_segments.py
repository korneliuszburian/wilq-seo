from __future__ import annotations

from typing import Literal, cast

from wilq.actions.google_ads.custom_segments import (
    CUSTOM_SEGMENT_ACTION_ID,
    CUSTOM_SEGMENT_BLOCKED_CLAIMS,
    custom_segment_apply_safety_review,
)
from wilq.briefing.ads_candidate_contracts import build_candidate_read_contracts
from wilq.content.operator_copy import unique
from wilq.schemas import (
    ActionPreviewCardViewModel,
    AdsCustomSegmentApplySafetyReview,
    AdsCustomSegmentAudienceForecastReadContract,
    AdsCustomSegmentAudienceForecastRow,
    AdsCustomSegmentCandidate,
    AdsCustomSegmentPayloadPreview,
    AdsCustomSegmentSourceQuality,
    AdsCustomSegmentsReadContract,
    AdsCustomSegmentTargetingPreview,
    AdsKeywordMatchContextReadContract,
    AdsKeywordPlannerIdeaRow,
    AdsKeywordPlannerReadContract,
    AdsNegativeKeywordsReadContract,
    AdsSearchTermMetricRow,
    AdsSearchTermSafetyReadContract,
    AdsSearchTermsReadContract,
    ConnectorRefreshRun,
    MetricFact,
)

from .labels import (
    _ads_confidence_label,
    _ads_missing_read_contract_labels,
    _ads_review_gate_labels,
    _ads_status_label,
    _ads_validation_status_label,
)
from .negative_keywords import (
    _negative_keywords_read_contract,
)
from .shared import (
    ADS_SUMMARY_VIEW_ROW_LIMIT,
    GOOGLE_ADS_CONNECTOR_ID,
    _ads_preview_card_id,
    _ads_preview_row,
    _copy_limited_model,
    _format_float,
    _format_micros,
    _int_metric_value,
    _latest_refresh_has_summary_metric,
    _refresh_or_connector_evidence_ids,
    _search_term_row_sort_key,
    _slug,
)

CUSTOM_SEGMENT_OPERATOR_REVIEW_GATES = [
    "review_source_terms",
    "reject_brand_or_low_intent_terms",
    "keyword_planner_enrichment",
    "forecast_or_audience_size",
    "human_confirm_before_apply",
]


def _build_ads_candidate_read_contracts(
    search_terms_read_contract: AdsSearchTermsReadContract,
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract,
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract,
    keyword_planner_read_contract: AdsKeywordPlannerReadContract,
    action_ids: list[str],
) -> tuple[AdsCustomSegmentsReadContract, AdsNegativeKeywordsReadContract]:
    return build_candidate_read_contracts(
        search_terms_read_contract,
        search_term_safety_read_contract,
        keyword_match_context_read_contract,
        keyword_planner_read_contract,
        action_ids,
        custom_segments=_custom_segments_read_contract,
        negative_keywords=_negative_keywords_read_contract,
    )


def _compact_custom_segment_candidate(
    candidate: AdsCustomSegmentCandidate,
) -> AdsCustomSegmentCandidate:
    return cast(
        AdsCustomSegmentCandidate,
        _copy_limited_model(
            candidate,
            search_term_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            keyword_planner_ideas=ADS_SUMMARY_VIEW_ROW_LIMIT,
            metric_facts=ADS_SUMMARY_VIEW_ROW_LIMIT,
        ),
    )


def _custom_segment_rejection_reason(row: AdsSearchTermMetricRow) -> str | None:
    term = row.search_term.strip()
    normalized = term.lower()
    if len(normalized) < 3:
        return "termin jest zbyt krótki"
    if not any(character.isalpha() for character in normalized):
        return "termin nie ma czytelnego intentu tekstowego"
    if "ekologus" in normalized:
        return "termin wygląda na własny brand albo zapytanie nawigacyjne"
    if not any((row.clicks or 0, row.impressions or 0, row.cost_micros or 0)):
        return "termin nie ma aktywności w dostępnych metrykach"
    return None


def _custom_segment_group_sort_key(rows: list[AdsSearchTermMetricRow]) -> tuple[int, int, str]:
    total_cost = sum(row.cost_micros or 0 for row in rows)
    total_clicks = sum(row.clicks or 0 for row in rows)
    first_campaign = next((row.campaign_name for row in rows if row.campaign_name), "")
    return (-total_cost, -total_clicks, first_campaign)


def _custom_segment_name(campaign_name: str | None, index: int) -> str:
    if campaign_name:
        return f"Wyszukiwane hasła: {campaign_name}"
    return f"Segment z wyszukiwanych haseł {index}"


def _custom_segment_confidence(
    rows: list[AdsSearchTermMetricRow],
) -> Literal["low", "medium", "high"]:
    total_clicks = sum(row.clicks or 0 for row in rows)
    source_term_count = len({row.search_term for row in rows})
    if source_term_count >= 8 and total_clicks >= 10:
        return "high"
    if source_term_count >= 3 and total_clicks >= 3:
        return "medium"
    return "low"


def _keyword_planner_read_contract(
    metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
) -> AdsKeywordPlannerReadContract:
    rows = _keyword_planner_idea_rows(metric_facts)
    read_attempted = _latest_refresh_has_summary_metric(
        latest_refresh,
        "keyword_planner_idea_count",
    )
    latest_status = (
        str(latest_refresh.metric_summary.get("keyword_planner_status"))
        if latest_refresh is not None
        else ""
    )
    blocked_claims = [
        "rozmiar odbiorców",
        "prognoza",
        "wzrost konwersji",
        "zwrot z reklam",
        "zapis kierowania reklam",
        "skuteczność kampanii",
    ]
    if rows:
        max_searches = max((row.avg_monthly_searches or 0 for row in rows), default=0)
        return AdsKeywordPlannerReadContract(
            status="ready",
            title="Keyword Planner: wzbogacenie segmentów",
            summary=(
                f"WILQ ma {len(rows)} pomysłów Keyword Planner dla haseł źródłowych z Ads. "
                f"Najwyższe avg_monthly_searches={max_searches}."
            ),
            allowed_metrics=[
                "keyword_idea_text",
                "keyword_planner_avg_monthly_searches",
                "keyword_planner_competition_index",
                "keyword_planner_low_top_of_page_bid_micros",
                "keyword_planner_high_top_of_page_bid_micros",
            ],
            missing_read_contracts=["forecast_or_audience_size"],
            operator_review_gates=[
                "review_keyword_planner_ideas",
                "reject_off-topic_or_brand_terms",
                "human_confirm_before_apply",
            ],
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=unique(evidence_id for row in rows for evidence_id in row.evidence_ids),
            idea_rows=rows,
            next_step=(
                "Użyj wzbogacenia jako dodatkowego kontekstu przy segmentach. "
                "Nie traktuj go jako prognozy, rozmiaru odbiorców ani zgody na zapis zmian."
            ),
        )
    if read_attempted or latest_status == "blocked":
        return AdsKeywordPlannerReadContract(
            status="blocked",
            title="Keyword Planner: wzbogacenie zablokowane",
            summary=(
                "Odczyt Keyword Plannera został podjęty, ale dostęp do propozycji "
                "jest nadal zablokowany po stronie Google Ads."
            ),
            missing_read_contracts=["keyword_planner_enrichment"],
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            idea_rows=[],
            next_step=(
                "Zostaw segmenty w trybie oceny haseł źródłowych. Nie dopowiadaj "
                "zasięgu ani prognozy bez faktów z Keyword Planner."
            ),
        )
    return AdsKeywordPlannerReadContract(
        status="blocked",
        title="Keyword Planner: brak wzbogacenia",
        summary="WILQ nie ma jeszcze danych wzbogacających z Keyword Plannera.",
        missing_read_contracts=["keyword_planner_enrichment"],
        blocked_claims=blocked_claims,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        idea_rows=[],
        next_step=(
            "Uruchom odczyt danych Google Ads z Keyword Planner albo zostaw "
            "segmenty jako przygotowanie do oceny haseł źródłowych."
        ),
    )


def _keyword_planner_idea_rows(metric_facts: list[MetricFact]) -> list[AdsKeywordPlannerIdeaRow]:
    grouped_facts: dict[str, list[MetricFact]] = {}
    seen_metric_keys: set[tuple[str, str]] = set()
    for fact in metric_facts:
        if fact.name not in {
            "keyword_planner_idea_available",
            "keyword_planner_avg_monthly_searches",
            "keyword_planner_competition_index",
            "keyword_planner_low_top_of_page_bid_micros",
            "keyword_planner_high_top_of_page_bid_micros",
        }:
            continue
        idea_text = fact.dimensions.get("keyword_idea_text")
        if not idea_text:
            continue
        metric_key = (idea_text, fact.name)
        if metric_key in seen_metric_keys:
            continue
        seen_metric_keys.add(metric_key)
        grouped_facts.setdefault(idea_text, []).append(fact)

    rows = [
        _keyword_planner_idea_row(idea_text, facts) for idea_text, facts in grouped_facts.items()
    ]
    return sorted(
        rows,
        key=lambda row: (-(row.avg_monthly_searches or 0), row.idea_text),
    )


def _keyword_planner_idea_row(
    idea_text: str,
    facts: list[MetricFact],
) -> AdsKeywordPlannerIdeaRow:
    facts_by_name = {fact.name: fact for fact in facts}
    expected_metrics = [
        "keyword_planner_avg_monthly_searches",
        "keyword_planner_competition_index",
    ]
    first_dimensions = facts[0].dimensions if facts else {}
    source_terms = [
        term.strip()
        for term in (first_dimensions.get("seed_terms") or "").split(",")
        if term.strip()
    ]
    return AdsKeywordPlannerIdeaRow(
        idea_text=idea_text,
        avg_monthly_searches=_int_metric_value(
            facts_by_name.get("keyword_planner_avg_monthly_searches")
        ),
        competition=first_dimensions.get("competition"),
        competition_index=_int_metric_value(facts_by_name.get("keyword_planner_competition_index")),
        low_top_of_page_bid_micros=_int_metric_value(
            facts_by_name.get("keyword_planner_low_top_of_page_bid_micros")
        ),
        high_top_of_page_bid_micros=_int_metric_value(
            facts_by_name.get("keyword_planner_high_top_of_page_bid_micros")
        ),
        source_terms=source_terms,
        evidence_ids=unique(fact.evidence_id for fact in facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        missing_metrics=[name for name in expected_metrics if name not in facts_by_name],
        blocked_claims=[
            "rozmiar odbiorców",
            "prognoza",
            "wzrost konwersji",
            "zwrot z reklam",
            "zapis kierowania reklam",
        ],
    )


def _custom_segments_read_contract(
    search_terms_read_contract: AdsSearchTermsReadContract,
    keyword_planner_read_contract: AdsKeywordPlannerReadContract,
    action_ids: list[str],
) -> AdsCustomSegmentsReadContract:
    if not search_terms_read_contract.search_term_rows:
        return AdsCustomSegmentsReadContract(
            status="blocked",
            title="Segmenty z wyszukiwanych haseł",
            summary=("Brak wierszy wyszukiwanych haseł do zbudowania propozycji segmentów."),
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=search_terms_read_contract.evidence_ids,
            missing_read_contracts=[
                "search_term_view",
                "keyword_planner_enrichment",
                "custom_segment_change_preview",
            ],
            blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
            action_ids=[],
            next_step=(
                "Najpierw zbierz fakty Google Ads o wyszukiwanych hasłach. Nie wymyślaj "
                "haseł odbiorców bez haseł źródłowych i identyfikatorów dowodów."
            ),
        )

    candidates = _custom_segment_candidates(
        search_terms_read_contract.search_term_rows,
        keyword_planner_read_contract.idea_rows,
    )
    custom_segment_action_ids = [
        action_id for action_id in action_ids if action_id == CUSTOM_SEGMENT_ACTION_ID
    ]
    if not candidates:
        return AdsCustomSegmentsReadContract(
            status="blocked",
            title="Segmenty z wyszukiwanych haseł",
            summary=(
                "Wiersze wyszukiwanych haseł istnieją, ale wszystkie terminy zostały odrzucone "
                "jako brand, zbyt krótkie albo bez wystarczającego sygnału."
            ),
            source_connectors=search_terms_read_contract.source_connectors,
            evidence_ids=search_terms_read_contract.evidence_ids,
            missing_read_contracts=[
                "eligible_source_terms",
                *(
                    []
                    if keyword_planner_read_contract.status == "ready"
                    else ["keyword_planner_enrichment"]
                ),
                "custom_segment_change_preview",
            ],
            blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
            action_ids=[],
            next_step=(
                "Zbierz więcej realnych haseł źródłowych albo użyj dowodów Keyword Planner; "
                "nie twórz segmentu z pustych lub brandowych terminów."
            ),
        )

    source_terms_count = sum(len(candidate.source_terms) for candidate in candidates)
    keyword_planner_idea_count = sum(
        len(candidate.keyword_planner_ideas) for candidate in candidates
    )
    payload_preview = [
        candidate.payload_preview
        for candidate in candidates
        if candidate.payload_preview is not None
    ]
    audience_forecast_read_contract = _custom_segment_audience_forecast_read_contract(candidates)
    missing_read_contracts = ["forecast_or_audience_size"]
    if keyword_planner_read_contract.status != "ready":
        missing_read_contracts.insert(0, "keyword_planner_enrichment")
    return AdsCustomSegmentsReadContract(
        status="ready",
        title="Segmenty z realnych wyszukiwanych haseł",
        summary=(
            f"WILQ ma {_custom_segment_candidate_count_label(len(candidates))} i "
            f"{source_terms_count} haseł źródłowych z dowodów Google Ads, "
            f"{_custom_segment_keyword_planner_count_label(keyword_planner_idea_count)} i "
            f"{_custom_segment_preview_count_label(len(payload_preview))}."
        ),
        candidates=candidates,
        payload_preview=payload_preview,
        audience_forecast_read_contract=audience_forecast_read_contract,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=unique(
            evidence_id for candidate in candidates for evidence_id in candidate.evidence_ids
        ),
        missing_read_contracts=missing_read_contracts,
        operator_review_gates=CUSTOM_SEGMENT_OPERATOR_REVIEW_GATES,
        blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
        action_ids=custom_segment_action_ids,
        next_step=(
            "Przejrzyj hasła źródłowe i podgląd zmian, odrzuć nietrafione frazy, "
            "użyj wzbogacenia Keyword Planner, jeśli jest dostępne, i sprawdź w WILQ "
            "akcję przed zapisem zmian."
        ),
    )


def _custom_segment_audience_forecast_read_contract(
    candidates: list[AdsCustomSegmentCandidate],
) -> AdsCustomSegmentAudienceForecastReadContract:
    forecast_rows = [
        AdsCustomSegmentAudienceForecastRow(
            id=f"forecast_{_slug(candidate.id)}",
            candidate_id=candidate.id,
            custom_segment_name=candidate.name,
            status="missing_forecast",
            forecast_available=False,
            audience_size=None,
            source_terms=candidate.source_terms,
            reason=(
                "Brak dowodów WILQ dla prognozy albo rozmiaru odbiorców tego "
                "segmentu. Propozycja zostaje tylko do przygotowania i oceny."
            ),
            evidence_ids=candidate.evidence_ids,
            blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
        )
        for candidate in candidates
    ]
    return AdsCustomSegmentAudienceForecastReadContract(
        status="blocked",
        title="Prognoza i rozmiar odbiorców segmentów",
        summary=(
            f"WILQ sprawdził {_custom_segment_candidate_count_label(len(candidates))}, ale "
            "nie ma dowodów prognozy ani rozmiaru odbiorców. Segmenty można tylko "
            "przygotować do oceny."
        ),
        checked_candidate_count=len(candidates),
        forecast_row_count=len(forecast_rows),
        forecast_rows=forecast_rows,
        missing_read_contracts=["forecast_or_audience_size"],
        operator_review_gates=["forecast_or_audience_size", "human_confirm_before_apply"],
        blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=unique(
            evidence_id for candidate in candidates for evidence_id in candidate.evidence_ids
        ),
        next_step=(
            "Nie oceniaj zasięgu ani skuteczności segmentu. Najpierw dostarcz "
            "dowody prognozy albo rozmiaru odbiorców i dopiero potem wróć do "
            "kierowania reklam."
        ),
    )


def _custom_segment_candidate_count_label(count: int) -> str:
    if count == 1:
        return "1 segment do sprawdzenia"
    if 2 <= count <= 4:
        return f"{count} segmenty do sprawdzenia"
    return f"{count} segmentów do sprawdzenia"


def _custom_segment_preview_count_label(count: int) -> str:
    if count == 1:
        return "1 podgląd zmian do sprawdzenia"
    if 2 <= count <= 4:
        return f"{count} podglądy zmian do sprawdzenia"
    return f"{count} podglądów zmian do sprawdzenia"


def _custom_segment_keyword_planner_count_label(count: int) -> str:
    if count == 0:
        return "brak pomysłów Keyword Planner"
    if count == 1:
        return "1 pomysł Keyword Planner"
    if 2 <= count <= 4:
        return f"{count} pomysły Keyword Planner"
    return f"{count} pomysłów Keyword Planner"


def _custom_segment_candidates(
    rows: list[AdsSearchTermMetricRow],
    keyword_planner_ideas: list[AdsKeywordPlannerIdeaRow],
) -> list[AdsCustomSegmentCandidate]:
    grouped, rejected_by_group = _custom_segment_group_rows(rows)

    candidates: list[AdsCustomSegmentCandidate] = []
    for index, ((campaign_id, campaign_name), group_rows) in enumerate(
        sorted(grouped.items(), key=lambda item: _custom_segment_group_sort_key(item[1])),
        start=1,
    ):
        sorted_rows = sorted(group_rows, key=_search_term_row_sort_key)[:12]
        source_terms = unique(row.search_term for row in sorted_rows)[:10]
        if not source_terms:
            continue
        name = _custom_segment_name(campaign_name, index)
        rejected_pairs = rejected_by_group.get((campaign_id, campaign_name), [])
        rejected_terms = unique(term for term, _reason in rejected_pairs)
        rejection_reasons = unique(f"{term}: {reason}" for term, reason in rejected_pairs)
        matched_keyword_planner_ideas = _matching_keyword_planner_ideas(
            source_terms,
            keyword_planner_ideas,
        )
        evidence_ids = unique(
            [
                *(evidence_id for row in sorted_rows for evidence_id in row.evidence_ids),
                *(
                    evidence_id
                    for idea in matched_keyword_planner_ideas
                    for evidence_id in idea.evidence_ids
                ),
            ]
        )
        metric_facts = [
            *(fact for row in sorted_rows for fact in row.metric_facts),
            *(fact for idea in matched_keyword_planner_ideas for fact in idea.metric_facts),
        ][:28]
        payload_preview, review_score = _custom_segment_payload_and_score(
            index=index,
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            source_terms=source_terms,
            rows=sorted_rows,
            evidence_ids=evidence_ids,
            metric_facts=metric_facts,
            keyword_planner_ideas=matched_keyword_planner_ideas,
        )
        has_keyword_planner = bool(matched_keyword_planner_ideas)
        candidates.append(
            AdsCustomSegmentCandidate(
                id=payload_preview.id.removeprefix("preview_"),
                name=name,
                intent="zainteresowanie z wyszukiwanych haseł",
                review_priority=_custom_segment_review_priority(review_score),
                review_score=review_score,
                review_reason=_custom_segment_review_reason(
                    source_terms=source_terms,
                    rows=sorted_rows,
                    rejected_terms=rejected_terms,
                ),
                human_review_gates=[
                    "sprawdź intencję haseł źródłowych",
                    "odrzuć brand, konkurencję i frazy o niskiej intencji",
                    (
                        "sprawdź wzbogacenie Keyword Planner"
                        if has_keyword_planner
                        else "dodaj wzbogacenie Keyword Planner"
                    ),
                    "sprawdź prognozę albo rozmiar odbiorców",
                    "zatwierdź segment przed zapisem zmian",
                ],
                source_terms=source_terms,
                rejected_terms=unique(rejected_terms)[:12],
                rejection_reasons=unique(rejection_reasons)[:12],
                source_quality=_custom_segment_source_quality(
                    source_terms=source_terms,
                    rows=sorted_rows,
                    rejected_pairs=rejected_pairs,
                ),
                search_term_rows=sorted_rows,
                keyword_planner_ideas=matched_keyword_planner_ideas,
                source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
                evidence_ids=evidence_ids,
                metric_facts=metric_facts,
                confidence=_custom_segment_confidence(sorted_rows),
                validation_status="pending_validation",
                payload_preview=payload_preview,
                blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
                next_step=(
                    "Użyj tych terminów jako materiału do przygotowania segmentu. Podgląd zmian "
                    "jest do sprawdzenia; przed zapisem zmian wymagaj prognozy, rozmiaru "
                    "odbiorców i sprawdzenia w WILQ."
                ),
            )
        )
    return candidates[:4]


def _custom_segment_payload_and_score(
    *,
    index: int,
    campaign_id: str | None,
    campaign_name: str | None,
    source_terms: list[str],
    rows: list[AdsSearchTermMetricRow],
    evidence_ids: list[str],
    metric_facts: list[MetricFact],
    keyword_planner_ideas: list[AdsKeywordPlannerIdeaRow],
) -> tuple[AdsCustomSegmentPayloadPreview, int]:
    payload_preview = _custom_segment_change_preview(
        candidate_id=f"ads_custom_segment_{_slug(campaign_id or campaign_name or str(index))}",
        name=_custom_segment_name(campaign_name, index),
        source_terms=source_terms,
        rows=rows,
        evidence_ids=evidence_ids,
        metric_facts=metric_facts,
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        keyword_planner_enriched=bool(keyword_planner_ideas),
    )
    return (
        payload_preview,
        _custom_segment_review_score(
            source_terms=source_terms,
            rows=rows,
            payload_preview=payload_preview,
            keyword_planner_ideas=keyword_planner_ideas,
        ),
    )


def _custom_segment_group_rows(
    rows: list[AdsSearchTermMetricRow],
) -> tuple[
    dict[tuple[str | None, str | None], list[AdsSearchTermMetricRow]],
    dict[tuple[str | None, str | None], list[tuple[str, str]]],
]:
    grouped: dict[tuple[str | None, str | None], list[AdsSearchTermMetricRow]] = {}
    rejected_by_group: dict[tuple[str | None, str | None], list[tuple[str, str]]] = {}
    for row in rows:
        group_key = (row.campaign_id, row.campaign_name)
        rejection_reason = _custom_segment_rejection_reason(row)
        if rejection_reason is not None:
            rejected_by_group.setdefault(group_key, []).append((row.search_term, rejection_reason))
            continue
        grouped.setdefault(group_key, []).append(row)
    return grouped, rejected_by_group


def _matching_keyword_planner_ideas(
    source_terms: list[str],
    ideas: list[AdsKeywordPlannerIdeaRow],
) -> list[AdsKeywordPlannerIdeaRow]:
    source_terms_lower = {term.lower() for term in source_terms}
    matched = [
        idea
        for idea in ideas
        if not idea.source_terms
        or any(term.lower() in source_terms_lower for term in idea.source_terms)
    ]
    return matched[:8]


def _custom_segment_review_score(
    source_terms: list[str],
    rows: list[AdsSearchTermMetricRow],
    payload_preview: AdsCustomSegmentPayloadPreview | None,
    keyword_planner_ideas: list[AdsKeywordPlannerIdeaRow],
) -> int:
    total_clicks = sum(row.clicks or 0 for row in rows)
    total_impressions = sum(row.impressions or 0 for row in rows)
    total_cost = sum(row.cost_micros or 0 for row in rows) / 1_000_000
    total_conversions = sum(row.conversions or 0 for row in rows)
    score = float(min(len(source_terms) * 8, 25))
    score += min(total_clicks * 4, 25)
    score += min(total_impressions / 50, 15)
    score += min(total_cost, 15)
    if total_conversions > 0:
        score += 10
    if payload_preview is not None:
        score += 10
    if keyword_planner_ideas:
        score += 10
    return min(100, int(round(score)))


def _custom_segment_review_priority(
    review_score: int,
) -> Literal["pilne", "wysokie", "normalne", "niski sygnał"]:
    if review_score >= 70:
        return "pilne"
    if review_score >= 45:
        return "wysokie"
    if review_score >= 15:
        return "normalne"
    return "niski sygnał"


def _custom_segment_review_reason(
    source_terms: list[str],
    rows: list[AdsSearchTermMetricRow],
    rejected_terms: list[str],
) -> str:
    total_clicks = sum(row.clicks or 0 for row in rows)
    total_conversions = sum(row.conversions or 0 for row in rows)
    return (
        f"{len(source_terms)} haseł źródłowych, {total_clicks} kliknięć, "
        f"wyświetlenia {_search_term_impressions_review_value(rows)}, "
        f"koszt {_search_term_cost_review_value(rows)}, "
        f"{_format_float(float(total_conversions))} konwersji, "
        f"{len(unique(rejected_terms))} odrzuconych terminów. "
        "To jest kolejność oceny segmentu, nie dowód rozmiaru odbiorców, kierowania "
        "reklam ani wpływu na kampanię."
    )


def _custom_segment_source_quality(
    source_terms: list[str],
    rows: list[AdsSearchTermMetricRow],
    rejected_pairs: list[tuple[str, str]],
) -> AdsCustomSegmentSourceQuality:
    accepted_terms = len(unique(source_terms))
    rejected_terms = len(unique(term for term, _reason in rejected_pairs))
    reason_counts: dict[str, int] = {}
    for _term, reason in rejected_pairs:
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    missing_metric_terms = sum(1 for row in rows if row.missing_metrics)
    return AdsCustomSegmentSourceQuality(
        total_terms=accepted_terms + rejected_terms,
        accepted_terms=accepted_terms,
        rejected_terms=rejected_terms,
        missing_metric_terms=missing_metric_terms,
        rejection_reasons=dict(sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))),
    )


def _search_term_impressions_review_value(rows: list[AdsSearchTermMetricRow]) -> str:
    if not any(row.impressions is not None for row in rows):
        return "niepotwierdzone"
    return str(sum(row.impressions or 0 for row in rows))


def _search_term_cost_review_value(rows: list[AdsSearchTermMetricRow]) -> str:
    if not any(row.cost_micros is not None for row in rows):
        return "niepotwierdzony"
    return _format_micros(sum(row.cost_micros or 0 for row in rows)) or "0"


def _custom_segment_change_preview(
    candidate_id: str,
    name: str,
    source_terms: list[str],
    rows: list[AdsSearchTermMetricRow],
    evidence_ids: list[str],
    metric_facts: list[MetricFact],
    campaign_id: str | None,
    campaign_name: str | None,
    keyword_planner_enriched: bool,
) -> AdsCustomSegmentPayloadPreview:
    source_metric_names = unique(
        fact.name for fact in metric_facts if fact.name.startswith("search_term_")
    )
    row_terms = unique(row.search_term for row in rows)
    preview_id = f"preview_{candidate_id}"
    return AdsCustomSegmentPayloadPreview(
        id=preview_id,
        custom_segment_name=name,
        member_type="KEYWORD",
        member_type_label="słowa kluczowe",
        source_terms=[term for term in source_terms if term in row_terms],
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        reason=(
            "Podgląd zmian do sprawdzenia dla segmentu Google Ads opartego na hasłach "
            "z realnych wyszukiwanych haseł. To nie jest gotowy zapis zmian ani targetowanie."
        ),
        evidence_ids=evidence_ids,
        source_metric_names=source_metric_names,
        required_validation=[
            "review_source_terms",
            "reject_brand_or_low_intent_terms",
            "keyword_planner_enrichment",
            "forecast_or_audience_size",
            "human_confirm_before_apply",
        ],
        blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
        targeting_preview=[
            AdsCustomSegmentTargetingPreview(
                id=f"targeting_{preview_id}",
                custom_segment_preview_id=preview_id,
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                reason=(
                    "Do sprawdzenia: podgląd kampanii, do której można wrócić po "
                    "sprawdzenia segmentu. To nie jest targetowanie ani mutacja Ads."
                ),
                required_validation=[
                    "keyword_planner_enrichment",
                    "forecast_or_audience_size",
                    "human_confirm_before_apply",
                    "mutation_audit_required",
                ],
                blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
                api_mutation_ready=False,
                apply_allowed=False,
                destructive=False,
            )
        ],
        safety_review=AdsCustomSegmentApplySafetyReview.model_validate(
            custom_segment_apply_safety_review(
                preview_id=preview_id,
                evidence_ids=evidence_ids,
                keyword_planner_enriched=keyword_planner_enriched,
                forecast_available=False,
            )
        ),
        api_mutation_ready=False,
        apply_allowed=False,
        destructive=False,
    )


def _hydrate_custom_segments_marketer_labels(
    contract: AdsCustomSegmentsReadContract,
) -> None:
    contract.missing_read_contract_labels = _ads_missing_read_contract_labels(
        contract.missing_read_contracts
    )
    contract.blocked_claim_labels = unique(contract.blocked_claims)
    forecast_contract = contract.audience_forecast_read_contract
    forecast_contract.missing_read_contract_labels = _ads_missing_read_contract_labels(
        forecast_contract.missing_read_contracts
    )
    forecast_contract.blocked_claim_labels = unique(forecast_contract.blocked_claims)

    for candidate in contract.candidates:
        candidate.confidence_label = _ads_confidence_label(candidate.confidence)
        candidate.validation_status_label = _ads_validation_status_label(
            candidate.validation_status
        )
        candidate.blocked_claim_labels = unique(candidate.blocked_claims)
        candidate.source_quality.rejection_reason_labels = {
            _custom_segment_rejection_reason_label(reason): count
            for reason, count in candidate.source_quality.rejection_reasons.items()
        }
        if candidate.payload_preview is not None:
            _hydrate_custom_segment_payload_preview_labels(candidate.payload_preview)
            candidate.preview_card = _custom_segment_preview_card(candidate.payload_preview)

    for preview in contract.payload_preview:
        _hydrate_custom_segment_payload_preview_labels(preview)

    for row in forecast_contract.forecast_rows:
        row.blocked_claim_labels = unique(row.blocked_claims)


def _custom_segment_preview_card(
    preview: AdsCustomSegmentPayloadPreview,
) -> ActionPreviewCardViewModel:
    targeting_preview = preview.targeting_preview[0] if preview.targeting_preview else None
    safety_review = preview.safety_review
    rows = [
        _ads_preview_row("Nazwa", preview.custom_segment_name),
        _ads_preview_row(
            "Typ odbiorców",
            preview.member_type_label or "typ odbiorców do sprawdzenia",
        ),
        _ads_preview_row(
            "Hasła źródłowe",
            ", ".join(preview.source_terms[:4]) if preview.source_terms else "brak haseł",
        ),
        _ads_preview_row(
            "Kampania do sprawdzenia",
            (
                targeting_preview.campaign_name
                if targeting_preview is not None and targeting_preview.campaign_name
                else "kampania do sprawdzenia"
            ),
        ),
        _ads_preview_row("Bezpieczeństwo", safety_review.status_label or "wymaga sprawdzenia"),
    ]
    if safety_review.missing_requirement_labels:
        rows.append(
            _ads_preview_row("Braki", ", ".join(safety_review.missing_requirement_labels[:4]))
        )
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
        id=_ads_preview_card_id("google_ads_custom_segment_review", preview.id),
        kind="google_ads_custom_segment_review",
        title_label="Segment odbiorców do sprawdzenia",
        subtitle_label="ocena segmentu bez zapisu zmian",
        status_label="zapis zmian zablokowany",
        rows=rows,
        apply_state_label=(
            "możliwy zapis po sprawdzeniu" if preview.apply_allowed else "zapis zmian zablokowany"
        ),
        system_readiness_label=(
            "system gotowy do zapisu" if preview.api_mutation_ready else "wymaga kontroli"
        ),
    )


def _hydrate_custom_segment_payload_preview_labels(
    preview: AdsCustomSegmentPayloadPreview,
) -> None:
    preview.required_validation_labels = _ads_review_gate_labels(preview.required_validation)
    preview.blocked_claim_labels = unique(preview.blocked_claims)
    safety_review = preview.safety_review
    safety_review.status_label = _ads_status_label(safety_review.status)
    safety_review.missing_requirement_labels = _ads_missing_read_contract_labels(
        safety_review.missing_requirements
    )
    safety_review.required_validation_labels = _ads_review_gate_labels(
        safety_review.required_validation
    )
    safety_review.blocked_claim_labels = unique(safety_review.blocked_claims)
    for target in preview.targeting_preview:
        target.required_validation_labels = _ads_review_gate_labels(target.required_validation)
        target.blocked_claim_labels = unique(target.blocked_claims)


def _custom_segment_rejection_reason_label(reason: str) -> str:
    labels = {
        "brand_or_generic": "brand albo zbyt ogólna fraza",
        "short_or_low_signal": "za krótka fraza albo za słaby sygnał",
        "no_click_or_conversion_signal": "brak kliknięć albo sygnału celu",
    }
    return labels.get(reason, "odrzucona fraza do sprawdzenia")
