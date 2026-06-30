from __future__ import annotations

from typing import Any

from wilq.actions.service import _action_audit_event_label


def first_context_sentence(value: str) -> str:
    for marker in (". To ", ". Blokada ", ". Bez "):
        if marker in value:
            return f"{value.split(marker, 1)[0]}."
    return value


def strip_raw_operator_context(value: Any) -> Any:
    if isinstance(value, list):
        return [strip_raw_operator_context(item) for item in value]
    if not isinstance(value, dict):
        return value
    stripped: dict[str, Any] = {}
    for key, item in value.items():
        if key == "mode" and item == "vendor_read":
            continue
        stripped[key] = strip_raw_operator_context(item)
    return stripped


def latest_audit_event(audit_events: Any) -> dict[str, Any] | None:
    if not isinstance(audit_events, list):
        return None
    dict_events = [event for event in audit_events if isinstance(event, dict)]
    if not dict_events:
        return None
    return max(
        dict_events,
        key=lambda event: (str(event.get("created_at") or ""), str(event.get("id") or "")),
    )


def compact_audit_event_for_daily_context(
    event: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if event is None:
        return None
    event_type = event.get("event_type") or "unknown"
    event_type_label = event.get("event_type_label") or _action_audit_event_label(str(event_type))
    summary = (
        f"Ślad bezpieczeństwa: {event_type_label}. "
        "szczegóły techniczne są dostępne w szczegółach akcji WILQ."
    )
    return {
        "id": event.get("id"),
        "action_id": event.get("action_id"),
        "event_type": event_type,
        "event_type_label": event_type_label,
        "actor": event.get("actor"),
        "created_at": event.get("created_at"),
        "summary": summary,
    }


def compact_audit_event_for_skill_context(
    event: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if event is None:
        return None
    event_type = event.get("event_type") or "unknown"
    event_type_label = event.get("event_type_label") or _action_audit_event_label(str(event_type))
    return {
        "id": event.get("id"),
        "action_id": event.get("action_id"),
        "event_type": event_type,
        "event_type_label": event_type_label,
        "actor": event.get("actor"),
        "created_at": event.get("created_at"),
        "summary": (
            f"Ślad bezpieczeństwa: {event_type_label}. "
            "szczegóły techniczne są dostępne w szczegółach akcji WILQ."
        ),
    }


def compact_metric_fact_for_context(fact: dict[str, Any]) -> dict[str, Any]:
    return {
        "metric_label": fact.get("metric_label"),
        "value": fact.get("value"),
        "unit": fact.get("unit"),
        "period": fact.get("period"),
        "source_connector": fact.get("source_connector"),
        "evidence_id": fact.get("evidence_id"),
        "dimensions": compact_dimensions_for_context(
            fact.get("dimensions"),
            dimension_labels=fact.get("dimension_labels"),
            dimension_value_labels=fact.get("dimension_value_labels"),
        ),
        "freshness_label": fact.get("freshness_label"),
        "trend": fact.get("trend"),
    }


def compact_dimensions_for_context(
    dimensions: Any,
    *,
    dimension_labels: Any = None,
    dimension_value_labels: Any = None,
) -> dict[str, str]:
    if not isinstance(dimensions, dict):
        return {}
    labels = dimension_labels if isinstance(dimension_labels, dict) else {}
    value_labels = dimension_value_labels if isinstance(dimension_value_labels, dict) else {}
    compact: dict[str, str] = {}
    for key, _value in list(dimensions.items())[:8]:
        label = str(labels.get(key) or "").strip()
        value_label = str(value_labels.get(key) or "").strip()
        if label in {"", "wymiar"} or value_label in {
            "",
            "wartość wymiaru do sprawdzenia",
        }:
            continue
        compact_label = label
        suffix = 2
        while compact_label in compact:
            compact_label = f"{label} {suffix}"
            suffix += 1
        compact[compact_label] = (
            value_label if len(value_label) <= 160 else f"{value_label[:157]}..."
        )
    return compact
