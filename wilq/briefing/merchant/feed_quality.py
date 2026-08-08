from __future__ import annotations

from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionRisk,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MerchantDecisionItem,
    MerchantDiagnosticSection,
    MerchantFreshnessAssessment,
    MerchantIssueCluster,
    MerchantProductPerformanceReadiness,
    MerchantUnknownFact,
    MetricFact,
    TacticalQueueItem,
    utc_now,
)

from .labels import (
    _merchant_display_label,
    _merchant_metric_fact_with_labels,
    _merchant_refresh_status_label,
    _merchant_reporting_context_label,
    _merchant_resolution_label,
    _merchant_risk_label,
    _merchant_severity_label,
)
from .shared import (
    MERCHANT_CONNECTOR_ID,
    MERCHANT_HEALTH_METRIC_NAMES,
    MERCHANT_STALE_AFTER_HOURS,
    _facts_by_names,
    _metric_sentence,
    _numeric_metric,
    _pl_count,
    _stable_slug,
    _unique,
)


def _merchant_freshness_assessment(
    latest_refresh: ConnectorRefreshRun | None,
) -> MerchantFreshnessAssessment:
    if latest_refresh is None:
        return MerchantFreshnessAssessment(
            state="missing",
            latest_refresh_id=None,
            latest_refresh_completed_at=None,
            age_hours=None,
            stale_after_hours=MERCHANT_STALE_AFTER_HOURS,
            requires_refresh=True,
            summary="Brak zapisanego odczytu danych Merchant Center.",
            next_step=(
                "Uruchom odczyt danych Merchant przed oceną aktualnego stanu "
                "pliku produktowego."
            ),
        )

    completed_at = latest_refresh.completed_at or latest_refresh.started_at
    age_hours = round((utc_now() - completed_at).total_seconds() / 3600, 2)
    if latest_refresh.status != ConnectorRefreshStatus.completed:
        return MerchantFreshnessAssessment(
            state="blocked",
            latest_refresh_id=latest_refresh.id,
            latest_refresh_completed_at=completed_at,
            age_hours=age_hours,
            stale_after_hours=MERCHANT_STALE_AFTER_HOURS,
            requires_refresh=True,
            summary=(
                "Ostatni odczyt Merchant nie zakończył się poprawnie. "
                f"Status odczytu: {_merchant_refresh_status_label(latest_refresh.status)}."
            ),
            next_step=(
                "Napraw blocker odczytu i uruchom ponownie odczyt danych Merchant przed "
                "budowaniem kolejki pliku produktowego."
            ),
        )

    if age_hours > MERCHANT_STALE_AFTER_HOURS:
        return MerchantFreshnessAssessment(
            state="stale",
            latest_refresh_id=latest_refresh.id,
            latest_refresh_completed_at=completed_at,
            age_hours=age_hours,
            stale_after_hours=MERCHANT_STALE_AFTER_HOURS,
            requires_refresh=True,
            summary=(
                f"Ostatni odczyt danych Merchant ma około {age_hours:.1f}h. "
                "To wystarcza do przeglądu nieświeżych danych, "
                "ale nie do obietnic o bieżącym stanie pliku produktowego."
            ),
            next_step=(
                "Uruchom odczyt danych Merchant, jeśli pytanie dotyczy aktualnego stanu produktów."
            ),
        )

    return MerchantFreshnessAssessment(
        state="fresh",
        latest_refresh_id=latest_refresh.id,
        latest_refresh_completed_at=completed_at,
        age_hours=age_hours,
        stale_after_hours=MERCHANT_STALE_AFTER_HOURS,
        requires_refresh=False,
        summary=(
            f"Ostatni odczyt danych Merchant ma około {age_hours:.1f}h i mieści się "
            f"w progu {MERCHANT_STALE_AFTER_HOURS}h."
        ),
        next_step="Można użyć danych do kolejki sprawdzenia bez dodatkowego odświeżenia.",
    )


def _merchant_unknowns(
    issue_clusters: list[MerchantIssueCluster],
    decisions: list[MerchantDecisionItem],
    product_performance_readiness: MerchantProductPerformanceReadiness,
) -> list[MerchantUnknownFact]:
    unknowns: list[MerchantUnknownFact] = []
    if issue_clusters or decisions:
        sample_ids = _unique(
            sample_id for cluster in issue_clusters for sample_id in cluster.sample_product_ids
        )
        if not sample_ids:
            unknowns.append(
                MerchantUnknownFact(
                    id="merchant_product_examples_missing",
                    title="Brak przykładowych produktów/SKU w kontrakcie odczytu",
                    reason=(
                        "Merchant diagnostics ma typ problemu, atrybut, kraj, kontekst "
                        "raportowania i licznik, ale nie zwraca product IDs, SKU ani tytułów."
                    ),
                    impact=(
                        "WILQ może przygotować kolejkę sprawdzenia po klastrach, ale nie listę "
                        "konkretnych produktów do edycji."
                    ),
                    next_step=(
                        "Dodać osobny read contract dla bezpiecznych przykładów produktów "
                        "albo otworzyć Merchant Center podczas sprawdzenia."
                    ),
                    blocked_claims=[
                        "naprawa pojedynczego produktu",
                        "zapis do pliku produktowego",
                        "automatyczna zmiana pliku produktowego",
                    ],
                )
            )
        unknowns.append(
            MerchantUnknownFact(
                id="merchant_unique_product_count_unknown",
                title="Zgłoszenia raportowe nie są liczbą unikalnych produktów",
                reason=(
                    "Ten sam problem może wystąpić w kilku kontekstach raportowania, "
                    "więc suma raportów może liczyć ten sam produkt więcej niż raz."
                ),
                impact=(
                    "Kolejka decyzji musi używać największej liczby zgłoszeń "
                    "jako skali i traktować "
                    "sumę raportów wyłącznie jako szczegóły raportowania."
                ),
                next_step=(
                    "Grupować decyzje po kolejce decyzji, a klastry problemów pokazywać "
                    "jako szczegóły raportowania."
                ),
                blocked_claims=[
                    "liczba unikalnych produktów",
                    "ponowne zatwierdzenie produktu",
                ],
            )
        )
    if product_performance_readiness.status == "blocked":
        unknowns.append(
            MerchantUnknownFact(
                id="merchant_product_performance_join_missing",
                title="Brak połączenia produktów Merchant z Ads/GA4",
                reason=(
                    "WILQ ma próbki produktów Merchant albo kolejkę problemów pliku produktowego, "
                    "ale nie ma dopasowanych faktów Ads/GA4 z kluczem produktu dla "
                    "tych produktów."
                ),
                impact=(
                    "Można prowadzić przegląd problemów pliku produktowego, "
                    "ale nie wolno twierdzić, "
                    "które produkty mają zwrot z reklam, przychód, koszt albo efekt naprawy."
                ),
                next_step=(
                    "Dodać kontrakty odczytu skuteczności produktu dla Google Ads "
                    "Shopping, Performance Max i GA4 ecommerce, z jawnie wspólnym "
                    "kluczem produktu."
                ),
                blocked_claims=product_performance_readiness.blocked_claims,
            )
        )
    return unknowns


def _current_facts_for_refresh(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
) -> list[MetricFact]:
    if latest_refresh is None or not latest_refresh.evidence_ids:
        return facts
    evidence_ids = set(latest_refresh.evidence_ids)
    return [fact for fact in facts if fact.evidence_id in evidence_ids]


def _current_tactical_items_for_refresh(
    latest_refresh: ConnectorRefreshRun | None,
    items: list[TacticalQueueItem],
) -> list[TacticalQueueItem]:
    if latest_refresh is None or not latest_refresh.evidence_ids:
        return items
    evidence_ids = set(latest_refresh.evidence_ids)
    return [
        item
        for item in items
        if any(evidence_id in evidence_ids for evidence_id in item.evidence_ids)
    ]


def _feed_health_section(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    action_ids: list[str],
) -> MerchantDiagnosticSection:
    if not facts:
        return MerchantDiagnosticSection(
            id="merchant_feed_health",
            title="Merchant Center: brak aktualnych metryk pliku produktowego",
            status="blocked",
            summary=_merchant_blocker_reason(latest_refresh),
            diagnosis=(
                "WILQ nie ma aktualnych metryk Merchant, więc nie może ocenić "
                "liczby produktów, liczby zgłoszeń problemów ani stanu pliku produktowego."
            ),
            next_step=(
                "Uruchom odczyt danych Merchant i dopiero potem twórz kolejkę pliku produktowego."
            ),
            source_connectors=[MERCHANT_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            action_ids=action_ids,
            blocked_claims=[
                "ocena stanu pliku produktowego",
                "zatwierdzenie produktu",
                "liczba zgłoszeń problemów",
            ],
            risk=ActionRisk.medium,
        )

    product_facts = _merchant_health_metric_facts(latest_refresh, facts)
    return MerchantDiagnosticSection(
        id="merchant_feed_health",
        title="Merchant Center: stan produktów i pliku produktowego",
        status="ready",
        summary=_metric_sentence(product_facts or facts),
        diagnosis=(
            "WILQ ma metryki Merchant z odczytu. Można ocenić skalę pliku produktowego i liczbę "
            "zgłoszonych problemów, ale nie wolno twierdzić, że produkt został naprawiony bez "
            "akcji do sprawdzenia i audytu."
        ),
        next_step="Przejdź do kolejki problemów i grupuj je po typie oraz atrybucie.",
        source_connectors=[MERCHANT_CONNECTOR_ID],
        evidence_ids=_unique(fact.evidence_id for fact in product_facts or facts),
        metric_facts=(product_facts or facts)[:10],
        action_ids=action_ids,
        blocked_claims=[
            "ponowne zatwierdzenie produktu",
            "odzyskany przychód",
            "wzrost zysku",
        ],
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
            title="Merchant Center: brak kolejki problemów pliku produktowego",
            status="missing",
            summary="Brak metryk problemów i pozycji kolejki Merchant.",
            diagnosis=(
                "Nie ma bezpiecznego materiału do kolejki oceny pliku produktowego. WILQ musi "
                "najpierw zebrać typ problemu, atrybut albo metryki statusu produktu."
            ),
            next_step="Odśwież dane Merchant i sprawdź aggregateProductStatuses.",
            source_connectors=[MERCHANT_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            action_ids=action_ids,
            blocked_claims=[
                "propozycja naprawy pliku produktowego",
                "naprawa pojedynczego produktu",
            ],
            risk=ActionRisk.medium,
        )

    cluster_count = _pl_count(
        len(issue_clusters),
        "grupę problemów pliku produktowego",
        "grupy problemów pliku produktowego",
        "grup problemów pliku produktowego",
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
        title="Merchant Center: kolejka problemów pliku produktowego",
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
        next_step=("Otwórz akcję do sprawdzenia i przygotuj kolejkę przeglądu."),
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
        blocked_claims=[
            "automatyczna zmiana pliku produktowego",
            "nadpisanie głównego pliku produktowego",
            "ponowne zatwierdzenie produktu",
        ],
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
            int(fact.value) for fact in group_facts if isinstance(fact.value, int | float)
        )
        sample_product_ids = _sample_product_ids_for_cluster(facts, key)
        sample_titles = _sample_titles_for_cluster(facts, key)
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
                issue_type_label=_merchant_display_label(issue_type),
                severity=severity,
                severity_label=_merchant_severity_label(severity),
                resolution=resolution or None,
                resolution_label=_merchant_resolution_label(resolution or None),
                affected_attribute=affected_attribute or None,
                affected_attribute_label=_merchant_display_label(
                    affected_attribute or "atrybut nieznany"
                ),
                country=country or None,
                reporting_context=reporting_context or None,
                reporting_context_label=_merchant_reporting_context_label(
                    reporting_context or None
                ),
                product_count=product_count,
                sample_product_ids=sample_product_ids,
                sample_titles=sample_titles,
                sample_unavailable_reason=None
                if sample_product_ids
                else (
                    "Obecny kontrakt odczytu Merchant zwraca wymiary problemu i liczbę "
                    "wystąpień problemu w raportach, ale nie zwraca przykładowych "
                    "produktów ani tytułów."
                ),
                source_connectors=[MERCHANT_CONNECTOR_ID],
                evidence_ids=_unique(fact.evidence_id for fact in group_facts),
                blocked_claims=[
                    "ponowne zatwierdzenie produktu",
                    "odzyskany przychód",
                    "automatyczna zmiana pliku produktowego",
                ],
                action_id=action_id,
                risk=_merchant_cluster_risk(severity, resolution),
                risk_label=_merchant_risk_label(_merchant_cluster_risk(severity, resolution)),
                next_step=(
                    "Przejrzyj tę grupę problemu przez akcję do sprawdzenia; "
                    "najpierw przygotuj podgląd zmian, bez automatycznej zmiany pliku produktowego."
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


def _sample_product_ids_for_cluster(
    facts: list[MetricFact],
    key: tuple[str, str, str, str, str, str],
) -> list[str]:
    issue_type, affected_attribute, country, reporting_context, severity, resolution = key
    sample_ids = [
        str(fact.value)
        for fact in sorted(
            facts,
            key=lambda fact: fact.dimensions.get("sample_index", ""),
        )
        if fact.name == "sample_product_id"
        and fact.dimensions.get("issue_type") == issue_type
        and _merchant_attribute_matches(
            fact.dimensions.get("affected_attribute"),
            affected_attribute,
        )
        and (fact.dimensions.get("country") or "") == country
        and (fact.dimensions.get("reporting_context") or "") == reporting_context
        and fact.dimensions.get("severity") == severity
        and (fact.dimensions.get("resolution") or "") == resolution
        and isinstance(fact.value, str)
    ]
    return _unique(sample_ids)[:10]


def _sample_titles_for_cluster(
    facts: list[MetricFact],
    key: tuple[str, str, str, str, str, str],
) -> list[str]:
    issue_type, affected_attribute, country, reporting_context, severity, resolution = key
    sample_titles = [
        str(fact.value)
        for fact in sorted(
            facts,
            key=lambda fact: fact.dimensions.get("sample_index", ""),
        )
        if fact.name == "sample_product_title"
        and fact.dimensions.get("issue_type") == issue_type
        and _merchant_attribute_matches(
            fact.dimensions.get("affected_attribute"),
            affected_attribute,
        )
        and (fact.dimensions.get("country") or "") == country
        and (fact.dimensions.get("reporting_context") or "") == reporting_context
        and fact.dimensions.get("severity") == severity
        and (fact.dimensions.get("resolution") or "") == resolution
        and isinstance(fact.value, str)
    ]
    return _unique(sample_titles)[:10]


def _merchant_attribute_matches(left: str | None, right: str | None) -> bool:
    return _merchant_attribute_key(left) == _merchant_attribute_key(right)


def _merchant_attribute_key(value: str | None) -> str:
    normalized = (value or "").removeprefix("n:").strip().lower()
    return "".join(char for char in normalized if char.isalnum())


def _facts_for_cluster(
    facts: list[MetricFact],
    cluster: MerchantIssueCluster,
) -> list[MetricFact]:
    return [
        fact
        for fact in facts
        if fact.name == "issue_product_count"
        and fact.dimensions.get("issue_type") == cluster.issue_type
        and fact.dimensions.get("severity") == cluster.severity
        and (fact.dimensions.get("affected_attribute") or None) == cluster.affected_attribute
        and (fact.dimensions.get("country") or None) == cluster.country
        and (fact.dimensions.get("reporting_context") or None) == cluster.reporting_context
    ]


def _facts_for_cluster_group(
    facts: list[MetricFact],
    clusters: list[MerchantIssueCluster],
) -> list[MetricFact]:
    return [fact for cluster in clusters for fact in _facts_for_cluster(facts, cluster)]


def _merchant_cluster_risk(severity: str, resolution: str | None) -> ActionRisk:
    if severity == "DISAPPROVED":
        return ActionRisk.high
    if resolution == "MERCHANT_ACTION":
        return ActionRisk.medium
    return ActionRisk.low


def _merchant_severity_rank(severity: str) -> int:
    return {"DISAPPROVED": 0, "DEMOTED": 1, "NOT_IMPACTED": 2}.get(severity, 3)


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
            _merchant_metric_fact_with_labels(
                MetricFact(
                    name=name,
                    value=value,
                    period="connector_refresh",
                    source_connector=MERCHANT_CONNECTOR_ID,
                    evidence_id=evidence_id,
                )
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
    return "Brak wykonanego odczytu danych Merchant."


def _refresh_or_connector_evidence_ids(latest_refresh: ConnectorRefreshRun | None) -> list[str]:
    if latest_refresh:
        return latest_refresh.evidence_ids
    return [connector_evidence_id(MERCHANT_CONNECTOR_ID)]
