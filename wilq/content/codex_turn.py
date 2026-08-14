from __future__ import annotations

from typing import cast

from wilq.codex.app_server import CodexAppServerTurnResult
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace


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


__all__ = [
    "definition",
    "mapping",
    "properties",
    "require_all_object_properties",
    "runtime_trace",
]
