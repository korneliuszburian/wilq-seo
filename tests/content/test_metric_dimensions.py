from wilq.content.canonical.metric_dimensions import (
    dimensions_with_metric_identity,
    metric_dimensions_match_landing,
)


def test_ga4_path_and_host_form_exact_landing_identity() -> None:
    dimensions = {
        "landing_page": "/oferta/doradztwo/",
        "host_name": "www.ekologus.pl",
    }

    enriched = dimensions_with_metric_identity(dimensions)

    assert enriched["_wilq_landing_identity"] == (
        "https://www.ekologus.pl/oferta/doradztwo"
    )
    assert metric_dimensions_match_landing(
        dimensions,
        "https://www.ekologus.pl/oferta/doradztwo/",
    )
    assert not metric_dimensions_match_landing(
        {**dimensions, "host_name": "other.example"},
        "https://www.ekologus.pl/oferta/doradztwo/",
    )
