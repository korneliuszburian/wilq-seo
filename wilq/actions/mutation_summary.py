from __future__ import annotations

from collections.abc import Callable

from wilq.schemas import (
    ActionMode,
    ActionMutationReadinessResponse,
    ActionMutationReadinessSummaryResponse,
)

SummaryNextStep = Callable[
    [
        list[ActionMutationReadinessResponse],
        dict[str, int],
        ActionMutationReadinessResponse | None,
    ],
    str,
]


def build_mutation_readiness_summary(
    *,
    items: list[ActionMutationReadinessResponse],
    blocker_counts: dict[str, int],
    first_write_candidate: ActionMutationReadinessResponse | None,
    first_write_candidate_reason: str,
    activation_plan_steps: list[str],
    activation_next_step: str,
    operator_next_step: SummaryNextStep,
) -> ActionMutationReadinessSummaryResponse:
    top_blockers = [
        code
        for code, _count in sorted(
            blocker_counts.items(),
            key=lambda pair: (-pair[1], pair[0]),
        )[:8]
    ]
    return ActionMutationReadinessSummaryResponse(
        action_count=len(items),
        ready_to_request_apply_count=sum(item.ready_to_request_apply for item in items),
        vendor_write_possible_count=sum(item.vendor_write_possible for item in items),
        would_attempt_vendor_write_count=sum(item.would_attempt_vendor_write for item in items),
        prepare_only_count=sum(item.mode == ActionMode.prepare for item in items),
        missing_adapter_count=blocker_counts.get("missing_mutation_adapter", 0),
        high_risk_blocked_count=blocker_counts.get("missing_risk_allowed", 0),
        top_blockers=top_blockers,
        first_write_candidate=first_write_candidate,
        first_write_candidate_reason=first_write_candidate_reason,
        activation_plan_steps=activation_plan_steps,
        activation_next_step=activation_next_step,
        operator_next_step=operator_next_step(
            items,
            blocker_counts,
            first_write_candidate,
        ),
        items=items,
    )
