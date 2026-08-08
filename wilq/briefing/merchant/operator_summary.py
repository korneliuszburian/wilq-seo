from __future__ import annotations

from wilq.actions.merchant import MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT
from wilq.briefing.merchant_labels import merchant_preview_contract_label
from wilq.operator_labels import reported_issue_occurrence_count_label
from wilq.schemas import (
    ActionPreviewCardViewModel,
    ActionPreviewRowViewModel,
    ActionRisk,
    ConnectorRefreshRun,
    MerchantDecisionItem,
    MerchantDiagnosticSection,
    MerchantIssueCluster,
    MerchantOperatorSummary,
    MerchantPriceImpactReadiness,
    MerchantProductPerformanceReadiness,
    MerchantProductPerformanceRow,
    MetricFact,
    TacticalQueueItem,
)

from .feed_quality import (
    _facts_for_cluster,
    _facts_for_cluster_group,
    _merchant_blocker_reason,
    _merchant_health_metric_facts,
    _numeric_metric_or_refresh_summary,
    _refresh_or_connector_evidence_ids,
)
from .labels import (
    _merchant_change_preview_with_operator_labels,
    _merchant_count_label,
    _merchant_display_label,
    _merchant_metric_snapshot_labels,
    _merchant_preview_apply_state_label,
    _merchant_preview_required_validation_label,
    _merchant_preview_scope_label,
    _merchant_preview_system_readiness_label,
    _merchant_reporting_context_label,
    _merchant_resolution_label,
    _merchant_severity_label,
)
from .products import (
    _has_ads_product_state,
    _has_product_performance_metric,
)
from .shared import (
    MERCHANT_CONNECTOR_ID,
    MERCHANT_EXPERT_RULE_IDS,
    MERCHANT_KNOWLEDGE_CARD_IDS,
    MERCHANT_PRODUCT_PERFORMANCE_BLOCKED_CLAIMS,
    MERCHANT_PRODUCT_STATE_REVIEW_PREVIEW_CONTRACT,
    MERCHANT_SUPPLEMENTAL_FEED_REVIEW_PREVIEW_CONTRACT,
    _numeric_metric,
    _stable_slug,
    _unique,
)


def _merchant_issue_decision_title(issue_label: str, attribute_label: str) -> str:
    if attribute_label and attribute_label not in {"atrybut", "atrybut nieznany"}:
        return f"Merchant: problem z atrybutem: {attribute_label} - {issue_label}"
    return f"Merchant: sprawdź problem pliku produktowego - {issue_label}"


def _operator_summary(
    decisions: list[MerchantDecisionItem],
    issue_clusters: list[MerchantIssueCluster],
    sections: list[MerchantDiagnosticSection],
    action_ids: list[str],
) -> MerchantOperatorSummary:
    issue_items = [item for section in sections for item in section.tactical_items]
    issue_metric_facts = [
        fact
        for section in sections
        for fact in section.metric_facts
        if fact.name == "issue_product_count"
    ]
    reported_issue_occurrences = (
        sum(cluster.product_count for cluster in issue_clusters)
        if issue_clusters
        else sum(
            int(fact.value) for fact in issue_metric_facts if isinstance(fact.value, int | float)
        )
    )
    top_issue_items = sorted(
        issue_items,
        key=lambda item: (-item.priority, item.id),
    )[:3]
    return MerchantOperatorSummary(
        title="Co marketer ma zrobić teraz z plikiem produktowym",
        summary=(
            "WILQ grupuje problemy Merchant po typie i atrybucie. To jest kolejka "
            "przeglądu: można przygotować decyzje i podgląd zmian, ale nie wolno "
            "obiecać ponownego zatwierdzenia produktu ani automatycznie nadpisać "
            "pliku produktowego."
        ),
        next_step=(
            "Przejdź przez top decyzje lub klastry problemów, przygotuj przegląd "
            "akcji i nie zapisuj zmian pliku produktowego bez sprawdzenia w WILQ "
            "oraz zgody operatora."
        ),
        top_decision_ids=[decision.id for decision in decisions[:4]],
        top_issue_cluster_ids=[cluster.id for cluster in issue_clusters[:4]],
        top_tactical_item_ids=[item.id for item in top_issue_items],
        reported_issue_occurrences=reported_issue_occurrences,
        issue_types=_unique(
            [
                *(
                    cluster.issue_type_label or _merchant_display_label(cluster.issue_type)
                    for cluster in issue_clusters
                ),
                *(
                    _merchant_display_label(
                        item.dimensions.get("issue_type") or "problem pliku produktowego"
                    )
                    for item in issue_items
                    if item.dimensions.get("issue_type")
                ),
            ]
        ),
        source_connectors=_unique(
            connector for decision in decisions[:4] for connector in decision.source_connectors
        )
        or [MERCHANT_CONNECTOR_ID],
        evidence_ids=_unique(
            [
                *(
                    evidence_id
                    for decision in decisions[:4]
                    for evidence_id in decision.evidence_ids
                ),
                *(
                    evidence_id
                    for cluster in issue_clusters[:4]
                    for evidence_id in cluster.evidence_ids
                ),
            ]
        ),
        action_ids=action_ids,
        blocked_claims=_unique(claim for section in sections for claim in section.blocked_claims),
    )


def _merchant_decision_queue(
    *,
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    issue_clusters: list[MerchantIssueCluster],
    action_ids: list[str],
) -> list[MerchantDecisionItem]:
    if not facts and not tactical_items:
        return [
            MerchantDecisionItem(
                id="merchant_block_vendor_read",
                decision_type="block_until_vendor_read",
                status="blocked",
                title="Merchant: odczyt pliku produktowego wymagany przed decyzją",
                summary=_merchant_blocker_reason(latest_refresh),
                priority=5,
                metric_tiles={"blokady": 1},
                source_connectors=[MERCHANT_CONNECTOR_ID],
                evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
                action_ids=action_ids,
                blocked_claims=[
                    "ocena stanu pliku produktowego",
                    "zatwierdzenie produktu",
                    "liczba zgłoszeń problemów",
                ],
                rationale=(
                    "WILQ nie ma aktualnych metryk Merchant, więc nie może "
                    "uczciwie zbudować kolejki problemów pliku produktowego ani "
                    "ocenić stanu produktów."
                ),
                next_step="Uruchom odczyt danych Merchant, potem wróć do /merchant.",
                risk=ActionRisk.medium,
            )
        ]

    decisions = [
        _merchant_decision_from_cluster_group(cluster_group, facts, action_ids)
        for cluster_group in _merchant_decision_cluster_groups(issue_clusters)[:8]
    ]
    if decisions:
        return decisions

    tactical_decisions = [
        _merchant_decision_from_tactical_item(item, action_ids) for item in tactical_items[:6]
    ]
    if tactical_decisions:
        return tactical_decisions

    aggregate_decision = _merchant_aggregate_feed_status_decision(
        latest_refresh,
        facts,
        action_ids,
    )
    return [aggregate_decision] if aggregate_decision is not None else []


def _merchant_decisions_with_product_state_review(
    decisions: list[MerchantDecisionItem],
    product_performance_readiness: MerchantProductPerformanceReadiness,
    action_ids: list[str],
) -> list[MerchantDecisionItem]:
    product_state_decision = _merchant_product_state_review_decision(
        product_performance_readiness,
        action_ids,
    )
    if product_state_decision is None:
        return decisions
    merged = [product_state_decision, *decisions]
    return sorted(merged, key=lambda decision: (decision.priority, decision.id))


def _merchant_decisions_with_price_impact_review(
    decisions: list[MerchantDecisionItem],
    price_impact_readiness: MerchantPriceImpactReadiness,
    action_ids: list[str],
) -> list[MerchantDecisionItem]:
    price_decision = _merchant_price_impact_review_decision(
        price_impact_readiness,
        action_ids,
    )
    if price_decision is None:
        return decisions
    merged = [price_decision, *decisions]
    return sorted(merged, key=lambda decision: (decision.priority, decision.id))


def _merchant_decisions_with_lineage(
    decisions: list[MerchantDecisionItem],
) -> list[MerchantDecisionItem]:
    return [
        decision.model_copy(
            update={
                "change_preview": [
                    _merchant_change_preview_with_operator_labels(preview)
                    for preview in decision.change_preview
                ],
                "preview_cards": _merchant_preview_cards(decision.change_preview),
                "knowledge_card_ids": _unique(
                    [*decision.knowledge_card_ids, *MERCHANT_KNOWLEDGE_CARD_IDS]
                ),
                "expert_rule_ids": _unique([*decision.expert_rule_ids, *MERCHANT_EXPERT_RULE_IDS]),
            }
        )
        for decision in decisions
    ]


def _merchant_preview_cards(
    previews: list[dict[str, object]],
) -> list[ActionPreviewCardViewModel]:
    return [
        _merchant_preview_card(_merchant_change_preview_with_operator_labels(preview))
        for preview in previews
    ]


def _merchant_preview_card(
    preview: dict[str, object],
) -> ActionPreviewCardViewModel:
    preview_id = str(preview.get("id") or "merchant_preview")
    contract_label = str(
        preview.get("preview_contract_label")
        or merchant_preview_contract_label(preview.get("preview_contract"))
    )
    rows = [
        ActionPreviewRowViewModel(label="Typ sprawdzenia", value=contract_label),
        ActionPreviewRowViewModel(
            label="Zakres",
            value=_merchant_preview_scope_label(preview),
        ),
        ActionPreviewRowViewModel(
            label="Warunki sprawdzenia",
            value=_merchant_preview_required_validation_label(preview),
        ),
    ]
    missing_read_contracts = preview.get("missing_read_contracts")
    if isinstance(missing_read_contracts, list) and missing_read_contracts:
        rows.append(
            ActionPreviewRowViewModel(
                label="Brakujące dane",
                value=_merchant_count_label(len(missing_read_contracts), "kontrakt", "kontrakty"),
            )
        )
    return ActionPreviewCardViewModel(
        id=preview_id,
        kind="merchant_review_preview",
        title_label="Podgląd sprawdzenia Merchant",
        subtitle_label=contract_label,
        status_label="do sprawdzenia",
        rows=rows,
        apply_state_label=_merchant_preview_apply_state_label(preview),
        system_readiness_label=_merchant_preview_system_readiness_label(preview),
    )


def _merchant_price_impact_review_decision(
    price_impact_readiness: MerchantPriceImpactReadiness,
    action_ids: list[str],
) -> MerchantDecisionItem | None:
    return MerchantDecisionItem(
        id="merchant_decision_review_price_impact_readiness",
        decision_type="review_price_impact_readiness",
        status=price_impact_readiness.status,
        title="Merchant: sprawdź gotowość analizy wpływu ceny",
        summary=price_impact_readiness.summary,
        priority=60,
        metric_tiles=_clean_merchant_metric_tiles(
            {
                "ceny bieżące": price_impact_readiness.products_with_current_price,
                "historia ceny": price_impact_readiness.products_with_previous_price,
                "zmiany ceny": price_impact_readiness.products_with_price_change,
                "performance": (price_impact_readiness.products_with_performance_metrics),
            }
        ),
        change_preview=price_impact_readiness.change_preview,
        source_connectors=price_impact_readiness.source_connectors,
        evidence_ids=price_impact_readiness.evidence_ids,
        action_ids=action_ids,
        blocked_claims=price_impact_readiness.blocked_claims,
        rationale=(
            "To jest decyzja gotowości price-impact. WILQ może pokazać bieżące "
            "ceny, historię ceny i brakujące kontrakty, ale nie może oceniać "
            "wpływu ceny bez zdarzenia zmiany ceny oraz okna performance."
        ),
        next_step=price_impact_readiness.next_step,
        risk=ActionRisk.medium,
    )


def _merchant_product_state_review_decision(
    product_performance_readiness: MerchantProductPerformanceReadiness,
    action_ids: list[str],
) -> MerchantDecisionItem | None:
    state_rows = [
        row
        for row in product_performance_readiness.performance_rows
        if _has_ads_product_state(row) and not _has_product_performance_metric(row)
    ]
    if not state_rows:
        return None
    visible_rows = state_rows[:8]
    not_eligible_count = sum(1 for row in state_rows if row.ads_product_status == "NOT_ELIGIBLE")
    out_of_stock_count = sum(
        1 for row in state_rows if row.ads_product_availability == "OUT_OF_STOCK"
    )
    return MerchantDecisionItem(
        id="merchant_decision_review_ads_product_state_mapping",
        decision_type="review_product_state_mapping",
        status="ready",
        title="Merchant: sprawdź powiązanie produktów ze statusem w Google Ads",
        summary=(
            f"WILQ połączył {len(state_rows)} próbek Merchant ze statusem produktów "
            "w Google Ads. To pokazuje status, dostępność i cenę z Ads, "
            "ale nie zawiera kliknięć, kosztu, przychodu ani efektu naprawy."
        ),
        issue_cluster_ids=[],
        priority=20,
        metric_tiles=_clean_merchant_metric_tiles(
            {
                "powiązane produkty": len(state_rows),
                "niekwalifikujące się": not_eligible_count,
                "niedostępne": out_of_stock_count,
            }
        ),
        sample_product_ids=[row.product_id for row in visible_rows],
        sample_titles=_unique(
            title
            for row in visible_rows
            for title in [row.sample_title or row.ads_product_title]
            if title
        ),
        change_preview=[
            _merchant_product_state_review_change_preview(
                visible_rows,
                product_performance_readiness.evidence_ids,
            ),
            _merchant_supplemental_feed_review_change_preview(
                visible_rows,
                product_performance_readiness.evidence_ids,
            ),
        ],
        source_connectors=product_performance_readiness.source_connectors,
        evidence_ids=product_performance_readiness.evidence_ids,
        action_ids=action_ids,
        blocked_claims=MERCHANT_PRODUCT_PERFORMANCE_BLOCKED_CLAIMS,
        rationale=(
            "To jest decyzja powiązania i sprawdzenia, nie decyzja o wynikach produktu. "
            "Wiersze samego statusu potwierdzają, że próbka Merchant ma odpowiednik w "
            "produktach Google Ads, ale bez metryk emisji i sprzedaży nie wolno "
            "wyciągać wniosków o zwrot z reklam, odzyskanym przychód ani skutku naprawy."
        ),
        next_step=(
            "Sprawdź powiązane produkty: status Ads, dostępność, cenę, "
            "powiązany problem Merchant i podgląd uzupełnienia pliku produktowego. "
            "Główny plik produktowy, zapis zmian i wpływ na zatwierdzenie pozostają zablokowane."
        ),
        risk=ActionRisk.medium,
    )


def _merchant_product_state_review_change_preview(
    rows: list[MerchantProductPerformanceRow],
    evidence_ids: list[str],
) -> dict[str, object]:
    return {
        "id": "merchant_product_state_review_preview",
        "preview_contract": MERCHANT_PRODUCT_STATE_REVIEW_PREVIEW_CONTRACT,
        "preview_contract_label": merchant_preview_contract_label(
            MERCHANT_PRODUCT_STATE_REVIEW_PREVIEW_CONTRACT
        ),
        "operation_type": "MerchantProductStateReview",
        "products": [
            {
                "product_id": row.product_id,
                "title": row.sample_title or row.ads_product_title,
                "issue_type": row.issue_type,
                "affected_attribute": row.affected_attribute,
                "ads_product_status": row.ads_product_status,
                "ads_product_availability": row.ads_product_availability,
                "ads_product_price_micros": row.ads_product_price_micros,
                "ads_product_currency_code": row.ads_product_currency_code,
            }
            for row in rows
        ],
        "reason": (
            "Do sprawdzenia: podgląd powiązania próbek Merchant ze statusem "
            "produktów w Google Ads. To nie jest gotowa zmiana pliku produktowego."
        ),
        "required_validation": [
            "review_product_identity_mapping",
            "review_ads_product_status",
            "review_merchant_issue_context",
            "prepare_supplemental_feed_preview_before_any_mutation",
            "human_confirm_before_apply",
            "mutation_audit_required",
        ],
        "blocked_claims": MERCHANT_PRODUCT_PERFORMANCE_BLOCKED_CLAIMS,
        "evidence_ids": evidence_ids,
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
    }


def _merchant_supplemental_feed_review_change_preview(
    rows: list[MerchantProductPerformanceRow],
    evidence_ids: list[str],
) -> dict[str, object]:
    candidates = [
        _merchant_supplemental_feed_candidate(row)
        for row in rows
        if row.issue_type or row.affected_attribute or row.ads_product_status
    ]
    return {
        "id": "merchant_supplemental_feed_review_preview",
        "preview_contract": MERCHANT_SUPPLEMENTAL_FEED_REVIEW_PREVIEW_CONTRACT,
        "preview_contract_label": merchant_preview_contract_label(
            MERCHANT_SUPPLEMENTAL_FEED_REVIEW_PREVIEW_CONTRACT
        ),
        "operation_type": "MerchantSupplementalFeedCandidateReview",
        "feed_target": "supplemental_feed_check_only",
        "primary_feed_mutation_allowed": False,
        "candidates": candidates,
        "reason": (
            "Do sprawdzenia: propozycje do uzupełnienia pliku produktowego. WILQ pokazuje pola do "
            "sprawdzenia i źródła sprawdzenia, ale nie wylicza docelowych wartości "
            "pliku produktowego i nie wykonuje mutacji."
        ),
        "required_validation": [
            "review_product_identity_mapping",
            "review_merchant_issue_context",
            "confirm_source_of_truth_values",
            "prepare_supplemental_feed_draft_preview",
            "validate_change_values",
            "human_confirm_before_apply",
            "mutation_audit_required",
        ],
        "blocked_claims": _unique(
            [
                *MERCHANT_PRODUCT_PERFORMANCE_BLOCKED_CLAIMS,
                "nadpisanie głównego pliku produktowego",
                "zapis do pliku produktowego uzupełniającego",
                "zmiana danych produktu",
                "automatyczna naprawa zatwierdzenia",
            ]
        ),
        "evidence_ids": evidence_ids,
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
    }


def _merchant_supplemental_feed_candidate(
    row: MerchantProductPerformanceRow,
) -> dict[str, object]:
    review_fields = _merchant_supplemental_feed_review_fields(row)
    value_sources = [
        "Merchant Center issue context",
        "Google Ads product status",
        "operator-confirmed product source of truth",
    ]
    return {
        "product_id": row.product_id,
        "title": row.sample_title or row.ads_product_title,
        "issue_type": row.issue_type,
        "affected_attribute": row.affected_attribute,
        "country": row.country,
        "reporting_context": row.reporting_context,
        "ads_product_status": row.ads_product_status,
        "ads_product_availability": row.ads_product_availability,
        "ads_product_price_micros": row.ads_product_price_micros,
        "ads_product_currency_code": row.ads_product_currency_code,
        "review_fields": review_fields,
        "value_sources_required": value_sources,
        "candidate_status": "requires_human_value_confirmation",
        "allowed_next_step": (
            "Przygotuj szkic uzupełnienia pliku produktowego dopiero po potwierdzeniu wartości "
            "w źródle produktu. Nie nadpisuj głównego pliku produktowego."
        ),
    }


def _merchant_supplemental_feed_review_fields(
    row: MerchantProductPerformanceRow,
) -> list[str]:
    attribute = (row.affected_attribute or "").removeprefix("n:").strip()
    fields = [attribute] if attribute else []
    if row.ads_product_availability:
        fields.append("availability")
    if row.ads_product_price_micros is not None:
        fields.append("price")
    return _unique(field for field in fields if field)


def _merchant_decision_cluster_groups(
    issue_clusters: list[MerchantIssueCluster],
) -> list[list[MerchantIssueCluster]]:
    grouped: dict[tuple[str, str | None, str | None, str, str | None], list[MerchantIssueCluster]]
    grouped = {}
    for cluster in issue_clusters:
        key = (
            cluster.issue_type,
            cluster.affected_attribute,
            cluster.country,
            cluster.severity,
            cluster.resolution,
        )
        grouped.setdefault(key, []).append(cluster)
    return list(grouped.values())


def _merchant_decision_from_cluster_group(
    clusters: list[MerchantIssueCluster],
    facts: list[MetricFact],
    action_ids: list[str],
) -> MerchantDecisionItem:
    if len(clusters) == 1:
        return _merchant_decision_from_cluster(clusters[0], facts, action_ids)

    primary_cluster = clusters[0]
    attribute = primary_cluster.affected_attribute or "atrybut nieznany"
    issue_type = primary_cluster.issue_type or "unknown_issue"
    display_issue_type = _merchant_display_label(issue_type)
    display_attribute = _merchant_display_label(attribute)
    context_labels = [
        cluster.reporting_context_label
        or _merchant_reporting_context_label(cluster.reporting_context)
        for cluster in sorted(clusters, key=lambda cluster: cluster.reporting_context or "")
    ]
    max_reported_count = max(cluster.product_count for cluster in clusters)
    reported_occurrences = sum(cluster.product_count for cluster in clusters)
    max_reported_label = reported_issue_occurrence_count_label(max_reported_count)
    group_facts = _facts_for_cluster_group(facts, clusters)
    return MerchantDecisionItem(
        id=(
            f"merchant_decision_{_stable_slug(primary_cluster.country or 'global')}_"
            f"{_stable_slug(primary_cluster.severity)}_{_stable_slug(issue_type)}_"
            f"{_stable_slug(attribute)}_"
            f"{_stable_slug(primary_cluster.resolution or 'resolution_unknown')}"
        ),
        decision_type="review_issue_cluster",
        status="ready",
        title=_merchant_issue_decision_title(display_issue_type, display_attribute),
        summary=(
            f"Ten sam problem Merchant występuje w {len(clusters)} raportach: "
            f"{', '.join(context_labels)}. Największy raport pokazuje "
            f"{max_reported_label}, a suma wystąpień raportowych to "
            f"{reported_occurrences}; to nie jest liczba unikalnych produktów."
        ),
        cluster_id=primary_cluster.id,
        issue_cluster_ids=[cluster.id for cluster in clusters],
        issue_type=issue_type,
        issue_type_label=display_issue_type,
        severity=primary_cluster.severity,
        severity_label=primary_cluster.severity_label
        or _merchant_severity_label(primary_cluster.severity),
        resolution=primary_cluster.resolution,
        resolution_label=primary_cluster.resolution_label
        or _merchant_resolution_label(primary_cluster.resolution),
        affected_attribute=primary_cluster.affected_attribute,
        affected_attribute_label=display_attribute,
        country=primary_cluster.country,
        reporting_context=None,
        reporting_context_label="wiele kontekstów",
        product_count=max_reported_count,
        issue_count=reported_occurrences,
        priority=_merchant_issue_priority(
            primary_cluster.severity,
            primary_cluster.resolution,
            max_reported_count,
        ),
        metric_tiles={
            "max zgłoszeń": max_reported_count,
            "raporty razem": reported_occurrences,
            "konteksty": len(clusters),
        },
        sample_product_ids=_unique(
            sample_id for cluster in clusters for sample_id in cluster.sample_product_ids
        )[:10],
        sample_titles=_unique(title for cluster in clusters for title in cluster.sample_titles)[
            :10
        ],
        change_preview=[
            _merchant_decision_change_preview(
                cluster=primary_cluster,
                product_count=max_reported_count,
                reported_issue_occurrences=reported_occurrences,
                metric_snapshot={
                    "max_issue_product_count": max_reported_count,
                    "reported_issue_occurrences": reported_occurrences,
                    "reporting_contexts": len(clusters),
                },
                sample_product_ids=_unique(
                    sample_id for cluster in clusters for sample_id in cluster.sample_product_ids
                )[:10],
                sample_titles=_unique(
                    title for cluster in clusters for title in cluster.sample_titles
                )[:10],
                evidence_ids=_unique(
                    evidence_id for cluster in clusters for evidence_id in cluster.evidence_ids
                ),
            )
        ],
        source_connectors=_unique(
            connector for cluster in clusters for connector in cluster.source_connectors
        ),
        evidence_ids=_unique(
            evidence_id for cluster in clusters for evidence_id in cluster.evidence_ids
        ),
        metric_facts=group_facts[:6],
        action_ids=action_ids
        or _unique(cluster.action_id for cluster in clusters if cluster.action_id),
        blocked_claims=_unique(claim for cluster in clusters for claim in cluster.blocked_claims),
        rationale=(
            "To jest jedna decyzja operatorska, bo typ problemu, atrybut, kraj, "
            "status i wymagana ścieżka rozwiązania są takie same. Konteksty "
            "raportowania są detalem przeglądu. Suma raportów nie jest liczbą "
            "unikalnych produktów ani gotową zmianą pliku produktowego."
        ),
        next_step=(
            "Przejrzyj problem przez akcję do sprawdzenia, sprawdź konteksty "
            "raportowania i przygotuj podgląd zmian bez automatycznej zmiany pliku produktowego."
        ),
        risk=max((cluster.risk for cluster in clusters), key=_action_risk_rank),
    )


def _merchant_decision_from_cluster(
    cluster: MerchantIssueCluster,
    facts: list[MetricFact],
    action_ids: list[str],
) -> MerchantDecisionItem:
    context = cluster.reporting_context_label or _merchant_reporting_context_label(
        cluster.reporting_context
    )
    attribute = cluster.affected_attribute or "atrybut nieznany"
    issue_type = cluster.issue_type or "unknown_issue"
    display_issue_type = _merchant_display_label(issue_type)
    display_attribute = _merchant_display_label(attribute)
    cluster_facts = _facts_for_cluster(facts, cluster)
    country_label = f"dla kraju {cluster.country}" if cluster.country else "globalnie"
    return MerchantDecisionItem(
        id=f"merchant_decision_{cluster.id}",
        decision_type="review_issue_cluster",
        status="ready",
        title=_merchant_issue_decision_title(display_issue_type, display_attribute),
        summary=(
            f"{cluster.reported_issue_summary_label}. "
            f"Status: {cluster.severity_label or _merchant_severity_label(cluster.severity)}. "
            "Zalecenie: "
            f"{cluster.resolution_label or _merchant_resolution_label(cluster.resolution)}. "
            f"Zakres: {country_label}; kontekst: {context}."
        ),
        cluster_id=cluster.id,
        issue_cluster_ids=[cluster.id],
        issue_type=issue_type,
        issue_type_label=display_issue_type,
        severity=cluster.severity,
        severity_label=cluster.severity_label or _merchant_severity_label(cluster.severity),
        resolution=cluster.resolution,
        resolution_label=cluster.resolution_label or _merchant_resolution_label(cluster.resolution),
        affected_attribute=cluster.affected_attribute,
        affected_attribute_label=display_attribute,
        country=cluster.country,
        reporting_context=cluster.reporting_context,
        reporting_context_label=context,
        product_count=cluster.product_count,
        issue_count=cluster.product_count,
        priority=_merchant_issue_priority(
            cluster.severity,
            cluster.resolution,
            cluster.product_count,
        ),
        metric_tiles={"zgłoszenia": cluster.product_count},
        sample_product_ids=cluster.sample_product_ids,
        sample_titles=cluster.sample_titles,
        change_preview=[
            _merchant_decision_change_preview(
                cluster=cluster,
                product_count=cluster.product_count,
                metric_snapshot={"issue_product_count": cluster.product_count},
                sample_product_ids=cluster.sample_product_ids,
                sample_titles=cluster.sample_titles,
                evidence_ids=cluster.evidence_ids,
            )
        ],
        source_connectors=cluster.source_connectors,
        evidence_ids=cluster.evidence_ids,
        metric_facts=cluster_facts[:6],
        action_ids=action_ids or ([cluster.action_id] if cluster.action_id else []),
        blocked_claims=cluster.blocked_claims,
        rationale=(
            "To jest klaster problemu Merchant do ręcznego sprawdzenia. Liczba oznacza "
            "wystąpienia problemu w raportach, nie gwarantowaną liczbę unikalnych "
            "produktów ani gotową zmianę pliku produktowego. Przykładowe produkty służą tylko do "
            "ręcznego sprawdzenia problemu."
        ),
        next_step=cluster.next_step,
        risk=cluster.risk,
    )


def _merchant_decision_from_tactical_item(
    item: TacticalQueueItem,
    action_ids: list[str],
) -> MerchantDecisionItem:
    issue_type = item.dimensions.get("issue_type")
    severity = item.dimensions.get("severity")
    product_count = _numeric_metric(item.metric_facts, "issue_product_count")
    display_issue_type = _merchant_display_label(issue_type or "problem pliku produktowego")
    display_attribute = _merchant_display_label(
        item.dimensions.get("affected_attribute") or "atrybut"
    )
    return MerchantDecisionItem(
        id=f"merchant_decision_{item.id}",
        decision_type="review_feed_status",
        status="ready",
        title=_merchant_issue_decision_title(display_issue_type, display_attribute),
        summary=item.diagnosis,
        issue_cluster_ids=[],
        issue_type=issue_type,
        issue_type_label=display_issue_type,
        severity=severity,
        severity_label=_merchant_severity_label(severity),
        resolution=item.dimensions.get("resolution"),
        resolution_label=_merchant_resolution_label(item.dimensions.get("resolution")),
        affected_attribute=item.dimensions.get("affected_attribute"),
        affected_attribute_label=display_attribute,
        country=item.dimensions.get("country"),
        reporting_context=item.dimensions.get("reporting_context"),
        reporting_context_label=_merchant_reporting_context_label(
            item.dimensions.get("reporting_context")
        ),
        product_count=product_count,
        issue_count=product_count,
        priority=max(1, min(100, item.priority)),
        metric_tiles=_clean_merchant_metric_tiles({"zgłoszenia": product_count}),
        source_connectors=item.source_connectors,
        evidence_ids=item.evidence_ids,
        metric_facts=item.metric_facts[:6],
        action_ids=item.action_ids or action_ids,
        blocked_claims=item.blocked_claims,
        rationale=item.diagnosis,
        next_step=item.next_step,
        risk=item.risk,
    )


def _merchant_decision_change_preview(
    *,
    cluster: MerchantIssueCluster,
    product_count: int,
    reported_issue_occurrences: int | None = None,
    metric_snapshot: dict[str, int],
    sample_product_ids: list[str],
    sample_titles: list[str],
    evidence_ids: list[str],
) -> dict[str, object]:
    reported_issue_occurrences = reported_issue_occurrences or product_count
    return {
        "id": f"merchant_feed_issue_review_{cluster.id}",
        "preview_contract": MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT,
        "preview_contract_label": merchant_preview_contract_label(
            MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT
        ),
        "operation_type": "MerchantIssueClusterReview",
        "cluster_id": cluster.id,
        "issue_type": cluster.issue_type,
        "issue_type_label": cluster.issue_type_label or _merchant_display_label(cluster.issue_type),
        "affected_attribute": cluster.affected_attribute,
        "affected_attribute_label": cluster.affected_attribute_label
        or _merchant_display_label(cluster.affected_attribute or "atrybut nieznany"),
        "country": cluster.country,
        "reporting_context": cluster.reporting_context,
        "reporting_context_label": cluster.reporting_context_label
        or _merchant_reporting_context_label(cluster.reporting_context),
        "severity": cluster.severity,
        "severity_label": cluster.severity_label or _merchant_severity_label(cluster.severity),
        "resolution": cluster.resolution,
        "resolution_label": cluster.resolution_label
        or _merchant_resolution_label(cluster.resolution),
        "metric_snapshot": metric_snapshot,
        "metric_snapshot_labels": _merchant_metric_snapshot_labels(metric_snapshot),
        "sample_products_available": bool(sample_product_ids),
        "sample_product_ids": sample_product_ids,
        "sample_titles": sample_titles,
        "sample_unavailable_reason": None
        if sample_product_ids
        else cluster.sample_unavailable_reason
        or (
            "Obecny kontrakt Merchant zwraca wymiary problemu i liczbę wystąpień, "
            "ale nie zwraca przykładowych produktów ani tytułów."
        ),
        "reason": (
            "Do sprawdzenia: podgląd konkretnej decyzji Merchant. WILQ może przygotować "
            "kolejkę oceny, ale nie może zmienić pliku produktowego ani obiecać przywrócenia "
            "zatwierdzenia bez osobnego kontraktu zapisu i audytu."
        ),
        "required_validation": [
            "review_issue_type_and_attribute",
            "review_reporting_context",
            "prepare_feed_fix_preview",
            "human_confirm_before_apply",
            "mutation_audit_required",
        ],
        "blocked_claims": [
            "ponowne zatwierdzenie produktu",
            "odzyskany przychód",
            "automatyczna zmiana pliku produktowego",
            "nadpisanie głównego pliku produktowego",
            "zapis do pliku produktowego",
            "zmiana danych produktu",
            "automatyczna naprawa zatwierdzenia",
        ],
        "evidence_ids": evidence_ids,
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
        "count_semantics": "reported_issue_occurrences",
        "reported_issue_occurrences": reported_issue_occurrences,
    }


def _merchant_aggregate_feed_status_decision(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    action_ids: list[str],
) -> MerchantDecisionItem | None:
    product_count = _numeric_metric_or_refresh_summary(
        facts,
        latest_refresh,
        "total_products",
    )
    if product_count is None:
        product_count = _numeric_metric_or_refresh_summary(
            facts,
            latest_refresh,
            "active_products",
        )
    issue_count = _numeric_metric_or_refresh_summary(
        facts,
        latest_refresh,
        "item_level_issue_count",
    )
    if issue_count is None:
        issue_count = _numeric_metric_or_refresh_summary(
            facts,
            latest_refresh,
            "merchant_action_issue_count",
        )
    if issue_count is None:
        issue_count = _numeric_metric_or_refresh_summary(
            facts,
            latest_refresh,
            "disapproved_products",
        )
    if product_count is None and issue_count is None:
        return None
    metric_facts = _merchant_health_metric_facts(latest_refresh, facts)
    return MerchantDecisionItem(
        id="merchant_decision_feed_status_review",
        decision_type="review_feed_status",
        status="ready",
        title="Merchant: przejrzyj zgłoszenia problemów pliku produktowego",
        summary=(
            f"WILQ widzi {product_count or 0} produktów i {issue_count or 0} "
            "zgłoszeń problemów pliku produktowego. Brakuje wymiarowego klastra problemów, "
            "więc to jest kolejka agregatowego review."
        ),
        issue_cluster_ids=[],
        product_count=product_count,
        issue_count=issue_count,
        priority=45,
        metric_tiles=_clean_merchant_metric_tiles(
            {
                "produkty": product_count,
                "zgłoszenia": issue_count,
            }
        ),
        source_connectors=[MERCHANT_CONNECTOR_ID],
        evidence_ids=_unique(
            [
                *(fact.evidence_id for fact in metric_facts),
                *_refresh_or_connector_evidence_ids(latest_refresh),
            ]
        ),
        metric_facts=metric_facts[:6],
        action_ids=action_ids,
        blocked_claims=[
            "ponowne zatwierdzenie produktu",
            "odzyskany przychód",
            "automatyczna zmiana pliku produktowego",
        ],
        rationale=(
            "Merchant ma zagregowane fakty produktów i pliku produktowego, ale bieżący odczyt nie "
            "dostarcza wymiarowych issue clusters. Marketer może rozpocząć review "
            "akcji, ale nie wolno twierdzić, który konkretny atrybut lub "
            "produkt został naprawiony."
        ),
        next_step=(
            "Otwórz akcję do sprawdzenia, sprawdź podgląd zmian i zatrzymaj "
            "zapis zmian do czasu sprawdzenia w WILQ."
        ),
        risk=ActionRisk.medium,
    )


def _action_risk_rank(risk: ActionRisk) -> int:
    return {
        ActionRisk.low: 0,
        ActionRisk.medium: 1,
        ActionRisk.high: 2,
        ActionRisk.critical: 3,
    }[risk]


def _merchant_issue_priority(
    severity: str,
    resolution: str | None,
    product_count: int,
) -> int:
    base_priority = {"DISAPPROVED": 10, "DEMOTED": 16, "NOT_IMPACTED": 28}.get(
        severity,
        40,
    )
    if resolution == "MERCHANT_ACTION":
        base_priority -= 4
    if product_count >= 1000:
        base_priority -= 6
    elif product_count >= 100:
        base_priority -= 3
    elif product_count >= 10:
        base_priority -= 1
    return max(5, min(100, base_priority))


def _clean_merchant_metric_tiles(
    values: dict[str, int | float | str | None],
) -> dict[str, int | float | str]:
    return {key: value for key, value in values.items() if value is not None and value != ""}


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
        summary=(
            "Akcje Merchant pozostają w trybie przygotowania do czasu sprawdzenia w WILQ "
            "zakresu zmian i audytu."
        ),
        diagnosis=(
            "Zmiany pliku produktowego lub produktów mogą wpływać na widoczność "
            "i sprzedaż. WILQ może przygotować kolejkę przeglądu, ale nie może "
            "zmieniać głównego pliku produktowego ani "
            "twierdzić, że naprawił produkty bez obsługi zapisu zmian."
        ),
        next_step=(
            "Sprawdź propozycję w WILQ, pokaż podgląd zmian i zatrzymaj zapis zmian "
            "do jawnego potwierdzenia."
        ),
        source_connectors=[MERCHANT_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        action_ids=action_ids,
        blocked_claims=[
            "zapis do pliku produktowego",
            "zmiana danych produktu",
            "automatyczna naprawa zatwierdzenia",
        ],
        risk=ActionRisk.medium,
    )
