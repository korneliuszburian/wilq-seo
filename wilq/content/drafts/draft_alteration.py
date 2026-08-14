"""Own the pre-persist alternation policy for one initial draft.

The orchestrator (initial_full_draft) previously inlined a schedule over
three repair systems: deterministic scope repair, regulated assurance and
its repair cycle, and the readability last-writer. Each repair call
appeared three to four times with the same terminal blocker closures
duplicated inline. This module owns that schedule as one policy: the
stage order, the bounded assure/readability alternation, and the
intentional asymmetry that regulatory grounding fires only when the
readability pass leaves a blocker.

The module exposes a single interface; all terminal states (blocked,
assurance failure, ready) come back as typed results so the orchestrator
has exactly one exit to persist.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from wilq.codex.app_server import CodexAppServerClientProtocol
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.draft_assurance import ContentDraftAssuranceReceipt
from wilq.content.drafts.draft_assurance_runtime import ContentDraftAssuranceFailure
from wilq.content.drafts.initial_draft_assurance_repair import (
    assure_and_repair_initial_draft,
    repair_initial_output_blocker,
)
from wilq.content.drafts.initial_draft_readability import assure_readability_and_repair
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftModelOutput,
)
from wilq.content.drafts.regulatory_draft_repair import repair_regulatory_assertions
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.storage.local_state import LocalStateStore

OutputBlocker = Callable[
    [ContentInitialDraftModelOutput],
    ContentInitialDraftBlocker | None,
]

_ALTERNATION_BUDGET = 2


class DraftAlterationResult:
    """One terminal outcome of the pre-persist alternation policy.

    ``status`` is "ready", "blocked" or "assurance_failure". Exactly the
    matching payload is set; the orchestrator maps it to persistence or a
    terminal blocker without re-reading the schedule.
    """

    def __init__(
        self,
        *,
        status: Literal["ready", "blocked", "assurance_failure"],
        output: ContentInitialDraftModelOutput | None = None,
        trace: ContentCodexRuntimeTrace | None = None,
        assurance: ContentDraftAssuranceReceipt | ContentDraftAssuranceFailure | None = None,
        blocker: ContentInitialDraftBlocker | None = None,
    ) -> None:
        self.status = status
        self.output = output
        self.trace = trace
        self.assurance = assurance
        self.blocker = blocker


def alter_draft_towards_persistence(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    trace: ContentCodexRuntimeTrace,
    client: CodexAppServerClientProtocol,
    run_store: LocalStateStore,
    output_blocker: OutputBlocker,
) -> DraftAlterationResult:
    """Run the pre-persist alternation policy to one terminal state.

    Stage order (intentional, preserved from the previous orchestrator):

    1. Deterministic scope repair — ground missing source-fact signals and
       regulatory assertions before any assurance turn.
    2. Regulated assurance with its bounded repair cycle.
    3. Readability last-writer. A readability blocker re-grounds regulatory
       assertions (the asymmetry: regulatory repair fires only here) and
       re-runs readability once; if the re-grounded output still blocks, the
       draft is terminal.
    4. If assurance changed the output (grounded facts reintroduced after the
       readability pass), alternate assurance and readability within a bounded
       budget so the persisted document keeps both exact regulatory concepts
       and readable prose.
    """

    output, trace, blocker = repair_initial_output_blocker(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        trace=trace,
        client=client,
        output_blocker=output_blocker,
    )
    if blocker is not None:
        return DraftAlterationResult(status="blocked", output=output, trace=trace, blocker=blocker)

    output, trace, assurance, blocker = assure_and_repair_initial_draft(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        trace=trace,
        client=client,
        run_store=run_store,
        output_blocker=output_blocker,
    )
    if blocker is not None:
        return DraftAlterationResult(status="blocked", output=output, trace=trace, blocker=blocker)
    if isinstance(assurance, ContentDraftAssuranceFailure):
        return DraftAlterationResult(
            status="assurance_failure", output=output, trace=trace, assurance=assurance
        )

    assured_output = output
    output, trace, blocker = assure_readability_and_repair(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        trace=trace,
        client=client,
        output_blocker=output_blocker,
    )
    if blocker is not None:
        repaired = repair_regulatory_assertions(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            blocker=blocker,
            client=client,
        )
        if repaired is not None:
            output, trace = repaired
            blocker = output_blocker(output)
            if blocker is None:
                output, trace, blocker = assure_readability_and_repair(
                    planning_input=planning_input,
                    proposal=proposal,
                    output=output,
                    trace=trace,
                    client=client,
                    output_blocker=output_blocker,
                )
                if blocker is not None:
                    repaired = repair_regulatory_assertions(
                        planning_input=planning_input,
                        proposal=proposal,
                        output=output,
                        blocker=blocker,
                        client=client,
                    )
                    if repaired is not None:
                        output, trace = repaired
                        blocker = output_blocker(output)
    if blocker is not None:
        return DraftAlterationResult(status="blocked", output=output, trace=trace, blocker=blocker)

    if output is assured_output:
        return DraftAlterationResult(
            status="ready", output=output, trace=trace, assurance=assurance
        )

    for _ in range(_ALTERNATION_BUDGET):
        before_assure = output
        output, trace, assurance, blocker = assure_and_repair_initial_draft(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            trace=trace,
            client=client,
            run_store=run_store,
            output_blocker=output_blocker,
        )
        if blocker is not None:
            return DraftAlterationResult(
                status="blocked", output=output, trace=trace, blocker=blocker
            )
        if isinstance(assurance, ContentDraftAssuranceFailure):
            return DraftAlterationResult(
                status="assurance_failure", output=output, trace=trace, assurance=assurance
            )
        output, trace, blocker = assure_readability_and_repair(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            trace=trace,
            client=client,
            output_blocker=output_blocker,
        )
        if blocker is None:
            return DraftAlterationResult(
                status="ready", output=output, trace=trace, assurance=assurance
            )
        repaired = repair_regulatory_assertions(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            blocker=blocker,
            client=client,
        )
        if repaired is None:
            return DraftAlterationResult(
                status="blocked", output=output, trace=trace, blocker=blocker
            )
        output, trace = repaired
        blocker = output_blocker(output)
        if blocker is not None:
            return DraftAlterationResult(
                status="blocked", output=output, trace=trace, blocker=blocker
            )
        if output is before_assure:
            return DraftAlterationResult(
                status="ready", output=output, trace=trace, assurance=assurance
            )
    return DraftAlterationResult(status="ready", output=output, trace=trace, assurance=assurance)


__all__ = ["DraftAlterationResult", "alter_draft_towards_persistence"]
