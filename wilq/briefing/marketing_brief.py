from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from wilq.actions.service import list_actions
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import list_connector_statuses
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionObject,
    ActionRisk,
    CommandCenterBriefItem,
    CommandCenterResponse,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ConnectorStatus,
    ConnectorStatusValue,
    ConnectorSummary,
    DailyDecision,
    MarketingBrief,
    MarketingBriefItem,
    MarketingBriefSection,
    MetricFact,
)
from wilq.storage.metric_store import metric_store

STRICT_BRIEF_INSTRUCTION = (
    "WILQ pokazuje tylko metryki z API/evidence. Brak danych oznacza blocker, "
    "nie domysł marketingowy."
)

CONNECTOR_LABELS = {
    "google_ads": "Google Ads",
    "google_search_console": "Google Search Console",
    "google_analytics_4": "GA4",
    "google_merchant_center": "Merchant Center",
    "ahrefs": "Ahrefs",
    "localo": "Localo",
    "wordpress_ekologus": "WordPress ekologus.pl",
    "wordpress_sklep": "WordPress sklep.ekologus.pl",
    "linkedin": "LinkedIn",
    "facebook": "Facebook",
}

OPTIONAL_BRIEF_BLOCKER_CONNECTORS = {"facebook", "google_sheets", "linkedin"}
MARKETING_BRIEF_CONNECTOR_FACT_LIMIT = 200
CORE_BRIEF_ACTION_CONNECTORS = {
    "google_ads",
    "google_analytics_4",
    "google_merchant_center",
    "google_search_console",
    "localo",
    "wordpress_ekologus",
    "wordpress_sklep",
}
METRIC_NAME_PRIORITY = {
    "issue_product_count": 0,
    "clicks": 0,
    "active_users": 0,
    "content_object_count": 0,
    "domain_rating": 0,
    "conversions": 1,
    "sessions": 1,
    "impressions": 1,
    "active_products": 1,
    "average_position": 2,
    "ctr": 2,
    "engagement_rate": 2,
    "disapproved_products": 2,
    "pages_total": 3,
    "posts_total": 3,
    "ahrefs_rank": 3,
    "row_count": 5,
    "api": 10,
    "connector_id": 10,
}


def build_marketing_brief(
    connectors: list[ConnectorStatus] | None = None,
    refresh_runs: list[ConnectorRefreshRun] | None = None,
    actions: list[ActionObject] | None = None,
    command_center: CommandCenterResponse | None = None,
) -> MarketingBrief:
    connectors = connectors if connectors is not None else list_connector_statuses()
    refresh_runs = refresh_runs if refresh_runs is not None else list_connector_refresh_runs()
    metric_facts = _marketing_brief_metric_facts(connectors)
    actions = actions if actions is not None else list_actions()
    latest_runs = _latest_run_by_connector(refresh_runs)
    latest_runs = _prefer_successful_localo_access_probe(latest_runs, refresh_runs)

    business_metric_facts = [
        fact
        for fact in metric_facts
        if not _is_probe_only_fact(fact)
        and _metric_fact_allowed_by_latest_refresh(fact, latest_runs)
    ]
    business_metric_facts = _latest_metric_facts_by_identity(business_metric_facts)
    metric_items = _metric_items(business_metric_facts)
    if command_center is not None:
        metric_items = _decision_metric_items(command_center.daily_decisions) + [
            item
            for item in metric_items
            if not _connectors_intersect(
                item.source_connectors,
                _daily_decision_connector_ids(command_center.daily_decisions),
            )
        ]
    blocker_items = _blocker_items(connectors, latest_runs)
    if command_center is not None:
        blocker_items = _merge_items(
            blocker_items,
            _decision_blocker_items(command_center.daily_decisions),
        )
        blocker_items = _merge_items(
            blocker_items,
            _operator_brief_blocker_items(command_center.operator_brief),
        )
    core_actions = core_brief_actions(actions)
    stateful_actions = _stateful_brief_actions(core_actions, blocker_items)
    if command_center is not None:
        stateful_actions = _actions_for_daily_decisions(
            stateful_actions,
            command_center.daily_decisions,
        )
    action_items = _action_items(
        stateful_actions,
        command_center.daily_decisions if command_center is not None else None,
    )
    recommendation_items = (
        _decision_recommendation_items(command_center.daily_decisions)
        if command_center is not None
        else _recommendation_items(business_metric_facts, blocker_items)
    )
    sections = [
        MarketingBriefSection(
            id="what_we_know",
            title="Co wiemy z realnych danych",
            description="Najświeższe metryki zapisane przez read-only connector refresh.",
            items=metric_items,
        ),
        MarketingBriefSection(
            id="what_blocks_us",
            title="Co blokuje decyzje",
            description="Braki danych, OAuth, uprawnienia lub niedokończone adaptery.",
            items=blocker_items,
        ),
        MarketingBriefSection(
            id="safe_next_actions",
            title="Bezpieczne następne kroki",
            description="ActionObjecty i działania przygotowawcze bez wykonywania zmian.",
            items=action_items,
        ),
        MarketingBriefSection(
            id="recommended_focus",
            title="Rekomendowany fokus",
            description="Priorytety oparte o dostępne metryki albo jawne blockery.",
            items=recommendation_items,
        ),
    ]
    evidence_ids = _unique(
        evidence_id
        for section in sections
        for item in section.items
        for evidence_id in item.evidence_ids
    )
    action_ids = _unique(action.id for action in core_actions)
    return MarketingBrief(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector_summary=_connector_summary(connectors),
        sections=sections,
        top_metric_facts=_representative_metric_facts(business_metric_facts, limit=12),
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        blocker_count=len(blocker_items),
        recommendation_count=len(recommendation_items),
    )


def _marketing_brief_metric_facts(connectors: list[ConnectorStatus]) -> list[MetricFact]:
    facts_by_connector = metric_store().list_metric_facts_by_connector(
        [connector.id for connector in connectors],
        limit_per_connector=MARKETING_BRIEF_CONNECTOR_FACT_LIMIT,
    )
    return [
        fact
        for connector in connectors
        for fact in facts_by_connector.get(connector.id, [])
    ]


def _connector_summary(connectors: list[ConnectorStatus]) -> ConnectorSummary:
    return ConnectorSummary(
        total=len(connectors),
        configured=sum(1 for connector in connectors if connector.configured),
        missing_credentials=sum(1 for connector in connectors if connector.missing_credentials),
    )


def _latest_run_by_connector(
    refresh_runs: list[ConnectorRefreshRun],
) -> dict[str, ConnectorRefreshRun]:
    latest: dict[str, ConnectorRefreshRun] = {}
    for run in refresh_runs:
        current = latest.get(run.connector_id)
        run_time = run.completed_at or run.started_at
        if current is None:
            latest[run.connector_id] = run
            continue
        current_time = current.completed_at or current.started_at
        if run_time > current_time:
            latest[run.connector_id] = run
    return latest


def _prefer_successful_localo_access_probe(
    latest_runs: dict[str, ConnectorRefreshRun],
    refresh_runs: list[ConnectorRefreshRun],
) -> dict[str, ConnectorRefreshRun]:
    successful_probe = _latest_successful_localo_mcp_run(refresh_runs)
    if successful_probe is None:
        return latest_runs
    return {**latest_runs, "localo": successful_probe}


def _latest_successful_localo_mcp_run(
    refresh_runs: list[ConnectorRefreshRun],
) -> ConnectorRefreshRun | None:
    localo_runs = [run for run in refresh_runs if run.connector_id == "localo"]
    sorted_runs = sorted(
        localo_runs,
        key=lambda run: run.completed_at or run.started_at,
        reverse=True,
    )
    for run in sorted_runs:
        if (
            run.status == ConnectorRefreshStatus.completed
            and run.metric_summary.get("api") == "localo_mcp_oauth_probe"
            and run.metric_summary.get("mcp_initialize_status") == 200
        ):
            return run
    return None


def _metric_items(metric_facts: list[MetricFact]) -> list[MarketingBriefItem]:
    grouped: dict[str, list[MetricFact]] = defaultdict(list)
    for fact in metric_facts:
        grouped[fact.source_connector].append(fact)

    items: list[MarketingBriefItem] = []
    for index, (connector_id, facts) in enumerate(grouped.items(), start=1):
        prioritized_facts = _prioritize_dimension_facts(facts)
        headline = _metric_headline(connector_id, prioritized_facts)
        evidence_ids = _unique(fact.evidence_id for fact in prioritized_facts)
        items.append(
            MarketingBriefItem(
                id=f"brief_metric_{connector_id}",
                title=headline,
                kind="metric",
                priority=min(20 + index, 39),
                source_connectors=[connector_id],
                evidence_ids=evidence_ids,
                metric_facts=prioritized_facts[:6],
                summary=_metric_summary(connector_id, prioritized_facts),
                next_step=_metric_next_step(connector_id),
                risk=ActionRisk.low,
            )
        )
    return sorted(items, key=lambda item: item.priority)


def _decision_metric_items(decisions: list[DailyDecision]) -> list[MarketingBriefItem]:
    return [
        MarketingBriefItem(
            id=f"brief_decision_{decision.id}",
            title=decision.title,
            kind="metric",
            priority=min(20 + index, 39),
            source_connectors=decision.source_connectors,
            evidence_ids=decision.evidence_ids,
            action_ids=decision.action_ids,
            summary=_decision_summary(decision),
            next_step=decision.bezpieczny_next_step,
            risk=decision.risk,
        )
        for index, decision in enumerate(
            sorted(decisions, key=lambda item: item.priority),
            start=1,
        )
    ]


def _decision_blocker_items(decisions: list[DailyDecision]) -> list[MarketingBriefItem]:
    return [
        MarketingBriefItem(
            id=f"brief_blocker_{decision.id}",
            title=decision.title,
            kind="blocker",
            priority=min(5 + index, 19),
            source_connectors=decision.source_connectors,
            evidence_ids=decision.evidence_ids,
            action_ids=decision.action_ids,
            summary=_decision_summary(decision),
            next_step=decision.bezpieczny_next_step,
            risk=decision.risk,
            blocker_reason=", ".join(decision.blocked_claims[:4]) or "brak kontraktu",
        )
        for index, decision in enumerate(
            sorted(
                (decision for decision in decisions if decision.status == "blocked"),
                key=lambda item: item.priority,
            ),
            start=1,
        )
    ]


def _operator_brief_blocker_items(
    operator_brief: list[CommandCenterBriefItem],
) -> list[MarketingBriefItem]:
    return [
        MarketingBriefItem(
            id=f"brief_blocker_{item.id}",
            title=item.title,
            kind="blocker",
            priority=min(10 + index, 19),
            source_connectors=item.source_connectors,
            evidence_ids=item.evidence_ids,
            action_ids=item.action_ids,
            summary=item.summary,
            next_step=item.next_step,
            risk=item.risk,
            blocker_reason=", ".join(item.blocked_claims[:4]) or "brak kontraktu",
        )
        for index, item in enumerate(
            sorted(
                (
                    item
                    for item in operator_brief
                    if item.status == "blocked"
                    and item.action_ids
                    and item.id not in {"daily_localo_readiness"}
                ),
                key=lambda item: item.priority,
            ),
            start=1,
        )
    ]


def _decision_recommendation_items(
    decisions: list[DailyDecision],
) -> list[MarketingBriefItem]:
    return [
        MarketingBriefItem(
            id=f"brief_focus_{decision.id}",
            title=decision.title,
            kind="recommendation",
            priority=min(60 + index, 79),
            source_connectors=decision.source_connectors,
            evidence_ids=decision.evidence_ids,
            action_ids=decision.action_ids,
            summary=decision.dlaczego_to_ma_znaczenie,
            next_step=decision.bezpieczny_next_step,
            risk=decision.risk,
        )
        for index, decision in enumerate(
            sorted(
                (decision for decision in decisions if decision.status == "ready"),
                key=lambda item: item.priority,
            ),
            start=1,
        )
    ]


def _daily_decision_connector_ids(decisions: list[DailyDecision]) -> set[str]:
    return {
        connector_id
        for decision in decisions
        for connector_id in decision.source_connectors
    }


def _decision_summary(decision: DailyDecision) -> str:
    return f"{decision.co_widzimy} {decision.dlaczego_to_ma_znaczenie}"


def _merge_items(
    primary: list[MarketingBriefItem],
    secondary: list[MarketingBriefItem],
) -> list[MarketingBriefItem]:
    items_by_id = {item.id: item for item in primary}
    semantic_keys = {_item_semantic_key(item) for item in primary}
    for item in secondary:
        semantic_key = _item_semantic_key(item)
        if semantic_key in semantic_keys:
            continue
        items_by_id.setdefault(item.id, item)
        semantic_keys.add(semantic_key)
    return sorted(items_by_id.values(), key=lambda item: item.priority)


def _item_semantic_key(item: MarketingBriefItem) -> tuple[
    str,
    str,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    return (
        item.kind,
        item.title,
        tuple(sorted(item.source_connectors)),
        tuple(sorted(item.action_ids)),
        tuple(sorted(item.evidence_ids)),
    )


def _latest_metric_facts_by_identity(metric_facts: list[MetricFact]) -> list[MetricFact]:
    latest_by_key: dict[tuple[str, str, tuple[tuple[str, str], ...]], MetricFact] = {}
    for fact in metric_facts:
        key = (
            fact.source_connector,
            fact.name,
            tuple(sorted(fact.dimensions.items())),
        )
        current = latest_by_key.get(key)
        if current is None or _metric_fact_sort_time(fact) > _metric_fact_sort_time(current):
            latest_by_key[key] = fact
    return sorted(
        latest_by_key.values(),
        key=lambda fact: _metric_fact_sort_time(fact),
        reverse=True,
    )


def _metric_fact_sort_time(fact: MetricFact) -> str:
    if fact.collected_at is None:
        return ""
    return fact.collected_at.isoformat()


def _representative_metric_facts(metric_facts: list[MetricFact], limit: int) -> list[MetricFact]:
    prioritized_facts = _prioritize_dimension_facts(metric_facts)
    selected: list[MetricFact] = []
    seen_connectors: set[str] = set()
    for fact in prioritized_facts:
        if _is_probe_only_fact(fact) or fact.source_connector in seen_connectors:
            continue
        selected.append(fact)
        seen_connectors.add(fact.source_connector)
        if len(selected) >= limit:
            return selected
    for fact in prioritized_facts:
        if _is_probe_only_fact(fact) or fact in selected:
            continue
        selected.append(fact)
        if len(selected) >= limit:
            return selected
    return selected


def _prioritize_dimension_facts(metric_facts: list[MetricFact]) -> list[MetricFact]:
    return sorted(
        metric_facts,
        key=lambda fact: (
            0 if fact.dimensions else 1,
            METRIC_NAME_PRIORITY.get(fact.name, 4),
            -_numeric_sort_value(fact.value),
        ),
    )


def _numeric_sort_value(value: float | int | str) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def _metric_fact_allowed_by_latest_refresh(
    fact: MetricFact,
    latest_runs: dict[str, ConnectorRefreshRun],
) -> bool:
    if fact.source_connector != "google_ads":
        return True
    latest_run = latest_runs.get(fact.source_connector)
    if latest_run is None:
        return True
    return (
        latest_run.status == ConnectorRefreshStatus.completed
        and latest_run.vendor_data_collected
    )


def _blocker_items(
    connectors: list[ConnectorStatus],
    latest_runs: dict[str, ConnectorRefreshRun],
) -> list[MarketingBriefItem]:
    blockers: list[MarketingBriefItem] = []
    for connector in connectors:
        if connector.status == ConnectorStatusValue.disabled:
            continue
        if connector.id in OPTIONAL_BRIEF_BLOCKER_CONNECTORS:
            continue
        latest_run = latest_runs.get(connector.id)
        has_blocked_run = latest_run is not None and latest_run.status in {
            ConnectorRefreshStatus.blocked,
            ConnectorRefreshStatus.failed,
        }
        has_readiness_blocker = bool(connector.missing_credentials) or not connector.configured
        if not has_blocked_run and not has_readiness_blocker:
            continue

        reason = _blocker_reason(connector, latest_run)
        evidence_ids = (
            latest_run.evidence_ids if latest_run else [connector_evidence_id(connector.id)]
        )
        priority = 1 if connector.id == "google_ads" else 5
        if connector.id == "localo":
            priority = 6
        risk = (
            ActionRisk.medium if connector.id in {"google_ads", "localo"} else ActionRisk.low
        )
        blockers.append(
            MarketingBriefItem(
                id=f"brief_blocker_{connector.id}",
                title=f"{_connector_label(connector.id)}: {reason}",
                kind="blocker",
                priority=priority,
                source_connectors=[connector.id],
                evidence_ids=evidence_ids,
                summary=_blocker_summary(connector, latest_run, reason),
                next_step=_blocker_next_step(connector.id, reason),
                risk=risk,
                blocker_reason=reason,
            )
        )
    return sorted(blockers, key=lambda item: item.priority)


def core_brief_actions(actions: Iterable[ActionObject]) -> list[ActionObject]:
    return [action for action in actions if action.connector in CORE_BRIEF_ACTION_CONNECTORS]


def _stateful_brief_actions(
    actions: Iterable[ActionObject],
    blocker_items: list[MarketingBriefItem],
) -> list[ActionObject]:
    blocked_connector_ids = {
        connector
        for item in blocker_items
        for connector in item.source_connectors
    }
    return [
        action
        for action in actions
        if not (
            action.id == "act_configure_google_ads_env"
            and "google_ads" not in blocked_connector_ids
        )
    ]


def _action_items(
    actions: list[ActionObject],
    decisions: list[DailyDecision] | None = None,
) -> list[MarketingBriefItem]:
    decisions_by_action_id = _decisions_by_action_id(decisions or [])
    items: list[MarketingBriefItem] = []
    for index, action in enumerate(actions, start=1):
        decision = decisions_by_action_id.get(action.id)
        if decision is not None:
            items.append(_action_item_from_decision(action, decision, index))
            continue
        items.append(
            MarketingBriefItem(
                id=f"brief_action_{action.id}",
                title=action.title,
                kind="action",
                priority=min(40 + index, 59),
                source_connectors=[action.connector],
                evidence_ids=action.evidence_ids,
                action_ids=[action.id],
                metric_facts=action.metrics,
                summary=action.human_diagnosis,
                next_step=action.recommended_reason,
                risk=action.risk,
            )
        )
    return items


def _actions_for_daily_decisions(
    actions: list[ActionObject],
    decisions: list[DailyDecision],
) -> list[ActionObject]:
    daily_action_ids = {
        action_id
        for decision in decisions
        for action_id in decision.action_ids
    }
    if not daily_action_ids:
        return []
    return [action for action in actions if action.id in daily_action_ids]


def _decisions_by_action_id(decisions: list[DailyDecision]) -> dict[str, DailyDecision]:
    result: dict[str, DailyDecision] = {}
    for decision in sorted(decisions, key=lambda item: item.priority):
        for action_id in decision.action_ids:
            result.setdefault(action_id, decision)
    return result


def _action_item_from_decision(
    action: ActionObject,
    decision: DailyDecision,
    index: int,
) -> MarketingBriefItem:
    return MarketingBriefItem(
        id=f"brief_action_{action.id}",
        title=action.title,
        kind="action",
        priority=min(40 + index, 59),
        source_connectors=decision.source_connectors or [action.connector],
        evidence_ids=decision.evidence_ids,
        action_ids=[action.id],
        metric_facts=[],
        summary=_decision_summary(decision),
        next_step=decision.bezpieczny_next_step,
        risk=max(action.risk, decision.risk, key=_risk_rank),
    )


def _risk_rank(risk: ActionRisk) -> int:
    return {
        ActionRisk.low: 0,
        ActionRisk.medium: 1,
        ActionRisk.high: 2,
        ActionRisk.critical: 3,
    }.get(risk, 0)


def _recommendation_items(
    metric_facts: list[MetricFact],
    blocker_items: list[MarketingBriefItem],
) -> list[MarketingBriefItem]:
    items: list[MarketingBriefItem] = []
    facts_by_connector: dict[str, list[MetricFact]] = defaultdict(list)
    for fact in metric_facts:
        facts_by_connector[fact.source_connector].append(fact)

    if "google_merchant_center" in facts_by_connector:
        merchant_facts = _prioritize_dimension_facts(facts_by_connector["google_merchant_center"])
        items.append(
            MarketingBriefItem(
                id="brief_focus_merchant_feed",
                title="Merchant Center: zacznij od kolejki problemów feedu",
                kind="recommendation",
                priority=60,
                source_connectors=["google_merchant_center"],
                evidence_ids=_unique(fact.evidence_id for fact in merchant_facts),
                metric_facts=merchant_facts[:6],
                summary=(
                    "Merchant ma realne metryki produktów i liczby problemów feedu. "
                    "To jest najbardziej operacyjny obszar do kolejki review bez "
                    "automatycznej zmiany danych produktu."
                ),
                next_step="Otwórz /merchant i przygotuj kolejkę problemów feedu z payload preview.",
                risk=ActionRisk.medium,
            )
        )

    if "google_search_console" in facts_by_connector:
        gsc_facts = _prioritize_dimension_facts(facts_by_connector["google_search_console"])
        items.append(
            MarketingBriefItem(
                id="brief_focus_gsc_content",
                title="GSC: przełóż widoczność na kolejkę treści",
                kind="recommendation",
                priority=62,
                source_connectors=["google_search_console"],
                evidence_ids=_unique(fact.evidence_id for fact in gsc_facts),
                metric_facts=gsc_facts[:6],
                summary=(
                    "GSC ma kliknięcia, impressions, CTR i pozycję. Następny krok to "
                    "query/page breakdown, nie ogólny content brainstorming."
                ),
                next_step="Zbuduj Content Planner queue: refresh/create/merge/block.",
                risk=ActionRisk.low,
            )
        )

    if any(item.source_connectors == ["google_ads"] for item in blocker_items):
        google_ads_blocker = next(
            item for item in blocker_items if item.source_connectors == ["google_ads"]
        )
        items.append(
            MarketingBriefItem(
                id="brief_focus_google_ads_blocker",
                title="Google Ads: najpierw napraw OAuth, potem diagnozuj spend",
                kind="recommendation",
                priority=61,
                source_connectors=["google_ads"],
                evidence_ids=google_ads_blocker.evidence_ids,
                summary=(
                    "WILQ nie może uczciwie diagnozować wasted spend bez live Ads evidence. "
                    "Obecny stan musi być pokazany jako blocker, nie rekomendacja."
                ),
                next_step="Użyj ActionObject `act_configure_google_ads_env` i helperów OAuth.",
                risk=ActionRisk.medium,
                blocker_reason=google_ads_blocker.blocker_reason,
            )
        )
    return sorted(items, key=lambda item: item.priority)


def _metric_headline(connector_id: str, facts: list[MetricFact]) -> str:
    if connector_id == "localo":
        return "Localo: widoczność lokalna i opinie do review"
    interesting = [fact for fact in facts if fact.name not in {"api", "connector_id"}]
    if not interesting:
        return f"{_connector_label(connector_id)}: zapisano metric facts"
    first = interesting[0]
    return f"{_connector_label(connector_id)}: {first.name} = {_format_value(first)}"


def _metric_summary(connector_id: str, facts: list[MetricFact]) -> str:
    if connector_id == "localo":
        return _localo_metric_summary(facts)
    sample = ", ".join(_metric_summary_parts(facts[:6])[:4])
    return (
        f"WILQ ma realne metric facts z connectora {_connector_label(connector_id)}: "
        f"{sample}. Każda metryka ma evidence ID."
    )


def _localo_metric_summary(facts: list[MetricFact]) -> str:
    metrics = {fact.name: fact for fact in facts}
    parts: list[str] = []
    tracked_keywords = metrics.get("localo_tracked_keyword_count")
    visibility = metrics.get("localo_avg_visibility_current")
    reviews = metrics.get("localo_reviews_count")
    replied_reviews = metrics.get("localo_reviews_replied_count")
    if tracked_keywords is not None:
        parts.append(f"{_format_value(tracked_keywords)} monitorowanych fraz")
    if visibility is not None:
        parts.append(f"średnia widoczność {_format_value(visibility)}")
    if reviews is not None:
        parts.append(f"{_format_value(reviews)} opinii")
    if replied_reviews is not None:
        parts.append(f"{_format_value(replied_reviews)} odpowiedzi na opinie")
    if not parts:
        parts = _metric_summary_parts(facts[:4])
    return (
        "WILQ ma realne Localo facts do review lokalnej widoczności: "
        f"{', '.join(parts)}. To nie jest claim o wzroście pozycji, GBP performance "
        "ani przewadze nad konkurencją bez osobnych kontraktów."
    )


def _metric_summary_parts(facts: list[MetricFact]) -> list[str]:
    by_name: dict[str, list[MetricFact]] = defaultdict(list)
    for fact in facts:
        by_name[fact.name].append(fact)
    parts: list[str] = []
    for name, named_facts in by_name.items():
        if len(named_facts) == 1:
            parts.append(f"{name}={_format_value(named_facts[0])}")
            continue
        values = {_format_value(fact) for fact in named_facts}
        if len(values) == 1:
            parts.append(f"{name}={next(iter(values))} w {len(named_facts)} wymiarach")
        else:
            parts.append(f"{name}: {len(named_facts)} wartości")
    return parts


def _metric_next_step(connector_id: str) -> str:
    if connector_id == "google_merchant_center":
        return "Rozbij problemy Merchant na produkty i przygotuj kolejkę feed review."
    if connector_id == "google_search_console":
        return "Pobierz query/page breakdown i zbuduj kolejkę content refresh/create."
    if connector_id == "google_analytics_4":
        return "Rozbij GA4 po landing page i źródle ruchu, zanim ocenimy jakość kampanii."
    if connector_id.startswith("wordpress"):
        return "Połącz inventory z GSC/GA4 i oznacz strony stale/refresh/merge/block."
    if connector_id == "ahrefs":
        return "Użyj Ahrefs jako kontekstu authority/gap, nie jako samodzielnej rekomendacji."
    if connector_id == "localo":
        return (
            "Otwórz /localo i potraktuj fakty Localo jako review lokalnej "
            "widoczności, nie apply."
        )
    return "Użyj tych faktów w odpowiednim workflow i nie rozszerzaj ich poza evidence."


def _blocker_reason(connector: ConnectorStatus, run: ConnectorRefreshRun | None) -> str:
    if connector.id == "localo" and run and _localo_access_token_blocked(run):
        return "OAuth MCP wymaga dokończenia autoryzacji access tokenem"
    if run and run.errors:
        return run.errors[0]
    if run and run.summary:
        return run.summary
    if connector.missing_credentials:
        return f"brakuje: {', '.join(connector.missing_credentials)}"
    if not connector.configured:
        return "connector nie jest skonfigurowany"
    return "ostatni refresh nie zebrał danych vendor"


def _blocker_summary(
    connector: ConnectorStatus,
    run: ConnectorRefreshRun | None,
    reason: str,
) -> str:
    if connector.id == "localo" and run and _localo_access_token_blocked(run):
        return (
            f"Ostatni refresh {run.id} potwierdza, że Localo MCP endpoint działa, "
            "Organization ID i MCP secret są skonfigurowane, ale initialize zwraca 401 "
            "bez wynikowego OAuth access tokenu."
        )
    if run:
        return (
            f"Ostatni refresh {run.id} zakończył się statusem {run.status}. "
            f"Powód: {reason}"
        )
    return f"{_connector_label(connector.id)} nie może dostarczyć evidence. Powód: {reason}"


def _blocker_next_step(connector_id: str, reason: str) -> str:
    if connector_id == "google_ads":
        return "Odśwież Google Ads OAuth przez ActionObject i nie pokazuj Ads rekomendacji."
    if connector_id == "localo" and (
        "LOCALO_ACCESS_TOKEN" in reason or "OAuth MCP" in reason
    ):
        return (
            "Dokończ Localo OAuth authorization_code + PKCE i zapisz wynikowy "
            "access token lokalnie jako LOCALO_ACCESS_TOKEN."
        )
    if connector_id == "localo":
        return "Dokończ Localo MCP OAuth i dopiero potem pokazuj local visibility facts."
    return "Uzupełnij wskazany blocker albo zostaw tę rekomendację zablokowaną."


def _localo_access_token_blocked(run: ConnectorRefreshRun) -> bool:
    serialized_errors = " ".join(run.errors)
    return (
        "LOCALO_ACCESS_TOKEN" in serialized_errors
        or run.metric_summary.get("access_token_present") == 0
    )


def _format_value(fact: MetricFact) -> str:
    suffix = f" {fact.unit}" if fact.unit else ""
    return f"{fact.value}{suffix}"


def _is_probe_only_fact(fact: MetricFact) -> bool:
    if (
        fact.source_connector == "localo"
        and fact.name == "api"
        and fact.value == "localo_mcp_oauth_probe"
    ):
        return True
    return fact.source_connector == "localo" and fact.name in {
        "access_token_present",
        "authorization_code_supported",
        "pkce_s256_supported",
        "mcp_initialize_status",
    }


def _connector_label(connector_id: str) -> str:
    return CONNECTOR_LABELS.get(connector_id, connector_id)


def _unique(items: Iterable[str]) -> list[str]:
    unique_items: list[str] = []
    for item in items:
        if item and item not in unique_items:
            unique_items.append(item)
    return unique_items


def _connectors_intersect(left: Iterable[str], right: Iterable[str]) -> bool:
    return bool(set(left) & set(right))
