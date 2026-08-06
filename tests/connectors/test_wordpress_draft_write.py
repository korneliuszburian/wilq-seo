from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest

from wilq.connectors.wordpress.client import (
    WordPressDraftReadError,
    WordPressDraftWriteError,
    _normalize_acf_for_create,
    create_wordpress_acf_draft,
    create_wordpress_draft_post,
    read_wordpress_draft_post,
)
from wilq.content.handoff.wordpress_execution import ContentWordPressDraftPayload


def _payload(**overrides: object) -> ContentWordPressDraftPayload:
    payload = ContentWordPressDraftPayload(
        title="Testowy szkic",
        content_markdown="# Testowy szkic\n\nTreść do sprawdzenia.",
        final_canonical_url="https://www.ekologus.pl/testowy-szkic/",
        evidence_ids=["ev_test_wordpress_draft"],
    )
    if not overrides:
        return payload
    return payload.model_copy(update=overrides)


def _wordpress_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://ekologus.dev.proudsite.pl/")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")


def test_create_wordpress_draft_post_posts_draft_only_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = request.read().decode()
        assert request.method == "POST"
        assert str(request.url) == (
            "https://ekologus.dev.proudsite.pl/wp-json/wp/v2/posts?_fields=id%2Cstatus%2Clink"
        )
        assert '"status":"draft"' in body
        assert '"title":"Testowy szkic"' in body
        return httpx.Response(201, json={"id": 321, "status": "draft"})

    client = httpx.Client(transport=httpx.MockTransport(handler))

    post_id = create_wordpress_draft_post(_payload(), http_client=client)

    assert post_id == "321"
    assert len(requests) == 1


def test_create_wordpress_draft_post_blocks_non_draft_vendor_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(201, json={"id": 321, "status": "publish"})
        )
    )

    with pytest.raises(WordPressDraftWriteError) as exc_info:
        create_wordpress_draft_post(_payload(), http_client=client)

    assert exc_info.value.public_message == (
        "WordPress nie potwierdził, że utworzony wpis jest szkicem."
    )


def test_create_wordpress_draft_post_keeps_only_safe_rest_error_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                400,
                json={
                    "code": "rest_invalid_param",
                    "message": "Nie ujawniaj treści szkicu ani tokenu secret-value.",
                    "data": {"params": {"acf": "Niedozwolone"}},
                },
            )
        )
    )

    with pytest.raises(WordPressDraftWriteError) as exc_info:
        create_wordpress_draft_post(_payload(), http_client=client)

    assert exc_info.value.public_message == (
        "WordPress odrzucił utworzenie szkicu HTTP 400. "
        "(rest_invalid_param; pola: acf)"
    )
    assert "secret-value" not in exc_info.value.public_message


def test_acf_create_normalizes_only_empty_values_rejected_by_rest_schema() -> None:
    schema = {
        "type": "object",
        "properties": {
            "flexible-home": {
                "type": ["array", "null"],
                "items": {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {
                                "acf_fc_layout": {"type": "string", "pattern": "^hero$"},
                                "img": {"type": ["integer", "null"]},
                                "content": {"type": ["string", "null"]},
                                "background_type": {
                                    "type": ["string", "null"],
                                    "enum": ["gradient", "img"],
                                },
                            },
                        }
                    ]
                },
            }
        },
    }

    normalized = _normalize_acf_for_create(
        {
            "flexible-home": [
                {
                    "acf_fc_layout": "hero",
                    "img": "",
                    "content": "",
                    "background_type": "",
                },
            ]
        },
        schema,
    )

    assert normalized == {
        "flexible-home": [
            {
                "acf_fc_layout": "hero",
                "img": None,
                "content": "",
            },
        ]
    }


def test_create_wordpress_acf_draft_uses_live_schema_before_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)
    requests: list[httpx.Request] = []
    schema = {
        "type": "object",
        "properties": {
            "flexible-home": {
                "type": ["array", "null"],
                "items": {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {
                                "acf_fc_layout": {"type": "string", "pattern": "^hero$"},
                                "img": {"type": ["integer", "null"]},
                            },
                        }
                    ]
                },
            }
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "OPTIONS":
            return httpx.Response(
                200,
                json={"endpoints": [{"methods": ["POST"], "args": {"acf": schema}}]},
            )
        body = json.loads(request.content)
        assert request.method == "POST"
        assert body["status"] == "draft"
        assert body["acf"]["flexible-home"][0]["img"] is None
        return httpx.Response(201, json={"id": 322, "status": "draft"})

    draft_id = create_wordpress_acf_draft(
        SimpleNamespace(
            connector="wordpress_ekologus",
            endpoint="uslugi",
            post_status="draft",
            create_only=True,
            publish_allowed=False,
            update_allowed=False,
            delete_allowed=False,
            title="Test ACF",
            acf={"flexible-home": [{"acf_fc_layout": "hero", "img": ""}]},
        ),
        action_apply_authorized=True,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert draft_id == "322"
    assert [request.method for request in requests] == ["OPTIONS", "POST"]


def test_create_wordpress_draft_post_blocks_publish_or_destructive_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(201, json={"id": 321, "status": "draft"})
        )
    )

    with pytest.raises(WordPressDraftWriteError) as exc_info:
        create_wordpress_draft_post(
            _payload(publish_allowed=True),
            http_client=client,
        )

    assert exc_info.value.public_message == (
        "Adapter blokuje publikację i destrukcyjne aktualizacje."
    )


def test_create_wordpress_draft_post_blocks_public_or_arbitrary_host_before_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://www.ekologus.pl/")
    requests: list[httpx.Request] = []
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: requests.append(request) or httpx.Response(201)
        )
    )

    with pytest.raises(WordPressDraftWriteError) as exc_info:
        create_wordpress_draft_post(_payload(), http_client=client)

    assert "zatwierdzonym hoście dev" in exc_info.value.public_message
    assert requests == []


def test_read_wordpress_service_draft_uses_service_rest_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.method == "GET"
        assert request.url.path == "/wp-json/wp/v2/uslugi/1935"
        return httpx.Response(
            200,
            json={
                "id": 1935,
                "status": "draft",
                "title": {"rendered": "Doradztwo ekologiczne"},
                "link": "https://ekologus.dev.proudsite.pl/oferta/doradztwo/",
                "modified_gmt": "2026-08-06T12:00:00",
                "content": {"rendered": ""},
                "acf": {"flexible-home": []},
            },
        )

    readback = read_wordpress_draft_post(
        "1935",
        endpoint="uslugi",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert readback.endpoint == "uslugi"
    assert readback.post_id == "1935"
    assert readback.status == "draft"
    assert len(requests) == 1


def test_read_wordpress_draft_rejects_unknown_rest_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)

    with pytest.raises(WordPressDraftReadError) as exc_info:
        read_wordpress_draft_post("1935", endpoint="arbitrary")

    assert exc_info.value.public_message == "Nieobsługiwany typ treści WordPress."
