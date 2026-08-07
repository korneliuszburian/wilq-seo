from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from wilq.connectors.wordpress import client as wordpress_client
from wilq.connectors.wordpress.client import WordPressDraftPostReadback
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftExecutionBoundary,
    ContentWordPressDraftExecutionResult,
    ContentWordPressDraftPayload,
)
from wilq.content.workflow import dev_draft_execution, stage_activation
from wilq.content.workflow.dev_draft_action import CONTENT_DEV_DRAFT_ACTION_TYPE


def _wordpress_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://ekologus.dev.proudsite.pl/")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")


def _action() -> SimpleNamespace:
    return SimpleNamespace(
        connector="wordpress_ekologus",
        payload={"action_type": CONTENT_DEV_DRAFT_ACTION_TYPE},
    )


def _post_payload() -> SimpleNamespace:
    return SimpleNamespace(
        connector="wordpress_ekologus",
        endpoint="posts",
        authoring_mode="wordpress_post_content",
        post_status="draft",
        create_only=True,
        publish_allowed=False,
        update_allowed=False,
        delete_allowed=False,
        destructive_update_allowed=False,
        title="Testowy szkic",
        content_html="<p>Oczekiwana treść.</p>",
        acf=None,
    )


def test_dev_draft_execution_marks_matching_content_readback_as_verified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST":
            return httpx.Response(201, json={"id": 417, "status": "draft"})
        return httpx.Response(
            200,
            json={
                "id": 417,
                "status": "draft",
                "title": {"raw": "Testowy szkic"},
                "content": {"raw": "<p>Oczekiwana treść.</p>"},
                "acf": {},
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(dev_draft_execution, "_dev_draft_writes_enabled", lambda: True)
    monkeypatch.setattr(
        dev_draft_execution,
        "build_content_dev_draft_write_payload",
        lambda _action: _post_payload(),
    )
    monkeypatch.setattr(
        dev_draft_execution,
        "create_wordpress_draft_post",
        lambda payload, *, connector_id: wordpress_client.create_wordpress_draft_post(
            payload,
            connector_id=connector_id,
            http_client=http_client,
        ),
    )

    result, errors = dev_draft_execution.execute_content_target_draft_action(_action())

    assert errors == []
    assert result is not None
    assert result["created_draft_id"] == "417"
    assert result["verification_status"] == "verified"
    assert [request.method for request in requests] == ["POST", "GET"]


def test_dev_draft_execution_blocks_mismatched_content_after_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST":
            return httpx.Response(201, json={"id": 417, "status": "draft"})
        return httpx.Response(
            200,
            json={
                "id": 417,
                "status": "draft",
                "title": {"raw": "Testowy szkic"},
                "content": {"raw": "<p>Inna treść.</p>"},
                "acf": {},
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(dev_draft_execution, "_dev_draft_writes_enabled", lambda: True)
    monkeypatch.setattr(
        dev_draft_execution,
        "build_content_dev_draft_write_payload",
        lambda _action: _post_payload(),
    )
    monkeypatch.setattr(
        dev_draft_execution,
        "create_wordpress_draft_post",
        lambda payload, *, connector_id: wordpress_client.create_wordpress_draft_post(
            payload,
            connector_id=connector_id,
            http_client=http_client,
        ),
    )

    result, errors = dev_draft_execution.execute_content_target_draft_action(_action())

    assert result is not None
    assert result["created_draft_id"] == "417"
    assert result["external_write_attempted"] is True
    assert result["verification_status"] == "blocked"
    assert result["verification_blocker_code"] == "wordpress_draft_content_mismatch"
    assert errors == [
        "Utworzono szkic WordPress, ale odczyt nie potwierdził zgodności zapisanej treści."
    ]
    assert [request.method for request in requests] == ["POST", "GET"]


def _created_execution(content_html: str) -> ContentWordPressDraftExecutionResult:
    return ContentWordPressDraftExecutionResult(
        status="created",
        mode="live",
        boundary=ContentWordPressDraftExecutionBoundary(
            live_write_enabled=True,
            live_adapter_configured=True,
        ),
        payload=ContentWordPressDraftPayload(
            title="Testowy szkic",
            content_markdown="Oczekiwana treść.",
            content_html=content_html,
            authoring_mode="the_content",
            final_canonical_url="https://www.ekologus.pl/testowy-szkic/",
        ),
        wordpress_post_id="417",
        external_write_attempted=True,
    )


def _readback(content_html: str) -> WordPressDraftPostReadback:
    return WordPressDraftPostReadback(
        post_id="417",
        endpoint="posts",
        status="draft",
        title="Testowy szkic",
        link="https://ekologus.dev.proudsite.pl/?p=417",
        modified_gmt="2026-08-07T12:00:00",
        content_summary="Oczekiwana treść.",
        content_word_count=2,
        acf_field_count=0,
        acf_field_names=[],
        content_digest=wordpress_client._wordpress_draft_value_digest(content_html),
        acf_digest=wordpress_client._wordpress_draft_value_digest({}),
    )


def test_stage_readback_surfaces_verified_matching_content_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_html = "<p>Oczekiwana treść.</p>"
    monkeypatch.setattr(
        stage_activation,
        "read_wordpress_draft_post",
        lambda _post_id: _readback(expected_html),
    )

    result = stage_activation.wordpress_draft_readback(_created_execution(expected_html))

    assert result is not None
    assert result.status == "available"
    assert result.verification_status == "verified"
    assert result.content_digest == wordpress_client._wordpress_draft_value_digest(
        expected_html
    )
    assert result.expected_content_digest == result.content_digest
    assert result.blockers == []


def test_stage_readback_blocks_content_digest_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        stage_activation,
        "read_wordpress_draft_post",
        lambda _post_id: _readback("<p>Inna treść.</p>"),
    )

    result = stage_activation.wordpress_draft_readback(
        _created_execution("<p>Oczekiwana treść.</p>")
    )

    assert result is not None
    assert result.status == "blocked"
    assert result.verification_status == "blocked"
    assert [blocker.code for blocker in result.blockers] == [
        "wordpress_draft_content_mismatch"
    ]
