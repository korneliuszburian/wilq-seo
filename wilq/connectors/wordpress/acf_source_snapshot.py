from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from urllib.parse import urljoin

import httpx

from wilq.connectors.wordpress.client import (
    _missing_credentials,
    _wordpress_credentials,
)

_WORDPRESS_ACF_CONTENT_TYPES = {"posts", "pages"}


@dataclass(frozen=True)
class WordPressAcfFlexibleSnapshot:
    """Raw source rows retained only in the in-process clone compiler."""

    object_id: str
    content_type: str
    root_field: str
    root_digest: str
    rows: list[dict[str, Any]]


def read_wordpress_acf_flexible_snapshot(
    connector_id: str,
    *,
    object_id: str,
    content_type: str,
    root_field: str,
    http_client: httpx.Client | None = None,
) -> WordPressAcfFlexibleSnapshot:
    """Read one exact root at apply time; do not persist its raw values."""

    credentials = _wordpress_credentials(connector_id)
    endpoint = content_type.strip().strip("/")
    normalized_id = str(object_id).strip()
    normalized_root = root_field.strip()
    if credentials is None or _missing_credentials(connector_id, credentials):
        raise ValueError("Brakuje konfiguracji WordPress do odczytu układu ACF.")
    if endpoint not in _WORDPRESS_ACF_CONTENT_TYPES or not normalized_id or not normalized_root:
        raise ValueError("Brakuje dokładnego obiektu, typu treści lub pola ACF.")

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30)
    auth = httpx.BasicAuth(credentials.username or "", credentials.application_auth or "")
    try:
        response = client.get(
            urljoin(credentials.base_url or "", f"wp-json/wp/v2/{endpoint}/{normalized_id}"),
            auth=auth,
            params={"context": "edit", "_fields": "id,acf"},
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        raise ValueError(
            "WordPress odrzucił odczyt pola ACF "
            f"dla dokładnego obiektu HTTP {exc.response.status_code}."
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise ValueError("Nie udało się odczytać dokładnego pola ACF z WordPress.") from exc
    finally:
        if owns_client:
            client.close()

    if not isinstance(payload, dict) or str(payload.get("id") or "") != normalized_id:
        raise ValueError("WordPress zwrócił inny obiekt niż wskazany target.")
    acf = payload.get("acf")
    rows = acf.get(normalized_root) if isinstance(acf, dict) else None
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("WordPress nie zwrócił kompletnej listy layoutów ACF.")
    normalized_rows = [dict(row) for row in rows]
    if any(
        not isinstance(row.get("acf_fc_layout"), str) or not row["acf_fc_layout"]
        for row in normalized_rows
    ):
        raise ValueError("WordPress nie zwrócił kompletnej tożsamości layoutów ACF.")
    return WordPressAcfFlexibleSnapshot(
        object_id=normalized_id,
        content_type=endpoint,
        root_field=normalized_root,
        root_digest=_digest_rows(normalized_rows),
        rows=normalized_rows,
    )


def _digest_rows(rows: list[dict[str, Any]]) -> str:
    return sha256(
        json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


__all__ = ["WordPressAcfFlexibleSnapshot", "read_wordpress_acf_flexible_snapshot"]
