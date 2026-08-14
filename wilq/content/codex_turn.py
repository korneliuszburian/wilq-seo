from __future__ import annotations

from typing import Final, cast

from wilq.codex.app_server import CodexAppServerTurnResult
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace

_EMPTY_ARRAY_ONLY_PLACEHOLDER: Final = "__WILQ_EMPTY_ARRAY_ONLY__"


def require_all_object_properties(value: object) -> None:
    """Make Pydantic defaults explicit for Codex structured output."""

    if isinstance(value, dict):
        properties_value = value.get("properties")
        if isinstance(properties_value, dict):
            value["required"] = list(properties_value)
        value.pop("default", None)
        for nested in value.values():
            require_all_object_properties(nested)
    elif isinstance(value, list):
        for nested in value:
            require_all_object_properties(nested)


def runtime_trace(result: CodexAppServerTurnResult) -> ContentCodexRuntimeTrace:
    return ContentCodexRuntimeTrace(
        status=result.status,
        thread_id=result.thread_id,
        turn_id=result.turn_id,
        event_methods=list(result.event_methods),
        item_types=list(result.item_types),
        external_call_attempted=result.external_call_attempted,
    )


def mapping(value: dict[str, object], key: str) -> dict[str, object]:
    nested = value.get(key)
    if not isinstance(nested, dict):
        raise RuntimeError(f"Codex output schema is missing {key}.")
    return cast(dict[str, object], nested)


def properties(definition: dict[str, object]) -> dict[str, object]:
    return mapping(definition, "properties")


def definition(definitions: dict[str, object], name: str) -> dict[str, object]:
    return mapping(definitions, name)


def restrict_array(
    properties: dict[str, object],
    key: str,
    values: list[str],
) -> None:
    """Restrict a planning array, forcing it empty when no values are allowed."""

    field = mapping(properties, key)
    unique = list(dict.fromkeys(values))
    if unique:
        field["items"] = {"enum": unique, "type": "string"}
    else:
        field["maxItems"] = 0


def restrict_array_with_empty_placeholder(
    properties: dict[str, object],
    key: str,
    values: list[str],
    *,
    missing_items_error_prefix: str = "Codex output schema",
) -> None:
    """Restrict existing string items, using an unreachable enum when empty.

    The error prefix stays explicit because assurance and semantic review expose
    different historical diagnostics for a malformed item schema.
    """

    field = mapping(properties, key)
    items = field.get("items")
    if not isinstance(items, dict):
        raise RuntimeError(f"{missing_items_error_prefix} is missing {key}.items.")
    cast(dict[str, object], items)["enum"] = values or [_EMPTY_ARRAY_ONLY_PLACEHOLDER]


def cap_array(properties: dict[str, object], key: str, maximum: int) -> None:
    field = mapping(properties, key)
    current = field.get("maxItems")
    if not isinstance(current, int) or current > maximum:
        field["maxItems"] = maximum


def set_array_size(properties: dict[str, object], key: str, size: int) -> None:
    field = mapping(properties, key)
    field["minItems"] = size
    field["maxItems"] = size


__all__ = [
    "cap_array",
    "definition",
    "mapping",
    "properties",
    "require_all_object_properties",
    "restrict_array",
    "restrict_array_with_empty_placeholder",
    "runtime_trace",
    "set_array_size",
]
