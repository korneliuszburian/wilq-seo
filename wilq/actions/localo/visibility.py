from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from wilq.actions.metric_utils import metric_sentence, prioritize_action_metrics
from wilq.actions.validation_copy import (
    missing,
    no_api_write,
    no_destructive_change,
    no_write,
    wrong,
)
from wilq.briefing.localo_labels import localo_metric_fact_label
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MetricFact,
    OpportunityDomain,
)

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


def localo_visibility_review_action(
    *,
    localo_metrics: list[MetricFact],
    localo_visibility_payload: dict[str, Any],
    metric_sentence: str,
) -> ActionObject:
    return ActionObject(
        id=LOCALO_VISIBILITY_REVIEW_ACTION_ID,
        title="Przygotuj przegląd widoczności lokalnej Localo",
        domain=OpportunityDomain.localo,
        connector="localo",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=list(dict.fromkeys(fact.evidence_id for fact in localo_metrics)),
        metrics=localo_metrics,
        human_diagnosis=(
            "Localo ma agregaty miejsc, fraz, widoczności i recenzji z odczytu danych. "
            f"{metric_sentence}. To wystarcza do sprawdzenia lokalnej "
            "widoczności, ale nie do twierdzeń o GBP, konkurencji ani poprawie wyniku."
        ),
        recommended_reason=(
            "W widoku Localo przygotuj przegląd agregatów i zostaw wyniki profilu firmy, "
            "zapis zmian i poprawę widoczności zablokowane do czasu osobnych kontraktów Localo."
        ),
        payload=localo_visibility_payload,
        validation_status="not_validated",
        created_by="system_metric_seed",
    )


def localo_visibility_review_action_from_metric_facts(
    *, localo_facts: list[MetricFact], localo_visibility_payload: dict[str, Any]
) -> ActionObject:
    metrics = prioritize_action_metrics(
        localo_facts,
        required_names={
            "localo_active_place_count",
            "localo_tracked_keyword_count",
            "localo_avg_visibility_current",
            "localo_reviews_count",
        },
    )[:10]
    return localo_visibility_review_action(
        localo_metrics=metrics,
        localo_visibility_payload=localo_visibility_payload,
        metric_sentence=metric_sentence(metrics),
    )


def localo_action_metric_facts(
    *,
    facts: list[MetricFact],
    refresh_runs: Iterable[ConnectorRefreshRun],
    metric_facts_by_evidence_ids: Callable[[list[str]], list[MetricFact]],
    is_probe_only_fact: Callable[[MetricFact], bool],
) -> list[MetricFact]:
    value_facts = [fact for fact in facts if not is_probe_only_fact(fact)]
    if value_facts:
        return value_facts
    for run in refresh_runs:
        if run.status != ConnectorRefreshStatus.completed or not run.vendor_data_collected:
            continue
        facts_by_evidence = metric_facts_by_evidence_ids(run.evidence_ids)
        value_facts = [
            fact
            for fact in facts_by_evidence
            if fact.source_connector == "localo" and not is_probe_only_fact(fact)
        ]
        if value_facts:
            return value_facts
    return []
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
    subject = "Przegląd widoczności lokalnej"
    if payload.get("connector") != "localo":
        errors.append(wrong(subject, "dotyczy tylko Localo"))
    if payload.get("mode") != "prepare_only":
        errors.append(wrong(subject, "musi pozostać etapem przygotowania"))
    if not isinstance(payload.get("source_metric_names"), list):
        errors.append(missing(subject, "listy odczytanych metryk"))
    if not isinstance(payload.get("allowed_contracts"), list):
        errors.append(missing(subject, "listy dostępnych odczytów"))
    if not isinstance(payload.get("missing_read_contracts"), list):
        errors.append(missing(subject, "listy brakujących odczytów"))
    if not isinstance(payload.get("review_steps"), list):
        errors.append(missing(subject, "listy kroków sprawdzenia"))
    if not isinstance(payload.get("blocked_claims"), list):
        errors.append(missing(subject, "listy zablokowanych obietnic"))
    preview_items = payload.get("payload_preview")
    if not isinstance(preview_items, list) or not preview_items:
        errors.append(missing(subject, "podglądu sprawdzenia"))
    elif not all(isinstance(item, dict) for item in preview_items):
        errors.append(wrong(f"{subject}, podgląd", "ma nieprawidłową strukturę"))
    else:
        for preview in preview_items:
            if preview.get("preview_contract") != LOCALO_VISIBILITY_REVIEW_PREVIEW_CONTRACT:
                errors.append(missing(f"{subject}, podgląd", "poprawnego kontraktu"))
            if not isinstance(preview.get("metric_snapshot"), dict):
                errors.append(missing(f"{subject}, podgląd", "podsumowania metryk"))
            if preview.get("metric_snapshot") and not isinstance(
                preview.get("metric_snapshot_labels"), dict
            ):
                errors.append(missing(f"{subject}, podgląd", "etykiet widocznych metryk"))
            if not isinstance(preview.get("required_validation"), list):
                errors.append(missing(f"{subject}, podgląd", "listy wymaganych sprawdzeń"))
            if not isinstance(preview.get("evidence_ids"), list):
                errors.append(missing(f"{subject}, podgląd", "dowodów w WILQ"))
            if preview.get("api_mutation_ready") is not False:
                errors.append(no_api_write(f"{subject}, podgląd"))
            if preview.get("apply_allowed") is not False:
                errors.append(no_write(f"{subject}, podgląd"))
            if preview.get("destructive") is not False:
                errors.append(no_destructive_change(f"{subject}, podgląd"))
    if payload.get("apply_allowed") is not False:
        errors.append(no_write(subject))
    if payload.get("destructive") is not False:
        errors.append(no_destructive_change(subject))
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
            labels[fact.name] = _localo_action_metric_label(fact.name)
    return labels


def _localo_action_metric_label(metric_name: str) -> str:
    if metric_name == "localo_reviews_count":
        return "opinie Localo"
    return localo_metric_fact_label(metric_name)


def _unique(items: Iterable[str]) -> list[str]:
    unique_items: list[str] = []
    for item in items:
        if item and item not in unique_items:
            unique_items.append(item)
    return unique_items


def _ordered_contracts(items: Iterable[str]) -> list[str]:
    present = set(items)
    return [contract for contract in LOCALO_VISIBILITY_CONTRACTS if contract in present]
