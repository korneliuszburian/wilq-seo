from __future__ import annotations

from typing import Any


def daily_context_evidence_ids(
    command: Any,
    brief: Any,
    actions: list[Any],
) -> set[str]:
    evidence_ids = set(brief.evidence_ids)
    evidence_ids.update(collect_values_by_key(command.model_dump(mode="json"), "evidence_ids"))
    for action in actions:
        evidence_ids.update(action.evidence_ids)
    return evidence_ids


def daily_context_connectors(
    command: Any,
    brief: Any,
    actions: list[Any],
) -> set[str]:
    source_connectors = set(
        collect_values_by_key(command.model_dump(mode="json"), "source_connectors")
    )
    source_connectors.update(
        collect_values_by_key(brief.model_dump(mode="json"), "source_connectors")
    )
    source_connectors.update(action.connector for action in actions)
    return source_connectors


def evidence_ids_from_context(
    diagnostics: dict[str, Any],
    actions: list[Any],
    scoped_connectors: set[str],
) -> set[str]:
    evidence_ids: set[str] = set()
    for value in diagnostics.values():
        evidence_ids.update(collect_values_by_key(value, "evidence_ids"))
    for action in actions:
        if action.connector in scoped_connectors:
            evidence_ids.update(action.evidence_ids)
    return evidence_ids


def collect_values_by_key(value: Any, key: str) -> set[str]:
    values: set[str] = set()
    if isinstance(value, dict):
        for item_key, item_value in value.items():
            if item_key == key and isinstance(item_value, list):
                values.update(str(item) for item in item_value if item)
            else:
                values.update(collect_values_by_key(item_value, key))
    elif isinstance(value, list):
        for item in value:
            values.update(collect_values_by_key(item, key))
    return values


def connectors_intersect(values: list[str], scoped_connectors: set[str]) -> bool:
    return bool(set(values).intersection(scoped_connectors))
