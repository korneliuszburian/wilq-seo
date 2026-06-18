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
MERCHANT_METRIC_FACT_LIMIT = 240


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
        product_count=_numeric_metric(trusted_facts, "total_products"),
        issue_count=_numeric_metric(trusted_facts, "item_level_issue_count"),
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
            title="Merchant Center: brak live feed facts",
            status="blocked",
            summary=_merchant_blocker_reason(latest_refresh),
            diagnosis=(
                "WILQ nie ma aktualnych Merchant metric facts, więc nie może ocenić "
                "liczby produktów, issue count ani stanu feedu."
            ),
            next_step="Uruchom read-only Merchant vendor_read i dopiero potem twórz feed queue.",
            source_connectors=[MERCHANT_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            action_ids=action_ids,
            blocked_claims=["feed health", "product approval", "issue count"],
            risk=ActionRisk.medium,
        )

    product_facts = _facts_by_names(
        facts,
        {
            "total_products",
            "active_products",
            "disapproved_products",
            "expiring_products",
            "item_level_issue_count",
            "merchant_action_issue_count",
        },
    )
    return MerchantDiagnosticSection(
        id="merchant_feed_health",
        title="Merchant Center: feed/product health",
        status="ready",
        summary=_metric_sentence(product_facts or facts),
        diagnosis=(
            "WILQ ma read-only Merchant facts. Można ocenić skalę feedu i issue "
            "counts, ale nie wolno twierdzić, że produkt został naprawiony bez "
            "ActionObject, walidacji i audytu."
        ),
        next_step="Przejdź do issue queue i grupuj problemy po issue_type oraz affected_attribute.",
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
            title="Merchant Center: brak issue queue",
            status="missing",
            summary="Brak issue facts i Merchant tactical queue items.",
            diagnosis=(
                "Nie ma bezpiecznego materiału do kolejki feed triage. WILQ musi "
                "najpierw zebrać issue_type, affected_attribute albo product status facts."
            ),
            next_step="Odśwież Merchant vendor_read i sprawdź aggregateProductStatuses.",
            source_connectors=[MERCHANT_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            action_ids=action_ids,
            blocked_claims=["feed fix candidate", "product-level fix"],
            risk=ActionRisk.medium,
        )

    return MerchantDiagnosticSection(
        id="merchant_issue_queue",
        title="Merchant Center: kolejka feed/product issues",
        status="ready",
        summary=(
            f"WILQ ma {len(issue_clusters)} issue clusters, "
            f"{len(tactical_items)} Merchant tactical items i {len(issue_facts)} "
            "issue metric facts."
        ),
        diagnosis=(
            "Najbezpieczniejsza praca dla marketera to review problemów po typie "
            "issue, atrybucie i destination. WILQ nadal nie pokazuje raw product dumps."
        ),
        next_step="Otwórz ActionObject `act_review_merchant_feed_issues` i przygotuj review queue.",
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
                    "Obecny Merchant read contract zwraca issue dimensions i liczby "
                    "produktów, ale nie zwraca sample product IDs ani tytułów."
                ),
                source_connectors=[MERCHANT_CONNECTOR_ID],
                evidence_ids=_unique(fact.evidence_id for fact in group_facts),
                blocked_claims=["approval restored", "revenue recovered", "automatic feed edit"],
                action_id=action_id,
                risk=_merchant_cluster_risk(severity, resolution),
                next_step=(
                    "Przejrzyj ten issue cluster w `act_review_merchant_feed_issues`; "
                    "najpierw przygotuj payload preview, bez automatycznej zmiany feedu."
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
        summary="Merchant actions pozostają prepare-only do czasu walidacji payloadu i audytu.",
        diagnosis=(
            "Zmiany feedu lub produktów mogą wpływać na widoczność i sprzedaż. WILQ "
            "może przygotować review queue, ale nie może zmieniać primary feedu ani "
            "twierdzić, że naprawił produkty bez apply support."
        ),
        next_step=(
            "Waliduj ActionObject, pokaż payload preview i zatrzymaj apply "
            "do explicit confirm."
        ),
        source_connectors=[MERCHANT_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        action_ids=action_ids,
        blocked_claims=["feed write", "product data mutation", "automatic approval fix"],
        risk=ActionRisk.medium,
    )


def _facts_by_names(facts: list[MetricFact], names: set[str]) -> list[MetricFact]:
    return [fact for fact in facts if fact.name in names]


def _numeric_metric(facts: list[MetricFact], name: str) -> int | None:
    for fact in facts:
        if fact.name == name and isinstance(fact.value, int | float):
            return int(fact.value)
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
    return f"Metric facts: {samples}."


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values
