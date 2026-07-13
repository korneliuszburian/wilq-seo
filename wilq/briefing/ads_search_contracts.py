from __future__ import annotations

from collections.abc import Callable

from wilq.schemas import (
    AdsKeywordMatchContextReadContract,
    AdsKeywordPlannerReadContract,
    AdsSearchTermNgramReadContract,
    AdsSearchTermReviewSummaryContract,
    AdsSearchTermSafetyReadContract,
    AdsSearchTermsReadContract,
    ConnectorRefreshRun,
    MetricFact,
)


def build_search_term_read_contracts(
    trusted_metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
    currency_code: str | None,
    *,
    search_terms: Callable[
        [list[MetricFact], ConnectorRefreshRun | None, str | None],
        AdsSearchTermsReadContract,
    ],
    search_term_safety: Callable[
        [list[MetricFact], ConnectorRefreshRun | None, str | None],
        AdsSearchTermSafetyReadContract,
    ],
    keyword_match_context: Callable[
        [list[MetricFact], ConnectorRefreshRun | None],
        AdsKeywordMatchContextReadContract,
    ],
    keyword_planner: Callable[
        [list[MetricFact], ConnectorRefreshRun | None], AdsKeywordPlannerReadContract
    ],
) -> tuple[
    AdsSearchTermsReadContract,
    AdsSearchTermSafetyReadContract,
    AdsKeywordMatchContextReadContract,
    AdsKeywordPlannerReadContract,
]:
    return (
        search_terms(trusted_metric_facts, latest_refresh, currency_code),
        search_term_safety(trusted_metric_facts, latest_refresh, currency_code),
        keyword_match_context(trusted_metric_facts, latest_refresh),
        keyword_planner(trusted_metric_facts, latest_refresh),
    )


def build_search_term_review_contracts(
    search_terms_read_contract: AdsSearchTermsReadContract,
    latest_refresh: ConnectorRefreshRun | None,
    currency_code: str | None,
    *,
    review_summary: Callable[
        [AdsSearchTermsReadContract, ConnectorRefreshRun | None, str | None],
        AdsSearchTermReviewSummaryContract,
    ],
    ngram: Callable[
        [AdsSearchTermsReadContract, ConnectorRefreshRun | None, str | None],
        AdsSearchTermNgramReadContract,
    ],
) -> tuple[AdsSearchTermReviewSummaryContract, AdsSearchTermNgramReadContract]:
    return (
        review_summary(search_terms_read_contract, latest_refresh, currency_code),
        ngram(search_terms_read_contract, latest_refresh, currency_code),
    )
