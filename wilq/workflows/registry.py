from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from wilq.briefing.daily_runtime import build_daily_runtime
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
            "Planowany workflow raportowy. Wymaga jeszcze okien porównawczych, "
            "historii zmian i klient-ready report contract."
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
        blocked_claims=("monthly performance verdict", "client-ready report"),
        risk=ActionRisk.medium,
    ),
    WorkflowBlueprint(
        id="ads_monthly_review",
        label="Miesięczny przegląd Ads",
        route="/ads-doctor",
        skill_id="wilq-ads-doctor",
        description=(
            "Planowany workflow Ads. Obecnie WILQ ma dzienne review kampanii, "
            "budżetów, rekomendacji i search terms, ale miesięczny werdykt wymaga "
            "pełnych okien zmian i review strategicznego."
        ),
        source_connectors=("google_ads",),
        missing_contracts=(
            "pre_post_change_window",
            "human_strategy_review",
            "profit_margin_or_business_goal",
        ),
        blocked_claims=("ROAS verdict", "budget optimization", "apply changes"),
        risk=ActionRisk.medium,
    ),
    WorkflowBlueprint(
        id="ads_changes_review",
        label="Przegląd historii zmian Ads",
        route="/ads-doctor",
        skill_id="wilq-ads-doctor",
        description=(
            "Planowany workflow do odpowiedzi: co zmieniono i jaki był skutek. "
            "Nie zastępuje jeszcze pre/post impact analysis."
        ),
        source_connectors=("google_ads",),
        missing_contracts=("pre_post_change_impact", "operator_change_notes"),
        blocked_claims=("causal impact", "performance recovered"),
    ),
    WorkflowBlueprint(
        id="ads_search_terms_ngram",
        label="N-gram review search terms",
        route="/ads-doctor",
        skill_id="wilq-ads-doctor",
        description=(
            "Planowany workflow analizy fragmentów search terms. Bieżący Ads "
            "contract pozwala na review terminów i negative keyword safety, ale "
            "nie ma jeszcze n-gram clustering contract."
        ),
        source_connectors=("google_ads",),
        missing_contracts=("ngram_cluster_contract", "90_day_cross_check_by_ngram"),
        blocked_claims=("negative keyword apply", "wasted budget verdict"),
    ),
    WorkflowBlueprint(
        id="ads_custom_segments",
        label="Custom segments z search terms",
        route="/ads-doctor",
        skill_id="wilq-custom-segments",
        description=(
            "Review-only workflow dla kandydatów custom segments z realnych search "
            "terms. Targeting/apply pozostaje poza zakresem."
        ),
        source_connectors=("google_ads",),
        action_ids=("act_prepare_custom_segments_from_search_terms",),
        missing_contracts=("forecast_or_audience_size", "targeting_apply_preview"),
        blocked_claims=("audience size", "campaign apply"),
        status="ready",
    ),
    WorkflowBlueprint(
        id="demand_gen_readiness",
        label="Demand Gen readiness",
        route="/ads-doctor/demand-gen",
        skill_id="wilq-demand-gen-operator",
        description=(
            "Planowany workflow Demand Gen. WILQ może sprawdzać Ads/GA4 evidence, "
            "ale pełna ocena wymaga creative asset i audience readiness contracts."
        ),
        source_connectors=("google_ads", "google_analytics_4"),
        missing_contracts=("creative_asset_readiness", "audience_readiness"),
        blocked_claims=("Demand Gen launch ready", "creative quality verdict"),
    ),
    WorkflowBlueprint(
        id="ahrefs_gap_finder",
        label="Ahrefs gap finder",
        route="/ahrefs",
        skill_id="wilq-ahrefs-gap-finder",
        description=(
            "Planowany workflow content/backlink gap. Obecnie Ahrefs daje context "
            "authority, ale nie pełną konkurencyjną gap matrix."
        ),
        source_connectors=("ahrefs",),
        missing_contracts=("competitor_gap_matrix", "backlink_gap_rows"),
        blocked_claims=("competitor gap priority", "link acquisition impact"),
    ),
    WorkflowBlueprint(
        id="localo_visibility_review",
        label="Localo visibility review",
        route="/localo",
        skill_id="wilq-localo-operator",
        description=(
            "Planowany workflow lokalnej widoczności. Localo access jest oddzielnym "
            "adapterem; ranking/GBP/review metrics muszą przyjść przez WILQ evidence."
        ),
        source_connectors=("localo",),
        missing_contracts=("local_ranking_rows", "gbp_performance_rows", "review_rows"),
        blocked_claims=("local ranking uplift", "GBP performance verdict"),
        status="blocked",
        risk=ActionRisk.medium,
    ),
    WorkflowBlueprint(
        id="content_calendar_builder",
        label="Content calendar builder",
        route="/content-planner",
        skill_id="wilq-content-strategist",
        description=(
            "Planowany workflow kalendarza treści. Bieżący content queue daje "
            "refresh/merge/create/block, ale nie publikuje kalendarza ani terminów."
        ),
        source_connectors=(
            "google_search_console",
            "wordpress_ekologus",
            "wordpress_sklep",
            "google_analytics_4",
        ),
        action_ids=("act_prepare_content_refresh_queue",),
        missing_contracts=("editorial_calendar_payload", "owner_due_date_review"),
        blocked_claims=("publishing schedule approved", "lead uplift"),
    ),
    WorkflowBlueprint(
        id="social_publishing_queue",
        label="Social publishing queue",
        route="/social-publisher",
        skill_id="wilq-social-publisher",
        description=(
            "Review-only workflow do kandydatów LinkedIn/Facebook opartych o WILQ "
            "evidence. Publikacja wymaga oddzielnych uprawnień, preview i audytu."
        ),
        source_connectors=("linkedin", "facebook"),
        action_ids=("act_prepare_linkedin_social_drafts", "act_prepare_facebook_social_drafts"),
        missing_contracts=("social_publish_permission", "post_payload_preview"),
        blocked_claims=("post published", "social performance uplift"),
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
    return Workflow(
        id="daily_command",
        label="Plan dnia WILQ",
        description=(
            "Główny workflow operatora: zbiera dzisiejsze decyzje, blockery, "
            "ActionObjecty i prompty do Codexa z WILQ API."
        ),
        status="blocked" if blocked_count else "ready",
        route="/command-center",
        skill_id="wilq-daily-command",
        safe_next_step="Otwórz Command Center i przejdź decyzje według priorytetu.",
        source_connectors=source_connectors,
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        blocked_claims=_unique(
            item for decision in decisions for item in decision.blocked_claims
        ),
        metric_tiles={
            "decyzje": len(decisions),
            "blockery": blocked_count,
            "źródła": len(source_connectors),
            "akcje": len(action_ids),
        },
        risk=ActionRisk.medium if blocked_count else ActionRisk.low,
        steps=_decision_steps(
            "daily_command",
            source_connectors,
            "Daily decisions, evidence IDs, ActionObject IDs and Codex prompts.",
        ),
    )


def _workflow_from_decision(workflow_id: str, decision: DailyDecision) -> Workflow:
    return Workflow(
        id=workflow_id,
        label=_decision_workflow_label(workflow_id, decision),
        description=f"{decision.co_widzimy} {decision.dlaczego_to_ma_znaczenie}",
        status=decision.status,
        route=decision.route,
        skill_id=decision.skill_id,
        safe_next_step=decision.bezpieczny_next_step,
        source_connectors=decision.source_connectors,
        evidence_ids=decision.evidence_ids,
        action_ids=decision.action_ids,
        blocked_claims=decision.blocked_claims,
        metric_tiles=decision.metric_tiles,
        risk=decision.risk,
        steps=_decision_steps(
            workflow_id,
            decision.source_connectors,
            "Decision metric tiles, evidence IDs, ActionObject IDs and blocked claims.",
        ),
    )


def _workflow_from_blueprint(blueprint: WorkflowBlueprint) -> Workflow:
    return Workflow(
        id=blueprint.id,
        label=blueprint.label,
        description=blueprint.description,
        status=blueprint.status,  # type: ignore[arg-type]
        route=blueprint.route,
        skill_id=blueprint.skill_id,
        safe_next_step=_blueprint_next_step(blueprint),
        source_connectors=list(blueprint.source_connectors),
        action_ids=list(blueprint.action_ids),
        blocked_claims=list(blueprint.blocked_claims),
        missing_contracts=list(blueprint.missing_contracts),
        risk=blueprint.risk,
        steps=_decision_steps(
            blueprint.id,
            blueprint.source_connectors,
            "Workflow readiness, missing contracts, evidence IDs and ActionObject IDs.",
        ),
    )


def _decision_workflow_label(workflow_id: str, decision: DailyDecision) -> str:
    labels = {
        "ads_daily_check": "Ads daily check",
        "ga4_data_analyst": "GA4 data analyst",
        "gsc_content_doctor": "GSC content doctor",
        "merchant_feed_review": "Merchant feed review",
    }
    return labels.get(workflow_id, decision.title)


def _blueprint_next_step(blueprint: WorkflowBlueprint) -> str:
    if blueprint.status == "ready":
        return f"Otwórz {blueprint.route} i użyj workflow tylko jako review-only."
    if blueprint.status == "blocked":
        return (
            f"Otwórz {blueprint.route} i potraktuj workflow jako blocker, dopóki "
            "brakujące kontrakty nie będą gotowe."
        )
    return (
        f"Nie traktuj tego workflow jako gotowej automatyzacji. Najpierw domknij: "
        f"{', '.join(blueprint.missing_contracts)}."
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
            label="Zwróć polski wynik review-only",
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
