from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from wilq.schemas import ActionObject, MetricFact

DraftHandoffBuilder = Callable[..., ActionObject]
DraftApplyBuilder = Callable[..., ActionObject]
UniqueValues = Callable[[Iterable[str]], list[str]]
ContractLabel = Callable[[str], str]
ContractLabels = Callable[[Iterable[str]], list[str]]
MeasurementPlan = Callable[..., dict[str, Any]]
MeasurementSummary = Callable[[Mapping[str, Any]], list[str]]


def build_draft_handoff_action(
    *,
    content_payload: dict[str, Any] | None,
    content_action_metrics: list[MetricFact],
    preview_item: Callable[[dict[str, Any]], dict[str, Any]],
    handoff_builder: DraftHandoffBuilder,
    unique_values: UniqueValues,
) -> ActionObject | None:
    if content_payload is None:
        return None
    brief_previews = [
        item
        for item in content_payload.get("content_brief_preview", [])
        if isinstance(item, dict) and isinstance(item.get("candidate_id"), str)
    ]
    if not brief_previews:
        return None
    preview_items = [preview_item(item) for item in brief_previews[:4]]
    return handoff_builder(
        source_connectors=content_payload.get("source_connectors", []),
        source_metric_names=content_payload.get("source_metric_names", []),
        preview_items=preview_items,
        content_action_metrics=content_action_metrics,
        evidence_ids=unique_values(fact.evidence_id for fact in content_action_metrics),
    )


def build_draft_apply_action(
    *,
    handoff_action: ActionObject,
    apply_builder: DraftApplyBuilder,
    apply_contract_payload: Callable[[ActionObject], dict[str, Any]],
) -> ActionObject:
    return apply_builder(
        handoff_action=handoff_action,
        apply_contract_payload=apply_contract_payload(handoff_action),
    )


def build_draft_apply_contract_payload(handoff_action: ActionObject) -> dict[str, Any]:
    return {
        "contract": "action_apply_contract_v1",
        "action_id": "act_apply_wordpress_draft_handoff",
        "action_type": "wordpress_draft_handoff",
        "connector": "wordpress_ekologus",
        "allowed_operation": "create_wordpress_draft",
        "required_mode": "apply",
        "draft_only": True,
        "publication_allowed": False,
        "destructive_allowed": False,
        "adapter_status": "not_implemented",
        "required_env_flags": ["WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES"],
        "required_input_contracts": handoff_action.payload.get("required_input_contracts", []),
        "required_audit_events": [
            "action_preview_generated",
            "human_review_*",
            "action_apply_confirmed",
        ],
        "blocked_outputs": [
            "wordpress_publish",
            "wordpress_update_existing_post",
            "wordpress_delete_post",
            "production_publish_ready_claim",
        ],
        "operator_summary": (
            "Ten apply-mode obiekt nadal jest zablokowany. Może w przyszłości "
            "utworzyć tylko szkic WordPress po pełnym preview, review, confirm, "
            "impact check, env readiness i adapterze z audytem."
        ),
    }


def build_draft_handoff_preview_item(
    item: dict[str, Any],
    *,
    contract_label: ContractLabel,
    contract_labels: ContractLabels,
    measurement_plan: MeasurementPlan,
    measurement_summary: MeasurementSummary,
) -> dict[str, Any]:
    source_public_url = (
        item.get("source_public_url") if isinstance(item.get("source_public_url"), str) else None
    )
    intended_final_url = (
        item.get("intended_final_url")
        if isinstance(item.get("intended_final_url"), str)
        else source_public_url
    )
    final_canonical_url = (
        item.get("final_canonical_url")
        if isinstance(item.get("final_canonical_url"), str)
        else intended_final_url
    )
    required_validation = [
        "content_url_preflight_review",
        "final_canonical_review",
        "duplicate_or_cannibalization_check",
        "legal_factual_review",
        "content_draft_readiness_review",
        "human_confirm_before_wordpress_write",
    ]
    blocked_claims = [
        "wordpress_draft_write",
        "wordpress_publish",
        "publish_ready_claim",
        "obietnica wzrostu pozycji albo leadów",
    ]
    plan = measurement_plan(
        final_canonical_url=str(final_canonical_url) if final_canonical_url else None,
    )
    return {
        "preview_contract": "wordpress_draft_handoff_preview_v1",
        "operation_type": "wordpress_draft_handoff_review",
        "candidate_id": item.get("candidate_id"),
        "topic": item.get("topic"),
        "source_public_url": source_public_url,
        "intended_final_url": intended_final_url,
        "final_canonical_url": final_canonical_url,
        "preview_url": (
            item.get("preview_url") if isinstance(item.get("preview_url"), str) else None
        ),
        "canonical_gate_status": item.get("canonical_gate_status"),
        "canonical_gate_status_label": contract_label(str(item.get("canonical_gate_status") or "")),
        "duplicate_gate_status": item.get("duplicate_gate_status"),
        "duplicate_gate_status_label": contract_label(str(item.get("duplicate_gate_status") or "")),
        "wordpress_draft_handoff_status": "blocked_until_draft_checks_complete",
        "wordpress_draft_handoff_summary": [
            "stan przekazania do WordPress: zablokowany do przejścia kontroli szkicu"
        ],
        "required_next_action_contract": "wordpress_draft_handoff_v1",
        "required_next_action_label": contract_label("wordpress_draft_handoff_v1"),
        "post_publication_measurement_plan": plan,
        "post_publication_measurement_summary": measurement_summary(plan),
        "required_validation": required_validation,
        "required_validation_labels": contract_labels(required_validation),
        "blocked_claims": blocked_claims,
        "blocked_claim_labels": contract_labels(blocked_claims),
        "apply_allowed": False,
        "api_mutation_ready": False,
        "destructive": False,
    }
