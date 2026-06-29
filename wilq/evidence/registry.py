from __future__ import annotations

from wilq.connectors.registry import list_connector_statuses
from wilq.schemas import ConnectorRefreshRun, Evidence, FreshnessState
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store

METRIC_EVIDENCE_CONNECTORS = (
    "google_ads",
    "google_search_console",
    "google_analytics_4",
    "google_merchant_center",
    "ahrefs",
    "localo",
    "wordpress_ekologus",
    "wordpress_sklep",
    "linkedin",
    "facebook",
    "openai_codex",
)


def connector_evidence_id(connector_id: str) -> str:
    return f"ev_connector_{connector_id}_status"


def refresh_run_evidence_id(run_id: str) -> str:
    return f"ev_refresh_{run_id}"


def list_evidence() -> list[Evidence]:
    connector_evidence = [
        Evidence(
            id=connector_evidence_id(connector.id),
            source_connector=connector.id,
            source_type="connector_status",
            source_id=connector.id,
            freshness=connector.freshness,
            summary=_connector_summary(
                connector.id,
                connector.configured,
                connector.missing_credentials,
            ),
            raw_ref=None,
        )
        for connector in list_connector_statuses()
    ]
    refresh_evidence = [
        _refresh_run_evidence(run) for run in local_state_store().list_connector_refresh_runs()
    ]
    known_evidence_ids = {evidence.id for evidence in [*connector_evidence, *refresh_evidence]}
    metric_evidence = [
        evidence for evidence in _metric_fact_evidence() if evidence.id not in known_evidence_ids
    ]
    return [*connector_evidence, *refresh_evidence, *metric_evidence]


def list_evidence_by_ids(evidence_ids: list[str]) -> list[Evidence]:
    requested_ids = list(dict.fromkeys(evidence_ids))
    if not requested_ids:
        return []
    requested_id_set = set(requested_ids)
    evidence_by_id: dict[str, Evidence] = {}

    for connector in list_connector_statuses():
        evidence_id = connector_evidence_id(connector.id)
        if evidence_id not in requested_id_set:
            continue
        evidence_by_id[evidence_id] = Evidence(
            id=evidence_id,
            source_connector=connector.id,
            source_type="connector_status",
            source_id=connector.id,
            freshness=connector.freshness,
            summary=_connector_summary(
                connector.id,
                connector.configured,
                connector.missing_credentials,
            ),
            raw_ref=None,
        )

    for run in local_state_store().list_connector_refresh_runs():
        evidence_id = refresh_run_evidence_id(run.id)
        if evidence_id not in requested_id_set:
            continue
        evidence_by_id[evidence_id] = _refresh_run_evidence(run)

    missing_metric_evidence_ids = [
        evidence_id for evidence_id in requested_ids if evidence_id not in evidence_by_id
    ]
    for evidence in _metric_fact_evidence_for_ids(missing_metric_evidence_ids):
        evidence_by_id.setdefault(evidence.id, evidence)

    return [
        evidence_by_id[evidence_id]
        for evidence_id in requested_ids
        if evidence_id in evidence_by_id
    ]


def get_evidence(evidence_id: str) -> Evidence | None:
    evidence = list_evidence_by_ids([evidence_id])
    return evidence[0] if evidence else None


def _metric_fact_evidence_for_ids(evidence_ids: list[str]) -> list[Evidence]:
    facts_by_evidence_id: dict[str, list[str]] = {}
    connector_by_evidence_id: dict[str, str] = {}
    for fact in metric_store().list_metric_facts_by_evidence_ids(evidence_ids):
        facts_by_evidence_id.setdefault(fact.evidence_id, []).append(fact.name)
        connector_by_evidence_id.setdefault(fact.evidence_id, fact.source_connector)
    return _metric_fact_evidence_from_groups(facts_by_evidence_id, connector_by_evidence_id)


def _connector_summary(
    connector_id: str,
    configured: bool,
    missing_credentials: list[str],
) -> str:
    if configured:
        return (
            f"Connector {connector_id} has required credential names available. "
            "No external API refresh has been run yet."
        )
    return (
        f"Connector {connector_id} is missing credential names: "
        f"{', '.join(missing_credentials)}. No secret values are exposed."
    )


def _refresh_run_evidence(run: ConnectorRefreshRun) -> Evidence:
    return Evidence(
        id=refresh_run_evidence_id(run.id),
        source_connector=run.connector_id,
        source_type="connector_refresh_run",
        source_id=run.id,
        collected_at=run.completed_at or run.started_at,
        freshness=FreshnessState(
            state="fresh" if run.status == "completed" else "missing",
            checked_at=run.completed_at or run.started_at,
            notes=run.summary,
        ),
        summary=run.summary,
        raw_ref=f"connector_refresh_runs:{run.id}",
    )


def _metric_fact_evidence() -> list[Evidence]:
    facts_by_evidence_id: dict[str, list[str]] = {}
    connector_by_evidence_id: dict[str, str] = {}
    metric_facts_by_connector = metric_store().list_metric_facts_by_connector(
        list(METRIC_EVIDENCE_CONNECTORS),
        limit_per_connector=500,
    )
    for facts in metric_facts_by_connector.values():
        for fact in facts:
            facts_by_evidence_id.setdefault(fact.evidence_id, []).append(fact.name)
            connector_by_evidence_id.setdefault(fact.evidence_id, fact.source_connector)
    return _metric_fact_evidence_from_groups(facts_by_evidence_id, connector_by_evidence_id)


def _metric_fact_evidence_from_groups(
    facts_by_evidence_id: dict[str, list[str]],
    connector_by_evidence_id: dict[str, str],
) -> list[Evidence]:
    evidence_items: list[Evidence] = []
    for evidence_id, fact_names in sorted(facts_by_evidence_id.items()):
        unique_fact_names = sorted(set(fact_names))
        source_connector = connector_by_evidence_id[evidence_id]
        evidence_items.append(
            Evidence(
                id=evidence_id,
                source_connector=source_connector,
                source_type="metric_fact_store",
                source_id=evidence_id,
                freshness=FreshnessState(
                    state="unknown",
                    notes=(
                        "Metric fact evidence is retained in DuckDB, but the original "
                        "connector refresh run is not present in local state."
                    ),
                ),
                summary=(
                    f"Metric fact evidence for connector {source_connector}: "
                    f"{', '.join(unique_fact_names[:8])}."
                ),
                raw_ref=f"metric_facts:{evidence_id}",
            )
        )
    return evidence_items
