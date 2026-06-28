from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from wilq.briefing.blocked_claim_labels import operator_blocked_claims
from wilq.briefing.daily_runtime import build_daily_runtime
from wilq.operator_labels import route_operator_label
from wilq.schemas import ActionRisk, DailyDecision
from wilq.workflows.models import Workflow, WorkflowStep


@dataclass(frozen=True)
class WorkflowBlueprint:
    id: str
    label: str
    route: str
    skill_id: str
    description: str
    source_connectors: tuple[str, ...]
    missing_contracts: tuple[str, ...] = ()
    blocked_claims: tuple[str, ...] = ()
    action_ids: tuple[str, ...] = ()
    status: str = "planned"
    risk: ActionRisk = ActionRisk.low


DECISION_WORKFLOW_BY_ROUTE = {
    "/merchant": "merchant_feed_review",
    "/content-planner": "gsc_content_doctor",
    "/ga4": "ga4_data_analyst",
    "/ads-doctor": "ads_daily_check",
}

WORKFLOW_BLUEPRINTS: tuple[WorkflowBlueprint, ...] = (
    WorkflowBlueprint(
        id="monthly_review",
        label="Miesięczny przegląd marketingu",
        route="/command-center",
        skill_id="wilq-daily-command",
        description=(
            "Planowany proces raportowy. Wymaga jeszcze okien porównawczych, "
            "historii zmian i kontraktu raportu dla klienta."
        ),
        source_connectors=(
            "google_ads",
            "google_analytics_4",
            "google_search_console",
            "google_merchant_center",
        ),
        missing_contracts=(
            "monthly_comparison_window",
            "client_report_payload",
            "change_history_summary",
        ),
        blocked_claims=("miesięczny werdykt skuteczności", "raport gotowy dla klienta"),
        risk=ActionRisk.medium,
    ),
    WorkflowBlueprint(
        id="ads_monthly_review",
        label="Miesięczny przegląd Ads",
        route="/ads-doctor",
        skill_id="wilq-ads-doctor",
        description=(
            "Planowany proces Ads. Obecnie WILQ ma dzienną ocenę kampanii, "
            "budżetów, rekomendacji i wyszukiwanych haseł, ale miesięczny werdykt "
            "wymaga pełnych okien zmian i oceny strategicznej."
        ),
        source_connectors=("google_ads",),
        missing_contracts=(
            "pre_post_change_window",
            "human_strategy_review",
            "profit_margin_or_business_goal",
        ),
        blocked_claims=("werdykt zwrotu z reklam", "optymalizacja budżetu", "zapis zmian"),
        risk=ActionRisk.medium,
    ),
    WorkflowBlueprint(
        id="ads_changes_review",
        label="Przegląd historii zmian Ads",
        route="/ads-doctor",
        skill_id="wilq-ads-doctor",
        description=(
            "Planowany proces do odpowiedzi: co zmieniono i jaki był skutek. "
            "Nie zastępuje jeszcze analizy efektu przed i po zmianie."
        ),
        source_connectors=("google_ads",),
        missing_contracts=("pre_post_change_impact", "operator_change_notes"),
        blocked_claims=("przyczynowy wpływ zmian", "odzyskana skuteczność"),
    ),
    WorkflowBlueprint(
        id="ads_search_terms_ngram",
        label="Ocena fragmentów wyszukiwanych haseł",
        route="/ads-doctor",
        skill_id="wilq-ads-doctor",
        description=(
            "Planowany proces analizy fragmentów wyszukiwanych haseł. Bieżący "
            "kontrakt Ads pozwala sprawdzić terminy i bezpieczeństwo wykluczeń, "
            "ale nie ma jeszcze grupowania n-gramów."
        ),
        source_connectors=("google_ads",),
        missing_contracts=("ngram_cluster_contract", "90_day_cross_check_by_ngram"),
        blocked_claims=("zapis wykluczeń", "werdykt przepalonego budżetu"),
    ),
    WorkflowBlueprint(
        id="ads_custom_segments",
        label="Segmenty z wyszukiwanych haseł",
        route="/ads-doctor",
        skill_id="wilq-custom-segments",
        description=(
            "Proces sprawdzania segmentów z realnych wyszukiwanych haseł. "
            "Targetowanie i zapis zmian pozostają poza zakresem."
        ),
        source_connectors=("google_ads",),
        action_ids=("act_prepare_custom_segments_from_search_terms",),
        missing_contracts=("forecast_or_audience_size", "targeting_apply_preview"),
        blocked_claims=("wielkość grupy odbiorców", "zapis kampanii"),
        status="ready",
    ),
    WorkflowBlueprint(
        id="demand_gen_readiness",
        label="Gotowość Demand Gen",
        route="/ads-doctor/demand-gen",
        skill_id="wilq-demand-gen-operator",
        description=(
            "Planowany proces Demand Gen. WILQ może sprawdzać dowody Ads/GA4, "
            "ale pełna ocena wymaga gotowości kreacji i odbiorców."
        ),
        source_connectors=("google_ads", "google_analytics_4"),
        missing_contracts=("creative_asset_readiness", "audience_readiness"),
        blocked_claims=("gotowość uruchomienia Demand Gen", "werdykt jakości kreacji"),
    ),
    WorkflowBlueprint(
        id="ahrefs_gap_finder",
        label="Luki SEO z Ahrefs",
        route="/ahrefs",
        skill_id="wilq-ahrefs-gap-finder",
        description=(
            "Planowany proces luk treści i linków. Obecnie Ahrefs daje kontekst "
            "autorytetu, ale nie pełną macierz luk względem konkurencji."
        ),
        source_connectors=("ahrefs",),
        missing_contracts=("competitor_gap_matrix", "backlink_gap_rows"),
        blocked_claims=("priorytet luk względem konkurencji", "wpływ pozyskanych linków"),
    ),
    WorkflowBlueprint(
        id="localo_visibility_review",
        label="Widoczność lokalna Localo",
        route="/localo",
        skill_id="wilq-localo-operator",
        description=(
            "Planowany proces lokalnej widoczności. Dostęp Localo jest oddzielnym "
            "adapterem; rankingi, GBP i opinie muszą przyjść jako dowody WILQ."
        ),
        source_connectors=("localo",),
        missing_contracts=("local_ranking_rows", "gbp_performance_rows", "review_rows"),
        blocked_claims=("wzrost lokalnych pozycji", "werdykt skuteczności profilu firmy"),
        status="blocked",
        risk=ActionRisk.medium,
    ),
    WorkflowBlueprint(
        id="content_calendar_builder",
        label="Kalendarz treści",
        route="/content-planner",
        skill_id="wilq-content-strategist",
        description=(
            "Planowany proces kalendarza treści. Bieżąca kolejka treści daje "
            "zachowanie, odświeżenie, scalenie, utworzenie albo blokadę, ale nie "
            "publikuje kalendarza ani terminów."
        ),
        source_connectors=(
            "google_search_console",
            "wordpress_ekologus",
            "wordpress_sklep",
            "google_analytics_4",
        ),
        action_ids=("act_prepare_content_refresh_queue",),
        missing_contracts=("editorial_calendar_payload", "owner_due_date_review"),
        blocked_claims=("zatwierdzony harmonogram publikacji", "wzrost liczby leadów"),
    ),
    WorkflowBlueprint(
        id="social_publishing_queue",
        label="Kolejka publikacji social",
        route="/social-publisher",
        skill_id="wilq-social-publisher",
        description=(
            "Proces sprawdzania propozycji LinkedIn/Facebook opartych o dowody "
            "WILQ. Publikacja wymaga oddzielnych uprawnień, podglądu i audytu."
        ),
        source_connectors=("linkedin", "facebook"),
        action_ids=("act_prepare_linkedin_social_drafts", "act_prepare_facebook_social_drafts"),
        missing_contracts=("social_publish_permission", "post_payload_preview"),
        blocked_claims=("opublikowany post", "wzrost skuteczności social"),
        status="blocked",
        risk=ActionRisk.medium,
    ),
)


def list_workflows() -> list[Workflow]:
    runtime = build_daily_runtime()
    decisions_by_route = _best_decisions_by_route(runtime.command_center.daily_decisions)
    workflows = [_daily_command_workflow(runtime.command_center.daily_decisions)]

    for route, workflow_id in DECISION_WORKFLOW_BY_ROUTE.items():
        decision = decisions_by_route.get(route)
        if decision is not None:
            workflows.append(_workflow_from_decision(workflow_id, decision))

    workflows.extend(_workflow_from_blueprint(blueprint) for blueprint in WORKFLOW_BLUEPRINTS)
    return sorted(workflows, key=_workflow_sort_key)


def _best_decisions_by_route(decisions: list[DailyDecision]) -> dict[str, DailyDecision]:
    selected: dict[str, DailyDecision] = {}
    for decision in decisions:
        current = selected.get(decision.route)
        if current is None or _decision_route_rank(decision) < _decision_route_rank(current):
            selected[decision.route] = decision
    return selected


def _decision_route_rank(decision: DailyDecision) -> tuple[int, int]:
    if decision.status == "ready" and decision.action_ids:
        status_rank = 0
    elif decision.status == "ready":
        status_rank = 1
    elif decision.action_ids:
        status_rank = 2
    else:
        status_rank = 3
    return (status_rank, decision.priority)


def _daily_command_workflow(decisions: list[DailyDecision]) -> Workflow:
    evidence_ids = _unique(item for decision in decisions for item in decision.evidence_ids)
    action_ids = _unique(item for decision in decisions for item in decision.action_ids)
    source_connectors = _unique(
        item for decision in decisions for item in decision.source_connectors
    )
    blocked_count = sum(1 for decision in decisions if decision.status == "blocked")
    status: Literal["ready", "blocked"] = "blocked" if blocked_count else "ready"
    risk = ActionRisk.medium if blocked_count else ActionRisk.low
    return Workflow(
        id="daily_command",
        label="Plan dnia WILQ",
        description=(
            "Główny proces pracy: zbiera dzisiejsze decyzje, blokady, akcje do "
            "sprawdzenia i polecenia do Codexa z WILQ API."
        ),
        status=status,
        status_label=_status_label(status),
        route="/command-center",
        route_label=_route_label("/command-center"),
        skill_id="wilq-daily-command",
        safe_next_step="Otwórz Centrum pracy i przejdź decyzje według priorytetu.",
        source_connectors=source_connectors,
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        blocked_claims=operator_blocked_claims(
            item for decision in decisions for item in decision.blocked_claims
        ),
        metric_tiles={
            "decyzje": len(decisions),
            "blokady": blocked_count,
            "źródła": len(source_connectors),
            "akcje": len(action_ids),
        },
        risk=risk,
        risk_label=_risk_label(risk),
        steps=_decision_steps(
            "daily_command",
            source_connectors,
            "Dzisiejsze decyzje, dowody, sprawdzone akcje i polecenia Codexa.",
        ),
    )


def _workflow_from_decision(workflow_id: str, decision: DailyDecision) -> Workflow:
    return Workflow(
        id=workflow_id,
        label=_decision_workflow_label(workflow_id, decision),
        description=f"{decision.co_widzimy} {decision.dlaczego_to_ma_znaczenie}",
        status=decision.status,
        status_label=_status_label(decision.status),
        route=decision.route,
        route_label=_route_label(decision.route),
        skill_id=decision.skill_id,
        safe_next_step=decision.bezpieczny_next_step,
        source_connectors=decision.source_connectors,
        evidence_ids=decision.evidence_ids,
        action_ids=decision.action_ids,
        blocked_claims=operator_blocked_claims(decision.blocked_claims),
        metric_tiles=decision.metric_tiles,
        risk=decision.risk,
        risk_label=_risk_label(decision.risk),
        steps=_decision_steps(
            workflow_id,
            decision.source_connectors,
            "Metryki decyzji, dowody, sprawdzone akcje i blokowane obietnice.",
        ),
    )


def _workflow_from_blueprint(blueprint: WorkflowBlueprint) -> Workflow:
    return Workflow(
        id=blueprint.id,
        label=blueprint.label,
        description=blueprint.description,
        status=blueprint.status,  # type: ignore[arg-type]
        status_label=_status_label(blueprint.status),
        route=blueprint.route,
        route_label=_route_label(blueprint.route),
        skill_id=blueprint.skill_id,
        safe_next_step=_blueprint_next_step(blueprint),
        source_connectors=list(blueprint.source_connectors),
        action_ids=list(blueprint.action_ids),
        blocked_claims=operator_blocked_claims(blueprint.blocked_claims),
        missing_contracts=list(blueprint.missing_contracts),
        risk=blueprint.risk,
        risk_label=_risk_label(blueprint.risk),
        steps=_decision_steps(
            blueprint.id,
            blueprint.source_connectors,
            "Gotowość procesu, braki do domknięcia, dowody i sprawdzone akcje.",
        ),
    )


def _decision_workflow_label(workflow_id: str, decision: DailyDecision) -> str:
    labels = {
        "ads_daily_check": "Ocena Ads",
        "ga4_data_analyst": "Analiza GA4",
        "gsc_content_doctor": "Treści z GSC",
        "merchant_feed_review": "Feed Merchant",
    }
    return labels.get(workflow_id, decision.title)


def _status_label(status: str) -> str:
    labels = {
        "ready": "gotowe",
        "blocked": "zablokowane",
        "planned": "planowane",
    }
    return labels.get(status, status)


def _risk_label(risk: ActionRisk | str) -> str:
    value = risk.value if isinstance(risk, ActionRisk) else risk
    labels = {
        "low": "niskie ryzyko",
        "medium": "średnie ryzyko",
        "high": "wysokie ryzyko",
    }
    return labels.get(value, value)


def _route_label(route: str | None) -> str | None:
    if route is None:
        return None
    return route_operator_label(route)


def _blueprint_next_step(blueprint: WorkflowBlueprint) -> str:
    if blueprint.status == "ready":
        return (
            f"Otwórz widok {_route_label(blueprint.route) or blueprint.label} "
            "i użyj procesu jako oceny bez zapisu zmian."
        )
    if blueprint.status == "blocked":
        return (
            f"Otwórz widok {_route_label(blueprint.route) or blueprint.label} "
            "i potraktuj proces jako zablokowany, dopóki braki do domknięcia "
            "nie będą gotowe."
        )
    missing_count = len(blueprint.missing_contracts)
    missing_phrase = (
        "brakujący warunek"
        if missing_count == 1
        else f"{missing_count} brakujące warunki"
    )
    return (
        "Nie traktuj tego procesu jako gotowej automatyzacji. "
        f"Najpierw domknij {missing_phrase} widoczne w szczegółach technicznych."
    )


def _decision_steps(
    workflow_id: str,
    source_connectors: Iterable[str],
    output_contract: str,
) -> list[WorkflowStep]:
    connectors = list(source_connectors)
    return [
        WorkflowStep(
            id=f"{workflow_id}_context",
            label="Pobierz kontekst z WILQ API",
            required_connectors=connectors,
            output_contract=output_contract,
        ),
        WorkflowStep(
            id=f"{workflow_id}_review",
            label="Zwróć polski wynik do sprawdzenia",
            required_connectors=connectors,
            output_contract="Polish operator output with no invented metrics or unsafe apply.",
        ),
    ]


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _workflow_sort_key(workflow: Workflow) -> tuple[int, str]:
    priority = {
        "daily_command": 0,
        "merchant_feed_review": 10,
        "gsc_content_doctor": 20,
        "ga4_data_analyst": 30,
        "ads_daily_check": 40,
    }.get(workflow.id, 90)
    return (priority, workflow.id)
