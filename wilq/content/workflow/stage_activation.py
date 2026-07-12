from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, cast

from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftExecutionResult,
    execute_content_wordpress_draft_handoff,
)
from wilq.content.workflow.contracts import (
    ContentWordPressDraftActivationPacketResponse,
    ContentWordPressDraftReadback,
    ContentWorkItemWorkflowSnapshotResponse,
)


@dataclass(frozen=True)
class ActivationProjectionCallbacks:
    readback: Callable[[ContentWordPressDraftExecutionResult], ContentWordPressDraftReadback | None]
    missing_step: Callable[..., str]
    missing_step_label: Callable[[str], str]
    missing_labels: Callable[..., list[str]]
    review_preview_label: Callable[[bool], str]
    checklist: Callable[..., list[str]]
    next_step: Callable[..., str]
    steps: Callable[..., list[str]]
    writes_enabled: Callable[[], bool]


def build_content_wordpress_draft_activation_packet_response(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    callbacks: ActivationProjectionCallbacks,
    action_id: str = "act_apply_wordpress_draft_handoff",
    latest_execution_result: ContentWordPressDraftExecutionResult | None = None,
) -> ContentWordPressDraftActivationPacketResponse:
    item = snapshot.preflight.item
    draft_package = snapshot.draft_package.draft_package_result.draft_package
    handoff_result = snapshot.wordpress_handoff.handoff_result
    handoff = handoff_result.handoff
    execution = latest_execution_result or execute_content_wordpress_draft_handoff(
        handoff=handoff,
        draft_package=draft_package,
        mode="dry_run",
        live_write_enabled=False,
        create_draft=None,
    )
    handoff_blockers: list[str] = [blocker.code for blocker in handoff_result.blockers]
    execution_blockers: list[str] = [blocker.code for blocker in execution.blockers]
    execution_ready = execution.status in {"dry_run_ready", "created"}
    draft_readback = callbacks.readback(execution)
    human_review_ready = "missing_human_review" not in handoff_blockers
    audit_ready = "missing_audit" not in handoff_blockers
    missing_step = cast(
        Literal["draft_package", "human_review", "audit", "handoff", "dry_run", "ready"],
        callbacks.missing_step(
            draft_package_ready=draft_package is not None,
            human_review_ready=human_review_ready,
            audit_ready=audit_ready,
            handoff_ready=handoff is not None,
            dry_run_ready=execution_ready,
        ),
    )
    return ContentWordPressDraftActivationPacketResponse(
        action_id=action_id,
        work_item_id=item.id,
        topic=item.topic,
        final_canonical_url=item.final_canonical_url,
        draft_package_ready=draft_package is not None,
        draft_package_id=draft_package.id if draft_package is not None else None,
        review_preview_ready=draft_package is not None,
        review_preview_status_label=callbacks.review_preview_label(draft_package is not None),
        human_review_checklist=callbacks.checklist(
            draft_package_ready=draft_package is not None,
            human_review_ready=human_review_ready,
        ),
        human_review_ready=human_review_ready,
        audit_ready=audit_ready,
        handoff_ready=handoff is not None,
        handoff_id=handoff.id if handoff is not None else None,
        dry_run_ready=execution_ready,
        live_write_enabled_by_env=callbacks.writes_enabled(),
        handoff_blockers=handoff_blockers,
        execution_blockers=execution_blockers,
        activation_missing_step=missing_step,
        activation_missing_step_label=callbacks.missing_step_label(missing_step),
        activation_missing_readiness_labels=callbacks.missing_labels(
            draft_package_ready=draft_package is not None,
            human_review_ready=human_review_ready,
            audit_ready=audit_ready,
            handoff_ready=handoff is not None,
            dry_run_ready=execution_ready,
        ),
        execution_result=execution,
        draft_readback=draft_readback,
        operator_next_step=callbacks.next_step(
            handoff_blockers,
            execution_blockers,
            execution_status=execution.status,
            draft_readback=draft_readback,
        ),
        next_steps=callbacks.steps(
            draft_package_ready=draft_package is not None,
            handoff_blockers=handoff_blockers,
            execution_blockers=execution_blockers,
            execution_status=execution.status,
        ),
        evidence_ids=item.evidence_ids,
        source_connectors=item.source_connectors,
    )
