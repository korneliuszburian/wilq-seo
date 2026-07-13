from __future__ import annotations

from collections.abc import Callable

from wilq.schemas import (
    AdsCustomSegmentsReadContract,
    AdsKeywordMatchContextReadContract,
    AdsKeywordPlannerReadContract,
    AdsNegativeKeywordsReadContract,
    AdsSearchTermSafetyReadContract,
    AdsSearchTermsReadContract,
)


def build_candidate_read_contracts(
    search_terms_read_contract: AdsSearchTermsReadContract,
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract,
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract,
    keyword_planner_read_contract: AdsKeywordPlannerReadContract,
    action_ids: list[str],
    *,
    custom_segments: Callable[
        [AdsSearchTermsReadContract, AdsKeywordPlannerReadContract, list[str]],
        AdsCustomSegmentsReadContract,
    ],
    negative_keywords: Callable[
        [
            AdsSearchTermsReadContract,
            AdsSearchTermSafetyReadContract,
            AdsKeywordMatchContextReadContract,
            list[str],
        ],
        AdsNegativeKeywordsReadContract,
    ],
) -> tuple[AdsCustomSegmentsReadContract, AdsNegativeKeywordsReadContract]:
    return (
        custom_segments(search_terms_read_contract, keyword_planner_read_contract, action_ids),
        negative_keywords(
            search_terms_read_contract,
            search_term_safety_read_contract,
            keyword_match_context_read_contract,
            action_ids,
        ),
    )
