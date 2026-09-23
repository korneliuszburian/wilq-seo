"""Operator label context shared by action review and preview projections."""

from __future__ import annotations

from collections.abc import Iterable

from wilq.actions.content_refresh import content_contract_label
from wilq.actions.gate_labels import action_gate_label
from wilq.actions.review_gate import (
    review_blocker_label,
    review_source_type_label,
    review_summary_item,
)
from wilq.briefing.blocked_claim_labels import operator_blocked_claims
from wilq.connectors.registry import get_connector_status


def operator_review_summary_item(item: str) -> str:
    return review_summary_item(
        item,
        contract_label=content_contract_label,
        source_type_label=operator_review_source_type_label,
    )


def operator_review_blocker_label(item: str) -> str:
    return review_blocker_label(
        item,
        gate_label=action_gate_label,
        contract_label=content_contract_label,
        blocked_claim_labels=operator_blocked_claims,
    )


def operator_review_source_type_label(value: str) -> str:
    return review_source_type_label(value, contract_label=content_contract_label)


def registered_source_connector_label(connector_id: str) -> str:
    connector = get_connector_status(connector_id)
    return connector.label if connector is not None and connector.label else "źródło danych"


def registered_source_connector_labels(connector_ids: Iterable[str]) -> list[str]:
    labels: list[str] = []
    for connector_id in connector_ids:
        label = registered_source_connector_label(connector_id)
        if label not in labels:
            labels.append(label)
    return labels
