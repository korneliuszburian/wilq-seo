from __future__ import annotations

from collections.abc import Iterable

from wilq.evidence.registry import connector_evidence_id
from wilq.operator_labels import source_connector_label
from wilq.schemas import ActionRisk, ConnectorRefreshRun, ContentDecisionItem


def content_vendor_read_blocker_decision(
    latest_refreshes: list[ConnectorRefreshRun],
    action_ids: list[str],
    *,
    knowledge_card_ids: tuple[str, ...],
    expert_rule_ids: tuple[str, ...],
) -> ContentDecisionItem:
    gsc_reason = content_blocker_reason(latest_refreshes, "google_search_console")
    wordpress_reason = content_blocker_reason(latest_refreshes, "wordpress_ekologus")
    return ContentDecisionItem(
        id="content_block_vendor_read",
        decision_type="block_until_vendor_read",
        status="blocked",
        title="Content: odczyt GSC i WordPress wymagany przed decyzją",
        summary=(
            "WILQ nie ma danych GSC dla zapytań i stron ani spisu treści "
            "WordPress wystarczających do decyzji: odświeżyć, scalić albo utworzyć."
        ),
        priority=5,
        metric_tiles={"blokady": 2},
        source_connectors=["google_search_console", "wordpress_ekologus"],
        evidence_ids=_unique(
            [
                *refresh_or_connector_evidence_ids(
                    latest_refreshes,
                    "google_search_console",
                ),
                *refresh_or_connector_evidence_ids(
                    latest_refreshes,
                    "wordpress_ekologus",
                ),
            ]
        ),
        action_ids=action_ids,
        knowledge_card_ids=list(knowledge_card_ids),
        expert_rule_ids=list(expert_rule_ids),
        blocked_claims=[
            "rekomendacja bez danych źródłowych",
            "wzrost pozycji",
            "wzrost liczby leadów",
            "automatyczna publikacja",
        ],
        rationale=(
            f"GSC blocker: {gsc_reason} WordPress blocker: {wordpress_reason} "
            "Bez tych odczytów WILQ może tylko wskazać brak danych, nie decyzję SEO."
        ),
        next_step=(
            "Uruchom odczyt danych z Google Search Console i WordPress, "
            "potem wróć do diagnozy treści."
        ),
        risk=ActionRisk.medium,
    )


def content_blocker_reason(
    latest_refreshes: list[ConnectorRefreshRun],
    connector_id: str,
) -> str:
    latest = next((run for run in latest_refreshes if run.connector_id == connector_id), None)
    if latest and latest.errors:
        return latest.errors[0]
    if latest and latest.summary:
        return latest.summary
    return f"Brak wykonanego odczytu danych dla: {source_connector_label(connector_id)}."


def refresh_or_connector_evidence_ids(
    latest_refreshes: list[ConnectorRefreshRun],
    connector_id: str,
) -> list[str]:
    latest = next((run for run in latest_refreshes if run.connector_id == connector_id), None)
    if latest:
        return latest.evidence_ids
    return [connector_evidence_id(connector_id)]


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values
