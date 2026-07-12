from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from wilq.actions.audit_store import latest_action_confirmation_event, latest_preview_event
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.handoff.wordpress import ContentWordPressDraftHandoff
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftWriteAuthorization,
    execute_content_wordpress_draft_handoff,
)
from wilq.content.workflow.contracts import (
    ContentWordPressDraftActivationPacketResponse,
    ContentWordPressDraftWriteReadinessResponse,
)
from wilq.credentials.runtime import variable_value
from wilq.schemas import (
    ActionApplyRequest,
    ActionMutationReadinessRequirement,
    ActionObject,
)

PreviewItems = Callable[[dict[str, Any]], list[dict[str, Any]]]


@dataclass(frozen=True)
class WordPressDraftApplyCapability:
    handoff: ContentWordPressDraftHandoff
    draft_package: ContentDraftPackage
    write_authorization: ContentWordPressDraftWriteAuthorization


def wordpress_draft_apply_capability(
    action: ActionObject,
    request: ActionApplyRequest | None,
) -> tuple[WordPressDraftApplyCapability | None, list[str]]:
    if action.id != "act_apply_wordpress_draft_handoff":
        return None, []
    input_contract = request.wordpress_draft if request is not None else None
    if input_contract is None:
        return None, [
            "Apply szkicu WordPress wymaga typed work item, handoff, draft package i target URL."
        ]
    if request is None or not request.confirmed_by:
        return None, ["Apply szkicu WordPress wymaga potwierdzonego aktora operatora."]

    from wilq.briefing.content_diagnostics import build_content_diagnostics_cached
    from wilq.content.workflow.api import (
        build_content_work_item_diagnostics_snapshot_response_for_work_item,
    )
    from wilq.content.workflow.store import content_workflow_store

    diagnostics = build_content_diagnostics_cached()
    workflow_store = content_workflow_store()
    review = workflow_store.latest_human_review(input_contract.work_item_id)
    if review is None:
        return None, ["Brakuje zapisanego review człowieka dla wskazanego work itemu."]
    audit = workflow_store.latest_audit_for_review(review.id)
    snapshot = build_content_work_item_diagnostics_snapshot_response_for_work_item(
        diagnostics,
        input_contract.work_item_id,
        human_review=review,
        audit=audit,
    )
    if snapshot is None:
        return None, ["Wskazany work item nie istnieje w aktualnej kolejce WILQ."]
    draft_package = snapshot.draft_package.draft_package_result.draft_package
    handoff = snapshot.wordpress_handoff.handoff_result.handoff
    if draft_package is None or handoff is None:
        return None, ["Brakuje kompletnej paczki szkicu albo handoffu WordPress."]
    if handoff.id != input_contract.handoff_id:
        return None, ["Handoff WordPress nie pasuje do wskazanego ActionObject apply."]
    if draft_package.id != input_contract.draft_package_id:
        return None, ["Paczka szkicu nie pasuje do wskazanego ActionObject apply."]
    if handoff.work_item_id != input_contract.work_item_id:
        return None, ["Handoff nie pasuje do wskazanego work itemu."]
    if handoff.final_canonical_url != input_contract.target_url:
        return None, ["Canonical URL nie pasuje do zatwierdzonego handoffu."]
    from urllib.parse import urlparse

    target_host = (urlparse(input_contract.target_url).hostname or "").lower()
    if target_host not in {"ekologus.pl", "www.ekologus.pl"}:
        return None, ["Apply szkicu wymaga publicznego canonical URL Ekologus."]
    if handoff.publish_allowed or handoff.destructive_update_allowed:
        return None, ["Handoff WordPress nie jest draft-only."]

    confirmation = latest_action_confirmation_event(action.audit_events)
    if confirmation is None or confirmation.actor != request.confirmed_by:
        return None, ["Aktor confirm nie pasuje do zapisanego audytu ActionObject."]
    preview = latest_preview_event(action.audit_events)
    if preview is None:
        return None, ["Brakuje audytu preview ActionObject."]
    return (
        WordPressDraftApplyCapability(
            handoff=handoff,
            draft_package=draft_package,
            write_authorization=ContentWordPressDraftWriteAuthorization(
                action_id=action.id,
                preview_audit_id=preview.id,
                review_audit_id=review.id,
                confirmation_audit_id=confirmation.id,
                confirmed_by=request.confirmed_by,
            ),
        ),
        [],
    )


def wordpress_draft_writes_enabled() -> bool:
    return (variable_value("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def wordpress_draft_write_readiness(
    action: ActionObject,
) -> ContentWordPressDraftWriteReadinessResponse | None:
    if action.id != "act_apply_wordpress_draft_handoff":
        return None
    from wilq.content.workflow.api import build_content_wordpress_draft_write_readiness_response

    return build_content_wordpress_draft_write_readiness_response(action_id=action.id)


def wordpress_draft_activation_packet(
    action: ActionObject,
) -> ContentWordPressDraftActivationPacketResponse | None:
    if action.id != "act_apply_wordpress_draft_handoff":
        return None
    from wilq.briefing.content_diagnostics import build_content_diagnostics
    from wilq.content.workflow.api import (
        build_content_wordpress_draft_activation_packet_response,
        build_content_work_item_diagnostics_snapshot_response,
    )

    diagnostics = build_content_diagnostics(actions=[])
    snapshot = build_content_work_item_diagnostics_snapshot_response(diagnostics)
    return build_content_wordpress_draft_activation_packet_response(
        snapshot,
        action_id=action.id,
    )


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
