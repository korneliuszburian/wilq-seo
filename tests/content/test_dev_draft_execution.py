from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

import wilq.content.workflow.pipeline_steps.stage_activation as stage_activation
import wilq.content.workflow.target.dev_draft_execution as dev_draft_execution
from wilq.connectors.wordpress import client as wordpress_client
from wilq.connectors.wordpress.client import (
    WordPressDraftPostReadback,
    WordPressDraftWriteError,
)
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftExecutionBoundary,
    ContentWordPressDraftExecutionResult,
    ContentWordPressDraftPayload,
)
from wilq.content.workflow.documents.revision_binding import ContentDraftRevisionBinding
from wilq.content.workflow.target.dev_draft_action import CONTENT_DEV_DRAFT_ACTION_TYPE


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


def _binding() -> ContentDraftRevisionBinding:
    return ContentDraftRevisionBinding(
        work_item_id="content_work_item_test",
        handoff_id="wordpress_draft_handoff_content_work_item_test_revision_test",
        revision_id="revision_test",
        content_digest="a" * 64,
        draft_package_id="draft_package_test",
        draft_package_digest="b" * 64,
        planning_digest="c" * 64,
        approval_decision_id="decision_test",
        final_canonical_url="https://ekologus.pl/test/",
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
        lambda payload, *, connector_id, endpoint: wordpress_client.create_wordpress_draft_post(
            payload,
            connector_id=connector_id,
            endpoint=endpoint,
            http_client=http_client,
        ),
    )

    result, errors = dev_draft_execution.execute_content_target_draft_action(
        _action(), binding=_binding()
    )

    assert errors == []
    assert result is not None
    assert result["created_draft_id"] == "417"
    assert result["verification_status"] == "verified"
    assert result["execution_result"]["wordpress_post_id"] == "417"
    assert result["execution_result"]["revision_binding"]["revision_id"] == "revision_test"
    assert [request.method for request in requests] == ["POST", "GET"]
    assert all("/posts" in request.url.path for request in requests)


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
        lambda payload, *, connector_id, endpoint: wordpress_client.create_wordpress_draft_post(
            payload,
            connector_id=connector_id,
            endpoint=endpoint,
            http_client=http_client,
        ),
    )

    result, errors = dev_draft_execution.execute_content_target_draft_action(
        _action(), binding=_binding()
    )

    assert result is not None
    assert result["created_draft_id"] == "417"
    assert result["external_write_attempted"] is True
    assert result["verification_status"] == "blocked"
    assert result["execution_result"]["external_write_attempted"] is True
    assert result["verification_blocker_code"] == "wordpress_draft_content_mismatch"
    assert errors == [
        "Utworzono szkic WordPress, ale odczyt nie potwierdził zgodności zapisanej treści."
    ]
    assert [request.method for request in requests] == ["POST", "GET"]


def test_dev_draft_execution_uses_confirmed_pages_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)
    requests: list[httpx.Request] = []
    payload = _post_payload()
    payload.endpoint = "pages"

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
        lambda _action: payload,
    )
    monkeypatch.setattr(
        dev_draft_execution,
        "create_wordpress_draft_post",
        lambda value, *, connector_id, endpoint: wordpress_client.create_wordpress_draft_post(
            value,
            connector_id=connector_id,
            endpoint=endpoint,
            http_client=http_client,
        ),
    )

    result, errors = dev_draft_execution.execute_content_target_draft_action(
        _action(), binding=_binding()
    )

    assert errors == []
    assert result is not None
    assert result["endpoint"] == "pages"
    assert result["execution_result"]["endpoint"] == "pages"
    assert all("/pages" in request.url.path for request in requests)


def test_dev_draft_execution_blocks_mismatched_title_after_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(201, json={"id": 417, "status": "draft"})
        return httpx.Response(
            200,
            json={
                "id": 417,
                "status": "draft",
                "title": {"raw": "Inny tytuł"},
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
        lambda payload, *, connector_id, endpoint: wordpress_client.create_wordpress_draft_post(
            payload,
            connector_id=connector_id,
            endpoint=endpoint,
            http_client=http_client,
        ),
    )

    result, errors = dev_draft_execution.execute_content_target_draft_action(
        _action(), binding=_binding()
    )

    assert result is not None
    assert result["verification_status"] == "blocked"
    assert result["verification_blocker_code"] == "wordpress_draft_title_mismatch"
    assert result["external_write_attempted"] is True
    assert errors == ["Utworzono szkic WordPress, ale odczyt nie potwierdził tytułu."]


def test_dev_draft_execution_blocks_divergent_raw_title_after_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(201, json={"id": 417, "status": "draft"})
        return httpx.Response(
            200,
            json={
                "id": 417,
                "status": "draft",
                "title": {"raw": "Inny tytuł", "rendered": "Testowy szkic"},
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
        lambda payload, *, connector_id, endpoint: wordpress_client.create_wordpress_draft_post(
            payload,
            connector_id=connector_id,
            endpoint=endpoint,
            http_client=http_client,
        ),
    )

    result, errors = dev_draft_execution.execute_content_target_draft_action(
        _action(), binding=_binding()
    )

    assert result is not None
    assert result["verification_blocker_code"] == "wordpress_draft_title_mismatch"
    assert result["external_write_attempted"] is True
    assert errors == ["Utworzono szkic WordPress, ale odczyt nie potwierdził tytułu."]


def test_dev_draft_execution_blocks_empty_raw_title_after_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(201, json={"id": 417, "status": "draft"})
        return httpx.Response(
            200,
            json={
                "id": 417,
                "status": "draft",
                "title": {"raw": "", "rendered": "Testowy szkic"},
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
        lambda payload, *, connector_id, endpoint: wordpress_client.create_wordpress_draft_post(
            payload,
            connector_id=connector_id,
            endpoint=endpoint,
            http_client=http_client,
        ),
    )

    result, errors = dev_draft_execution.execute_content_target_draft_action(
        _action(), binding=_binding()
    )

    assert result is not None
    assert result["verification_blocker_code"] == "wordpress_draft_title_mismatch"
    assert errors == ["Utworzono szkic WordPress, ale odczyt nie potwierdził tytułu."]


def test_dev_draft_execution_blocks_readback_without_raw_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(201, json={"id": 417, "status": "draft"})
        return httpx.Response(
            200,
            json={
                "id": 417,
                "status": "draft",
                "title": {"rendered": "Testowy szkic"},
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
        lambda payload, *, connector_id, endpoint: wordpress_client.create_wordpress_draft_post(
            payload,
            connector_id=connector_id,
            endpoint=endpoint,
            http_client=http_client,
        ),
    )

    result, errors = dev_draft_execution.execute_content_target_draft_action(
        _action(), binding=_binding()
    )

    assert result is not None
    assert result["verification_blocker_code"] == "wordpress_draft_title_mismatch"
    assert result["external_write_attempted"] is True
    assert errors == ["Utworzono szkic WordPress, ale odczyt nie potwierdził tytułu."]


def test_dev_draft_execution_blocks_normalized_raw_title_difference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(201, json={"id": 417, "status": "draft"})
        return httpx.Response(
            200,
            json={
                "id": 417,
                "status": "draft",
                "title": {"raw": "Testowy   szkic", "rendered": "Testowy szkic"},
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
        lambda payload, *, connector_id, endpoint: wordpress_client.create_wordpress_draft_post(
            payload,
            connector_id=connector_id,
            endpoint=endpoint,
            http_client=http_client,
        ),
    )

    result, errors = dev_draft_execution.execute_content_target_draft_action(
        _action(), binding=_binding()
    )

    assert result is not None
    assert result["verification_blocker_code"] == "wordpress_draft_title_mismatch"
    assert errors == ["Utworzono szkic WordPress, ale odczyt nie potwierdził tytułu."]


def test_dev_draft_execution_accepts_presentation_filtered_rendered_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(201, json={"id": 417, "status": "draft"})
        return httpx.Response(
            200,
            json={
                "id": 417,
                "status": "draft",
                "title": {"raw": "Testowy szkic", "rendered": "Testowy – szkic"},
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
        lambda payload, *, connector_id, endpoint: wordpress_client.create_wordpress_draft_post(
            payload,
            connector_id=connector_id,
            endpoint=endpoint,
            http_client=http_client,
        ),
    )

    result, errors = dev_draft_execution.execute_content_target_draft_action(
        _action(), binding=_binding()
    )

    assert errors == []
    assert result is not None
    assert result["verification_status"] == "verified"


def test_dev_draft_execution_consumes_claim_after_undecodable_post_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wordpress_env(monkeypatch)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            201,
            content=b"not-json",
            headers={"content-type": "application/json"},
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
        lambda payload, *, connector_id, endpoint: wordpress_client.create_wordpress_draft_post(
            payload,
            connector_id=connector_id,
            endpoint=endpoint,
            http_client=http_client,
        ),
    )

    result, errors = dev_draft_execution.execute_content_target_draft_action(
        _action(), binding=_binding()
    )

    assert errors == ["WordPress zwrócił nieprawidłową odpowiedź szkicu."]
    assert result is not None
    assert result["external_write_attempted"] is True
    assert result["execution_result"]["external_write_attempted"] is True
    assert [request.method for request in requests] == ["POST"]


def test_dev_draft_execution_marks_prewrite_failure_as_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dev_draft_execution, "_dev_draft_writes_enabled", lambda: True)
    monkeypatch.setattr(
        dev_draft_execution,
        "build_content_dev_draft_write_payload",
        lambda _action: _post_payload(),
    )
    monkeypatch.setattr(
        dev_draft_execution,
        "create_wordpress_draft_post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            WordPressDraftWriteError("Brakuje konfiguracji WordPress.")
        ),
    )

    result, errors = dev_draft_execution.execute_content_target_draft_action(
        _action(), binding=_binding()
    )

    assert errors == ["Brakuje konfiguracji WordPress."]
    assert result is not None
    assert result["external_write_attempted"] is False
    assert result["execution_result"]["external_write_attempted"] is False


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


def _readback(content_html: str, *, status: str = "draft") -> WordPressDraftPostReadback:
    return WordPressDraftPostReadback(
        post_id="417",
        endpoint="posts",
        status=status,
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
        lambda _post_id, *, endpoint="posts": _readback(expected_html),
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


def test_stage_readback_uses_persisted_execution_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_html = "<p>Oczekiwana treść.</p>"
    calls: list[tuple[str, str]] = []

    def readback(post_id: str, *, endpoint: str) -> WordPressDraftPostReadback:
        calls.append((post_id, endpoint))
        return _readback(expected_html)

    monkeypatch.setattr(stage_activation, "read_wordpress_draft_post", readback)
    execution = _created_execution(expected_html).model_copy(update={"endpoint": "pages"})

    result = stage_activation.wordpress_draft_readback(execution)

    assert result is not None
    assert result.status == "available"
    assert calls == [("417", "pages")]


def test_stage_readback_blocks_content_digest_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        stage_activation,
        "read_wordpress_draft_post",
        lambda _post_id, *, endpoint="posts": _readback("<p>Inna treść.</p>"),
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


def test_stage_readback_blocks_non_draft_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_html = "<p>Oczekiwana treść.</p>"
    monkeypatch.setattr(
        stage_activation,
        "read_wordpress_draft_post",
        lambda _post_id, *, endpoint="posts": _readback(expected_html, status="publish"),
    )

    result = stage_activation.wordpress_draft_readback(_created_execution(expected_html))

    assert result is not None
    assert result.status == "blocked"
    assert result.verification_status == "blocked"
    assert [blocker.code for blocker in result.blockers] == [
        "wordpress_draft_status_mismatch"
    ]
