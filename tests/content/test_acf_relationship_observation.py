from __future__ import annotations

from contextlib import contextmanager

import httpx

from wilq.connectors.wordpress.acf_relationship_observation import (
    observe_wordpress_acf_panel_labels,
)


def test_public_panel_observation_requires_exact_labels_for_every_acf_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://ekologus.dev.proudsite.pl/"
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
            "https://ekologus.dev.proudsite.pl/", [374, 352], http_client=client
        )
        missing = observe_wordpress_acf_panel_labels(
            "https://ekologus.dev.proudsite.pl/", [374, 999], http_client=client
        )

    assert observed.status == "available"
    assert observed.labels_by_id == {374: "EKOdokumentacje", 352: "Sprzedaż sorbentów"}
    assert missing.status == "unavailable"
    assert missing.labels_by_id == {}


def test_malformed_panel_suffix_fails_closed_without_value_error() -> None:
    for suffix in ("²", "9" * 4301):
        def handler(request: httpx.Request, suffix: str = suffix) -> httpx.Response:
            assert request.url == "https://ekologus.dev.proudsite.pl/"
            return httpx.Response(
                200,
                text=f'<button data-panel-target="sub-mega-menu-panel-{suffix}">x</button>',
            )

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            observed = observe_wordpress_acf_panel_labels(
                "https://ekologus.dev.proudsite.pl/", [1], http_client=client
            )

        assert observed.status == "unavailable" and observed.labels_by_id == {}


def test_panel_label_observation_handles_void_html_elements() -> None:
    for void_element in ("<br>", "<br/>"):
        def handler(request: httpx.Request, void_element: str = void_element) -> httpx.Response:
            assert request.url == "https://ekologus.dev.proudsite.pl/"
            return httpx.Response(
                200,
                text=(
                    '<button data-panel-target="sub-mega-menu-panel-374">'
                    f"EKO{void_element}dokumentacje</button>"
                ),
            )

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            observed = observe_wordpress_acf_panel_labels(
                "https://ekologus.dev.proudsite.pl/", [374], http_client=client
            )

        assert observed.status == "available" and observed.labels_by_id == {374: "EKOdokumentacje"}


def test_panel_label_observation_fails_closed_for_malformed_html_and_transport_guards() -> None:
    cases = [
        httpx.Response(
            200,
            content=b"\xff\xfe",
            headers={"content-type": "text/html; charset=utf-8"},
        ),
        httpx.Response(200, text="x" * 1_000_001),
        httpx.Response(503),
    ]
    for response in cases:
        def handler(_request: httpx.Request, response: httpx.Response = response) -> httpx.Response:
            return response

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            observed = observe_wordpress_acf_panel_labels(
                "https://ekologus.dev.proudsite.pl/", [374], http_client=client
            )
        assert observed.status == "unavailable" and observed.labels_by_id == {}

    class ForeignOriginClient:
        @contextmanager
        def stream(self, *_args, **_kwargs):
            yield type(
                "ForeignResponse",
                (),
                {
                    "url": "https://attacker.example/",
                    "raise_for_status": lambda _self: None,
                    "iter_text": lambda _self: iter(
                        ['<button data-panel-target="sub-mega-menu-panel-374">x</button>']
                    ),
                },
            )()

    observed = observe_wordpress_acf_panel_labels(
        "https://ekologus.dev.proudsite.pl/", [374], http_client=ForeignOriginClient()
    )
    assert observed.status == "unavailable" and observed.labels_by_id == {}


def test_panel_label_observation_fails_closed_for_mismatched_end_tag() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://ekologus.dev.proudsite.pl/"
        return httpx.Response(
            200,
            text=(
                '<div data-panel-target="sub-mega-menu-panel-374">'
                "<span>Wewnątrz</div>Na zewnątrz</div>"
            ),
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        observed = observe_wordpress_acf_panel_labels(
            "https://ekologus.dev.proudsite.pl/", [374], http_client=client
        )

    assert observed.status == "unavailable"
    assert observed.labels_by_id == {}


def test_panel_label_observation_enforces_the_ekologus_dev_host_allowlist() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("foreign origin was requested")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        observed = observe_wordpress_acf_panel_labels(
            "https://dev.example.test/", [374], http_client=client
        )

    assert observed.status == "unavailable"
    assert observed.labels_by_id == {}


def test_panel_label_observation_rejects_malformed_source_url_without_request() -> None:
    observed = observe_wordpress_acf_panel_labels("https://[", [374])

    assert observed.status == "unavailable"
    assert observed.labels_by_id == {}
