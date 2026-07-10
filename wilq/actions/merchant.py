from __future__ import annotations

from typing import Any

from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    MetricFact,
    OpportunityDomain,
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
