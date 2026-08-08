from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Literal

from wilq.briefing.ads_landing_service_binding import (
    resolve_ads_landing_service_binding,
)
from wilq.briefing.ads_metric_utils import (
    format_money_micros as _format_money_micros,
)
from wilq.briefing.ads_search_contracts import (
    build_search_term_read_contracts,
    build_search_term_review_contracts,
)
from wilq.schemas import (
    AdsKeywordMatchContextReadContract,
    AdsKeywordMatchContextRow,
    AdsKeywordPlannerReadContract,
    AdsSearchTermCampaignReviewRow,
    AdsSearchTermMetricRow,
    AdsSearchTermNgramReadContract,
    AdsSearchTermNgramRow,
    AdsSearchTermReviewRow,
    AdsSearchTermReviewSummaryContract,
    AdsSearchTermSafetyReadContract,
    AdsSearchTermSafetyRow,
    AdsSearchTermsReadContract,
    ConnectorRefreshRun,
    MetricFact,
)
from wilq.storage.metric_store import metric_store as metric_store

from .custom_segments import (
    _keyword_planner_read_contract,
)
from .negative_keywords import (
    _ads_keyword_match_type_label,
)
from .shared import (
    ADS_METRIC_FACT_LIMIT,
    ADS_SEARCH_TERM_ROW_LIMIT_30D,
    ADS_SEARCH_TERM_ROW_LIMIT_90D,
    ADS_SUMMARY_METRIC_FACT_LIMIT,
    GOOGLE_ADS_CONNECTOR_ID,
    _float_metric_value,
    _format_float,
    _int_metric_value,
    _latest_refresh_has_summary_metric,
    _refresh_or_connector_evidence_ids,
    _remove_missing_contract_names,
    _search_term_coverage,
    _search_term_row_sort_key,
    _unique,
)

ADS_NGRAM_STOPWORDS = {
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


def _build_ads_search_term_read_contracts(
    trusted_metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
    currency_code: str | None,
) -> tuple[
    AdsSearchTermsReadContract,
    AdsSearchTermSafetyReadContract,
    AdsKeywordMatchContextReadContract,
    AdsKeywordPlannerReadContract,
]:
    return build_search_term_read_contracts(
        trusted_metric_facts,
        latest_refresh,
        currency_code,
        search_terms=_search_terms_read_contract,
        search_term_safety=_search_term_safety_read_contract,
        keyword_match_context=_keyword_match_context_read_contract,
        keyword_planner=_keyword_planner_read_contract,
    )


def _build_ads_search_term_review_contracts(
    search_terms_read_contract: AdsSearchTermsReadContract,
    latest_refresh: ConnectorRefreshRun | None,
    currency_code: str | None,
) -> tuple[
    AdsSearchTermReviewSummaryContract,
    AdsSearchTermNgramReadContract,
]:
    return build_search_term_review_contracts(
        search_terms_read_contract,
        latest_refresh,
        currency_code,
        review_summary=_search_term_review_summary_contract,
        ngram=_search_term_ngram_read_contract,
    )


def _reconcile_search_term_read_contracts(
    search_terms_read_contract: AdsSearchTermsReadContract,
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract,
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract,
) -> tuple[AdsSearchTermsReadContract, AdsSearchTermSafetyReadContract]:
    if search_term_safety_read_contract.status == "ready":
        search_terms_read_contract = search_terms_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    search_terms_read_contract.missing_read_contracts,
                    "90_day_safety_check",
                )
            }
        )
    if keyword_match_context_read_contract.status == "ready":
        search_terms_read_contract = search_terms_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    search_terms_read_contract.missing_read_contracts,
                    "keyword match context",
                )
            }
        )
        search_term_safety_read_contract = search_term_safety_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    search_term_safety_read_contract.missing_read_contracts,
                    "keyword match context",
                )
            }
        )
    return search_terms_read_contract, search_term_safety_read_contract


def _ads_metric_facts_for_view(
    view: Literal["full", "summary"],
    latest_refresh: ConnectorRefreshRun | None,
) -> list[MetricFact]:
    if view == "summary" and latest_refresh is not None and latest_refresh.evidence_ids:
        latest_evidence_facts = metric_store().list_metric_facts_by_evidence_ids(
            latest_refresh.evidence_ids
        )
        if not latest_refresh.metrics_persisted:
            return latest_evidence_facts
        if latest_evidence_facts:
            return latest_evidence_facts
        if (
            "row_count" in latest_refresh.metric_summary
            and not latest_refresh.vendor_data_collected
        ):
            return latest_evidence_facts

    metric_fact_limit = (
        ADS_SUMMARY_METRIC_FACT_LIMIT if view == "summary" else ADS_METRIC_FACT_LIMIT
    )
    return metric_store().list_metric_facts(
        connector_id=GOOGLE_ADS_CONNECTOR_ID,
        limit=metric_fact_limit,
    )


def _search_terms_read_contract(
    metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
    currency_code: str | None,
) -> AdsSearchTermsReadContract:
    rows = _search_term_metric_rows(metric_facts)
    missing_read_contracts = [
        "keyword match context",
        "90_day_safety_check",
    ]
    operator_review_gates = ["negative_keyword_action_validation"]
    blocked_claims = [
        "marnowanie budżetu na zapytaniach",
        "propozycje wykluczeń",
        "dodanie wykluczających słów kluczowych",
        "koszt pozyskania celu",
        "zwrot z reklam",
        "utrata konwersji",
    ]
    if rows:
        total_clicks = sum(row.clicks or 0 for row in rows)
        total_impressions = sum(row.impressions or 0 for row in rows)
        total_cost_micros = sum(row.cost_micros or 0 for row in rows)
        total_conversions = sum(row.conversions or 0 for row in rows)
        total_conversion_value = sum(row.conversion_value or 0 for row in rows)
        return AdsSearchTermsReadContract(
            status="ready",
            title="Google Ads: zapytania użytkowników",
            summary=(
                f"WILQ ma {len(rows)} wierszy zapytań: {total_clicks} kliknięć, "
                f"{total_impressions} wyświetleń, "
                f"koszt {_format_money_micros(total_cost_micros, currency_code)}, "
                f"{_format_float(total_conversions)} konwersji, "
                f"wartość konwersji {_format_float(total_conversion_value)}."
            ),
            allowed_metrics=[
                "search_term",
                "campaign",
                "ad_group",
                "status",
                "clicks",
                "impressions",
                "cost_micros",
                "conversions",
                "conversion_value",
            ],
            missing_read_contracts=missing_read_contracts,
            operator_review_gates=operator_review_gates,
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(evidence_id for row in rows for evidence_id in row.evidence_ids),
            coverage=[
                _search_term_coverage(
                    window="last_30_days",
                    returned_row_count=len(rows),
                    requested_row_limit=ADS_SEARCH_TERM_ROW_LIMIT_30D,
                )
            ],
            search_term_rows=rows,
            next_step=(
                "Użyj wierszy zapytań jako przeglądu danych z reklam. Nie twórz "
                "wykluczeń ani obietnic o marnowaniu budżetu bez kontekstu dopasowania, 90-dniowej "
                "kontroli i akcji do sprawdzenia."
            ),
        )

    return AdsSearchTermsReadContract(
        status="blocked",
        title="Google Ads: brak zapytań użytkowników",
        summary="WILQ nie ma jeszcze wymiarowych faktów z `search_term_view`.",
        allowed_metrics=[],
        missing_read_contracts=["search_term_view", *missing_read_contracts],
        blocked_claims=["wyszukiwane hasła", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        coverage=[
            _search_term_coverage(
                window="last_30_days",
                returned_row_count=0,
                requested_row_limit=ADS_SEARCH_TERM_ROW_LIMIT_30D,
                blocked=True,
            )
        ],
        search_term_rows=[],
        next_step=(
            "Uruchom odczyt danych Google Ads po dodaniu odczytu `search_term_view` "
            "i zapisz metryki search_term_*."
        ),
    )


def _search_term_review_summary_contract(
    search_terms_read_contract: AdsSearchTermsReadContract,
    latest_refresh: ConnectorRefreshRun | None,
    currency_code: str | None,
) -> AdsSearchTermReviewSummaryContract:
    rows = search_terms_read_contract.search_term_rows
    blocked_claims = [
        "marnowanie budżetu na zapytaniach",
        "dodanie wykluczających słów kluczowych",
        "koszt pozyskania celu",
        "zwrot z reklam",
    ]
    if not rows:
        return AdsSearchTermReviewSummaryContract(
            status="blocked",
            title="Google Ads: brak kolejki oceny wyszukiwanych haseł",
            summary=(
                "WILQ nie ma wierszy wyszukiwanych haseł, więc nie może wskazać kolejności oceny."
            ),
            allowed_metrics=[],
            missing_read_contracts=["search_term_view"],
            operator_review_gates=[],
            blocked_claims=["wyszukiwane hasła", *blocked_claims],
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            top_cost_search_terms=[],
            campaign_review_rows=[],
            next_step="Uruchom odczyt danych Google Ads z odczytem `search_term_view`.",
        )

    total_clicks = sum(row.clicks or 0 for row in rows)
    total_impressions = sum(row.impressions or 0 for row in rows)
    total_cost_micros = sum(row.cost_micros or 0 for row in rows)
    total_conversions = sum(row.conversions or 0 for row in rows)
    zero_conversion_count = sum(1 for row in rows if row.conversions == 0)
    campaign_review_rows = _search_term_campaign_review_rows(rows)
    return AdsSearchTermReviewSummaryContract(
        status="ready",
        title="Google Ads: kolejność oceny wyszukiwanych haseł",
        summary=(
            f"WILQ ma {len(rows)} wierszy wyszukiwanych haseł do ręcznej oceny: "
            f"{total_clicks} kliknięć, {total_impressions} wyświetleń, "
            f"koszt {_format_money_micros(total_cost_micros, currency_code)}, "
            f"{_format_float(total_conversions)} konwersji, "
            f"{zero_conversion_count} wierszy bez konwersji."
        ),
        allowed_metrics=search_terms_read_contract.allowed_metrics,
        missing_read_contracts=search_terms_read_contract.missing_read_contracts,
        operator_review_gates=_unique(
            ["human_intent_review", *search_terms_read_contract.operator_review_gates]
        ),
        blocked_claims=blocked_claims,
        source_connectors=search_terms_read_contract.source_connectors,
        evidence_ids=search_terms_read_contract.evidence_ids,
        coverage=search_terms_read_contract.coverage,
        total_search_term_count=len(rows),
        zero_conversion_search_term_count=zero_conversion_count,
        total_clicks=total_clicks,
        total_impressions=total_impressions,
        total_cost_micros=total_cost_micros,
        total_conversions=round(total_conversions, 6),
        top_cost_search_terms=[_search_term_review_row(row) for row in rows[:5]],
        campaign_review_rows=campaign_review_rows,
        next_step=(
            "Najpierw przejrzyj kampanie i zapytania z największym kosztem. "
            "Nie nazywaj ich stratą budżetu i nie twórz wykluczeń bez oceny intencji, "
            "kontroli 90 dni, podglądu zmian i sprawdzenia w WILQ."
        ),
    )


def _search_term_review_row(row: AdsSearchTermMetricRow) -> AdsSearchTermReviewRow:
    return AdsSearchTermReviewRow(
        search_term=row.search_term,
        campaign_id=row.campaign_id,
        campaign_name=row.campaign_name,
        ad_group_id=row.ad_group_id,
        ad_group_name=row.ad_group_name,
        search_term_status=row.search_term_status,
        clicks=row.clicks,
        impressions=row.impressions,
        cost_micros=row.cost_micros,
        conversions=row.conversions,
        evidence_ids=row.evidence_ids,
        blocked_claims=[
            "marnowanie budżetu na zapytaniach",
            "dodanie wykluczających słów kluczowych",
            "koszt pozyskania celu",
            "zwrot z reklam",
        ],
    )


def _search_term_campaign_review_rows(
    rows: list[AdsSearchTermMetricRow],
) -> list[AdsSearchTermCampaignReviewRow]:
    grouped: dict[tuple[str | None, str | None], list[AdsSearchTermMetricRow]] = {}
    for row in rows:
        grouped.setdefault((row.campaign_id, row.campaign_name), []).append(row)

    review_rows = []
    for (campaign_id, campaign_name), campaign_rows in grouped.items():
        review_rows.append(
            AdsSearchTermCampaignReviewRow(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                search_term_count=len(campaign_rows),
                zero_conversion_search_term_count=sum(
                    1 for row in campaign_rows if row.conversions == 0
                ),
                clicks=sum(row.clicks or 0 for row in campaign_rows),
                impressions=sum(row.impressions or 0 for row in campaign_rows),
                cost_micros=sum(row.cost_micros or 0 for row in campaign_rows),
                conversions=round(
                    sum(row.conversions or 0 for row in campaign_rows),
                    6,
                ),
                evidence_ids=_unique(
                    evidence_id for row in campaign_rows for evidence_id in row.evidence_ids
                ),
                blocked_claims=[
                    "marnowanie budżetu na zapytaniach",
                    "dodanie wykluczających słów kluczowych",
                    "koszt pozyskania celu",
                    "zwrot z reklam",
                ],
            )
        )
    return sorted(
        review_rows,
        key=lambda row: (-row.cost_micros, -row.clicks, row.campaign_name or ""),
    )


def _search_term_metric_rows(metric_facts: list[MetricFact]) -> list[AdsSearchTermMetricRow]:
    grouped_facts: dict[tuple[str, str | None, str | None], list[MetricFact]] = {}
    seen_metric_keys: set[tuple[str, str | None, str | None, str]] = set()
    for fact in metric_facts:
        if fact.name not in {
            "search_term_clicks",
            "search_term_impressions",
            "search_term_cost_micros",
            "search_term_conversions",
            "search_term_conversion_value",
        }:
            continue
        search_term = fact.dimensions.get("search_term")
        if not search_term:
            continue
        campaign_id = fact.dimensions.get("campaign_id")
        ad_group_id = fact.dimensions.get("ad_group_id")
        row_key = (search_term, campaign_id, ad_group_id)
        metric_key = (*row_key, fact.name)
        if metric_key in seen_metric_keys:
            continue
        seen_metric_keys.add(metric_key)
        grouped_facts.setdefault(row_key, []).append(fact)

    rows = [
        _search_term_metric_row(search_term, campaign_id, ad_group_id, facts)
        for (search_term, campaign_id, ad_group_id), facts in grouped_facts.items()
    ]
    return sorted(rows, key=_search_term_row_sort_key)


def _search_term_metric_row(
    search_term: str,
    campaign_id: str | None,
    ad_group_id: str | None,
    facts: list[MetricFact],
) -> AdsSearchTermMetricRow:
    facts_by_name = {fact.name: fact for fact in facts}
    expected_metrics = [
        "search_term_clicks",
        "search_term_impressions",
        "search_term_cost_micros",
        "search_term_conversions",
        "search_term_conversion_value",
    ]
    first_dimensions = facts[0].dimensions if facts else {}
    return AdsSearchTermMetricRow(
        search_term=search_term,
        campaign_id=campaign_id,
        campaign_name=first_dimensions.get("campaign_name"),
        ad_group_id=ad_group_id,
        ad_group_name=first_dimensions.get("ad_group_name"),
        search_term_status=first_dimensions.get("search_term_status"),
        landing_mapping_status=first_dimensions.get("landing_mapping_status"),
        landing_identity_sha256=first_dimensions.get("landing_identity_sha256"),
        landing_service_binding=resolve_ads_landing_service_binding(
            first_dimensions.get("landing_identity_sha256")
        ),
        clicks=_int_metric_value(facts_by_name.get("search_term_clicks")),
        impressions=_int_metric_value(facts_by_name.get("search_term_impressions")),
        cost_micros=_int_metric_value(facts_by_name.get("search_term_cost_micros")),
        conversions=_float_metric_value(facts_by_name.get("search_term_conversions")),
        conversion_value=_float_metric_value(facts_by_name.get("search_term_conversion_value")),
        evidence_ids=_unique(fact.evidence_id for fact in facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        missing_metrics=[name for name in expected_metrics if name not in facts_by_name],
        blocked_claims=[
            "koszt pozyskania celu",
            "zwrot z reklam",
            "dodanie wykluczających słów kluczowych",
            "zmarnowany budżet",
        ],
    )


def _search_term_ngram_read_contract(
    search_terms_read_contract: AdsSearchTermsReadContract,
    latest_refresh: ConnectorRefreshRun | None,
    currency_code: str | None,
) -> AdsSearchTermNgramReadContract:
    rows = _search_term_ngram_rows(search_terms_read_contract.search_term_rows)
    blocked_claims = [
        "marnowanie budżetu na zapytaniach",
        "propozycje wykluczeń",
        "dodanie wykluczających słów kluczowych",
        "koszt pozyskania celu",
        "zwrot z reklam",
        "utrata konwersji",
    ]
    if rows:
        total_terms = sum(row.source_search_term_count for row in rows)
        total_clicks = sum(row.clicks or 0 for row in rows)
        total_cost_micros = sum(row.cost_micros or 0 for row in rows)
        return AdsSearchTermNgramReadContract(
            status="ready",
            title="Google Ads: n-gramy zapytań",
            summary=(
                f"WILQ zgrupował {len(rows)} n-gramów z {total_terms} wystąpień "
                f"wyszukiwanych haseł: {total_clicks} kliknięć, "
                f"koszt {_format_money_micros(total_cost_micros, currency_code)}."
            ),
            allowed_metrics=[
                "ngram",
                "ngram_size",
                "source_search_term_count",
                "sample_search_terms",
                "clicks",
                "impressions",
                "cost_micros",
                "conversions",
                "conversion_value",
            ],
            missing_read_contracts=[
                "human_intent_review",
                "ngram_to_negative_keyword_change_preview",
            ],
            operator_review_gates=[
                "human_intent_review",
                "negative_keyword_action_validation",
            ],
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(evidence_id for row in rows for evidence_id in row.evidence_ids),
            coverage=search_terms_read_contract.coverage,
            ngram_rows=rows,
            next_step=(
                "Użyj n-gramów do znalezienia powtarzających się tematów w "
                "zapytaniach. Nie traktuj ich jako gotowej listy wykluczeń bez "
                "oceny intencji, 90-dniowego odczytu bezpieczeństwa i podglądu zmian."
            ),
        )

    return AdsSearchTermNgramReadContract(
        status="blocked",
        title="Google Ads: brak n-gramów zapytań",
        summary=("WILQ nie ma wierszy wyszukiwanych haseł, więc nie może zbudować n-gramów."),
        allowed_metrics=[],
        missing_read_contracts=["search_term_view"],
        operator_review_gates=[],
        blocked_claims=["wyszukiwane hasła", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        coverage=search_terms_read_contract.coverage,
        ngram_rows=[],
        next_step="Uruchom odczyt danych Google Ads z odczytem `search_term_view`.",
    )


def _search_term_ngram_rows(
    rows: list[AdsSearchTermMetricRow],
) -> list[AdsSearchTermNgramRow]:
    grouped_rows: dict[tuple[str, int], list[AdsSearchTermMetricRow]] = {}
    for row in rows:
        tokens = _search_term_tokens(row.search_term)
        for ngram_size in (1, 2, 3):
            if len(tokens) < ngram_size:
                continue
            seen_for_row: set[tuple[str, int]] = set()
            for index in range(0, len(tokens) - ngram_size + 1):
                ngram = " ".join(tokens[index : index + ngram_size])
                key = (ngram, ngram_size)
                if key in seen_for_row:
                    continue
                seen_for_row.add(key)
                grouped_rows.setdefault(key, []).append(row)

    ngram_rows = [
        _search_term_ngram_row(ngram, ngram_size, source_rows)
        for (ngram, ngram_size), source_rows in grouped_rows.items()
    ]
    return sorted(ngram_rows, key=_search_term_ngram_sort_key)[:30]


def _search_term_tokens(search_term: str) -> list[str]:
    tokens = re.findall(r"[\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+", search_term.lower())
    return [token for token in tokens if len(token) > 1 and token not in ADS_NGRAM_STOPWORDS]


def _search_term_ngram_row(
    ngram: str,
    ngram_size: int,
    rows: list[AdsSearchTermMetricRow],
) -> AdsSearchTermNgramRow:
    metric_facts = _dedupe_metric_facts(fact for row in rows for fact in row.metric_facts)
    missing_metrics = _unique(metric for row in rows for metric in row.missing_metrics)
    sample_search_terms = _unique(row.search_term for row in rows)[:3]
    return AdsSearchTermNgramRow(
        ngram=ngram,
        ngram_size=ngram_size,
        source_search_term_count=len({row.search_term for row in rows}),
        sample_search_terms=sample_search_terms,
        clicks=sum(row.clicks or 0 for row in rows),
        impressions=sum(row.impressions or 0 for row in rows),
        cost_micros=sum(row.cost_micros or 0 for row in rows),
        conversions=round(sum(row.conversions or 0 for row in rows), 6),
        conversion_value=round(sum(row.conversion_value or 0 for row in rows), 6),
        evidence_ids=_unique(evidence_id for row in rows for evidence_id in row.evidence_ids),
        metric_facts=metric_facts[:12],
        missing_metrics=missing_metrics,
        blocked_claims=[
            "koszt pozyskania celu",
            "zwrot z reklam",
            "dodanie wykluczających słów kluczowych",
            "marnowanie budżetu na zapytaniach",
        ],
    )


def _dedupe_metric_facts(facts: Iterable[MetricFact]) -> list[MetricFact]:
    deduped: list[MetricFact] = []
    seen: set[tuple[str, str, tuple[tuple[str, str], ...]]] = set()
    for fact in facts:
        key = (fact.name, fact.evidence_id, tuple(sorted(fact.dimensions.items())))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(fact)
    return sorted(deduped, key=lambda fact: (fact.name, fact.evidence_id))


def _search_term_ngram_sort_key(
    row: AdsSearchTermNgramRow,
) -> tuple[int, int, int, int, str]:
    return (
        -(row.cost_micros or 0),
        -(row.clicks or 0),
        -row.source_search_term_count,
        row.ngram_size,
        row.ngram,
    )


def _search_term_safety_read_contract(
    metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
    currency_code: str | None,
) -> AdsSearchTermSafetyReadContract:
    rows = _search_term_safety_rows(metric_facts)
    read_attempted = _latest_refresh_has_summary_metric(
        latest_refresh,
        "search_term_safety_row_count",
    )
    blocked_claims = [
        "dodanie wykluczających słów kluczowych",
        "marnowanie budżetu na zapytaniach",
        "utrata konwersji",
        "koszt pozyskania celu",
        "zwrot z reklam",
    ]
    if rows or read_attempted:
        total_clicks = sum(row.clicks_90d or 0 for row in rows)
        total_impressions = sum(row.impressions_90d or 0 for row in rows)
        total_cost_micros = sum(row.cost_micros_90d or 0 for row in rows)
        total_conversions = sum(row.conversions_90d or 0 for row in rows)
        total_conversion_value = sum(row.conversion_value_90d or 0 for row in rows)
        return AdsSearchTermSafetyReadContract(
            status="ready",
            title="Google Ads: 90-dniowy odczyt bezpieczeństwa zapytań",
            summary=(
                f"WILQ ma 90-dniowy odczyt bezpieczeństwa dla {len(rows)} zapytań: "
                f"{total_clicks} kliknięć, {total_impressions} wyświetleń, "
                f"koszt {_format_money_micros(total_cost_micros, currency_code)}, "
                f"{_format_float(total_conversions)} konwersji, "
                f"wartość konwersji {_format_float(total_conversion_value)}."
            ),
            allowed_metrics=[
                "search_term",
                "campaign",
                "ad_group",
                "status",
                "search_term_90d_clicks",
                "search_term_90d_impressions",
                "search_term_90d_cost_micros",
                "search_term_90d_conversions",
                "search_term_90d_conversion_value",
            ],
            missing_read_contracts=[
                "keyword match context",
            ],
            operator_review_gates=["human_intent_review"],
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(evidence_id for row in rows for evidence_id in row.evidence_ids)
            or _refresh_or_connector_evidence_ids(latest_refresh),
            coverage=[
                _search_term_coverage(
                    window="search_term_safety_90d",
                    returned_row_count=len(rows),
                    requested_row_limit=ADS_SEARCH_TERM_ROW_LIMIT_90D,
                )
            ],
            safety_rows=rows,
            next_step=(
                "Użyj 90-dniowego odczytu jako hamulca bezpieczeństwa. Jeśli termin "
                "ma konwersje w 90 dniach, nie kwalifikuj go do wykluczenia; jeśli "
                "nie ma konwersji, nadal wymagaj oceny intencji, kontekstu dopasowań "
                "i podglądu zmian."
            ),
        )

    return AdsSearchTermSafetyReadContract(
        status="blocked",
        title="Google Ads: brak 90-dniowego odczytu bezpieczeństwa",
        summary="WILQ nie ma jeszcze 90-dniowego odczytu listy wyszukiwanych haseł.",
        allowed_metrics=[],
        missing_read_contracts=[
            "search_term_90d_read",
            "keyword match context",
            "negative_keyword_change_preview",
        ],
        blocked_claims=["90-dniowa kontrola bezpieczeństwa wykluczeń", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        coverage=[
            _search_term_coverage(
                window="search_term_safety_90d",
                returned_row_count=0,
                requested_row_limit=ADS_SEARCH_TERM_ROW_LIMIT_90D,
                blocked=True,
            )
        ],
        safety_rows=[],
        next_step=(
            "Uruchom 90-dniowy odczyt wyszukiwanych haseł w Google Ads. Nie twórz "
            "wykluczeń bez tego hamulca bezpieczeństwa."
        ),
    )


def _search_term_safety_rows(metric_facts: list[MetricFact]) -> list[AdsSearchTermSafetyRow]:
    grouped_facts: dict[tuple[str, str | None, str | None], list[MetricFact]] = {}
    seen_metric_keys: set[tuple[str, str | None, str | None, str]] = set()
    for fact in metric_facts:
        if fact.name not in {
            "search_term_90d_clicks",
            "search_term_90d_impressions",
            "search_term_90d_cost_micros",
            "search_term_90d_conversions",
            "search_term_90d_conversion_value",
        }:
            continue
        search_term = fact.dimensions.get("search_term")
        if not search_term:
            continue
        campaign_id = fact.dimensions.get("campaign_id")
        ad_group_id = fact.dimensions.get("ad_group_id")
        row_key = (search_term, campaign_id, ad_group_id)
        metric_key = (*row_key, fact.name)
        if metric_key in seen_metric_keys:
            continue
        seen_metric_keys.add(metric_key)
        grouped_facts.setdefault(row_key, []).append(fact)

    rows = [
        _search_term_safety_row(search_term, campaign_id, ad_group_id, facts)
        for (search_term, campaign_id, ad_group_id), facts in grouped_facts.items()
    ]
    return sorted(rows, key=_search_term_safety_row_sort_key)


def _search_term_safety_row(
    search_term: str,
    campaign_id: str | None,
    ad_group_id: str | None,
    facts: list[MetricFact],
) -> AdsSearchTermSafetyRow:
    facts_by_name = {fact.name: fact for fact in facts}
    expected_metrics = [
        "search_term_90d_clicks",
        "search_term_90d_impressions",
        "search_term_90d_cost_micros",
        "search_term_90d_conversions",
        "search_term_90d_conversion_value",
    ]
    first_dimensions = facts[0].dimensions if facts else {}
    return AdsSearchTermSafetyRow(
        search_term=search_term,
        campaign_id=campaign_id,
        campaign_name=first_dimensions.get("campaign_name"),
        ad_group_id=ad_group_id,
        ad_group_name=first_dimensions.get("ad_group_name"),
        search_term_status=first_dimensions.get("search_term_status"),
        clicks_90d=_int_metric_value(facts_by_name.get("search_term_90d_clicks")),
        impressions_90d=_int_metric_value(facts_by_name.get("search_term_90d_impressions")),
        cost_micros_90d=_int_metric_value(facts_by_name.get("search_term_90d_cost_micros")),
        conversions_90d=_float_metric_value(facts_by_name.get("search_term_90d_conversions")),
        conversion_value_90d=_float_metric_value(
            facts_by_name.get("search_term_90d_conversion_value")
        ),
        evidence_ids=_unique(fact.evidence_id for fact in facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        missing_metrics=[name for name in expected_metrics if name not in facts_by_name],
        blocked_claims=[
            "koszt pozyskania celu",
            "zwrot z reklam",
            "dodanie wykluczających słów kluczowych",
            "zmarnowany budżet",
        ],
    )


def _search_term_safety_row_sort_key(
    row: AdsSearchTermSafetyRow,
) -> tuple[int, int, str]:
    return (-(row.cost_micros_90d or 0), -(row.clicks_90d or 0), row.search_term)


def _keyword_match_context_read_contract(
    metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
) -> AdsKeywordMatchContextReadContract:
    rows = _keyword_match_context_rows(metric_facts)
    read_attempted = _latest_refresh_has_summary_metric(
        latest_refresh,
        "keyword_match_context_row_count",
    )
    blocked_claims = [
        "dodanie wykluczających słów kluczowych",
        "marnowanie budżetu na zapytaniach",
        "utrata konwersji",
        "koszt pozyskania celu",
        "zwrot z reklam",
    ]
    if rows or read_attempted:
        match_type_labels = _unique(
            _ads_keyword_match_type_label(row.match_type) for row in rows if row.match_type
        )
        return AdsKeywordMatchContextReadContract(
            status="ready",
            title="Google Ads: kontekst dopasowań słów kluczowych",
            summary=(
                f"WILQ ma kontekst {len(rows)} istniejących słów kluczowych "
                "z typami dopasowania: "
                f"{', '.join(match_type_labels) if match_type_labels else 'brak wierszy'}."
            ),
            allowed_metrics=[
                "keyword_text",
                "keyword_match_type",
                "criterion_status",
                "keyword_negative",
                "campaign",
                "ad_group",
            ],
            missing_read_contracts=[],
            operator_review_gates=["human_intent_review"],
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(evidence_id for row in rows for evidence_id in row.evidence_ids)
            or _refresh_or_connector_evidence_ids(latest_refresh),
            context_rows=rows,
            next_step=(
                "Użyj tego jako kontekstu review: sprawdź, które istniejące "
                "słowa kluczowe i typy dopasowań mogły wywołać wyszukiwane hasło. Nie traktuj "
                "tego jako zgody na dodanie wykluczających słów kluczowych."
            ),
        )

    return AdsKeywordMatchContextReadContract(
        status="blocked",
        title="Google Ads: brak kontekstu dopasowań słów kluczowych",
        summary="WILQ nie ma jeszcze odczytu istniejących słów kluczowych i typów dopasowania.",
        allowed_metrics=[],
        missing_read_contracts=["keyword_match_context_read"],
        blocked_claims=["keyword match context", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        context_rows=[],
        next_step=(
            "Uruchom odczyt kontekstu słów kluczowych w Google Ads. Nie zapisuj "
            "wykluczeń bez sprawdzenia, które istniejące słowa i typy dopasowania "
            "mogły wywołać wyszukiwane hasło."
        ),
    )


def _keyword_match_context_rows(
    metric_facts: list[MetricFact],
) -> list[AdsKeywordMatchContextRow]:
    grouped_facts: dict[
        tuple[str, str | None, str | None, str | None],
        list[MetricFact],
    ] = {}
    seen_metric_keys: set[tuple[str, str | None, str | None, str | None, str]] = set()
    for fact in metric_facts:
        if fact.name not in {
            "keyword_match_context_available",
            "keyword_match_type",
            "keyword_match_context_negative",
        }:
            continue
        keyword_text = fact.dimensions.get("keyword_text")
        if not keyword_text:
            continue
        campaign_id = fact.dimensions.get("campaign_id")
        ad_group_id = fact.dimensions.get("ad_group_id")
        criterion_id = fact.dimensions.get("criterion_id")
        row_key = (keyword_text, campaign_id, ad_group_id, criterion_id)
        metric_key = (*row_key, fact.name)
        if metric_key in seen_metric_keys:
            continue
        seen_metric_keys.add(metric_key)
        grouped_facts.setdefault(row_key, []).append(fact)

    rows = [
        _keyword_match_context_row(keyword_text, campaign_id, ad_group_id, facts)
        for (
            keyword_text,
            campaign_id,
            ad_group_id,
            _criterion_id,
        ), facts in grouped_facts.items()
    ]
    return sorted(rows, key=_keyword_match_context_row_sort_key)


def _keyword_match_context_row(
    keyword_text: str,
    campaign_id: str | None,
    ad_group_id: str | None,
    facts: list[MetricFact],
) -> AdsKeywordMatchContextRow:
    facts_by_name = {fact.name: fact for fact in facts}
    first_dimensions = facts[0].dimensions if facts else {}
    negative_value = _int_metric_value(facts_by_name.get("keyword_match_context_negative"))
    match_type_fact = facts_by_name.get("keyword_match_type")
    match_type = match_type_fact.value if match_type_fact is not None else None
    return AdsKeywordMatchContextRow(
        keyword_text=keyword_text,
        match_type=str(match_type or first_dimensions.get("keyword_match_type") or "UNKNOWN"),
        criterion_id=first_dimensions.get("criterion_id"),
        criterion_status=first_dimensions.get("criterion_status"),
        negative=bool(negative_value) if negative_value is not None else None,
        campaign_id=campaign_id,
        campaign_name=first_dimensions.get("campaign_name"),
        ad_group_id=ad_group_id,
        ad_group_name=first_dimensions.get("ad_group_name"),
        evidence_ids=_unique(fact.evidence_id for fact in facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        blocked_claims=[
            "dodanie wykluczających słów kluczowych",
            "marnowanie budżetu na zapytaniach",
            "zmarnowany budżet",
        ],
    )


def _keyword_match_context_row_sort_key(
    row: AdsKeywordMatchContextRow,
) -> tuple[str, str, str]:
    return (
        row.campaign_name or row.campaign_id or "",
        row.ad_group_name or "",
        row.keyword_text,
    )
