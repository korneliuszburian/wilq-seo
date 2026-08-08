from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from wilq.briefing.blocked_claim_labels import operator_blocked_claims
from wilq.operator_labels import freshness_state_label, source_connector_label
from wilq.schemas import (
    CommandCenterActionPlanItem,
    CommandCenterBriefItem,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ConnectorStatus,
    DailyDecision,
    DecisionState,
    FreshnessState,
    MetricFact,
    utc_now,
)

from .labels import (
    _action_count_summary,
    _connector_label,
    _connector_label_map,
    _decision_state_label,
    _evidence_count_summary,
    _metric_tiles_sentence,
    _priority_label,
    _route_cta_label,
    _route_label,
    _skill_label,
)
from .metrics import (
    _decision_metric_facts,
    _decision_metric_tiles,
)
from .shared import (
    DAILY_DECISION_FRESH_AFTER_HOURS,
    PRIMARY_DAILY_PLAN_IDS,
)


def build_daily_decisions(
    action_plan: list[CommandCenterActionPlanItem],
    operator_brief: list[CommandCenterBriefItem],
    connectors: list[ConnectorStatus] | None = None,
    refresh_runs: list[ConnectorRefreshRun] | None = None,
    facts_by_connector: dict[str, list[MetricFact]] | None = None,
) -> list[DailyDecision]:
    brief_by_plan_id = _brief_items_by_plan_id(operator_brief)
    freshness_by_connector = _daily_decision_freshness_by_connector(
        connectors or [],
        refresh_runs or [],
    )
    facts_by_connector = facts_by_connector or {}
    connector_labels = _connector_label_map(connectors or [])
    decisions: list[DailyDecision] = []
    for plan_item in action_plan:
        if plan_item.id not in PRIMARY_DAILY_PLAN_IDS:
            continue
        freshness = _combined_decision_freshness(
            plan_item.source_connectors,
            freshness_by_connector,
        )
        decision_state = _daily_decision_state(plan_item.status, freshness)
        operator_action = _daily_decision_operator_action(plan_item, decision_state)
        expected_codex_output = _daily_decision_expected_codex_output(
            plan_item,
            decision_state,
        )
        decisions.append(
            DailyDecision(
                id=plan_item.id.replace("plan_", "decision_", 1),
                title=plan_item.title,
                domain=_daily_decision_domain(plan_item.category),
                freshness=freshness,
                freshness_label=freshness_state_label(freshness.state),
                decision_state=decision_state,
                decision_state_label=_decision_state_label(decision_state),
                route=plan_item.route,
                route_label=_route_label(plan_item.route),
                cta_label=_route_cta_label(plan_item.route),
                status=plan_item.status,
                priority=plan_item.priority,
                priority_label=_priority_label(plan_item.priority),
                metric_tiles=_decision_metric_tiles(plan_item, brief_by_plan_id),
                metric_facts=_decision_metric_facts(plan_item, facts_by_connector),
                co_widzimy=_decision_observation(
                    plan_item,
                    brief_by_plan_id.get(plan_item.id),
                ),
                dlaczego_to_ma_znaczenie=plan_item.why_it_matters,
                bezpieczny_next_step=operator_action,
                why_it_matters=plan_item.why_it_matters,
                operator_action=operator_action,
                source_connectors=plan_item.source_connectors,
                source_connector_labels=[
                    _connector_label(connector_id, connector_labels)
                    for connector_id in plan_item.source_connectors
                ],
                evidence_ids=plan_item.evidence_ids,
                evidence_summary=_evidence_count_summary(len(plan_item.evidence_ids)),
                action_ids=plan_item.action_ids,
                action_summary=_action_count_summary(len(plan_item.action_ids)),
                blocked_claims=plan_item.blocked_claims,
                blocked_claim_labels=operator_blocked_claims(plan_item.blocked_claims),
                skill_id=plan_item.skill_id,
                skill_label=_skill_label(plan_item.skill_id),
                codex_prompt=plan_item.codex_prompt,
                codex_context_endpoint=plan_item.codex_context_endpoint,
                expected_codex_output=expected_codex_output,
                risk=plan_item.risk,
            )
        )
    return decisions


def _daily_decision_state(
    status: Literal["ready", "blocked"],
    freshness: FreshnessState,
) -> DecisionState:
    if status == "blocked":
        return "blocked"
    if freshness.state == "fresh":
        return "ready"
    return freshness.state


def _daily_decision_operator_action(
    plan_item: CommandCenterActionPlanItem,
    decision_state: DecisionState,
) -> str:
    if decision_state == "stale":
        if plan_item.id == "plan_review_merchant_feed_issues":
            return (
                "Najpierw odśwież dane Merchant Center, potem wróć do kolejki problemów "
                "pliku produktowego i sprawdź akcję do sprawdzenia."
            )
        return (
            "Najpierw odśwież dane źródłowe dla tej decyzji, potem wróć do review i "
            "sprawdź akcję do sprawdzenia."
        )
    if decision_state in {"missing", "unknown"}:
        return (
            "Najpierw potwierdź dostęp i świeżość danych źródłowych, potem wróć do "
            "review tej decyzji."
        )
    return plan_item.operator_action


def _daily_decision_expected_codex_output(
    plan_item: CommandCenterActionPlanItem,
    decision_state: DecisionState,
) -> str | None:
    if decision_state == "stale":
        base = plan_item.expected_codex_output or "Polska decyzja operatora z dowodami."
        return (
            f"{base} Zacznij od informacji, że dane wymagają odświeżenia, i podaj "
            "ścieżkę odczytu przed ręcznym review."
        )
    if decision_state in {"missing", "unknown"}:
        return (
            "Polska blokada operatora: czego brakuje w dostępie albo świeżości danych, "
            "jak to potwierdzić i kiedy wrócić do review."
        )
    return plan_item.expected_codex_output


def _daily_decision_domain(category: str) -> str:
    return {
        "Merchant Center": "merchant",
        "Content + SEO": "content",
        "GA4": "ga4",
        "Google Ads": "google_ads",
        "Localo": "localo",
    }.get(category, "wilq")


def _daily_decision_freshness_by_connector(
    connectors: list[ConnectorStatus],
    refresh_runs: list[ConnectorRefreshRun],
) -> dict[str, FreshnessState]:
    freshness_by_connector = {connector.id: connector.freshness for connector in connectors}
    latest_vendor_reads: dict[str, ConnectorRefreshRun] = {}
    for run in refresh_runs:
        if run.mode != ConnectorRefreshMode.vendor_read:
            continue
        if run.status != ConnectorRefreshStatus.completed:
            continue
        if run.completed_at is None:
            continue
        current = latest_vendor_reads.get(run.connector_id)
        if current is None or _as_utc(run.completed_at) > _as_utc(
            current.completed_at or datetime.min.replace(tzinfo=UTC)
        ):
            latest_vendor_reads[run.connector_id] = run
    for connector_id, run in latest_vendor_reads.items():
        completed_at = _as_utc(run.completed_at or run.started_at)
        age = utc_now() - completed_at
        state: Literal["fresh", "stale"] = (
            "fresh" if age <= timedelta(hours=DAILY_DECISION_FRESH_AFTER_HOURS) else "stale"
        )
        freshness_by_connector[connector_id] = FreshnessState(
            state=state,
            last_success_at=completed_at,
            notes=(
                f"Ostatni odczyt danych: {completed_at.isoformat()}. "
                f"Próg świeżości: {DAILY_DECISION_FRESH_AFTER_HOURS}h."
            ),
        )
    return freshness_by_connector


def _combined_decision_freshness(
    source_connectors: list[str],
    freshness_by_connector: dict[str, FreshnessState],
) -> FreshnessState:
    if not source_connectors:
        return FreshnessState(
            state="unknown",
            notes=(
                "Nie ma źródeł danych dla tej decyzji; nie traktuj jej jako "
                "gotowej rekomendacji."
            ),
        )
    states = [
        freshness_by_connector.get(
            connector_id,
            FreshnessState(state="unknown", notes="Brak statusu świeżości źródła."),
        )
        for connector_id in source_connectors
    ]
    state_priority = {"fresh": 0, "unknown": 1, "stale": 2, "missing": 3}
    combined_state = max(
        (state.state for state in states),
        key=lambda value: state_priority.get(value, 1),
    )
    last_success_values = [state.last_success_at for state in states if state.last_success_at]
    notes = ", ".join(
        f"{source_connector_label(connector_id)}: {freshness_state_label(state.state)}"
        for connector_id, state in zip(source_connectors, states, strict=False)
    )
    return FreshnessState(
        state=combined_state,
        last_success_at=min(last_success_values) if last_success_values else None,
        notes=f"Świeżość źródeł decyzji: {notes}.",
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _brief_items_by_plan_id(
    operator_brief: list[CommandCenterBriefItem],
) -> dict[str, CommandCenterBriefItem]:
    items_by_id = {item.id: item for item in operator_brief}
    mapping = {
        "plan_review_merchant_feed_issues": "daily_merchant_feed",
        "plan_prepare_content_refresh_queue": "daily_content_queue",
        "plan_review_ga4_landing_quality": "daily_ga4_landing_quality",
        "plan_review_ads_campaign_metrics": "daily_ads_status",
        "plan_fix_ads_oauth_before_spend_analysis": "daily_ads_status",
        "plan_ads_business_context_before_budget_decisions": "daily_ads_business_context",
        "plan_review_localo_visibility_facts": "daily_localo_visibility_facts",
        "plan_localo_access_ready_wait_for_visibility_facts": "daily_localo_readiness",
        "plan_finish_localo_access_before_local_visibility": "daily_localo_readiness",
    }
    return {
        plan_id: items_by_id[item_id]
        for plan_id, item_id in mapping.items()
        if item_id in items_by_id
    }


def _decision_observation(
    item: CommandCenterActionPlanItem,
    brief_item: CommandCenterBriefItem | None,
) -> str:
    if item.id == "plan_review_merchant_feed_issues" and brief_item is not None:
        return _decision_metric_observation(
            prefix="Merchant Center ma",
            metric_tiles=brief_item.metric_tiles,
            suffix=(
                "To jest kolejka ręcznego sprawdzenia pliku produktowego; WILQ nie twierdzi, że "
                "zatwierdzenie produktu, przychód albo dane produktu zostały już naprawione."
            ),
        )
    if item.id == "plan_prepare_content_refresh_queue" and brief_item is not None:
        return _decision_metric_observation(
            prefix="GSC i WordPress tworzą kolejkę SEO:",
            metric_tiles=brief_item.metric_tiles,
            suffix=(
                "To jest decyzja zachowania, odświeżenia, scalenia, nowej treści "
                "albo blokady oparta o zapytania, adresy i spis treści, nie obietnica "
                "leadów ani wzrostów pozycji."
            ),
        )
    if item.id == "plan_review_ga4_landing_quality" and brief_item is not None:
        if "Blokada oznacza" in brief_item.summary:
            return brief_item.summary
        return (
            f"{brief_item.summary} Blokada oznacza, że nie ma potwierdzonych podstaw "
            "do wniosków o zwrocie z reklam, przychodzie, spadku konwersji "
            "i naprawionym pomiarze; to nie jest awaria źródła danych."
        )
    if item.id == "plan_ads_business_context_before_budget_decisions" and brief_item is not None:
        return (
            f"{brief_item.summary} To blokada decyzji zależnych od celu, nie awaria "
            "Google Ads ani brak aktualnych danych kampanii."
        )
    if item.id == "plan_review_ads_campaign_metrics" and brief_item is not None:
        return _decision_metric_observation(
            prefix="Google Ads ma kolejki do oceny:",
            metric_tiles=brief_item.metric_tiles,
            suffix=(
                "To są kolejki oceny budżetu, rekomendacji, wykluczeń i "
                "segmentów oraz wskaźników kampanii do sprawdzenia. Zapis zmian, ocena "
                "rentowności, kosztu pozyskania celu, zwrotu z reklam i zmarnowanego budżetu "
                "pozostają zablokowane."
            ),
        )
    if item.id == "plan_review_localo_visibility_facts" and brief_item is not None:
        return _decision_metric_observation(
            prefix="Localo ma agregaty z odczytu:",
            metric_tiles=brief_item.metric_tiles,
            suffix=(
                "To pozwala zrobić ostrożny przegląd lokalnej widoczności, ale "
                "profil firmy w Google, konkurencja i poprawa widoczności nadal "
                "wymagają osobnych danych."
            ),
        )
    metric_sentence = ""
    if brief_item and brief_item.metric_tiles:
        metric_sentence = _metric_tiles_sentence(brief_item.metric_tiles) + ". "
    return f"{item.category}: {metric_sentence}{item.why_it_matters}"


def _decision_metric_observation(
    *,
    prefix: str,
    metric_tiles: dict[str, float | int | str],
    suffix: str,
) -> str:
    metric_sentence = _metric_tiles_sentence(metric_tiles)
    if metric_sentence:
        return f"{prefix} {metric_sentence}. {suffix}"
    return suffix
