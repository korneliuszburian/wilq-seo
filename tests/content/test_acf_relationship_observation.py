from __future__ import annotations

import httpx

from wilq.connectors.wordpress.acf_relationship_observation import (
    observe_wordpress_acf_panel_labels,
)


def test_public_panel_observation_requires_exact_labels_for_every_acf_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://dev.example.test/"
        return httpx.Response(
            200,
            text=(
                '<button data-panel-target="sub-mega-menu-panel-374">'
                "EKOdokumentacje</button>"
                '<button data-panel-target="sub-mega-menu-panel-352">'
                "Sprzedaż sorbentów</button>"
            ),
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        observed = observe_wordpress_acf_panel_labels(
            "https://dev.example.test/", [374, 352], http_client=client
        )
        missing = observe_wordpress_acf_panel_labels(
            "https://dev.example.test/", [374, 999], http_client=client
        )

    assert observed.status == "available"
    assert observed.labels_by_id == {374: "EKOdokumentacje", 352: "Sprzedaż sorbentów"}
    assert missing.status == "unavailable"
    assert missing.labels_by_id == {}
