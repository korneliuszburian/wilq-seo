from __future__ import annotations

from collections.abc import Mapping
from typing import Any

PreviewSupport = Mapping[str, Any]


def build_wordpress_draft_payload_preview(
    preview: dict[str, Any],
    *,
    support: PreviewSupport,
    url_review: dict[str, str] | None = None,
    draft_readiness_review: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Assemble the typed, draft-only WordPress payload preview.

    Content-refresh owns the policy helpers and labels. This module owns the
    payload assembly boundary so the action service can keep consuming the
    same contract without embedding the whole preview object in its queue
    builder.
    """
    topic = str(preview.get("topic") or "Plan treści")
    mode = str(preview.get("mode") or "review")
    source_type = str(preview.get("source_type") or "unknown")
    source_public_url = _string_or_none(preview.get("source_public_url"))
    intended_final_url = _string_or_none(preview.get("intended_final_url")) or source_public_url
    final_canonical_url = _string_or_none(preview.get("final_canonical_url")) or intended_final_url
    inventory_gate_status = _string_or_none(preview.get("inventory_gate_status"))
    canonical_gate_status = _string_or_none(preview.get("canonical_gate_status"))
    duplicate_gate_status = _string_or_none(preview.get("duplicate_gate_status"))
    draft_generation_status = support["draft_generation_status"](
        inventory_gate_status=inventory_gate_status,
        canonical_gate_status=canonical_gate_status,
        duplicate_gate_status=duplicate_gate_status,
    )
    draft_blockers = support["draft_blockers"](draft_generation_status)
    wordpress_draft_final_url = final_canonical_url or intended_final_url or source_public_url
    wordpress_draft_handoff_status = support["wordpress_draft_handoff_status"](
        draft_generation_status=draft_generation_status,
        draft_readiness_outcome=(draft_readiness_review or {}).get("draft_readiness_outcome"),
    )
    wordpress_draft_handoff_blockers = support["wordpress_draft_handoff_blockers"](
        wordpress_draft_handoff_status
    )
    draft_generation_contract = support["draft_generation_contract"](
        draft_generation_status=draft_generation_status,
        draft_blockers=draft_blockers,
    )
    draft_readiness_review_contract = support["draft_readiness_review_contract"]()
    wordpress_draft_handoff_contract = support["wordpress_draft_handoff_contract"](
        wordpress_draft_handoff_status=wordpress_draft_handoff_status,
        wordpress_draft_handoff_blockers=wordpress_draft_handoff_blockers,
        final_canonical_url=wordpress_draft_final_url,
    )
    post_publication_plan = support["post_publication_measurement_plan"](
        final_canonical_url=wordpress_draft_final_url,
    )
    required_validation = support["unique"](
        [
            "operator_review_approved_for_prepare",
            *[item for item in preview.get("required_validation", []) if isinstance(item, str)],
            "wordpress_draft_payload_review",
            "human_confirm_before_wordpress_write",
        ]
    )
    candidate_id = str(preview["candidate_id"])
    operation_type = support["wordpress_draft_operation"](mode)
    blocked_claims = support["unique"](
        [item for item in preview.get("blocked_claims", []) if isinstance(item, str)]
    )
    context = _preview_context(
        topic=topic,
        mode=mode,
        source_type=source_type,
        source_public_url=source_public_url,
        intended_final_url=intended_final_url,
        final_canonical_url=final_canonical_url,
        inventory_gate_status=inventory_gate_status,
        canonical_gate_status=canonical_gate_status,
        duplicate_gate_status=duplicate_gate_status,
        draft_generation_status=draft_generation_status,
        draft_blockers=draft_blockers,
        wordpress_draft_handoff_status=wordpress_draft_handoff_status,
        wordpress_draft_handoff_blockers=wordpress_draft_handoff_blockers,
        draft_generation_contract=draft_generation_contract,
        draft_readiness_review_contract=draft_readiness_review_contract,
        wordpress_draft_handoff_contract=wordpress_draft_handoff_contract,
        post_publication_plan=post_publication_plan,
        required_validation=required_validation,
        candidate_id=candidate_id,
        operation_type=operation_type,
        blocked_claims=blocked_claims,
        url_review=url_review,
        draft_readiness_review=draft_readiness_review,
    )
    return {
        **_preview_identity_fields(preview, context, support),
        **_preview_review_fields(preview, context, support),
    }


def _preview_context(**values: Any) -> dict[str, Any]:
    return values


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _preview_identity_fields(
    preview: dict[str, Any],
    context: Mapping[str, Any],
    support: PreviewSupport,
) -> dict[str, Any]:
    contract_label = support["content_contract_label"]
    contract_labels = support["content_contract_labels"]
    return {
        "preview_contract": support["preview_contract"],
        "source_preview_contract": support["source_preview_contract"],
        "candidate_id": context["candidate_id"],
        "source_type": context["source_type"],
        "source_type_label": contract_label(context["source_type"]),
        "mode": context["mode"],
        "mode_label": contract_label(context["mode"]),
        "connector": "wordpress_ekologus",
        "operation_type": context["operation_type"],
        "operation_type_label": contract_label(context["operation_type"]),
        "post_status": "draft",
        "post_status_label": contract_label("draft"),
        "topic": context["topic"],
        "intent": preview.get("intent") if isinstance(preview.get("intent"), str) else None,
        "source_public_url": context["source_public_url"],
        "preview_url": preview.get("preview_url")
        if isinstance(preview.get("preview_url"), str)
        else None,
        "intended_final_url": context["intended_final_url"],
        "final_canonical_url": context["final_canonical_url"],
        "content_url_review_recorded_outcome": (
            (context["url_review"] or {}).get("url_review_outcome") or None
        ),
        "content_url_review_reviewed_url": (
            (context["url_review"] or {}).get("reviewed_url") or None
        ),
        "content_url_review_notes": (context["url_review"] or {}).get("review_notes") or None,
        "inventory_gate_status": context["inventory_gate_status"],
        "inventory_gate_status_label": contract_label(context["inventory_gate_status"]),
        "canonical_gate_status": context["canonical_gate_status"],
        "canonical_gate_status_label": contract_label(context["canonical_gate_status"]),
        "duplicate_gate_status": context["duplicate_gate_status"],
        "duplicate_gate_status_label": contract_label(context["duplicate_gate_status"]),
        "content_gate_summary": preview.get("content_gate_summary")
        if isinstance(preview.get("content_gate_summary"), str)
        else None,
        "content_gate_status_summary": support["content_gate_status_summary"](
            inventory_gate_status=context["inventory_gate_status"],
            canonical_gate_status=context["canonical_gate_status"],
            duplicate_gate_status=context["duplicate_gate_status"],
            content_gate_summary=preview.get("content_gate_summary")
            if isinstance(preview.get("content_gate_summary"), str)
            else None,
        ),
        "draft_generation_status": context["draft_generation_status"],
        "draft_generation_status_label": contract_label(context["draft_generation_status"]),
        "draft_blockers": context["draft_blockers"],
        "draft_blocker_labels": contract_labels(context["draft_blockers"]),
        "draft_generation_contract": context["draft_generation_contract"],
        "draft_generation_summary": support["draft_generation_summary"](
            context["draft_generation_contract"]
        ),
    }


def _preview_review_fields(
    preview: dict[str, Any],
    context: Mapping[str, Any],
    support: PreviewSupport,
) -> dict[str, Any]:
    contract_labels = support["content_contract_labels"]
    draft_readiness_review = context["draft_readiness_review"] or {}
    return {
        "draft_readiness_review_contract": context["draft_readiness_review_contract"],
        "draft_readiness_review_contract_summary": support[
            "draft_readiness_review_contract_summary"
        ](context["draft_readiness_review_contract"]),
        "draft_readiness_review_recorded_outcome": (
            draft_readiness_review.get("draft_readiness_outcome") or None
        ),
        "canonical_review_recorded_outcome": (
            draft_readiness_review.get("canonical_review_outcome") or None
        ),
        "duplicate_review_recorded_outcome": (
            draft_readiness_review.get("duplicate_review_outcome") or None
        ),
        "legal_factual_review_recorded_outcome": (
            draft_readiness_review.get("legal_factual_review_outcome") or None
        ),
        "human_review_recorded_outcome": (
            draft_readiness_review.get("human_review_outcome") or None
        ),
        "draft_readiness_review_notes": (
            draft_readiness_review.get("draft_readiness_notes") or None
        ),
        "draft_readiness_review_summary": support["draft_readiness_review_summary"](
            draft_readiness_review
        ),
        "wordpress_draft_handoff_status": context["wordpress_draft_handoff_status"],
        "wordpress_draft_handoff_blockers": context["wordpress_draft_handoff_blockers"],
        "wordpress_draft_handoff_blocker_labels": contract_labels(
            context["wordpress_draft_handoff_blockers"]
        ),
        "wordpress_draft_handoff_summary": support["wordpress_draft_handoff_summary"](
            context["wordpress_draft_handoff_status"],
            context["wordpress_draft_handoff_blockers"],
        ),
        "wordpress_draft_handoff_contract": context["wordpress_draft_handoff_contract"],
        "wordpress_draft_handoff_contract_summary": support[
            "wordpress_draft_handoff_contract_summary"
        ](context["wordpress_draft_handoff_contract"]),
        "post_publication_measurement_plan": context["post_publication_plan"],
        "post_publication_measurement_summary": support[
            "post_publication_measurement_summary"
        ](context["post_publication_plan"]),
        "draft_payload": {
            "post_status": "draft",
            "post_status_label": support["content_contract_label"]("draft"),
            "post_title": support["draft_title"](context["topic"], context["mode"]),
            "post_excerpt_direction": support["draft_excerpt_direction"](preview),
            "content_blocks": support["draft_content_blocks"](preview),
        },
        "required_validation": context["required_validation"],
        "required_validation_labels": contract_labels(context["required_validation"]),
        "blocked_claims": context["blocked_claims"],
        "blocked_claim_labels": contract_labels(context["blocked_claims"]),
        "source_connectors": support["unique"](
            [item for item in preview.get("source_connectors", []) if isinstance(item, str)]
        ),
        "evidence_ids": support["unique"](
            [item for item in preview.get("evidence_ids", []) if isinstance(item, str)]
        ),
        "mutation_allowed": False,
        "apply_allowed": False,
        "api_mutation_ready": False,
        "destructive": False,
    }
