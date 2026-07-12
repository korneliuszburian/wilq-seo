from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.content.handoff.wordpress_execution import execute_content_wordpress_draft_handoff
from wilq.content.workflow.contracts import (
    ContentWordPressDraftActivationPacketResponse,
    ContentWordPressDraftWriteReadinessResponse,
)
from wilq.credentials.runtime import variable_value
from wilq.schemas import ActionMutationReadinessRequirement, ActionObject

PreviewItems = Callable[[dict[str, Any]], list[dict[str, Any]]]


def wordpress_draft_writes_enabled() -> bool:
    return (variable_value("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def wordpress_draft_execution_readiness_requirements(
    action: ActionObject,
    *,
    activation_packet: ContentWordPressDraftActivationPacketResponse | None = None,
) -> list[ActionMutationReadinessRequirement]:
    if action.id != "act_apply_wordpress_draft_handoff":
        return []
    if activation_packet is not None:
        blocker_evidence = (
            ", ".join(
                [
                    *activation_packet.handoff_blockers,
                    *activation_packet.execution_blockers,
                ]
            )
            or "ready"
        )
        return [
            _requirement(
                code="wordpress_draft_handoff_ready",
                label="Zatwierdzone przekazanie do WordPress istnieje",
                satisfied=activation_packet.handoff_ready,
                evidence=blocker_evidence,
            ),
            _requirement(
                code="wordpress_draft_package_ready",
                label="Paczka szkicu WordPress istnieje",
                satisfied=activation_packet.draft_package_ready,
                evidence=activation_packet.draft_package_id or blocker_evidence,
            ),
        ]
    execution = execute_content_wordpress_draft_handoff(
        handoff=None,
        draft_package=None,
        mode="dry_run",
        live_write_enabled=False,
        create_draft=None,
    )
    blocker_codes = {blocker.code for blocker in execution.blockers}
    execution_blocker_evidence: str | None = (
        ", ".join(blocker.code for blocker in execution.blockers) or None
    )
    return [
        _requirement(
            code="wordpress_draft_handoff_ready",
            label="Zatwierdzone przekazanie do WordPress istnieje",
            satisfied="missing_handoff" not in blocker_codes,
            evidence=execution_blocker_evidence or "ready",
        ),
        _requirement(
            code="wordpress_draft_package_ready",
            label="Paczka szkicu WordPress istnieje",
            satisfied="missing_draft_package" not in blocker_codes,
            evidence=execution_blocker_evidence or "ready",
        ),
    ]


def wordpress_draft_target_content_readiness_requirements(
    action: ActionObject,
    *,
    activation_packet: ContentWordPressDraftActivationPacketResponse | None = None,
    preview_items: PreviewItems,
) -> list[ActionMutationReadinessRequirement]:
    if action.id != "act_apply_wordpress_draft_handoff":
        return []
    if activation_packet is not None:
        evidence_parts = [
            f"draft_package_ready={str(activation_packet.draft_package_ready).lower()}",
            f"human_review_ready={str(activation_packet.human_review_ready).lower()}",
            f"audit_ready={str(activation_packet.audit_ready).lower()}",
            f"dry_run_ready={str(activation_packet.dry_run_ready).lower()}",
        ]
        return [
            _requirement(
                code="wordpress_draft_target_content_ready",
                label="Target treści przeszedł Claim Ledger i review szkicu",
                satisfied=activation_packet.dry_run_ready,
                evidence="; ".join(evidence_parts),
            )
        ]
    items = preview_items(action.payload)
    if not items:
        return [
            _requirement(
                code="wordpress_draft_target_content_ready",
                label="Target treści przeszedł Claim Ledger i review szkicu",
                satisfied=False,
                evidence="missing_payload_preview",
            )
        ]
    first = items[0]
    apply_allowed = first.get("apply_allowed") is True
    api_mutation_ready = first.get("api_mutation_ready") is True
    required_validation = [
        value for value in first.get("required_validation", []) if isinstance(value, str)
    ]
    validation_evidence = ", ".join(required_validation[:4])
    if len(required_validation) > 4:
        validation_evidence = f"{validation_evidence}, +{len(required_validation) - 4}"
    evidence_parts = [
        f"apply_allowed={str(apply_allowed).lower()}",
        f"api_mutation_ready={str(api_mutation_ready).lower()}",
    ]
    if validation_evidence:
        evidence_parts.append(f"required_validation={validation_evidence}")
    return [
        _requirement(
            code="wordpress_draft_target_content_ready",
            label="Target treści przeszedł Claim Ledger i review szkicu",
            satisfied=apply_allowed and api_mutation_ready,
            evidence="; ".join(evidence_parts),
        )
    ]


def wordpress_draft_write_readiness_requirements(
    action: ActionObject,
    *,
    wordpress_draft_readiness: ContentWordPressDraftWriteReadinessResponse | None = None,
) -> list[ActionMutationReadinessRequirement]:
    if action.id != "act_apply_wordpress_draft_handoff":
        return []
    readiness = wordpress_draft_readiness
    if readiness is None:
        from wilq.content.workflow.api import build_content_wordpress_draft_write_readiness_response

        readiness = build_content_wordpress_draft_write_readiness_response(action_id=action.id)
    authorization_ready = readiness.suggested_write_authorization is not None
    blocker_codes = ", ".join(blocker.code for blocker in readiness.blockers[:4]) or None
    return [
        _requirement(
            code="wordpress_draft_write_readiness",
            label="WordPress draft write readiness przechodzi",
            satisfied=readiness.ready,
            evidence=blocker_codes or "ready",
        ),
        _requirement(
            code="wordpress_draft_live_write_env",
            label="Env pozwala na zapis szkicu WordPress",
            satisfied=readiness.live_write_enabled_by_env,
            evidence=str(readiness.live_write_enabled_by_env).lower(),
        ),
        _requirement(
            code="wordpress_rest_adapter_configured",
            label="REST adapter WordPress jest skonfigurowany",
            satisfied=readiness.rest_adapter_configured,
            evidence=str(readiness.rest_adapter_configured).lower(),
        ),
        _requirement(
            code="wordpress_write_authorization",
            label="Autoryzacja write z audytu jest gotowa",
            satisfied=authorization_ready,
            evidence="ready" if authorization_ready else "missing",
        ),
    ]
def _requirement(
    *,
    code: str,
    label: str,
    satisfied: bool,
    evidence: str | None = None,
) -> ActionMutationReadinessRequirement:
    return ActionMutationReadinessRequirement(
        code=code,
        label=label,
        satisfied=satisfied,
        evidence=evidence,
    )
