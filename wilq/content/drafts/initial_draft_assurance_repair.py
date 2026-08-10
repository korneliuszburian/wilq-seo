"""Bounded assurance-repair orchestration for one transient draft candidate."""

from __future__ import annotations

from collections.abc import Callable

from wilq.codex.app_server import CodexAppServerClientProtocol
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.draft_assurance import ContentDraftAssuranceReceipt
from wilq.content.drafts.draft_assurance_runtime import (
    ContentDraftAssuranceFailure,
    run_regulatory_draft_assurance,
)
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftModelOutput,
)
from wilq.content.drafts.regulatory_draft_repair import repair_regulatory_assertions
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.storage.local_state import LocalStateStore

AssuranceResult = ContentDraftAssuranceReceipt | ContentDraftAssuranceFailure | None
AssureDraft = Callable[
    [ContentInitialDraftModelOutput, ContentCodexRuntimeTrace],
    AssuranceResult,
]
OutputBlocker = Callable[[ContentInitialDraftModelOutput], ContentInitialDraftBlocker | None]


def assure_and_repair_initial_draft(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    trace: ContentCodexRuntimeTrace,
    client: CodexAppServerClientProtocol,
    run_store: LocalStateStore,
    output_blocker: OutputBlocker,
) -> tuple[
    ContentInitialDraftModelOutput,
    ContentCodexRuntimeTrace,
    AssuranceResult,
    ContentInitialDraftBlocker | None,
]:
    """Run assurance and its bounded repair policy as one fail-closed step."""

    assurance = assure_regulated_draft(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        client=client,
        run_store=run_store,
    )
    if not isinstance(assurance, ContentDraftAssuranceFailure):
        return output, trace, assurance, None
    return repair_after_assurance_failure(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        trace=trace,
        assurance=assurance,
        client=client,
        assure_draft=lambda candidate, _candidate_trace: assure_regulated_draft(
            planning_input=planning_input,
            proposal=proposal,
            output=candidate,
            client=client,
            run_store=run_store,
        ),
        output_blocker=output_blocker,
    )


def repair_initial_output_blocker(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    trace: ContentCodexRuntimeTrace,
    client: CodexAppServerClientProtocol,
    output_blocker: OutputBlocker,
) -> tuple[
    ContentInitialDraftModelOutput,
    ContentCodexRuntimeTrace,
    ContentInitialDraftBlocker | None,
]:
    """Repair deterministic scope failures before invoking assurance."""

    blocker = output_blocker(output)
    if blocker is None:
        return output, trace, None
    repaired = repair_regulatory_assertions(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        blocker=blocker,
        client=client,
    )
    if repaired is None:
        return output, trace, blocker
    output, trace = repaired
    return output, trace, output_blocker(output)


def assure_regulated_draft(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    client: CodexAppServerClientProtocol,
    run_store: LocalStateStore,
) -> AssuranceResult:
    """Run the independent critic before a regulated draft can be persisted."""

    return run_regulatory_draft_assurance(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        client=client,
        run_store=run_store,
    )


def repair_after_assurance_failure(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    trace: ContentCodexRuntimeTrace,
    assurance: ContentDraftAssuranceFailure,
    client: CodexAppServerClientProtocol,
    assure_draft: AssureDraft,
    output_blocker: OutputBlocker,
) -> tuple[
    ContentInitialDraftModelOutput,
    ContentCodexRuntimeTrace,
    AssuranceResult,
    ContentInitialDraftBlocker | None,
]:
    """Repair disclosed failures to a finite regulatory-section fixed point."""

    repaired = repair_regulatory_assertions(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        blocker=_assurance_blocker(assurance),
        client=client,
        repair_reasons=assurance.repair_reasons,
    )
    if repaired is None:
        return output, trace, assurance, None
    output, trace = repaired
    blocker = output_blocker(output)
    if blocker is not None:
        assertion_repair = repair_regulatory_assertions(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            blocker=blocker,
            client=client,
        )
        if assertion_repair is not None:
            output, trace = assertion_repair
            blocker = output_blocker(output)
    if blocker is not None:
        return output, trace, assurance, blocker

    reassured = assure_draft(output, trace)
    if not isinstance(reassured, ContentDraftAssuranceFailure):
        return output, trace, reassured, None

    # Each deterministic repair canonicalizes at least one regulatory section
    # from approved official facts. The finite section count therefore bounds
    # successive critic failures without permitting an unbounded model loop.
    deterministic_repair_budget = len(
        {section.section_id for section in proposal.sections if section.regulatory_requirement_ids}
    )
    for _ in range(deterministic_repair_budget):
        deterministic = repair_regulatory_assertions(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            blocker=_assurance_blocker(reassured),
            client=client,
            force_deterministic_replace=True,
        )
        if deterministic is None:
            return output, trace, reassured, None
        output, trace = deterministic
        blocker = output_blocker(output)
        if blocker is not None:
            return output, trace, reassured, blocker
        reassured = assure_draft(output, trace)
        if not isinstance(reassured, ContentDraftAssuranceFailure):
            return output, trace, reassured, None
    return output, trace, reassured, None


def _assurance_blocker(
    assurance: ContentDraftAssuranceFailure,
) -> ContentInitialDraftBlocker:
    return ContentInitialDraftBlocker(
        code=assurance.code,
        label=assurance.label,
        reason=assurance.reason,
        next_step=assurance.next_step,
        source_codes=assurance.source_codes,
    )


__all__ = [
    "assure_and_repair_initial_draft",
    "assure_regulated_draft",
    "repair_after_assurance_failure",
    "repair_initial_output_blocker",
]
