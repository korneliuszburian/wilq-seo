from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from wilq.briefing.localo_labels import localo_metric_fact_label
from wilq.schemas import MetricFact

LOCALO_VISIBILITY_REVIEW_ACTION_ID = "act_review_localo_visibility_facts"
LOCALO_VISIBILITY_REVIEW_ACTION_TYPE = "local_visibility_task"
LOCALO_VISIBILITY_REVIEW_PREVIEW_CONTRACT = "local_visibility_review_preview_v1"
LOCALO_VISIBILITY_CONTRACTS = [
    "place_inventory",
    "local_rankings",
    "gbp_visibility",
    "competitor_visibility",
    "reviews",
    "local_tasks",
]
LOCALO_VISIBILITY_REVIEW_STEPS = [
    "review_place_inventory",
    "review_local_rankings_aggregate",
    "review_reviews_aggregate",
    "require_human_confirm_before_any_write",
]
LOCALO_CLAIMS_BY_MISSING_CONTRACT = {
    "local_rankings": "lokalne pozycje",
    "gbp_visibility": "wyniki profilu firmy w Google",
    "competitor_visibility": "widoczność konkurencji",
    "reviews": "tempo opinii",
    "local_tasks": "ukończone zadanie lokalne",
}


def localo_visibility_review_payload_from_metric_facts(
    facts: list[MetricFact],
) -> dict[str, Any] | None:
    visibility_facts = [fact for fact in facts if fact.source_connector == "localo"]
    if not visibility_facts:
        return None
    present_contracts = _ordered_contracts(
        str(fact.dimensions.get("contract", ""))
        for fact in visibility_facts
        if fact.dimensions.get("contract")
    )
    missing_contracts = [
        contract
        for contract in LOCALO_VISIBILITY_CONTRACTS
        if contract not in set(present_contracts)
    ]
    blocked_claims = _blocked_claims_for_missing_contracts(missing_contracts)
    review_steps = _review_steps_for_missing_contracts(missing_contracts)
    blocked_scope = _blocked_scope_sentence(missing_contracts)
    source_metric_names = _unique(fact.name for fact in visibility_facts)
    evidence_ids = _unique(fact.evidence_id for fact in visibility_facts)
    return {
        "action_type": LOCALO_VISIBILITY_REVIEW_ACTION_TYPE,
        "connector": "localo",
        "mode": "prepare_only",
        "source_metric_names": source_metric_names,
        "source_connectors": ["localo"],
        "allowed_contracts": present_contracts,
        "missing_read_contracts": missing_contracts,
        "review_steps": review_steps,
        "blocked_claims": blocked_claims,
        "preview_contract": LOCALO_VISIBILITY_REVIEW_PREVIEW_CONTRACT,
        "payload_preview": [
            {
                "id": "localo_visibility_review",
                "preview_contract": LOCALO_VISIBILITY_REVIEW_PREVIEW_CONTRACT,
                "operation_type": "local_visibility_review",
                "source_metric_names": source_metric_names,
                "metric_snapshot": _metric_snapshot(visibility_facts),
                "metric_snapshot_labels": _metric_snapshot_labels(visibility_facts),
                "allowed_contracts": present_contracts,
                "missing_read_contracts": missing_contracts,
                "reason": (
                    "Podgląd agregatów Localo do sprawdzenia. WILQ może "
                    f"sprawdzić wskazane kontrakty, ale blokuje {blocked_scope} "
                    "bez osobnych danych źródłowych albo dowodu efektu."
                ),
                "required_validation": review_steps,
                "blocked_claims": blocked_claims,
                "evidence_ids": evidence_ids,
                "api_mutation_ready": False,
                "apply_allowed": False,
                "destructive": False,
            }
        ],
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
    preview_items = payload.get("payload_preview")
    if not isinstance(preview_items, list) or not preview_items:
        errors.append("local_visibility_task requires payload_preview list.")
    elif not all(isinstance(item, dict) for item in preview_items):
        errors.append("local_visibility_task payload_preview items must be objects.")
    else:
        for preview in preview_items:
            if preview.get("preview_contract") != LOCALO_VISIBILITY_REVIEW_PREVIEW_CONTRACT:
                errors.append(
                    "local_visibility_task payload_preview requires "
                    f"{LOCALO_VISIBILITY_REVIEW_PREVIEW_CONTRACT}."
                )
            if not isinstance(preview.get("metric_snapshot"), dict):
                errors.append("local_visibility_task payload_preview requires metric_snapshot.")
            if preview.get("metric_snapshot") and not isinstance(
                preview.get("metric_snapshot_labels"), dict
            ):
                errors.append(
                    "local_visibility_task payload_preview requires "
                    "metric_snapshot_labels for visible metrics."
                )
            if not isinstance(preview.get("required_validation"), list):
                errors.append(
                    "local_visibility_task payload_preview requires required_validation list."
                )
            if not isinstance(preview.get("evidence_ids"), list):
                errors.append("local_visibility_task payload_preview requires evidence_ids list.")
            if preview.get("api_mutation_ready") is not False:
                errors.append(
                    "local_visibility_task payload_preview must keep "
                    "api_mutation_ready=false."
                )
            if preview.get("apply_allowed") is not False:
                errors.append(
                    "local_visibility_task payload_preview must keep apply_allowed=false."
                )
            if preview.get("destructive") is not False:
                errors.append("local_visibility_task payload_preview must be non-destructive.")
    if payload.get("apply_allowed") is not False:
        errors.append("local_visibility_task must keep apply_allowed=false.")
    if payload.get("destructive") is not False:
        errors.append("local_visibility_task must be non-destructive.")
    return errors


def _blocked_claims_for_missing_contracts(missing_contracts: list[str]) -> list[str]:
    claims = [
        claim
        for contract, claim in LOCALO_CLAIMS_BY_MISSING_CONTRACT.items()
        if contract in missing_contracts
    ]
    claims.extend(["zapis zmian w profilu firmy", "poprawa widoczności lokalnej"])
    return _unique(claims)


def _review_steps_for_missing_contracts(missing_contracts: list[str]) -> list[str]:
    steps = list(LOCALO_VISIBILITY_REVIEW_STEPS)
    if "gbp_visibility" in missing_contracts or "competitor_visibility" in missing_contracts:
        steps.append("block_gbp_and_competitor_claims_without_contract")
    if "local_tasks" in missing_contracts:
        steps.append("block_local_tasks_without_contract")
    return steps


def _blocked_scope_sentence(missing_contracts: list[str]) -> str:
    missing_labels = [
        label
        for contract, label in {
            "local_rankings": "lokalne rankingi",
            "gbp_visibility": "profil firmy w Google",
            "competitor_visibility": "konkurencję",
            "reviews": "tempo opinii",
            "local_tasks": "lokalne zadania",
        }.items()
        if contract in missing_contracts
    ]
    labels = [*missing_labels, "zapis zmian w profilu firmy", "poprawę widoczności"]
    if len(labels) == 1:
        return labels[0]
    return f"{', '.join(labels[:-1])} i {labels[-1]}"


def _metric_snapshot(facts: list[MetricFact]) -> dict[str, int | float | str]:
    snapshot: dict[str, int | float | str] = {}
    for fact in facts:
        if fact.name not in snapshot:
            snapshot[fact.name] = fact.value
    return snapshot


def _metric_snapshot_labels(facts: list[MetricFact]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for fact in facts:
        if fact.name not in labels:
            labels[fact.name] = localo_metric_fact_label(fact.name)
    return labels


def _unique(items: Iterable[str]) -> list[str]:
    unique_items: list[str] = []
    for item in items:
        if item and item not in unique_items:
            unique_items.append(item)
    return unique_items


def _ordered_contracts(items: Iterable[str]) -> list[str]:
    present = set(items)
    return [contract for contract in LOCALO_VISIBILITY_CONTRACTS if contract in present]
