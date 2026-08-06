from __future__ import annotations

import json
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, ConfigDict, Field

from wilq.connectors.wordpress.client import _missing_credentials, _wordpress_credentials

if TYPE_CHECKING:
    from wilq.connectors.wordpress.authoring import WordPressAuthoringDevContentObject


class WordPressAcfRestSchemaField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    label: str
    field_type: str
    required: bool = False
    source_method: Literal["acf_rest"] = "acf_rest"
    sub_fields: list[WordPressAcfRestSchemaField] = Field(default_factory=list)


class WordPressAcfRestSchemaLayout(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    label: str
    fields: list[WordPressAcfRestSchemaField] = Field(default_factory=list)
    source_method: Literal["acf_rest"] = "acf_rest"
    required_field_names: list[str] = Field(default_factory=list)
    optional_field_names: list[str] = Field(default_factory=list)


class WordPressAcfRestSchema(BaseModel):
    """Exact ACF schema observed for one WordPress object through ``OPTIONS``.

    This is deliberately an observation, not a write profile. ACF's REST
    schema explains the object shape, but a safe create-only draft must still
    preserve every non-copy value from the source layout.
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["available", "unavailable"]
    root_field: str
    layouts: list[WordPressAcfRestSchemaLayout] = Field(default_factory=list)
    schema_digest: str | None = None
    source_ref: str = ""
    reason: str = ""


def read_wordpress_acf_rest_schema(
    connector_id: str,
    item: WordPressAuthoringDevContentObject,
    *,
    http_client: httpx.Client | None = None,
) -> WordPressAcfRestSchema:
    """Read one exact Flexible Content schema from the core WordPress endpoint.

    ACF documents ``OPTIONS`` on the ordinary post/page endpoint as the schema
    surface for fields exposed through its REST integration. The response is
    untrusted external input; malformed or partial schemas stay unavailable.
    """

    root_field = item.acf_field_name or ""
    endpoint = item.rest_endpoint.strip().strip("/")
    source_ref = f"wp-json/wp/v2/{endpoint or item.content_type}/{item.post_id} OPTIONS"
    if not root_field:
        return _unavailable_schema(
            root_field, source_ref, "Obiekt dev nie wskazuje pola ACF Flexible Content."
        )
    if not endpoint:
        return _unavailable_schema(
            root_field,
            source_ref,
            "WILQ nie obsługuje schematu ACF dla tego typu obiektu dev.",
        )
    credentials = _wordpress_credentials(connector_id)
    if credentials is None or _missing_credentials(connector_id, credentials):
        return _unavailable_schema(
            root_field,
            source_ref,
            "Brakuje konfiguracji WordPress do odczytu schematu ACF.",
        )

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=20)
    auth = httpx.BasicAuth(credentials.username or "", credentials.application_auth or "")
    try:
        try:
            response = client.options(
                urljoin(credentials.base_url or "", f"wp-json/wp/v2/{endpoint}/{item.post_id}"),
                auth=auth,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            return _unavailable_schema(
                root_field,
                source_ref,
                "WordPress nie udostępnił schematu ACF tego obiektu "
                f"(HTTP {exc.response.status_code}).",
            )
        except (httpx.HTTPError, ValueError):
            return _unavailable_schema(
                root_field,
                source_ref,
                "Nie udało się odczytać poprawnego schematu ACF z WordPress.",
            )
    finally:
        if owns_client:
            client.close()

    layouts = _acf_rest_layouts_from_options(payload, root_field=root_field)
    if not layouts:
        return _unavailable_schema(
            root_field,
            source_ref,
            "Odczyt OPTIONS nie potwierdza kompletnych layoutów Flexible Content dla tego pola.",
        )
    normalized = [layout.model_dump(mode="json") for layout in layouts]
    digest = sha256(
        json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return WordPressAcfRestSchema(
        status="available",
        root_field=root_field,
        layouts=layouts,
        schema_digest=digest,
        source_ref=source_ref,
        reason="Schema ACF została odczytana przez OPTIONS dla dokładnego obiektu dev.",
    )


def _unavailable_schema(root_field: str, source_ref: str, reason: str) -> WordPressAcfRestSchema:
    return WordPressAcfRestSchema(
        status="unavailable",
        root_field=root_field,
        source_ref=source_ref,
        reason=reason,
    )


def _acf_rest_layouts_from_options(
    payload: object,
    *,
    root_field: str,
) -> list[WordPressAcfRestSchemaLayout]:
    if not isinstance(payload, dict):
        return []
    schema = payload.get("schema")
    if not isinstance(schema, dict):
        return []
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return []
    acf = properties.get("acf")
    if not isinstance(acf, dict):
        return []
    acf_properties = acf.get("properties")
    if not isinstance(acf_properties, dict):
        return []
    flexible = acf_properties.get(root_field)
    if not isinstance(flexible, dict):
        return []
    items = flexible.get("items")
    if not isinstance(items, dict):
        return []
    branches = items.get("oneOf")
    if not isinstance(branches, list):
        return []
    layouts = [
        layout
        for branch in branches
        if isinstance(branch, dict)
        for layout in [_acf_rest_layout_from_branch(branch)]
        if layout is not None
    ]
    return sorted(layouts, key=lambda layout: layout.name)


def _acf_rest_layout_from_branch(branch: dict[str, Any]) -> WordPressAcfRestSchemaLayout | None:
    properties = branch.get("properties")
    if not isinstance(properties, dict):
        return None
    selector = properties.get("acf_fc_layout")
    if not isinstance(selector, dict):
        return None
    layout_name = _exact_layout_name(selector.get("pattern"))
    if layout_name is None:
        return None
    required_names = _required_property_names(branch.get("required"))
    fields = [
        field
        for name, value in properties.items()
        if name != "acf_fc_layout" and isinstance(name, str) and name
        for field in [_acf_rest_field(name, value, required=name in required_names)]
        if field is not None
    ]
    required = [field.name for field in fields if field.required]
    optional = [field.name for field in fields if not field.required]
    return WordPressAcfRestSchemaLayout(
        name=layout_name,
        label=layout_name.replace("_", " ").replace("-", " ").capitalize(),
        fields=fields,
        source_method="acf_rest",
        required_field_names=required,
        optional_field_names=optional,
    )


def _exact_layout_name(value: object) -> str | None:
    if not isinstance(value, str) or len(value) < 3:
        return None
    if not value.startswith("^") or not value.endswith("$"):
        return None
    candidate = value[1:-1]
    if not candidate or any(not (char.isalnum() or char in {"_", "-"}) for char in candidate):
        return None
    return candidate


def _acf_rest_field(
    name: str,
    payload: object,
    *,
    required: bool,
    depth: int = 0,
) -> WordPressAcfRestSchemaField | None:
    if not isinstance(payload, dict) or depth > 8:
        return None
    properties = payload.get("properties")
    nested_properties = properties if isinstance(properties, dict) else {}
    items = payload.get("items")
    if not nested_properties and isinstance(items, dict):
        item_properties = items.get("properties")
        nested_properties = item_properties if isinstance(item_properties, dict) else {}
    required_names = _required_property_names(payload.get("required"))
    sub_fields = [
        field
        for child_name, child_payload in nested_properties.items()
        if isinstance(child_name, str) and child_name
        for field in [
            _acf_rest_field(
                child_name,
                child_payload,
                required=child_name in required_names,
                depth=depth + 1,
            )
        ]
        if field is not None
    ]
    return WordPressAcfRestSchemaField(
        name=name,
        label=name.replace("_", " ").replace("-", " ").capitalize(),
        field_type=_acf_rest_field_type(payload, has_children=bool(sub_fields)),
        required=required,
        source_method="acf_rest",
        sub_fields=sub_fields,
    )


def _acf_rest_field_type(payload: dict[str, Any], *, has_children: bool) -> str:
    if has_children and isinstance(payload.get("items"), dict):
        return "array"
    if has_children:
        return "object"
    raw_type = payload.get("type")
    types = raw_type if isinstance(raw_type, list) else [raw_type]
    values = [value for value in types if isinstance(value, str) and value != "null"]
    items = payload.get("items")
    if set(values) == {"integer", "array"} and isinstance(items, dict):
        return "integer_array"
    return values[0] if len(values) == 1 else "unknown"


def _required_property_names(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str) and item}
