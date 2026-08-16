"""Action-authorized transport for one create-only new-page dev draft."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from wilq.connectors.wordpress.client import (
    WordPressDraftWriteError,
    create_wordpress_draft_post,
    missing_credentials,
    read_wordpress_draft_post,
    wordpress_credentials,
    wordpress_edit_link,
)
from wilq.content.workflow.policies import wordpress_dev_host_allowed
from wilq.content.workflow.target.new_page_draft_payload import ContentNewPageDevDraftWritePayload


@dataclass(frozen=True)
class ContentNewPageDevDraftCreated:
    wordpress_post_id: str
    status: str
    link: str
    edit_link: str


def create_new_page_dev_draft(
    payload: ContentNewPageDevDraftWritePayload,
    *,
    action_apply_authorized: bool,
    http_client: httpx.Client | None = None,
) -> ContentNewPageDevDraftCreated:
    """Write exactly one dev draft; callers cannot publish, update, or delete."""
    if action_apply_authorized is not True:
        raise WordPressDraftWriteError("Utworzenie szkicu wymaga autoryzacji ActionObject.")
    credentials = wordpress_credentials(payload.connector)
    if credentials is None:
        raise WordPressDraftWriteError("WILQ nie zna tego connectora WordPress.")
    if not wordpress_dev_host_allowed(credentials.base_url):
        raise WordPressDraftWriteError("Adapter szkicu WordPress działa wyłącznie na hoście dev.")
    if missing_credentials(payload.connector, credentials):
        raise WordPressDraftWriteError(
            "Brakuje konfiguracji WordPress wymaganej do utworzenia szkicu."
        )
    if (
        payload.post_status != "draft"
        or payload.create_only is not True
        or payload.publish_allowed is not False
        or payload.update_allowed is not False
        or payload.delete_allowed is not False
    ):
        raise WordPressDraftWriteError("Adapter przyjmuje wyłącznie create-only szkic dev.")
    post_id = create_wordpress_draft_post(
        payload,
        connector_id=payload.connector,
        endpoint=payload.endpoint,
        http_client=http_client,
    )
    readback = read_wordpress_draft_post(
        post_id,
        connector_id=payload.connector,
        endpoint=payload.endpoint,
        http_client=http_client,
    )
    return ContentNewPageDevDraftCreated(
        wordpress_post_id=post_id,
        status=readback.status,
        link=readback.link,
        edit_link=readback.edit_link or wordpress_edit_link(credentials.base_url, post_id),
    )
