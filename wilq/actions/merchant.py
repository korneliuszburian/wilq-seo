from __future__ import annotations

from typing import Any

from wilq.actions.metric_utils import metric_sentence, unique_values
from wilq.briefing.merchant_labels import (
    merchant_display_label,
    merchant_metric_snapshot_labels,
    merchant_preview_contract_label,
    merchant_reporting_context_label,
    merchant_resolution_label,
    merchant_severity_label,
)
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    MetricFact,
    OpportunityDomain,
)

MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT = "merchant_feed_issue_review_preview_v1"


def seed_merchant_feed_issue_action() -> ActionObject:
    return ActionObject(
        id="act_review_merchant_feed_issues",
        title="Przygotuj kolejkę przeglądu pliku produktowego Merchant Center",
        domain=OpportunityDomain.merchant,
        connector="google_merchant_center",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=[connector_evidence_id("google_merchant_center")],
        human_diagnosis=(
            "Merchant Center jest core workflow WILQ. W clean runtime WILQ może "
            "przygotować tylko kolejkę bezpieczną do sprawdzenia, dopóki odczyt nie "
            "dostarczy metryk problemów pliku produktowego."
        ),
        recommended_reason=(
            "Uruchom odczyt danych Merchant albo użyj istniejących evidence, "
            "potem sprawdź w WILQ podgląd zmian przed jakąkolwiek zmianą pliku produktowego."
        ),
        payload={
            "action_type": "merchant_feed_issue",
            "connector": "google_merchant_center",
            "mode": "prepare_only",
            "source_metric_names": [],
            "review_steps": [
                "collect_merchant_issue_facts",
                "group_issue_reasons",
                "prepare_feed_fix_preview",
                "require_human_confirm_before_apply",
            ],
            "blocked_claims": [
                "ponowne zatwierdzenie produktu",
                "odzyskany przychód",
                "automatyczna zmiana pliku produktowego",
            ],
            "destructive": False,
        },
        validation_status="not_validated",
        created_by="system_core_seed",
    )


def merchant_feed_issue_action(
    *,
    merchant_action_metrics: list[MetricFact],
    merchant_issue_clusters: list[dict[str, Any]],
    merchant_payload_preview: list[dict[str, Any]],
    metric_sentence: str,
    preview_contract: str,
) -> ActionObject:
    return ActionObject(
        id="act_review_merchant_feed_issues",
        title="Przygotuj kolejkę przeglądu pliku produktowego Merchant Center",
        domain=OpportunityDomain.merchant,
        connector="google_merchant_center",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=list(dict.fromkeys(fact.evidence_id for fact in merchant_action_metrics)),
        metrics=merchant_action_metrics,
        human_diagnosis=(
            "Merchant Center ma dane o problemach pliku produktowego w WILQ. "
            f"{metric_sentence}. To uzasadnia kolejkę przeglądu problemów pliku produktowego, "
            "ale nie automatyczną zmianę danych produktu."
        ),
        recommended_reason=(
            "W widoku Merchant pokaż grupy problemów jako kolejkę przygotowawczą: "
            "sprawdź typ problemu, atrybut, kraj, podgląd zmian i sprawdzenie "
            "przed jakąkolwiek zmianą pliku produktowego."
        ),
        payload={
            "action_type": "merchant_feed_issue",
            "connector": "google_merchant_center",
            "mode": "prepare_only",
            "source_metric_names": list(
                dict.fromkeys(fact.name for fact in merchant_action_metrics)
            ),
            "issue_clusters": merchant_issue_clusters,
            "preview_contract": preview_contract,
            "payload_preview": merchant_payload_preview,
            "review_steps": [
                "identify_disapproved_products",
                "group_issue_reasons",
                "prepare_feed_fix_preview",
                "require_human_confirm_before_apply",
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
            "apply_allowed": False,
            "destructive": False,
        },
        validation_status="not_validated",
        created_by="system_metric_seed",
    )


def merchant_feed_issue_action_from_metric_facts(
    facts: list[MetricFact], *, preview_contract: str
) -> ActionObject | None:
    merchant_issue_facts = _merchant_issue_metric_facts(facts)
    if not merchant_issue_facts:
        return None
    merchant_action_metrics = merchant_issue_facts[:8]
    merchant_issue_clusters = _merchant_issue_clusters_payload(facts)
    merchant_payload_preview = _merchant_issue_payload_preview(
        merchant_issue_clusters,
        preview_contract=preview_contract,
    )
    return merchant_feed_issue_action(
        merchant_action_metrics=merchant_action_metrics,
        merchant_issue_clusters=merchant_issue_clusters,
        merchant_payload_preview=merchant_payload_preview,
        metric_sentence=metric_sentence(merchant_action_metrics),
        preview_contract=preview_contract,
    )


def _merchant_issue_clusters_payload(facts: list[MetricFact]) -> list[dict[str, Any]]:
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
    clusters: list[dict[str, Any]] = []
    for key, group_facts in grouped.items():
        issue_type, affected_attribute, country, reporting_context, severity, resolution = key
        sample_product_ids = _merchant_sample_values_for_cluster(
            facts, key, fact_name="sample_product_id"
        )
        sample_titles = _merchant_sample_values_for_cluster(
            facts, key, fact_name="sample_product_title"
        )
        clusters.append(
            {
                "issue_type": issue_type,
                "affected_attribute": affected_attribute or None,
                "country": country or None,
                "reporting_context": reporting_context or None,
                "severity": severity,
                "resolution": resolution or None,
                "product_count": sum(
                    int(fact.value) for fact in group_facts if isinstance(fact.value, int | float)
                ),
                "evidence_ids": unique_values(fact.evidence_id for fact in group_facts),
                "sample_products_available": bool(sample_product_ids),
                "sample_product_ids": sample_product_ids,
                "sample_titles": sample_titles,
            }
        )
    return sorted(
        clusters,
        key=lambda cluster: (
            merchant_severity_rank(str(cluster["severity"])),
            -int(cluster["product_count"]),
            str(cluster["issue_type"]),
        ),
    )[:10]


def _merchant_issue_payload_preview(
    issue_clusters: list[dict[str, Any]], *, preview_contract: str
) -> list[dict[str, Any]]:
    preview_items: list[dict[str, Any]] = []
    for cluster in issue_clusters[:8]:
        product_count = int(cluster.get("product_count") or 0)
        cluster_id = _merchant_issue_cluster_id(cluster)
        preview_items.append(
            {
                "id": f"merchant_feed_issue_review_{cluster_id}",
                "preview_contract": preview_contract,
                "preview_contract_label": merchant_preview_contract_label(preview_contract),
                "operation_type": "MerchantIssueClusterReview",
                "cluster_id": cluster_id,
                "issue_type": cluster.get("issue_type"),
                "issue_type_label": merchant_display_label(cluster.get("issue_type")),
                "affected_attribute": cluster.get("affected_attribute"),
                "affected_attribute_label": merchant_display_label(
                    cluster.get("affected_attribute")
                ),
                "country": cluster.get("country"),
                "reporting_context": cluster.get("reporting_context"),
                "reporting_context_label": merchant_reporting_context_label(
                    cluster.get("reporting_context")
                ),
                "severity": cluster.get("severity"),
                "severity_label": merchant_severity_label(cluster.get("severity")),
                "resolution": cluster.get("resolution"),
                "resolution_label": merchant_resolution_label(cluster.get("resolution")),
                "metric_snapshot": {"issue_product_count": product_count},
                "metric_snapshot_labels": merchant_metric_snapshot_labels(
                    {"issue_product_count": product_count}
                ),
                "sample_products_available": bool(cluster.get("sample_product_ids")),
                "sample_product_ids": cluster.get("sample_product_ids", []),
                "sample_titles": cluster.get("sample_titles", []),
                "sample_unavailable_reason": None
                if cluster.get("sample_product_ids")
                else (
                    "Obecny kontrakt Merchant zwraca wymiary problemu i liczbę "
                    "wystąpień, ale nie zwraca przykładowych produktów ani tytułów."
                ),
                "reason": (
                    "Podgląd klastra problemów pliku produktowego do sprawdzenia. WILQ może "
                    "przygotować kolejkę przeglądu, ale nie może zmienić pliku produktowego ani "
                    "obiecać przywrócenia zatwierdzenia bez osobnego kontraktu zapisu i audytu."
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
                "evidence_ids": cluster.get("evidence_ids", []),
                "api_mutation_ready": False,
                "apply_allowed": False,
                "destructive": False,
            }
        )
    return preview_items


def _merchant_sample_values_for_cluster(
    facts: list[MetricFact],
    key: tuple[str, str, str, str, str, str],
    *,
    fact_name: str,
) -> list[str]:
    issue_type, affected_attribute, country, reporting_context, severity, resolution = key
    values = [
        str(fact.value)
        for fact in sorted(facts, key=lambda fact: fact.dimensions.get("sample_index", ""))
        if fact.name == fact_name
        and fact.dimensions.get("issue_type") == issue_type
        and _merchant_attribute_matches(
            fact.dimensions.get("affected_attribute"), affected_attribute
        )
        and (fact.dimensions.get("country") or "") == country
        and (fact.dimensions.get("reporting_context") or "") == reporting_context
        and fact.dimensions.get("severity") == severity
        and (fact.dimensions.get("resolution") or "") == resolution
        and isinstance(fact.value, str)
    ]
    return unique_values(values)[:10]


def _merchant_attribute_matches(left: str | None, right: str | None) -> bool:
    return _merchant_attribute_key(left) == _merchant_attribute_key(right)


def _merchant_attribute_key(value: str | None) -> str:
    normalized = (value or "").removeprefix("n:").strip().lower()
    return "".join(char for char in normalized if char.isalnum())


def _merchant_issue_cluster_id(cluster: dict[str, Any]) -> str:
    return (
        f"merchant_issue_{_stable_slug(str(cluster.get('country') or 'global'))}_"
        f"{_stable_slug(str(cluster.get('severity') or 'UNKNOWN'))}_"
        f"{_stable_slug(str(cluster.get('issue_type') or 'unknown_issue'))}_"
        f"{_stable_slug(str(cluster.get('affected_attribute') or 'attribute_unknown'))}_"
        f"{_stable_slug(str(cluster.get('reporting_context') or 'all_contexts'))}_"
        f"{_stable_slug(str(cluster.get('resolution') or 'resolution_unknown'))}"
    )


def _stable_slug(value: str) -> str:
    lowered = value.lower()
    chars = [char if char.isalnum() else "_" for char in lowered]
    return "_".join("".join(chars).split("_")) or "unknown"


def _merchant_issue_metric_facts(facts: list[MetricFact]) -> list[MetricFact]:
    return [
        fact
        for fact in facts
        if fact.name == "issue_product_count" and fact.dimensions.get("issue_type")
    ]


def merchant_severity_rank(severity: str) -> int:
    return {"DISAPPROVED": 0, "DEMOTED": 1, "NOT_IMPACTED": 2}.get(severity, 3)
