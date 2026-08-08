"""Decomposed localo_diagnostics shared implementation."""

from __future__ import annotations

from collections.abc import Iterable

from wilq.actions.localo.visibility import LOCALO_VISIBILITY_REVIEW_ACTION_ID
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import ConnectorRefreshRun, LocaloReadContractStatus, MetricFact

LOCALO_CONNECTOR_ID = "localo"


LOCALO_METRIC_FACT_LIMIT = 120


LOCALO_PROBE_METRIC_NAMES = {
    "access_token_present",
    "api",
    "authorization_code_supported",
    "mcp_initialize_status",
    "pkce_s256_supported",
}


LOCALO_VISIBILITY_READ_CONTRACTS = [
    "local_rankings",
    "gbp_visibility",
    "competitor_visibility",
    "reviews",
    "local_tasks",
]


LOCALO_CONTRACT_FACT_NAMES = {
    "place_inventory": {
        "localo_active_place_count",
        "localo_place_detail_count",
    },
    "local_rankings": {
        "localo_tracked_keyword_count",
        "localo_visibility_score_count",
        "localo_avg_visibility_current",
        "localo_avg_visibility_change",
        "localo_latest_grid_position_count",
        "localo_avg_latest_grid_position",
        "localo_keyword_volume_count",
        "localo_total_keyword_volume",
    },
    "reviews": {
        "localo_avg_rating",
        "localo_snapshot_reviews_count",
        "localo_reviews_count",
        "localo_reviews_replied_count",
        "localo_reviews_removed_count",
        "localo_review_reply_rate",
    },
    "gbp_visibility": {
        "localo_gbp_impressions_total",
        "localo_gbp_actions_total",
        "localo_gbp_metric_point_count",
    },
    "competitor_visibility": {
        "localo_competitor_count",
        "localo_favorite_competitor_count",
        "localo_competitor_change_count",
    },
}


LOCALO_CONTRACT_ORDER = [
    "place_inventory",
    "local_rankings",
    "gbp_visibility",
    "competitor_visibility",
    "reviews",
    "local_tasks",
]


LOCALO_BLOCKED_CLAIMS = [
    "lokalne rankingi",
    "wyniki profilu firmy w Google",
    "widoczności konkurencji",
    "poprawa widoczności lokalnej",
    "tempo nowych opinii",
]


LOCALO_KNOWLEDGE_CARD_IDS = ["card_localo_local_seo_playbook"]


LOCALO_EXPERT_RULE_IDS = ["local_visibility_v1", "local_reviews_v1"]


def _present_contracts(visibility_facts: list[MetricFact]) -> list[str]:
    fact_names = {fact.name for fact in visibility_facts}
    present = [
        contract
        for contract in LOCALO_CONTRACT_ORDER
        if contract in LOCALO_CONTRACT_FACT_NAMES
        and fact_names.intersection(LOCALO_CONTRACT_FACT_NAMES[contract])
    ]
    return present


def _missing_contract_ids(
    read_contract_statuses: list[LocaloReadContractStatus],
) -> list[str]:
    return [str(contract.id) for contract in read_contract_statuses if contract.status != "ready"]


def _localo_contract_evidence_kind(contract: str) -> str:
    labels = {
        "place_inventory": "miejsca i aktywne profile",
        "local_rankings": "agregaty fraz, widoczności i pozycji grid",
        "gbp_visibility": "widoczność profilu firmy w Google",
        "competitor_visibility": "porównanie lokalnych konkurentów",
        "reviews": "recenzje i odpowiedzi",
        "local_tasks": "lokalne zadania do wykonania",
    }
    return labels.get(contract, "zakres danych Localo do sprawdzenia")


def _localo_contracts_phrase(contracts: list[str]) -> str:
    labels = {
        "place_inventory": "miejsca i profile",
        "local_rankings": "lokalne pozycje i frazy",
        "gbp_visibility": "profil firmy w Google",
        "competitor_visibility": "lokalni konkurenci",
        "reviews": "opinie",
        "local_tasks": "zadania lokalne",
    }
    values = [labels.get(contract, "zakres danych Localo do sprawdzenia") for contract in contracts]
    if not values:
        return "żaden zakres danych Localo nie jest brakujący"
    if len(values) == 1:
        return values[0]
    return f"{', '.join(values[:-1])} i {values[-1]}"


def _localo_missing_contracts_phrase(contracts: list[str]) -> str:
    labels = {
        "place_inventory": "miejsca i profile",
        "local_rankings": "lokalne rankingi",
        "gbp_visibility": "profil firmy w Google",
        "competitor_visibility": "konkurencję",
        "reviews": "recenzje",
        "local_tasks": "zadania lokalne",
    }
    values = [labels.get(contract, "zakres danych Localo do sprawdzenia") for contract in contracts]
    if not values:
        return "żaden brakujący zakres danych Localo"
    if len(values) == 1:
        return values[0]
    return f"{', '.join(values[:-1])} i {values[-1]}"


def _localo_visibility_summary_with_contracts(
    *,
    visibility_facts: list[MetricFact],
    present_contracts: list[str],
    missing_contracts: list[str],
) -> str:
    ready_summary = (
        f"WILQ ma {_localo_aggregate_count_label(len(visibility_facts))} dla danych: "
        f"{_localo_contracts_phrase(present_contracts)}."
    )
    if not missing_contracts:
        return (
            f"{ready_summary} Żaden zakres Localo z obecnego kontraktu nie jest oznaczony "
            "jako brakujący."
        )
    return f"{ready_summary} Nadal brakuje: {_localo_contracts_phrase(missing_contracts)}."


def _blocked_claims_for_contract(contract: str) -> list[str]:
    claims_by_contract = {
        "local_rankings": ["lokalne rankingi", "poprawa widoczności lokalnej"],
        "gbp_visibility": [
            "wyniki profilu firmy w Google",
            "zapis zmian w profilu firmy",
            "poprawa widoczności lokalnej",
        ],
        "competitor_visibility": ["widoczności konkurencji", "poprawa widoczności lokalnej"],
        "reviews": ["tempo nowych opinii", "poprawa widoczności lokalnej"],
        "local_tasks": [
            "ukończone zadanie lokalne",
            "zapis zmian w profilu firmy",
            "poprawa widoczności lokalnej",
        ],
    }
    return claims_by_contract.get(contract, [])


def _localo_contract_next_step(contract: str, *, ready: bool) -> str:
    if ready:
        return "Użyj tych danych jako dowodu dla sprawdzenia Localo."
    next_steps = {
        "gbp_visibility": (
            "Dodaj odczyt widoczności profilu firmy w Google przed oceną tego profilu."
        ),
        "competitor_visibility": (
            "Dodaj odczyt widoczności konkurencji przed porównaniem konkurencji."
        ),
        "local_tasks": "Dodaj odczyt zadań lokalnych przed planem zadań lokalnych.",
        "local_rankings": "Dodaj odczyt lokalnych rankingów przed obietnicami o pozycjach.",
        "reviews": "Dodaj odczyt recenzji przed oceną tempa recenzji.",
        "place_inventory": "Dodaj odczyt miejsca i profile przed oceną profili.",
    }
    return next_steps.get(contract, "Dodaj odczyt danych Localo przed obietnicami.")


def _missing_visibility_contracts(present_contracts: list[str]) -> list[str]:
    present = set(present_contracts)
    return [contract for contract in LOCALO_VISIBILITY_READ_CONTRACTS if contract not in present]


def _blocked_claims_for_missing_contracts(missing_contracts: list[str]) -> list[str]:
    claims_by_contract = {
        "local_rankings": "lokalne rankingi",
        "gbp_visibility": "wyniki profilu firmy w Google",
        "competitor_visibility": "widoczności konkurencji",
        "reviews": "tempo nowych opinii",
        "local_tasks": "ukończone zadanie lokalne",
    }
    claims = [
        claim for contract, claim in claims_by_contract.items() if contract in missing_contracts
    ]
    claims.extend(["zapis zmian w profilu firmy", "poprawa widoczności lokalnej"])
    return _unique(claims)


def _localo_visibility_action_ids(visibility_facts: list[MetricFact]) -> list[str]:
    if not visibility_facts:
        return []
    return [LOCALO_VISIBILITY_REVIEW_ACTION_ID]


def _localo_visibility_tiles(
    visibility_facts: list[MetricFact],
    missing_contracts: list[str],
) -> dict[str, int | float | str]:
    return {
        "dane Localo": len(visibility_facts),
        "miejsca": _int_fact_value(visibility_facts, "localo_active_place_count"),
        "frazy": _int_fact_value(visibility_facts, "localo_tracked_keyword_count"),
        "średnia widoczność": _float_fact_value(
            visibility_facts,
            "localo_avg_visibility_current",
        ),
        "recenzje": _int_fact_value(visibility_facts, "localo_reviews_count"),
        "brakujące dane": len(missing_contracts),
    }


def _int_fact_value(visibility_facts: list[MetricFact], name: str) -> int:
    value = _fact_value(visibility_facts, name)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _float_fact_value(visibility_facts: list[MetricFact], name: str) -> float:
    value = _fact_value(visibility_facts, name)
    if isinstance(value, int | float):
        return round(float(value), 2)
    return 0.0


def _localo_aggregate_count_label(count: int) -> str:
    if count == 1:
        return "1 agregat Localo"
    if 2 <= count % 10 <= 4 and count % 100 not in {12, 13, 14}:
        return f"{count} agregaty Localo"
    return f"{count} agregatów Localo"


def _fact_value(visibility_facts: list[MetricFact], name: str) -> int | float | str | None:
    for fact in visibility_facts:
        if fact.name == name:
            return fact.value
    return None


def _refresh_or_connector_evidence_ids(run: ConnectorRefreshRun | None) -> list[str]:
    if run and run.evidence_ids:
        return run.evidence_ids
    return [connector_evidence_id(LOCALO_CONNECTOR_ID)]


def _int_or_none(value: float | int | str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: float | int | str | None) -> bool | None:
    numeric_value = _int_or_none(value)
    if numeric_value is None:
        return None
    return bool(numeric_value)


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered
