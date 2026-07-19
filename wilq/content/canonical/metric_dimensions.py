from __future__ import annotations

from urllib.parse import urlsplit

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
GA4_HOST_DIMENSION = "host_name"


def _metric_landing_candidates(dimensions: dict[str, str]) -> list[LandingPageCandidate]:
    landing_page = dimensions.get("landing_page")
    host_name = dimensions.get(GA4_HOST_DIMENSION)
    candidates = [
        LandingPageCandidate(candidate_id=key, url=dimensions.get(key))
        for key in METRIC_LANDING_URL_DIMENSIONS
        if dimensions.get(key)
        and not (
            key == "landing_page"
            and landing_page
            and urlsplit(landing_page).path.startswith("/")
            and not urlsplit(landing_page).netloc
        )
    ]
    if landing_page and host_name:
        parsed = urlsplit(landing_page)
        if not parsed.netloc and parsed.path.startswith("/"):
            candidates.append(
                LandingPageCandidate(
                    candidate_id="landing_page_with_host_name",
                    url=f"https://{host_name}{landing_page}",
                )
            )
    return candidates


def dimensions_with_metric_identity(dimensions: dict[str, str]) -> dict[str, str]:
    cleaned = {
        str(key): str(value)
        for key, value in dimensions.items()
        if str(key).strip()
        and str(value).strip()
        and not str(key).startswith("_wilq_")
    }
    landing_dimensions = [
        build_landing_page_identity(candidate.url)
        for candidate in _metric_landing_candidates(cleaned)
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
    *,
    allow_relative_path: bool = False,
) -> bool:
    candidates = _metric_landing_candidates(dimensions)
    if allow_relative_path and expected_url:
        expected = urlsplit(expected_url)
        for key in ("landing_page", "landing_page_plus_query_string"):
            value = dimensions.get(key)
            parsed = urlsplit(value or "")
            if value and parsed.path.startswith("/") and not parsed.netloc:
                candidates.append(
                    LandingPageCandidate(
                        candidate_id=f"{key}_with_expected_host",
                        url=f"{expected.scheme or 'https'}://{expected.netloc}{value}",
                    )
                )
    matches = [
        match_landing_page(expected_url, candidate)
        for candidate in candidates
    ]
    return bool(expected_url) and bool(matches) and all(match.matched for match in matches)
