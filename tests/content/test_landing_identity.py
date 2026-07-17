from __future__ import annotations

from wilq.content.canonical.landing_identity import (
    LandingPageCandidate,
    build_landing_page_identity,
    landing_page_metric_legacy_base_urls,
    landing_page_metric_lookup_path,
    landing_page_metric_lookup_urls,
    match_landing_page,
    resolve_landing_page_candidates,
)

EXPECTED = "https://www.ekologus.pl/oferta/doradztwo/?service=outsourcing"


def test_landing_identity_distinguishes_safe_match_tiers_and_functional_queries() -> None:
    exact = match_landing_page(
        EXPECTED,
        LandingPageCandidate(candidate_id="exact", url=EXPECTED),
    )
    tracking = match_landing_page(
        EXPECTED,
        LandingPageCandidate(
            candidate_id="tracking",
            url=f"{EXPECTED}&utm_source=ads&gclid=secret-click-id",
        ),
    )
    host_alias = match_landing_page(
        EXPECTED,
        LandingPageCandidate(
            candidate_id="host-alias",
            url="https://ekologus.pl/oferta/doradztwo?service=outsourcing",
        ),
    )
    path_only = match_landing_page(
        EXPECTED,
        LandingPageCandidate(
            candidate_id="ga4-path",
            url="/oferta/doradztwo/?service=outsourcing&utm_medium=cpc",
        ),
    )
    functional_query = match_landing_page(
        EXPECTED,
        LandingPageCandidate(
            candidate_id="different-service",
            url="https://www.ekologus.pl/oferta/doradztwo?service=audyt",
        ),
    )

    assert (exact.tier, exact.matched, exact.review_required) == ("exact", True, False)
    assert tracking.tier == "tracking_only"
    assert tracking.identity.removed_tracking_parameters == ["gclid", "utm_source"]
    assert host_alias.tier == "host_alias"
    assert (path_only.tier, path_only.matched, path_only.review_required) == (
        "path_only",
        False,
        True,
    )
    assert (
        functional_query.tier,
        functional_query.matched,
        functional_query.review_required,
    ) == ("functional_query", False, True)


def test_landing_resolution_exposes_ambiguity_and_missing_instead_of_guessing() -> None:
    ambiguous = resolve_landing_page_candidates(
        EXPECTED,
        [
            LandingPageCandidate(candidate_id="gsc", url=EXPECTED),
            LandingPageCandidate(
                candidate_id="ga4",
                url="/oferta/doradztwo?service=outsourcing",
            ),
        ],
    )
    missing = resolve_landing_page_candidates(EXPECTED, [])
    missing_candidate = resolve_landing_page_candidates(
        EXPECTED,
        [LandingPageCandidate(candidate_id="ga4-missing", url="(not set)")],
    )
    no_match = resolve_landing_page_candidates(
        EXPECTED,
        [
            LandingPageCandidate(
                candidate_id="foreign-page",
                url="https://www.ekologus.pl/kpo/",
            )
        ],
    )

    assert ambiguous.matched_candidate_ids == ["gsc"]
    assert ambiguous.tier == "exact"
    assert ambiguous.selected_candidate_id == "gsc"
    assert not ambiguous.review_required

    duplicate_exact = resolve_landing_page_candidates(
        EXPECTED,
        [
            LandingPageCandidate(candidate_id="gsc-a", url=EXPECTED),
            LandingPageCandidate(candidate_id="gsc-b", url=EXPECTED),
        ],
    )
    assert duplicate_exact.tier == "ambiguous"
    assert duplicate_exact.selected_candidate_id is None
    assert duplicate_exact.matched_candidate_ids == ["gsc-a", "gsc-b"]
    assert duplicate_exact.review_required
    assert missing.tier == "missing"
    assert missing.review_required
    assert missing_candidate.tier == "missing"
    assert no_match.tier == "no_match"
    assert not no_match.review_required


def test_landing_identity_preserves_functional_query_and_discards_only_tracking() -> None:
    identity = build_landing_page_identity(
        "https://EKOLOGUS.PL/oferta/?z=2&utm_campaign=summer&a=1#contact"
    )

    assert identity.canonical_url == "https://www.ekologus.pl/oferta?z=2&a=1"
    assert identity.functional_query == "z=2&a=1"
    assert identity.removed_tracking_parameters == ["utm_campaign"]
    assert identity.host_alias_applied
    assert landing_page_metric_lookup_urls(identity.canonical_url) == [
        "https://www.ekologus.pl/oferta?z=2&a=1",
    ]
    assert landing_page_metric_lookup_path(identity.canonical_url) == "/oferta?z=2&a=1"
    assert landing_page_metric_legacy_base_urls(identity.canonical_url) == [
        "https://ekologus.pl/oferta",
        "https://ekologus.pl:443/oferta",
        "https://www.ekologus.pl/oferta",
        "https://www.ekologus.pl:443/oferta",
    ]


def test_landing_identity_rejects_malformed_or_different_origin_and_keeps_pair_order() -> None:
    malformed = build_landing_page_identity("https://[broken/path")
    http = match_landing_page(
        EXPECTED,
        LandingPageCandidate(
            candidate_id="http",
            url="http://www.ekologus.pl/oferta/doradztwo?service=outsourcing",
        ),
    )
    other_port = match_landing_page(
        EXPECTED,
        LandingPageCandidate(
            candidate_id="other-port",
            url="https://www.ekologus.pl:8443/oferta/doradztwo?service=outsourcing",
        ),
    )
    reversed_pairs = match_landing_page(
        "https://www.ekologus.pl/form/?step=1&step=2",
        LandingPageCandidate(
            candidate_id="reversed-pairs",
            url="https://www.ekologus.pl/form/?step=2&step=1",
        ),
    )

    assert malformed.status == "invalid"
    assert (http.tier, http.matched) == ("no_match", False)
    assert (other_port.tier, other_port.matched) == ("no_match", False)
    assert (reversed_pairs.tier, reversed_pairs.matched) == (
        "functional_query",
        False,
    )
