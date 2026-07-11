from __future__ import annotations

import httpx
import pytest

from wilq.connectors.wordpress.client import (
    WordPressDraftWriteError,
    create_wordpress_draft_post,
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
