"""Decomposed ga4_diagnostics measurement implementation."""

from __future__ import annotations

from typing import Literal

from wilq.briefing.ga4.labels import _ga4_dimension_value_label, _ga4_refresh_status_label
from wilq.briefing.ga4.shared import (
    GA4_CONNECTOR_ID,
    GA4_CONVERSION_METRIC_NAMES,
    GA4_EXPERT_RULE_IDS,
    GA4_KNOWLEDGE_CARD_IDS,
    GA4_STALE_AFTER_HOURS,
    Ga4DecisionType,
    _dimensioned_ga4_facts,
    _ga4_blocker_reason,
    _ga4_metric_tiles,
    _refresh_or_connector_evidence_ids,
    _slug,
    _tactical_landing_group_count,
    _unique,
    _unique_tactical_items,
)
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.schemas import (
    ActionObject,
    ActionRisk,
    ConnectorRefreshRun,
    Ga4DecisionItem,
    Ga4DiagnosticSection,
    Ga4FreshnessAssessment,
    MetricFact,
    TacticalQueueItem,
    connector_refresh_has_live_data,
    utc_now,
)


def _latest_ga4_refresh() -> ConnectorRefreshRun | None:
    runs = list_connector_refresh_runs(connector_id=GA4_CONNECTOR_ID)
    return runs[0] if runs else None


def _ga4_freshness_assessment(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
) -> Ga4FreshnessAssessment:
    if latest_refresh is None:
        fact_collected_dates = [
            fact.collected_at for fact in facts if fact.collected_at is not None
        ]
        if fact_collected_dates:
            latest_fact_collected_at = max(fact_collected_dates)
            age_hours = round((utc_now() - latest_fact_collected_at).total_seconds() / 3600, 2)
            if age_hours > GA4_STALE_AFTER_HOURS:
                return Ga4FreshnessAssessment(
                    state="stale",
                    latest_refresh_id=None,
                    latest_refresh_completed_at=latest_fact_collected_at,
                    age_hours=age_hours,
                    stale_after_hours=GA4_STALE_AFTER_HOURS,
                    requires_refresh=True,
                    summary=(
                        f"Najnowsze metryki GA4 mają około {age_hours:.1f}h i są do odświeżenia."
                    ),
                    next_step=(
                        "Uruchom odczyt danych GA4, jeśli pytanie dotyczy "
                        "aktualnego stanu stron wejścia, źródeł ruchu albo kampanii."
                    ),
                )
            return Ga4FreshnessAssessment(
                state="fresh",
                latest_refresh_id=None,
                latest_refresh_completed_at=latest_fact_collected_at,
                age_hours=age_hours,
                stale_after_hours=GA4_STALE_AFTER_HOURS,
                requires_refresh=False,
                summary=(
                    f"Najnowsze metryki GA4 mają około {age_hours:.1f}h i mieszczą się "
                    f"w progu {GA4_STALE_AFTER_HOURS}h."
                ),
                next_step="Można użyć danych GA4 do sprawdzenia bez dodatkowego odświeżenia.",
            )
        return Ga4FreshnessAssessment(
            state="missing",
            latest_refresh_id=None,
            latest_refresh_completed_at=None,
            age_hours=None,
            stale_after_hours=GA4_STALE_AFTER_HOURS,
            requires_refresh=True,
            summary="Brak zapisanego odczytu danych GA4.",
            next_step="Uruchom odczyt danych GA4 przed oceną aktualnej jakości ruchu.",
        )

    completed_at = latest_refresh.completed_at or latest_refresh.started_at
    age_hours = round((utc_now() - completed_at).total_seconds() / 3600, 2)
    if not connector_refresh_has_live_data(latest_refresh):
        return Ga4FreshnessAssessment(
            state="blocked",
            latest_refresh_id=latest_refresh.id,
            latest_refresh_completed_at=completed_at,
            age_hours=age_hours,
            stale_after_hours=GA4_STALE_AFTER_HOURS,
            requires_refresh=True,
            summary=(
                "Ostatni odczyt GA4 nie zakończył się pełnym pobraniem metryk. "
                f"Status odczytu: {_ga4_refresh_status_label(latest_refresh)}."
            ),
            next_step=(
                "Napraw blocker odczytu i uruchom ponownie odczyt danych GA4 przed "
                "wnioskami o aktualnej jakości ruchu."
            ),
        )

    if age_hours > GA4_STALE_AFTER_HOURS:
        return Ga4FreshnessAssessment(
            state="stale",
            latest_refresh_id=latest_refresh.id,
            latest_refresh_completed_at=completed_at,
            age_hours=age_hours,
            stale_after_hours=GA4_STALE_AFTER_HOURS,
            requires_refresh=True,
            summary=(
                f"Ostatni odczyt danych GA4 ma około {age_hours:.1f}h i jest do odświeżenia. "
                "To wystarcza do przeglądu nieświeżych danych, "
                "ale nie do obietnic o bieżącym stanie ruchu."
            ),
            next_step=(
                "Uruchom odczyt danych GA4, jeśli pytanie dotyczy aktualnego "
                "stanu stron wejścia, źródeł ruchu albo kampanii."
            ),
        )

    return Ga4FreshnessAssessment(
        state="fresh",
        latest_refresh_id=latest_refresh.id,
        latest_refresh_completed_at=completed_at,
        age_hours=age_hours,
        stale_after_hours=GA4_STALE_AFTER_HOURS,
        requires_refresh=False,
        summary=(
            f"Ostatni odczyt danych GA4 ma około {age_hours:.1f}h i mieści się "
            f"w progu {GA4_STALE_AFTER_HOURS}h."
        ),
        next_step="Można użyć danych GA4 do sprawdzenia bez dodatkowego odświeżenia.",
    )


def _ga4_action_ids(actions: list[ActionObject]) -> list[str]:
    return [action.id for action in actions if action.connector == GA4_CONNECTOR_ID]


def _tracking_readiness_section(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> Ga4DiagnosticSection:
    conversion_like_facts = [fact for fact in facts if fact.name in GA4_CONVERSION_METRIC_NAMES]
    dimensioned_facts = _dimensioned_ga4_facts(facts)
    tactical_group_count = _tactical_landing_group_count(tactical_items)
    if not facts:
        return Ga4DiagnosticSection(
            id="ga4_tracking_readiness",
            title="GA4: brak metryk zachowania",
            status="blocked",
            summary=_ga4_blocker_reason(latest_refresh),
            diagnosis="Brak metryk GA4 oznacza blokadę pomiaru, nie spadek jakości ruchu.",
            next_step="Odśwież odczyt GA4 i dopiero potem sprawdzaj problemy pomiaru.",
            source_connectors=[GA4_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            action_ids=action_ids,
            blocked_claims=["brak w pomiarze", "spadek konwersji", "spadek w lejku"],
            risk=ActionRisk.medium,
        )
    return Ga4DiagnosticSection(
        id="ga4_tracking_readiness",
        title="GA4: gotowość pomiaru konwersji",
        status="ready" if conversion_like_facts else "missing",
        summary=(
            f"WILQ ma {len(dimensioned_facts)} metryk zachowania, "
            f"{tactical_group_count} grup stron wejścia i "
            f"{len(conversion_like_facts)} metryk konwersji albo kluczowych zdarzeń."
        ),
        diagnosis=(
            "Aktualne dane wspierają ocenę jakości ruchu. Jeżeli brakuje metryk "
            "konwersji albo kluczowych zdarzeń, WILQ musi oznaczyć konwersje jako "
            "brakujący wymiar analizy."
        ),
        next_step=(
            "Sprawdź propozycję w WILQ i przygotuj checklistę jakości pomiaru bez zapisu zmian."
        ),
        source_connectors=[GA4_CONNECTOR_ID],
        evidence_ids=_unique(fact.evidence_id for fact in facts[:20]),
        metric_facts=[*dimensioned_facts[:8], *conversion_like_facts[:4]],
        tactical_items=tactical_items[:4],
        action_ids=action_ids,
        blocked_claims=[
            "spadek konwersji",
            "diagnoza lejka",
            "ocena atrybucji",
        ],
        risk=ActionRisk.low if conversion_like_facts else ActionRisk.medium,
    )


def _ga4_action_safety_section(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> Ga4DiagnosticSection:
    return Ga4DiagnosticSection(
        id="ga4_action_safety",
        title="Bezpieczeństwo akcji GA4",
        status="ready" if facts or tactical_items else "blocked",
        summary="Akcje GA4 pozostają w trybie przygotowania i nie zapisują zmian w pomiarze.",
        diagnosis=(
            "WILQ może przygotować listę sprawdzenia jakości pomiaru "
            "i przegląd stron wejścia. Nie może "
            "zmieniać konfiguracji GA4 ani twierdzić, że naprawił pomiar bez osobnego "
            "potwierdzenia, sprawdzenia i audytu."
        ),
        next_step="Sprawdź jakość pomiaru w WILQ i zatrzymaj zapis zmian.",
        source_connectors=[GA4_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        action_ids=action_ids,
        blocked_claims=["zapis w GA4", "wdrożona konfiguracja konwersji", "naprawiony pomiar"],
        risk=ActionRisk.medium,
    )


def _ga4_decision_queue(
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
    dimensioned_facts: list[MetricFact],
) -> list[Ga4DecisionItem]:
    decisions: list[Ga4DecisionItem] = []
    for index, item in enumerate(_unique_tactical_items(tactical_items), start=1):
        landing_page = item.dimensions.get("landing_page")
        source_medium = item.dimensions.get("source_medium")
        campaign_name = item.dimensions.get("campaign_name")
        wordpress_match = item.dimensions.get("wordpress_match")
        has_missing_reporting_dimension = any(
            value == "(not set)" for value in (landing_page, source_medium, campaign_name)
        )
        if item.intent == "tracking_gap" or has_missing_reporting_dimension:
            decision_type: Ga4DecisionType = "fix_measurement"
            title = _ga4_measurement_title(landing_page, source_medium)
            rationale = (
                "GA4 zwraca brakujące wymiary raportu, więc to jest problem pomiaru "
                "albo atrybucji, nie gotowa rekomendacja marketingowa."
            )
            next_step = (
                "Sprawdź stronę wejścia, źródło i medium ruchu, UTM-y i konfigurację raportu. "
                "Nie oceniaj kampanii ani strony po tym wierszu."
            )
            risk = ActionRisk.medium
        elif wordpress_match == "missing":
            decision_type = "review_landing_mapping"
            title = f"Sprawdź stronę wejścia: {landing_page or 'brak strony wejścia'}"
            rationale = (
                "GA4 widzi ruch, ale spis treści WordPress nie potwierdza tej strony. "
                "Najpierw trzeba sprawdzić, czy URL istnieje i jest poprawnym adresem, "
                "zanim powstanie wniosek o treści."
            )
            next_step = (
                "Zweryfikuj, czy strona wejścia istnieje w WordPress lub mapie strony, "
                "a potem sprawdź "
                "dopasowanie komunikatu dla kampanii."
            )
            risk = ActionRisk.medium
        else:
            decision_type = "review_traffic_quality"
            title = f"Sprawdź jakość ruchu: {landing_page or 'brak strony wejścia'}"
            rationale = (
                "GA4 pokazuje ruch dla potwierdzonej strony wejścia. To wystarcza do "
                "oceny jakości ruchu i dopasowania komunikatu, ale nie do obietnic konwersji."
            )
            next_step = (
                "Porównaj stronę wejścia, źródło ruchu i kampanię z intencją strony. "
                "Nie oceniaj zwrotu z reklam "
                "ani przychodu bez osobnych metryk konwersji i kosztów."
            )
            risk = ActionRisk.low
        decisions.append(
            Ga4DecisionItem(
                id=f"ga4_decision_{_slug(item.id)}",
                decision_type=decision_type,
                title=title,
                status=_ga4_decision_status(decision_type),
                priority=_ga4_decision_priority(decision_type, index),
                metric_tiles=_ga4_metric_tiles(item.metric_facts),
                landing_page=landing_page,
                source_medium=source_medium,
                campaign_name=campaign_name,
                wordpress_match=wordpress_match,
                wordpress_match_confidence=item.dimensions.get("wordpress_match_confidence"),
                wordpress_content_url=item.dimensions.get("wordpress_content_url"),
                source_connectors=item.source_connectors,
                evidence_ids=item.evidence_ids,
                metric_facts=item.metric_facts[:8],
                action_ids=_unique([*item.action_ids, *action_ids]),
                blocked_claims=_unique(
                    [
                        *item.blocked_claims,
                        "współczynnik konwersji",
                        "zwrot z reklam",
                        "przychód",
                        "opłacalność",
                    ]
                ),
                rationale=rationale,
                next_step=next_step,
                risk=risk,
            )
        )
    if not decisions:
        decisions.extend(_ga4_decisions_from_dimensioned_facts(dimensioned_facts, action_ids))
    return sorted(decisions, key=lambda decision: (decision.priority, decision.id))[:6]


def _ga4_decisions_with_lineage(decisions: list[Ga4DecisionItem]) -> list[Ga4DecisionItem]:
    return [
        decision.model_copy(
            update={
                "knowledge_card_ids": _unique(
                    [*decision.knowledge_card_ids, *GA4_KNOWLEDGE_CARD_IDS]
                ),
                "expert_rule_ids": _unique([*decision.expert_rule_ids, *GA4_EXPERT_RULE_IDS]),
            }
        )
        for decision in decisions
    ]


def _ga4_decisions_from_dimensioned_facts(
    facts: list[MetricFact],
    action_ids: list[str],
) -> list[Ga4DecisionItem]:
    grouped: dict[tuple[str, str, str], list[MetricFact]] = {}
    for fact in facts:
        key = (
            fact.dimensions.get("landing_page", ""),
            fact.dimensions.get("source_medium", ""),
            fact.dimensions.get("campaign_name", ""),
        )
        grouped.setdefault(key, []).append(fact)

    decisions: list[Ga4DecisionItem] = []
    for index, ((landing_page, source_medium, campaign_name), group_facts) in enumerate(
        grouped.items(),
        start=1,
    ):
        has_missing_reporting_dimension = any(
            value == "(not set)" for value in (landing_page, source_medium, campaign_name)
        )
        if has_missing_reporting_dimension:
            decision_type: Ga4DecisionType = "fix_measurement"
            title = _ga4_measurement_title(landing_page, source_medium)
            rationale = (
                "GA4 ma wymiar `(not set)`, więc najpierw trzeba sprawdzić pomiar, "
                "UTM-y i atrybucję zamiast oceniać kampanię lub stronę wejścia."
            )
            next_step = (
                "Zweryfikuj stronę wejścia, źródło i medium ruchu oraz nazwę kampanii w GA4. "
                "Nie oceniaj jakości kampanii po wierszu z brakującymi wymiarami."
            )
            risk = ActionRisk.medium
        else:
            decision_type = "review_traffic_quality"
            title = f"Sprawdź jakość ruchu: {landing_page}"
            rationale = (
                "GA4 ma fakty strony wejścia, źródła ruchu i kampanii. "
                "To wystarcza do sprawdzenia jakości ruchu i dopasowania komunikatu, "
                "ale nie do obietnic zwrotu z reklam albo przychodu."
            )
            next_step = (
                "Porównaj stronę wejścia, źródło ruchu i kampanię z intencją strony. Jeśli trzeba, "
                "sprawdź jakość pomiaru w WILQ jako akcję do sprawdzenia."
            )
            risk = ActionRisk.low

        decisions.append(
            Ga4DecisionItem(
                id=(
                    "ga4_decision_metric_"
                    f"{_slug(landing_page)}_{_slug(source_medium)}_{_slug(campaign_name)}"
                ),
                decision_type=decision_type,
                title=title,
                status=_ga4_decision_status(decision_type),
                priority=_ga4_decision_priority(decision_type, index),
                metric_tiles=_ga4_metric_tiles(group_facts),
                landing_page=landing_page,
                source_medium=source_medium,
                campaign_name=campaign_name,
                source_connectors=[GA4_CONNECTOR_ID],
                evidence_ids=_unique(fact.evidence_id for fact in group_facts),
                metric_facts=group_facts[:8],
                action_ids=action_ids,
                blocked_claims=[
                    "współczynnik konwersji",
                    "zwrot z reklam",
                    "przychód",
                    "opłacalność",
                ],
                rationale=rationale,
                next_step=next_step,
                risk=risk,
            )
        )
    return decisions


def _ga4_measurement_title(landing_page: str | None, source_medium: str | None) -> str:
    landing_label = _ga4_dimension_value_label(
        landing_page,
        missing_label="brak strony wejścia w raporcie",
    )
    source_label = _ga4_dimension_value_label(
        source_medium,
        missing_label="brak źródła i medium w raporcie",
    )
    return f"GA4: napraw pomiar - {landing_label}; źródło ruchu: {source_label}"


def _ga4_decision_status(decision_type: Ga4DecisionType) -> Literal["ready", "blocked"]:
    if decision_type in {"fix_measurement", "review_landing_mapping"}:
        return "blocked"
    return "ready"


def _ga4_decision_priority(decision_type: Ga4DecisionType, index: int) -> int:
    base_priority = {
        "fix_measurement": 10,
        "review_landing_mapping": 30,
        "review_traffic_quality": 50,
    }[decision_type]
    return min(base_priority + index, 100)
