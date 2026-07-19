from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from wilq.actions.service import _action_audit_event_label
from wilq.operator_labels import (
    connector_refresh_status_label,
    credential_field_count_label,
    evidence_count_label,
    freshness_state_label,
    metric_fact_label,
    source_connector_label,
)
from wilq.schemas import ConnectorStatus, connector_status_label


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
        "Szczegóły techniczne są dostępne w szczegółach akcji WILQ."
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


def context_pack_text(value: Any, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3]}..."


def compact_ahrefs_cross_check_for_context(check: Any) -> dict[str, Any]:
    if not isinstance(check, dict):
        return {}
    compact: dict[str, Any] = {
        "strength": check.get("strength", "missing"),
        "label": check.get("label", "brak potwierdzonego dopasowania"),
    }
    for key, limit in (
        ("matching_labels", 4),
        ("source_connectors", 3),
        ("evidence_ids", 3),
    ):
        values = check.get(key)
        if not isinstance(values, list):
            values = []
        compact[key] = values[:limit]
        compact[f"{key}_total"] = len(values)
    return compact


def without_metric_facts(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: without_metric_facts(item)
            for key, item in value.items()
            if key != "metric_facts" and not key.endswith("_metric_facts")
        }
    if isinstance(value, list):
        return [without_metric_facts(item) for item in value]
    return value


def list_at(data: dict[str, Any], *path: str) -> list[Any]:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    return current if isinstance(current, list) else []


def metric_value(facts: list[Any], name: str) -> float | int | str | None:
    for fact in facts:
        if getattr(fact, "name", None) == name:
            return getattr(fact, "value", None)
    return None


def numeric_or_zero(value: Any) -> float:
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def priority_limited_strings(value: Any, required: list[str], limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in [*required, *value]:
        if not isinstance(item, str) or item in result:
            continue
        if item not in value:
            continue
        result.append(item)
        if len(result) >= limit:
            break
    return result


def compact_refresh_run_for_operator_context(run: dict[str, Any]) -> dict[str, Any]:
    raw_evidence_ids = run.get("evidence_ids")
    evidence_ids: list[Any] = raw_evidence_ids if isinstance(raw_evidence_ids, list) else []
    raw_missing_credentials = run.get("missing_credentials")
    missing_credentials: list[Any] = (
        raw_missing_credentials if isinstance(raw_missing_credentials, list) else []
    )
    checked_credentials = (
        run.get("checked_credentials") if isinstance(run.get("checked_credentials"), list) else []
    )
    metric_summary = run.get("metric_summary")
    metric_keys = sorted(metric_summary.keys()) if isinstance(metric_summary, dict) else []
    connector_id = str(run.get("connector_id") or "")
    metric_labels = [metric_fact_label(key, connector_id) for key in metric_keys]
    source_label = source_connector_label(str(run.get("connector_id") or ""))
    status_label = connector_refresh_status_label(run.get("status"))
    evidence_summary_label = evidence_count_label(str(item) for item in evidence_ids)
    missing_credentials_summary_label = credential_field_count_label(
        str(item) for item in missing_credentials
    )
    summary = (
        f"Odczyt danych {source_label}: {status_label}; "
        f"{evidence_summary_label}; {missing_credentials_summary_label}."
    )
    return {
        "id": run.get("id"),
        "connector_id": run.get("connector_id"),
        "status": run.get("status"),
        "status_label": status_label,
        "connector_label": source_label,
        "started_at": run.get("started_at"),
        "completed_at": run.get("completed_at"),
        "summary": summary,
        "evidence_ids": evidence_ids,
        "missing_credentials": missing_credentials,
        "checked_credentials": checked_credentials,
        "external_call_attempted": bool(run.get("external_call_attempted")),
        "vendor_data_collected": bool(run.get("vendor_data_collected")),
        "metric_summary": {
            "metric_key_count": len(metric_keys),
            "metric_labels": metric_labels[:8],
            "metric_labels_included": min(len(metric_labels), 8),
        },
        "errors": [],
        "redacted": True,
    }


def compact_connector_status_for_operator_context(
    connector: ConnectorStatus | dict[str, Any],
) -> dict[str, Any]:
    dumped = (
        connector.model_dump(mode="json")
        if isinstance(connector, ConnectorStatus)
        else dict(connector)
    )
    freshness = dumped.get("freshness")
    compact_freshness: Any
    if isinstance(freshness, dict):
        freshness_state = freshness.get("state") or "unknown"
        compact_freshness = {
            "state": freshness_state,
            "label": freshness_state_label(str(freshness_state)),
            "checked_at": freshness.get("checked_at"),
            "last_success_at": freshness.get("last_success_at"),
            "notes": freshness.get("notes"),
        }
    else:
        compact_freshness = freshness
    capabilities = dumped.get("capabilities")
    compact_capabilities: dict[str, Any] = (
        {
            "read": bool(capabilities.get("read")),
            "write": bool(capabilities.get("write")),
            "read_adapter_implemented": capabilities.get("read_adapter") is not None,
            "mutation_adapter_implemented": capabilities.get("mutation_adapter") is not None,
            "action_scope": capabilities.get("action_scope") or "read_only",
            "blockers": capabilities.get("blockers")
            if isinstance(capabilities.get("blockers"), list)
            else [],
        }
        if isinstance(capabilities, dict)
        else {}
    )
    supported_actions = dumped.get("supported_actions")
    missing_credentials = dumped.get("missing_credentials")
    status_label = dumped.get("status_label") or connector_status_label(
        str(dumped.get("status") or "unknown")
    )
    freshness_label = (
        compact_freshness.get("label")
        if isinstance(compact_freshness, dict)
        else freshness_state_label(None)
    )
    return {
        "id": dumped.get("id"),
        "label": dumped.get("label"),
        "status": dumped.get("status"),
        "status_label": status_label,
        "configured": dumped.get("configured"),
        "freshness": compact_freshness,
        "last_success_at": dumped.get("last_success_at"),
        "missing_credentials": (
            missing_credentials if isinstance(missing_credentials, list) else []
        ),
        "capabilities": compact_capabilities,
        "capability_count": sum(
            1
            for key in ("read", "write")
            if compact_capabilities.get(key) is True
        )
        + (1 if supported_actions else 0),
        "supported_action_count": (
            len(supported_actions) if isinstance(supported_actions, list) else 0
        ),
        "summary": (
            f"Źródło danych {dumped.get('label') or dumped.get('id')}: "
            f"{status_label}; {freshness_label}."
        ),
    }


def connector_readiness_for_context(
    connectors: Sequence[ConnectorStatus | dict[str, Any]],
    scoped_connector_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Project connector health into an explicit consumer-facing fail-closed contract.

    A connector count alone cannot tell an operator whether a metric-backed
    decision may use a source. Keep the existing status as authority, but add
    the concrete consequence for the current context pack.
    """
    rows: list[dict[str, Any]] = []
    for connector in connectors:
        dumped = (
            connector.model_dump(mode="json")
            if isinstance(connector, ConnectorStatus)
            else dict(connector)
        )
        connector_id = str(dumped.get("id") or "")
        if scoped_connector_ids is not None and connector_id not in scoped_connector_ids:
            continue
        status = str(dumped.get("status") or "unknown")
        configured = bool(dumped.get("configured"))
        capabilities = dumped.get("capabilities")
        read_available = bool(capabilities.get("read")) if isinstance(capabilities, dict) else False
        freshness = dumped.get("freshness")
        freshness_state = (
            str(freshness.get("state") or "unknown")
            if isinstance(freshness, dict)
            else "unknown"
        )
        missing_credentials = dumped.get("missing_credentials")
        has_missing_credentials = isinstance(missing_credentials, list) and bool(
            missing_credentials
        )
        if has_missing_credentials or status == "missing_credentials":
            readiness_status = "blocked"
            blocker_code = "missing_credentials"
            effect = "decyzje wymagające tego źródła pozostają zablokowane"
        elif not configured or not read_available:
            readiness_status = "blocked"
            blocker_code = "read_unavailable"
            effect = "nie wolno opierać decyzji na tym źródle"
        elif freshness_state != "fresh":
            readiness_status = "blocked"
            blocker_code = "stale_or_unknown_source"
            effect = "metryki i wnioski z tego źródła wymagają odświeżenia"
        else:
            readiness_status = "ready"
            blocker_code = None
            effect = "źródło może zasilać decyzje w tym kontekście"
        rows.append(
            {
                "connector_id": connector_id,
                "label": dumped.get("label"),
                "status": readiness_status,
                "blocker_code": blocker_code,
                "configured": configured,
                "read_available": read_available,
                "freshness_state": freshness_state,
                "missing_credentials": (
                    missing_credentials if isinstance(missing_credentials, list) else []
                ),
                "effect": effect,
            }
        )
    blocked = [row for row in rows if row["status"] == "blocked"]
    return {
        "contract": "connector_consumer_readiness_v1",
        "rows": rows,
        "total": len(rows),
        "ready": len(rows) - len(blocked),
        "blocked": len(blocked),
        "blocked_connector_ids": [row["connector_id"] for row in blocked],
        "instruction": (
            "Źródło z blokadą nie może zasilać metryk, rekomendacji ani claimów; "
            "najpierw usuń wskazaną blokadę lub jawnie oznacz wynik jako niepełny."
        ),
    }


def compact_labelled_contract_list_for_context(
    payload: dict[str, Any],
    *,
    raw_key: str,
    label_key: str,
) -> None:
    raw_values = payload.get(raw_key)
    labels = payload.get(label_key)
    raw_count = len(raw_values) if isinstance(raw_values, list) else 0
    if isinstance(labels, list):
        payload[f"{label_key}_total"] = len(labels)
        payload[label_key] = labels[:6]
        payload[f"{label_key}_included"] = len(payload[label_key])
    elif raw_count:
        payload[f"{label_key}_total"] = raw_count
        payload[f"{label_key}_included"] = 0
    payload[f"{raw_key}_total"] = raw_count
    payload.pop(raw_key, None)
