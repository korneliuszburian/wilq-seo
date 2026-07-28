"""Action-authorized transport for one create-only new-page dev draft."""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

import httpx

from wilq.connectors.wordpress.client import (
    WORDPRESS_DEV_HOSTS,
    WordPressDraftWriteError,
    _created_draft_post_id,
    _missing_credentials,
    _wordpress_credentials,
)
from wilq.content.workflow.new_page_draft_payload import ContentNewPageDevDraftWritePayload


def create_new_page_dev_draft(
    payload: ContentNewPageDevDraftWritePayload,
    *,
    action_apply_authorized: bool,
    http_client: httpx.Client | None = None,
) -> str:
    """Write exactly one dev draft; callers cannot publish, update, or delete."""
    if action_apply_authorized is not True:
        raise WordPressDraftWriteError("Utworzenie szkicu wymaga autoryzacji ActionObject.")
    credentials = _wordpress_credentials(payload.connector)
    if credentials is None:
        raise WordPressDraftWriteError("WILQ nie zna tego connectora WordPress.")
    if (urlparse(credentials.base_url or "").hostname or "").lower() not in WORDPRESS_DEV_HOSTS:
        raise WordPressDraftWriteError("Adapter szkicu WordPress działa wyłącznie na hoście dev.")
    if _missing_credentials(payload.connector, credentials):
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
    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30)
    try:
        response = client.post(
            urljoin(credentials.base_url or "", f"wp-json/wp/v2/{payload.endpoint}"),
            auth=httpx.BasicAuth(credentials.username or "", credentials.application_auth or ""),
            params={"_fields": "id,status,link"},
            json={"status": "draft", "title": payload.title, "content": payload.content_html},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise WordPressDraftWriteError(
            f"WordPress odrzucił utworzenie szkicu HTTP {exc.response.status_code}."
        ) from exc
    except httpx.HTTPError as exc:
        raise WordPressDraftWriteError(
            f"Połączenie WordPress przerwało tworzenie szkicu ({type(exc).__name__})."
        ) from exc
    finally:
        if owns_client:
            client.close()
    return _created_draft_post_id(response)
