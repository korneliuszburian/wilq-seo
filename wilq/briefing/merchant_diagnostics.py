from __future__ import annotations

from collections.abc import Iterable

from wilq.actions.service import list_actions
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionObject,
    ActionRisk,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MerchantDiagnosticSection,
    MerchantDiagnosticsResponse,
    MerchantIssueCluster,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
)
from wilq.storage.metric_store import metric_store

MERCHANT_CONNECTOR_ID = "google_merchant_center"
MERCHANT_METRIC_FACT_LIMIT = 2000
MERCHANT_HEALTH_METRIC_NAMES = {
    "total_products",
    "active_products",
    "disapproved_products",
    "expiring_products",
    "item_level_issue_count",
    "merchant_action_issue_count",
}


def build_merchant_diagnostics() -> MerchantDiagnosticsResponse:
    connector = get_connector_status(MERCHANT_CONNECTOR_ID)
    if connector is None:
        raise RuntimeError("Merchant Center connector is not registered.")
    latest_refresh = _latest_merchant_refresh()
    metric_facts = metric_store().list_metric_facts(
        connector_id=MERCHANT_CONNECTOR_ID,
        limit=MERCHANT_METRIC_FACT_LIMIT,
    )
    live_data_available = bool(metric_facts) and (
        latest_refresh is None
        or (
            latest_refresh.status == ConnectorRefreshStatus.completed
            and latest_refresh.vendor_data_collected
        )
    )
    trusted_facts = metric_facts if live_data_available else []
    tactical_items = [
        item
        for item in build_tactical_queue().items
        if item.domain == OpportunityDomain.merchant
    ]
    action_ids = _merchant_action_ids(list_actions())
    issue_clusters = _merchant_issue_clusters(trusted_facts, action_ids)
    sections = [
        _feed_health_section(latest_refresh, trusted_facts, action_ids),
        _issue_queue_section(
            latest_refresh,
            trusted_facts,
            tactical_items,
            issue_clusters,
            action_ids,
        ),
        _product_action_safety_section(latest_refresh, trusted_facts, tactical_items, action_ids),
    ]
    return MerchantDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector=connector,
        latest_refresh=latest_refresh,
        live_data_available=live_data_available,
        product_count=_numeric_metric_or_refresh_summary(
            trusted_facts,
            latest_refresh,
            "total_products",
        ),
        issue_count=_numeric_metric_or_refresh_summary(
            trusted_facts,
            latest_refresh,
            "item_level_issue_count",
        ),
        issue_clusters=issue_clusters,
        sections=sections,
        evidence_ids=_unique(
            evidence_id for section in sections for evidence_id in section.evidence_ids
        ),
        action_ids=_unique(action_id for section in sections for action_id in section.action_ids),
        blocker_count=sum(1 for section in sections if section.status == "blocked"),
    )


def _latest_merchant_refresh() -> ConnectorRefreshRun | None:
    runs = list_connector_refresh_runs(connector_id=MERCHANT_CONNECTOR_ID)
    return runs[0] if runs else None


def _merchant_action_ids(actions: list[ActionObject]) -> list[str]:
    return [action.id for action in actions if action.connector == MERCHANT_CONNECTOR_ID]


def _feed_health_section(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    action_ids: list[str],
) -> MerchantDiagnosticSection:
    if not facts:
        return MerchantDiagnosticSection(
            id="merchant_feed_health",
            title="Merchant Center: brak aktualnych metryk feedu",
            status="blocked",
            summary=_merchant_blocker_reason(latest_refresh),
            diagnosis=(
                "WILQ nie ma aktualnych Merchant metric facts, więc nie może ocenić "
                "liczby produktów, issue count ani stanu feedu."
            ),
            next_step=(
                "Uruchom odczyt Merchant w trybie vendor_read i dopiero potem "
                "twórz kolejkę feedu."
            ),
            source_connectors=[MERCHANT_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            action_ids=action_ids,
            blocked_claims=["feed health", "product approval", "issue count"],
            risk=ActionRisk.medium,
        )

    product_facts = _merchant_health_metric_facts(latest_refresh, facts)
    return MerchantDiagnosticSection(
        id="merchant_feed_health",
        title="Merchant Center: stan produktów i feedu",
        status="ready",
        summary=_metric_sentence(product_facts or facts),
        diagnosis=(
            "WILQ ma metryki Merchant z odczytu. Można ocenić skalę feedu i liczbę "
            "zgłoszonych problemów, ale nie wolno twierdzić, że produkt został naprawiony bez "
            "ActionObject, walidacji i audytu."
        ),
        next_step="Przejdź do kolejki problemów i grupuj je po typie oraz atrybucie.",
        source_connectors=[MERCHANT_CONNECTOR_ID],
        evidence_ids=_unique(fact.evidence_id for fact in product_facts or facts),
        metric_facts=(product_facts or facts)[:10],
        action_ids=action_ids,
        blocked_claims=["approval restored", "revenue recovered", "profit uplift"],
        risk=ActionRisk.medium,
    )


def _issue_queue_section(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    issue_clusters: list[MerchantIssueCluster],
    action_ids: list[str],
) -> MerchantDiagnosticSection:
    issue_facts = [
        fact
        for fact in facts
        if fact.name == "issue_product_count" or "issue_type" in fact.dimensions
    ]
    if not issue_facts and not tactical_items:
        return MerchantDiagnosticSection(
            id="merchant_issue_queue",
            title="Merchant Center: brak kolejki problemów feedu",
            status="missing",
            summary="Brak metryk problemów i pozycji kolejki Merchant.",
            diagnosis=(
                "Nie ma bezpiecznego materiału do kolejki feed triage. WILQ musi "
                "najpierw zebrać typ problemu, atrybut albo metryki statusu produktu."
            ),
            next_step="Odśwież Merchant vendor_read i sprawdź aggregateProductStatuses.",
            source_connectors=[MERCHANT_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            action_ids=action_ids,
            blocked_claims=["feed fix candidate", "product-level fix"],
            risk=ActionRisk.medium,
        )

    cluster_count = _pl_count(
        len(issue_clusters),
        "grupę problemów feedu",
        "grupy problemów feedu",
        "grup problemów feedu",
    )
    tactical_count = _pl_count(
        len(tactical_items),
        "taktykę Merchant",
        "taktyki Merchant",
        "taktyk Merchant",
    )
    issue_fact_count = _pl_count(
        len(issue_facts),
        "metrykę problemu",
        "metryki problemu",
        "metryk problemu",
    )

    return MerchantDiagnosticSection(
        id="merchant_issue_queue",
        title="Merchant Center: kolejka problemów feedu",
        status="ready",
        summary=(
            f"WILQ ma {cluster_count}, {tactical_count} i {issue_fact_count}. "
            "Liczby w grupach są wystąpieniami problemu w raportach, nie gwarancją "
            "unikalnych produktów."
        ),
        diagnosis=(
            "Najbezpieczniejsza praca dla marketera to review problemów po typie "
            "problemu, atrybucie i kontekście widoczności. WILQ nadal nie pokazuje "
            "surowych list produktów."
        ),
        next_step=(
            "Otwórz ActionObject `act_review_merchant_feed_issues` i przygotuj "
            "kolejkę przeglądu."
        ),
        source_connectors=[MERCHANT_CONNECTOR_ID],
        evidence_ids=_unique(
            [
                *(fact.evidence_id for fact in issue_facts),
                *(evidence_id for item in tactical_items for evidence_id in item.evidence_ids),
            ]
        ),
        metric_facts=issue_facts[:10],
        tactical_items=tactical_items[:6],
        action_ids=action_ids,
        blocked_claims=["automatic feed edit", "primary feed overwrite", "approval restored"],
        risk=ActionRisk.medium,
    )


def _merchant_issue_clusters(
    facts: list[MetricFact],
    action_ids: list[str],
) -> list[MerchantIssueCluster]:
    issue_facts = [
        fact
        for fact in facts
        if fact.name == "issue_product_count" and fact.dimensions.get("issue_type")
    ]
    grouped: dict[tuple[str, str, str, str, str, str], list[MetricFact]] = {}
    for fact in issue_facts:
        dimensions = fact.dimensions
        key = (
            dimensions.get("issue_type", "unknown_issue"),
            dimensions.get("affected_attribute", ""),
            dimensions.get("country", ""),
            dimensions.get("reporting_context", ""),
            dimensions.get("severity", "UNKNOWN"),
            dimensions.get("resolution", ""),
        )
        grouped.setdefault(key, []).append(fact)

    clusters: list[MerchantIssueCluster] = []
    action_id = action_ids[0] if action_ids else None
    for key, group_facts in grouped.items():
        issue_type, affected_attribute, country, reporting_context, severity, resolution = key
        product_count = sum(
            int(fact.value)
            for fact in group_facts
            if isinstance(fact.value, int | float)
        )
        clusters.append(
            MerchantIssueCluster(
                id=(
                    f"merchant_issue_{_stable_slug(country or 'global')}_"
                    f"{_stable_slug(severity)}_{_stable_slug(issue_type)}_"
                    f"{_stable_slug(affected_attribute or 'attribute_unknown')}_"
                    f"{_stable_slug(reporting_context or 'all_contexts')}_"
                    f"{_stable_slug(resolution or 'resolution_unknown')}"
                ),
                issue_type=issue_type,
                severity=severity,
                resolution=resolution or None,
                affected_attribute=affected_attribute or None,
                country=country or None,
                reporting_context=reporting_context or None,
                product_count=product_count,
                sample_unavailable_reason=(
                    "Obecny kontrakt odczytu Merchant zwraca wymiary problemu i liczbę "
                    "wystąpień problemu w raportach, ale nie zwraca przykładowych ID "
                    "produktów ani tytułów."
                ),
                source_connectors=[MERCHANT_CONNECTOR_ID],
                evidence_ids=_unique(fact.evidence_id for fact in group_facts),
                blocked_claims=["approval restored", "revenue recovered", "automatic feed edit"],
                action_id=action_id,
                risk=_merchant_cluster_risk(severity, resolution),
                next_step=(
                    "Przejrzyj tę grupę problemu w `act_review_merchant_feed_issues`; "
                    "najpierw przygotuj podgląd payloadu, bez automatycznej zmiany feedu."
                ),
            )
        )
    return sorted(
        clusters,
        key=lambda cluster: (
            _merchant_severity_rank(cluster.severity),
            -cluster.product_count,
            cluster.issue_type,
        ),
    )


def _merchant_cluster_risk(severity: str, resolution: str | None) -> ActionRisk:
    if severity == "DISAPPROVED":
        return ActionRisk.high
    if resolution == "MERCHANT_ACTION":
        return ActionRisk.medium
    return ActionRisk.low


def _merchant_severity_rank(severity: str) -> int:
    return {"DISAPPROVED": 0, "DEMOTED": 1, "NOT_IMPACTED": 2}.get(severity, 3)


def _stable_slug(value: str) -> str:
    lowered = value.lower()
    chars = [char if char.isalnum() else "_" for char in lowered]
    return "_".join("".join(chars).split("_")) or "unknown"


def _product_action_safety_section(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> MerchantDiagnosticSection:
    return MerchantDiagnosticSection(
        id="merchant_action_safety",
        title="Merchant Center: bezpieczne akcje",
        status="ready" if facts or tactical_items else "blocked",
        summary=(
            "Akcje Merchant pozostają w trybie przygotowania do czasu walidacji "
            "payloadu i audytu."
        ),
        diagnosis=(
            "Zmiany feedu lub produktów mogą wpływać na widoczność i sprzedaż. WILQ "
            "może przygotować kolejkę przeglądu, ale nie może zmieniać głównego feedu ani "
            "twierdzić, że naprawił produkty bez obsługi apply."
        ),
        next_step=(
            "Waliduj ActionObject, pokaż podgląd payloadu i zatrzymaj apply "
            "do jawnego potwierdzenia."
        ),
        source_connectors=[MERCHANT_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        action_ids=action_ids,
        blocked_claims=["feed write", "product data mutation", "automatic approval fix"],
        risk=ActionRisk.medium,
    )


def _facts_by_names(facts: list[MetricFact], names: set[str]) -> list[MetricFact]:
    return [fact for fact in facts if fact.name in names]


def _merchant_health_metric_facts(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
) -> list[MetricFact]:
    summary_facts = _metric_facts_from_refresh_summary(
        latest_refresh,
        MERCHANT_HEALTH_METRIC_NAMES,
    )
    if summary_facts:
        return summary_facts
    return _dedupe_metric_facts(_facts_by_names(facts, MERCHANT_HEALTH_METRIC_NAMES))


def _metric_facts_from_refresh_summary(
    latest_refresh: ConnectorRefreshRun | None,
    names: set[str],
) -> list[MetricFact]:
    if latest_refresh is None:
        return []
    evidence_id = (
        latest_refresh.evidence_ids[-1]
        if latest_refresh.evidence_ids
        else connector_evidence_id(MERCHANT_CONNECTOR_ID)
    )
    facts: list[MetricFact] = []
    for name in names:
        value = latest_refresh.metric_summary.get(name)
        if value is None:
            continue
        facts.append(
            MetricFact(
                name=name,
                value=value,
                period="connector_refresh",
                source_connector=MERCHANT_CONNECTOR_ID,
                evidence_id=evidence_id,
            )
        )
    return sorted(facts, key=lambda fact: fact.name)


def _dedupe_metric_facts(facts: list[MetricFact]) -> list[MetricFact]:
    seen: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
    result: list[MetricFact] = []
    for fact in facts:
        key = (fact.name, tuple(sorted(fact.dimensions.items())))
        if key in seen:
            continue
        seen.add(key)
        result.append(fact)
    return result


def _numeric_metric(facts: list[MetricFact], name: str) -> int | None:
    for fact in facts:
        if fact.name == name and isinstance(fact.value, int | float):
            return int(fact.value)
    return None


def _numeric_metric_or_refresh_summary(
    facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
    name: str,
) -> int | None:
    value = _numeric_metric(facts, name)
    if value is not None:
        return value
    if latest_refresh is None:
        return None
    summary_value = latest_refresh.metric_summary.get(name)
    if isinstance(summary_value, int | float):
        return int(summary_value)
    return None


def _merchant_blocker_reason(latest_refresh: ConnectorRefreshRun | None) -> str:
    if latest_refresh and latest_refresh.errors:
        return latest_refresh.errors[0]
    if latest_refresh and latest_refresh.summary:
        return latest_refresh.summary
    return "Brak wykonanego Merchant vendor_read."


def _refresh_or_connector_evidence_ids(latest_refresh: ConnectorRefreshRun | None) -> list[str]:
    if latest_refresh:
        return latest_refresh.evidence_ids
    return [connector_evidence_id(MERCHANT_CONNECTOR_ID)]


def _metric_sentence(facts: list[MetricFact]) -> str:
    samples = ", ".join(f"{fact.name}={fact.value}" for fact in facts[:6])
    return f"Metryki Merchant: {samples}."


def _pl_count(count: int, one: str, few: str, many: str) -> str:
    absolute = abs(count)
    last_digit = absolute % 10
    last_two_digits = absolute % 100
    if absolute == 1:
        form = one
    elif 2 <= last_digit <= 4 and not 12 <= last_two_digits <= 14:
        form = few
    else:
        form = many
    return f"{count} {form}"


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values
