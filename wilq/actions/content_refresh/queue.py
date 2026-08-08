from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from wilq.actions.metric_utils import (
    metric_sentence,
    prioritize_action_metrics,
    unique_values,
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

from .core import (
    _empty_content_brief_preview,
    content_refresh_payload_from_metric_facts,
)
from .review import content_url_review_contract
from .shared import CONTENT_REFRESH_ACTION_TYPE

__all__ = [
    "seed_content_refresh_action",
    "content_refresh_queue_action",
    "ContentRefreshMetricCandidate",
    "content_refresh_metric_candidate",
]



def seed_content_refresh_action() -> ActionObject:
    wordpress_evidence_id = connector_evidence_id("wordpress_ekologus")
    gsc_evidence_id = connector_evidence_id("google_search_console")
    return ActionObject(
        id="act_prepare_content_refresh_queue",
        title="Przygotuj kolejkę odświeżenia treści ekologus.pl",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=[wordpress_evidence_id, gsc_evidence_id],
        human_diagnosis=(
            "Treści są jednym z głównych obszarów pracy WILQ. WILQ może "
            "przygotować tylko kolejkę bezpieczną do sprawdzenia, dopóki "
            "GSC, WordPress i GA4 nie dostarczą danych o publicznych URL, "
            "zapytaniach, stronach i zachowaniu użytkowników."
        ),
        recommended_reason=(
            "Zbierz dane GSC dla zapytań i stron oraz spis treści WordPress, "
            "potem klasyfikuj: zachować, odświeżyć, scalić, utworzyć albo "
            "zablokować bez obietnic leadów ani rankingów."
        ),
        payload={
            "action_type": CONTENT_REFRESH_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "mode": "prepare_only",
            "source_connectors": ["google_search_console", "wordpress_ekologus"],
            "source_metric_names": [],
            "queue_steps": [
                "collect_gsc_query_page_facts",
                "join_wordpress_inventory_with_gsc",
                "classify_refresh_create_merge_block",
                "review_public_final_url",
                "require_human_confirm_before_wordpress_write",
            ],
            "content_url_review_contract": content_url_review_contract(),
            "content_brief_preview": [
                _empty_content_brief_preview(
                    wordpress_evidence_id=wordpress_evidence_id,
                    gsc_evidence_id=gsc_evidence_id,
                )
            ],
            "blocked_claims": ["wzrost liczby leadów", "wpływ na przychód", "gwarancja pozycji"],
            "destructive": False,
        },
        validation_status="not_validated",
        created_by="system_core_seed",
    )


def content_refresh_queue_action(
    *,
    content_facts: list[MetricFact],
    content_action_metrics: list[MetricFact],
    content_payload: dict[str, Any] | None,
    unique_evidence_ids: list[str],
    metric_sentence: str,
) -> ActionObject:
    payload = content_payload if content_payload is not None else {
        "action_type": "wordpress_content_refresh",
        "connector": "wordpress_ekologus",
        "mode": "prepare_only",
        "source_connectors": list(dict.fromkeys(fact.source_connector for fact in content_facts)),
        "source_metric_names": list(dict.fromkeys(fact.name for fact in content_facts)),
        "content_url_review_contract": content_url_review_contract(),
        "queue_steps": [
            "join_wordpress_inventory_with_gsc",
            "classify_refresh_create_merge_block",
            "review_public_final_url",
            "prepare_brief_preview",
            "require_human_confirm_before_wordpress_write",
        ],
        "required_validation": [
            "gsc_query_page_check",
            "wordpress_inventory_check",
            "content_url_preflight_review",
            "duplicate_or_cannibalization_check",
            "human_confirm_before_wordpress_write",
        ],
        "destructive": False,
    }
    return ActionObject(
        id="act_prepare_content_refresh_queue",
        title="Przygotuj kolejkę odświeżenia treści ekologus.pl",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=unique_evidence_ids,
        metrics=content_action_metrics,
        human_diagnosis=(
            "Spis treści WordPress istnieje w WILQ i można go zestawić z GSC/Ahrefs, "
            "żeby planować odświeżenie zamiast duplikować treści. "
            f"{metric_sentence}."
        ),
        recommended_reason=(
            "W widoku Treści przygotuj kolejkę zachowania, odświeżenia, scalenia, "
            "nowej treści albo blokady. Traktuj plan treści jako materiał do sprawdzenia: "
            "GSC i WordPress mogą dać odświeżenie albo scalenie, a Ahrefs tylko tematy do "
            "oceny po dodatkowym sprawdzeniu popytu z GSC i spisu treści."
        ),
        payload=payload,
        validation_status="not_validated",
        created_by="system_metric_seed",
    )


@dataclass(frozen=True)
class ContentRefreshMetricCandidate:
    action: ActionObject
    action_metrics: list[MetricFact]
    payload: dict[str, Any] | None


def content_refresh_metric_candidate(
    facts: list[MetricFact],
) -> ContentRefreshMetricCandidate | None:
    if not facts or not any(fact.source_connector == "wordpress_ekologus" for fact in facts):
        return None
    action_metrics = prioritize_action_metrics(
        facts,
        required_names={"content_object_count", "clicks", "domain_rating"},
    )[:10]
    payload = content_refresh_payload_from_metric_facts(facts)
    action = content_refresh_queue_action(
        content_facts=facts,
        content_action_metrics=action_metrics,
        content_payload=payload,
        unique_evidence_ids=unique_values(fact.evidence_id for fact in action_metrics),
        metric_sentence=metric_sentence(facts),
    )
    return ContentRefreshMetricCandidate(
        action=action,
        action_metrics=action_metrics,
        payload=payload,
    )
