"""Ahrefs diagnostics assembly and operator-facing response construction."""
from __future__ import annotations

from typing import Any, cast

from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.operator_labels import evidence_count_label, source_connector_labels
from wilq.schemas import (
    ActionRisk,
    AhrefsDecisionItem,
    AhrefsDiagnosticSection,
    AhrefsDiagnosticsResponse,
    AhrefsGapReadContract,
    AhrefsOperatorSummary,
    AhrefsRequestBudget,
    AhrefsRequestBudgetStage,
    ConnectorRefreshRun,
    MetricFact,
)
from wilq.storage.metric_store import metric_store

from .authority import (
    _authority_summary,
    _authority_tiles,
    _competitor_read_summary,
    _missing_authority_summary,
)
from .gap_records import (
    AHREFS_GAP_BLOCKED_CLAIMS,
    AHREFS_GAP_READ_CONTRACTS,
    _ahrefs_gap_read_contract,
    _ahrefs_gap_records,
    _allowed_gap_evidence,
    _blocked_claims_for_missing_contracts,
    _gap_record_tiles,
    _missing_gap_contracts,
    _missing_gap_contracts_summary,
)
from .labels import (
    _ahrefs_budget_stage_status_label,
    _ahrefs_connector_status_label,
    _ahrefs_decision_type_label,
    _ahrefs_gap_record_count_label,
    _ahrefs_live_data_status_label,
    _ahrefs_metric_fact_label,
    _ahrefs_read_contract_label,
    _ahrefs_refresh_status_label,
    _label_ahrefs_decision,
    _label_ahrefs_gap_read_contract,
    _label_ahrefs_operator_summary,
    _label_ahrefs_section,
    _labels_for_values,
    _metric_fact_labels_for_facts,
    _missing_gap_contract_label,
)
from .shared import (
    AHREFS_AUTHORITY_FACT_NAMES,
    AHREFS_COMPETITOR_READ_FACT_NAMES,
    AHREFS_CONNECTOR_ID,
    AHREFS_CONTENT_REFRESH_ACTION_ID,
    AHREFS_EXPERT_RULE_IDS,
    AHREFS_KNOWLEDGE_CARD_IDS,
    AHREFS_METRIC_FACT_LIMIT,
    AhrefsBudgetStageStatus,
    _cross_check_metric_facts,
    _evidence_ids_for_facts_or_refresh,
    _facts_for_known_refresh_runs,
    _gap_facts,
    _latest_facts_by_name,
    _latest_relevant_ahrefs_refresh,
    _refresh_or_connector_evidence_ids,
    _unique,
)


def build_ahrefs_diagnostics() -> AhrefsDiagnosticsResponse:
    connector = get_connector_status(AHREFS_CONNECTOR_ID)
    if connector is None:
        raise RuntimeError("Ahrefs connector is not registered.")

    refresh_runs = list_connector_refresh_runs(connector_id=AHREFS_CONNECTOR_ID)
    latest_refresh = _latest_relevant_ahrefs_refresh(refresh_runs)
    metric_facts = _facts_for_known_refresh_runs(
        metric_store().list_metric_facts(
            connector_id=AHREFS_CONNECTOR_ID,
            limit=AHREFS_METRIC_FACT_LIMIT,
        ),
        refresh_runs,
        latest_refresh=latest_refresh,
    )
    authority_facts = _latest_facts_by_name(metric_facts, AHREFS_AUTHORITY_FACT_NAMES)
    competitor_read_facts = _latest_facts_by_name(
        metric_facts,
        AHREFS_COMPETITOR_READ_FACT_NAMES,
    )
    gap_facts = _gap_facts(metric_facts)
    cross_check_facts = _cross_check_metric_facts()
    live_data_available = bool(authority_facts or competitor_read_facts or gap_facts)
    sections = _ahrefs_sections(
        connector_missing=connector.missing_credentials,
        latest_refresh=latest_refresh,
        authority_facts=authority_facts,
        competitor_read_facts=competitor_read_facts,
        gap_facts=gap_facts,
    )
    decision_queue = _ahrefs_decisions_with_lineage(
        _ahrefs_decision_queue(
            connector_missing=connector.missing_credentials,
            latest_refresh=latest_refresh,
            authority_facts=authority_facts,
            competitor_read_facts=competitor_read_facts,
            gap_facts=gap_facts,
        )
    )
    gap_read_contract = _ahrefs_gap_read_contract(
        latest_refresh=latest_refresh,
        authority_facts=authority_facts,
        gap_facts=gap_facts,
        cross_check_facts=cross_check_facts,
    )
    labeled_gap_read_contract = _label_ahrefs_gap_read_contract(gap_read_contract)

    evidence_ids = _unique(
        [
            *(evidence_id for section in sections for evidence_id in section.evidence_ids),
            *(evidence_id for decision in decision_queue for evidence_id in decision.evidence_ids),
            *labeled_gap_read_contract.evidence_ids,
        ]
    )
    action_ids = _unique(
        [
            *(action_id for section in sections for action_id in section.action_ids),
            *(action_id for decision in decision_queue for action_id in decision.action_ids),
            *labeled_gap_read_contract.action_ids,
        ]
    )
    response_source_connectors = _unique(
        [
            *(connector for section in sections for connector in section.source_connectors),
            *(connector for decision in decision_queue for connector in decision.source_connectors),
            *labeled_gap_read_contract.source_connectors,
        ]
    )
    return AhrefsDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector=connector,
        connector_status_label=_ahrefs_connector_status_label(str(connector.status)),
        latest_refresh=latest_refresh,
        latest_refresh_status_label=_ahrefs_refresh_status_label(latest_refresh)
        if latest_refresh
        else None,
        request_budget=_ahrefs_request_budget(latest_refresh),
        live_data_status_label=_ahrefs_live_data_status_label(live_data_available),
        live_data_available=live_data_available,
        authority_fact_count=len(authority_facts),
        gap_fact_count=len(gap_facts),
        gap_read_contract=labeled_gap_read_contract,
        operator_summary=_operator_summary(
            decision_queue,
            labeled_gap_read_contract,
            len(authority_facts),
            len(gap_facts),
        ),
        decision_queue=decision_queue,
        sections=[_label_ahrefs_section(section) for section in sections],
        evidence_ids=evidence_ids,
        evidence_summary_label=evidence_count_label(evidence_ids),
        source_connector_labels=source_connector_labels(response_source_connectors),
        action_ids=action_ids,
        blocker_count=sum(1 for decision in decision_queue if decision.status == "blocked"),
    )

def _ahrefs_request_budget(
    latest_refresh: ConnectorRefreshRun | None,
) -> AhrefsRequestBudget:
    if latest_refresh is None:
        return AhrefsRequestBudget(summary="Brak odczytu Ahrefs do rozliczenia.")
    summary = latest_refresh.metric_summary
    competitor_calls = int(summary.get("organic_competitor_rows", 0))
    top_page_calls = int(summary.get("top_pages_by_competitor_competitors", 0))
    keyword_calls = int(summary.get("organic_keywords_by_url_urls", 0))
    content_calls = int(bool(summary.get("content_gap_competitor_keywords", 0)))
    backlink_competitor_calls = int(summary.get("backlink_gap_competitors", 0))
    stages = [
        _ahrefs_budget_stage(
            "domain_rating",
            "Domain Rating",
            summary,
            status_key=None,
            requested_calls=1,
            rows=int(bool(summary.get("domain_rating"))),
            latest_errors=latest_refresh.errors,
        ),
        _ahrefs_budget_stage(
            "organic_competitors",
            "Konkurenci organiczni",
            summary,
            status_key="organic_competitor_read_status",
            requested_calls=1,
            rows=competitor_calls,
            latest_errors=latest_refresh.errors,
        ),
        _ahrefs_budget_stage(
            "top_pages_by_competitor",
            "Najlepsze strony konkurencji",
            summary,
            status_key="top_pages_by_competitor_read_status",
            requested_calls=top_page_calls,
            rows=int(summary.get("top_pages_by_competitor_rows", 0)),
            latest_errors=latest_refresh.errors,
        ),
        _ahrefs_budget_stage(
            "organic_keywords_by_url",
            "Organiczne słowa dla URL",
            summary,
            status_key="organic_keywords_by_url_read_status",
            requested_calls=keyword_calls,
            rows=int(summary.get("organic_keywords_by_url_rows", 0)),
            latest_errors=latest_refresh.errors,
        ),
        _ahrefs_budget_stage(
            "content_gap",
            "Luki treści",
            summary,
            status_key="content_gap_read_status",
            requested_calls=content_calls,
            rows=int(summary.get("content_gap_rows", 0)),
            latest_errors=latest_refresh.errors,
        ),
        _ahrefs_budget_stage(
            "backlink_gap",
            "Luki linków zwrotnych",
            summary,
            status_key="backlink_gap_read_status",
            requested_calls=(1 + backlink_competitor_calls)
            if backlink_competitor_calls
            else 0,
            rows=int(summary.get("backlink_gap_rows", 0)),
            latest_errors=latest_refresh.errors,
        ),
    ]
    failed = sum(stage.status == "failed" for stage in stages)
    estimated = sum(stage.requested_calls for stage in stages)
    return AhrefsRequestBudget(
        estimated_calls=estimated,
        failed_stages=failed,
        partial=failed > 0,
        stages=stages,
        summary=(
            f"Szacowany zakres odczytu: {estimated} wywołań; "
            f"nieudane etapy: {failed}."
        ),
    )

def _ahrefs_budget_stage(
    stage_id: str,
    label: str,
    summary: dict[str, float | int | str],
    *,
    status_key: str | None,
    requested_calls: int,
    rows: int,
    latest_errors: list[str],
) -> AhrefsRequestBudgetStage:
    raw_status = summary.get(status_key) if status_key else None
    if status_key is None:
        status: AhrefsBudgetStageStatus = "completed" if summary.get("domain_rating") else (
            "failed" if latest_errors else "not_run"
        )
    elif isinstance(raw_status, str) and raw_status == "completed":
        status = "completed"
    elif isinstance(raw_status, str) and raw_status.startswith("skipped"):
        status = "skipped"
    elif raw_status:
        status = "failed"
    else:
        status = "not_run"
    return AhrefsRequestBudgetStage(
        id=cast(Any, stage_id),
        label=label,
        status=status,
        status_label=_ahrefs_budget_stage_status_label(status),
        requested_calls=max(0, requested_calls),
        rows=max(0, rows),
        summary=(
            f"{requested_calls} wywołań, {rows} wierszy; "
            f"status: {status}."
        ),
    )

def _operator_summary(
    decisions: list[AhrefsDecisionItem],
    gap_read_contract: AhrefsGapReadContract,
    authority_fact_count: int,
    gap_fact_count: int,
) -> AhrefsOperatorSummary:
    top_decisions = decisions[:4]
    available_contracts = gap_read_contract.available_read_contracts
    missing_contracts = gap_read_contract.missing_read_contracts
    return _label_ahrefs_operator_summary(
        AhrefsOperatorSummary(
            title="Co marketer ma wiedzieć o Ahrefs",
            summary=(
                "Ten widok pokazuje, czy Ahrefs może wesprzeć decyzje SEO i treści. "
                "Autorytet domeny może być kontekstem, ale wnioski o lukach treści "
                "lub linków zwrotnych wymagają konkretnych danych Ahrefs."
            ),
            next_step=_operator_summary_next_step(gap_read_contract),
            review_decision_after_review=_ahrefs_review_decision_after_review(
                gap_read_contract
            ),
            review_question_for_operator=_ahrefs_review_question_for_operator(
                gap_read_contract
            ),
            review_next_safe_click=_ahrefs_review_next_safe_click(gap_read_contract),
            review_action_ids=list(gap_read_contract.action_ids),
            top_decision_ids=[decision.id for decision in top_decisions],
            gap_read_status=gap_read_contract.status,
            authority_fact_count=authority_fact_count,
            gap_fact_count=gap_fact_count,
            available_read_contracts=available_contracts,
            available_read_contract_labels=_labels_for_values(
                available_contracts,
                _ahrefs_read_contract_label,
            ),
            missing_read_contracts=missing_contracts,
            missing_read_contract_labels=_labels_for_values(
                missing_contracts,
                _missing_gap_contract_label,
            ),
            source_connectors=_unique(
                [
                    *(
                        connector
                        for decision in top_decisions
                        for connector in decision.source_connectors
                    ),
                    *gap_read_contract.source_connectors,
                ]
            ),
            evidence_ids=_unique(
                [
                    *(
                        evidence_id
                        for decision in top_decisions
                        for evidence_id in decision.evidence_ids
                    ),
                    *gap_read_contract.evidence_ids,
                ]
            ),
            action_ids=_unique(
                [
                    *(action_id for decision in top_decisions for action_id in decision.action_ids),
                    *gap_read_contract.action_ids,
                ]
            ),
            blocked_claims=_unique(
                [
                    *(claim for decision in top_decisions for claim in decision.blocked_claims),
                    *gap_read_contract.blocked_claims,
                ]
            ),
        )
    )

def _operator_summary_next_step(gap_read_contract: AhrefsGapReadContract) -> str:
    if gap_read_contract.status == "ready":
        return (
            "Połącz kontekst autorytetu z rekordami luk Ahrefs, widokiem Treści i GSC. "
            "Przygotuj sprawdzenie treści/linków bez obietnic wzrostu widoczności."
        )
    return (
        "Użyj najważniejszych decyzji Ahrefs jako kontekstu dla widoku Treści. "
        "Nie twierdź o lukach treści, lukach linków ani wzroście widoczności "
        "bez konkretnych danych Ahrefs."
    )

def _ahrefs_review_decision_after_review(
    gap_read_contract: AhrefsGapReadContract,
) -> str:
    if gap_read_contract.status == "ready":
        if gap_read_contract.cross_check_status == "api_backed":
            return (
                "Po review wybierz, czy temat z Ahrefs idzie do odświeżenia albo "
                "scalenia istniejącej treści, osobnego briefu contentowego, link-review "
                "czy zostaje w obserwacji. Sprawdzenie GSC i WordPress jest dostępne, "
                "ale nadal nie odblokowuje obietnic wzrostu ruchu ani autorytetu."
            )
        return (
            "Po review zdecyduj, czy luka z Ahrefs ma przejść do dalszego "
            "sprawdzenia GSC i WordPress, briefu contentowego, link-review czy "
            "obserwacji. Bez cross-checku nie traktuj jej jako gotowego tematu."
        )
    return (
        "Po review możesz użyć Ahrefs tylko jako kontekstu autorytetu. Luki treści, "
        "luki linków i przewaga konkurencji zostają zablokowane do czasu brakujących "
        "rekordów Ahrefs."
    )

def _ahrefs_review_question_for_operator(
    gap_read_contract: AhrefsGapReadContract,
) -> str:
    if gap_read_contract.status == "ready":
        return (
            "Który temat z Ahrefs ma największy sens dla Ekologus po porównaniu "
            "intencji, istniejącego URL, GSC i WordPress: odświeżenie, scalenie, "
            "nowy brief, link-review czy obserwacja?"
        )
    return (
        "Czy dostępne dane Ahrefs wystarczają tylko do kontekstu autorytetu, "
        "czy najpierw trzeba odświeżyć/uzupełnić rekordy luk treści i linków?"
    )

def _ahrefs_review_next_safe_click(gap_read_contract: AhrefsGapReadContract) -> str:
    if AHREFS_CONTENT_REFRESH_ACTION_ID in gap_read_contract.action_ids:
        return (
            f"Uruchom podgląd bez zapisu dla {AHREFS_CONTENT_REFRESH_ACTION_ID}, "
            "ale dopiero po ręcznym review intencji, GSC, WordPress i zakresu "
            "treści/linków. To nie publikuje treści i nie tworzy automatycznego briefu."
        )
    if gap_read_contract.cross_check_status == "manual_required":
        return (
            "Najpierw ręcznie porównaj temat Ahrefs z zapytaniami GSC i spisem WordPress. "
            "Słabe podobieństwo nie odblokowuje podglądu kolejki ani briefu."
        )
    return (
        "Najpierw odśwież lub uzupełnij dane Ahrefs; bez rekordów luk nie ma "
        "bezpiecznego kliknięcia do kolejki treści."
    )

def _ahrefs_sections(
    *,
    connector_missing: list[str],
    latest_refresh: ConnectorRefreshRun | None,
    authority_facts: list[MetricFact],
    competitor_read_facts: list[MetricFact],
    gap_facts: list[MetricFact],
) -> list[AhrefsDiagnosticSection]:
    authority_section = AhrefsDiagnosticSection(
        id="ahrefs_authority_context",
        title="Ahrefs: kontekst autorytetu",
        status="ready" if authority_facts else ("blocked" if connector_missing else "missing"),
        summary=(
            f"WILQ ma {len(authority_facts)} świeże dane autorytetu z Ahrefs: "
            f"{_authority_summary(authority_facts)}. "
            f"{_competitor_read_summary(competitor_read_facts)}"
            if authority_facts
            else _missing_authority_summary(connector_missing, latest_refresh)
        ),
        diagnosis=(
            "Metryki autorytetu Ahrefs mogą wspierać priorytety SEO jako kontekst, "
            "ale nie są samodzielnym dowodem luki treści, luki linków zwrotnych ani wzrostu ruchu."
            if authority_facts
            else (
                "Bez danych autorytetu z Ahrefs WILQ nie może nawet użyć Ahrefs jako kontekstu SEO."
            )
        ),
        next_step=(
            "Użyj tych danych jako pomocniczego kontekstu przy sprawdzeniu treści i GSC. "
            "Nie zamieniaj ich w obietnicę przewagi nad konkurencją."
            if authority_facts
            else "Uruchom odczyt danych autorytetu Ahrefs, potem wróć do /ahrefs."
        ),
        source_connectors=[AHREFS_CONNECTOR_ID],
        evidence_ids=_evidence_ids_for_facts_or_refresh(
            [*authority_facts, *competitor_read_facts],
            latest_refresh,
        ),
        metric_facts=[*authority_facts, *competitor_read_facts],
        metric_fact_labels=_metric_fact_labels_for_facts(
            [*authority_facts, *competitor_read_facts]
        ),
        blocked_claims=[] if authority_facts else AHREFS_GAP_BLOCKED_CLAIMS,
        risk=ActionRisk.low if authority_facts else ActionRisk.medium,
    )

    missing_gap_contracts = _missing_gap_contracts(gap_facts)
    gap_records = _ahrefs_gap_records(gap_facts)
    gap_section = AhrefsDiagnosticSection(
        id="ahrefs_gap_contract",
        title="Ahrefs: rekordy luk SEO",
        status="ready" if gap_records else "blocked",
        summary=(
            f"WILQ ma {_ahrefs_gap_record_count_label(len(gap_records))} z Ahrefs. Brakujące dane: "
            f"{_missing_gap_contracts_summary(missing_gap_contracts)}."
            if gap_records
            else (
                "WILQ nie ma jeszcze rekordów luk konkurencji, treści "
                "ani linków zwrotnych z Ahrefs."
            )
        ),
        diagnosis=(
            "Rekordy luk można połączyć z GSC i spisem treści WordPress, ale tylko w zakresie "
            "konkretnych danych z dowodami."
            if gap_records
            else (
                "To jest brak danych, nie brak promptu. DR/rank nie mówi, "
                "gdzie konkurencja ma przewagę ani które linki/treści trzeba zbudować."
            )
        ),
        next_step=(
            "Połącz rekordy luk z GSC i WordPress, "
            "potem przygotuj kolejkę sprawdzenia treści i linków."
            if gap_records
            else ("Dodaj odczyt danych Ahrefs dla stron konkurencji, luk treści i luk linków.")
        ),
        source_connectors=[AHREFS_CONNECTOR_ID],
        evidence_ids=_evidence_ids_for_facts_or_refresh(gap_facts, latest_refresh),
        metric_facts=gap_facts[:12],
        metric_fact_labels=_metric_fact_labels_for_facts(gap_facts),
        blocked_claims=_blocked_claims_for_missing_contracts(missing_gap_contracts),
        risk=ActionRisk.low if gap_records else ActionRisk.medium,
    )

    safety_section = AhrefsDiagnosticSection(
        id="ahrefs_action_safety",
        title="Bezpieczeństwo decyzji Ahrefs",
        status="blocked" if not gap_facts else "ready",
        summary=(
            "Ahrefs jest źródłem danych do sprawdzenia. WILQ nie może obiecywać luki treści, "
            "luki linków zwrotnych ani wzrostu ruchu bez konkretnych danych i "
            "sprawdzenia przez operatora."
        ),
        diagnosis=(
            "Metryki autorytetu są pomocne, ale zbyt ogólne. Decyzje treściowe muszą przejść "
            "przez widok treści, GSC, spis treści WordPress i przegląd akcji."
        ),
        next_step="Zostaw zapis zmian zablokowany. Najpierw dodaj brakujące odczyty danych.",
        source_connectors=[AHREFS_CONNECTOR_ID],
        evidence_ids=_evidence_ids_for_facts_or_refresh(
            [*authority_facts, *gap_facts],
            latest_refresh,
        ),
        metric_fact_labels=_metric_fact_labels_for_facts([*authority_facts, *gap_facts]),
        blocked_claims=AHREFS_GAP_BLOCKED_CLAIMS,
        risk=ActionRisk.medium,
    )
    return [authority_section, gap_section, safety_section]

def _ahrefs_decision_queue(
    *,
    connector_missing: list[str],
    latest_refresh: ConnectorRefreshRun | None,
    authority_facts: list[MetricFact],
    competitor_read_facts: list[MetricFact],
    gap_facts: list[MetricFact],
) -> list[AhrefsDecisionItem]:
    decisions: list[AhrefsDecisionItem] = []
    gap_records = _ahrefs_gap_records(gap_facts)
    if authority_facts:
        decisions.append(
            AhrefsDecisionItem(
                id="ahrefs_review_authority_context",
                decision_type="review_authority_context",
                status="ready",
                decision_type_label=_ahrefs_decision_type_label("review_authority_context"),
                title="Użyj Ahrefs tylko jako kontekstu autorytetu",
                summary=(
                    f"{_authority_summary(authority_facts)}. "
                    f"{_competitor_read_summary(competitor_read_facts)}"
                ),
                rationale=(
                    "WILQ ma metryki autorytetu Ahrefs z dowodami, więc może dodać kontekst "
                    "autorytetu do sprawdzenia SEO i treści. To nadal nie jest analiza luk."
                ),
                next_step=(
                    "Połącz ten kontekst z rekordami luk Ahrefs, widokiem Treści i GSC. "
                    "Sprawdzenie luk nadal wymaga kontroli GSC i WordPress i nie jest obietnicą "
                    "wzrostu."
                    if gap_records
                    else (
                        "Połącz ten kontekst z widokiem Treści i GSC. Nie twierdź, że "
                        "Ahrefs wykrył lukę treści/linków, dopóki nie ma rekordów luk."
                    )
                ),
                priority=25,
                metric_tiles=_authority_tiles(
                    authority_facts,
                    gap_facts,
                    competitor_read_facts,
                ),
                allowed_evidence=[
                    "domain_rating",
                    "ahrefs_rank",
                    "authority_summary",
                    *(fact.name for fact in competitor_read_facts),
                ],
                allowed_evidence_labels=_labels_for_values(
                    [
                        "domain_rating",
                        "ahrefs_rank",
                        "authority_summary",
                        *(fact.name for fact in competitor_read_facts),
                    ],
                    _ahrefs_metric_fact_label,
                ),
                missing_read_contracts=_missing_gap_contracts(gap_facts),
                missing_read_contract_labels=_labels_for_values(
                    _missing_gap_contracts(gap_facts),
                    _missing_gap_contract_label,
                ),
                source_connectors=[AHREFS_CONNECTOR_ID],
                evidence_ids=_evidence_ids_for_facts_or_refresh(
                    [*authority_facts, *competitor_read_facts],
                    latest_refresh,
                ),
                metric_facts=[*authority_facts, *competitor_read_facts],
                metric_fact_labels=_metric_fact_labels_for_facts(
                    [*authority_facts, *competitor_read_facts]
                ),
                action_ids=[],
                blocked_claims=_blocked_claims_for_missing_contracts(
                    _missing_gap_contracts(gap_facts)
                ),
                risk=ActionRisk.low,
            )
        )
    else:
        decisions.append(
            AhrefsDecisionItem(
                id="ahrefs_run_authority_read_before_gap_review",
                decision_type="run_authority_read",
                status="blocked",
                decision_type_label=_ahrefs_decision_type_label("run_authority_read"),
                title="Uruchom odczyt autorytetu Ahrefs przed sprawdzeniem luk SEO",
                summary=_missing_authority_summary(connector_missing, latest_refresh),
                rationale=(
                    "Bez świeżych danych autorytetu Ahrefs WILQ nie powinien nawet używać "
                    "Ahrefs jako kontekstu SEO."
                ),
                next_step=(
                    "Uzupełnij dostęp Ahrefs i wykonaj odczyt danych."
                    if connector_missing
                    else "Wykonaj odczyt danych Ahrefs, potem wróć do /ahrefs."
                ),
                priority=10,
                metric_tiles={"dane Ahrefs": 0, "brakujące dane": len(AHREFS_GAP_READ_CONTRACTS)},
                allowed_evidence=[],
                missing_read_contracts=["domain_rating", *AHREFS_GAP_READ_CONTRACTS],
                missing_read_contract_labels=_labels_for_values(
                    ["domain_rating", *AHREFS_GAP_READ_CONTRACTS],
                    _missing_gap_contract_label,
                ),
                source_connectors=[AHREFS_CONNECTOR_ID],
                evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
                action_ids=[],
                blocked_claims=AHREFS_GAP_BLOCKED_CLAIMS,
                risk=ActionRisk.medium,
            )
        )

    missing_gap_contracts = _missing_gap_contracts(gap_facts)
    if gap_records:
        allowed_evidence = _allowed_gap_evidence(authority_facts, gap_facts)
        decisions.append(
            AhrefsDecisionItem(
                id="ahrefs_review_gap_records",
                decision_type="review_gap_records",
                status="ready",
                decision_type_label=_ahrefs_decision_type_label("review_gap_records"),
                title="Przejrzyj rekordy luk Ahrefs",
                summary=(
                    f"WILQ ma {_ahrefs_gap_record_count_label(len(gap_records))} z Ahrefs. "
                    f"Brakujące dane: {_missing_gap_contracts_summary(missing_gap_contracts)}."
                ),
                rationale=(
                    "To są konkretne rekordy z dowodami Ahrefs, więc mogą wejść do "
                    "sprawdzenia SEO i treści. Nadal wymagają połączenia z GSC i spisem "
                    "treści WordPress przed decyzją publikacyjną."
                ),
                next_step=(
                    "Połącz rekordy z widokiem Treści, sprawdź duplikaty WordPress "
                    "i przygotuj zachowanie, odświeżenie, scalenie, utworzenie albo blokadę "
                    "zamiast obiecywać wzrost."
                ),
                priority=18,
                metric_tiles=_gap_record_tiles(gap_records, missing_gap_contracts),
                allowed_evidence=allowed_evidence,
                allowed_evidence_labels=_labels_for_values(
                    allowed_evidence,
                    _ahrefs_metric_fact_label,
                ),
                missing_read_contracts=missing_gap_contracts,
                missing_read_contract_labels=_labels_for_values(
                    missing_gap_contracts,
                    _missing_gap_contract_label,
                ),
                source_connectors=[AHREFS_CONNECTOR_ID],
                evidence_ids=_unique(
                    evidence_id for record in gap_records for evidence_id in record.evidence_ids
                ),
                metric_facts=[fact for record in gap_records for fact in record.metric_facts][:12],
                metric_fact_labels=_metric_fact_labels_for_facts(
                    [fact for record in gap_records for fact in record.metric_facts]
                ),
                action_ids=[],
                blocked_claims=_blocked_claims_for_missing_contracts(missing_gap_contracts),
                risk=ActionRisk.medium if missing_gap_contracts else ActionRisk.low,
            )
        )
    if missing_gap_contracts:
        decisions.append(
            AhrefsDecisionItem(
                id="ahrefs_block_gap_claims_without_records",
                decision_type="block_gap_claims",
                status="blocked",
                decision_type_label=_ahrefs_decision_type_label("block_gap_claims"),
                title="Nie wskazuj luk konkurencji bez rekordów Ahrefs",
                summary=(
                    "Brakuje danych Ahrefs dla luk treści, luk linków zwrotnych, "
                    "organicznych słów kluczowych i najlepszych stron konkurencji."
                ),
                rationale=(
                    "DR/rank to metryki domeny. Nie mówią, które treści, linki albo "
                    "konkurenci tworzą realną przestrzeń do działania."
                ),
                next_step=(
                    "Dodaj odczyty danych: strony konkurencji, rekordy luk treści, "
                    "rekordy luk linków zwrotnych, organiczne słowa dla URL i najlepsze "
                    "strony konkurencji."
                ),
                priority=12,
                metric_tiles={
                    "brakujące dane": len(missing_gap_contracts),
                    "nie wolno twierdzić": len(
                        _blocked_claims_for_missing_contracts(missing_gap_contracts)
                    ),
                },
                allowed_evidence=["domain_rating", "ahrefs_rank"] if authority_facts else [],
                allowed_evidence_labels=_labels_for_values(
                    ["domain_rating", "ahrefs_rank"] if authority_facts else [],
                    _ahrefs_metric_fact_label,
                ),
                missing_read_contracts=missing_gap_contracts,
                missing_read_contract_labels=_labels_for_values(
                    missing_gap_contracts,
                    _missing_gap_contract_label,
                ),
                source_connectors=[AHREFS_CONNECTOR_ID],
                evidence_ids=_evidence_ids_for_facts_or_refresh(authority_facts, latest_refresh),
                action_ids=[],
                blocked_claims=_blocked_claims_for_missing_contracts(missing_gap_contracts),
                risk=ActionRisk.medium,
            )
        )
    return decisions

def _ahrefs_decisions_with_lineage(
    decisions: list[AhrefsDecisionItem],
) -> list[AhrefsDecisionItem]:
    return [
        _label_ahrefs_decision(decision).model_copy(
            update={
                "knowledge_card_ids": _unique(
                    [*decision.knowledge_card_ids, *AHREFS_KNOWLEDGE_CARD_IDS]
                ),
                "expert_rule_ids": _unique([*decision.expert_rule_ids, *AHREFS_EXPERT_RULE_IDS]),
            }
        )
        for decision in decisions
    ]

__all__ = ["build_ahrefs_diagnostics"]

