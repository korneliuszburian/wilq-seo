from __future__ import annotations

from wilq.actions.google_ads.keyword_planner import KEYWORD_PLANNER_ACCESS_ACTION_ID
from wilq.schemas import ActionRisk, AdsDiagnosticSection, AdsKeywordPlannerReadContract

GOOGLE_ADS_CONNECTOR_ID = "google_ads"


def build_keyword_planner_section(
    keyword_planner_read_contract: AdsKeywordPlannerReadContract,
    action_ids: list[str],
) -> AdsDiagnosticSection:
    metric_facts = [
        fact for row in keyword_planner_read_contract.idea_rows for fact in row.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_keyword_planner",
        title="Wzbogacenie Keyword Planner",
        status=keyword_planner_read_contract.status,
        summary=keyword_planner_read_contract.summary,
        diagnosis=(
            "Ten kontrakt wzbogaca hasła źródłowe o pomysły i historyczne metryki "
            "Keyword Planner. Nie jest prognozą, rozmiarem odbiorców ani zgodą na "
            "zapis kierowania reklam."
        ),
        next_step=keyword_planner_read_contract.next_step,
        source_connectors=keyword_planner_read_contract.source_connectors,
        evidence_ids=keyword_planner_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        action_ids=[
            action_id for action_id in action_ids if action_id == KEYWORD_PLANNER_ACCESS_ACTION_ID
        ],
        blocked_claims=keyword_planner_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )
