from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from wilq.schemas import MetricFact

LOCALO_VISIBILITY_REVIEW_ACTION_ID = "act_review_localo_visibility_facts"
LOCALO_VISIBILITY_REVIEW_ACTION_TYPE = "local_visibility_task"
LOCALO_VISIBILITY_BLOCKED_CLAIMS = [
    "GBP performance",
    "competitor visibility",
    "local task completed",
    "GBP write",
    "local visibility uplift",
]
LOCALO_VISIBILITY_CONTRACTS = [
    "place_inventory",
    "local_rankings",
    "gbp_visibility",
    "competitor_visibility",
    "reviews",
    "local_tasks",
]


def localo_visibility_review_payload_from_metric_facts(
    facts: list[MetricFact],
) -> dict[str, Any] | None:
    visibility_facts = [fact for fact in facts if fact.source_connector == "localo"]
    if not visibility_facts:
        return None
    present_contracts = _unique(
        str(fact.dimensions.get("contract", ""))
        for fact in visibility_facts
        if fact.dimensions.get("contract")
    )
    missing_contracts = [
        contract
        for contract in LOCALO_VISIBILITY_CONTRACTS
        if contract not in set(present_contracts)
    ]
    return {
        "action_type": LOCALO_VISIBILITY_REVIEW_ACTION_TYPE,
        "connector": "localo",
        "mode": "prepare_only",
        "source_metric_names": _unique(fact.name for fact in visibility_facts),
        "source_connectors": ["localo"],
        "allowed_contracts": present_contracts,
        "missing_read_contracts": missing_contracts,
        "review_steps": [
            "review_place_inventory",
            "review_local_rankings_aggregate",
            "review_reviews_aggregate",
            "block_gbp_and_competitor_claims_without_contract",
            "require_human_confirm_before_any_write",
        ],
        "blocked_claims": LOCALO_VISIBILITY_BLOCKED_CLAIMS,
        "apply_allowed": False,
        "destructive": False,
    }


def validate_localo_visibility_review_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("connector") != "localo":
        errors.append("local_visibility_task requires connector=localo.")
    if payload.get("mode") != "prepare_only":
        errors.append("local_visibility_task requires mode=prepare_only.")
    if not isinstance(payload.get("source_metric_names"), list):
        errors.append("local_visibility_task requires source_metric_names list.")
    if not isinstance(payload.get("allowed_contracts"), list):
        errors.append("local_visibility_task requires allowed_contracts list.")
    if not isinstance(payload.get("missing_read_contracts"), list):
        errors.append("local_visibility_task requires missing_read_contracts list.")
    if not isinstance(payload.get("review_steps"), list):
        errors.append("local_visibility_task requires review_steps list.")
    if not isinstance(payload.get("blocked_claims"), list):
        errors.append("local_visibility_task requires blocked_claims list.")
    if payload.get("apply_allowed") is not False:
        errors.append("local_visibility_task must keep apply_allowed=false.")
    if payload.get("destructive") is not False:
        errors.append("local_visibility_task must be non-destructive.")
    return errors


def _unique(items: Iterable[str]) -> list[str]:
    unique_items: list[str] = []
    for item in items:
        if item and item not in unique_items:
            unique_items.append(item)
    return unique_items
