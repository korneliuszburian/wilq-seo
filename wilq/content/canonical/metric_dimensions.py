from __future__ import annotations

from wilq.content.canonical.landing_identity import (
    LandingPageCandidate,
    build_landing_page_identity,
    match_landing_page,
)

METRIC_LANDING_URL_DIMENSIONS = frozenset(
    {
        "content_url",
        "final_url",
        "landing_page",
        "landing_page_plus_query_string",
        "page",
        "page_location",
    }
)
LANDING_IDENTITY_DIMENSION = "_wilq_landing_identity"


def dimensions_with_metric_identity(dimensions: dict[str, str]) -> dict[str, str]:
    cleaned = {
        str(key): str(value)
        for key, value in dimensions.items()
        if str(key).strip()
        and str(value).strip()
        and not str(key).startswith("_wilq_")
    }
    landing_dimensions = [
        build_landing_page_identity(value)
        for key, value in cleaned.items()
        if key in METRIC_LANDING_URL_DIMENSIONS
    ]
    if not landing_dimensions or any(
        identity.status != "resolved" or not identity.canonical_url
        for identity in landing_dimensions
    ):
        return cleaned
    landing_identities = {
        str(identity.canonical_url) for identity in landing_dimensions
    }
    if len(landing_identities) != 1:
        return cleaned

    landing_identity = next(iter(landing_identities))
    return {
        **cleaned,
        LANDING_IDENTITY_DIMENSION: landing_identity,
    }


def metric_dimensions_landing_identity(dimensions: dict[str, str]) -> str | None:
    return dimensions_with_metric_identity(dimensions).get(LANDING_IDENTITY_DIMENSION)


def metric_dimensions_match_landing(
    dimensions: dict[str, str],
    expected_url: str | None,
) -> bool:
    matches = [
        match_landing_page(
            expected_url,
            LandingPageCandidate(candidate_id=key, url=dimensions.get(key)),
        )
        for key in METRIC_LANDING_URL_DIMENSIONS
        if dimensions.get(key)
    ]
    return bool(expected_url) and bool(matches) and all(match.matched for match in matches)
