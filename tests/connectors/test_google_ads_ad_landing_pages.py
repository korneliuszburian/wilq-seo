import pytest

from wilq.connectors.google_ads.ad_landing_pages import (
    ADS_LANDING_ACTUAL_CLICKED,
    ADS_LANDING_IDENTITY,
    ADS_LANDING_MAPPING_STATUS,
    ADS_LANDING_RESOLVED,
    search_term_landing_dimensions,
    strict_search_stream_rows,
)


def test_clicked_search_term_landing_is_redacted_and_identity_bound() -> None:
    dimensions = search_term_landing_dimensions(
        _row(
            "https://ekologus.pl/oferta/?service=outsourcing&utm_source=ads"
        )
    )

    assert dimensions[ADS_LANDING_MAPPING_STATUS] == ADS_LANDING_RESOLVED
    assert dimensions[ADS_LANDING_ACTUAL_CLICKED] == "true"
    assert len(dimensions[ADS_LANDING_IDENTITY]) == 64
    assert dimensions["tracking_parameters_removed"] == "true"
    assert dimensions["functional_query_present"] == "true"
    assert "outsourcing" not in str(dimensions)


@pytest.mark.parametrize(
    "query_name",
    ["access_token", "apiKey", "customer_email", "X-Amz-Signature", "session"],
)
def test_sensitive_clicked_url_names_never_persist(query_name: str) -> None:
    dimensions = search_term_landing_dimensions(
        _row(f"https://example.test/?{query_name}=secret")
    )

    assert dimensions == {ADS_LANDING_MAPPING_STATUS: "sensitive"}
    assert "secret" not in str(dimensions)


@pytest.mark.parametrize(
    ("row", "status"),
    [
        ({"expandedLandingPageView": {}}, "missing"),
        ({"expandedLandingPageView": {"expandedFinalUrl": "not a url"}}, "invalid"),
        ({"expandedLandingPageView": "malformed"}, "missing"),
    ],
)
def test_missing_or_invalid_clicked_url_stays_unmapped(
    row: dict[str, object], status: str
) -> None:
    assert search_term_landing_dimensions(row) == {
        ADS_LANDING_MAPPING_STATUS: status
    }


def test_malformed_search_stream_discards_all_rows() -> None:
    rows, valid = strict_search_stream_rows(
        [{"results": [_row("https://ekologus.pl/bdo/")]}, {"results": "bad"}]
    )

    assert rows == []
    assert valid is False


def _row(url: str) -> dict[str, object]:
    return {"expandedLandingPageView": {"expandedFinalUrl": url}}
