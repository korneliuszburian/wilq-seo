from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest

from wilq.connectors.wordpress.client import (
    WordPressCredentials,
    WordPressDraftVerificationError,
    WordPressDraftWriteError,
)
from wilq.content.workflow.target.new_page_apply_capability import NewPageApplyCapability
from wilq.content.workflow.target.new_page_document import ContentNewPageDeliveryReadiness
from wilq.content.workflow.target.new_page_draft_action import (
    ContentNewPageDraftActionCommand,
    create_new_page_draft_action,
)
from wilq.content.workflow.target.new_page_draft_execution import create_new_page_dev_draft
from wilq.content.workflow.target.new_page_draft_executor import execute_new_page_draft_action
from wilq.content.workflow.target.new_page_draft_payload import ContentNewPageDevDraftWritePayload
from wilq.content.workflow.target.new_page_revision_binding import ContentNewPageDraftBinding


def _payload() -> ContentNewPageDevDraftWritePayload:
    return ContentNewPageDevDraftWritePayload(
        endpoint="pages",
        title="Dokumentacja środowiskowa",
        content_html="<h1>Dokumentacja</h1>",
        binding=ContentNewPageDraftBinding(
            work_item_id="content_work_item_new_page",
            brief_id="brief_1",
            brief_digest="a" * 64,
            foundation_id="foundation_1",
            service_card_id="service_environment",
            service_card_digest="b" * 64,
            revision_id="revision_1",
            revision_digest="c" * 64,
            authoring_profile_digest="d" * 64,
            content_type="page",
        ),
    )


def test_new_page_execution_writes_only_one_authorized_dev_page_draft(monkeypatch) -> None:
    credentials = WordPressCredentials(
        base_url="https://ekologus.dev.proudsite.pl/",
        public_url=None,
        username="operator",
        application_auth="secret",
        site_kind="primary",
    )
    monkeypatch.setattr(
        "wilq.content.workflow.target.new_page_draft_execution.wordpress_credentials",
        lambda connector_id: credentials,
    )
    monkeypatch.setattr(
        "wilq.content.workflow.target.new_page_draft_execution.missing_credentials",
        lambda connector_id, credentials: [],
    )
    monkeypatch.setattr(
        "wilq.connectors.wordpress.client.wordpress_credentials",
        lambda connector_id: credentials,
    )
    monkeypatch.setattr(
        "wilq.connectors.wordpress.client.missing_credentials",
        lambda connector_id, credentials: [],
    )
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.method == "POST":
            return httpx.Response(
                201, json={"id": 41, "status": "draft", "link": "https://dev/draft"}
            )
        return httpx.Response(
            200,
            json={
                "id": 41,
                "status": "draft",
                "link": "https://dev/draft",
                "title": {"raw": "Dokumentacja środowiskowa"},
                "content": {"raw": "<h1>Dokumentacja</h1>"},
                "acf": {},
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler)
    )
    try:
        result = create_new_page_dev_draft(
            _payload(), action_apply_authorized=True, http_client=client
        )
    finally:
        client.close()
    assert [request.method for request in seen] == ["POST", "GET", "GET"]
    assert seen[0].url.path == "/wp-json/wp/v2/pages"
    assert result.wordpress_post_id == "41"
    assert result.status == "draft"
    assert result.link == "https://dev/draft"
    assert result.edit_link == (
        "https://ekologus.dev.proudsite.pl/wp-admin/post.php?post=41&action=edit"
    )
    body = json.loads(seen[0].content)
    assert body["status"] == "draft"
    assert body["content"] == "<h1>Dokumentacja</h1>"


def test_new_page_execution_blocks_mismatched_verified_readback(monkeypatch) -> None:
    credentials = WordPressCredentials(
        base_url="https://ekologus.dev.proudsite.pl/",
        public_url=None,
        username="operator",
        application_auth="secret",
        site_kind="primary",
    )
    monkeypatch.setattr(
        "wilq.content.workflow.target.new_page_draft_execution.wordpress_credentials",
        lambda connector_id: credentials,
    )
    monkeypatch.setattr(
        "wilq.content.workflow.target.new_page_draft_execution.missing_credentials",
        lambda connector_id, credentials: [],
    )
    monkeypatch.setattr(
        "wilq.connectors.wordpress.client.wordpress_credentials",
        lambda connector_id: credentials,
    )
    monkeypatch.setattr(
        "wilq.connectors.wordpress.client.missing_credentials",
        lambda connector_id, credentials: [],
    )
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                201 if request.method == "POST" else 200,
                json=(
                    {"id": 41, "status": "draft"}
                    if request.method == "POST"
                    else {
                        "id": 41,
                        "status": "draft",
                        "content": {"raw": "<p>Inna treść</p>"},
                        "acf": {},
                    }
                ),
            )
        )
    )
    try:
        with pytest.raises(WordPressDraftVerificationError):
            create_new_page_dev_draft(
                _payload(), action_apply_authorized=True, http_client=client
            )
    finally:
        client.close()


def test_new_page_execution_rejects_missing_action_authorization() -> None:
    with pytest.raises(WordPressDraftWriteError, match="autoryzacji"):
        create_new_page_dev_draft(_payload(), action_apply_authorized=False)


def test_new_page_executor_stops_before_store_or_transport_when_env_is_disabled(
    monkeypatch,
) -> None:
    action = create_new_page_draft_action(
        ContentNewPageDeliveryReadiness(
            status="ready_for_action",
            work_item_id="content_work_item_new_page",
            brief_id="brief_1",
            brief_digest="a" * 64,
            foundation_id="foundation_1",
            service_card_id="service_environment",
            service_card_digest="b" * 64,
            revision_id="revision_1",
            revision_digest="c" * 64,
            allowed_content_types=["page"],
            authoring_profile_digest="d" * 64,
            evidence_ids=["ev_authoring"],
            safe_next_step="Utwórz ActionObject.",
        ),
        ContentNewPageDraftActionCommand(
            expected_revision_digest="c" * 64,
            expected_authoring_profile_digest="d" * 64,
            content_type="page",
            requested_by="Wilku",
        ),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.target.new_page_draft_executor._dev_draft_writes_enabled",
        lambda: False,
    )

    result, errors = execute_new_page_draft_action(action)

    assert result is None
    assert errors == ["Środowisko dev nie zezwala obecnie na utworzenie szkicu WordPress."]


@pytest.mark.parametrize(
    "error",
    [
        WordPressDraftWriteError("Nie udało się utworzyć szkicu WordPress."),
        WordPressDraftVerificationError(
            "Nie można potwierdzić dokładnego szkicu WordPress.",
            post_id="41",
            code="content_digest_mismatch",
        ),
    ],
)
def test_new_page_executor_returns_wordpress_transport_errors_as_blockers(
    monkeypatch, error
) -> None:
    action = create_new_page_draft_action(
        ContentNewPageDeliveryReadiness(
            status="ready_for_action",
            work_item_id="content_work_item_new_page",
            brief_id="brief_1",
            brief_digest="a" * 64,
            foundation_id="foundation_1",
            service_card_id="service_environment",
            service_card_digest="b" * 64,
            revision_id="revision_1",
            revision_digest="c" * 64,
            allowed_content_types=["page"],
            authoring_profile_digest="d" * 64,
            evidence_ids=["ev_authoring"],
            safe_next_step="Utwórz ActionObject.",
        ),
        ContentNewPageDraftActionCommand(
            expected_revision_digest="c" * 64,
            expected_authoring_profile_digest="d" * 64,
            content_type="page",
            requested_by="Wilku",
        ),
    )
    binding = _payload().binding
    monkeypatch.setattr(
        "wilq.content.workflow.target.new_page_draft_executor.content_workflow_store",
        lambda: type(
            "Store",
            (),
            {
                "list_draft_revisions": lambda self, _: [
                    SimpleNamespace(
                        revision_id=binding.revision_id,
                        content_digest=binding.revision_digest,
                    )
                ]
            },
        )(),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.target.new_page_draft_executor.build_new_page_dev_draft_write_payload",
        lambda revision, current_binding: _payload(),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.target.new_page_draft_executor.create_new_page_dev_draft",
        lambda payload, *, action_apply_authorized: (_ for _ in ()).throw(error),
    )

    result, errors = execute_new_page_draft_action(
        action,
        NewPageApplyCapability(binding=binding, action_chain=object()),
    )

    assert result is None
    assert errors == [str(error)]
